from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import Trader
from app.services.trader_orchestrator import ensure_trader_container, stop_trader_container, remove_trader_container
from app.services.events import add_event
from app.services.telegram import send_telegram
from app.settings import Settings

router = APIRouter()
_settings = Settings()


class TraderCreateRequest(BaseModel):
    trader_name: str = Field(..., description="Unique name")
    strategy: str = Field(..., description="Strategy name")
    risk_mode: str = Field(..., description="SAFE/STANDARD/PROFIT/CRAZY")
    run_mode: str = Field(default="PAPER", description="PAPER or LIVE")
    seed_krw: float | None = None
    credential_name: str | None = None


class TraderRunRequest(BaseModel):
    run_mode: str = Field(..., description="PAPER or LIVE")


def _protect_remaining_sec(t: Trader) -> int:
    if not t.paper_started_at:
        return 0
    deadline = t.paper_started_at + timedelta(hours=_settings.paper_protect_hours)
    remaining = (deadline - datetime.utcnow()).total_seconds()
    return max(0, int(remaining))


@router.get("/traders/{trader_name}")
def get_trader(trader_name: str, db: Session = Depends(get_db)):
    """Trader 상세 정보 조회"""
    t = db.get(Trader, trader_name)
    if not t:
        raise HTTPException(404, "not found")
    
    pnl_pct = None
    if t.seed_krw and t.seed_krw > 0:
        pnl_pct = t.pnl_krw / t.seed_krw if t.pnl_krw else 0.0
    elif t.pnl_krw:
        pnl_pct = 0.0
    
    return {
        "name": t.name,
        "strategy": t.strategy,
        "risk_mode": t.risk_mode,
        "run_mode": t.run_mode,
        "credential_name": t.credential_name,
        "status": t.status,
        "container_name": t.container_name,
        "seed_krw": t.seed_krw,
        "pnl_krw": t.pnl_krw,
        "pnl": pnl_pct,
        "paper_started_at": t.paper_started_at.isoformat() if t.paper_started_at else None,
        "armed_at": t.armed_at.isoformat() if t.armed_at else None,
        "paper_protect_remaining_sec": _protect_remaining_sec(t),
        "last_heartbeat_at": t.last_heartbeat_at.isoformat() if t.last_heartbeat_at else None,
        "created_at": t.created_at.isoformat(),
    }


@router.get("/traders")
def list_traders(db: Session = Depends(get_db)):
    rows = db.execute(select(Trader).order_by(Trader.created_at.desc())).scalars().all()
    items = []
    for r in rows:
        # 수익률 계산 (seed_krw 기준)
        pnl_pct = None
        if r.seed_krw and r.seed_krw > 0:
            pnl_pct = r.pnl_krw / r.seed_krw if r.pnl_krw else 0.0
        elif r.pnl_krw:
            pnl_pct = 0.0
        
        items.append({
            "name": r.name,
            "strategy": r.strategy,
            "risk_mode": r.risk_mode,
            "run_mode": r.run_mode,
            "credential_name": r.credential_name,
            "status": r.status,
            "container_name": r.container_name,
            "seed_krw": r.seed_krw,
            "pnl_krw": r.pnl_krw,
            "pnl": pnl_pct,  # 프론트엔드 호환성
            "paper_started_at": r.paper_started_at.isoformat() if r.paper_started_at else None,
            "armed_at": r.armed_at.isoformat() if r.armed_at else None,
            "paper_protect_remaining_sec": _protect_remaining_sec(r),
            "last_heartbeat_at": r.last_heartbeat_at.isoformat() if r.last_heartbeat_at else None,
            "created_at": r.created_at.isoformat(),
        })
    return {"items": items}


@router.post("/traders")
def create_trader(req: TraderCreateRequest, db: Session = Depends(get_db)):
    name = req.trader_name.strip()
    if not name:
        raise HTTPException(400, "trader_name required")
    if db.get(Trader, name):
        raise HTTPException(400, "trader already exists")
    now = datetime.utcnow()
    t = Trader(
        name=name,
        strategy=req.strategy,
        risk_mode=req.risk_mode,
        run_mode="PAPER",        # always PAPER on creation
        credential_name=req.credential_name,
        seed_krw=req.seed_krw,
        status="STOP",
        paper_started_at=now,   # 24h protection starts now
    )
    db.add(t)
    db.commit()
    add_event(db, t.name, "INFO", "trader", f"created (strategy={t.strategy}, risk={t.risk_mode}, seed={t.seed_krw})")
    return {"created": True, "name": t.name}


@router.post("/traders/{trader_name}/run")
def run_trader(trader_name: str, req: TraderRunRequest, db: Session = Depends(get_db)):
    t = db.get(Trader, trader_name)
    if not t:
        raise HTTPException(404, "not found")
    if req.run_mode == "LIVE":
        remaining = _protect_remaining_sec(t)
        if remaining > 0:
            raise HTTPException(400, f"PAPER 보호기간 {remaining}초 남음. LIVE 전환 불가.")
        if t.armed_at is None:
            raise HTTPException(400, "ARM 먼저 필요합니다. POST /api/traders/{name}/arm")
    ensure_trader_container(db, t, req.run_mode)
    return {"ok": True}


@router.post("/traders/{trader_name}/arm")
def arm_trader(trader_name: str, db: Session = Depends(get_db)):
    t = db.get(Trader, trader_name)
    if not t:
        raise HTTPException(404, "not found")
    remaining = _protect_remaining_sec(t)
    if remaining > 0:
        raise HTTPException(400, f"PAPER 보호기간 {remaining}초 남음. ARM 불가.")
    if t.armed_at is not None:
        return {"ok": True, "armed_at": t.armed_at.isoformat(), "already_armed": True}
    t.armed_at = datetime.utcnow()
    db.commit()
    add_event(db, t.name, "WARN", "trader", "ARMED — LIVE 전환 준비 완료")
    send_telegram("WARN", f"[{t.name}] ARMED — LIVE 전환이 허용되었습니다.")
    return {"ok": True, "armed_at": t.armed_at.isoformat()}


@router.post("/traders/{trader_name}/stop")
def stop_trader(trader_name: str, db: Session = Depends(get_db)):
    t = db.get(Trader, trader_name)
    if not t:
        raise HTTPException(404, "not found")
    stop_trader_container(db, t)
    send_telegram("INFO", f"[{t.name}] STOPPED")
    return {"ok": True}


@router.delete("/traders/{trader_name}")
def delete_trader(trader_name: str, db: Session = Depends(get_db)):
    t = db.get(Trader, trader_name)
    if not t:
        return {"deleted": False}
    remove_trader_container(db, t)
    db.delete(t)
    db.commit()
    return {"deleted": True}
