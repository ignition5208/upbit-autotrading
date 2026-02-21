"""
거래 관련 API 엔드포인트
신호, 주문, 거래, 포지션 관리
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db import get_db
from app.models_trading import Signal, Order, Trade, Position
import json

router = APIRouter()


class SignalIn(BaseModel):
    trader_name: str
    symbol: str
    total_score: float
    scores_json: dict = Field(default_factory=dict)
    regime: str
    action: str  # ENTRY, EXIT, HOLD
    reason_codes: list[str] = Field(default_factory=list)


class OrderIn(BaseModel):
    trader_name: str
    order_id: str
    symbol: str
    side: str  # BUY, SELL
    price: float
    size: float
    status: str = "PENDING"
    filled_qty: float = 0.0
    avg_price: float | None = None


@router.post("/trades/signal")
def create_signal(req: SignalIn, db: Session = Depends(get_db)):
    """신호 기록"""
    signal = Signal(
        trader_name=req.trader_name,
        symbol=req.symbol,
        ts=datetime.utcnow(),
        total_score=req.total_score,
        scores_json=json.dumps(req.scores_json),
        regime=req.regime,
        action=req.action,
        reason_codes=json.dumps(req.reason_codes),
        raw_metrics_json="{}",
    )
    db.add(signal)
    db.commit()
    return {"ok": True, "id": signal.id}


@router.post("/trades/order")
def create_order(req: OrderIn, db: Session = Depends(get_db)):
    """주문 기록"""
    order = Order(
        order_id=req.order_id,
        trader_name=req.trader_name,
        symbol=req.symbol,
        side=req.side,
        price=req.price,
        size=req.size,
        status=req.status,
        filled_qty=req.filled_qty,
        avg_price=req.avg_price,
    )
    db.add(order)
    db.commit()
    return {"ok": True, "id": order.id}


@router.get("/trades/signals")
def list_signals(
    trader_name: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    """신호 리스트"""
    query = db.query(Signal)
    if trader_name:
        query = query.filter_by(trader_name=trader_name)
    rows = query.order_by(Signal.ts.desc()).limit(limit).all()
    
    return {
        "items": [{
            "id": r.id,
            "trader_name": r.trader_name,
            "symbol": r.symbol,
            "ts": r.ts.isoformat(),
            "total_score": r.total_score,
            "scores_json": json.loads(r.scores_json),
            "regime": r.regime,
            "action": r.action,
            "reason_codes": json.loads(r.reason_codes),
        } for r in rows]
    }


@router.get("/trades")
def list_trades(
    trader_name: str | None = None,
    limit: int = 200,
    db: Session = Depends(get_db),
):
    """
    체결 이력 조회.
    현재는 FILLED 주문을 트레이드 뷰로 제공한다.
    """
    query = db.query(Order).filter_by(status="FILLED")
    if trader_name:
        query = query.filter_by(trader_name=trader_name)
    rows = query.order_by(Order.created_at.desc()).limit(limit).all()
    return {
        "items": [{
            "id": r.id,
            "order_id": r.order_id,
            "trader_name": r.trader_name,
            "market": r.symbol,
            "side": r.side,
            "qty": r.filled_qty if r.filled_qty and r.filled_qty > 0 else r.size,
            "price": r.avg_price if r.avg_price is not None else r.price,
            "status": r.status,
            "ts": r.created_at.isoformat(),
        } for r in rows]
    }


@router.get("/trades/positions")
def list_positions(
    trader_name: str | None = None,
    db: Session = Depends(get_db),
):
    """포지션 리스트"""
    query = db.query(Position).filter_by(status="OPEN")
    if trader_name:
        query = query.filter_by(trader_name=trader_name)
    rows = query.all()
    
    return {
        "items": [{
            "id": r.id,
            "trader_name": r.trader_name,
            "symbol": r.symbol,
            "open_time": r.open_time.isoformat(),
            "avg_entry_price": r.avg_entry_price,
            "size": r.size,
            "current_price": r.current_price,
            "unreal_pnl": r.unreal_pnl,
            "unreal_pnl_pct": r.unreal_pnl_pct,
            "stop_price": r.stop_price,
            "take_prices": json.loads(r.take_prices_json),
        } for r in rows]
    }
