import os, time
from datetime import datetime
import httpx

NAME = os.getenv("TRADER_NAME","trader")
BASE = os.getenv("DASHBOARD_API_BASE","http://dashboard-api:8000")
INTERVAL = 5

print(f"[trader] starting {NAME}")
while True:
  try:
    httpx.post(f"{BASE}/api/events", json={
      "trader_name": NAME,
      "level": "INFO",
      "kind": "heartbeat",
      "message": datetime.utcnow().isoformat()
    }, timeout=5.0)
  except Exception as e:
    print("[trader] heartbeat error:", e)
  time.sleep(INTERVAL)
