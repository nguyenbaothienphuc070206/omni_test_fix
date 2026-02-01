"""Compatibility shim.

This module used to host a placeholder gRPC service implementation.
The canonical implementation now lives in `fabric/grpc_host.py`.
"""

from fabric.grpc_host import GrpcServer

__all__ = ["GrpcServer"]