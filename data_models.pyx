import numpy as np
cimport numpy as cnp
from cython.parallel import prange

cdef class Ledger:
    # Fields defined in .pxd

    def __init__(self, int id, double balance):
        self.id = id
        self.balance = balance
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

    cpdef double get_balance(self):
        return self.balance

import hashlib
import time

import hashlib
import time

cdef class Transaction:
    # Fields are defined in .pxd
    
    def __init__(self, str sender, str receiver, double amount, list parent_hashes):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.parent_hashes = parent_hashes
        self.timestamp = time.time()
        self.is_validated = False
        self.hash = self._calculate_hash()
        self.id = self.hash  # ID is the hash in this system

    cpdef str _calculate_hash(self):
        # High-performance SHA-256 generation
        # In a real C-optimized version, we would use OpenSSL directly
        cdef str payload = f"{self.sender}|{self.receiver}|{self.amount}|{self.timestamp}|{''.join(self.parent_hashes)}"
        return hashlib.sha256(payload.encode('utf-8')).hexdigest()

    cpdef bint verify_integrity(self):
        # Re-calculates hash to ensure no tampering
        return self._calculate_hash() == self.hash
    
    def to_dict(self):
        return {
            "id": self.id,
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "parents": self.parent_hashes,
            "timestamp": self.timestamp,
            "hash": self.hash
        }

    def __repr__(self):
        return f"<Transaction {self.id[:8]}... Amount={self.amount}>"


cdef class DataIngestion:
    cdef int id
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id):
        self.id = id
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef class Shard:
    cdef int id
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id):
        self.id = id
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef class ConsensusMechanism:
    cdef int id
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id):
        self.id = id
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef class SmartContract:
    cdef int id
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id):
        self.id = id
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef class FraudDetection:
    cdef int id
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id):
        self.id = id
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef class EncryptionProtocol:
    cdef int id
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id):
        self.id = id
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef class ApiGateway:
    cdef int id
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id):
        self.id = id
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef class User:
    cdef int id
    cdef str email
    cdef str hashed_password
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id, str email, str password):
        self.id = id
        self.email = email
        self.hashed_password = hash_password(password)
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef class Node:
    cdef int id
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id):
        self.id = id
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef class AuditLog:
    cdef int id
    cdef str action
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt

    def __init__(self, int id, str action):
        self.id = id
        self.action = action
        self.createdAt = current_time()
        self.updatedAt = current_time()
        self.isDeleted = False
        self.deletedAt = -1.0

    cpdef void delete(self):
        self.isDeleted = True
        self.deletedAt = current_time()

cdef double current_time():
    # Placeholder for actual timestamp retrieval
    return 0.0

cdef str hash_password(str password):
    # Placeholder for password hashing logic
    return password