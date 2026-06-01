"""Reversible encryption for account-vault secrets (Fernet: AES-128-CBC + HMAC)."""

from cryptography.fernet import Fernet, InvalidToken

from persona_genesis.exceptions import ConfigError


def generate_vault_key() -> bytes:
    return Fernet.generate_key()


class VaultCipher:
    def __init__(self, key: str | bytes) -> None:
        key_bytes = key.encode() if isinstance(key, str) else key
        try:
            self._fernet = Fernet(key_bytes)
        except (ValueError, TypeError) as exc:
            raise ConfigError(
                "vault_key is not a valid Fernet key (use db.crypto.generate_vault_key())"
            ) from exc

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, token: str) -> str:
        try:
            return self._fernet.decrypt(token.encode()).decode()
        except InvalidToken as exc:
            raise ConfigError("vault_key cannot decrypt stored secret") from exc
