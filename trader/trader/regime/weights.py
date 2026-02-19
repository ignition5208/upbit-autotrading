def applied_weight(w: float, regime_score: float) -> float:
    # applied_weight = 1 + (w-1)*(regime_score/100)
    return 1 + (w - 1) * (regime_score / 100.0)
