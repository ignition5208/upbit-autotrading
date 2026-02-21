from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import BanditState
from app.services.bandit import update_bandit

router = APIRouter()


class RewardRequest(BaseModel):
    regime: str = Field(...)
    strategy_id: str = Field(...)
    reward_positive: bool = Field(...)


@router.get("/bandit/states")
def list_bandit_states(db: Session = Depends(get_db)):
    rows = db.execute(select(BanditState).order_by(BanditState.regime, BanditState.strategy_id)).scalars().all()
    return {"items": [{
        "id": r.id,
        "regime": r.regime,
        "strategy_id": r.strategy_id,
        "alpha": r.alpha,
        "beta": r.beta_,
        "updated_at": r.updated_at.isoformat(),
    } for r in rows]}


@router.post("/bandit/reward")
def post_reward(req: RewardRequest, db: Session = Depends(get_db)):
    update_bandit(db, regime=req.regime, strategy_id=req.strategy_id, reward_positive=req.reward_positive)
    return {"ok": True}
