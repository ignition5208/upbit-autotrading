from sqlalchemy.orm import Session
from sqlalchemy import select
from app.models import Event

def add_event(db: Session, trader_name: str | None, level: str, kind: str, message: str):
    e = Event(trader_name=trader_name, level=level, kind=kind, message=message)
    db.add(e)
    db.commit()
    return e

def list_events(db: Session, limit: int = 200):
    rows = db.execute(select(Event).order_by(Event.id.desc()).limit(limit)).scalars().all()
    return [{
        "id": r.id,
        "ts": r.ts.isoformat(),
        "trader_name": r.trader_name,
        "level": r.level,
        "kind": r.kind,
        "message": r.message,
    } for r in rows][::-1]
