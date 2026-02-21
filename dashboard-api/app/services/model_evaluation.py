"""
OPT-0002 평가 & 게이트 구현
평가 지표 계산 및 상태 결정 (PASS/HOLD/REJECT)
"""
import json
import numpy as np
from typing import Dict, List, Tuple
from datetime import datetime, timedelta


def calculate_evaluation_metrics(
    feature_snapshots: List[Dict],
    fee_rate: float = 0.0005,
    slippage_rate: float = 0.001,
) -> Dict:
    """
    평가 지표 계산
    
    Args:
        feature_snapshots: FeatureSnapshot 데이터 리스트
        fee_rate: 수수료율 (기본 0.05%)
        slippage_rate: 슬리피지율 (기본 0.1%)
    
    Returns:
        평가 지표 딕셔너리
    """
    if not feature_snapshots:
        return {}
    
    # 라벨 추출
    returns_60m = []
    returns_240m = []
    mfe_240m = []
    mae_240m = []
    
    for snapshot in feature_snapshots:
        if snapshot.get('label_ret_60m') is not None:
            ret = snapshot['label_ret_60m']
            # 비용 반영: r_net = r - (2 × fee + 2 × slippage)
            r_net = ret - (2 * fee_rate + 2 * slippage_rate)
            returns_60m.append(r_net)
        
        if snapshot.get('label_ret_240m') is not None:
            ret = snapshot['label_ret_240m']
            r_net = ret - (2 * fee_rate + 2 * slippage_rate)
            returns_240m.append(r_net)
        
        if snapshot.get('label_mfe_240m') is not None:
            mfe_240m.append(snapshot['label_mfe_240m'])
        
        if snapshot.get('label_mae_240m') is not None:
            mae_240m.append(snapshot['label_mae_240m'])
    
    if not returns_240m:
        return {}
    
    returns = np.array(returns_240m)
    
    # E (mean r_net)
    mean_return = float(np.mean(returns))
    
    # Sharpe ratio
    std_return = float(np.std(returns))
    sharpe = float(mean_return / std_return) if std_return > 0 else 0.0
    
    # Q05, Q01 (5분위, 1분위)
    q05 = float(np.percentile(returns, 5))
    q01 = float(np.percentile(returns, 1))
    
    # MAE_mean, MAE_95
    mae_array = np.array(mae_240m) if mae_240m else np.array([])
    mae_mean = float(np.mean(mae_array)) if len(mae_array) > 0 else 0.0
    mae_95 = float(np.percentile(mae_array, 95)) if len(mae_array) > 0 else 0.0
    
    # SPD (signals per day) - 일일 신호 수
    # 간단히 샘플 수를 일수로 나눔
    days = max(1, len(feature_snapshots) / 24)  # 1시간당 1개 샘플 가정
    spd = len(feature_snapshots) / days if days > 0 else 0.0
    
    return {
        'E': mean_return,
        'Sharpe': sharpe,
        'Q05': q05,
        'Q01': q01,
        'MAE_mean': mae_mean,
        'MAE_95': mae_95,
        'SPD': spd,
        'sample_count': len(returns_240m),
    }


def evaluate_model(metrics: Dict) -> Tuple[str, str]:
    """
    모델 평가 및 상태 결정
    
    Returns:
        (status, reason)
        status: PASS, HOLD, REJECT
    """
    if not metrics:
        return "REJECT", "평가 지표 없음"
    
    # 하드 실패 조건
    if metrics.get('E', 0) < -0.05:  # 평균 수익률 -5% 미만
        return "REJECT", f"평균 수익률 {metrics['E']:.2%} < -5%"
    
    if metrics.get('Sharpe', 0) < -1.0:  # Sharpe < -1.0
        return "REJECT", f"Sharpe ratio {metrics['Sharpe']:.2f} < -1.0"
    
    if metrics.get('Q01', 0) < -0.10:  # 1분위 < -10%
        return "REJECT", f"Q01 {metrics['Q01']:.2%} < -10%"
    
    if metrics.get('sample_count', 0) < 100:  # 샘플 수 부족
        return "REJECT", f"샘플 수 {metrics['sample_count']} < 100"
    
    # PASS 조건
    if (metrics.get('E', 0) > 0.01 and  # 평균 수익률 > 1%
        metrics.get('Sharpe', 0) > 0.5 and  # Sharpe > 0.5
        metrics.get('Q05', 0) > -0.03):  # Q05 > -3%
        return "PASS", "모든 PASS 조건 충족"
    
    # HOLD (PASS도 REJECT도 아닌 경우)
    return "HOLD", "추가 검증 필요"


def check_hard_fail_conditions(metrics: Dict) -> Tuple[bool, str]:
    """
    하드 실패 조건 확인
    
    Returns:
        (is_hard_fail, reason)
    """
    if not metrics:
        return True, "평가 지표 없음"
    
    # 하드 실패 조건들
    if metrics.get('E', 0) < -0.10:  # 평균 수익률 -10% 미만
        return True, f"평균 수익률 {metrics['E']:.2%} < -10%"
    
    if metrics.get('Sharpe', 0) < -2.0:  # Sharpe < -2.0
        return True, f"Sharpe ratio {metrics['Sharpe']:.2f} < -2.0"
    
    if metrics.get('Q01', 0) < -0.20:  # 1분위 < -20%
        return True, f"Q01 {metrics['Q01']:.2%} < -20%"
    
    if metrics.get('MAE_95', 0) > 0.15:  # MAE_95 > 15%
        return True, f"MAE_95 {metrics['MAE_95']:.2%} > 15%"
    
    return False, ""
