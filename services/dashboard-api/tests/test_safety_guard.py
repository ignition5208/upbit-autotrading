"""
Runtime Guard 테스트
"""
import pytest
from datetime import datetime
from app.services.safety_guard import (
    check_slippage_anomaly,
    record_api_error,
    record_db_error,
    reset_error_counts,
    is_entry_blocked_by_errors,
    check_panic_block,
)
from app.models import TraderSafetyState, RegimeSnapshot
import json


class TestSlippageAnomaly:
    """Slippage 이상 감지 테스트"""
    
    def test_slippage_normal(self, db_session, sample_trader):
        """정상 Slippage"""
        is_anomaly = check_slippage_anomaly(
            db_session,
            sample_trader.name,
            expected_price=1000000.0,
            actual_price=1000005.0,  # 0.0005% 차이
            threshold_pct=0.5,
        )
        assert is_anomaly is False
    
    def test_slippage_anomaly_detected(self, db_session, sample_trader):
        """Slippage 이상 감지"""
        is_anomaly = check_slippage_anomaly(
            db_session,
            sample_trader.name,
            expected_price=1000000.0,
            actual_price=1006000.0,  # 0.6% 차이
            threshold_pct=0.5,
        )
        assert is_anomaly is True
        
        # 상태 확인
        state = db_session.get(TraderSafetyState, sample_trader.name)
        assert state.slippage_anomaly_count == 1
    
    def test_slippage_anomaly_block(self, db_session, sample_trader):
        """연속 3회 이상 감지 시 블록"""
        # 3회 연속 이상 감지
        for _ in range(3):
            check_slippage_anomaly(
                db_session,
                sample_trader.name,
                expected_price=1000000.0,
                actual_price=1006000.0,
                threshold_pct=0.5,
            )
        
        state = db_session.get(TraderSafetyState, sample_trader.name)
        assert state.blocked is True
        assert "Slippage" in state.block_reason


class TestAPIError:
    """API 에러 기록 테스트"""
    
    def test_record_api_error(self, db_session, sample_trader):
        """API 에러 기록"""
        record_api_error(db_session, sample_trader.name)
        
        state = db_session.get(TraderSafetyState, sample_trader.name)
        assert state.api_error_count == 1
    
    def test_api_error_block(self, db_session, sample_trader):
        """연속 5회 에러 시 블록"""
        for _ in range(5):
            record_api_error(db_session, sample_trader.name)
        
        state = db_session.get(TraderSafetyState, sample_trader.name)
        assert state.blocked is True
        assert "API 에러" in state.block_reason


class TestDBError:
    """DB 에러 기록 테스트"""
    
    def test_record_db_error(self, db_session, sample_trader):
        """DB 에러 기록"""
        record_db_error(db_session, sample_trader.name)
        
        state = db_session.get(TraderSafetyState, sample_trader.name)
        assert state.db_error_count == 1
    
    def test_db_error_block(self, db_session, sample_trader):
        """연속 3회 에러 시 블록"""
        for _ in range(3):
            record_db_error(db_session, sample_trader.name)
        
        state = db_session.get(TraderSafetyState, sample_trader.name)
        assert state.blocked is True
        assert "DB 에러" in state.block_reason


class TestEntryBlocking:
    """에러 기반 진입 차단 테스트"""
    
    def test_entry_blocked_api_error(self, db_session, sample_trader):
        """API 에러로 인한 진입 차단"""
        for _ in range(3):
            record_api_error(db_session, sample_trader.name)
        
        blocked, reason = is_entry_blocked_by_errors(db_session, sample_trader.name)
        assert blocked is True
        assert "API" in reason
    
    def test_entry_blocked_db_error(self, db_session, sample_trader):
        """DB 에러로 인한 진입 차단"""
        for _ in range(2):
            record_db_error(db_session, sample_trader.name)
        
        blocked, reason = is_entry_blocked_by_errors(db_session, sample_trader.name)
        assert blocked is True
        assert "DB" in reason
    
    def test_entry_allowed_no_errors(self, db_session, sample_trader):
        """에러 없을 때 진입 허용"""
        blocked, reason = is_entry_blocked_by_errors(db_session, sample_trader.name)
        assert blocked is False


class TestPanicBlock:
    """PANIC 자동 차단 테스트"""
    
    def test_panic_block(self, db_session, sample_trader):
        """PANIC 레짐 자동 차단"""
        snap = RegimeSnapshot(
            ts=datetime.utcnow(),
            market="KRW-BTC",
            regime_id=3,
            regime_label="PANIC",
            confidence=0.8,
            metrics_json="{}",
        )
        db_session.add(snap)
        db_session.commit()
        
        blocked = check_panic_block(db_session, sample_trader.name)
        assert blocked is True
        
        state = db_session.get(TraderSafetyState, sample_trader.name)
        assert state.blocked is True
        assert "PANIC" in state.block_reason
    
    def test_no_panic_no_block(self, db_session, sample_trader):
        """PANIC 아닐 때 차단 안 함"""
        snap = RegimeSnapshot(
            ts=datetime.utcnow(),
            market="KRW-BTC",
            regime_id=1,
            regime_label="TREND",
            confidence=0.7,
            metrics_json="{}",
        )
        db_session.add(snap)
        db_session.commit()
        
        blocked = check_panic_block(db_session, sample_trader.name)
        assert blocked is False


class TestResetErrors:
    """에러 카운트 리셋 테스트"""
    
    def test_reset_error_counts(self, db_session, sample_trader):
        """에러 카운트 리셋"""
        record_api_error(db_session, sample_trader.name)
        record_db_error(db_session, sample_trader.name)
        
        reset_error_counts(db_session, sample_trader.name)
        
        state = db_session.get(TraderSafetyState, sample_trader.name)
        assert state.api_error_count == 0
        assert state.db_error_count == 0
        assert state.slippage_anomaly_count == 0
