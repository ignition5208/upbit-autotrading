"""
Regime Engine v1.0
지침 4.2에 명시된 6개 지표를 계산하여 Regime 분류
"""
import os
import time
import json
import httpx
import pyupbit
import pandas as pd
from datetime import datetime, timedelta
from indicators import (
    calculate_adx,
    calculate_atr_pct,
    calculate_breadth_up,
    calculate_dispersion,
    calculate_top5_value_share,
    calculate_whipsaw,
    calculate_regime_score,
)

BASE = os.getenv("DASHBOARD_API_BASE", "http://dashboard-api:8000")
MARKET = os.getenv("MARKET", "KRW-BTC")
INTERVAL = float(os.getenv("INTERVAL_SEC", "300"))  # 기본 5분

# 주요 코인 리스트 (시가총액 상위)
MAJOR_MARKETS = [
    "KRW-BTC", "KRW-ETH", "KRW-XRP", "KRW-ADA", "KRW-DOT",
    "KRW-DOGE", "KRW-SOL", "KRW-MATIC", "KRW-AVAX", "KRW-LINK",
    "KRW-ATOM", "KRW-ETC", "KRW-LTC", "KRW-BCH", "KRW-NEAR",
]


def fetch_candles(market: str, interval: str = "minute240", count: int = 200) -> pd.DataFrame:
    """Upbit에서 캔들 데이터 가져오기"""
    try:
        df = pyupbit.get_ohlcv(market, interval=interval, count=count)
        if df is None or df.empty:
            return pd.DataFrame()
        return df
    except Exception as e:
        print(f"[regime-engine] Error fetching {market} {interval}: {e}")
        return pd.DataFrame()


def fetch_multiple_markets_candles(markets: list, interval: str = "minute60", count: int = 24) -> list:
    """여러 마켓의 캔들 데이터 가져오기"""
    results = []
    for market in markets:
        try:
            df = pyupbit.get_ohlcv(market, interval=interval, count=count)
            if df is not None and not df.empty:
                # DataFrame을 dict 형태로 변환
                candles = []
                for idx, row in df.iterrows():
                    candles.append({
                        'trade_price': float(row['close']),
                        'candle_acc_trade_volume': float(row['volume']),
                    })
                results.append({
                    'market': market,
                    'candles': candles
                })
        except Exception as e:
            print(f"[regime-engine] Error fetching {market}: {e}")
            continue
        time.sleep(0.1)  # API rate limit 방지
    return results


def calculate_all_indicators() -> dict:
    """모든 지표 계산"""
    indicators = {}
    
    # BTC 4시간봉 데이터 (ADX, ATR 계산용)
    btc_4h = fetch_candles("KRW-BTC", interval="minute240", count=200)
    if not btc_4h.empty:
        indicators['btc_adx_4h'] = calculate_adx(btc_4h, period=14)
        indicators['btc_atr_pct_4h'] = calculate_atr_pct(btc_4h, period=14)
    
    # 1시간봉 데이터 (breadth, dispersion, top5 계산용)
    markets_1h = fetch_multiple_markets_candles(MAJOR_MARKETS, interval="minute60", count=24)
    if markets_1h:
        indicators['breadth_up_1h'] = calculate_breadth_up(markets_1h, timeframe='1h')
        indicators['dispersion_1h'] = calculate_dispersion(markets_1h, timeframe='1h')
        indicators['top5_value_share_1h'] = calculate_top5_value_share(markets_1h, timeframe='1h')
    
    # BTC 5분봉 데이터 (whipsaw 계산용)
    btc_5m = fetch_candles("KRW-BTC", interval="minute5", count=100)
    if not btc_5m.empty:
        indicators['whipsaw_5m'] = calculate_whipsaw(btc_5m, period=5)
    
    return indicators


def main():
    print(f"[regime-engine] Starting Regime Engine v1.0")
    print(f"[regime-engine] Market: {MARKET}, Interval: {INTERVAL}s")
    
    while True:
        try:
            # 지표 계산
            indicators = calculate_all_indicators()
            
            # Regime 분류
            regime_id, regime_label, confidence = calculate_regime_score(indicators)
            
            # 메트릭스에 지표 포함
            metrics = {
                **indicators,
                "close": float(pyupbit.get_current_price("KRW-BTC") or 0),
            }
            
            # API로 전송
            response = httpx.post(
                f"{BASE}/api/regimes/snapshot",
                json={
                    "market": MARKET,
                    "regime_id": regime_id,
                    "regime_label": regime_label,
                    "confidence": confidence,
                    "metrics": metrics,
                },
                timeout=10.0,
            )
            
            if response.status_code == 200:
                print(
                    f"[regime-engine] {MARKET} {regime_label} "
                    f"(conf={confidence:.2f}, ADX={indicators.get('btc_adx_4h', 0):.1f})"
                )
            else:
                print(f"[regime-engine] API error: {response.status_code}")
                
        except Exception as e:
            print(f"[regime-engine] Error: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
