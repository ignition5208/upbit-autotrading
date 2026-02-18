from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .settings import SETTINGS

DB_URL = f"mysql+pymysql://{SETTINGS.DB_USER}:{SETTINGS.DB_PASS}@{SETTINGS.DB_HOST}:{SETTINGS.DB_PORT}/{SETTINGS.DB_NAME}?charset=utf8mb4"

engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
