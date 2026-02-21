from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import RegimeSnapshot
from app.services.events import add_event

router = APIRouter()

class SnapshotIn(BaseModel):
    market: str = Field(default="KRW-BTC")
    regime_id: int
    regime_label: str
    confidence: float = 0.0
    metrics: dict = Field(default_factory=dict)

@router.get("/regimes")
def list_regimes():
    return {"items": [
        {"id": 0, "label": "Neutral"},
        {"id": 1, "label": "Bull"},
        {"id": 2, "label": "Bear"},
        {"id": 3, "label": "Sideways"},
    ]}

@router.post("/regimes/snapshot")
def post_snapshot(req: SnapshotIn, db: Session = Depends(get_db)):
    snap = RegimeSnapshot(
        ts=datetime.utcnow(),
        market=req.market,
        regime_id=req.regime_id,
        regime_label=req.regime_label,
        confidence=req.confidence,
        metrics_json=str(req.metrics),
    )
    db.add(snap)
    db.commit()
    add_event(db, None, "INFO", "regime", f"{req.market} {req.regime_label} conf={req.confidence:.2f}")
    return {"ok": True}

@router.get("/regimes/snapshots")
def list_snapshots(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(RegimeSnapshot)
        .order_by(RegimeSnapshot.ts.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [
            {
                "ts": r.ts.isoformat(),
                "market": getattr(r, "market", None),
                "regime_id": r.regime_id,
                "regime_label": r.regime_label,
                "confidence": float(r.confidence),
                "metrics": r.metrics_json,
            }
            for r in rows
        ]
    }