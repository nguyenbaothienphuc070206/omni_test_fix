"""Phase 6: Neural Fraud Detection (MVP).

Cheap online scoring per sender using Welford stats + rate limiter.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(slots=True)
class _Stats:
    n: int = 0
    mean: float = 0.0
    m2: float = 0.0
    last_ts: float = 0.0
    ewma_rate: float = 0.0  # tx/sec

    def update(self, x: float, ts: float, alpha: float = 0.2) -> None:
        self.n += 1
        delta = x - self.mean
        self.mean += delta / self.n
        self.m2 += delta * (x - self.mean)

        if self.last_ts > 0:
            dt = max(1e-6, ts - self.last_ts)
            rate = 1.0 / dt
            self.ewma_rate = (1 - alpha) * self.ewma_rate + alpha * rate
        self.last_ts = ts

    def var(self) -> float:
        return self.m2 / (self.n - 1) if self.n > 1 else 0.0


class FraudDetector:
    def __init__(self, rate_threshold: float = 20.0, z_suspicious: float = 3.0, z_outlier: float = 6.0) -> None:
        self._by_sender: Dict[str, _Stats] = {}
        self.rate_threshold = float(rate_threshold)
        self.z_suspicious = float(z_suspicious)
        self.z_outlier = float(z_outlier)

    def set_thresholds(self, *, rate_threshold: float | None = None, z_suspicious: float | None = None, z_outlier: float | None = None) -> None:
        if rate_threshold is not None:
            self.rate_threshold = float(rate_threshold)
        if z_suspicious is not None:
            self.z_suspicious = float(z_suspicious)
        if z_outlier is not None:
            self.z_outlier = float(z_outlier)

    def score(self, sender: str, amount: float, ts: float | None = None) -> Tuple[float, Dict[str, object]]:
        ts = ts or time.time()
        st = self._by_sender.get(sender)
        if st is None:
            st = _Stats()
            self._by_sender[sender] = st

        st.update(float(amount), ts)

        var = st.var()
        std = var ** 0.5 if var > 0 else 0.0
        z = (amount - st.mean) / std if std > 1e-9 else 0.0

        # risk in [0,1]
        risk = 0.0
        flags = []

        if st.ewma_rate > 20.0:
            risk = max(risk, 0.9)
            flags.append("high_rate")

        if st.ewma_rate > self.rate_threshold:
            risk = max(risk, 0.9)
            if "high_rate" not in flags:
                flags.append("high_rate")

        if abs(z) > self.z_outlier:
            risk = max(risk, 0.95)
            flags.append("amount_outlier")
        elif abs(z) > self.z_suspicious:
            risk = max(risk, 0.6)
            flags.append("amount_suspicious")

        meta = {
            "n": st.n,
            "mean": st.mean,
            "std": std,
            "z": z,
            "rate": st.ewma_rate,
            "flags": flags,
        }
        return risk, meta


fraud_detector = FraudDetector()
