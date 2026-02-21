import os, subprocess, logging
from sqlalchemy.orm import Session
from app.models import Trader
from app.services.events import add_event

log = logging.getLogger("orchestrator")
TRADER_IMAGE = os.getenv("TRADER_IMAGE", "upbit-trader:latest")

def _docker(*args: str) -> tuple[int,str,str]:
    p = subprocess.Popen(["docker", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    out, err = p.communicate()
    return p.returncode, out.strip(), err.strip()

def ensure_trader_container(db: Session, trader: Trader, run_mode: str):
    cname = f"ats-trader-{trader.name}"
    _docker("rm","-f",cname)
    env = [
        "-e", f"TRADER_NAME={trader.name}",
        "-e", f"STRATEGY={trader.strategy}",
        "-e", f"RISK_MODE={trader.risk_mode}",
        "-e", f"RUN_MODE={run_mode}",
        "-e", f"CREDENTIAL_NAME={trader.credential_name or ''}",
        "-e", "DASHBOARD_API_BASE=http://dashboard-api:8000",
    ]
    code, out, err = _docker("run","-d","--name",cname, *env, TRADER_IMAGE)
    if code != 0:
        trader.status = "ERROR"
        add_event(db, trader.name, "ERROR", "trader", f"docker run failed: {err or out}")
        db.commit()
        raise RuntimeError(err or out)

    trader.status = "RUN"
    trader.run_mode = run_mode
    trader.container_name = cname
    add_event(db, trader.name, "INFO", "trader", f"started {cname} ({run_mode})")
    db.commit()

def stop_trader_container(db: Session, trader: Trader):
    cname = trader.container_name or f"ats-trader-{trader.name}"
    _docker("stop", cname)
    trader.status = "STOP"
    add_event(db, trader.name, "INFO", "trader", f"stopped {cname}")
    db.commit()

def remove_trader_container(db: Session, trader: Trader):
    cname = trader.container_name or f"ats-trader-{trader.name}"
    _docker("rm","-f", cname)
    add_event(db, trader.name, "INFO", "trader", f"removed {cname}")
    db.commit()
