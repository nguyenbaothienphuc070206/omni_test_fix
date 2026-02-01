import json
import os
import random
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from preprocessing.polymorphic import ingest_and_vectorize
from services.sharding import shard_manager
from consensus.poi import poi
from contracts.self_healing import auditor
from fraud.detector import fraud_detector
from crypto.homomorphic import he
from ledger.dag_ledger import RollingDagLedger, tx_key
from data_models import Transaction
from math_core import validate_dag_batch


def tps(n: int, sec: float) -> float:
    return 0.0 if sec <= 0 else n / sec


def bench(n_tx: int = 20000) -> dict:
    payloads = [
        json.dumps(
            {
                "sender": f"u{random.randint(1, 2000)}",
                "receiver": f"u{random.randint(1, 2000)}",
                "amount": random.random() * 1000,
            }
        )
        for _ in range(n_tx)
    ]

    out = {"N": n_tx, "sec": {}, "tps": {}}

    # Phase 2
    t0 = time.perf_counter()
    items = ingest_and_vectorize(payloads, dim=64)
    t1 = time.perf_counter()
    out["sec"]["phase2_ingest"] = t1 - t0
    out["tps"]["phase2_ingest"] = tps(n_tx, t1 - t0)

    # Build tx (shared infra)
    parents = []
    txs = []
    t2 = time.perf_counter()
    for it in items:
        tx = Transaction(it["sender"], it["receiver"], float(it["amount"]), parents)
        txs.append(tx)
        parents = [tx.hash]
    t3 = time.perf_counter()
    out["sec"]["build_tx"] = t3 - t2
    out["tps"]["build_tx"] = tps(len(txs), t3 - t2)

    # Phase 1 validate
    t4 = time.perf_counter()
    ok = validate_dag_batch(txs)
    t5 = time.perf_counter()
    out["sec"]["phase1_validate"] = t5 - t4
    out["tps"]["phase1_validate"] = tps(len(txs), t5 - t4)
    out["valid"] = bool(ok)

    # Phase 1 DAG store (rolling int64)
    ledger = RollingDagLedger(max_nodes=1_000_000)
    t6 = time.perf_counter()
    prev = tx_key("GENESIS")
    for i in range(len(txs)):
        tid = tx_key(txs[i].id)
        ledger.add(tid, [prev])
        prev = tid
    t7 = time.perf_counter()
    out["sec"]["phase1_dag_store"] = t7 - t6
    out["tps"]["phase1_dag_store"] = tps(len(txs), t7 - t6)

    # Phase 3 sharding (route)
    t8 = time.perf_counter()
    for i in range(len(txs)):
        shard_manager.get_shard_for_transaction_load_aware(txs[i].id, probe=5)
    t9 = time.perf_counter()
    out["sec"]["phase3_route"] = t9 - t8
    out["tps"]["phase3_route"] = tps(len(txs), t9 - t8)

    # Phase 6 fraud
    t10 = time.perf_counter()
    for tx in txs:
        fraud_detector.score(tx.sender, tx.amount, tx.timestamp)
    t11 = time.perf_counter()
    out["sec"]["phase6_fraud"] = t11 - t10
    out["tps"]["phase6_fraud"] = tps(len(txs), t11 - t10)

    # Phase 4 PoI (subset for runtime predictability)
    m = min(5000, len(items))
    vec = items[0]["vector"] if items else [1.0] * 64
    t12 = time.perf_counter()
    okv = 0
    for i in range(m):
        p = poi.make_proof(txs[i].id, vec, "validator_1")
        okv += 1 if poi.verify(p)[0] else 0
    t13 = time.perf_counter()
    out["sec"]["phase4_poi"] = t13 - t12
    out["tps"]["phase4_poi"] = tps(m, t13 - t12)
    out["poi_M"] = m
    out["poi_ok"] = okv

    # Phase 5 contract audit (not per-tx; measure per contract)
    safe = "def f(x):\n    return x+1\n"
    bad = "import os\n"

    # cached (same source)
    k = 2000
    t14 = time.perf_counter()
    for _ in range(k):
        auditor.auto_patch(safe)
        auditor.auto_patch(bad)
    t15 = time.perf_counter()
    out["sec"]["phase5_audit_cached_2k"] = t15 - t14

    # uncached (unique sources)
    u = 500
    t16 = time.perf_counter()
    for i in range(u):
        auditor.auto_patch(safe + f"# {i}\n")
    t17 = time.perf_counter()
    out["sec"]["phase5_audit_uncached_500"] = t17 - t16

    # Phase 7 HE (not per-tx; expensive). Measure small loop.
    if he.available():
        he.keygen(n_length=1024)
        h = 50
        t18 = time.perf_counter()
        for i in range(h):
            a = he.encrypt(i)
            b = he.encrypt(i + 1)
            c = he.add(a, b)
            he.decrypt(c)
        t19 = time.perf_counter()
        out["sec"]["phase7_he_50"] = t19 - t18
    else:
        out["sec"]["phase7_he_50"] = None

    # Phase 8 API gateway: network+framework overhead depends; not benchmarked here.
    return out


if __name__ == "__main__":
    n = int(os.getenv("BENCH_N", "20000"))
    print(json.dumps(bench(n), indent=2))
