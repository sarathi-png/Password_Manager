"""AES-256-GCM encryption for vault secrets.

Every sensitive field (username, password, notes) is encrypted individually
with a fresh random nonce. The master key lives in the environment (or a
local key file in development) and is never stored in the database.

Ciphertext format:  v1:<nonce_b64>:<tag_b64>:<ciphertext_b64>
"""

import base64
import os
import secrets
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import get_settings

settings = get_settings()

_KEY = None


def _load_or_create_master_key() -> bytes:
    env_key = settings.vault_master_key
    if env_key:
        try:
            return base64.b64decode(env_key)
        except Exception:
            raise RuntimeError("VAULT_MASTER_KEY must be base64-encoded 32 bytes")

    key_file = Path(settings.master_key_file)
    if key_file.exists():
        return key_file.read_bytes()

    key = secrets.token_bytes(32)
    key_file.parent.mkdir(parents=True, exist_ok=True)
    key_file.write_bytes(key)
    key_file.chmod(0o600)
    return key


def _get_key() -> bytes:
    global _KEY
    if _KEY is None:
        _KEY = _load_or_create_master_key()
        if len(_KEY) != 32:
            raise RuntimeError("Vault master key must be exactly 32 bytes")
    return _KEY


def encrypt(plaintext: str) -> str:
    if not plaintext:
        return ""
    nonce = os.urandom(12)
    ct = AESGCM(_get_key()).encrypt(nonce, plaintext.encode("utf-8"), None)
    return "v1:" + base64.b64encode(nonce).decode() + ":" + base64.b64encode(ct).decode()


def decrypt(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    version, nonce_b64, blob_b64 = ciphertext.split(":", 2)
    if version != "v1":
        raise ValueError(f"Unsupported ciphertext version: {version}")
    nonce = base64.b64decode(nonce_b64)
    blob = base64.b64decode(blob_b64)
    return AESGCM(_get_key()).decrypt(nonce, blob, None).decode("utf-8")


def generate_master_key_b64() -> str:
    return base64.b64encode(secrets.token_bytes(32)).decode()