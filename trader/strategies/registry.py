from __future__ import annotations

from typing import Callable, Dict

from .base import StrategyResult
from .buy.breakout_volume import evaluate as buy_breakout_volume
from .buy.ma_pullback import evaluate as buy_ma_pullback
from .buy.volatility_breakout import evaluate as buy_volatility_breakout
from .buy.rsi_momentum import evaluate as buy_rsi_momentum

BUY_REGISTRY: Dict[str, Callable[..., StrategyResult]] = {
    "breakout_volume": buy_breakout_volume,
    "ma_pullback": buy_ma_pullback,
    "volatility_breakout": buy_volatility_breakout,
    "rsi_momentum": buy_rsi_momentum,
}


def eval_buy(name: str, market_state: dict, cfg: dict) -> StrategyResult:
    fn = BUY_REGISTRY.get(name)
    if not fn:
        # unknown plugin => hold
        from .base import Signal
        return StrategyResult(Signal.HOLD, None, f"unknown_plugin:{name}", {"symbol": market_state.get("symbol")})
    return fn(market_state, cfg)
