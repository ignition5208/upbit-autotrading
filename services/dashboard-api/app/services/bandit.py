import random
from datetime import datetime
from sqlalchemy.orm import Session
from app.models import BanditState


def sample_bandit_weight(db: Session, regime: str, strategy_id: str) -> float:
    """Thompson Sampling → 0.5 ~ 1.5 스케일 가중치 반환."""
    row = db.query(BanditState).filter_by(regime=regime, strategy_id=strategy_id).first()
    if not row:
        return 1.0
    sample = random.betavariate(row.alpha, row.beta_)  # 0 ~ 1
    return 0.5 + sample                                # 0.5 ~ 1.5


def update_bandit(db: Session, regime: str, strategy_id: str, reward_positive: bool) -> None:
    """성공이면 alpha 증가, 실패면 beta 증가."""
    row = db.query(BanditState).filter_by(regime=regime, strategy_id=strategy_id).first()
    if not row:
        row = BanditState(regime=regime, strategy_id=strategy_id)
        db.add(row)
    if reward_positive:
        row.alpha += 1.0
    else:
        row.beta_ += 1.0
    row.updated_at = datetime.utcnow()
    db.commit()
