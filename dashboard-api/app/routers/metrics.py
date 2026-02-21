from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.db import get_db
from app.models import Trader

router = APIRouter()

@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(Trader)) or 0
    live = db.scalar(select(func.count()).select_from(Trader).where(Trader.run_mode=="LIVE")) or 0
    paper = db.scalar(select(func.count()).select_from(Trader).where(Trader.run_mode=="PAPER")) or 0
    active = db.scalar(select(func.count()).select_from(Trader).where(Trader.status=="RUN")) or 0
    return {"total_traders": total, "live_traders": live, "paper_traders": paper, "active_traders": active, "pnl_24h": 0.0}
