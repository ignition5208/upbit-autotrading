from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.events import list_events, add_event
from pydantic import BaseModel

router = APIRouter()

@router.get("/events")
def get_events(limit: int = Query(default=200, ge=1, le=2000), db: Session = Depends(get_db)):
    return {"items": list_events(db, limit=limit)}

class EventIn(BaseModel):
    trader_name: str | None = None
    level: str = "INFO"
    kind: str = "system"
    message: str = ""

@router.post("/events")
def post_event(req: EventIn, db: Session = Depends(get_db)):
    add_event(db, req.trader_name, req.level, req.kind, req.message)
    return {"ok": True}
