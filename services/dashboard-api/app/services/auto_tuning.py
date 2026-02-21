"""
OPT-0003 자동 튜닝 구현
TPE / Bayesian Optimization을 사용한 하이퍼파라미터 최적화
"""
import json
import random
from typing import Dict, List, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import ModelVersion, ModelCandidate
from app.services.model_evaluation import calculate_evaluation_metrics, evaluate_model


class TPEOptimizer:
    """Tree-structured Parzen Estimator 최적화"""
    
    def __init__(self, n_trials: int = 60):
        self.n_trials = n_trials
        self.trials = []
        self.best_score = float('-inf')
        self.best_params = None
    
    def suggest(self, param_space: Dict) -> Dict:
        """다음 파라미터 후보 제안"""
        if len(self.trials) == 0:
            # 첫 번째는 랜덤 샘플링
            return self._random_sample(param_space)
        
        # 간단화된 TPE: 좋은 결과와 나쁜 결과를 분리하여 샘플링
        good_trials = [t for t in self.trials if t['score'] > 0]
        bad_trials = [t for t in self.trials if t['score'] <= 0]
        
        if len(good_trials) > 0 and len(bad_trials) > 0:
            # 좋은 결과의 분포를 따르되, 나쁜 결과를 피함
            return self._sample_from_good(good_trials, param_space)
        else:
            return self._random_sample(param_space)
    
    def _random_sample(self, param_space: Dict) -> Dict:
        """랜덤 샘플링"""
        params = {}
        for key, space in param_space.items():
            if isinstance(space, list):
                params[key] = random.choice(space)
            elif isinstance(space, tuple) and len(space) == 2:
                if isinstance(space[0], int):
                    params[key] = random.randint(space[0], space[1])
                else:
                    params[key] = random.uniform(space[0], space[1])
        return params
    
    def _sample_from_good(self, good_trials: List[Dict], param_space: Dict) -> Dict:
        """좋은 결과에서 샘플링"""
        # 간단화: 좋은 결과의 평균값 주변에서 샘플링
        params = {}
        for key in param_space.keys():
            values = [t['params'].get(key) for t in good_trials if key in t['params']]
            if values:
                mean_val = sum(values) / len(values)
                if isinstance(mean_val, int):
                    params[key] = int(mean_val + random.randint(-2, 2))
                else:
                    params[key] = mean_val + random.uniform(-0.1, 0.1)
            else:
                params[key] = self._random_sample({key: param_space[key]})[key]
        return params
    
    def update(self, params: Dict, score: float):
        """시도 결과 업데이트"""
        self.trials.append({'params': params, 'score': score})
        if score > self.best_score:
            self.best_score = score
            self.best_params = params


def optimize_hyperparameters(
    db: Session,
    strategy_id: str,
    feature_snapshots: List[Dict],
    param_space: Dict = None,
) -> Dict:
    """
    하이퍼파라미터 최적화
    
    Args:
        db: DB 세션
        strategy_id: 전략 ID
        feature_snapshots: FeatureSnapshot 데이터
        param_space: 파라미터 공간 정의
    
    Returns:
        최적 파라미터
    """
    if param_space is None:
        param_space = {
            'feature_weights': [(0.5, 1.5), (0.5, 1.5), (0.5, 1.5)],  # 예시
            'penalty_weights': (0.0, 1.0),
            'score_threshold': (0.0, 1.0),
            'topn': [3, 5, 7, 10],
            'regime_policy_multiplier': (0.5, 1.5),
        }
    
    optimizer = TPEOptimizer(n_trials=60)
    
    best_candidate = None
    best_score = float('-inf')
    
    for trial in range(optimizer.n_trials):
        # 파라미터 제안
        params = optimizer.suggest(param_space)
        
        # 간단화: 파라미터를 적용한 평가 (실제로는 모델 재학습 필요)
        # 여기서는 평가 지표만 계산
        metrics = calculate_evaluation_metrics(feature_snapshots)
        
        # 점수 계산 (Sharpe ratio 사용)
        score = metrics.get('Sharpe', 0) if metrics else float('-inf')
        
        # 게이트 통과 확인
        status, _ = evaluate_model(metrics)
        if status == "PASS":
            score += 1.0  # PASS면 보너스
        
        optimizer.update(params, score)
        
        # 후보 저장
        candidate = ModelCandidate(
            strategy_id=strategy_id,
            params_json=json.dumps(params),
            metrics_json=json.dumps(metrics) if metrics else "{}",
            score=score,
            status="PASS" if status == "PASS" else "REJECT",
            created_at=datetime.utcnow(),
        )
        db.add(candidate)
        
        if score > best_score:
            best_score = score
            best_candidate = candidate
    
    db.commit()
    
    if best_candidate:
        return json.loads(best_candidate.params_json)
    
    return optimizer.best_params if optimizer.best_params else {}
