import json
import os
import random
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api.routes import router
from preprocessing.polymorphic import normalize_one
from services.sharding import shard_manager
from consensus.poi import poi
from contracts.self_healing import auditor
from fraud.detector import fraud_detector
from crypto.homomorphic import he
from ledger.dag_ledger import RollingDagLedger, tx_key


def _acc(ok: int, total: int) -> float:
    return 1.0 if total <= 0 else ok / total


def _f1(tp: int, fp: int, fn: int) -> float:
    p = 0.0 if (tp + fp) == 0 else tp / (tp + fp)
    r = 0.0 if (tp + fn) == 0 else tp / (tp + fn)
    return 0.0 if (p + r) == 0 else 2 * p * r / (p + r)


def phase2_accuracy() -> dict:
    cases = [
        ("{\"sender\":\"a\",\"receiver\":\"b\",\"amount\":1}", ("a", "b", 1.0)),
        ("<tx><sender>a</sender><receiver>b</receiver><amount>2</amount></tx>", ("a", "b", 2.0)),
        ("insert into t(sender,receiver,amount) values('a','b',3)", ("a", "b", 3.0)),
        ("a->b:4", ("a", "b", 4.0)),
    ]

    ok = 0
    total = 0
    for raw, exp in cases:
        total += 1
        n = normalize_one(raw)
        if not n:
            continue
        if (n["sender"], n["receiver"], float(n["amount"])) == exp:
            ok += 1

    # malformed should be rejected
    bad = ["{", "<tx>", "insert into t values(", ""]
    rej_ok = sum(1 for b in bad if normalize_one(b) is None)

    return {
        "field_accuracy": _acc(ok, total),
        "reject_accuracy": _acc(rej_ok, len(bad)),
    }


def phase1_accuracy() -> dict:
    ledger = RollingDagLedger(max_nodes=1000)

    ok_accept = 0
    total_accept = 0
    prev = tx_key("GENESIS")
    for i in range(2000):
        tid = tx_key(f"tx{i}")
        total_accept += 1
        a_ok, _ = ledger.add(tid, [prev])
        ok_accept += 1 if a_ok else 0
        prev = tid

    # missing parent must reject
    missing_parent = tx_key("never_seen")
    b_ok, missing = ledger.add(tx_key("bad"), [missing_parent])
    reject_ok = (not b_ok) and (missing_parent in missing)

    return {
        "accept_accuracy": _acc(ok_accept, total_accept),
        "missing_parent_reject": 1.0 if reject_ok else 0.0,
        "window_size": ledger.max_nodes,
    }


def phase3_accuracy() -> dict:
    # Consistency: same tx_id always routes to same shard if loads not recorded.
    ids = [f"tx{i}" for i in range(1000)]
    a = [shard_manager.get_shard_for_transaction(x) for x in ids]
    b = [shard_manager.get_shard_for_transaction(x) for x in ids]
    consistent = sum(1 for i in range(len(ids)) if a[i] == b[i])

    # Load-aware: if we record high load for the default shard, routing should change sometimes.
    flips = 0
    for x in ids[:200]:
        s0 = shard_manager.get_shard_for_transaction(x)
        shard_manager.record_shard_load(s0, latency_ms=10_000.0, items=1)
        s1 = shard_manager.get_shard_for_transaction_load_aware(x, probe=8)
        flips += 1 if s1 != s0 else 0

    return {
        "consistency_accuracy": _acc(consistent, len(ids)),
        "load_aware_flip_rate": _acc(flips, 200),
    }


def phase4_accuracy() -> dict:
    # Accept valid proofs, reject tampered proofs.
    total = 0
    ok = 0

    vec = [1.0] * 64
    for i in range(200):
        txid = f"tx{i}"
        p = poi.make_proof(txid, vec, "v")
        total += 1
        ok += 1 if poi.verify(p)[0] else 0

        # tamper
        total += 1
        bad = type(p)(validator_id=p.validator_id, tx_id=p.tx_id, score=p.score + 1.0, proof=p.proof)
        ok += 1 if (not poi.verify(bad)[0]) else 0

    return {"accuracy": _acc(ok, total)}


