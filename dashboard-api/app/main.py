from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.settings import Settings
from app.logging_ import configure_logging
from app.migrate import run_all
from app.routers import health, metrics, traders, credentials, models
from app.routers import regimes, events, configs, trainer, trades, bandit, safety

settings = Settings()
configure_logging(settings.log_level)

app = FastAPI(title="dashboard-api", version=settings.version)

origins = settings.cors_allow_origins
if isinstance(origins, str):
    origins = [o.strip() for o in origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

run_all()

app.include_router(health.router)
app.include_router(metrics.router,     prefix="/api", tags=["metrics"])
app.include_router(traders.router,     prefix="/api", tags=["traders"])
app.include_router(credentials.router, prefix="/api", tags=["credentials"])
app.include_router(models.router,      prefix="/api", tags=["models"])
app.include_router(regimes.router,     prefix="/api", tags=["regimes"])
app.include_router(events.router,      prefix="/api", tags=["events"])
app.include_router(configs.router,     prefix="/api", tags=["configs"])
app.include_router(trainer.router,     prefix="/api", tags=["trainer"])
app.include_router(trades.router,      prefix="/api", tags=["trades"])
app.include_router(bandit.router,      prefix="/api", tags=["bandit"])
app.include_router(safety.router,      prefix="/api", tags=["safety"])


@app.get("/")
def root():
    return {"service": "dashboard-api", "version": settings.version}
