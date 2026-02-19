from __future__ import annotations

from fastapi import APIRouter, Depends
from app.deps import require_api_key

# 다른 라우터의 "기능"을 포함하고 싶으면 include_router로 넣어도 됨
from app.routers import traders as traders_router
from app.routers import bandit as bandit_router
from app.routers import events as events_router
from app.routers import configs as configs_router


router = APIRouter(prefix="/api")


# ---- (A) 프론트에서 label undefined가 가장 자주 나는 모델/레짐은 "호환 최대로" 내려준다 ----

REGIMES = [
    {"id": 0, "label": "Neutral"},
    {"id": 1, "label": "Bull"},
    {"id": 2, "label": "Bear"},
    {"id": 3, "label": "Sideways"},
]

MODELS = [
    {"id": "baseline", "label": "Baseline"},
    {"id": "v1", "label": "Model v1"},
]


def _wrap_items_with_indexes(items: list[dict]) -> dict:
    """
    프론트 호환성을 최대치로 올리는 wrapper.

    - items: 기존 형태 유지
    - data/result: 프론트가 { data } 디스트럭쳐링하는 케이스 대응
    - ok: 관례적으로 쓰는 flag
    - id-key 인덱스: regimes[0].label / models["baseline"].label 같은 코드 대응
    """
    payload: dict = {
        "ok": True,
        "items": items,
        "data": items,
        "result": items,
    }
    for it in items:
        payload[str(it["id"])] = it  # ✅ JS에서 obj[0] → "0"로 접근 가능
    return payload


@router.get("/regimes")
def api_regimes():
    return _wrap_items_with_indexes(REGIMES)


@router.get("/models")
def api_models():
    return _wrap_items_with_indexes(MODELS)


# ---- (B) overview는 "data 래핑 + top-level 동시 제공"으로 active_traders undefined 방지 ----

@router.get("/overview")
def api_overview():
    # 기본값(렌더 안전)
    total_traders = 0
    live_traders = 0
    paper_traders = 0
    active_traders = 0
    pnl_24h = 0.0

    # 레짐/모델도 label까지 같이 포함(프론트가 lookup하다 죽는 케이스 방지)
    market_regime = REGIMES[0]
    model = MODELS[0]

    core = {
        "total_traders": total_traders,
        "live_traders": live_traders,
        "paper_traders": paper_traders,
        "active_traders": active_traders,
        "pnl_24h": pnl_24h,

        # 다양한 프론트 구현 대응용 필드들
        "market_regime": market_regime,                 # {id,label}
        "market_regime_id": market_regime["id"],
        "market_regime_label": market_regime["label"],

        "model": model,                                 # {id,label}
        "model_id": model["id"],
        "model_label": model["label"],

        "entry_block": False,
    }

    # ✅ res.data.active_traders 도 되고, res.active_traders 도 되게
    return {
        "ok": True,
        "data": core,
        "result": core,
        **core,
    }


# ---- (C) 나머지 /api/* 는 기존 라우터를 include해서 그대로 제공 ----
# /api/traders  -> 기존 traders_router의 "" , POST, DELETE 등 재사용
router.include_router(traders_router.router, prefix="/traders", tags=["traders"])

# /api/bandit, /api/events, /api/configs 등도 동일하게 재사용
router.include_router(bandit_router.router, prefix="/bandit", tags=["bandit"])
router.include_router(events_router.router, prefix="/events", tags=["events"])
router.include_router(configs_router.router, prefix="/configs", tags=["configs"])
