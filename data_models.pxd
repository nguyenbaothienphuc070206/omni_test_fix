# data_models.pxd

cdef class Transaction:
    cdef public str id
    cdef public double amount
    cdef public str sender
    cdef public str receiver
    cdef public list parent_hashes
    cdef public str hash
    cdef public double timestamp
    cdef public bint is_validated
    cpdef str _calculate_hash(self)
    cpdef bint verify_integrity(self)

cdef class Ledger:
    cdef int id
    cdef double balance
    cdef double createdAt
    cdef double updatedAt
    cdef bint isDeleted
    cdef double deletedAt
    cpdef void delete(self)
    cpdef double get_balance(self)
