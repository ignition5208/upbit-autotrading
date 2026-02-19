from pydantic import BaseModel, Field
from typing import Dict, Any, Literal

RiskMode = Literal["SAFE", "STANDARD", "PROFIT", "CRAZY"]
RunMode = Literal["LIVE", "PAPER"]

class PlatformConfig(BaseModel):
    exchange: Literal["upbit"] = "upbit"
    fee: float = Field(default=0.0005, description="Default trading fee")
    slippage: float = Field(default=0.0005, description="Default slippage model")

class TraderConfig(BaseModel):
    trader_name: str
    strategy: str
    risk_mode: RiskMode
    run_mode: RunMode
    seed_krw: float | None = None

class StrategyConfig(BaseModel):
    name: str
    params: Dict[str, Any] = Field(default_factory=dict)
