from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.settings import Settings
from app.logging_ import configure_logging
from app.routers import health, traders, metrics, models, regimes, bandit, events, configs
from app.routers.api_aliases import router as api_aliases_router

settings = Settings()
configure_logging(settings.log_level)

app = FastAPI(title="dashboard-api", version=settings.version)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# health (no prefix)
app.include_router(health.router)

# native routes
app.include_router(traders.router, prefix="/traders", tags=["traders"])
app.include_router(metrics.router, prefix="/metrics", tags=["metrics"])
app.include_router(models.router, prefix="/models", tags=["models"])
app.include_router(regimes.router, prefix="/regimes", tags=["regimes"])
app.include_router(bandit.router, prefix="/bandit", tags=["bandit"])
app.include_router(events.router, prefix="/events", tags=["events"])
app.include_router(configs.router, prefix="/configs", tags=["configs"])

# dashboard-web compatibility aliases (/api/*)
app.include_router(api_aliases_router)

@app.get("/")
def root():
    return {"service": "dashboard-api", "version": settings.version}
