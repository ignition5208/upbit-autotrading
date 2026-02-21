from sqlalchemy import inspect, text
from app.db import engine, Base
from app.models import BanditState  # noqa: F401 – needed so Base.metadata has it
from app.models_trading import Signal, Order, Trade, Position, ConfigAudit  # noqa: F401


_REGIMES = ["TREND", "RANGE", "CHOP", "PANIC", "BREAKOUT_ROTATION"]
_DEFAULT_STRATEGY = "standard"


def ensure_columns():
    with engine.begin() as conn:
        insp = inspect(conn)
        tables = set(insp.get_table_names())

        # ── regime_snapshots ────────────────────────────────────────────────
        if "regime_snapshots" in tables:
            cols = {c["name"] for c in insp.get_columns("regime_snapshots")}
            if "market" not in cols:
                conn.execute(text(
                    "ALTER TABLE regime_snapshots ADD COLUMN market VARCHAR(32) DEFAULT 'KRW-BTC'"
                ))

        # ── traders ─────────────────────────────────────────────────────────
        if "traders" in tables:
            cols = {c["name"] for c in insp.get_columns("traders")}
            if "seed_krw" not in cols:
                conn.execute(text("ALTER TABLE traders ADD COLUMN seed_krw FLOAT NULL"))
            if "pnl_krw" not in cols:
                conn.execute(text("ALTER TABLE traders ADD COLUMN pnl_krw FLOAT NOT NULL DEFAULT 0.0"))
            if "paper_started_at" not in cols:
                conn.execute(text("ALTER TABLE traders ADD COLUMN paper_started_at DATETIME NULL"))
            if "armed_at" not in cols:
                conn.execute(text("ALTER TABLE traders ADD COLUMN armed_at DATETIME NULL"))


def seed_bandit_states():
    """BanditState 초기 시드: regime × strategy 조합이 없으면 삽입."""
    from sqlalchemy.orm import Session
    from app.models import BanditState
    with Session(engine) as db:
        for regime in _REGIMES:
            exists = db.query(BanditState).filter_by(
                regime=regime, strategy_id=_DEFAULT_STRATEGY
            ).first()
            if not exists:
                db.add(BanditState(regime=regime, strategy_id=_DEFAULT_STRATEGY))
        db.commit()


def run_all():
    # 1) ORM이 모르는 테이블은 create_all 로 생성
    Base.metadata.create_all(engine)
    # 2) 기존 테이블에 누락된 컬럼 추가
    ensure_columns()
    # 3) BanditState 시드
    seed_bandit_states()
