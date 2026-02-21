"""
OPT-0001 데이터 파이프라인 구현
실제 데이터 수집 및 라벨 계산
"""
import json
import pyupbit
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict
from sqlalchemy.orm import Session
from app.models import ScanRun, FeatureSnapshot


def calculate_labels(
    entry_price: float,
    current_price: float,
    high_price: float,
    low_price: float,
    entry_time: datetime,
    current_time: datetime,
) -> Dict[str, float]:
    """
    라벨 계산
    
    Returns:
        {
            'label_ret_60m': float,
            'label_ret_240m': float,
            'label_mfe_240m': float,
            'label_mae_240m': float,
            'label_dd_240m': float,
        }
    """
    if entry_price == 0:
        return {}
    
    time_diff = (current_time - entry_time).total_seconds() / 60  # 분 단위
    
    # 수익률 계산
    ret = (current_price - entry_price) / entry_price
    
    # 60분, 240분 수익률 (시간대별로 계산)
    ret_60m = ret if time_diff >= 60 else None
    ret_240m = ret if time_diff >= 240 else None
    
    # MFE (Maximum Favorable Excursion) - 최대 유리한 가격 변동
    mfe_240m = (high_price - entry_price) / entry_price if time_diff >= 240 else None
    
    # MAE (Maximum Adverse Excursion) - 최대 불리한 가격 변동
    mae_240m = (entry_price - low_price) / entry_price if time_diff >= 240 else None
    
    # DD (Drawdown) - 최대 낙폭
    dd_240m = (low_price - entry_price) / entry_price if time_diff >= 240 else None
    
    return {
        'label_ret_60m': ret_60m,
        'label_ret_240m': ret_240m,
        'label_mfe_240m': mfe_240m,
        'label_mae_240m': mae_240m,
        'label_dd_240m': dd_240m,
    }


def collect_market_data(markets: List[str], count: int = 200) -> Dict[str, pd.DataFrame]:
    """시장 데이터 수집"""
    data = {}
    for market in markets:
        try:
            df = pyupbit.get_ohlcv(market, interval="minute60", count=count)
            if df is not None and not df.empty:
                data[market] = df
        except Exception as e:
            print(f"Error collecting {market}: {e}")
            continue
    return data


def calculate_features(df: pd.DataFrame) -> Dict:
    """
    Feature 계산 (예시)
    실제 전략에 따라 다르게 구현 필요
    """
    if df.empty or len(df) < 20:
        return {}
    
    close = df['close'].values
    volume = df['volume'].values
    high = df['high'].values
    low = df['low'].values
    
    # 간단한 기술적 지표들
    features = {
        'price': float(close[-1]),
        'volume_ma_20': float(np.mean(volume[-20:])) if len(volume) >= 20 else 0.0,
        'rsi_14': calculate_rsi(close, 14),
        'macd': calculate_macd(close),
        'bb_upper': calculate_bollinger_upper(close, 20),
        'bb_lower': calculate_bollinger_lower(close, 20),
    }
    
    return features


def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """RSI 계산"""
    if len(prices) < period + 1:
        return 50.0
    
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)
    
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        return 100.0
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return float(rsi)


def calculate_macd(prices: np.ndarray) -> float:
    """MACD 계산 (간단화)"""
    if len(prices) < 26:
        return 0.0
    
    ema12 = calculate_ema(prices, 12)
    ema26 = calculate_ema(prices, 26)
    macd = ema12 - ema26
    return float(macd)


def calculate_ema(prices: np.ndarray, period: int) -> float:
    """EMA 계산"""
    if len(prices) < period:
        return float(np.mean(prices))
    
    multiplier = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = (price - ema) * multiplier + ema
    return float(ema)


def calculate_bollinger_upper(prices: np.ndarray, period: int = 20, std_dev: int = 2) -> float:
    """볼린저 밴드 상단"""
    if len(prices) < period:
        return float(prices[-1])
    
    ma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    return float(ma + std_dev * std)


def calculate_bollinger_lower(prices: np.ndarray, period: int = 20, std_dev: int = 2) -> float:
    """볼린저 밴드 하단"""
    if len(prices) < period:
        return float(prices[-1])
    
    ma = np.mean(prices[-period:])
    std = np.std(prices[-period:])
    return float(ma - std_dev * std)


def run_scan(
    db: Session,
    strategy_id: str,
    markets: List[str],
    top_n: int = 5,
    params: Dict = None,
) -> ScanRun:
    """
    스캔 실행 및 데이터 수집
    
    Returns:
        ScanRun 객체
    """
    scan_run = ScanRun(
        strategy_id=strategy_id,
        market_count=len(markets),
        top_n=top_n,
        params_json=json.dumps(params or {}),
        ts=datetime.utcnow(),
    )
    db.add(scan_run)
    db.flush()  # ID 생성
    
    # 시장 데이터 수집
    market_data = collect_market_data(markets)
    
    # 각 마켓에 대해 Feature 계산 및 저장
    for market, df in market_data.items():
        features = calculate_features(df)
        
        snapshot = FeatureSnapshot(
            scan_run_id=scan_run.id,
            market=market,
            ts=datetime.utcnow(),
            features_json=json.dumps(features),
        )
        db.add(snapshot)
    
    db.commit()
    return scan_run
