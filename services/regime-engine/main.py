import os, time, random
import httpx

BASE = os.getenv("DASHBOARD_API_BASE","http://dashboard-api:8000")
MARKET = os.getenv("MARKET","KRW-BTC")
INTERVAL = float(os.getenv("INTERVAL_SEC","5"))

REGIMES = [(0,"Neutral"),(1,"Bull"),(2,"Bear"),(3,"Sideways")]

while True:
  rid, label = random.choice(REGIMES)
  conf = random.random()*0.5 + 0.5
  metrics = {"close": random.randint(1_000_000, 100_000_000), "vol_5m": random.random()/100}
  try:
    httpx.post(f"{BASE}/api/regimes/snapshot", json={
      "market": MARKET, "regime_id": rid, "regime_label": label, "confidence": conf, "metrics": metrics
    }, timeout=5.0)
    print(f"[regime-engine] {MARKET} {label} conf={conf:.2f}")
  except Exception as e:
    print("[regime-engine] error:", e)
  time.sleep(INTERVAL)
