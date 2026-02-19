from fastapi import APIRouter, Depends
from app.deps import require_api_key

router = APIRouter(dependencies=[Depends(require_api_key)])

@router.get("/states")
def bandit_states():
    # TODO: bandit_states 조회
    return {"items": []}
