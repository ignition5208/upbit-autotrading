from fastapi import APIRouter

from app.routers import traders, metrics, models, regimes, bandit, events, configs

router = APIRouter(prefix="/api")

# /api/overview  (metrics.router가 "/overview"를 갖고 있으므로 prefix 없이 include)
router.include_router(metrics.router)

# /api/traders/*
router.include_router(traders.router, prefix="/traders")

# /api/models/*
router.include_router(models.router, prefix="/models")

# /api/regimes/*
router.include_router(regimes.router, prefix="/regimes")

# /api/bandit/*
router.include_router(bandit.router, prefix="/bandit")

# /api/events/*
router.include_router(events.router, prefix="/events")

# /api/configs/*
router.include_router(configs.router, prefix="/configs")
