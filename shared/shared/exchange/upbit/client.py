import os
import requests
from typing import Any, Dict, Optional
from .auth import make_jwt
from .rate_limit import SimpleRateLimiter

UPBIT_API = "https://api.upbit.com"

class UpbitClient:
    def __init__(self, access_key: str | None = None, secret_key: str | None = None):
        self.access_key = access_key or os.getenv("UPBIT_ACCESS_KEY", "")
        self.secret_key = secret_key or os.getenv("UPBIT_SECRET_KEY", "")
        self.s = requests.Session()
        self.rl = SimpleRateLimiter()

    def _headers(self, query: dict | None = None) -> Dict[str, str]:
        token = make_jwt(self.access_key, self.secret_key, query=query)
        return {"Authorization": f"Bearer {token}"}

    def get(self, path: str, params: Optional[dict] = None) -> Any:
        self.rl.wait()
        url = f"{UPBIT_API}{path}"
        r = self.s.get(url, params=params, headers=self._headers(params or None), timeout=10)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, json: dict) -> Any:
        self.rl.wait()
        url = f"{UPBIT_API}{path}"
        r = self.s.post(url, json=json, headers=self._headers(json), timeout=10)
        r.raise_for_status()
        return r.json()
