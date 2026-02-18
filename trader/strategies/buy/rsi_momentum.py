from __future__ import annotations

from ..base import Signal, StrategyResult, OrderIntent


def evaluate(st: dict, cfg: dict) -> StrategyResult:
    symbol = st["symbol"]
    strict = cfg.get("buy", {}).get("strictness", 0.6)
    score = st.get("score", 0.0)
    last = st.get("last", 0.0)
    rsi14 = st.get("rsi14")

    if rsi14 is None or last <= 0:
        return StrategyResult(Signal.HOLD, None, "insufficient_data", {"symbol": symbol})

    # strict 낮을수록 더 공격적으로 낮은 rsi에서 반등을 노림
    low_th = 32 + int(10 * strict)   # 32~42
    high_th = 58 + int(10 * strict)  # 58~68

    if rsi14 <= low_th and score >= cfg.get("buy", {}).get("min_score", 0.55):
        krw = cfg.get("risk", {}).get("per_trade_krw", 50_000)
        return StrategyResult(
            Signal.BUY,
            OrderIntent(type="MARKET", side="bid", krw_amount=krw),
            "rsi_oversold_reversal",
            {"symbol": symbol, "last": last, "rsi14": rsi14, "low_th": low_th, "score": score},
        )

    if rsi14 >= high_th and score >= cfg.get("buy", {}).get("min_score", 0.55):
        # 모멘텀(상승) 추종
        krw = cfg.get("risk", {}).get("per_trade_krw", 50_000)
        return StrategyResult(
            Signal.BUY,
            OrderIntent(type="MARKET", side="bid", krw_amount=krw),
            "rsi_momentum_follow",
            {"symbol": symbol, "last": last, "rsi14": rsi14, "high_th": high_th, "score": score},
        )

    return StrategyResult(
        Signal.HOLD,
        None,
        "rsi_momentum_not_met",
        {"symbol": symbol, "last": last, "rsi14": rsi14, "low_th": low_th, "high_th": high_th, "score": score},
    )
