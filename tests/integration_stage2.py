import sys
import os
from fastapi.testclient import TestClient
import json
import time

# Ensure we can import main
sys.path.append(os.path.dirname(os.path.abspath(os.path.join(__file__, '..'))))

from main import app

client = TestClient(app)

def test_integration_flow():
    print("🚀 Starting Stage 2 Integration Test...")
    
    # 1. Health Check
    print("[1] Testing Health Endpoint...")
    response = client.get("/health")
    assert response.status_code == 200
    print(f"    Health: {response.json()}")
    
    # 2. Ingestion (Triggering Cython)
    print("[2] Testing High-Speed Ingestion...")
    payloads = [json.dumps({"sender": f"user_{i}", "amount": i}) for i in range(100)]
    response = client.post("/api/v1/ingest", json={"batch_id": "test_batch_1", "payloads": payloads})
    assert response.status_code == 200
    data = response.json()
    print(f"    Ingested: {data['processed_count']} items")
    print(f"    TPS (Ingest): {data['tps_ingest']}")
    
    # 3. Validation (Triggering DAG + SHA256)
    print("[3] Testing DAG Validation...")
    # Simulate the output of ingestion being passed to validation
    tx_batch = [{"sender": "user_A", "receiver": "user_B", "amount": 100.0, "parents": []}]
    response = client.post("/api/v1/validate", json=tx_batch)
    assert response.status_code == 200
    v_data = response.json()
    print(f"    Validation Result: {v_data['valid']}")
    print(f"    TPS (Validate): {v_data['tps_validation']}")
    
    print("✅ Stage 2 Integration Test PASSED")

if __name__ == "__main__":
    test_integration_flow()
