import pytest
from cryptography.fernet import Fernet

from services import field_crypto
from services.field_crypto import decrypt_text, encrypt_text, is_encrypted


@pytest.fixture
def key(monkeypatch):
    k = Fernet.generate_key().decode()
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", k)
    field_crypto._fernet.cache_clear()
    yield k
    field_crypto._fernet.cache_clear()


def test_round_trip(key):
    enc = encrypt_text("ACCT 8151183521 balance 1,234.00")
    assert is_encrypted(enc)
    assert "8151183521" not in enc
    assert decrypt_text(enc) == "ACCT 8151183521 balance 1,234.00"


def test_plaintext_and_empty_pass_through(key):
    assert decrypt_text("legacy plaintext") == "legacy plaintext"
    assert encrypt_text("") == ""
    assert encrypt_text(None) is None


def test_encrypt_is_idempotent(key):
    enc = encrypt_text("x")
    assert encrypt_text(enc) == enc


def test_rotation_old_key_still_decrypts(monkeypatch, key):
    enc = encrypt_text("secret")
    monkeypatch.setenv("DATA_ENCRYPTION_KEY", f"{Fernet.generate_key().decode()},{key}")
    field_crypto._fernet.cache_clear()
    assert decrypt_text(enc) == "secret"


def test_no_key_stores_plaintext_but_refuses_to_read_ciphertext(monkeypatch, key):
    enc = encrypt_text("secret")
    monkeypatch.delenv("DATA_ENCRYPTION_KEY")
    field_crypto._fernet.cache_clear()
    assert encrypt_text("plain") == "plain"
    with pytest.raises(RuntimeError):
        decrypt_text(enc)
