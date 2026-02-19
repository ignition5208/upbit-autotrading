from trader.regime.metrics import compute_metrics

class RegimeEngine:
    def current_regime(self) -> dict:
        m = compute_metrics()
        # TODO: 실제 레짐 분류기(스코어/룰 기반)
        label = "RANGE"
        score = 50
        return {"label": label, "score": score, "metrics": m}
