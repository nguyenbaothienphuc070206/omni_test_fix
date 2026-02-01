# cython: language_level=3
import json
import time

# We want to ingest large batches of polymorphic data (JSON/XML/SQL)
# Phase 2: Polymorphic Data Ingestion Engine

def parse_and_normalize_batch(list raw_data_batch):
    """
    Takes a list of raw string payloads (simulating heterogeneous sources).
    Normalizes them into a standard dictionary format for the Transaction engine.
    """
    cdef int n = len(raw_data_batch)
    cdef int i
    cdef list normalized_results = []
    cdef str payload
    cdef dict parsed
    cdef dict normalized
    
    # Pre-allocate if possible (Python lists don't support pre-alloc nicely in Cython without C-API)
    # But loop unrolling/typing helps.
    
    for i in range(n):
        payload = raw_data_batch[i]
        try:
            # Polymorphic handling: Try JSON first
            if payload.strip().startswith("{"):
                parsed = json.loads(payload)
                
                # Normalization Logic (Vectorization prep)
                # Map various fields to standard 'sender', 'receiver', 'amount'
                normalized = {
                    "sender": parsed.get("sender") or parsed.get("from") or "unknown",
                    "receiver": parsed.get("receiver") or parsed.get("to") or "burn_address",
                    "amount": float(parsed.get("amount") or parsed.get("value") or 0.0),
                    "meta": parsed  # Keep original data
                }
                normalized_results.append(normalized)
        except Exception:
            # Skip malformed data
            continue
            
    return normalized_results
