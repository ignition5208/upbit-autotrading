from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from pydantic import BaseModel
from datetime import datetime
import json

from ..db import get_db
from ..models import Trader, ConfigVersion
from ..events import log_event
from ..dockerctl import stop_remove_trader_container_if_exists
from ..settings import SETTINGS

router = APIRouter()

class TraderCreateReq(BaseModel):
    trader_id: str
    display_name: str | None = None
    mode: str = "PAPER"               # LIVE/PAPER
    strategy_mode: str = "STANDARD"   # SAFE/STANDARD/PROFIT/CRAZY
    account_id: int | None = None
    krw_alloc_limit: int = 0

@router.get("/traders")
def list_traders(db: Session = Depends(get_db)):
    items = db.query(Trader).order_by(Trader.id.asc()).all()
    return [{
        "trader_id": t.trader_id,
        "display_name": t.display_name,
        "mode": t.mode,
        "strategy_mode": t.strategy_mode,
        "account_id": t.account_id,
        "krw_alloc_limit": int(t.krw_alloc_limit or 0),
        "is_enabled": int(t.is_enabled or 0),
        "is_paused": int(t.is_paused or 0),
        "trade_enabled": int(t.trade_enabled or 0),
        "heartbeat_at": t.heartbeat_at.isoformat() if t.heartbeat_at else None,
    } for t in items]

@router.post("/traders")
def add_trader(req: TraderCreateReq, db: Session = Depends(get_db)):
    exists = db.query(Trader).filter(Trader.trader_id == req.trader_id).first()
    if exists:
        raise HTTPException(400, "trader_id exists")

    t = Trader(
        trader_id=req.trader_id,
        display_name=req.display_name,
        mode=req.mode.upper(),
        strategy_mode=req.strategy_mode.upper(),
        account_id=req.account_id,
        krw_alloc_limit=req.krw_alloc_limit,
        is_enabled=1,
        is_paused=1,
        trade_enabled=0,
        created_at=datetime.utcnow(),
    )
    db.add(t); db.commit()

    preset = {
        "strategy_mode": t.strategy_mode,
        "runtime": {"mode": t.mode, "account_id": t.account_id, "krw_alloc_limit": int(t.krw_alloc_limit or 0),
                    "trade_enabled": 0, "paused": 1},
        "scanner": {"timeframe":"3m","scan_interval_sec":30,"top_n":10,"min_krw_volume_24h":2_000_000_000,"max_spread_bp":40,"max_positions":3},
        "plugins": {"buy_plugins":["breakout_volume","ma_pullback","volatility_breakout","rsi_momentum"],
                    "sell_plugins":["fixed_tp_sl","trailing_stop","indicator_reversal","time_exit"]},
        "risk": {"daily_loss_limit_pct":3.0,"max_consecutive_losses":3,"per_trade_krw":70_000},
        "score_model":"SCORE_A"
    }
    v = ConfigVersion(trader_id=t.trader_id, version=1, config_json=json.dumps(preset, ensure_ascii=False), created_at=datetime.utcnow())
    db.add(v); db.commit()

    log_event(db, "INFO", "TRADER_CREATED", f"Trader created: {t.trader_id}", t.trader_id, {"mode": t.mode, "strategy_mode": t.strategy_mode})
    return {"ok": True, "trader_id": t.trader_id}

@router.delete("/traders/{trader_id}")
def delete_trader(trader_id: str, hard: bool = Query(False), db: Session = Depends(get_db)):
    t = db.query(Trader).filter(Trader.trader_id == trader_id).first()
    if not t:
        raise HTTPException(404, "trader not found")

    container_existed = stop_remove_trader_container_if_exists(trader_id)

    if not hard:
        t.is_enabled = 0
        t.is_paused = 1
        t.trade_enabled = 0
        db.commit()
        log_event(db, "WARN", "TRADER_DEACTIVATED", f"Trader deactivated (container_existed={container_existed})", trader_id, {"container_existed": container_existed})
        return {"ok": True, "mode": "deactivate", "container_existed": container_existed}

    try:
        db.execute(text("DELETE FROM config_current  WHERE trader_id=:tid"), {"tid": trader_id})
        db.execute(text("DELETE FROM config_versions WHERE trader_id=:tid"), {"tid": trader_id})
        db.execute(text("DELETE FROM positions WHERE trader_id=:tid"), {"tid": trader_id})
        db.execute(text("DELETE FROM orders    WHERE trader_id=:tid"), {"tid": trader_id})
        db.execute(text("DELETE FROM trades    WHERE trader_id=:tid"), {"tid": trader_id})
        db.execute(text("DELETE FROM scores    WHERE trader_id=:tid"), {"tid": trader_id})
        db.delete(t)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(500, f"hard delete failed: {e}")

    log_event(db, "WARN", "TRADER_DELETED", f"Trader hard deleted (container_existed={container_existed})", trader_id, {"container_existed": container_existed})
    return {"ok": True, "mode": "hard", "container_existed": container_existed}
