"""
Runtime Guard 추가 기능
- Slippage anomaly detection
- API/DB 장애 감지
- PANIC 자동 차단
"""
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models import TraderSafetyState
from app.services.regime import get_current_regime
from app.services.telegram import send_telegram


def check_slippage_anomaly(
    db: Session,
    trader_name: str,
    expected_price: float,
    actual_price: float,
    threshold_pct: float = 0.5,
) -> bool:
    """
    Slippage 이상 감지
    
    Args:
        expected_price: 예상 가격
        actual_price: 실제 체결 가격
        threshold_pct: 이상 감지 임계값 (%)
    
    Returns:
        이상 감지 여부
    """
    if expected_price == 0:
        return False
    
    slippage_pct = abs((actual_price - expected_price) / expected_price) * 100
    
    if slippage_pct > threshold_pct:
        row = db.get(TraderSafetyState, trader_name)
        if not row:
            row = TraderSafetyState(trader_name=trader_name)
            db.add(row)
        
        row.slippage_anomaly_count += 1
        row.last_slippage_check = datetime.utcnow()
        
        # 연속 3회 이상 이상 감지 시 블록
        if row.slippage_anomaly_count >= 3:
            row.blocked = True
            row.block_reason = f"Slippage 이상 감지 {row.slippage_anomaly_count}회 (최근: {slippage_pct:.2f}%)"
            send_telegram("CRITICAL", f"[{trader_name}] 블록: {row.block_reason}")
            db.commit()
            return True
        
        send_telegram("WARN", f"[{trader_name}] Slippage 이상 감지: {slippage_pct:.2f}%")
        db.commit()
        return True
    
    return False


def record_api_error(db: Session, trader_name: str) -> None:
    """API 에러 기록"""
    row = db.get(TraderSafetyState, trader_name)
    if not row:
        row = TraderSafetyState(trader_name=trader_name)
        db.add(row)
    
    row.api_error_count += 1
    row.last_error_check = datetime.utcnow()
    
    # 연속 5회 이상 에러 시 블록
    if row.api_error_count >= 5:
        row.blocked = True
        row.block_reason = f"API 에러 {row.api_error_count}회 연속 발생"
        send_telegram("CRITICAL", f"[{trader_name}] 블록: {row.block_reason}")
    
    db.commit()


def record_db_error(db: Session, trader_name: str) -> None:
    """DB 에러 기록"""
    row = db.get(TraderSafetyState, trader_name)
    if not row:
        row = TraderSafetyState(trader_name=trader_name)
        db.add(row)
    
    row.db_error_count += 1
    row.last_error_check = datetime.utcnow()
    
    # 연속 3회 이상 에러 시 블록
    if row.db_error_count >= 3:
        row.blocked = True
        row.block_reason = f"DB 에러 {row.db_error_count}회 연속 발생"
        send_telegram("CRITICAL", f"[{trader_name}] 블록: {row.block_reason}")
    
    db.commit()


def reset_error_counts(db: Session, trader_name: str) -> None:
    """에러 카운트 리셋 (정상 동작 확인 시)"""
    row = db.get(TraderSafetyState, trader_name)
    if row:
        row.api_error_count = 0
        row.db_error_count = 0
        row.slippage_anomaly_count = 0
        db.commit()


def is_entry_blocked_by_errors(db: Session, trader_name: str) -> tuple[bool, str]:
    """
    API/DB 장애로 인한 신규 진입 차단 확인
    
    Returns:
        (is_blocked, reason)
    """
    row = db.get(TraderSafetyState, trader_name)
    if not row:
        return False, ""
    
    # API 에러가 있으면 차단
    if row.api_error_count >= 3:
        return True, f"API 장애 감지 ({row.api_error_count}회)"
    
    # DB 에러가 있으면 차단
    if row.db_error_count >= 2:
        return True, f"DB 장애 감지 ({row.db_error_count}회)"
    
    return False, ""


def check_panic_block(db: Session, trader_name: str) -> bool:
    """
    PANIC 레짐 자동 차단 확인
    
    Returns:
        차단 여부
    """
    regime = get_current_regime(db)
    if not regime:
        return False
    
    if regime['regime_label'] == "PANIC":
        row = db.get(TraderSafetyState, trader_name)
        if not row:
            row = TraderSafetyState(trader_name=trader_name)
            db.add(row)
        
        if not row.blocked:
            row.blocked = True
            row.block_reason = "PANIC 레짐 자동 차단"
            send_telegram("CRITICAL", f"[{trader_name}] PANIC 레짐으로 인한 자동 차단")
            db.commit()
            return True
    
    return False
