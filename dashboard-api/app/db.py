from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.settings import Settings

_settings = Settings()

def make_db_url():
    return (
        f"mysql+pymysql://{_settings.mysql_user}:{_settings.mysql_password}"
        f"@{_settings.mysql_host}:{_settings.mysql_port}/{_settings.mysql_database}"
        f"?charset=utf8mb4"
    )

engine = create_engine(make_db_url(), pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
