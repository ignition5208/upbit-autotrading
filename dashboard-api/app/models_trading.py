"""
거래 관련 모델 (지침 6번: 로그·DB 스키마)
"""
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Float, Boolean, ForeignKey, BigInteger
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


# ===== 신호 (Signals) =====
class Signal(Base):
    __tablename__ = "signals"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trader_name: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    total_score: Mapped[float] = mapped_column(Float)
    scores_json: Mapped[str] = mapped_column(Text, default="{}")  # {tp: 85, vcb: 70, lsr: 60, lf: 50, regime: 80}
    regime: Mapped[str] = mapped_column(String(32))
    action: Mapped[str] = mapped_column(String(16))  # ENTRY, EXIT, HOLD
    reason_codes: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of reason codes
    raw_metrics_json: Mapped[str] = mapped_column(Text, default="{}")


# ===== 주문 (Orders) =====
class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)  # 거래소 주문 ID
    trader_name: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))  # BUY, SELL
    price: Mapped[float] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="PENDING")  # PENDING, FILLED, PARTIAL, CANCELLED, FAILED
    filled_qty: Mapped[float] = mapped_column(Float, default=0.0)
    avg_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ===== 거래 (Trades) =====
class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trade_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    trader_name: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    entry_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    entry_price: Mapped[float] = mapped_column(Float)
    entry_size: Mapped[float] = mapped_column(Float)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    exit_size: Mapped[float | None] = mapped_column(Float, nullable=True)
    pnl: Mapped[float] = mapped_column(Float, default=0.0)
    pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    mode: Mapped[str] = mapped_column(String(8), default="PAPER")  # PAPER, LIVE
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ===== 포지션 (Positions) =====
class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trader_name: Mapped[str] = mapped_column(String(64), index=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    open_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    avg_entry_price: Mapped[float] = mapped_column(Float)
    size: Mapped[float] = mapped_column(Float)
    current_price: Mapped[float] = mapped_column(Float)
    unreal_pnl: Mapped[float] = mapped_column(Float, default=0.0)
    unreal_pnl_pct: Mapped[float] = mapped_column(Float, default=0.0)
    stop_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    take_prices_json: Mapped[str] = mapped_column(Text, default="[]")  # JSON array of take profit prices
    tags: Mapped[str] = mapped_column(String(256), nullable=True)  # 메타데이터 (예: "tp_score_85")
    status: Mapped[str] = mapped_column(String(16), default="OPEN")  # OPEN, CLOSED, PARTIAL
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ===== 설정 변경 감사 (Config Audit) =====
class ConfigAudit(Base):
    __tablename__ = "config_audit"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    trader_name: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    config_key: Mapped[str] = mapped_column(String(64), index=True)
    old_value: Mapped[str] = mapped_column(Text, nullable=True)
    new_value: Mapped[str] = mapped_column(Text)
    changed_by: Mapped[str] = mapped_column(String(64), default="system")  # system, user, auto_tune
    changed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
