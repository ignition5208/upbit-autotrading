import os
import time
import logging

from trainer.opt.opt_0002_gate import gate_decision
from trainer.opt.opt_0003_tuning import run_tuning
from trainer.deploy.stages import advance_stage

log = logging.getLogger("trainer")

def main():
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    while True:
        # TODO: scan_runs / feature_snapshots 기반으로 후보 생성/평가/튜닝/배포
        decision = gate_decision(metrics={"E": 0.0, "Sharpe": 0.0, "SPD": 0.0})
        log.info("gate decision=%s", decision)
        if decision == "PASS":
            cand = run_tuning()
            advance_stage(cand, target="PAPER_DEPLOYED")
        time.sleep(60)

if __name__ == "__main__":
    main()
