from concurrent import futures
import grpc
import proto.logging_pb2 as logging_pb2
import proto.logging_pb2_grpc as logging_pb2_grpc

class LoggingService(logging_pb2_grpc.LoggingServicer):
    def __init__(self):
        self.messages = {}

    def StoreMessage(self, request, context):
        if request.id in self.messages:
            print("Message with such ID already exists.")
            return logging_pb2.LogResponse(success=True)  

        self.messages[request.id] = request.msg
        print(f"Logged: {request.msg}")
        return logging_pb2.LogResponse(success=True)
    
    def GetMessages(self, request, context):
        return logging_pb2.LogResponse(success=True, messages="\n".join(self.messages.values()))

def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    logging_pb2_grpc.add_LoggingServicer_to_server(LoggingService(), server)
    server.add_insecure_port("[::]:50051")
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    serve()