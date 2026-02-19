import logging

log = logging.getLogger("events")

class EventEmitter:
    def __init__(self, trader_name: str):
        self.trader_name = trader_name

    def info(self, title: str, msg: str): self._emit("INFO", title, msg)
    def warn(self, title: str, msg: str): self._emit("WARN", title, msg)
    def critical(self, title: str, msg: str): self._emit("CRITICAL", title, msg)

    def _emit(self, level: str, title: str, msg: str):
        # TODO: DB events 테이블 저장 + Telegram 전송
        log.warning("[%s][%s] %s - %s", level, self.trader_name, title, msg)
