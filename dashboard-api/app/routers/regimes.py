import json
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db import get_db
from app.models import RegimeSnapshot
from app.services.events import add_event
from app.services.bandit import sample_bandit_weight

router = APIRouter()

_REGIMES = [
    {"id": 0, "label": "RANGE"},
    {"id": 1, "label": "TREND"},
    {"id": 2, "label": "CHOP"},
    {"id": 3, "label": "PANIC"},
    {"id": 4, "label": "BREAKOUT_ROTATION"},
]

_PANIC_NOTIFIED = False  # 프로세스당 PANIC 알람 중복 방지


class SnapshotIn(BaseModel):
    market: str = Field(default="KRW-BTC")
    regime_id: int = 0
    regime_label: str = "RANGE"
    confidence: float = 0.0
    metrics: dict = Field(default_factory=dict)


@router.get("/regimes")
def list_regimes():
    return {"items": _REGIMES}


@router.post("/regimes/snapshot")
def post_snapshot(req: SnapshotIn, db: Session = Depends(get_db)):
    global _PANIC_NOTIFIED
    snap = RegimeSnapshot(
        ts=datetime.utcnow(),
        market=req.market,
        regime_id=req.regime_id,
        regime_label=req.regime_label,
        confidence=req.confidence,
        metrics_json=json.dumps(req.metrics),
    )
    db.add(snap)
    db.commit()
    add_event(db, None, "INFO", "regime",
              f"{req.market} {req.regime_label} conf={req.confidence:.2f}")
    if req.regime_label == "PANIC" and not _PANIC_NOTIFIED:
        from app.services.telegram import send_telegram
        send_telegram("CRITICAL", f"PANIC 레짐 감지: {req.market} (신뢰도 {req.confidence:.0%})")
        _PANIC_NOTIFIED = True
    elif req.regime_label != "PANIC":
        _PANIC_NOTIFIED = False
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
                "market": getattr(r, "market", "KRW-BTC"),
                "regime_id": r.regime_id,
                "regime_label": r.regime_label,
                "confidence": float(r.confidence),
                "metrics": r.metrics_json,
            }
            for r in rows
        ]
    }


@router.get("/regimes/weight/{regime_label}/{strategy_id}")
def get_weight(
    regime_label: str,
    strategy_id: str,
    db: Session = Depends(get_db),
):
    """Bandit 가중치 반환"""
    weight = sample_bandit_weight(db, regime=regime_label, strategy_id=strategy_id)
    return {"regime": regime_label, "strategy_id": strategy_id, "weight": round(weight, 4)}


@router.get("/regimes/regime-weight/{regime_label}")
def get_regime_weight(
    regime_label: str,
    base_weight: float = 1.0,
    db: Session = Depends(get_db),
):
    """Regime 가중치 계산 (지침 4.3)"""
    from app.services.regime import calculate_regime_weight
    weight = calculate_regime_weight(db, regime_label, base_weight=base_weight)
    return {"regime": regime_label, "base_weight": base_weight, "applied_weight": round(weight, 4)}


@router.get("/regimes/entry-blocked")
def check_entry_blocked(
    market: str = "KRW-BTC",
    db: Session = Depends(get_db),
):
    """신규 진입 차단 여부 확인"""
    from app.services.regime import is_entry_blocked
    blocked, reason = is_entry_blocked(db, market)
    return {"blocked": blocked, "reason": reason}


@router.get("/regimes/should-reduce-position")
def check_should_reduce_position(
    market: str = "KRW-BTC",
    db: Session = Depends(get_db),
):
    """포지션 축소 필요 여부 확인"""
    from app.services.regime import should_reduce_position
    should_reduce = should_reduce_position(db, market)
    return {"should_reduce": should_reduce}
