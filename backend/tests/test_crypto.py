import os

from app.crypto import decrypt, encrypt


def test_roundtrip_unicode():
    for plain in ["", "simple", "s3cret-Ä-密码-🔑", "x" * 2000]:
        assert decrypt(encrypt(plain)) == plain


def test_ciphertexts_are_unique():
    ct1 = encrypt("same")
    ct2 = encrypt("same")
    assert ct1 != ct2
    assert decrypt(ct1) == decrypt(ct2) == "same"


def test_ciphertext_is_versioned():
    ct = encrypt("hello")
    assert ct.startswith("v1:")


def test_plaintext_never_leaks():
    ct = encrypt("topsecretvalue")
    assert "topsecretvalue" not in ct


def test_corrupt_ciphertext_raises():
    ct = encrypt("value")
    parts = ct.split(":")
    parts[2] = parts[2][:-2] + "AA"
    import pytest
    with pytest.raises(Exception):
        decrypt(":".join(parts))


def test_key_is_32_bytes():
    from app.crypto import _get_key
    assert len(_get_key()) == 32