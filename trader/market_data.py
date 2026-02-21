"""
Upbit 시장 데이터 조회 유틸.
과호출 방지를 위해 배치 조회 + rate limit + 백오프를 적용한다.
"""
from __future__ import annotations

import os
import random
import threading
import time
from collections import deque
from typing import Dict, Optional

import httpx


UPBIT_TICKER_URL = "https://api.upbit.com/v1/ticker"
UPBIT_ORDERBOOK_URL = "https://api.upbit.com/v1/orderbook"
UPBIT_MARKETS_URL = "https://api.upbit.com/v1/market/all"

# 기본값은 보수적으로 설정 (문서 한도보다 낮게 운용)
_DEFAULT_GROUP_RPS = float(os.getenv("UPBIT_GROUP_RPS", "8.0"))
_CHUNK_SIZE = int(os.getenv("UPBIT_BATCH_CHUNK_SIZE", "70"))
_MAX_RETRY = int(os.getenv("UPBIT_API_MAX_RETRY", "4"))


class _RateLimiter:
    def __init__(self, rate_per_sec: float):
        self.rate_per_sec = max(1.0, float(rate_per_sec))
        self._events = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        while True:
            now = time.monotonic()
            with self._lock:
                # 최근 1초 윈도우 정리
                while self._events and (now - self._events[0]) >= 1.0:
                    self._events.popleft()
                if len(self._events) < int(self.rate_per_sec):
                    self._events.append(now)
                    return
                wait_sec = 1.0 - (now - self._events[0])
            if wait_sec > 0:
                time.sleep(wait_sec)


_group_limiter = {
    "ticker": _RateLimiter(_DEFAULT_GROUP_RPS),
    "orderbook": _RateLimiter(_DEFAULT_GROUP_RPS),
    "market": _RateLimiter(max(2.0, _DEFAULT_GROUP_RPS / 2.0)),
}


def _respect_remaining_req(headers: httpx.Headers) -> None:
    """
    Upbit Remaining-Req 헤더를 읽어 초당 잔여 요청이 낮으면 짧게 휴식.
    예: "group=ticker; min=599; sec=9"
    """
    raw = headers.get("Remaining-Req")
    if not raw:
        return
    try:
        sec_part = [p.strip() for p in raw.split(";") if "sec=" in p]
        if not sec_part:
            return
        sec_left = int(sec_part[0].split("sec=")[1])
        if sec_left <= 0:
            time.sleep(0.35)
        elif sec_left <= 1:
            time.sleep(0.15)
    except Exception:
        return


def _request_with_backoff(url: str, params: dict, group: str, timeout: float = 5.0):
    limiter = _group_limiter.get(group)
    if limiter is None:
        limiter = _group_limiter["ticker"]

    for attempt in range(_MAX_RETRY):
        limiter.acquire()
        try:
            resp = httpx.get(url, params=params, timeout=timeout)
        except Exception:
            backoff = min(2.0, (0.2 * (2 ** attempt))) + random.uniform(0, 0.15)
            time.sleep(backoff)
            continue

        if resp.status_code == 200:
            _respect_remaining_req(resp.headers)
            return resp
        if resp.status_code == 429:
            backoff = min(3.0, (0.25 * (2 ** attempt))) + random.uniform(0, 0.2)
            time.sleep(backoff)
            continue
        if resp.status_code == 418:
            # 일시 차단 대응: 즉시 공격 중단
            time.sleep(3.0 + random.uniform(0, 2.0))
            return None
        # 기타 오류도 짧게 백오프 후 재시도
        backoff = min(1.5, 0.15 * (attempt + 1))
        time.sleep(backoff)
    return None


def _chunks(values: list[str], chunk_size: int) -> list[list[str]]:
    return [values[i:i + chunk_size] for i in range(0, len(values), chunk_size)]


def get_krw_markets(timeout: float = 5.0) -> list[str]:
    resp = _request_with_backoff(
        UPBIT_MARKETS_URL,
        params={"isDetails": "false"},
        group="market",
        timeout=timeout,
    )
    if resp is None:
        return []
    try:
        data = resp.json()
        if not isinstance(data, list):
            return []
        return [d.get("market", "") for d in data if str(d.get("market", "")).startswith("KRW-")]
    except Exception:
        return []


def get_tickers(markets: list[str], timeout: float = 5.0) -> Dict[str, Dict]:
    result: Dict[str, Dict] = {}
    normalized = [m for m in dict.fromkeys(markets) if m]
    if not normalized:
        return result
    for batch in _chunks(normalized, _CHUNK_SIZE):
        resp = _request_with_backoff(
            UPBIT_TICKER_URL,
            params={"markets": ",".join(batch)},
            group="ticker",
            timeout=timeout,
        )
        if resp is None:
            continue
        try:
            data = resp.json()
            if not isinstance(data, list):
                continue
            for item in data:
                market = item.get("market")
                if not market:
                    continue
                result[str(market)] = {
                    "trade_price": float(item.get("trade_price", 0) or 0),
                    "high_price": float(item.get("high_price", 0) or 0),
                    "low_price": float(item.get("low_price", 0) or 0),
                    "acc_trade_volume_24h": float(item.get("acc_trade_volume_24h", 0) or 0),
                    "acc_trade_price_24h": float(item.get("acc_trade_price_24h", 0) or 0),
                }
        except Exception:
            continue
    return result


def get_orderbooks(markets: list[str], timeout: float = 5.0) -> Dict[str, Dict]:
    result: Dict[str, Dict] = {}
    normalized = [m for m in dict.fromkeys(markets) if m]
    if not normalized:
        return result
    for batch in _chunks(normalized, _CHUNK_SIZE):
        resp = _request_with_backoff(
            UPBIT_ORDERBOOK_URL,
            params={"markets": ",".join(batch)},
            group="orderbook",
            timeout=timeout,
        )
        if resp is None:
            continue
        try:
            data = resp.json()
            if not isinstance(data, list):
                continue
            for item in data:
                market = item.get("market")
                units = item.get("orderbook_units") or []
                if not market or not units:
                    continue
                result[str(market)] = {
                    "orderbook_units": units,
                }
        except Exception:
            continue
    return result


def get_ticker(market: str, timeout: float = 5.0) -> Optional[Dict]:
    """
    단일 마켓 ticker 조회.
    내부적으로 batch API를 사용해 동일 레이트 제어 경로를 탄다.
    """
    data = get_tickers([market], timeout=timeout)
    return data.get(market)
