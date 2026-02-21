"""
Score 모듈들 (5개 기법)
지침: TP, VCB, LSR, LF, Regime Modifier
각 모듈은 0-100 정규화 점수 반환
"""
import pyupbit
import pandas as pd
import numpy as np
from typing import Dict, Tuple, List
from datetime import datetime, timedelta


def calculate_ema(prices: np.ndarray, period: int) -> float:
    """EMA 계산"""
    if len(prices) < period:
        return float(np.mean(prices))
    multiplier = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    return float(ema)


def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """ATR 계산"""
    if len(df) < period + 1:
        return 0.0
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    tr_list = []
    for i in range(1, len(df)):
        tr = max(
            high[i] - low[i],
            abs(high[i] - close[i-1]),
            abs(low[i] - close[i-1])
        )
        tr_list.append(tr)
    
    if len(tr_list) < period:
        return 0.0
    
    return float(np.mean(tr_list[-period:]))


# ===== 1. Trend Pullback (TP) =====
def score_trend_pullback(symbol: str, df: pd.DataFrame) -> Tuple[float, List[str], Dict]:
    """
    트렌드 풀백 점수
    - EMA50 > EMA200 (상승 트렌드)
    - 현재가가 EMA50 근처로 풀백
    - 피보나치 되돌림 고려
    """
    if len(df) < 200:
        return 0.0, ["INSUFFICIENT_DATA"], {}
    
    close = df['close'].values
    high = df['high'].values
    low = df['low'].values
    
    ema50 = calculate_ema(close, 50)
    ema200 = calculate_ema(close, 200)
    current_price = close[-1]
    
    reason_codes = []
    raw_metrics = {
        'ema50': ema50,
        'ema200': ema200,
        'current_price': current_price,
    }
    
    # 상승 트렌드 확인
    if ema50 <= ema200:
        return 0.0, ["NO_UPTREND"], raw_metrics
    
    reason_codes.append("UPTREND")
    
    # 피보나치 되돌림 계산
    recent_high = float(np.max(high[-50:]))
    recent_low = float(np.min(low[-50:]))
    fib_range = recent_high - recent_low
    
    if fib_range == 0:
        return 0.0, ["NO_RANGE"], raw_metrics
    
    pullback_pct = (recent_high - current_price) / fib_range
    
    # 0.382 ~ 0.618 피보나치 구간에서 점수 최대
    if 0.3 <= pullback_pct <= 0.7:
        reason_codes.append("FIB_PULLBACK")
        score = 100 - abs(pullback_pct - 0.5) * 200  # 0.5에서 최대
        score = max(0, min(100, score))
    elif pullback_pct < 0.3:
        score = 50 - pullback_pct * 100  # 너무 높음
        score = max(0, score)
    else:
        score = 30  # 너무 깊은 되돌림
    
    raw_metrics['pullback_pct'] = pullback_pct
    raw_metrics['recent_high'] = recent_high
    raw_metrics['recent_low'] = recent_low
    
    return float(score), reason_codes, raw_metrics


# ===== 2. Volatility Contraction Breakout (VCB) =====
def score_volatility_contraction_breakout(symbol: str, df: pd.DataFrame) -> Tuple[float, List[str], Dict]:
    """
    변동성 수축 돌파 점수
    - 볼린저 밴드 수축 후 확장
    - ATR 감소 후 증가
    """
    if len(df) < 50:
        return 0.0, ["INSUFFICIENT_DATA"], {}
    
    close = df['close'].values
    current_price = close[-1]
    
    # 볼린저 밴드
    period = 20
    if len(close) < period:
        return 0.0, ["INSUFFICIENT_DATA"], {}
    
    ma = np.mean(close[-period:])
    std = np.std(close[-period:])
    upper = ma + 2 * std
    lower = ma - 2 * std
    
    # 최근 10일 vs 이전 10일 변동성 비교
    if len(close) < 30:
        return 0.0, ["INSUFFICIENT_DATA"], {}
    
    recent_vol = np.std(close[-10:]) / np.mean(close[-10:])
    prev_vol = np.std(close[-20:-10]) / np.mean(close[-20:-10])
    
    reason_codes = []
    raw_metrics = {
        'bb_upper': float(upper),
        'bb_lower': float(lower),
        'bb_middle': float(ma),
        'current_price': current_price,
        'recent_vol': float(recent_vol),
        'prev_vol': float(prev_vol),
    }
    
    # 변동성 수축 확인
    if prev_vol == 0 or recent_vol / prev_vol > 0.8:
        return 0.0, ["NO_CONTRACTION"], raw_metrics
    
    contraction_ratio = recent_vol / prev_vol
    reason_codes.append("VOL_CONTRACTION")
    
    # 돌파 확인
    if current_price > upper:
        reason_codes.append("BREAKOUT_UP")
        score = 80 + (contraction_ratio < 0.5) * 20  # 수축이 클수록 높은 점수
    elif current_price < lower:
        reason_codes.append("BREAKOUT_DOWN")
        score = 30  # 하향 돌파는 낮은 점수
    else:
        score = 40  # 밴드 내부
    
    raw_metrics['contraction_ratio'] = float(contraction_ratio)
    return float(score), reason_codes, raw_metrics


