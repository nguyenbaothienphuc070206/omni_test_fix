"""Phase 7: Homomorphic encryption (MVP).

Additive homomorphic encryption via Paillier if `phe` is installed.
If not installed, endpoints should return a clear error.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional, Tuple


@dataclass(slots=True)
class HEKeys:
    public: Any
    private: Any


class PaillierHE:
    def __init__(self) -> None:
        self._keys: Optional[HEKeys] = None

    def available(self) -> bool:
        try:
            import phe  # noqa: F401
            return True
        except Exception:
            return False

    def keygen(self, n_length: int = 2048) -> None:
        from phe import paillier

        pub, priv = paillier.generate_paillier_keypair(n_length=n_length)
        self._keys = HEKeys(public=pub, private=priv)

    def encrypt(self, value: int) -> str:
        if not self._keys:
            raise RuntimeError("no_keys")
        c = self._keys.public.encrypt(int(value))
        # serialize minimal
        return f"{c.ciphertext()}|{c.exponent}"

    def decrypt(self, blob: str) -> int:
        if not self._keys:
            raise RuntimeError("no_keys")
        from phe.paillier import EncryptedNumber

        ct_s, exp_s = blob.split("|", 1)
        enc = EncryptedNumber(self._keys.public, int(ct_s), int(exp_s))
        return int(self._keys.private.decrypt(enc))

    def add(self, a_blob: str, b_blob: str) -> str:
        if not self._keys:
            raise RuntimeError("no_keys")
        from phe.paillier import EncryptedNumber

        a_ct, a_exp = a_blob.split("|", 1)
        b_ct, b_exp = b_blob.split("|", 1)
        a = EncryptedNumber(self._keys.public, int(a_ct), int(a_exp))
        b = EncryptedNumber(self._keys.public, int(b_ct), int(b_exp))
        c = a + b
        return f"{c.ciphertext()}|{c.exponent}"


he = PaillierHE()
