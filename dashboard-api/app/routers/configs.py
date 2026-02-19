from fastapi import APIRouter, Depends
from app.deps import require_api_key

router = APIRouter()

@router.get("/versions")
def config_versions():
    # TODO: config_versions 조회
    return {"items": []}
