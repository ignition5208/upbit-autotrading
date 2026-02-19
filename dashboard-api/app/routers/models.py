from fastapi import APIRouter

router = APIRouter()

@router.get("")
def list_models():
    items = [
        {"id": "baseline", "value": "baseline", "label": "Baseline"},
        {"id": "v1", "value": "v1", "label": "Model v1"},
    ]
    return {"items": items, "data": items}
