from __future__ import annotations

import json
from typing import Any, Dict, Optional
from sqlalchemy import text
from sqlalchemy.engine import Engine


def log_event(engine: Engine, trader_id: str, level: str, code: str, message: str, detail: Optional[Dict[str, Any]] = None):
    detail_json = json.dumps(detail, ensure_ascii=False) if detail is not None else None
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO events(trader_id, level, code, message, detail_json) VALUES (:tid,:lvl,:code,:msg,:detail)"
            ),
            {"tid": trader_id, "lvl": level, "code": code, "msg": message, "detail": detail_json},
        )


def save_scores(engine: Engine, trader_id: str, items: list[dict]):
    if not items:
        return
    with engine.begin() as conn:
        for it in items:
            conn.execute(
                text("INSERT INTO scores(trader_id, symbol, score) VALUES (:tid,:sym,:score)"),
                {"tid": trader_id, "sym": it.get("symbol"), "score": float(it.get("score", 0.0))},
            )
