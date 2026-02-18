from __future__ import annotations

from ..base import Signal, StrategyResult, OrderIntent


def evaluate(st: dict, cfg: dict) -> StrategyResult:
    symbol = st["symbol"]
    strict = cfg.get("buy", {}).get("strictness", 0.6)
    score = st.get("score", 0.0)
    last = st.get("last", 0.0)
    prev_high = st.get("prev_high", None)
    vol24h = st.get("acc_trade_price_24h", 0.0)
    vol_norm = min(1.0, vol24h / 5_000_000_000)

    if prev_high is None or last <= 0:
        return StrategyResult(Signal.HOLD, None, "insufficient_data", {"symbol": symbol})

    breakout = (last - prev_high) / prev_high
    threshold = 0.002 + (0.004 * strict)  # 0.2% ~ 0.6%
    if breakout >= threshold and vol_norm >= (0.35 + 0.25 * strict) and score >= cfg.get("buy", {}).get("min_score", 0.55):
        krw = cfg.get("risk", {}).get("per_trade_krw", 50_000)
        return StrategyResult(
            Signal.BUY,
            OrderIntent(type="MARKET", side="bid", krw_amount=krw),
            "breakout_volume_ok",
            {
                "symbol": symbol,
                "last": last,
                "prev_high": prev_high,
                "breakout_pct": breakout * 100,
                "acc_trade_price_24h": vol24h,
                "vol_norm": vol_norm,
                "score": score,
            },
        )

    return StrategyResult(
        Signal.HOLD,
        None,
        "breakout_volume_not_met",
        {
            "symbol": symbol,
            "last": last,
            "prev_high": prev_high,
            "breakout_pct": breakout * 100,
            "acc_trade_price_24h": vol24h,
            "vol_norm": vol_norm,
            "score": score,
            "threshold_pct": threshold * 100,
        },
    )
