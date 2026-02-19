# bandit_weight range: 0.5 ~ 1.5 (CHOP/PANIC disabled)
def clamp(v: float) -> float:
    return max(0.5, min(1.5, v))

class BanditWeightEngine:
    def weight_for(self, regime_label: str, strategy: str) -> float:
        if regime_label in ("CHOP", "PANIC"):
            return 1.0
        # TODO: DB bandit_states 기반 Thompson Sampling
        return clamp(1.0)
