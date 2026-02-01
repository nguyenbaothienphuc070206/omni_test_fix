"""Phase 2: Polymorphic ingestion + vectorization.

Simple, fast, no dependencies. Parsing is best-effort.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
import zlib
import csv
import io
from typing import Any, Dict, List, Tuple


def _to_float(x: Any) -> float | None:
    if x is None:
        return 0.0
    try:
        return float(x)
    except Exception:
        return None

_SQL_INSERT_RE = re.compile(
    r"insert\s+into\s+\w+\s*\([^)]*\)\s*values\s*\((?P<values>.*)\)\s*;?",
    re.IGNORECASE,
)


def _hash32(s: str) -> int:
    # Fast deterministic 32-bit hash.
    return zlib.crc32(s.encode("utf-8")) & 0xFFFFFFFF


def _feature_hash_vector(tokens: List[str], dim: int = 64) -> List[float]:
    vec = [0.0] * dim
    for t in tokens:
        h = _hash32(t)
        vec[h % dim] += 1.0
    return vec


def _try_json(s: str) -> Tuple[bool, Dict[str, Any]]:
    if not s.startswith("{"):
        return False, {}
    try:
        return True, json.loads(s)
    except Exception:
        return False, {}


def _try_xml(s: str) -> Tuple[bool, Dict[str, Any]]:
    if not s.startswith("<"):
        return False, {}
    try:
        root = ET.fromstring(s)
    except Exception:
        return False, {}

    def find_text(*names: str) -> str | None:
        for name in names:
            el = root.find(f".//{name}")
            if el is not None and el.text:
                return el.text.strip()
        return None

    sender = find_text("sender", "from")
    receiver = find_text("receiver", "to")
    amount = find_text("amount", "value")

    meta = {"tag": root.tag, "xml": s}
    return True, {"sender": sender, "receiver": receiver, "amount": amount, "meta": meta}


def _try_sql(s: str) -> Tuple[bool, Dict[str, Any]]:
    m = _SQL_INSERT_RE.match(s)
    if not m:
        return False, {}
    values = m.group("values")
    # csv parsing handles quoted commas: ('a,b', 'c', 1)
    try:
        reader = csv.reader(io.StringIO(values), skipinitialspace=True)
        parts = next(reader)
    except Exception:
        parts = [p.strip() for p in values.split(",")]
    if len(parts) < 3:
        return False, {}

    def unquote(x: str) -> str:
        x = x.strip()
        if (x.startswith("'") and x.endswith("'")) or (x.startswith('"') and x.endswith('"')):
            return x[1:-1]
        return x

    sender = unquote(parts[0])
    receiver = unquote(parts[1])
    amount = unquote(parts[2])
    return True, {"sender": sender, "receiver": receiver, "amount": amount, "meta": {"sql": s}}


def _try_text(s: str) -> Tuple[bool, Dict[str, Any]]:
    # Formats:
    #   alice->bob:12.5
    #   alice bob 12.5
    s = s.strip()
    if not s:
        return False, {}

    if "->" in s and ":" in s:
        left, amt = s.split(":", 1)
        sender, receiver = [x.strip() for x in left.split("->", 1)]
        return True, {"sender": sender, "receiver": receiver, "amount": amt.strip(), "meta": {"text": s}}

    parts = s.split()
    if len(parts) >= 3:
        return True, {"sender": parts[0], "receiver": parts[1], "amount": parts[2], "meta": {"text": s}}

    return False, {}


def parse_payload(payload: str) -> Dict[str, Any] | None:
    s = (payload or "").strip()

    ok, parsed = _try_json(s)
    if ok:
        amt = _to_float(parsed.get("amount") or parsed.get("value"))
        if amt is None:
            return None
        return {
            "sender": parsed.get("sender") or parsed.get("from") or "unknown",
            "receiver": parsed.get("receiver") or parsed.get("to") or "burn_address",
            "amount": amt,
            "meta": parsed,
        }

    ok, parsed = _try_xml(s)
    if ok:
        amt = _to_float(parsed.get("amount"))
        if amt is None:
            return None
        return {
            "sender": parsed.get("sender") or "unknown",
            "receiver": parsed.get("receiver") or "burn_address",
            "amount": amt,
            "meta": parsed.get("meta") or {},
        }

    ok, parsed = _try_sql(s)
    if ok:
        amt = _to_float(parsed.get("amount"))
        if amt is None:
            return None
        return {
            "sender": parsed.get("sender") or "unknown",
            "receiver": parsed.get("receiver") or "burn_address",
            "amount": amt,
            "meta": parsed.get("meta") or {},
        }

    ok, parsed = _try_text(s)
    if ok:
        amt = _to_float(parsed.get("amount"))
        if amt is None:
            return None
        return {
            "sender": parsed.get("sender") or "unknown",
            "receiver": parsed.get("receiver") or "burn_address",
            "amount": amt,
            "meta": parsed.get("meta") or {},
        }

    return None


def parse_and_vectorize(payloads: List[str], dim: int = 64) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for p in payloads:
        n = parse_payload(p)
        if not n:
            continue
        tokens = [
            f"s:{n['sender']}",
            f"r:{n['receiver']}",
            f"a:{n['amount']}",
        ]
        vec = _feature_hash_vector(tokens, dim=dim)
        n["vector"] = vec
        out.append(n)
    return out
