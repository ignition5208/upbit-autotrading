import uuid
import jwt
from urllib.parse import urlencode

def make_jwt(access_key: str, secret_key: str, query: dict | None = None) -> str:
    payload = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
    }
    if query:
        payload["query"] = urlencode(query).encode()
    token = jwt.encode(payload, secret_key)
    return token
