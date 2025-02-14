from fastapi import FastAPI, HTTPException
import requests
import uuid
import grpc
import proto.logging_pb2 as logging_pb2
import proto.logging_pb2_grpc as logging_pb2_grpc
import time
from pydantic import BaseModel

app = FastAPI()

class Msg(BaseModel):
    msg: str

LOGGING_SERVICE_GRPC = "420"
MESSAGES_SERVICE_URL = "http://localhost:8002/message"

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
    def grpc_call():
        with grpc.insecure_channel(LOGGING_SERVICE_GRPC) as channel:
            stub = logging_pb2_grpc.LoggingStub(channel)
            return stub.StoreMessage(logging_pb2.LogRequest(id=message_id, msg=item.msg))

    response = retry_rpc(grpc_call)

    if not response.success:
        raise HTTPException(status_code=500, detail="Failed to log message")

    return {"id": message_id, "msg": item.msg}

@app.get("/messages")
def get_messages():
    with grpc.insecure_channel(LOGGING_SERVICE_GRPC) as channel:
        stub = logging_pb2_grpc.LoggingStub(channel)
        log_response = stub.GetMessages(logging_pb2.Empty())
    
    messages_response = requests.get(MESSAGES_SERVICE_URL)
    
    if messages_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Messages service unavailable")
    
    return {"logged_messages": log_response.messages, "static_message": messages_response.text}