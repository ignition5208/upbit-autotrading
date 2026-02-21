from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import TraderSafetyState
from app.services.telegram import send_telegram

router = APIRouter()


class PnlUpdate(BaseModel):
    loss_krw: float = Field(default=0.0, ge=0)
    consecutive: bool = Field(default=False, description="연속 손실 여부")


@router.get("/safety")
def list_safety(db: Session = Depends(get_db)):
    rows = db.execute(select(TraderSafetyState)).scalars().all()
    return {"items": [{
        "trader_name": r.trader_name,
        "daily_loss_krw": r.daily_loss_krw,
        "consecutive_losses": r.consecutive_losses,
        "last_loss_at": r.last_loss_at.isoformat() if r.last_loss_at else None,
        "blocked": r.blocked,
        "block_reason": r.block_reason,
        "updated_at": r.updated_at.isoformat(),
    } for r in rows]}


@router.get("/safety/{trader_name}")
def get_safety(trader_name: str, db: Session = Depends(get_db)):
    row = db.get(TraderSafetyState, trader_name)
    if not row:
        return {"trader_name": trader_name, "blocked": False, "daily_loss_krw": 0.0,
                "consecutive_losses": 0, "last_loss_at": None, "block_reason": None}
    return {
        "trader_name": row.trader_name,
        "daily_loss_krw": row.daily_loss_krw,
        "consecutive_losses": row.consecutive_losses,
        "last_loss_at": row.last_loss_at.isoformat() if row.last_loss_at else None,
        "blocked": row.blocked,
        "block_reason": row.block_reason,
        "updated_at": row.updated_at.isoformat(),
    }


@router.post("/safety/{trader_name}/update_pnl")
def update_pnl(trader_name: str, req: PnlUpdate, db: Session = Depends(get_db)):
    from app.settings import Settings
    from app.models import Trader
    settings = Settings()
    row = db.get(TraderSafetyState, trader_name)
    if not row:
        row = TraderSafetyState(trader_name=trader_name)
        db.add(row)
    row.daily_loss_krw += req.loss_krw
    if req.consecutive:
        row.consecutive_losses += 1
        row.last_loss_at = datetime.utcnow()
    else:
        row.consecutive_losses = 0
    row.updated_at = datetime.utcnow()
    # 블록 조건 확인
    trader = db.get(Trader, trader_name)
    seed = (trader.seed_krw or 0) if trader else 0
    limit_krw = seed * settings.daily_loss_limit_pct if seed else 0
    if limit_krw > 0 and row.daily_loss_krw >= limit_krw:
        row.blocked = True
        row.block_reason = f"일일 손실 한도 초과 ({row.daily_loss_krw:,.0f} KRW)"
        send_telegram("CRITICAL", f"[{trader_name}] 블록: {row.block_reason}")
    elif row.consecutive_losses >= settings.consecutive_loss_limit:
        row.blocked = True
        row.block_reason = f"연속 손실 {row.consecutive_losses}회"
        send_telegram("CRITICAL", f"[{trader_name}] 블록: {row.block_reason}")
    # pnl_krw 업데이트
    if trader:
        trader.pnl_krw -= req.loss_krw
    db.commit()
    return {"ok": True, "blocked": row.blocked}


@router.post("/safety/{trader_name}/reset")
def reset_safety(trader_name: str, db: Session = Depends(get_db)):
    row = db.get(TraderSafetyState, trader_name)
    if not row:
        raise HTTPException(404, "not found")
    row.blocked = False
    row.block_reason = None
    row.daily_loss_krw = 0.0
    row.consecutive_losses = 0
    row.updated_at = datetime.utcnow()
    db.commit()
    send_telegram("INFO", f"[{trader_name}] Runtime Guard 블록 해제됨")
    return {"ok": True}
