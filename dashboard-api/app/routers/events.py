from fastapi import APIRouter, Depends, Query
from app.deps import require_api_key

router = APIRouter()

@router.get("")
def list_events(limit: int = Query(100, ge=1, le=1000)):
    # TODO: events 조회
    return {"items": [], "limit": limit}
