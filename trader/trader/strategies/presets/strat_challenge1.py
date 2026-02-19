from trader.strategies.base import Strategy, Pick, StrategyRegistry
from trader.market.universe import select_universe

class Challenge1(Strategy):
    name = "challenge1"
    score_threshold = 10.0

    def scan_and_score(self, regime: dict):
        items = []
        for m in select_universe():
            # TODO: 실제 feature 기반 base_score 계산
            base = 12.0
            items.append(Pick(market=m, base_score=base, evidence={"regime": regime["label"]}))
        return items

StrategyRegistry.register(Challenge1())
