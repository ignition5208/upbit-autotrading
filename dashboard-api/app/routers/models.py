from fastapi import APIRouter, Depends
from app.deps import require_api_key

router = APIRouter()

@router.get("/versions")
def model_versions():
    # TODO: model_versions/model_candidates 조회
    return {"items": []}
