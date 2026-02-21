from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Float, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

# 거래 관련 모델 import
from app.models_trading import Signal, Order, Trade, Position, ConfigAudit


class Credential(Base):
    __tablename__ = "credentials"
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    access_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    secret_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Trader(Base):
    __tablename__ = "traders"
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy: Mapped[str] = mapped_column(String(64), default="standard")
    risk_mode: Mapped[str] = mapped_column(String(16), default="STANDARD")
    run_mode: Mapped[str] = mapped_column(String(8), default="PAPER")
    credential_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="STOP")
    container_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    seed_krw: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl_krw: Mapped[float] = mapped_column(Float, default=0.0)
    paper_started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    armed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Event(Base):
    __tablename__ = "events"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    trader_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="INFO")
    kind: Mapped[str] = mapped_column(String(64), default="system")
    message: Mapped[str] = mapped_column(Text, default="")


class RegimeSnapshot(Base):
    __tablename__ = "regime_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    market: Mapped[str] = mapped_column(String(32), default="KRW-BTC")
    regime_id: Mapped[int] = mapped_column(Integer, default=0)
    regime_label: Mapped[str] = mapped_column(String(32), default="RANGE")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")


# ===== STAB-0001: Runtime Guard 상태 =====
class TraderSafetyState(Base):
    __tablename__ = "trader_safety_state"
    trader_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    daily_loss_krw: Mapped[float] = mapped_column(Float, default=0.0)
    consecutive_losses: Mapped[int] = mapped_column(Integer, default=0)
    last_loss_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    block_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    slippage_anomaly_count: Mapped[int] = mapped_column(Integer, default=0)
    last_slippage_check: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    api_error_count: Mapped[int] = mapped_column(Integer, default=0)
    db_error_count: Mapped[int] = mapped_column(Integer, default=0)
    last_error_check: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ===== OPT-0004: Multi-Armed Bandit =====
class BanditState(Base):
    __tablename__ = "bandit_states"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    regime: Mapped[str] = mapped_column(String(32))           # TREND, RANGE, CHOP, PANIC, BREAKOUT_ROTATION
    strategy_id: Mapped[str] = mapped_column(String(64))
    alpha: Mapped[float] = mapped_column(Float, default=1.0)  # Thompson: 성공+1
    beta_: Mapped[float] = mapped_column("beta", Float, default=1.0)  # Thompson: 실패+1
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ===== §7: 모델 배포 라이프사이클 =====
class ModelVersion(Base):
    __tablename__ = "model_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(64))
    version: Mapped[str] = mapped_column(String(32))
    # DRAFT → VALIDATED → PAPER_DEPLOYED → LIVE_ELIGIBLE → LIVE_ARMED
    status: Mapped[str] = mapped_column(String(32), default="DRAFT")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    deployed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rolled_back_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    rollback_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)


# ===== OPT-0001: 데이터 파이프라인 =====
class ScanRun(Base):
    __tablename__ = "scan_runs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    strategy_id: Mapped[str] = mapped_column(String(64))
    market_count: Mapped[int] = mapped_column(Integer, default=0)
    top_n: Mapped[int] = mapped_column(Integer, default=5)
    params_json: Mapped[str] = mapped_column(Text, default="{}")


class FeatureSnapshot(Base):
    __tablename__ = "feature_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    scan_run_id: Mapped[int] = mapped_column(Integer, ForeignKey("scan_runs.id"), index=True)
    market: Mapped[str] = mapped_column(String(32))
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    features_json: Mapped[str] = mapped_column(Text, default="{}")
    label_ret_60m: Mapped[float | None] = mapped_column(Float, nullable=True)
    label_ret_240m: Mapped[float | None] = mapped_column(Float, nullable=True)
    label_mfe_240m: Mapped[float | None] = mapped_column(Float, nullable=True)
    label_mae_240m: Mapped[float | None] = mapped_column(Float, nullable=True)
    label_dd_240m: Mapped[float | None] = mapped_column(Float, nullable=True)


# ===== 전략 설정 이력 =====
class ConfigVersion(Base):
    __tablename__ = "config_versions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(64))
    version: Mapped[int] = mapped_column(Integer, default=1)
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=False)


# ===== OPT-0003: 튜닝 후보 =====
class ModelCandidate(Base):
    __tablename__ = "model_candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    params_json: Mapped[str] = mapped_column(Text, default="{}")
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    score: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING, PASS, REJECT
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ===== STAB-0002: Baseline & Drift =====
class ModelBaseline(Base):
    __tablename__ = "model_baselines"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    baseline_model_id: Mapped[int] = mapped_column(Integer, nullable=True)
    baseline_metrics_json: Mapped[str] = mapped_column(Text, default="{}")
    reference_window_start: Mapped[datetime] = mapped_column(DateTime)
    reference_window_end: Mapped[datetime] = mapped_column(DateTime)
    drift_warn_count: Mapped[int] = mapped_column(Integer, default=0)
    last_drift_check: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ModelMetrics24h(Base):
    __tablename__ = "model_metrics_24h"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_id: Mapped[int] = mapped_column(Integer, index=True)
    strategy_id: Mapped[str] = mapped_column(String(64), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    net_return_24h: Mapped[float] = mapped_column(Float, default=0.0)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
