from fastapi import APIRouter

router = APIRouter()

@router.get("")
def list_regimes():
    items = [
        {"id": "0", "value": "0", "label": "Neutral"},
        {"id": "1", "value": "1", "label": "Bull"},
        {"id": "2", "value": "2", "label": "Bear"},
        {"id": "3", "value": "3", "label": "Sideways"},
    ]
    return {"items": items, "data": items}
    