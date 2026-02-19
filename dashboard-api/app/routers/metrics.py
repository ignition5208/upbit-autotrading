from fastapi import APIRouter, Depends
from app.deps import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])

@router.get("/overview")
def overview():
    # TODO: PnL, 드리프트, 밴딧 상태 등 집계
    return {
        "total_traders": 0,
        "live_traders": 0,
        "paper_traders": 0,
        "pnl_24h": 0.0,
    }
