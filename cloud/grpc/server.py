"""gRPC server for NexTTS service."""

from concurrent import futures

import grpc

try:
    from cloud.proto import nexxtts_pb2_grpc
    from cloud.grpc import handlers
except ModuleNotFoundError:
    from proto import nexxtts_pb2_grpc
    import grpc.handlers


def serve(port: int = 50051, max_workers: int = 10):
    """Create and return a gRPC server.

    Args:
        port: Port to listen on (default: 50051)
        max_workers: Maximum thread pool workers (default: 10)

    Returns:
        Configured gRPC server
    """
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
    nexxtts_pb2_grpc.add_NexTTSServicer_to_server(
        handlers.NexTTTServicer(),
        server,
    )
    server.add_insecure_port(f"[::]:{port}")
    return server


def start_serve(port: int = 50051, max_workers: int = 10) -> None:
    """Start the gRPC server.

    Args:
        port: Port to listen on (default: 50051)
        max_workers: Maximum thread pool workers (default: 10)
    """
    server = serve(port=port, max_workers=max_workers)
    server.start()
    server.wait_for_termination()


if __name__ == "__main__":
    start_serve()
