from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_db
from app.models import ModelVersion, FeatureSnapshot
from app.services.model_evaluation import calculate_evaluation_metrics, evaluate_model
from app.services.drift_detection import check_auto_rollback_conditions, execute_auto_rollback
from app.services.telegram import send_telegram

router = APIRouter()


class ModelCreate(BaseModel):
    strategy_id: str = Field(...)
    version: str = Field(...)
    metrics: dict = Field(default_factory=dict)


@router.get("/models")
def list_models(db: Session = Depends(get_db)):
    rows = db.execute(
        select(ModelVersion).order_by(ModelVersion.created_at.desc())
    ).scalars().all()
    return {"items": [{
        "id": r.id,
        "strategy_id": r.strategy_id,
        "version": r.version,
        "status": r.status,
        "metrics": r.metrics_json,
        "created_at": r.created_at.isoformat(),
        "deployed_at": r.deployed_at.isoformat() if r.deployed_at else None,
        "rolled_back_at": r.rolled_back_at.isoformat() if r.rolled_back_at else None,
        "rollback_reason": r.rollback_reason,
    } for r in rows]}


@router.post("/models")
def create_model(req: ModelCreate, db: Session = Depends(get_db)):
    import json
    mv = ModelVersion(
        strategy_id=req.strategy_id,
        version=req.version,
        metrics_json=json.dumps(req.metrics),
        created_at=datetime.utcnow(),
    )
    db.add(mv)
    db.commit()
    return {"created": True, "id": mv.id}


@router.post("/models/{model_id}/validate")
def validate_model(model_id: int, db: Session = Depends(get_db)):
    """모델 평가 및 VALIDATED 상태 전환"""
    mv = db.get(ModelVersion, model_id)
    if not mv:
        raise HTTPException(404, "not found")
    
    if mv.status != "DRAFT":
        raise HTTPException(400, f"현재 상태 {mv.status}에서 VALIDATED 전환 불가")
    
    # FeatureSnapshot 데이터로 평가
    snapshots = (
        db.query(FeatureSnapshot)
        .filter_by(scan_run_id=mv.id)  # 간단화: model_id를 scan_run_id로 사용
        .all()
    )
    
    snapshot_data = []
    for snap in snapshots:
        import json
        features = json.loads(snap.features_json) if snap.features_json else {}
        snapshot_data.append({
            'label_ret_60m': snap.label_ret_60m,
            'label_ret_240m': snap.label_ret_240m,
            'label_mfe_240m': snap.label_mfe_240m,
            'label_mae_240m': snap.label_mae_240m,
            'label_dd_240m': snap.label_dd_240m,
        })
    
    # 평가 지표 계산
    metrics = calculate_evaluation_metrics(snapshot_data)
    
    # 상태 결정
    status, reason = evaluate_model(metrics)
    
    import json
    mv.metrics_json = json.dumps(metrics)
    
    if status == "PASS":
        mv.status = "VALIDATED"
        send_telegram("INFO", f"[{mv.strategy_id}] 모델 VALIDATED: {reason}")
    elif status == "REJECT":
        mv.status = "DRAFT"
        mv.rollback_reason = f"평가 실패: {reason}"
        send_telegram("WARN", f"[{mv.strategy_id}] 모델 평가 실패: {reason}")
    else:  # HOLD
        mv.status = "DRAFT"
        send_telegram("INFO", f"[{mv.strategy_id}] 모델 HOLD: {reason}")
    
    db.commit()
    return {"ok": True, "status": mv.status, "evaluation": status, "reason": reason, "metrics": metrics}


