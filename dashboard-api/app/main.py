from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Upbit Auto-Trading Platform v1.7.0 (Refactor)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .routers.overview import router as overview_router
from .routers.traders import router as traders_router
from .routers.config import router as config_router
from .routers.query import router as query_router
from .routers.accounts import router as accounts_router

app.include_router(overview_router)
app.include_router(traders_router)
app.include_router(config_router)
app.include_router(query_router)
app.include_router(accounts_router)

# Startup reconcile intentionally does NOT start traders automatically.
