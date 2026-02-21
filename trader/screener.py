"""
Screener 모듈
지침: 전체 마켓 → 후보(예: top N 거래대금) 필터링
"""
import pyupbit
from typing import List, Dict
from datetime import datetime


def get_all_krw_markets() -> List[str]:
    """모든 KRW 마켓 리스트 가져오기"""
    try:
        markets = pyupbit.get_tickers(fiat="KRW")
        return markets
    except Exception as e:
        print(f"[screener] Error fetching markets: {e}")
        return []


def screen_markets(
    top_n: int = 30,
    min_24h_volume: float = 100_000_000,  # 최소 24시간 거래대금 (1억원)
    max_spread_pct: float = 0.5,  # 최대 스프레드 0.5%
) -> List[Dict]:
    """
    마켓 스크리닝
    
    Returns:
        [{
            'symbol': 'KRW-BTC',
            '24h_volume': float,
            'spread': float,
            'avg_depth5': float,
            'volatility': float,
            'reason_flags': List[str]
        }]
    """
    markets = get_all_krw_markets()
    candidates = []
    
    for market in markets:
        try:
            # 24시간 거래대금
            ticker = pyupbit.get_ticker(market)
            if not ticker:
                continue
            
            volume_24h = ticker.get('acc_trade_volume_24h', 0) * ticker.get('trade_price', 0)
            if volume_24h < min_24h_volume:
                continue
            
            # 현재가, 매수/매도 호가
            orderbook = pyupbit.get_orderbook(market)
            if not orderbook or not orderbook.get('orderbook_units'):
                continue
            
            bids = orderbook['orderbook_units'][:5]  # 상위 5개 매수 호가
            asks = orderbook['orderbook_units'][:5]  # 상위 5개 매도 호가
            
            best_bid = bids[0]['bid_price'] if bids else 0
            best_ask = asks[0]['ask_price'] if asks else 0
            
            if best_bid == 0 or best_ask == 0:
                continue
            
            current_price = ticker.get('trade_price', best_bid)
            spread = (best_ask - best_bid) / current_price * 100 if current_price > 0 else 999
            
            if spread > max_spread_pct:
                continue
            
            # 평균 depth (상위 5개 호가 합계)
            avg_depth5 = (sum(b['bid_size'] * b['bid_price'] for b in bids) +
                         sum(a['ask_size'] * a['ask_price'] for a in asks)) / 2
            
            # 변동성 (간단히 24시간 고저 차이)
            high_24h = ticker.get('high_price', current_price)
            low_24h = ticker.get('low_price', current_price)
            volatility = (high_24h - low_24h) / current_price * 100 if current_price > 0 else 0
            
            # Reason flags
            reason_flags = []
            if volume_24h > min_24h_volume * 5:
                reason_flags.append("HIGH_VOLUME")
            if spread < max_spread_pct * 0.5:
                reason_flags.append("TIGHT_SPREAD")
            if avg_depth5 > volume_24h * 0.01:
                reason_flags.append("GOOD_DEPTH")
            
            candidates.append({
                'symbol': market,
                '24h_volume': volume_24h,
                'spread': spread,
                'avg_depth5': avg_depth5,
                'volatility': volatility,
                'current_price': current_price,
                'reason_flags': reason_flags,
            })
        except Exception as e:
            print(f"[screener] Error processing {market}: {e}")
            continue
    
    # 거래대금 순으로 정렬 후 top_n 반환
    candidates.sort(key=lambda x: x['24h_volume'], reverse=True)
    return candidates[:top_n]
