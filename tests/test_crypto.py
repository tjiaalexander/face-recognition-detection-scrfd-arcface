import numpy as np
import pytest

from app.services.crypto import CryptoError, EmbeddingCipher


def test_roundtrip_and_ciphertext_differs():
    c = EmbeddingCipher(EmbeddingCipher.generate_key())
    v = np.random.default_rng(0).normal(size=512).astype(np.float32)
    blob = c.encrypt(v)
    assert v.tobytes() not in blob
    assert np.array_equal(c.decrypt(blob, 512), v)


def test_wrong_key_and_wrong_dim_fail():
    a, b = EmbeddingCipher(EmbeddingCipher.generate_key()), EmbeddingCipher(EmbeddingCipher.generate_key())
    blob = a.encrypt(np.ones(8, np.float32))
    with pytest.raises(CryptoError):
        b.decrypt(blob, 8)
    with pytest.raises(CryptoError):
        a.decrypt(blob, 9)


def test_invalid_key_message():
    with pytest.raises(CryptoError):
        EmbeddingCipher("bukan-kunci")
