"""
pytest 설정 및 공통 fixtures
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
import json

from app.db import Base, get_db
from app.models import (
    Trader,
    RegimeSnapshot,
    TraderSafetyState,
    BanditState,
    ModelVersion,
    ScanRun,
    FeatureSnapshot,
    ModelBaseline,
    ModelMetrics24h,
    ModelCandidate,
)


# 테스트용 인메모리 SQLite DB
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """테스트용 DB 세션"""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def sample_trader(db_session):
    """샘플 Trader 생성"""
    trader = Trader(
        name="test_trader",
        strategy="test_strategy",
        risk_mode="STANDARD",
        run_mode="PAPER",
        seed_krw=1000000.0,
        status="STOP",
        paper_started_at=datetime.utcnow(),
    )
    db_session.add(trader)
    db_session.commit()
    return trader


@pytest.fixture
def sample_regime_snapshot(db_session):
    """샘플 Regime Snapshot 생성"""
    snap = RegimeSnapshot(
        ts=datetime.utcnow(),
        market="KRW-BTC",
        regime_id=1,
        regime_label="TREND",
        confidence=0.75,
        metrics_json=json.dumps({
            'btc_adx_4h': 30.0,
            'btc_atr_pct_4h': 2.0,
        }),
    )
    db_session.add(snap)
    db_session.commit()
    return snap


@pytest.fixture
def sample_model_version(db_session):
    """샘플 ModelVersion 생성"""
    mv = ModelVersion(
        strategy_id="test_strategy",
        version="v1.0.0",
        status="DRAFT",
        metrics_json=json.dumps({}),
    )
    db_session.add(mv)
    db_session.commit()
    return mv
