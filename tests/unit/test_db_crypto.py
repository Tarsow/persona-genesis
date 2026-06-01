import pytest

from persona_genesis.db.crypto import VaultCipher, generate_vault_key
from persona_genesis.exceptions import ConfigError


def test_round_trip() -> None:
    cipher = VaultCipher(generate_vault_key())
    token = cipher.encrypt("s3cret")
    assert token != "s3cret"
    assert cipher.decrypt(token) == "s3cret"


def test_accepts_str_key() -> None:
    cipher = VaultCipher(generate_vault_key().decode())
    assert cipher.decrypt(cipher.encrypt("x")) == "x"


def test_invalid_key_raises() -> None:
    with pytest.raises(ConfigError):
        VaultCipher("not-a-fernet-key")
