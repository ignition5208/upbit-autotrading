from fastapi import APIRouter, Depends
from app.deps import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])

@router.get("/current")
def current_regime():
    # TODO: market_regimes 최신값 조회
    return {
        "label": "RANGE",
        "score": 50,
        "updated_at": None,
        "metrics": {},
    }
