from __future__ import annotations

import hashlib
import hmac
import os
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class PasswordHash:
    algo: str
    salt: str
    iterations: int
    digest: str

    def encode(self) -> str:
        return f"{self.algo}${self.iterations}${self.salt}${self.digest}"


def hash_password(password: str, *, iterations: int = 210_000) -> str:
    salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    ph = PasswordHash(
        algo="pbkdf2_sha256",
        salt=salt.hex(),
        iterations=iterations,
        digest=dk.hex(),
    )
    return ph.encode()


def verify_password(password: str, encoded: str) -> bool:
    try:
        algo, it_s, salt_hex, digest_hex = encoded.split("$", 3)
        if algo != "pbkdf2_sha256":
            return False
        iterations = int(it_s)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except Exception:
        return False

    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(dk, expected)
