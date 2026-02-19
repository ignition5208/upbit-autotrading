from fastapi import Depends, Header, HTTPException
from app.settings import Settings

def get_settings() -> Settings:
    return Settings()

def require_api_key(
    x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    settings: Settings = Depends(get_settings),
) -> None:
    # API_KEY 미설정이면 auth 비활성화
    if not settings.api_key:
        return
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
