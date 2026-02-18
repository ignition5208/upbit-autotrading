PRESET = {
    "name": "PROFIT",
    "scanner": {
        "timeframe": "1m",
        "scan_interval_sec": 20,
        "top_n": 15,
        "min_krw_volume_24h": 1_200_000_000,
        "max_spread_bp": 60,
        "max_positions": 4,
    },
    "risk": {
        "daily_loss_limit_pct": 3.5,
        "max_consecutive_losses": 4,
        "per_trade_krw": 100_000,
    },
    "buy": {"strictness": 0.45, "min_score": 0.5},
    "sell": {"tp_pct": 2.8, "sl_pct": 1.6, "trailing_pct": 0.6, "max_hold_minutes": 120},
    "plugins": {
        "buy": ["volatility_breakout", "breakout_volume"],
        "sell": ["trailing_stop", "indicator_reversal"],
    },
    "scoring": {"model": "SCORE_C"},
}
