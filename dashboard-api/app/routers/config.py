from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from ..db import get_db
from ..models import Trader, ConfigVersion, ConfigCurrent
from ..events import log_event
from ..settings import SETTINGS
from ..dockerctl import ensure_trader_container

router = APIRouter()

class ConfigDraftReq(BaseModel):
    config_json: Optional[str] = None

class ConfigApplyReq(BaseModel):
    apply_mode: Optional[str] = "restart"
    trade_enabled: Optional[int] = None
    confirm_crazy_live: Optional[bool] = False

class ConfigRollbackReq(BaseModel):
    version: int

def _get_trader_or_404(db: Session, trader_id: str) -> Trader:
    t = db.query(Trader).filter(Trader.trader_id == trader_id).first()
    if not t:
        raise HTTPException(404, "trader not found")
    return t

def _next_version(db: Session, trader_id: str) -> int:
    latest = (db.query(ConfigVersion)
              .filter(ConfigVersion.trader_id == trader_id)
              .order_by(ConfigVersion.version.desc())
              .first())
    return 1 if not latest else int(latest.version) + 1

def _get_latest_version_or_404(db: Session, trader_id: str) -> ConfigVersion:
    v = (db.query(ConfigVersion)
         .filter(ConfigVersion.trader_id == trader_id)
         .order_by(ConfigVersion.version.desc())
         .first())
    if not v:
        raise HTTPException(404, "no config version")
    return v

def _trader_env(trader_id: str) -> Dict[str, str]:
    return {
        "TRADER_ID": trader_id,
        "DB_HOST": SETTINGS.DB_HOST,
        "DB_PORT": str(SETTINGS.DB_PORT),
        "DB_NAME": SETTINGS.DB_NAME,
        "DB_USER": SETTINGS.DB_USER,
        "DB_PASS": SETTINGS.DB_PASS,
        "TZ": SETTINGS.TZ,
        "KEY_ENC_SECRET": SETTINGS.KEY_ENC_SECRET,
    }

@router.get("/config/{trader_id}/current")
def get_current(trader_id: str, db: Session = Depends(get_db)):
    _get_trader_or_404(db, trader_id)
    cur = db.query(ConfigCurrent).filter(ConfigCurrent.trader_id == trader_id).first()
    if not cur:
        return {"trader_id": trader_id, "current": None}
    return {"trader_id": trader_id, "current": {
        "version": int(cur.version),
        "config_json": cur.config_json,
        "applied_at": cur.applied_at.isoformat() if cur.applied_at else None,
        "apply_mode": cur.apply_mode,
    }}

@router.get("/config/{trader_id}/draft")
def get_draft(trader_id: str, db: Session = Depends(get_db)):
    _get_trader_or_404(db, trader_id)
    v = _get_latest_version_or_404(db, trader_id)
    return {"trader_id": trader_id, "draft": {
        "version": int(v.version),
        "config_json": v.config_json,
        "created_at": v.created_at.isoformat() if v.created_at else None
    }}

@router.post("/config/{trader_id}/draft")
def save_draft(trader_id: str, req: ConfigDraftReq, db: Session = Depends(get_db)):
    _get_trader_or_404(db, trader_id)
    if req.config_json is None:
        raise HTTPException(400, "config_json required")
    ver = _next_version(db, trader_id)
    v = ConfigVersion(trader_id=trader_id, version=ver, config_json=req.config_json, created_at=datetime.utcnow())
    db.add(v); db.commit()
    log_event(db, "INFO", "CONFIG_DRAFT_SAVED", f"Draft saved v{ver}", trader_id, {"version": ver})
    return {"ok": True, "trader_id": trader_id, "version": ver}

@router.post("/config/{trader_id}/validate")
def validate(trader_id: str, db: Session = Depends(get_db)):
    _get_trader_or_404(db, trader_id)
    v = _get_latest_version_or_404(db, trader_id)
    return {"ok": True, "errors": [], "version": int(v.version)}

