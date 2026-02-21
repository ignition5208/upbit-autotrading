"""
Regime 가중치 및 특수 규칙 테스트
"""
import pytest
from datetime import datetime
import json
from app.services.regime import (
    get_current_regime,
    calculate_regime_weight,
    is_entry_blocked,
    should_reduce_position,
)
from app.models import RegimeSnapshot


class TestRegimeWeight:
    """Regime 가중치 계산 테스트"""
    
    def test_get_current_regime(self, db_session, sample_regime_snapshot):
        """현재 Regime 가져오기"""
        regime = get_current_regime(db_session, "KRW-BTC")
        assert regime is not None
        assert regime['regime_label'] == "TREND"
        assert regime['confidence'] == 0.75
    
    def test_get_current_regime_not_found(self, db_session):
        """Regime 없을 때"""
        regime = get_current_regime(db_session, "KRW-ETH")
        assert regime is None
    
    def test_calculate_regime_weight_normal(self, db_session, sample_regime_snapshot):
        """정상 Regime 가중치 계산"""
        weight = calculate_regime_weight(
            db_session,
            regime_label="TREND",
            base_weight=1.2,
            regime_score=75.0,
        )
        # applied_weight = 1 + (1.2 - 1) * (75 / 100) = 1 + 0.2 * 0.75 = 1.15
        assert weight == pytest.approx(1.15, rel=0.01)
    
    def test_calculate_regime_weight_chop(self, db_session):
        """CHOP 레짐 가중치 0"""
        weight = calculate_regime_weight(
            db_session,
            regime_label="CHOP",
            base_weight=1.2,
        )
        assert weight == 0.0
    
    def test_calculate_regime_weight_panic(self, db_session):
        """PANIC 레짐 가중치 0"""
        weight = calculate_regime_weight(
            db_session,
            regime_label="PANIC",
            base_weight=1.2,
        )
        assert weight == 0.0
    
    def test_calculate_regime_weight_with_confidence(self, db_session, sample_regime_snapshot):
        """Confidence 기반 가중치 계산"""
        weight = calculate_regime_weight(
            db_session,
            regime_label="TREND",
            base_weight=1.5,
        )
        # regime_score는 confidence * 100 = 75
        # applied_weight = 1 + (1.5 - 1) * (75 / 100) = 1 + 0.5 * 0.75 = 1.375
        assert weight == pytest.approx(1.375, rel=0.01)


class TestEntryBlocking:
    """신규 진입 차단 테스트"""
    
    def test_entry_blocked_chop(self, db_session):
        """CHOP 레짐에서 진입 차단"""
        snap = RegimeSnapshot(
            ts=datetime.utcnow(),
            market="KRW-BTC",
            regime_id=2,
            regime_label="CHOP",
            confidence=0.7,
            metrics_json="{}",
        )
        db_session.add(snap)
        db_session.commit()
        
        blocked, reason = is_entry_blocked(db_session, "KRW-BTC")
        assert blocked is True
        assert "CHOP" in reason
    
    def test_entry_blocked_panic(self, db_session):
        """PANIC 레짐에서 진입 차단"""
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
        
        blocked, reason = is_entry_blocked(db_session, "KRW-BTC")
        assert blocked is True
        assert "PANIC" in reason
    
    def test_entry_allowed_trend(self, db_session, sample_regime_snapshot):
        """TREND 레짐에서 진입 허용"""
        blocked, reason = is_entry_blocked(db_session, "KRW-BTC")
        assert blocked is False


class TestPositionReduction:
    """포지션 축소 테스트"""
    
    def test_should_reduce_position_panic(self, db_session):
        """PANIC 레짐에서 포지션 축소"""
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
        
        should_reduce = should_reduce_position(db_session, "KRW-BTC")
        assert should_reduce is True
    
    def test_should_not_reduce_position_trend(self, db_session, sample_regime_snapshot):
        """TREND 레짐에서 포지션 축소 불필요"""
        should_reduce = should_reduce_position(db_session, "KRW-BTC")
        assert should_reduce is False
