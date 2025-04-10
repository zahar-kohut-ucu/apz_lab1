from fastapi import FastAPI
import atexit
import hazelcast
import socket
import threading
import time
import os
import consul
import uvicorn

app = FastAPI()

stored_messages = []

def get_free_port():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port

PORT = get_free_port()

def consume_messages(queue):
    while True:
        try:
            msg = queue.take()
            print(f"Consumed message: {msg}")
            stored_messages.append(msg)
        except Exception as e:
            print("Error consuming message:", e)
            time.sleep(1)

@app.on_event("startup")
def startup_event():
    global hz_client, message_queue, instance_id
    
    consul_client = consul.Consul()

    hz_client = hazelcast.HazelcastClient()
    service_address = socket.gethostbyname(socket.gethostname())
    instance_id = f"{socket.gethostname()}-{PORT}"

    consul_client.agent.service.register(
        name="messages-service",
        service_id=instance_id,
        address=service_address,
        port=PORT
    )

    print(f"Registered messages-service in Consul with id {instance_id} at {service_address}:{PORT}")

    index, data = consul_client.kv.get("mq/queue")
    queue_name = data['Value'].decode() if data and data['Value'] else "message_queue"
    message_queue = hz_client.get_queue(queue_name).blocking()

    def shutdown():
        print("Removing instance...")
        consul_client.agent.service.deregister(instance_id)
        print(f"Deregistered messages-service with id {instance_id}")    
    atexit.register(shutdown)
    
    consumer_thread = threading.Thread(target=consume_messages, args=(message_queue,), daemon=True)
    consumer_thread.start()

    print("Started consumer thread for message queue.")

@app.get("/message")
def get_message():
    return {"messages": stored_messages}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=PORT)
