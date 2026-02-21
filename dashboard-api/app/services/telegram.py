import logging
import httpx
from app.settings import Settings

log = logging.getLogger("telegram")
_settings = Settings()

_ICONS = {"INFO": "ℹ️", "WARN": "⚠️", "CRITICAL": "🔴"}


def send_telegram(level: str, text: str) -> None:
    """텔레그램 메시지 전송 (토큰/채팅ID 없으면 로그만)."""
    token = _settings.telegram_bot_token.strip()
    chat_id = _settings.telegram_chat_id.strip()
    if not token or not chat_id:
        log.info("[Telegram-%s] %s", level, text)
        return
    icon = _ICONS.get(level, "📢")
    msg = f"{icon} [{level}] {text}"
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.post(
                f"https://api.telegram.org/bot{token}/sendMessage",
                json={"chat_id": chat_id, "text": msg, "parse_mode": "HTML"},
            )
            if resp.status_code != 200:
                log.warning("Telegram HTTP %s: %s", resp.status_code, resp.text[:200])
    except Exception as exc:
        log.warning("Telegram send failed: %s", exc)
