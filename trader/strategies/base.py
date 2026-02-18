from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class Signal(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class OrderIntent:
    type: str  # MARKET/LIMIT
    side: str  # bid/ask
    qty: Optional[float] = None
    krw_amount: Optional[float] = None
    price: Optional[float] = None


@dataclass
class StrategyResult:
    signal: Signal
    order_intent: Optional[OrderIntent]
    reason: str
    evidence: Dict[str, Any]
