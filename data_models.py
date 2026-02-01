"""Python fallback for the Cython `data_models` module.

Kept intentionally small and fast so the project runs even if Cython extensions
aren't built.
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List


def _now() -> float:
    return time.time()


@dataclass(slots=True)
class Transaction:
    sender: str
    receiver: str
    amount: float
    parent_hashes: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=_now)
    is_validated: bool = False
    hash: str = field(init=False)
    id: str = field(init=False)

    def __post_init__(self) -> None:
        self.hash = self._calculate_hash()
        self.id = self.hash

    def _calculate_hash(self) -> str:
        payload = f"{self.sender}|{self.receiver}|{self.amount}|{self.timestamp}|{''.join(self.parent_hashes)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def verify_integrity(self) -> bool:
        return self._calculate_hash() == self.hash

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "parents": list(self.parent_hashes),
            "timestamp": self.timestamp,
            "hash": self.hash,
        }
