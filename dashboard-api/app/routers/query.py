from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..db import get_db
from ..models import Order, Trade, Position, Score

router = APIRouter()

@router.get("/positions")
def positions(trader_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Position)
    if trader_id:
        q = q.filter(Position.trader_id == trader_id)
    items = q.order_by(Position.id.desc()).limit(500).all()
    return [{"id": i.id, "trader_id": i.trader_id, "symbol": i.symbol, "state": i.state, "updated_at": i.updated_at.isoformat()} for i in items]

@router.get("/orders")
def orders(trader_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Order)
    if trader_id:
        q = q.filter(Order.trader_id == trader_id)
    items = q.order_by(Order.id.desc()).limit(500).all()
    return [{"id": i.id, "trader_id": i.trader_id, "symbol": i.symbol, "state": i.state, "created_at": i.created_at.isoformat()} for i in items]

@router.get("/trades")
def trades(trader_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Trade)
    if trader_id:
        q = q.filter(Trade.trader_id == trader_id)
    items = q.order_by(Trade.id.desc()).limit(500).all()
    return [{"id": i.id, "trader_id": i.trader_id, "symbol": i.symbol, "created_at": i.created_at.isoformat()} for i in items]

@router.get("/scores")
def scores(trader_id: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Score)
    if trader_id:
        q = q.filter(Score.trader_id == trader_id)
    items = q.order_by(Score.id.desc()).limit(500).all()
    return [{"id": i.id, "trader_id": i.trader_id, "symbol": i.symbol, "score": float(i.score), "created_at": i.created_at.isoformat()} for i in items]
