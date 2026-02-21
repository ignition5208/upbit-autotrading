"""
Trainer API 엔드포인트
OPT-0001 ~ OPT-0004 구현
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from app.db import get_db
from app.services.data_pipeline import run_scan, calculate_labels
from app.services.model_evaluation import calculate_evaluation_metrics, evaluate_model
from app.services.auto_tuning import optimize_hyperparameters
from app.services.bandit import update_bandit
from app.models import ScanRun, FeatureSnapshot

router = APIRouter()


class ScanRequest(BaseModel):
    strategy_id: str = Field(...)
    markets: list[str] = Field(...)
    top_n: int = Field(default=5)
    params: dict = Field(default_factory=dict)


class UpdateLabelsRequest(BaseModel):
    scan_run_id: int = Field(...)


class EvaluateRequest(BaseModel):
    strategy_id: str = Field(...)


class TuneRequest(BaseModel):
    strategy_id: str = Field(...)
    param_space: dict = Field(default_factory=dict)


class BanditUpdateRequest(BaseModel):
    regime: str = Field(...)
    strategy_id: str = Field(...)
    reward_positive: bool = Field(...)


@router.post("/trainer/scan")
def run_scan_endpoint(req: ScanRequest, db: Session = Depends(get_db)):
    """스캔 실행 (OPT-0001)"""
    scan_run = run_scan(
        db=db,
        strategy_id=req.strategy_id,
        markets=req.markets,
        top_n=req.top_n,
        params=req.params,
    )
    return {"ok": True, "scan_run_id": scan_run.id}


@router.post("/trainer/update-labels")
def update_labels(req: UpdateLabelsRequest, db: Session = Depends(get_db)):
    """라벨 업데이트 (OPT-0001)"""
    snapshots = (
        db.query(FeatureSnapshot)
        .filter_by(scan_run_id=req.scan_run_id)
        .all()
    )
    
    updated_count = 0
    for snapshot in snapshots:
        # 실제로는 거래 기록에서 라벨을 계산해야 함
        # 여기서는 예시로 랜덤 값 사용
        import random
        snapshot.label_ret_60m = random.uniform(-0.05, 0.05)
        snapshot.label_ret_240m = random.uniform(-0.1, 0.1)
        snapshot.label_mfe_240m = random.uniform(0, 0.15)
        snapshot.label_mae_240m = random.uniform(0, 0.1)
        snapshot.label_dd_240m = random.uniform(-0.1, 0)
        updated_count += 1
    
    db.commit()
    return {"ok": True, "updated_count": updated_count}


@router.post("/trainer/evaluate")
def evaluate(req: EvaluateRequest, db: Session = Depends(get_db)):
    """모델 평가 (OPT-0002)"""
    # 최근 스캔의 FeatureSnapshot 가져오기
    scan_run = (
        db.query(ScanRun)
        .filter_by(strategy_id=req.strategy_id)
        .order_by(ScanRun.ts.desc())
        .first()
    )
    
    if not scan_run:
        raise HTTPException(404, "Scan run not found")
    
    snapshots = (
        db.query(FeatureSnapshot)
        .filter_by(scan_run_id=scan_run.id)
        .all()
    )
    
    snapshot_data = []
    for snap in snapshots:
        snapshot_data.append({
            'label_ret_60m': snap.label_ret_60m,
            'label_ret_240m': snap.label_ret_240m,
            'label_mfe_240m': snap.label_mfe_240m,
            'label_mae_240m': snap.label_mae_240m,
            'label_dd_240m': snap.label_dd_240m,
        })
    
    metrics = calculate_evaluation_metrics(snapshot_data)
    status, reason = evaluate_model(metrics)
    
    return {
        "ok": True,
        "status": status,
        "reason": reason,
        "metrics": metrics,
    }


@router.post("/trainer/tune")
def tune(req: TuneRequest, db: Session = Depends(get_db)):
    """자동 튜닝 (OPT-0003)"""
    # 최근 스캔의 FeatureSnapshot 가져오기
    scan_run = (
        db.query(ScanRun)
        .filter_by(strategy_id=req.strategy_id)
        .order_by(ScanRun.ts.desc())
        .first()
    )
    
    if not scan_run:
        raise HTTPException(404, "Scan run not found")
    
    snapshots = (
        db.query(FeatureSnapshot)
        .filter_by(scan_run_id=scan_run.id)
        .all()
    )
    
    snapshot_data = []
    for snap in snapshots:
        snapshot_data.append({
            'label_ret_60m': snap.label_ret_60m,
            'label_ret_240m': snap.label_ret_240m,
            'label_mfe_240m': snap.label_mfe_240m,
            'label_mae_240m': snap.label_mae_240m,
            'label_dd_240m': snap.label_dd_240m,
        })
    
    best_params = optimize_hyperparameters(
        db=db,
        strategy_id=req.strategy_id,
        feature_snapshots=snapshot_data,
        param_space=req.param_space if req.param_space else None,
    )
    
    return {
        "ok": True,
        "best_params": best_params,
    }


@router.post("/trainer/bandit-update")
def bandit_update(req: BanditUpdateRequest, db: Session = Depends(get_db)):
    """Bandit 보상 업데이트 (OPT-0004)"""
    update_bandit(
        db=db,
        regime=req.regime,
        strategy_id=req.strategy_id,
        reward_positive=req.reward_positive,
    )
    return {"ok": True}
