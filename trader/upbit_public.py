from __future__ import annotations

import requests

BASE = "https://api.upbit.com"


def market_all() -> list[dict]:
    r = requests.get(f"{BASE}/v1/market/all", params={"isDetails": "false"}, timeout=10)
    r.raise_for_status()
    return r.json()


def ticker(markets: list[str]) -> list[dict]:
    r = requests.get(f"{BASE}/v1/ticker", params={"markets": ",".join(markets)}, timeout=10)
    r.raise_for_status()
    return r.json()


def orderbook(markets: list[str]) -> list[dict]:
    r = requests.get(f"{BASE}/v1/orderbook", params={"markets": ",".join(markets)}, timeout=10)
    r.raise_for_status()
    return r.json()


def candles_minutes(market: str, unit: int, count: int = 60) -> list[dict]:
    r = requests.get(
        f"{BASE}/v1/candles/minutes/{unit}",
        params={"market": market, "count": count},
        timeout=10,
    )
    r.raise_for_status()
    return r.json()
