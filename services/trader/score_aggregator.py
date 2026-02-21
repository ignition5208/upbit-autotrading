"""
Score Aggregator
지침: 가중치 합 + EMA 평활화
"""
from typing import Dict, List
import numpy as np


# 기본 가중치 (지침 3번)
DEFAULT_WEIGHTS = {
    'tp': 0.30,
    'vcb': 0.25,
    'regime': 0.20,
    'lsr': 0.15,
    'lf': 0.10,
}

# EMA 평활화 계수
EMA_ALPHA = 0.3


class ScoreAggregator:
    """점수 집계 및 평활화"""
    
    def __init__(self, weights: Dict[str, float] = None):
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.score_history = {}  # symbol별 점수 히스토리
    
    def aggregate(
        self,
        symbol: str,
        scores: Dict[str, float],
        reason_codes: Dict[str, List[str]] = None,
    ) -> Dict:
        """
        점수 집계
        
        Args:
            symbol: 심볼
            scores: {'tp': 85, 'vcb': 70, 'lsr': 60, 'lf': 50, 'regime': 80}
            reason_codes: 각 모듈의 reason codes
        
        Returns:
            {
                'total_score': float,
                'smoothed_score': float,
                'weighted_scores': Dict,
                'all_reason_codes': List[str]
            }
        """
        # 가중치 합 계산
        total_score = 0.0
        weighted_scores = {}
        
        for module, score in scores.items():
            weight = self.weights.get(module, 0.0)
            weighted = score * weight
            total_score += weighted
            weighted_scores[module] = weighted
        
        # EMA 평활화
        if symbol not in self.score_history:
            self.score_history[symbol] = []
        
        history = self.score_history[symbol]
        history.append(total_score)
        
        # 최근 10개만 유지
        if len(history) > 10:
            history = history[-10:]
            self.score_history[symbol] = history
        
        # EMA 계산
        if len(history) == 1:
            smoothed_score = total_score
        else:
            smoothed_score = EMA_ALPHA * total_score + (1 - EMA_ALPHA) * history[-2]
        
        # 모든 reason codes 수집
        all_reason_codes = []
        if reason_codes:
            for codes in reason_codes.values():
                all_reason_codes.extend(codes)
        
        return {
            'total_score': float(total_score),
            'smoothed_score': float(smoothed_score),
            'weighted_scores': weighted_scores,
            'all_reason_codes': list(set(all_reason_codes)),  # 중복 제거
        }
    
    def update_weights(self, new_weights: Dict[str, float]):
        """가중치 업데이트 (동적 조정)"""
        self.weights.update(new_weights)
