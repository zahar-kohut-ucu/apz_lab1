import subprocess
import atexit
import socket
from concurrent import futures
import grpc
import hazelcast
import proto.logging_pb2 as logging_pb2
import proto.logging_pb2_grpc as logging_pb2_grpc

BASE_PORT = 50051  

class LoggingService(logging_pb2_grpc.LoggingServicer):
    def __init__(self, hazelcast_client):
        self.hz_client = hazelcast_client
        self.messages_map = self.hz_client.get_map("messages").blocking()

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

def get_available_port(hz_client):
    instances_map = hz_client.get_map("instances").blocking()
    
    used_ports = set(instances_map.values())
    for port in range(BASE_PORT, BASE_PORT + 10):  
        if port not in used_ports:
            return port
    raise RuntimeError("No available ports for new logging instance!")

def register_instance(hz_client, port):
    instances_map = hz_client.get_map("instances").blocking()
    instance_id = f"{socket.gethostname()}-{port}"
    instances_map.put(instance_id, port)
    print(f"Registered instance {instance_id} on port {port}")
    return instance_id

def remove_instance(hz_client, instance_id):
    instances_map = hz_client.get_map("instances").blocking()
    instances_map.remove(instance_id)
    print(f"Removed instance {instance_id}")

def serve():
    hz_process = start_hazelcast()  
    hz_client = hazelcast.HazelcastClient()

    grpc_port = get_available_port(hz_client) 
    instance_id = register_instance(hz_client, grpc_port)
    
    def shutdown():
        print("Shutting down Hazelcast...")
        remove_instance(hz_client, instance_id)  
        hz_process.terminate()
        hz_process.wait()

    atexit.register(shutdown)

    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    logging_pb2_grpc.add_LoggingServicer_to_server(LoggingService(hz_client), server)
    server.add_insecure_port(f"[::]:{grpc_port}")
    server.start()
    print(f"Logging service started on port {grpc_port}")
    server.wait_for_termination()

if __name__ == "__main__":
    serve()
