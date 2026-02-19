from fastapi import APIRouter

from app.routers import metrics, traders, models, regimes, bandit, events, configs

router = APIRouter(tags=["api-aliases"])

# ---- Overview ----
@router.get("/api/overview")
def api_overview():
    # Must return JSON (NO redirect)
    return metrics.overview()

# ---- Traders ----
@router.get("/api/traders")
def api_traders():
    return traders.list_traders()

@router.post("/api/traders")
def api_create_trader(req: traders.TraderCreateRequest):
    return traders.create_trader(req)

@router.delete("/api/traders/{trader_name}")
def api_delete_trader(trader_name: str):
    return traders.delete_trader(trader_name)

# ---- Optional: pass-through aliases if dashboard-web calls these ----
@router.get("/api/models")
def api_models():
    # if models router already has a handler you can call similarly
    # for now safe placeholder; replace with real call when implemented
    return {"items": []}

@router.get("/api/regimes")
def api_regimes():
    return {"items": []}

@router.get("/api/bandit")
def api_bandit():
    return {"status": "ok"}

@router.get("/api/events")
def api_events():
    return {"items": []}

@router.get("/api/configs")
def api_configs():
    return {"items": []}
