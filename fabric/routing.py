import hashlib
import bisect
import os
from typing import List, Dict, Any
import threading
import time


class _Ewma:
    __slots__ = ("value",)

    def __init__(self) -> None:
        self.value = 0.0

    def update(self, x: float, alpha: float = 0.2) -> None:
        self.value = (1 - alpha) * self.value + alpha * x

class ShardManager:
    """
    Phase 3: Dynamic Load-Based Sharding.
    Implements Consistent Hashing to distribute transactions across nodes.
    Solves the Blockchain Trilemma by horizontal scaling.
    """
    def __init__(self, num_shards: int = 10, replication_factor: int = 3):
        self.num_shards = num_shards
        self.replication_factor = replication_factor
        self.ring: Dict[int, str] = {}
        self.sorted_keys: List[int] = []
        self._lock = threading.Lock()
        self._load = {f"shard_{i}": _Ewma() for i in range(num_shards)}
        self._last_seen = {f"shard_{i}": 0.0 for i in range(num_shards)}
        self._initialize_ring()

    def _initialize_ring(self):
        """Builds the consistent hash ring."""
        for i in range(self.num_shards):
            shard_id = f"shard_{i}"
            for r in range(self.replication_factor):
                # Virtual nodes for balanced distribution
                key = self._hash(f"{shard_id}:{r}")
                self.ring[key] = shard_id
                bisect.insort(self.sorted_keys, key)
        # Keep imports and report scripts machine-parsable by default.
        # Opt-in init logging via AEGIS_VERBOSE_INIT=1.
        if os.getenv("AEGIS_VERBOSE_INIT") == "1":
            print(
                f"Sharding Manager Initialized: {self.num_shards} shards, {len(self.sorted_keys)} virtual nodes."
            )

    def _hash(self, key: str) -> int:
        """SHA-256 specific hashing for the ring."""
        return int(hashlib.sha256(key.encode('utf-8')).hexdigest(), 16)

    def get_shard_for_transaction(self, tx_id: str) -> str:
        """
        Determines which shard handles a given transaction ID (O(log N)).
        """
        if not self.ring:
            return None
        
        key = self._hash(tx_id)
        # Binary search for the next highest node in the ring
        idx = bisect.bisect_right(self.sorted_keys, key)
        
        # Wrap around to 0 if at end
        if idx == len(self.sorted_keys):
            idx = 0
            
        return self.ring[self.sorted_keys[idx]]

    def record_shard_load(self, shard_id: str, latency_ms: float, items: int = 1) -> None:
        """Records a cheap load signal (EWMA of latency per item)."""
        if shard_id is None:
            return
        per_item = float(latency_ms) / max(1, int(items))
        with self._lock:
            ewma = self._load.get(shard_id)
            if ewma is not None:
                ewma.update(per_item)
                self._last_seen[shard_id] = time.time()

    def get_shard_for_transaction_load_aware(self, tx_id: str, probe: int = 5) -> str:
        """Routes to the least-loaded shard among a small ring neighborhood.

        Complexity: O(log V + probe)
        """
        if not self.ring:
            return None

        key = self._hash(tx_id)
        idx = bisect.bisect_right(self.sorted_keys, key)
        if idx == len(self.sorted_keys):
            idx = 0

        best_shard = self.ring[self.sorted_keys[idx]]
        with self._lock:
            best_load = self._load.get(best_shard).value if best_shard in self._load else 0.0

            # Probe next few virtual nodes; pick shard with min EWMA load.
            nkeys = len(self.sorted_keys)
            for step in range(1, max(1, int(probe)) + 1):
                sid = self.ring[self.sorted_keys[(idx + step) % nkeys]]
                load = self._load.get(sid).value if sid in self._load else 0.0
                if load < best_load:
                    best_load = load
                    best_shard = sid

        return best_shard

    def distribute_batch(self, transactions: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """
        Distributes a batch of transactions to their respective shards.
        """
        sharded_batches = {f"shard_{i}": [] for i in range(self.num_shards)}
        
        for tx in transactions:
            # Assume 'sender' or 'id' is the routing key
            routing_key = tx.get("id") or tx.get("sender")
            shard_id = self.get_shard_for_transaction_load_aware(routing_key)
            sharded_batches[shard_id].append(tx)
            
        return sharded_batches

# Singleton
shard_manager = ShardManager()
