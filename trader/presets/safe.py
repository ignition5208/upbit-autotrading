PRESET = {
    "name": "SAFE",
    "scanner": {
        "timeframe": "5m",
        "scan_interval_sec": 60,
        "top_n": 10,
        "min_krw_volume_24h": 3_000_000_000,
        "max_spread_bp": 30,
        "max_positions": 2,
    },
    "risk": {
        "daily_loss_limit_pct": 1.0,
        "max_consecutive_losses": 2,
        "per_trade_krw": 50_000,
    },
    "buy": {
        "strictness": 0.8,
        "min_score": 0.65,
    },
    "sell": {
        "tp_pct": 1.8,
        "sl_pct": 1.0,
        "trailing_pct": 0.9,
        "max_hold_minutes": 240,
    },
    "plugins": {
        "buy": ["ma_pullback", "breakout_volume"],
        "sell": ["fixed_tp_sl", "time_exit"],
    },
    "scoring": {"model": "SCORE_B"},
}
