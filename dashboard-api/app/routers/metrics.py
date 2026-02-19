from fastapi import APIRouter

router = APIRouter()

@router.get("/overview")
def overview():
    data = {
        "total_traders": 0,
        "live_traders": 0,
        "paper_traders": 0,
        "active_traders": 0,
        "pnl_24h": 0.0,
    }
    return {**data, "data": data}
