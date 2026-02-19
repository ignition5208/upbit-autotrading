import os
from dotenv import load_dotenv

def load_env(dotenv_path: str | None = None) -> None:
    # .env 로드 (컨테이너에서는 환경변수가 우선)
    load_dotenv(dotenv_path=dotenv_path, override=False)

def require(name: str) -> str:
    v = os.getenv(name)
    if not v:
        raise RuntimeError(f"Missing env: {name}")
    return v
