import logging
from cryptography.fernet import Fernet, InvalidToken
from app.settings import Settings

log = logging.getLogger("crypto")
_settings = Settings()

def _build_fernet() -> Fernet:
    key = (_settings.crypto_master_key or "").strip()
    if not key:
        gen = Fernet.generate_key()
        log.warning("CRYPTO_MASTER_KEY is empty. Generated ephemeral key (dev-only).")
        return Fernet(gen)
    try:
        return Fernet(key.encode("utf-8"))
    except Exception:
        gen = Fernet.generate_key()
        log.error("Invalid CRYPTO_MASTER_KEY. Generated ephemeral key (dev-only).")
        return Fernet(gen)

_fernet = _build_fernet()

def encrypt_str(s: str) -> str:
    return _fernet.encrypt(s.encode("utf-8")).decode("utf-8")

def decrypt_str(token: str) -> str:
    try:
        return _fernet.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("Cannot decrypt secret. CRYPTO_MASTER_KEY mismatch?")
