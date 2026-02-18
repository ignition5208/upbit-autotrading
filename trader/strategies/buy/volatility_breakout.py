from __future__ import annotations

from ..base import Signal, StrategyResult, OrderIntent


def evaluate(st: dict, cfg: dict) -> StrategyResult:
    symbol = st["symbol"]
    strict = cfg.get("buy", {}).get("strictness", 0.6)
    score = st.get("score", 0.0)
    last = st.get("last", 0.0)
    atr14 = st.get("atr14")
    prev_close = st.get("prev_close")

    if not atr14 or not prev_close or last <= 0:
        return StrategyResult(Signal.HOLD, None, "insufficient_data", {"symbol": symbol})

    move = (last - prev_close)
    k = 0.35 + 0.35 * strict
    trigger = atr14 * k

    if move >= trigger and score >= cfg.get("buy", {}).get("min_score", 0.55):
        krw = cfg.get("risk", {}).get("per_trade_krw", 50_000)
        return StrategyResult(
            Signal.BUY,
            OrderIntent(type="MARKET", side="bid", krw_amount=krw),
            "volatility_breakout_ok",
            {
                "symbol": symbol,
                "last": last,
                "prev_close": prev_close,
                "atr14": atr14,
                "move": move,
                "k": k,
                "trigger": trigger,
                "score": score,
            },
        )

    return StrategyResult(
        Signal.HOLD,
        None,
        "volatility_breakout_not_met",
        {
            "symbol": symbol,
            "last": last,
            "prev_close": prev_close,
            "atr14": atr14,
            "move": move,
            "k": k,
            "trigger": trigger,
            "score": score,
        },
    )
