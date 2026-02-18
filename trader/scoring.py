from __future__ import annotations

from typing import Dict


def clamp01(x: float) -> float:
    return 0.0 if x < 0 else (1.0 if x > 1.0 else x)


def score_a(st: Dict) -> float:
    # 거래대금 + 돌파
    vol = st.get("acc_trade_price_24h", 0.0)
    vol_s = clamp01(vol / 6_000_000_000)
    breakout = st.get("breakout_pct", 0.0)
    brk_s = clamp01(breakout / 1.0)  # 1% 기준
    return clamp01(0.65 * vol_s + 0.35 * brk_s)


def score_b(st: Dict) -> float:
    # 추세/모멘텀 안정성 (MA 정렬 + RSI)
    ema20 = st.get("ema20")
    ema50 = st.get("ema50")
    rsi14 = st.get("rsi14")
    trend = 0.0
    if ema20 and ema50 and ema50 > 0:
        trend = clamp01((ema20 - ema50) / ema50 * 25)  # 4%면 1
    rsi_s = 0.0
    if rsi14 is not None:
        # 50 중심, 70/30에서 약화
        rsi_s = 1.0 - clamp01(abs(rsi14 - 50) / 25)
    return clamp01(0.6 * trend + 0.4 * rsi_s)


def score_c(st: Dict) -> float:
    # 변동성 확장(ATR/Range)
    atr14 = st.get("atr14")
    last = st.get("last")
    if not atr14 or not last or last <= 0:
        return 0.0
    vol_s = clamp01((atr14 / last) * 120)  # 0.8%면 0.96
    return clamp01(vol_s)


def compute(model: str, st: Dict) -> float:
    m = (model or "SCORE_A").upper()
    if m == "SCORE_A":
        return score_a(st)
    if m == "SCORE_B":
        return score_b(st)
    if m == "SCORE_C":
        return score_c(st)
    return score_a(st)
