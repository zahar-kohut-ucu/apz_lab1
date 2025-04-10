import subprocess
import atexit
import socket
from concurrent import futures
import grpc
import hazelcast
import proto.logging_pb2 as logging_pb2
import proto.logging_pb2_grpc as logging_pb2_grpc
import consul

BASE_PORT = 50051  

class LoggingService(logging_pb2_grpc.LoggingServicer):
    def __init__(self, hazelcast_client, messages_map_name):
        self.hz_client = hazelcast_client
        self.messages_map = self.hz_client.get_map(messages_map_name).blocking()

    def StoreMessage(self, request, context):
        if self.messages_map.contains_key(request.id):
            print("Message with such ID already exists.")
            return logging_pb2.LogResponse(success=False)

        self.messages_map.put(request.id, request.msg)
        print(f"Logged: {request.msg}")
        return logging_pb2.LogResponse(success=True)

    def GetMessages(self, request, context):
        all_messages = self.messages_map.values()
        print(all_messages)
        return logging_pb2.LogResponse(success=True, messages=", ".join(all_messages))

def start_hazelcast():
    return subprocess.Popen(["../hazelcast-5.5.0/bin/hz-start"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def get_available_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

def serve():
    hz_process = start_hazelcast()  
    hz_client = hazelcast.HazelcastClient()

    grpc_port = get_available_port() 
    instance_id = f"{socket.gethostname()}-{grpc_port}"

    consul_client = consul.Consul()
    service_address = socket.gethostbyname(socket.gethostname())
    consul_client.agent.service.register(
        name="logging-service",
        service_id=instance_id,
        address=service_address,
        port=grpc_port
    )
    print(f"Registered logging-service in Consul with id {instance_id} at {service_address}:{grpc_port}")

    index, data = consul_client.kv.get("messages/dict")
    if data and data['Value']:
        messages_map_name = data['Value'].decode()
    else:
        messages_map_name = "messages"

    def shutdown():
        print("Shutting down Hazelcast...")
        consul_client.agent.service.deregister(instance_id)
        print(f"Deregistered logging-service with id {instance_id}")
        hz_process.terminate()
        hz_process.wait()

    atexit.register(shutdown)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    logging_pb2_grpc.add_LoggingServicer_to_server(LoggingService(hz_client, messages_map_name), server)
    server.add_insecure_port(f"[::]:{grpc_port}")
    server.start()
    print(f"Logging service started on port {grpc_port}")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
