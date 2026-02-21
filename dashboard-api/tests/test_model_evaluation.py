"""
모델 평가 테스트
"""
import pytest
import numpy as np
from app.services.model_evaluation import (
    calculate_evaluation_metrics,
    evaluate_model,
    check_hard_fail_conditions,
)


class TestEvaluationMetrics:
    """평가 지표 계산 테스트"""
    
    def test_calculate_metrics_basic(self):
        """기본 평가 지표 계산"""
        snapshots = [
            {
                'label_ret_60m': 0.01,
                'label_ret_240m': 0.02,
                'label_mfe_240m': 0.03,
                'label_mae_240m': 0.01,
                'label_dd_240m': -0.01,
            }
            for _ in range(100)
        ]
        
        metrics = calculate_evaluation_metrics(snapshots)
        
        assert 'E' in metrics
        assert 'Sharpe' in metrics
        assert 'Q05' in metrics
        assert 'Q01' in metrics
        assert 'MAE_mean' in metrics
        assert 'MAE_95' in metrics
        assert 'SPD' in metrics
        assert metrics['sample_count'] == 100
    
    def test_calculate_metrics_empty(self):
        """빈 데이터"""
        metrics = calculate_evaluation_metrics([])
        assert metrics == {}
    
    def test_calculate_metrics_with_costs(self):
        """비용 반영 수익률 계산"""
        snapshots = [
            {
                'label_ret_240m': 0.02,  # 2% 수익
            }
            for _ in range(10)
        ]
        
        # fee_rate=0.0005, slippage_rate=0.001
        # r_net = 0.02 - (2 * 0.0005 + 2 * 0.001) = 0.02 - 0.003 = 0.017
        metrics = calculate_evaluation_metrics(snapshots)
        
        assert metrics['E'] == pytest.approx(0.017, rel=0.01)


class TestModelEvaluation:
    """모델 평가 테스트"""
    
    def test_evaluate_pass(self):
        """PASS 평가"""
        metrics = {
            'E': 0.015,  # 평균 수익률 > 1%
            'Sharpe': 0.8,  # Sharpe > 0.5
            'Q05': -0.02,  # Q05 > -3%
            'sample_count': 200,
        }
        
        status, reason = evaluate_model(metrics)
        assert status == "PASS"
        assert "PASS" in reason
    
    def test_evaluate_reject_negative_return(self):
        """음수 수익률로 REJECT"""
        metrics = {
            'E': -0.06,  # -6% < -5%
            'Sharpe': 0.5,
            'sample_count': 200,
        }
        
        status, reason = evaluate_model(metrics)
        assert status == "REJECT"
        assert "-5%" in reason
    
    def test_evaluate_reject_low_sharpe(self):
        """낮은 Sharpe로 REJECT"""
        metrics = {
            'E': 0.01,
            'Sharpe': -1.5,  # < -1.0
            'sample_count': 200,
        }
        
        status, reason = evaluate_model(metrics)
        assert status == "REJECT"
        assert "Sharpe" in reason
    
    def test_evaluate_reject_low_q01(self):
        """낮은 Q01로 REJECT"""
        metrics = {
            'E': 0.01,
            'Sharpe': 0.5,
            'Q01': -0.15,  # < -10%
            'sample_count': 200,
        }
        
        status, reason = evaluate_model(metrics)
        assert status == "REJECT"
        assert "Q01" in reason
    
    def test_evaluate_reject_insufficient_samples(self):
        """샘플 수 부족으로 REJECT"""
        metrics = {
            'E': 0.01,
            'Sharpe': 0.5,
            'sample_count': 50,  # < 100
        }
        
        status, reason = evaluate_model(metrics)
        assert status == "REJECT"
        assert "샘플" in reason
    
    def test_evaluate_hold(self):
        """HOLD 평가"""
        metrics = {
            'E': 0.005,  # < 1%
            'Sharpe': 0.3,  # < 0.5
            'Q05': -0.02,
            'sample_count': 200,
        }
        
        status, reason = evaluate_model(metrics)
        assert status == "HOLD"


class TestHardFailConditions:
    """하드 실패 조건 테스트"""
    
    def test_hard_fail_extreme_negative_return(self):
        """극단적 음수 수익률"""
        metrics = {
            'E': -0.15,  # < -10%
        }
        
        is_fail, reason = check_hard_fail_conditions(metrics)
        assert is_fail is True
        assert "-10%" in reason
    
    def test_hard_fail_extreme_sharpe(self):
        """극단적 낮은 Sharpe"""
        metrics = {
            'Sharpe': -2.5,  # < -2.0
        }
        
        is_fail, reason = check_hard_fail_conditions(metrics)
        assert is_fail is True
        assert "Sharpe" in reason
    
    def test_hard_fail_extreme_q01(self):
        """극단적 낮은 Q01"""
        metrics = {
            'Q01': -0.25,  # < -20%
        }
        
        is_fail, reason = check_hard_fail_conditions(metrics)
        assert is_fail is True
        assert "Q01" in reason
    
    def test_hard_fail_high_mae(self):
        """높은 MAE"""
        metrics = {
            'MAE_95': 0.18,  # > 15%
        }
        
        is_fail, reason = check_hard_fail_conditions(metrics)
        assert is_fail is True
        assert "MAE_95" in reason
    
    def test_no_hard_fail(self):
        """하드 실패 조건 없음"""
        metrics = {
            'E': 0.01,
            'Sharpe': 0.5,
            'Q01': -0.05,
            'MAE_95': 0.10,
        }
        
        is_fail, reason = check_hard_fail_conditions(metrics)
        assert is_fail is False
