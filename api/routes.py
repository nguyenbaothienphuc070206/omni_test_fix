from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import time

from ledger.dag_ledger import dag_ledger, tx_key
from preprocessing.polymorphic import ingest_and_vectorize
from services.sharding import shard_manager
from consensus.poi import poi, PoIProof
from contracts.self_healing import auditor
from fraud.detector import fraud_detector
from crypto.homomorphic import he

# Import Cython Modules
from preprocessing.ingestor import parse_and_normalize_batch
from data_models import Transaction
from math_core import validate_dag_batch

router = APIRouter()

class IngestionRequest(BaseModel):
    batch_id: str
    payloads: List[str]  # Raw JSON strings strings to simulate polymorphic input


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


class PoIRequest(BaseModel):
    tx_id: str
    validator_id: str
    vector: List[float]


class PoIVerifyRequest(BaseModel):
    validator_id: str
    tx_id: str
    score: float
    proof: str


class ContractRequest(BaseModel):
    source: str


class FraudRequest(BaseModel):
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
    """
    High-Performance Ingestion Endpoint.
    Passes raw data to Cython 'ingestor' for O(n) parsing.
    """
    start = time.perf_counter()
    
    # call Cython logic
    normalized_data = parse_and_normalize_batch(request.payloads)
    
    # In a real scenario, we'd pipe this to the DAG Validator immediately
    # For now, we return the parsed count and speed
    
    elapsed = time.perf_counter() - start
    tps = len(request.payloads) / elapsed if elapsed > 0 else 0
    
    return {
        "batch_id": request.batch_id,
        "processed_count": len(normalized_data),
        "tps_ingest": round(tps, 2),
        "preview": normalized_data[:1] if normalized_data else []
    }


@router.post("/phase1/dag/submit")
async def phase1_dag_submit(txs: List[DagSubmitTx]):
    items = [(tx_key(t.id), [tx_key(p) for p in (t.parents or [])]) for t in txs]
    return dag_ledger.add_batch(items)


@router.get("/phase1/dag/tips")
async def phase1_dag_tips():
    return {"tips": dag_ledger.tips()}


@router.post("/phase2/ingest")
async def phase2_polymorphic_ingest(request: PolyIngestRequest):
    start = time.perf_counter()
    out = ingest_and_vectorize(request.payloads, dim=int(request.dim))
    elapsed = time.perf_counter() - start
    tps = len(request.payloads) / elapsed if elapsed > 0 else 0
    return {"processed": len(out), "tps": round(tps, 2), "preview": out[:1] if out else []}


@router.post("/phase3/shard/route")
async def phase3_shard_route(request: ShardRouteRequest):
    shard = shard_manager.get_shard_for_transaction_load_aware(request.tx_id)
    if request.latency_ms is not None:
        shard_manager.record_shard_load(shard, float(request.latency_ms), int(request.items))
    return {"shard": shard}


@router.post("/phase4/poi/prove")
async def phase4_poi_prove(request: PoIRequest):
    p = poi.make_proof(request.tx_id, request.vector, request.validator_id)
    ok, reason = poi.verify(p)
    return {"ok": ok, "reason": reason, "score": p.score, "proof": p.proof}


@router.post("/phase4/poi/verify")
async def phase4_poi_verify(request: PoIVerifyRequest):
    p = PoIProof(
        validator_id=request.validator_id,
        tx_id=request.tx_id,
        score=float(request.score),
        proof=request.proof,
    )
    ok, reason = poi.verify(p)
    return {"ok": ok, "reason": reason}


@router.post("/phase5/contracts/audit")
async def phase5_contract_audit(request: ContractRequest):
    patched, issues = auditor.auto_patch(request.source)
    return {
        "issues": [{"kind": i.kind, "detail": i.detail, "line": i.line} for i in issues],
        "patched": patched,
        "blocked": bool(issues),
    }


@router.post("/phase6/fraud/score")
async def phase6_fraud_score(request: FraudRequest):
    risk, meta = fraud_detector.score(request.sender, float(request.amount))
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
    """
    DAG Validation Endpoint.
    """
    start = time.perf_counter()
    
    # Convert Dicts -> Cython Transaction Objects
    cython_txs = []
    for tx_data in transactions:
        tx = Transaction(
            sender=tx_data.get("sender", "unknown"),
            receiver=tx_data.get("receiver", "unknown"),
            amount=float(tx_data.get("amount", 0.0)),
            parent_hashes=tx_data.get("parents", [])
        )
        cython_txs.append(tx)
        
    # High-Performance Parallel Validation
    is_valid = validate_dag_batch(cython_txs)
    
    elapsed = time.perf_counter() - start
    tps = len(transactions) / elapsed if elapsed > 0 else 0
    
    return {
        "valid": is_valid,
        "count": len(cython_txs),
        "tps_validation": round(tps, 2)
    }