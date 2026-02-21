from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import ModelVersion

router = APIRouter()


class ModelCreate(BaseModel):
    strategy_id: str = Field(...)
    version: str = Field(...)
    metrics: dict = Field(default_factory=dict)


@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    rows = db.execute(
        select(ModelVersion).order_by(ModelVersion.created_at.desc())
    ).scalars().all()
    return {"items": [{
        "id": r.id,
        "strategy_id": r.strategy_id,
        "version": r.version,
        "status": r.status,
        "metrics": r.metrics_json,
        "created_at": r.created_at.isoformat(),
        "deployed_at": r.deployed_at.isoformat() if r.deployed_at else None,
        "rolled_back_at": r.rolled_back_at.isoformat() if r.rolled_back_at else None,
        "rollback_reason": r.rollback_reason,
    } for r in rows]}


@router.post("/models")
def create_model(req: ModelCreate, db: Session = Depends(get_db)):
    import json
    mv = ModelVersion(
        strategy_id=req.strategy_id,
        version=req.version,
        metrics_json=json.dumps(req.metrics),
        created_at=datetime.utcnow(),
    )
    db.add(mv)
    db.commit()
    return {"created": True, "id": mv.id}


@router.post("/models/{model_id}/deploy")
def deploy_model(model_id: int, db: Session = Depends(get_db)):
    mv = db.get(ModelVersion, model_id)
    if not mv:
        raise HTTPException(404, "not found")
    mv.status = "PAPER_DEPLOYED"
    mv.deployed_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "status": mv.status}


@router.post("/models/{model_id}/arm")
def arm_model(model_id: int, db: Session = Depends(get_db)):
    mv = db.get(ModelVersion, model_id)
    if not mv:
        raise HTTPException(404, "not found")
    if mv.status not in ("PAPER_DEPLOYED", "LIVE_ELIGIBLE"):
        raise HTTPException(400, f"현재 상태 {mv.status}에서 LIVE_ARMED 불가")
    mv.status = "LIVE_ARMED"
    db.commit()
    return {"ok": True, "status": mv.status}


@router.post("/models/{model_id}/rollback")
def rollback_model(model_id: int, reason: str = "", db: Session = Depends(get_db)):
    mv = db.get(ModelVersion, model_id)
    if not mv:
        raise HTTPException(404, "not found")
    mv.rolled_back_at = datetime.utcnow()
    mv.rollback_reason = reason or "manual rollback"
    mv.status = "DRAFT"
    db.commit()
    return {"ok": True}
