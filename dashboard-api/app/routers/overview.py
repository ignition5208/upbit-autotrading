from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Trader, Event

router = APIRouter()

@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    traders = db.query(Trader).count()
    latest = db.query(Event).order_by(Event.id.desc()).limit(10).all()
    return {
        "traders": traders,
        "latest_events": [{"id": e.id, "level": e.level, "code": e.code, "message": e.message, "trader_id": e.trader_id, "created_at": e.created_at.isoformat()} for e in latest]
    }
