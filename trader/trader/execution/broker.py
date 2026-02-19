from trader.execution.paper import enter as paper_enter
from trader.execution.live import enter as live_enter

class ExecutionBroker:
    def __init__(self, ctx):
        self.ctx = ctx

    def maybe_enter(self, pick: dict, regime: dict, bandit_weight: float):
        payload = {
            "market": pick["market"],
            "final_score": pick["final_score"],
            "evidence": pick["evidence"],
            "regime": regime,
            "bandit_weight": bandit_weight,
            "run_mode": self.ctx.run_mode,
        }
        if self.ctx.run_mode == "LIVE":
            return live_enter(payload)
        return paper_enter(payload)
