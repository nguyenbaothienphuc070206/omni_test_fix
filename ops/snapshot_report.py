import json
import math
import os
from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Dict, Tuple


TX_TARGET_DEFAULT = 123_456_789


@dataclass(frozen=True)
class Stage:
    name: str
    seconds: float
    ops: int

    @property
    def sec_per_op(self) -> float:
        if self.ops <= 0:
            return float("nan")
        return self.seconds / self.ops


def _read_json(path: str) -> Dict[str, Any]:
    # Windows redirection can sometimes produce UTF-8 with BOM.
    with open(path, "r", encoding="utf-8-sig") as f:
        return json.load(f)


def _format_duration(seconds: float) -> str:
    if not math.isfinite(seconds) or seconds < 0:
        return "n/a"
    return str(timedelta(seconds=int(round(seconds))))


def _load_stages(bench: Dict[str, Any]) -> Tuple[Stage, ...]:
    n = int(bench.get("N") or 0)
    sec = bench.get("sec") or {}

    # Stages measured on N transactions
    stages = [
        Stage("phase2_ingest", float(sec["phase2_ingest"]), n),
        Stage("build_tx", float(sec["build_tx"]), n),
        Stage("phase1_validate", float(sec["phase1_validate"]), n),
        Stage("phase1_dag_store", float(sec["phase1_dag_store"]), n),
        Stage("phase3_route", float(sec["phase3_route"]), n),
        Stage("phase6_sentinel", float(sec["phase6_sentinel"]), n),
    ]

    # Intel measured on intel_M proofs (not N)
    intel_m = int(bench.get("intel_M") or 0)
    if "phase4_intel" in sec and intel_m > 0:
        stages.append(Stage("phase4_intel", float(sec["phase4_intel"]), intel_m))

    return tuple(stages)


def build_snapshot(
    bench: Dict[str, Any],
    accuracy: Dict[str, Any],
    tx_target: int,
) -> Dict[str, Any]:
    stages = _load_stages(bench)

    total_sec_per_tx = 0.0
    stage_rows = []
    for s in stages:
        sp = s.sec_per_op
        total_sec_per_tx += sp
        stage_rows.append(
            {
                "stage": s.name,
                "seconds": s.seconds,
                "ops": s.ops,
                "sec_per_op": sp,
            }
        )

    est_total_seconds = tx_target * total_sec_per_tx
    est_tps_sequential = 1.0 / total_sec_per_tx if total_sec_per_tx > 0 else 0.0

    for r in stage_rows:
        share = (r["sec_per_op"] / total_sec_per_tx) if total_sec_per_tx > 0 else 0.0
        r["time_share"] = share

    # Convenience: pull through raw per-stage TPS if present
    tps = bench.get("tps") or {}

    # Non-per-tx benchmarks (reported but not included in sequential tx estimate)
    non_tx_bench = {
        "phase5_audit_cached_2k": (bench.get("sec") or {}).get("phase5_audit_cached_2k"),
        "phase5_audit_uncached_500": (bench.get("sec") or {}).get("phase5_audit_uncached_500"),
        "phase7_he_50": (bench.get("sec") or {}).get("phase7_he_50"),
    }

    return {
        "inputs": {
            "tx_target": tx_target,
            "bench_N": bench.get("N"),
            "intel_M": bench.get("intel_M"),
        },
        "accuracy": accuracy,
        "bench": {
            "sec": bench.get("sec"),
            "tps": tps,
            "non_tx_bench_sec": non_tx_bench,
        },
        "estimate": {
            "sequential_sec_per_tx": total_sec_per_tx,
            "sequential_tps": est_tps_sequential,
            "estimated_total_seconds": est_total_seconds,
            "estimated_total_hms": _format_duration(est_total_seconds),
            "stage_breakdown": stage_rows,
        },
        "notes": {
            "sequential_model": (
                "Estimate assumes phases run sequentially in a single worker. "
                "If you parallelize across workers/cores, wall-clock time can drop roughly with concurrency until another bottleneck dominates."
            ),
            "phase4_intel": "Measured on intel_M proofs; per-tx cost uses sec/intel_M.",
            "phase5_phase7": "Phase 5 and Phase 7 are benchmarked separately and are not included in the per-tx sequential estimate by default.",
            "sentinel_metrics": "Sentinel (phase6) accuracy/F1 are on synthetic labeled data; real accuracy requires real labels.",
        },
    }


def main() -> None:
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    reports_dir = os.path.join(repo_root, "reports")

    bench_path = os.path.join(reports_dir, "bench_latest.json")
    acc_path = os.path.join(reports_dir, "accuracy_latest.json")
    out_path = os.path.join(reports_dir, "snapshot_latest.json")

    tx_target = int(os.environ.get("AEGIS_TX_TARGET", str(TX_TARGET_DEFAULT)))

    bench = _read_json(bench_path)
    accuracy = _read_json(acc_path)

    snapshot = build_snapshot(bench, accuracy, tx_target)

    os.makedirs(reports_dir, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2, sort_keys=True)
        f.write("\n")

    print(out_path)


if __name__ == "__main__":
    main()
