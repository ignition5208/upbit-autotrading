import time
from trader.strategies.base import StrategyRegistry
from trader.regime.engine import RegimeEngine
from trader.bandit.weights import BanditWeightEngine
from trader.safety.runtime_guard import RuntimeGuard
from trader.execution.broker import ExecutionBroker

SCAN_INTERVAL_SEC = 5

def run_loop(ctx, emitter):
    # 1) 안전장치 체크
    guard = RuntimeGuard(ctx.trader_name)
    if not guard.allow_new_entry():
        emitter.warn("GUARD_BLOCK", "New entry blocked by runtime guard")
        time.sleep(SCAN_INTERVAL_SEC)
        return

    # 2) 레짐 산출
    regime = RegimeEngine().current_regime()
    if regime["label"] in ("CHOP", "PANIC"):
        emitter.info("REGIME_BLOCK", f"Regime={regime['label']} 신규진입 금지")
        time.sleep(SCAN_INTERVAL_SEC)
        return

    # 3) 전략 점수
    strat = StrategyRegistry.get(ctx.strategy)
    picks = strat.scan_and_score(regime=regime)

    # 4) 밴딧 가중치
    bw = BanditWeightEngine().weight_for(regime["label"], ctx.strategy)

    # 5) 최종 스코어(스켈레톤)
    # final = base_score * regime_weight * bandit_weight * risk_multiplier
    best = strat.select_best(picks, bandit_weight=bw, regime=regime)

    if not best:
        emitter.info("NO_PICK", "No candidate met threshold")
        time.sleep(SCAN_INTERVAL_SEC)
        return

    # 6) 실행(LIVE/PAPER)
    broker = ExecutionBroker(ctx)
    broker.maybe_enter(best, regime=regime, bandit_weight=bw)

    time.sleep(SCAN_INTERVAL_SEC)
