"""
Baseline & Drift 감지 시스템
지침 STAB-0002 구현
"""
import json
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import ModelVersion, ModelBaseline, ModelMetrics24h
from app.services.telegram import send_telegram


def create_baseline(
    db: Session,
    strategy_id: str,
    model_id: int,
    baseline_metrics: dict,
) -> ModelBaseline:
    """Baseline 생성 (14일 reference window)"""
    now = datetime.utcnow()
    window_start = now - timedelta(days=14)
    window_end = now
    
    baseline = ModelBaseline(
        strategy_id=strategy_id,
        baseline_model_id=model_id,
        baseline_metrics_json=json.dumps(baseline_metrics),
        reference_window_start=window_start,
        reference_window_end=window_end,
        created_at=now,
        updated_at=now,
    )
    db.add(baseline)
    db.commit()
    return baseline


def record_24h_metrics(
    db: Session,
    model_id: int,
    strategy_id: str,
    net_return_24h: float,
    metrics: dict,
) -> None:
    """24시간 롤링 메트릭 기록"""
    metric = ModelMetrics24h(
        model_id=model_id,
        strategy_id=strategy_id,
        ts=datetime.utcnow(),
        net_return_24h=net_return_24h,
        metrics_json=json.dumps(metrics),
    )
    db.add(metric)
    db.commit()


def check_drift(db: Session, strategy_id: str, current_metrics: dict) -> tuple[bool, str]:
    """
    Drift 감지
    
    Returns:
        (has_drift, warning_message)
    """
    baseline = (
        db.query(ModelBaseline)
        .filter_by(strategy_id=strategy_id)
        .order_by(ModelBaseline.created_at.desc())
        .first()
    )
    
    if not baseline:
        return False, ""
    
    baseline_metrics = json.loads(baseline.baseline_metrics_json)
    
    # 간단한 drift 감지: 주요 메트릭 비교
    drift_detected = False
    warnings = []
    
    # Sharpe ratio 비교
    baseline_sharpe = baseline_metrics.get('sharpe', 0)
    current_sharpe = current_metrics.get('sharpe', 0)
    if baseline_sharpe > 0 and current_sharpe < baseline_sharpe * 0.7:
        drift_detected = True
        warnings.append(f"Sharpe ratio 하락 ({baseline_sharpe:.2f} → {current_sharpe:.2f})")
    
    # 수익률 비교
    baseline_return = baseline_metrics.get('mean_return', 0)
    current_return = current_metrics.get('mean_return', 0)
    if baseline_return > 0 and current_return < baseline_return * 0.5:
        drift_detected = True
        warnings.append(f"수익률 하락 ({baseline_return:.2%} → {current_return:.2%})")
    
    if drift_detected:
        baseline.drift_warn_count += 1
        baseline.last_drift_check = datetime.utcnow()
        db.commit()
        
        warning_msg = "; ".join(warnings)
        send_telegram("WARN", f"[{strategy_id}] Drift 경고: {warning_msg}")
        return True, warning_msg
    
    return False, ""


def check_auto_rollback_conditions(
    db: Session,
    strategy_id: str,
    model_id: int,
) -> tuple[bool, str]:
    """
    자동 롤백 조건 확인
    
    조건:
    1. net_return_24h < -2%
    2. drift_warn 3회 연속
    3. consecutive_losses ≥ 5
    
    Returns:
        (should_rollback, reason)
    """
    # 1. 24시간 수익률 확인
    recent_metric = (
        db.query(ModelMetrics24h)
        .filter_by(model_id=model_id)
        .order_by(ModelMetrics24h.ts.desc())
        .first()
    )
    
    if recent_metric and recent_metric.net_return_24h < -0.02:
        return True, f"24시간 수익률 {recent_metric.net_return_24h:.2%} < -2%"
    
    # 2. Drift 경고 3회 연속 확인
    baseline = (
        db.query(ModelBaseline)
        .filter_by(strategy_id=strategy_id)
        .order_by(ModelBaseline.created_at.desc())
        .first()
    )
    
    if baseline and baseline.drift_warn_count >= 3:
        return True, f"Drift 경고 {baseline.drift_warn_count}회 연속"
    
    # 3. 연속 손실 확인 (TraderSafetyState에서 확인)
    from app.models import TraderSafetyState
    from app.models import Trader
    
    traders = db.query(Trader).filter_by(strategy=strategy_id).all()
    for trader in traders:
        safety = db.get(TraderSafetyState, trader.name)
        if safety and safety.consecutive_losses >= 5:
            return True, f"{trader.name} 연속 손실 {safety.consecutive_losses}회"
    
    return False, ""


def execute_auto_rollback(db: Session, model_id: int, reason: str) -> None:
    """자동 롤백 실행"""
    model = db.get(ModelVersion, model_id)
    if not model:
        return
    
    model.rolled_back_at = datetime.utcnow()
    model.rollback_reason = f"AUTO_ROLLBACK: {reason}"
    model.status = "DRAFT"
    
    send_telegram("CRITICAL", f"[{model.strategy_id}] 자동 롤백 실행: {reason}")
    db.commit()
