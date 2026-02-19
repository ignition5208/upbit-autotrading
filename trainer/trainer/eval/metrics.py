def compute_metrics(rows) -> dict:
    # E, Sharpe, Q05/Q01, MAE_mean/MAE_95, SPD 등
    return {"E": 0.0, "Sharpe": 0.0, "Q05": 0.0, "Q01": 0.0, "MAE_mean": 0.0, "MAE_95": 0.0, "SPD": 0.0}
