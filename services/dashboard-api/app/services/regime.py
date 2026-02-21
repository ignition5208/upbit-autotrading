"""
Regime 가중치 적용 서비스
지침 4.3: applied_weight = 1 + (w - 1) × (regime_score / 100)
"""
from sqlalchemy.orm import Session
from app.models import RegimeSnapshot
from datetime import datetime, timedelta


def get_current_regime(db: Session, market: str = "KRW-BTC") -> dict | None:
    """현재 Regime 정보 가져오기"""
    snap = (
        db.query(RegimeSnapshot)
        .filter_by(market=market)
        .order_by(RegimeSnapshot.ts.desc())
        .first()
    )
    if not snap:
        return None
    
    import json
    metrics = json.loads(snap.metrics_json) if snap.metrics_json else {}
    
    return {
        "regime_id": snap.regime_id,
        "regime_label": snap.regime_label,
        "confidence": float(snap.confidence),
        "metrics": metrics,
    }


def calculate_regime_weight(
    db: Session,
    regime_label: str,
    base_weight: float = 1.0,
    regime_score: float | None = None,
) -> float:
    """
    Regime 가중치 계산
    applied_weight = 1 + (w - 1) × (regime_score / 100)
    
    Args:
        db: DB 세션
        regime_label: Regime 라벨
        base_weight: 기본 가중치 (w)
        regime_score: Regime 점수 (0-100), None이면 confidence 기반 계산
    
    Returns:
        적용된 가중치
    """
    if regime_score is None:
        # 현재 Regime의 confidence를 점수로 사용
        regime = get_current_regime(db)
        if regime and regime['regime_label'] == regime_label:
            regime_score = regime['confidence'] * 100
        else:
            regime_score = 50.0  # 기본값
    
    # 특수 규칙: CHOP, PANIC은 가중치 0 (신규 진입 금지)
    if regime_label in ("CHOP", "PANIC"):
        return 0.0
    
    # 공식 적용
    applied_weight = 1 + (base_weight - 1) * (regime_score / 100)
    return applied_weight


def is_entry_blocked(db: Session, market: str = "KRW-BTC") -> tuple[bool, str]:
    """
    신규 진입이 차단되어야 하는지 확인
    
    Returns:
        (is_blocked, reason)
    """
    regime = get_current_regime(db, market)
    if not regime:
        return False, ""
    
    regime_label = regime['regime_label']
    
    # CHOP → 신규 진입 금지
    if regime_label == "CHOP":
        return True, "CHOP 레짐: 신규 진입 금지"
    
    # PANIC → 신규 진입 금지
    if regime_label == "PANIC":
        return True, "PANIC 레짐: 신규 진입 금지"
    
    return False, ""


def should_reduce_position(db: Session, market: str = "KRW-BTC") -> bool:
    """
    기존 포지션 축소가 필요한지 확인
    PANIC 레짐에서만 True 반환
    """
    regime = get_current_regime(db, market)
    if not regime:
        return False
    
    return regime['regime_label'] == "PANIC"
