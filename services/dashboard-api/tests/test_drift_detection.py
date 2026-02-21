"""
Baseline & Drift 감지 테스트
"""
import pytest
from datetime import datetime, timedelta
import json
from app.services.drift_detection import (
    create_baseline,
    record_24h_metrics,
    check_drift,
    check_auto_rollback_conditions,
    execute_auto_rollback,
)
from app.models import ModelBaseline, ModelMetrics24h, ModelVersion, TraderSafetyState, Trader


class TestBaseline:
    """Baseline 생성 테스트"""
    
    def test_create_baseline(self, db_session):
        """Baseline 생성"""
        baseline_metrics = {
            'sharpe': 1.5,
            'mean_return': 0.02,
        }
        
        baseline = create_baseline(
            db_session,
            strategy_id="test_strategy",
            model_id=1,
            baseline_metrics=baseline_metrics,
        )
        
        assert baseline.strategy_id == "test_strategy"
        assert baseline.baseline_model_id == 1
        assert baseline.drift_warn_count == 0
        
        # 14일 window 확인
        window_days = (baseline.reference_window_end - baseline.reference_window_start).days
        assert window_days == 14


class Test24hMetrics:
    """24시간 메트릭 기록 테스트"""
    
    def test_record_24h_metrics(self, db_session, sample_model_version):
        """24시간 메트릭 기록"""
        metrics = {
            'sharpe': 1.2,
            'return': 0.01,
        }
        
        record_24h_metrics(
            db_session,
            model_id=sample_model_version.id,
            strategy_id=sample_model_version.strategy_id,
            net_return_24h=0.01,
            metrics=metrics,
        )
        
        metric = db_session.query(ModelMetrics24h).filter_by(
            model_id=sample_model_version.id
        ).first()
        
        assert metric is not None
        assert metric.net_return_24h == 0.01
        assert metric.strategy_id == sample_model_version.strategy_id


class TestDriftDetection:
    """Drift 감지 테스트"""
    
    def test_drift_detected_sharpe_drop(self, db_session):
        """Sharpe ratio 하락으로 Drift 감지"""
        baseline = create_baseline(
            db_session,
            strategy_id="test_strategy",
            model_id=1,
            baseline_metrics={'sharpe': 1.5, 'mean_return': 0.02},
        )
        
        current_metrics = {
            'sharpe': 0.8,  # 1.5 * 0.7 = 1.05보다 낮음
            'mean_return': 0.02,
        }
        
        has_drift, warning = check_drift(db_session, "test_strategy", current_metrics)
        assert has_drift is True
        assert "Sharpe" in warning
        
        # Drift 경고 카운트 증가 확인
        db_session.refresh(baseline)
        assert baseline.drift_warn_count == 1
    
    def test_drift_detected_return_drop(self, db_session):
        """수익률 하락으로 Drift 감지"""
        baseline = create_baseline(
            db_session,
            strategy_id="test_strategy",
            model_id=1,
            baseline_metrics={'sharpe': 1.5, 'mean_return': 0.02},
        )
        
        current_metrics = {
            'sharpe': 1.5,
            'mean_return': 0.005,  # 0.02 * 0.5 = 0.01보다 낮음
        }
        
        has_drift, warning = check_drift(db_session, "test_strategy", current_metrics)
        assert has_drift is True
        assert "수익률" in warning
    
    def test_no_drift(self, db_session):
        """Drift 없음"""
        baseline = create_baseline(
            db_session,
            strategy_id="test_strategy",
            model_id=1,
            baseline_metrics={'sharpe': 1.5, 'mean_return': 0.02},
        )
        
        current_metrics = {
            'sharpe': 1.4,  # 하락하지만 임계값 이상
            'mean_return': 0.015,  # 하락하지만 임계값 이상
        }
        
        has_drift, warning = check_drift(db_session, "test_strategy", current_metrics)
        assert has_drift is False


class TestAutoRollback:
    """자동 롤백 테스트"""
    
    def test_rollback_24h_return(self, db_session, sample_model_version):
        """24시간 수익률 -2% 미만으로 롤백"""
        record_24h_metrics(
            db_session,
            model_id=sample_model_version.id,
            strategy_id=sample_model_version.strategy_id,
            net_return_24h=-0.03,  # -3%
            metrics={},
        )
        
        should_rollback, reason = check_auto_rollback_conditions(
            db_session,
            sample_model_version.strategy_id,
            sample_model_version.id,
        )
        
        assert should_rollback is True
        assert "-2%" in reason
    
    def test_rollback_drift_warn(self, db_session, sample_model_version):
        """Drift 경고 3회 연속으로 롤백"""
        baseline = create_baseline(
            db_session,
            strategy_id=sample_model_version.strategy_id,
            model_id=sample_model_version.id,
            baseline_metrics={'sharpe': 1.5},
        )
        
        # 3회 연속 Drift 경고
        for _ in range(3):
            check_drift(
                db_session,
                sample_model_version.strategy_id,
                {'sharpe': 0.8},
            )
        
        should_rollback, reason = check_auto_rollback_conditions(
            db_session,
            sample_model_version.strategy_id,
            sample_model_version.id,
        )
        
        assert should_rollback is True
        assert "Drift 경고" in reason
    
    def test_rollback_consecutive_losses(self, db_session, sample_model_version):
        """연속 손실 5회로 롤백"""
        trader = Trader(
            name="test_trader",
            strategy=sample_model_version.strategy_id,
            seed_krw=1000000.0,
        )
        db_session.add(trader)
        db_session.commit()
        
        safety = TraderSafetyState(
            trader_name=trader.name,
            consecutive_losses=5,
        )
        db_session.add(safety)
        db_session.commit()
        
        should_rollback, reason = check_auto_rollback_conditions(
            db_session,
            sample_model_version.strategy_id,
            sample_model_version.id,
        )
        
        assert should_rollback is True
        assert "연속 손실" in reason
    
    def test_execute_rollback(self, db_session, sample_model_version):
        """롤백 실행"""
        execute_auto_rollback(
            db_session,
            sample_model_version.id,
            "테스트 롤백",
        )
        
        db_session.refresh(sample_model_version)
        assert sample_model_version.status == "DRAFT"
        assert sample_model_version.rolled_back_at is not None
        assert "AUTO_ROLLBACK" in sample_model_version.rollback_reason
