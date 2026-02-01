"""Python fallback for the Cython `math_core` module."""

from __future__ import annotations

from typing import Iterable


def validate_dag_batch(transactions: Iterable[object]) -> bool:
    # Minimal parity with the Cython implementation: integrity checks.
    for tx in transactions:
        verify = getattr(tx, "verify_integrity", None)
        if verify is None or not verify():
            return False
        setattr(tx, "is_validated", True)
    return True
