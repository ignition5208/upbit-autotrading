"""
Upbit 시장 데이터 조회 유틸
pyupbit 버전 차이에 영향받지 않도록 REST ticker API를 직접 사용한다.
"""
from typing import Dict, Optional
import httpx


UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker"


def get_ticker(market: str, timeout: float = 5.0) -> Optional[Dict]:
    """
    단일 마켓 ticker 조회.

    Returns:
        {
          "trade_price": float,
          "high_price": float,
          "low_price": float,
          "acc_trade_volume_24h": float,
          "acc_trade_price_24h": float,
        }
    """
    try:
        resp = httpx.get(UPBIT_TICKER_URL, params={"markets": market}, timeout=timeout)
        if resp.status_code != 200:
            return None
        data = resp.json()
        if not data or not isinstance(data, list):
            return None
        item = data[0]
        return {
            "trade_price": float(item.get("trade_price", 0) or 0),
            "high_price": float(item.get("high_price", 0) or 0),
            "low_price": float(item.get("low_price", 0) or 0),
            "acc_trade_volume_24h": float(item.get("acc_trade_volume_24h", 0) or 0),
            "acc_trade_price_24h": float(item.get("acc_trade_price_24h", 0) or 0),
        }
    except Exception:
        return None
