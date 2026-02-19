import os
import requests
from .templates import fmt

class TelegramNotifier:
    def __init__(self, token: str | None = None, chat_id: str | None = None):
        self.token = token or os.getenv("TELEGRAM_BOT_TOKEN", "")
        self.chat_id = chat_id or os.getenv("TELEGRAM_CHAT_ID", "")

    def send(self, level: str, title: str, msg: str) -> None:
        if not self.token or not self.chat_id:
            return
        text = fmt(level, title, msg)
        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        requests.post(url, json={"chat_id": self.chat_id, "text": text}, timeout=10)
