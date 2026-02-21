from fastapi import APIRouter
router = APIRouter()
@router.get("/models")
def models():
    return {"items":[{"id":"baseline","label":"Baseline"},{"id":"v1","label":"Model v1"}]}