# ===== 3. Liquidity Sweep Reversal (LSR) =====
def score_liquidity_sweep_reversal(symbol: str, df: pd.DataFrame) -> Tuple[float, List[str], Dict]:
    """
    유동성 스위프 반전 점수
    - 최근 고점/저점 돌파 후 즉시 반전
    - 긴 꼬리 캔들 패턴
    """
    if len(df) < 20:
        return 0.0, ["INSUFFICIENT_DATA"], {}
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    open_price = df['open'].values
    
    recent_high = float(np.max(high[-20:]))
    recent_low = float(np.min(low[-20:]))
    current_price = close[-1]
    
    reason_codes = []
    raw_metrics = {
        'recent_high': recent_high,
        'recent_low': recent_low,
        'current_price': current_price,
    }
    
    # 최근 캔들 분석
    last_candle_high = high[-1]
    last_candle_low = low[-1]
    last_candle_body = abs(close[-1] - open_price[-1])
    last_candle_range = last_candle_high - last_candle_low
    
    if last_candle_range == 0:
        return 0.0, ["NO_RANGE"], raw_metrics
    
    # 꼬리 비율 (위꼬리 + 아래꼬리)
    upper_wick = last_candle_high - max(close[-1], open_price[-1])
    lower_wick = min(close[-1], open_price[-1]) - last_candle_low
    wick_ratio = (upper_wick + lower_wick) / last_candle_range
    
    raw_metrics['wick_ratio'] = float(wick_ratio)
    
    # 고점 스위프 후 반전
    if last_candle_high > recent_high * 0.99 and close[-1] < open_price[-1]:
        if wick_ratio > 0.5:  # 긴 위꼬리
            reason_codes.append("SWEEP_HIGH_REVERSAL")
            score = 75
        else:
            score = 40
    # 저점 스위프 후 반전
    elif last_candle_low < recent_low * 1.01 and close[-1] > open_price[-1]:
        if wick_ratio > 0.5:  # 긴 아래꼬리
            reason_codes.append("SWEEP_LOW_REVERSAL")
            score = 80
        else:
            score = 45
    else:
        score = 30
    
    return float(score), reason_codes, raw_metrics


# ===== 4. Leader-Follower (LF) =====
def score_leader_follower(symbol: str, df: pd.DataFrame, btc_df: pd.DataFrame = None) -> Tuple[float, List[str], Dict]:
    """
    리더-팔로워 점수
    - BTC 대비 상대 강도
    - BTC 상승 시 더 강한 상승
    """
    if len(df) < 20:
        return 0.0, ["INSUFFICIENT_DATA"], {}
    
    close = df['close'].values
    current_price = close[-1]
    
    # BTC 데이터가 없으면 기본 점수
    if btc_df is None or len(btc_df) < 20:
        return 50.0, ["NO_BTC_DATA"], {'current_price': current_price}
    
    btc_close = btc_df['close'].values
    
    # 최근 20일 수익률 비교
    symbol_return = (current_price / close[-20] - 1) * 100
    btc_return = (btc_close[-1] / btc_close[-20] - 1) * 100
    
    relative_strength = symbol_return - btc_return
    
    reason_codes = []
    raw_metrics = {
        'symbol_return': float(symbol_return),
        'btc_return': float(btc_return),
        'relative_strength': float(relative_strength),
    }
    
    # BTC가 상승 중이고 심볼이 더 강함
    if btc_return > 0 and relative_strength > 5:
        reason_codes.append("OUTPERFORM_BTC")
        score = 70 + min(relative_strength, 30)  # 최대 100
    # BTC가 하락 중이지만 심볼이 상대적으로 강함
    elif btc_return < 0 and relative_strength > 0:
        reason_codes.append("RESILIENT")
        score = 60 + min(relative_strength * 2, 30)
    # BTC 대비 약함
    else:
        score = max(0, 50 + relative_strength)
    
    return float(score), reason_codes, raw_metrics


# ===== 5. Regime Modifier (Global) =====
def score_regime_modifier(regime_label: str, regime_confidence: float) -> Tuple[float, List[str], Dict]:
    """
    레짐 수정자 점수
    - 레짐에 따라 전체 점수에 가중치 적용
    """
    raw_metrics = {
        'regime': regime_label,
        'confidence': float(regime_confidence),
    }
    
    # 레짐별 기본 점수
    regime_scores = {
        "BREAKOUT_ROTATION": 85,
        "TREND": 80,
        "RANGE": 60,
        "CHOP": 30,
        "PANIC": 10,
    }
    
    base_score = regime_scores.get(regime_label, 50)
    
    # 신뢰도에 따라 조정
    score = base_score * regime_confidence
    
    reason_codes = [f"REGIME_{regime_label}"]
    if regime_confidence > 0.8:
        reason_codes.append("HIGH_CONFIDENCE")
    
    return float(score), reason_codes, raw_metrics
