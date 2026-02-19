import os
import time
import logging

from trader.runtime.context import TraderContext
from trader.runtime.loop import run_loop
from trader.events.emitter import EventEmitter

log = logging.getLogger("trader")

def main():
    ctx = TraderContext.from_env()
    emitter = EventEmitter(trader_name=ctx.trader_name)
    emitter.info("BOOT", f"Trader starting: {ctx.trader_name} {ctx.run_mode}/{ctx.risk_mode} strategy={ctx.strategy}")
    while True:
        try:
            run_loop(ctx, emitter)
        except Exception as e:
            emitter.critical("LOOP_ERROR", str(e))
            time.sleep(2)

if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    main()
