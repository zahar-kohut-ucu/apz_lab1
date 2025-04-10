from fastapi import FastAPI, HTTPException
import requests
import uuid
import grpc
import proto.logging_pb2 as logging_pb2
import proto.logging_pb2_grpc as logging_pb2_grpc
import time
from pydantic import BaseModel
import hazelcast as hz
import random
import consul
import uvicorn

app = FastAPI()

class Msg(BaseModel):
    msg: str
    

hz_client = hz.HazelcastClient()
consul_client = consul.Consul()

def get_service_instances(service_name: str):
    index, service_entries = consul_client.health.service(service_name, passing=True)
    instances = []
    for entry in service_entries:
        service = entry['Service']
        instances.append((service['Address'], service['Port']))
    return instances

def select_logging_instance():
    instances = get_service_instances("logging-service")
    if not instances:
        raise HTTPException(status_code=500, detail="No logging instances available")
    return random.choice(instances)

def select_message_instance():
    instances = get_service_instances("messages-service")
    if not instances:
        raise HTTPException(status_code=500, detail="No messages instances available")
    return random.choice(instances)

def retry_rpc(func, max_retries=3, backoff_factor=2):
    for attempt in range(max_retries):
        try:
            return func()
        except grpc.RpcError as e:
            if attempt < max_retries - 1:
                wait_time = backoff_factor ** attempt
                print(f"Retrying in {wait_time} seconds due to: {e.details()}")
                time.sleep(wait_time)
            else:
                raise HTTPException(status_code=500, detail="Logging service unavailable")

@app.post("/send")
def send_message(item: Msg):
    message_id = str(uuid.uuid4())
    logging_address, logging_port = select_logging_instance()
    LOGGING_SERVICE_GRPC = f"{logging_address}:{logging_port}"
    def grpc_call():
        with grpc.insecure_channel(LOGGING_SERVICE_GRPC) as channel:
            stub = logging_pb2_grpc.LoggingStub(channel)
            return stub.StoreMessage(logging_pb2.LogRequest(id=message_id, msg=item.msg))

    response = retry_rpc(grpc_call)

    if not response.success:
        raise HTTPException(status_code=500, detail="Failed to log message")
    
    index, data = consul_client.kv.get("mq/queue")
    queue_name = data['Value'].decode() if data and data['Value'] else "message_queue"
    try:
        message_queue = hz_client.get_queue(queue_name).blocking()
        message_queue.put(item.msg)
        print(f"Enqueued message: {item.msg} to queue: {queue_name}")
    except Exception as e:
        print("Failed to enqueue message:", e)
        raise HTTPException(status_code=500, detail="Failed to enqueue message")
    
    return {"id": message_id, "msg": item.msg}

@app.get("/messages")
def get_messages():
    logging_address, logging_port = select_logging_instance()
    LOGGING_SERVICE_GRPC = f"{logging_address}:{logging_port}"
    with grpc.insecure_channel(LOGGING_SERVICE_GRPC) as channel:
        stub = logging_pb2_grpc.LoggingStub(channel)
        log_response = stub.GetMessages(logging_pb2.Empty())
    
    message_address, message_port = select_message_instance()
    messages_service_url = f"http://{message_address}:{message_port}/message"
    messages_response = requests.get(messages_service_url)
    if messages_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Messages service unavailable")
    
    return {
        "logged_messages": log_response.messages,
        "messages_service_data": messages_response.json()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)