@router.post("/config/{trader_id}/apply")
def apply(trader_id: str, req: ConfigApplyReq, db: Session = Depends(get_db)):
    t = _get_trader_or_404(db, trader_id)
    v = _get_latest_version_or_404(db, trader_id)

    apply_mode = (req.apply_mode or "restart").lower()
    applied_at = datetime.utcnow()

    if (t.mode or "").upper() == "LIVE" and (t.strategy_mode or "").upper() == "CRAZY":
        if not req.confirm_crazy_live:
            raise HTTPException(400, "CRAZY+LIVE requires confirm_crazy_live=true")

    if req.trade_enabled is not None:
        t.trade_enabled = 1 if int(req.trade_enabled) == 1 else 0
        db.add(t)

    try:
        db.execute(
            text("""
                INSERT INTO config_current (trader_id, version, config_json, applied_at, apply_mode)
                VALUES (:trader_id, :version, :config_json, :applied_at, :apply_mode)
                ON DUPLICATE KEY UPDATE
                    version = VALUES(version),
                    config_json = VALUES(config_json),
                    applied_at = VALUES(applied_at),
                    apply_mode = VALUES(apply_mode)
            """),
            {
                "trader_id": trader_id,
                "version": int(v.version),
                "config_json": v.config_json,
                "applied_at": applied_at,
                "apply_mode": apply_mode,
            }
        )
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise HTTPException(500, f"apply failed: {str(e)}")

    recreate = True if apply_mode in ("restart", "immediate") else False
    ensure_trader_container(trader_id, _trader_env(trader_id), recreate=recreate)

    log_event(db, "INFO", "CONFIG_APPLIED", f"Applied v{int(v.version)} ({apply_mode})", trader_id,
              {"version": int(v.version), "apply_mode": apply_mode})

    return {"ok": True, "trader_id": trader_id, "version": int(v.version), "apply_mode": apply_mode}

@router.get("/config/{trader_id}/history")
def history(trader_id: str, db: Session = Depends(get_db)):
    _get_trader_or_404(db, trader_id)
    items = (db.query(ConfigVersion)
             .filter(ConfigVersion.trader_id == trader_id)
             .order_by(ConfigVersion.version.desc())
             .limit(200).all())
    return [{"version": int(i.version),
             "created_at": i.created_at.isoformat() if i.created_at else None} for i in items]

@router.post("/config/{trader_id}/rollback")
def rollback(trader_id: str, req: ConfigRollbackReq, db: Session = Depends(get_db)):
    _get_trader_or_404(db, trader_id)
    target = (db.query(ConfigVersion)
              .filter(ConfigVersion.trader_id == trader_id, ConfigVersion.version == int(req.version))
              .first())
    if not target:
        raise HTTPException(404, "version not found")

    applied_at = datetime.utcnow()
    try:
        db.execute(
            text("""
                INSERT INTO config_current (trader_id, version, config_json, applied_at, apply_mode)
                VALUES (:trader_id, :version, :config_json, :applied_at, :apply_mode)
                ON DUPLICATE KEY UPDATE
                    version = VALUES(version),
                    config_json = VALUES(config_json),
                    applied_at = VALUES(applied_at),
                    apply_mode = VALUES(apply_mode)
            """),
            {
                "trader_id": trader_id,
                "version": int(target.version),
                "config_json": target.config_json,
                "applied_at": applied_at,
                "apply_mode": "rollback",
            }
        )
        db.commit()
    except OperationalError as e:
        db.rollback()
        raise HTTPException(500, f"rollback failed: {str(e)}")

    ensure_trader_container(trader_id, _trader_env(trader_id), recreate=True)
    log_event(db, "WARN", "CONFIG_ROLLBACK", f"Rollback to v{int(target.version)}", trader_id, {"version": int(target.version)})
    return {"ok": True, "trader_id": trader_id, "version": int(target.version)}
