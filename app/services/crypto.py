"""Enkripsi embedding saat disimpan (Fernet: AES-128-CBC + HMAC)."""
from __future__ import annotations

import numpy as np
from cryptography.fernet import Fernet, InvalidToken


class CryptoError(RuntimeError):
    pass


class EmbeddingCipher:
    def __init__(self, key: str):
        try:
            self._fernet = Fernet(key.encode("ascii"))
        except (ValueError, TypeError) as exc:
            raise CryptoError("EMBEDDING_KEY tidak valid (harus kunci Fernet base64 32-byte).") from exc

    @staticmethod
    def generate_key() -> str:
        return Fernet.generate_key().decode("ascii")

    def encrypt(self, vector: np.ndarray) -> bytes:
        return self._fernet.encrypt(np.asarray(vector, dtype=np.float32).tobytes())

    def decrypt(self, blob: bytes, dim: int) -> np.ndarray:
        try:
            raw = self._fernet.decrypt(bytes(blob))
        except InvalidToken as exc:
            raise CryptoError("Template tidak dapat didekripsi (kunci salah atau data rusak).") from exc
        arr = np.frombuffer(raw, dtype=np.float32)
        if arr.size != dim:
            raise CryptoError(f"Dimensi embedding {arr.size} tidak sesuai dengan {dim}.")
        return arr.copy()
