PRESET = {
    "name": "CRAZY",
    "scanner": {
        "timeframe": "1m",
        "scan_interval_sec": 10,
        "top_n": 20,
        "min_krw_volume_24h": 800_000_000,
        "max_spread_bp": 80,
        "max_positions": 6,
    },
    "risk": {
        "daily_loss_limit_pct": 6.0,
        "max_consecutive_losses": 6,
        "per_trade_krw": 120_000,
    },
    "buy": {"strictness": 0.25, "min_score": 0.45},
    "sell": {"tp_pct": 3.2, "sl_pct": 2.0, "trailing_pct": 0.4, "max_hold_minutes": 60},
    "plugins": {
        "buy": ["breakout_volume", "rsi_momentum"],
        "sell": ["trailing_stop", "time_exit"],
    },
    "scoring": {"model": "SCORE_A"},
}
