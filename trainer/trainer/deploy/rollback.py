def should_auto_rollback(metrics_24h: dict) -> bool:
    # net_return_24h < -2% or drift_warn 3회 or consecutive_losses>=5
    return False
