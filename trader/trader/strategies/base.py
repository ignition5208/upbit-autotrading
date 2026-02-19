from dataclasses import dataclass
from typing import Dict, List, Any, Optional

@dataclass
class Pick:
    market: str
    base_score: float
    evidence: Dict[str, Any]

class Strategy:
    name: str = "base"
    score_threshold: float = 0.0

    def scan_and_score(self, regime: dict) -> List[Pick]:
        raise NotImplementedError

    def select_best(self, picks: List[Pick], bandit_weight: float, regime: dict) -> Optional[dict]:
        # 기본 선택: final_score 계산 후 max
        best = None
        best_score = -1e18
        for p in picks:
            final_score = p.base_score * bandit_weight  # regime/risk multiplier는 스켈레톤
            if final_score > best_score and final_score >= self.score_threshold:
                best_score = final_score
                best = {
                    "market": p.market,
                    "base_score": p.base_score,
                    "final_score": final_score,
                    "evidence": p.evidence,
                }
        return best

class StrategyRegistry:
    _m: Dict[str, Strategy] = {}

    @classmethod
    def register(cls, s: Strategy):
        cls._m[s.name] = s

    @classmethod
    def get(cls, name: str) -> Strategy:
        if not cls._m:
            from trader.strategies.presets import strat_challenge1  # noqa: F401
        return cls._m[name]
