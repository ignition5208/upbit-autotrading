from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from app.settings import Settings

def get_engine(settings: Settings) -> Engine:
    return create_engine(settings.database_url, pool_pre_ping=True, pool_recycle=1800)
