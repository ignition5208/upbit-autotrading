from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.deps import require_api_key
from app.services.trader_orchestrator import TraderOrchestrator

router = APIRouter(dependencies=[Depends(require_api_key)])

class TraderCreateRequest(BaseModel):
    trader_name: str = Field(..., description="Unique container/service name")
    strategy: str = Field(..., description="Score-Strategy name")
    risk_mode: str = Field(..., description="SAFE/STANDARD/PROFIT/CRAZY")
    run_mode: str = Field(..., description="LIVE or PAPER")
    seed_krw: float | None = Field(default=None, description="optional seed money")

@router.get("")
def list_traders():
    # TODO: DB 조회(traders 테이블)로 교체
    return {"items": []}

@router.post("")
def create_trader(req: TraderCreateRequest):
    orch = TraderOrchestrator()
    result = orch.create_trader_service(req.model_dump())
    return {"created": True, "detail": result}

@router.delete("/{trader_name}")
def delete_trader(trader_name: str):
    orch = TraderOrchestrator()
    result = orch.delete_trader_service(trader_name)
    return {"deleted": True, "detail": result}
