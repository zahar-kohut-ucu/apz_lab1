from fastapi import FastAPI
import atexit
import hazelcast
import socket
import threading
import time
import os

app = FastAPI()

stored_messages = []

def consume_messages(queue):
    while True:
        try:
            msg = queue.take()
            print(f"Consumed message: {msg}")
            stored_messages.append(msg)
        except Exception as e:
            print("Error consuming message:", e)
            time.sleep(1)

def register_instance(hz_client, port):
    instances_map = hz_client.get_map("messages_instances").blocking()
    instance_id = f"{socket.gethostname()}-{port}"
    instances_map.put(instance_id, port)
    print(f"Registered messages-service instance {instance_id} on port {port}")
    return instance_id

def remove_instance(hz_client, instance_id):
    instances_map = hz_client.get_map("messages_instances").blocking()
    instances_map.remove(instance_id)
    print(f"Removed instance {instance_id}")

@app.on_event("startup")
def startup_event():
    global hz_client, message_queue, instance_id
    hz_client = hazelcast.HazelcastClient()
    port = int(os.environ.get("PORT", "8002"))
    instance_id = register_instance(hz_client, port)
    message_queue = hz_client.get_queue("message_queue").blocking()

    def shutdown():
        print("Removing instance...")
        remove_instance(hz_client, instance_id)
    atexit.register(shutdown)
    
    consumer_thread = threading.Thread(target=consume_messages, args=(message_queue,), daemon=True)
    consumer_thread.start()

    print("Started consumer thread for message queue.")

@app.get("/message")
def get_message():
    return {"messages": stored_messages}