def phase5_accuracy() -> dict:
    # Simple labeled set
    safe = [
        "def f(x):\n    return x+1\n",
        "x = 1\ny = x * 2\n",
    ]
    bad = [
        "import os\n",
        "eval('1+1')\n",
        "__builtins__\n",
    ]

    tp = fp = tn = fn = 0

    for s in safe:
        _, issues = auditor.auto_patch(s)
        blocked = bool(issues)
        if blocked:
            fp += 1
        else:
            tn += 1

    for s in bad:
        _, issues = auditor.auto_patch(s)
        blocked = bool(issues)
        if blocked:
            tp += 1
        else:
            fn += 1

    return {
        "accuracy": _acc(tp + tn, tp + tn + fp + fn),
        "f1": _f1(tp, fp, fn),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "tn": tn,
    }


def phase6_accuracy() -> dict:
    # Synthetic labeled stream.
    # normal: stable amounts; fraud: spikes or high-rate bursts.
    samples = []

    t = time.time()
    sender = "alice"

    # warmup normal
    for i in range(200):
        t += 0.2
        samples.append((sender, 100.0 + random.random() * 10.0, t, 0))

    # fraud spikes
    for i in range(50):
        t += 0.2
        samples.append((sender, 10000.0, t, 1))

    # fraud high-rate burst (same timestamp increments tiny)
    for i in range(50):
        t += 0.001
        samples.append((sender, 120.0, t, 1))

    # score
    scores = []
    labels = []
    for s, amt, ts, y in samples:
        r, _ = fraud_detector.score(s, amt, ts)
        scores.append(r)
        labels.append(y)

    # pick threshold maximizing F1
    best = {"thr": 0.5, "f1": -1.0, "tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for thr in [i / 100 for i in range(5, 96, 5)]:
        tp = fp = tn = fn = 0
        for r, y in zip(scores, labels):
            pred = 1 if r >= thr else 0
            if pred == 1 and y == 1:
                tp += 1
            elif pred == 1 and y == 0:
                fp += 1
            elif pred == 0 and y == 1:
                fn += 1
            else:
                tn += 1
        f1 = _f1(tp, fp, fn)
        if f1 > best["f1"]:
            best = {"thr": thr, "f1": f1, "tp": tp, "fp": fp, "fn": fn, "tn": tn}

    acc = _acc(best["tp"] + best["tn"], best["tp"] + best["tn"] + best["fp"] + best["fn"])
    return {"best_threshold": best["thr"], "accuracy": acc, "f1": best["f1"], **best}


def phase7_accuracy() -> dict:
    if not he.available():
        return {"skipped": True}
    he.keygen(n_length=1024)
    a = 12
    b = 7
    ea = he.encrypt(a)
    eb = he.encrypt(b)
    s = he.add(ea, eb)
    out = he.decrypt(s)
    return {"skipped": False, "correct": 1.0 if out == (a + b) else 0.0}


def phase8_accuracy() -> dict:
    want = {
        "/ingest",
        "/validate",
        "/phase1/dag/submit",
        "/phase1/dag/tips",
        "/phase2/ingest",
        "/phase3/shard/route",
        "/phase4/poi/prove",
        "/phase4/poi/verify",
        "/phase5/contracts/audit",
        "/phase6/fraud/score",
        "/phase7/he/keygen",
        "/phase7/he/encrypt",
        "/phase7/he/decrypt",
        "/phase7/he/add",
    }

    have = set(getattr(r, "path", "") for r in getattr(router, "routes", []))
    ok = sum(1 for p in want if p in have)
    return {"route_existence_accuracy": _acc(ok, len(want)), "total": len(want)}


def main() -> None:
    report = {
        "phase1": phase1_accuracy(),
        "phase2": phase2_accuracy(),
        "phase3": phase3_accuracy(),
        "phase4": phase4_accuracy(),
        "phase5": phase5_accuracy(),
        "phase6": phase6_accuracy(),
        "phase7": phase7_accuracy(),
        "phase8": phase8_accuracy(),
        "notes": {
            "fraud_contract_accuracy": "synthetic labeled data; real accuracy needs real labels",
            "dag_accuracy": "bounded-memory ledger; bloom filter used for parent existence checks",
        },
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
