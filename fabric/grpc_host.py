from __future__ import annotations

import logging
from concurrent import futures
from typing import Any, Optional

try:
    import grpc  # type: ignore
except Exception:  # pragma: no cover
    grpc = None  # type: ignore

logger = logging.getLogger(__name__)


class GrpcServer:
    """Lightweight gRPC server wrapper.

    This module is intentionally minimal: it provides a clean entry point to
    start a gRPC server and is ready for service registration.
    """

    def __init__(self, max_workers: int = 10) -> None:
        self._max_workers = int(max_workers)
        self._server: Optional[Any] = None

    def start(self, port: int) -> None:
        """Start the gRPC server on the given port."""
        if grpc is None:
            raise RuntimeError("grpcio_not_installed")
        if self._server is not None:
            raise RuntimeError("grpc_server_already_started")

        server = grpc.server(futures.ThreadPoolExecutor(max_workers=self._max_workers))

        # TODO: register service implementations here.
        # Example: my_pb2_grpc.add_ExampleServicer_to_server(ExampleService(), server)

        server.add_insecure_port(f"[::]:{int(port)}")
        server.start()
        self._server = server
        logger.info("gRPC server started on port %s", port)

    def wait(self) -> None:
        """Block the current thread until termination."""
        if self._server is None:
            raise RuntimeError("grpc_server_not_started")
        self._server.wait_for_termination()

    def stop(self, grace: float = 1.0) -> None:
        """Stop the server."""
        if self._server is None:
            return
        self._server.stop(grace=grace)
        self._server = None
