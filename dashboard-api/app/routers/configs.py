import json
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import ConfigVersion

router = APIRouter()


class ConfigCreate(BaseModel):
    strategy_id: str = Field(..., description="전략 ID")
    params: dict = Field(default_factory=dict)


@router.get("/configs")
def list_configs(db: Session = Depends(get_db)):
    rows = db.execute(
        select(ConfigVersion).order_by(ConfigVersion.created_at.desc())
    ).scalars().all()
    return {"items": [{
        "id": r.id,
        "strategy_id": r.strategy_id,
        "version": r.version,
        "params": r.params_json,
        "is_active": r.is_active,
        "created_at": r.created_at.isoformat(),
    } for r in rows]}


@router.post("/configs")
def create_config(req: ConfigCreate, db: Session = Depends(get_db)):
    latest = db.execute(
        select(ConfigVersion)
        .where(ConfigVersion.strategy_id == req.strategy_id)
        .order_by(ConfigVersion.version.desc())
    ).scalars().first()
    next_version = (latest.version + 1) if latest else 1
    cfg = ConfigVersion(
        strategy_id=req.strategy_id,
        version=next_version,
        params_json=json.dumps(req.params),
        created_at=datetime.utcnow(),
        is_active=False,
    )
    db.add(cfg)
    db.commit()
    return {"created": True, "id": cfg.id, "version": cfg.version}


@router.post("/configs/{cfg_id}/activate")
def activate_config(cfg_id: int, db: Session = Depends(get_db)):
    cfg = db.get(ConfigVersion, cfg_id)
    if not cfg:
        raise HTTPException(404, "not found")
    # 같은 strategy_id의 기존 active 해제
    for row in db.execute(
        select(ConfigVersion).where(
            ConfigVersion.strategy_id == cfg.strategy_id,
            ConfigVersion.is_active == True,  # noqa: E712
        )
    ).scalars().all():
        row.is_active = False
    cfg.is_active = True
    db.commit()
    return {"activated": True, "id": cfg.id}
