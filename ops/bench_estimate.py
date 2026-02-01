import json
import random
import time
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from intake.codec import parse_and_vectorize
from aegis_types import Transaction
from aegis_math import validate_dag_batch
from chronicle.graph_store import RollingChronicleStore, tx_fingerprint
from sentinel.risk import sentinel_scorer
from quorum.proofs import intel_engine


def tps(count: int, sec: float) -> float:
    return 0.0 if sec <= 0 else count / sec


def main() -> None:
    N = 20000
    payloads = [
        json.dumps(
            {
                "sender": f"u{random.randint(1, 2000)}",
                "receiver": f"u{random.randint(1, 2000)}",
                "amount": random.random() * 1000,
            }
        )
        for _ in range(N)
    ]

    t0 = time.perf_counter()
    items = parse_and_vectorize(payloads, dim=64)
    t1 = time.perf_counter()

    parents = []
    txs = []
    t2 = time.perf_counter()
    for it in items:
        tx = Transaction(it["sender"], it["receiver"], float(it["amount"]), parents)
        txs.append(tx)
        parents = [tx.hash]
    t3 = time.perf_counter()

    ok = validate_dag_batch(txs)
    t4 = time.perf_counter()

    ledger = RollingChronicleStore(max_nodes=1_000_000)
    t5 = time.perf_counter()
    prev = tx_fingerprint("ROOT")
    for tx in txs:
        tid = tx_fingerprint(tx.id)
        ledger.add(tid, [prev])
        prev = tid
    t6 = time.perf_counter()

    t7 = time.perf_counter()
    for tx in txs:
        sentinel_scorer.score(tx.sender, float(tx.amount), float(tx.timestamp))
    t8 = time.perf_counter()

    M = min(2000, len(items))
    t9 = time.perf_counter()
    v_ok = 0
    for i in range(M):
        it = items[i]
        p = intel_engine.make_proof(txs[i].id, it["vector"], "validator_1")
        ok2, _ = intel_engine.verify(p)
        v_ok += 1 if ok2 else 0
    t10 = time.perf_counter()

    ph2 = t1 - t0
    build = t3 - t2
    val = t4 - t3
    dag = t6 - t5
    sentinel = t8 - t7
    intel_t = t10 - t9

    print(
        json.dumps(
            {
                "N": N,
                "items": len(items),
                "valid": ok,
                "sec": {
                    "phase2_ingest": ph2,
                    "build_tx": build,
                    "validate": val,
                    "dag_store": dag,
                    "sentinel": sentinel,
                    "intel(M=2000)": intel_t,
                },
                "tps": {
                    "phase2_ingest": tps(N, ph2),
                    "build_tx": tps(len(items), build),
                    "validate": tps(len(txs), val),
                    "dag_store": tps(len(txs), dag),
                    "sentinel": tps(len(txs), sentinel),
                    "intel": tps(M, intel_t),
                },
                "intel_verified": v_ok,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
