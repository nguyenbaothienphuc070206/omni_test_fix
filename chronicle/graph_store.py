"""Phase 1: Non-linear DAG ledger (in-memory MVP).

Optimized for RAM and speed:
- Stores only parents (tuple) and a child-count per tx_id.
- Keeps a live tips set without storing children sets.
"""

from __future__ import annotations

import hashlib
import os
from collections import deque
from typing import Deque, Dict, Iterable, List, Set, Tuple


ROOT_ANCHOR = "ROOT"


def tx_fingerprint(tx_id: str) -> int:
    """Deterministic 64-bit key for any tx_id string.

    Uses blake2s(8 bytes) -> uint64. Fast, stable, low collision risk for MVP.
    """
    d = hashlib.blake2s(tx_id.encode("utf-8"), digest_size=8).digest()
    return int.from_bytes(d, "big", signed=False)


class ChronicleStore:
    """Fast O(1) lookups, O(p) insert where p=#parents."""

    def __init__(self) -> None:
        # tx_id -> parents tuple
        self._parents: Dict[str, Tuple[str, ...]] = {ROOT_ANCHOR: ()}
        # tx_id -> number of children (0 means tip)
        self._child_count: Dict[str, int] = {ROOT_ANCHOR: 0}
        self._tips: Set[str] = {ROOT_ANCHOR}

    def has(self, tx_id: str) -> bool:
        return tx_id in self._parents

    def tips(self) -> List[str]:
        return list(self._tips)

    def get_missing_parents(self, parents: Iterable[str]) -> List[str]:
        missing: List[str] = []
        for p in parents:
            if p != ROOT_ANCHOR and p not in self._parents:
                missing.append(p)
        return missing

    def add(self, tx_id: str, parents: List[str]) -> Tuple[bool, List[str]]:
        if tx_id in self._parents:
            return True, []

        parent_tuple = tuple(parents) if parents else (ROOT_ANCHOR,)
        missing = self.get_missing_parents(parent_tuple)
        if missing:
            return False, missing

        self._parents[tx_id] = parent_tuple
        self._child_count[tx_id] = 0

        for p in parent_tuple:
            prev = self._child_count.get(p, 0)
            self._child_count[p] = prev + 1
            if prev == 0 and p in self._tips:
                self._tips.remove(p)

        self._tips.add(tx_id)
        return True, []

    def add_batch(self, items: List[Tuple[str, List[str]]]) -> Dict[str, object]:
        accepted: List[str] = []
        rejected: Dict[str, List[str]] = {}

        for tx_id, parents in items:
            ok, missing = self.add(tx_id, parents)
            if ok:
                accepted.append(tx_id)
            else:
                rejected[tx_id] = missing

        return {
            "accepted": accepted,
            "rejected": rejected,
            "tips": self.tips(),
            "size": len(self._parents),
        }


class RollingChronicleStore:
    """Bounded-memory chronicle for very large streams.

    - Stores only last `max_nodes` txs in RAM.
    - Parent existence checks are best-effort: if parent is older than window,
      it's treated as existing (to keep throughput and bounded RAM).
    """

    def __init__(self, max_nodes: int = 1_000_000) -> None:
        self.max_nodes = int(max_nodes)

        self._parents: Dict[int, Tuple[int, ...]] = {}
        self._child_count: Dict[int, int] = {}
        self._tips: Set[int] = set()
        self._order: Deque[int] = deque()

        # Bloom filter for "seen tx keys" to keep parent-check accuracy high
        # even when old nodes are evicted.
        # Default ~64MB -> low false-positive rate for large streams.
        bits = int(os.getenv("CHRONICLE_BLOOM_BITS", str(512 * 1024 * 1024)))
        self._bloom_bits = max(1 << 20, bits)
        self._bloom = bytearray((self._bloom_bits + 7) // 8)

        g = tx_fingerprint(ROOT_ANCHOR)
        self._parents[g] = ()
        self._child_count[g] = 0
        self._tips.add(g)
        self._order.append(g)
        self._bloom_add(g)

    def _bloom_hashes(self, key: int) -> Tuple[int, int, int]:
        d = hashlib.blake2s(key.to_bytes(8, "big"), digest_size=12).digest()
        h1 = int.from_bytes(d[0:4], "big") % self._bloom_bits
        h2 = int.from_bytes(d[4:8], "big") % self._bloom_bits
        h3 = int.from_bytes(d[8:12], "big") % self._bloom_bits
        return h1, h2, h3

    def _bloom_add(self, key: int) -> None:
        for h in self._bloom_hashes(key):
            i = h >> 3
            self._bloom[i] |= 1 << (h & 7)

    def _bloom_maybe_has(self, key: int) -> bool:
        for h in self._bloom_hashes(key):
            i = h >> 3
            if (self._bloom[i] & (1 << (h & 7))) == 0:
                return False
        return True

    def has(self, tx: int) -> bool:
        return tx in self._parents

    def tips(self) -> List[int]:
        return list(self._tips)

    def _evict_if_needed(self) -> None:
        # Evict oldest items. Keep it simple and O(k) for k evictions.
        while len(self._order) > self.max_nodes:
            old = self._order.popleft()
            # Never evict root anchor.
            if old == tx_fingerprint(ROOT_ANCHOR):
                self._order.append(old)
                return

            self._parents.pop(old, None)
            self._child_count.pop(old, None)
            self._tips.discard(old)

    def add(self, tx: int, parents: List[int]) -> Tuple[bool, List[int]]:
        if tx in self._parents:
            return True, []

        if not parents:
            parents = [tx_fingerprint(ROOT_ANCHOR)]

        # Best-effort missing detection (only within current window).
        missing: List[int] = []
        for p in parents:
            if p != tx_fingerprint(ROOT_ANCHOR) and p not in self._parents:
                # If Bloom says "definitely not seen" -> missing.
                if not self._bloom_maybe_has(p):
                    missing.append(p)
        if missing:
            return False, missing

        pt = tuple(int(p) for p in parents)
        self._parents[tx] = pt
        self._child_count[tx] = 0
        self._tips.add(tx)
        self._order.append(tx)
        self._bloom_add(tx)

        for p in pt:
            prev = self._child_count.get(p)
            if prev is None:
                continue
            self._child_count[p] = prev + 1
            if prev == 0:
                self._tips.discard(p)

        self._evict_if_needed()
        return True, []

    def add_batch(self, items: List[Tuple[int, List[int]]]) -> Dict[str, object]:
        accepted: List[int] = []
        rejected: Dict[int, List[int]] = {}

        for tx, parents in items:
            ok, missing = self.add(tx, parents)
            if ok:
                accepted.append(tx)
            else:
                rejected[tx] = missing

        return {
            "accepted": accepted,
            "rejected": rejected,
            "tips": self.tips(),
            "size": len(self._parents),
            "max_nodes": self.max_nodes,
        }


_MAX = int(os.getenv("CHRONICLE_MAX_NODES", "1000000"))
chronicle_store = RollingChronicleStore(max_nodes=_MAX)
