from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time

from chronicle.graph_store import chronicle_store, tx_fingerprint
from intake.codec import parse_and_vectorize
from fabric.routing import shard_manager
from quorum.proofs import intel_engine, IntelProof
from covenant.autopatch import covenant_auditor
from sentinel.risk import sentinel_scorer
from cipherworks.paillier import he

# Import Cython Modules
from intake.decoder import decode_json_batch
from aegis_types import Transaction
from aegis_math import validate_dag_batch

router = APIRouter()


class IngestionRequest(BaseModel):
    batch_id: str
    payloads: List[str]  # Raw JSON strings to simulate polymorphic input


class DagSubmitTx(BaseModel):
    id: str
    parents: List[str] = []


class PolyIngestRequest(BaseModel):
    payloads: List[str]
    dim: int = 64


class ShardRouteRequest(BaseModel):
    tx_id: str
    latency_ms: Optional[float] = None
    items: int = 1


class IntelRequest(BaseModel):
    tx_id: str
    validator_id: str
    vector: List[float]


class IntelVerifyRequest(BaseModel):
    validator_id: str
    tx_id: str
    score: float
    proof: str


class ContractRequest(BaseModel):
    source: str


class SentinelRequest(BaseModel):
    sender: str
    amount: float


class HEKeygenRequest(BaseModel):
    n_length: int = 2048


class HEEncryptRequest(BaseModel):
    value: int


class HEDecryptRequest(BaseModel):
    blob: str


class HEAddRequest(BaseModel):
    a: str
    b: str


@router.post("/ingest")
async def ingest_data(request: IngestionRequest):
    """High-Performance Ingestion Endpoint."""
    start = time.perf_counter()
    normalized_data = decode_json_batch(request.payloads)
    elapsed = time.perf_counter() - start
    tps = len(request.payloads) / elapsed if elapsed > 0 else 0
    return {
        "batch_id": request.batch_id,
        "processed_count": len(normalized_data),
        "tps_ingest": round(tps, 2),
        "preview": normalized_data[:1] if normalized_data else [],
    }


@router.post("/phase1/dag/submit")
async def phase1_dag_submit(txs: List[DagSubmitTx]):
    items = [(tx_fingerprint(t.id), [tx_fingerprint(p) for p in (t.parents or [])]) for t in txs]
    return chronicle_store.add_batch(items)


@router.get("/phase1/dag/tips")
async def phase1_dag_tips():
    return {"tips": chronicle_store.tips()}


@router.post("/phase2/ingest")
async def phase2_polymorphic_ingest(request: PolyIngestRequest):
    start = time.perf_counter()
    out = parse_and_vectorize(request.payloads, dim=int(request.dim))
    elapsed = time.perf_counter() - start
    tps = len(request.payloads) / elapsed if elapsed > 0 else 0
    return {"processed": len(out), "tps": round(tps, 2), "preview": out[:1] if out else []}


@router.post("/phase3/shard/route")
async def phase3_shard_route(request: ShardRouteRequest):
    shard = shard_manager.get_shard_for_transaction_load_aware(request.tx_id)
    if request.latency_ms is not None:
        shard_manager.record_shard_load(shard, float(request.latency_ms), int(request.items))
    return {"shard": shard}


@router.post("/phase4/intel/prove")
async def phase4_intel_prove(request: IntelRequest):
    p = intel_engine.make_proof(request.tx_id, request.vector, request.validator_id)
    ok, reason = intel_engine.verify(p)
    return {"ok": ok, "reason": reason, "score": p.score, "proof": p.proof}


@router.post("/phase4/intel/verify")
async def phase4_intel_verify(request: IntelVerifyRequest):
    p = IntelProof(
        validator_id=request.validator_id,
        tx_id=request.tx_id,
        score=float(request.score),
        proof=request.proof,
    )
    ok, reason = intel_engine.verify(p)
    return {"ok": ok, "reason": reason}


@router.post("/phase5/covenant/audit")
async def phase5_contract_audit(request: ContractRequest):
    patched, issues = covenant_auditor.auto_patch(request.source)
    return {
        "issues": [{"kind": i.kind, "detail": i.detail, "line": i.line} for i in issues],
        "patched": patched,
        "blocked": bool(issues),
    }


@router.post("/phase6/sentinel/score")
async def phase6_sentinel_score(request: SentinelRequest):
    risk, meta = sentinel_scorer.score(request.sender, float(request.amount))
    return {"risk": risk, "meta": meta}


@router.post("/phase7/he/keygen")
async def phase7_he_keygen(request: HEKeygenRequest):
    if not he.available():
        raise HTTPException(status_code=400, detail="phe_not_installed")
    he.keygen(n_length=int(request.n_length))
    return {"ok": True}


@router.post("/phase7/he/encrypt")
async def phase7_he_encrypt(request: HEEncryptRequest):
    if not he.available():
        raise HTTPException(status_code=400, detail="phe_not_installed")
    try:
        blob = he.encrypt(int(request.value))
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"cipher": blob}


@router.post("/phase7/he/decrypt")
async def phase7_he_decrypt(request: HEDecryptRequest):
    if not he.available():
        raise HTTPException(status_code=400, detail="phe_not_installed")
    try:
        val = he.decrypt(request.blob)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"value": val}


@router.post("/phase7/he/add")
async def phase7_he_add(request: HEAddRequest):
    if not he.available():
        raise HTTPException(status_code=400, detail="phe_not_installed")
    try:
        blob = he.add(request.a, request.b)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"cipher": blob}


@router.post("/validate")
async def validate_batch(transactions: List[Dict[str, Any]]):
    """DAG Validation Endpoint."""
    start = time.perf_counter()

    cython_txs = []
    for tx_data in transactions:
        tx = Transaction(
            sender=tx_data.get("sender", "unknown"),
            receiver=tx_data.get("receiver", "unknown"),
            amount=float(tx_data.get("amount", 0.0)),
            parent_hashes=tx_data.get("parents", []),
        )
        cython_txs.append(tx)

    is_valid = validate_dag_batch(cython_txs)

    elapsed = time.perf_counter() - start
    tps = len(transactions) / elapsed if elapsed > 0 else 0

    return {"valid": is_valid, "count": len(cython_txs), "tps_validation": round(tps, 2)}
