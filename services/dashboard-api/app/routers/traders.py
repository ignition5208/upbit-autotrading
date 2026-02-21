from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import Trader
from app.services.trader_orchestrator import ensure_trader_container, stop_trader_container, remove_trader_container
from app.services.events import add_event

router = APIRouter()

class TraderCreateRequest(BaseModel):
    trader_name: str = Field(..., description="Unique name")
    strategy: str = Field(..., description="Strategy name")
    risk_mode: str = Field(..., description="SAFE/STANDARD/PROFIT/CRAZY")
    run_mode: str = Field(..., description="PAPER or LIVE")
    seed_krw: float | None = None
    credential_name: str | None = None

class TraderRunRequest(BaseModel):
    run_mode: str = Field(..., description="PAPER or LIVE")

@router.get("/traders")
def list_traders(db: Session = Depends(get_db)):
    rows = db.execute(select(Trader).order_by(Trader.created_at.desc())).scalars().all()
    return {"items": [{
        "name": r.name,
        "strategy": r.strategy,
        "risk_mode": r.risk_mode,
        "run_mode": r.run_mode,
        "credential_name": r.credential_name,
        "status": r.status,
        "container_name": r.container_name,
        "last_heartbeat_at": r.last_heartbeat_at.isoformat() if r.last_heartbeat_at else None,
        "created_at": r.created_at.isoformat(),
    } for r in rows]}

@router.post("/traders")
def create_trader(req: TraderCreateRequest, db: Session = Depends(get_db)):
    name = req.trader_name.strip()
    if not name:
        raise HTTPException(400, "trader_name required")
    if db.get(Trader, name):
        raise HTTPException(400, "trader already exists")
    t = Trader(
        name=name,
        strategy=req.strategy,
        risk_mode=req.risk_mode,
        run_mode=req.run_mode,
        credential_name=req.credential_name,
        status="STOP",
    )
    db.add(t)
    db.commit()
    add_event(db, t.name, "INFO", "trader", f"created (mode={t.run_mode}, strategy={t.strategy}, risk={t.risk_mode}, cred={t.credential_name})")
    return {"created": True, "name": t.name}

@router.post("/traders/{trader_name}/run")
def run_trader(trader_name: str, req: TraderRunRequest, db: Session = Depends(get_db)):
    t = db.get(Trader, trader_name)
    if not t:
        raise HTTPException(404, "not found")
    ensure_trader_container(db, t, req.run_mode)
    return {"ok": True}

@router.post("/traders/{trader_name}/stop")
def stop_trader(trader_name: str, db: Session = Depends(get_db)):
    t = db.get(Trader, trader_name)
    if not t:
        raise HTTPException(404, "not found")
    stop_trader_container(db, t)
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
