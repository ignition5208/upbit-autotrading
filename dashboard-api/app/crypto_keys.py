from cryptography.fernet import Fernet
import base64, hashlib
from .settings import SETTINGS

def _fernet():
    h = hashlib.sha256(SETTINGS.KEY_ENC_SECRET.encode("utf-8")).digest()
    k = base64.urlsafe_b64encode(h)
    return Fernet(k)

def encrypt_keypair(access_key: str, secret_key: str):
    f = _fernet()
    return f.encrypt(access_key.encode()).decode(), f.encrypt(secret_key.encode()).decode()

def decrypt_keypair(enc_access: str, enc_secret: str):
    f = _fernet()
    return f.decrypt(enc_access.encode()).decode(), f.decrypt(enc_secret.encode()).decode()
