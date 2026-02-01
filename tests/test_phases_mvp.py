import json

from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_phase1_dag_submit_and_tips():
    r = client.post("/api/v1/phase1/dag/submit", json=[{"id": "A", "parents": []}])
    assert r.status_code == 200
    tips = client.get("/api/v1/phase1/dag/tips").json()["tips"]
    assert isinstance(tips, list)
    assert all(isinstance(x, int) for x in tips)


def test_phase2_polymorphic_ingest_json_and_text():
    payloads = [
        json.dumps({"sender": "alice", "receiver": "bob", "amount": 12.5}),
        "carol->dave:3",
    ]
    r = client.post("/api/v1/phase2/ingest", json={"payloads": payloads, "dim": 32})
    assert r.status_code == 200
    data = r.json()
    assert data["processed"] == 2
    assert isinstance(data["preview"], list)


def test_phase3_shard_route():
    r = client.post("/api/v1/phase3/shard/route", json={"tx_id": "tx123"})
    assert r.status_code == 200
    assert r.json()["shard"].startswith("shard_")


def test_phase4_poi_roundtrip():
    vec = [1.0] * 64
    p = client.post(
        "/api/v1/phase4/poi/prove",
        json={"tx_id": "tx1", "validator_id": "v1", "vector": vec},
    ).json()
    assert "proof" in p

    r = client.post(
        "/api/v1/phase4/poi/verify",
        json={"validator_id": "v1", "tx_id": "tx1", "score": p["score"], "proof": p["proof"]},
    )
    assert r.status_code == 200


def test_phase5_contract_audit_blocks_import():
    r = client.post("/api/v1/phase5/contracts/audit", json={"source": "import os\nprint(1)\n"})
    assert r.status_code == 200
    data = r.json()
    assert data["blocked"] is True
    assert len(data["issues"]) >= 1


def test_phase6_fraud_score():
    r = client.post("/api/v1/phase6/fraud/score", json={"sender": "alice", "amount": 100.0})
    assert r.status_code == 200
    data = r.json()
    assert 0.0 <= data["risk"] <= 1.0
