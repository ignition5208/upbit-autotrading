"""
Regime Engine 지표 계산 모듈
지침 4.2에 명시된 6개 지표 계산
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional


def calculate_adx(df: pd.DataFrame, period: int = 14) -> float:
    """ADX (Average Directional Index) 계산"""
    if len(df) < period + 1:
        return 0.0
    
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    
    # True Range 계산
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
    
    # ATR 계산
    atr = np.mean(tr_list[-period:])
    
    # Directional Movement 계산
    plus_dm = []
    minus_dm = []
    for i in range(1, len(df)):
        up_move = high[i] - high[i-1]
        down_move = low[i-1] - low[i]
        
        if up_move > down_move and up_move > 0:
            plus_dm.append(up_move)
        else:
            plus_dm.append(0)
            
        if down_move > up_move and down_move > 0:
            minus_dm.append(down_move)
        else:
            minus_dm.append(0)
    
    if len(plus_dm) < period:
        return 0.0
    
    plus_di = 100 * (np.mean(plus_dm[-period:]) / atr) if atr > 0 else 0
    minus_di = 100 * (np.mean(minus_dm[-period:]) / atr) if atr > 0 else 0
    
    # DX 계산
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
    
    # ADX는 DX의 이동평균 (간단화: 최근 period개 평균)
    if len(tr_list) >= period * 2:
        dx_values = []
        for i in range(period, len(df) - 1):
            # 각 시점의 DX 계산 (간단화)
            dx_val = dx  # 실제로는 각 시점마다 계산해야 함
            dx_values.append(dx_val)
        if dx_values:
            adx = np.mean(dx_values[-period:])
        else:
            adx = dx
    else:
        adx = dx
    
    return float(adx)


def calculate_atr_pct(df: pd.DataFrame, period: int = 14) -> float:
    """ATR 퍼센트 계산 (ATR / Close * 100)"""
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
    
    atr = np.mean(tr_list[-period:])
    current_close = close[-1]
    
    if current_close == 0:
        return 0.0
    
    atr_pct = (atr / current_close) * 100
    return float(atr_pct)


def calculate_breadth_up(markets_data: List[Dict], timeframe: str = '1h') -> float:
    """상승 종목 비율 계산 (breadth_up_1h)"""
    if not markets_data:
        return 0.0
    
    up_count = 0
    total_count = 0
    
    for market_data in markets_data:
        if 'candles' not in market_data or len(market_data['candles']) < 2:
            continue
        
        candles = market_data['candles']
        if len(candles) < 2:
            continue
        
        prev_close = candles[-2].get('trade_price', 0)
        curr_close = candles[-1].get('trade_price', 0)
        
        if prev_close > 0:
            total_count += 1
            if curr_close > prev_close:
                up_count += 1
    
    if total_count == 0:
        return 0.0
    
    return float(up_count / total_count)


def calculate_dispersion(markets_data: List[Dict], timeframe: str = '1h') -> float:
    """분산도 계산 (dispersion_1h) - 수익률의 표준편차"""
    if not markets_data:
        return 0.0
    
    returns = []
    
    for market_data in markets_data:
        if 'candles' not in market_data or len(market_data['candles']) < 2:
            continue
        
        candles = market_data['candles']
        if len(candles) < 2:
            continue
        
        prev_close = candles[-2].get('trade_price', 0)
        curr_close = candles[-1].get('trade_price', 0)
        
        if prev_close > 0:
            ret = (curr_close - prev_close) / prev_close
            returns.append(ret)
    
    if len(returns) < 2:
        return 0.0
    
    return float(np.std(returns))


def calculate_top5_value_share(markets_data: List[Dict], timeframe: str = '1h') -> float:
    """상위 5개 코인 시가총액 비중 계산"""
    if not markets_data:
        return 0.0
    
    market_values = []
    
    for market_data in markets_data:
        if 'candles' not in market_data or len(market_data['candles']) < 1:
            continue
        
        candle = market_data['candles'][-1]
        close_price = candle.get('trade_price', 0)
        volume = candle.get('candle_acc_trade_volume', 0)
        
        # 시가총액 근사치 (가격 * 거래량)
        market_value = close_price * volume
        market_values.append({
            'market': market_data.get('market', ''),
            'value': market_value
        })
    
    if len(market_values) < 5:
        return 0.0
    
    # 시가총액 순으로 정렬
    market_values.sort(key=lambda x: x['value'], reverse=True)
    
    top5_value = sum(m['value'] for m in market_values[:5])
    total_value = sum(m['value'] for m in market_values)
    
    if total_value == 0:
        return 0.0
    
    return float(top5_value / total_value)


def calculate_whipsaw(df: pd.DataFrame, period: int = 5) -> float:
    """휩소 지표 계산 (whipsaw_5m) - 방향 전환 빈도"""
    if len(df) < period * 2:
        return 0.0
    
    close = df['close'].values
    
    direction_changes = 0
    for i in range(period, len(df)):
        # 최근 period개 봉의 방향 확인
        recent_closes = close[i-period:i+1]
        directions = []
        
        for j in range(1, len(recent_closes)):
            if recent_closes[j] > recent_closes[j-1]:
                directions.append(1)  # 상승
            elif recent_closes[j] < recent_closes[j-1]:
                directions.append(-1)  # 하락
            else:
                directions.append(0)  # 횡보
        
        # 방향 전환 횟수 계산
        for k in range(1, len(directions)):
            if directions[k] != directions[k-1] and directions[k] != 0 and directions[k-1] != 0:
                direction_changes += 1
    
    # 정규화 (최근 period*2개 봉 기준)
    max_changes = period * 2
    whipsaw_score = min(direction_changes / max_changes if max_changes > 0 else 0, 1.0)
    
    return float(whipsaw_score)


def calculate_regime_score(indicators: Dict[str, float]) -> tuple[int, str, float]:
    """
    지표를 기반으로 Regime 분류 및 점수 계산
    
    Returns:
        (regime_id, regime_label, confidence)
    """
    adx = indicators.get('btc_adx_4h', 0)
    atr_pct = indicators.get('btc_atr_pct_4h', 0)
    breadth_up = indicators.get('breadth_up_1h', 0)
    dispersion = indicators.get('dispersion_1h', 0)
    top5_share = indicators.get('top5_value_share_1h', 0)
    whipsaw = indicators.get('whipsaw_5m', 0)
    
    # PANIC 감지 (높은 변동성 + 낮은 상승 비율)
    if atr_pct > 5.0 and breadth_up < 0.3:
        return (3, "PANIC", 0.8)
    
    # CHOP 감지 (높은 휩소 + 낮은 ADX)
    if whipsaw > 0.6 and adx < 20:
        return (2, "CHOP", 0.7)
    
    # TREND 감지 (높은 ADX + 낮은 휩소)
    if adx > 25 and whipsaw < 0.3:
        if breadth_up > 0.6:
            return (1, "TREND", 0.75)
        else:
            return (1, "TREND", 0.65)
    
    # BREAKOUT_ROTATION 감지 (높은 분산도 + 높은 상위 5개 비중 변화)
    if dispersion > 0.05 and top5_share < 0.4:
        return (4, "BREAKOUT_ROTATION", 0.7)
    
    # 기본값: RANGE
    confidence = 0.6
    if adx < 20 and whipsaw < 0.5:
        confidence = 0.7
    
    return (0, "RANGE", confidence)
