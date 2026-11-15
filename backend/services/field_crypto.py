"""Application-level encryption for sensitive DB columns (statement text).

Supabase already encrypts the disk; this keeps statement contents unreadable to
anyone who gets database access (a leaked DATABASE_URL, a backup, the Supabase
dashboard) without also having the app's key.

DATA_ENCRYPTION_KEY holds one or more comma-separated Fernet keys. The first
key encrypts; all keys are tried for decryption, so to rotate: put the new key
first, deploy, re-run scripts/encrypt_raw_text.py, then drop the old key.

Generate a key:
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
"""
from __future__ import annotations

import logging
import os
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet

logger = logging.getLogger("field_crypto")

PREFIX = "enc:v1:"


@lru_cache(maxsize=1)
def _fernet() -> MultiFernet | None:
    raw = os.environ.get("DATA_ENCRYPTION_KEY", "").strip()
    keys = [k.strip() for k in raw.split(",") if k.strip()]
    if not keys:
        logger.warning("DATA_ENCRYPTION_KEY not set: statement text is stored unencrypted")
        return None
    return MultiFernet([Fernet(k) for k in keys])


def is_encrypted(value: str | None) -> bool:
    return bool(value) and value.startswith(PREFIX)


def encrypt_text(value: str | None) -> str | None:
    """Encrypt a string for storage. Empty values and already-encrypted values pass through."""
    if not value or is_encrypted(value):
        return value
    f = _fernet()
    if f is None:
        return value
    return PREFIX + f.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(value: str | None) -> str | None:
    """Decrypt a stored string. Plaintext (rows written before encryption) passes through."""
    if not is_encrypted(value):
        return value
    f = _fernet()
    if f is None:
        raise RuntimeError("DATA_ENCRYPTION_KEY is not set but the database holds encrypted data")
    try:
        return f.decrypt(value[len(PREFIX):].encode("ascii")).decode("utf-8")
    except InvalidToken as e:
        raise RuntimeError("Could not decrypt stored data: wrong DATA_ENCRYPTION_KEY") from e
