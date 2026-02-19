import os
from dataclasses import dataclass

@dataclass
class TraderContext:
    trader_name: str
    strategy: str
    risk_mode: str
    run_mode: str
    seed_krw: float | None = None

    @staticmethod
    def from_env() -> "TraderContext":
        return TraderContext(
            trader_name=os.getenv("TRADER_NAME", "trader-1"),
            strategy=os.getenv("STRATEGY", "challenge1"),
            risk_mode=os.getenv("RISK_MODE", "STANDARD"),
            run_mode=os.getenv("RUN_MODE", "PAPER"),
            seed_krw=float(os.getenv("SEED_KRW", "0") or 0) or None,
        )
