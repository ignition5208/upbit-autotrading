from fastapi import APIRouter
router = APIRouter()
@router.get("/configs")
def configs():
    return {"ok": True}
