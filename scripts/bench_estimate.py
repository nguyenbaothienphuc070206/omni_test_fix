import json
import random
import time
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from preprocessing.polymorphic import ingest_and_vectorize
from data_models import Transaction
from math_core import validate_dag_batch
from ledger.dag_ledger import DagLedger
from fraud.detector import fraud_detector
from consensus.poi import poi


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
    items = ingest_and_vectorize(payloads, dim=64)
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

    ledger = DagLedger()
    t5 = time.perf_counter()
    for tx in txs:
        ledger.add(tx.id, list(tx.parent_hashes))
    t6 = time.perf_counter()

    t7 = time.perf_counter()
    for tx in txs:
        fraud_detector.score(tx.sender, tx.amount, tx.timestamp)
    t8 = time.perf_counter()

    M = min(2000, len(items))
    t9 = time.perf_counter()
    v_ok = 0
    for i in range(M):
        it = items[i]
        p = poi.make_proof(txs[i].id, it["vector"], "validator_1")
        ok2, _ = poi.verify(p)
        v_ok += 1 if ok2 else 0
    t10 = time.perf_counter()

    ph2 = t1 - t0
    build = t3 - t2
    val = t4 - t3
    dag = t6 - t5
    fraud = t8 - t7
    poi_t = t10 - t9

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
                    "fraud": fraud,
                    "poi(M=2000)": poi_t,
                },
                "tps": {
                    "phase2_ingest": tps(N, ph2),
                    "build_tx": tps(len(items), build),
                    "validate": tps(len(txs), val),
                    "dag_store": tps(len(txs), dag),
                    "fraud": tps(len(txs), fraud),
                    "poi": tps(M, poi_t),
                },
                "poi_verified": v_ok,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