@router.post("/models/{model_id}/deploy")
def deploy_model(model_id: int, db: Session = Depends(get_db)):
    """모델 PAPER 배포"""
    mv = db.get(ModelVersion, model_id)
    if not mv:
        raise HTTPException(404, "not found")
    
    if mv.status != "VALIDATED":
        raise HTTPException(400, f"현재 상태 {mv.status}에서 PAPER_DEPLOYED 전환 불가. 먼저 VALIDATE 필요")
    
    # 재배포 쿨다운 확인 (24시간)
    if mv.deployed_at:
        hours_since_deploy = (datetime.utcnow() - mv.deployed_at).total_seconds() / 3600
        if hours_since_deploy < 24:
            remaining = 24 - hours_since_deploy
            raise HTTPException(400, f"재배포 쿨다운 {remaining:.1f}시간 남음")
    
    mv.status = "PAPER_DEPLOYED"
    mv.deployed_at = datetime.utcnow()
    db.commit()
    
    send_telegram("INFO", f"[{mv.strategy_id}] 모델 PAPER 배포됨 (24h 보호기간 시작)")
    return {"ok": True, "status": mv.status}


@router.post("/models/{model_id}/check_eligible")
def check_live_eligible(model_id: int, db: Session = Depends(get_db)):
    """PAPER_DEPLOYED → LIVE_ELIGIBLE 자동 전환 확인 (24시간 경과 후)"""
    mv = db.get(ModelVersion, model_id)
    if not mv:
        raise HTTPException(404, "not found")
    
    if mv.status != "PAPER_DEPLOYED":
        return {"ok": False, "status": mv.status, "message": "PAPER_DEPLOYED 상태가 아님"}
    
    if not mv.deployed_at:
        return {"ok": False, "status": mv.status, "message": "배포 시간 정보 없음"}
    
    # 24시간 경과 확인
    hours_since_deploy = (datetime.utcnow() - mv.deployed_at).total_seconds() / 3600
    
    if hours_since_deploy >= 24:
        # 자동 롤백 조건 확인
        should_rollback, reason = check_auto_rollback_conditions(db, mv.strategy_id, model_id)
        
        if should_rollback:
            execute_auto_rollback(db, model_id, reason)
            return {"ok": False, "status": "DRAFT", "message": f"자동 롤백: {reason}"}
        
        mv.status = "LIVE_ELIGIBLE"
        db.commit()
        send_telegram("INFO", f"[{mv.strategy_id}] 모델 LIVE_ELIGIBLE 전환 (24h PAPER 완료)")
        return {"ok": True, "status": mv.status, "message": "LIVE_ELIGIBLE로 전환됨"}
    else:
        remaining = 24 - hours_since_deploy
        return {"ok": False, "status": mv.status, "message": f"{remaining:.1f}시간 남음"}


@router.post("/models/{model_id}/arm")
def arm_model(model_id: int, db: Session = Depends(get_db)):
    """모델 ARM (LIVE 전환 준비)"""
    mv = db.get(ModelVersion, model_id)
    if not mv:
        raise HTTPException(404, "not found")
    
    if mv.status not in ("PAPER_DEPLOYED", "LIVE_ELIGIBLE"):
        raise HTTPException(400, f"현재 상태 {mv.status}에서 LIVE_ARMED 불가")
    
    # LIVE_ELIGIBLE이 아니면 자동 전환 시도
    if mv.status == "PAPER_DEPLOYED":
        result = check_live_eligible(model_id, db)
        if not result.get("ok"):
            raise HTTPException(400, result.get("message", "LIVE_ELIGIBLE 전환 실패"))
    
    mv.status = "LIVE_ARMED"
    db.commit()
    send_telegram("WARN", f"[{mv.strategy_id}] 모델 LIVE_ARMED - LIVE 거래 가능")
    return {"ok": True, "status": mv.status}


@router.post("/models/{model_id}/rollback")
def rollback_model(model_id: int, reason: str = "", db: Session = Depends(get_db)):
    mv = db.get(ModelVersion, model_id)
    if not mv:
        raise HTTPException(404, "not found")
    mv.rolled_back_at = datetime.utcnow()
    mv.rollback_reason = reason or "manual rollback"
    mv.status = "DRAFT"
    db.commit()
    return {"ok": True}
