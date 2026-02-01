"""Phase 4: Proof-of-Intelligence (PoI) MVP.

Deterministic, cheap verification. Not mining, not staking.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple


def _u32(x: int) -> int:
    return x & 0xFFFFFFFF


def _xorshift32(seed: int) -> int:
    x = _u32(seed)
    x ^= _u32(x << 13)
    x ^= _u32(x >> 17)
    x ^= _u32(x << 5)
    return _u32(x)


def _seed_from(s: str) -> int:
    return int.from_bytes(hashlib.blake2s(s.encode("utf-8"), digest_size=4).digest(), "big")


@dataclass(slots=True)
class PoIProof:
    validator_id: str
    tx_id: str
    score: float
    proof: str


class ProofOfIntelligence:
    def __init__(self, dim: int = 64, threshold: float = 0.0) -> None:
        self.dim = dim
        env_thr = os.getenv("POI_THRESHOLD")
        self.threshold = float(env_thr) if env_thr is not None else float(threshold)
        self._weights_cache: Dict[str, List[int]] = {}
        self._cache_max = 1024

    def _weights_for(self, validator_id: str) -> List[int]:
        w = self._weights_cache.get(validator_id)
        if w is not None:
            return w

        seed = _seed_from(validator_id)
        out: List[int] = [0] * self.dim
        for i in range(self.dim):
            seed = _xorshift32(seed + i)
            out[i] = (seed % 2001) - 1000  # [-1000..1000]

        # Tiny LRU-ish cap: clear if too large (simple and fast).
        if len(self._weights_cache) >= self._cache_max:
            self._weights_cache.clear()
        self._weights_cache[validator_id] = out
        return out

    def score_vector(self, vector: List[float], validator_id: str) -> float:
        weights = self._weights_for(validator_id)
        s = 0.0
        n = min(len(vector), self.dim)
        for i in range(n):
            s += float(vector[i]) * float(weights[i]) / 1000.0
        return s

    def make_proof(self, tx_id: str, vector: List[float], validator_id: str) -> PoIProof:
        score = self.score_vector(vector, validator_id)
        payload = f"{validator_id}|{tx_id}|{score:.6f}"
        proof = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return PoIProof(validator_id=validator_id, tx_id=tx_id, score=score, proof=proof)

    def verify(self, p: PoIProof) -> Tuple[bool, str]:
        payload = f"{p.validator_id}|{p.tx_id}|{p.score:.6f}"
        expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        if expected != p.proof:
            return False, "bad_proof"
        if abs(p.score) < self.threshold:
            return False, "score_too_low"
        return True, "ok"


poi = ProofOfIntelligence()
