# app/routers/metrics.py
from fastapi import APIRouter, Depends
from app.deps import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])

@router.get("/overview")
def overview():
    # 프론트가 lookup하다 죽는 걸 막기 위해 label 포함
    market_regime = {"id": 0, "label": "Neutral"}
    model = {"id": "baseline", "label": "Baseline"}

    return {
        "total_traders": 0,
        "live_traders": 0,
        "paper_traders": 0,
        "active_traders": 0,   # ✅ 프론트가 쓰는 키
        "pnl_24h": 0.0,

        # ✅ label undefined 방지용 (정석)
        "market_regime": market_regime,
        "model": model,

        # (선택) 프론트가 entry block 같은 뱃지를 쓰면 미리
        "entry_block": False,
    }
