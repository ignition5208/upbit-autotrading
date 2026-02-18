PRESET = {
    "name": "STANDARD",
    "scanner": {
        "timeframe": "3m",
        "scan_interval_sec": 30,
        "top_n": 12,
        "min_krw_volume_24h": 2_000_000_000,
        "max_spread_bp": 40,
        "max_positions": 3,
    },
    "risk": {
        "daily_loss_limit_pct": 2.0,
        "max_consecutive_losses": 3,
        "per_trade_krw": 70_000,
    },
    "buy": {"strictness": 0.6, "min_score": 0.55},
    "sell": {"tp_pct": 2.2, "sl_pct": 1.2, "trailing_pct": 0.8, "max_hold_minutes": 180},
    "plugins": {
        "buy": ["breakout_volume", "rsi_momentum"],
        "sell": ["trailing_stop", "fixed_tp_sl"],
    },
    "scoring": {"model": "SCORE_A"},
}
