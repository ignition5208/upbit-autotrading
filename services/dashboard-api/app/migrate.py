from sqlalchemy import inspect, text
from app.db import engine

def ensure_columns():
    with engine.begin() as conn:
        insp = inspect(conn)
        tables = set(insp.get_table_names())

        if "regime_snapshots" in tables:
            cols = {c["name"] for c in insp.get_columns("regime_snapshots")}
            if "market" not in cols:
                conn.execute(text("ALTER TABLE regime_snapshots ADD COLUMN market VARCHAR(32) DEFAULT 'KRW-BTC'"))
