import json
from sqlalchemy.orm import Session
from .models import Event
from datetime import datetime

def log_event(db: Session, level: str, code: str, message: str, trader_id: str | None = None, detail: dict | None = None):
    e = Event(
        trader_id=trader_id,
        level=level,
        code=code,
        message=message,
        detail_json=json.dumps(detail, ensure_ascii=False) if detail is not None else None,
        created_at=datetime.utcnow(),
    )
    db.add(e)
    db.commit()
