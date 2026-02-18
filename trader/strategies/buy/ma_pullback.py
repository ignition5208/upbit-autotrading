from __future__ import annotations

from ..base import Signal, StrategyResult, OrderIntent


def evaluate(st: dict, cfg: dict) -> StrategyResult:
    symbol = st["symbol"]
    strict = cfg.get("buy", {}).get("strictness", 0.6)
    score = st.get("score", 0.0)
    last = st.get("last", 0.0)
    ema20 = st.get("ema20")
    ema50 = st.get("ema50")
    rsi14 = st.get("rsi14")

    if not ema20 or not ema50 or not rsi14 or last <= 0:
        return StrategyResult(Signal.HOLD, None, "insufficient_data", {"symbol": symbol})

    trend_ok = ema20 > ema50
    pullback = abs(last - ema20) / ema20
    pull_th = 0.002 + 0.006 * (1.0 - strict)  # strict 높을수록 더 타이트
    rsi_ok = rsi14 >= (45 + 10 * strict)

    if trend_ok and pullback <= pull_th and rsi_ok and score >= cfg.get("buy", {}).get("min_score", 0.55):
        krw = cfg.get("risk", {}).get("per_trade_krw", 50_000)
        return StrategyResult(
            Signal.BUY,
            OrderIntent(type="MARKET", side="bid", krw_amount=krw),
            "ma_pullback_ok",
            {
                "symbol": symbol,
                "last": last,
                "ema20": ema20,
                "ema50": ema50,
                "pullback_pct": pullback * 100,
                "pullback_threshold_pct": pull_th * 100,
                "rsi14": rsi14,
                "score": score,
            },
        )

    return StrategyResult(
        Signal.HOLD,
        None,
        "ma_pullback_not_met",
        {
            "symbol": symbol,
            "last": last,
            "ema20": ema20,
            "ema50": ema50,
            "trend_ok": trend_ok,
            "pullback_pct": pullback * 100,
            "pullback_threshold_pct": pull_th * 100,
            "rsi14": rsi14,
            "rsi_ok": rsi_ok,
            "score": score,
        },
    )
