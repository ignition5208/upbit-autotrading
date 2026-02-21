from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, Float
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base

class Credential(Base):
    __tablename__ = "credentials"
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    access_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    secret_key_enc: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Trader(Base):
    __tablename__ = "traders"
    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    strategy: Mapped[str] = mapped_column(String(64), default="challenge1")
    risk_mode: Mapped[str] = mapped_column(String(16), default="STANDARD")
    run_mode: Mapped[str] = mapped_column(String(8), default="PAPER")
    credential_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="STOP")
    container_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
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
    regime_label: Mapped[str] = mapped_column(String(32), default="Neutral")
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    metrics_json: Mapped[str] = mapped_column(Text, default="{}")
