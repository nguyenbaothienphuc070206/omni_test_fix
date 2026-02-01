"""Python fallback for the Cython `intake.decoder` module."""

from __future__ import annotations

import json
from typing import Any, Dict, List


def decode_json_batch(raw_data_batch: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for payload in raw_data_batch:
        s = (payload or "").strip()
        if not s.startswith("{"):
            continue
        try:
            parsed = json.loads(s)
        except Exception:
            continue
        out.append(
            {
                "sender": parsed.get("sender") or parsed.get("from") or "unknown",
                "receiver": parsed.get("receiver") or parsed.get("to") or "burn_address",
                "amount": float(parsed.get("amount") or parsed.get("value") or 0.0),
                "meta": parsed,
            }
        )
    return out
