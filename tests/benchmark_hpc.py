import time
import random
import json
import asyncio
import sys
import os

# Ensure root directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from intake.decoder import parse_and_normalize_batch
from aegis_types import Transaction
from aegis_math import validate_dag_batch

def generate_dummy_data(n=1000):
    data = []
    for i in range(n):
        payload = json.dumps({
            "sender": f"user_{random.randint(1, 1000)}",
            "receiver": f"user_{random.randint(1, 1000)}",
            "amount": random.random() * 1000,
            "nonce": i
        })
        data.append(payload)
    return data

def run_benchmark():
    BATCH_SIZE = 10000
    print(f"Generating {BATCH_SIZE} mock payloads...")
    raw_data = generate_dummy_data(BATCH_SIZE)
    
    print("Starting Ingestion Phase (JSON Parse + Normalization)...")
    start_ingest = time.perf_counter()
    normalized_data = parse_and_normalize_batch(raw_data)
    end_ingest = time.perf_counter()
    
    print("Starting Conversion to Cython Objects...")
    start_convert = time.perf_counter()
    transactions = []
    parent_hashes = [] # Genesis block simulation
    for item in normalized_data:
        tx = Transaction(
            sender=item['sender'],
            receiver=item['receiver'],
            amount=item['amount'],
            parent_hashes=parent_hashes
        )
        transactions.append(tx)
        # Simple chain for demo (each points to previous)
        parent_hashes = [tx.hash]
    end_convert = time.perf_counter()
    
    print("Starting DAG Validation Phase (SHA-256 integrity)...")
    start_validate = time.perf_counter()
    is_valid = validate_dag_batch(transactions)
    end_validate = time.perf_counter()
    
    ingest_time = end_ingest - start_ingest
    validate_time = end_validate - start_validate
    total_time = ingest_time + validate_time
    
    print("-" * 40)
    print(f"BENCHMARK RESULTS (Batch: {BATCH_SIZE})")
    print("-" * 40)
    print(f"Ingestion TPS: {BATCH_SIZE / ingest_time:,.2f}")
    print(f"Validation TPS: {BATCH_SIZE / validate_time:,.2f}")
    print(f"Total TPS:     {BATCH_SIZE / total_time:,.2f}")
    print(f"DAG Valid:     {is_valid}")
    print("-" * 40)

if __name__ == "__main__":
    run_benchmark()
