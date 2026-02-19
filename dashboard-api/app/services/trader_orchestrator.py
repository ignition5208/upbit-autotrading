import os
import logging
from dataclasses import dataclass
from typing import Any, Dict

log = logging.getLogger("trader_orchestrator")

@dataclass
class OrchestratorSettings:
    compose_project_dir: str | None = None
    service_template: str = "trader-template"

class TraderOrchestrator:
    """
    v1.8-0001 요구사항:
    - trader는 UI에서 추가 시 동적 생성
    - dashboard-api는 주문 호출 금지(여긴 컨테이너 lifecycle만)
    """

    def __init__(self, settings: OrchestratorSettings | None = None):
        if settings is None:
            settings = OrchestratorSettings(
                compose_project_dir=os.getenv("TRADER_COMPOSE_PROJECT_DIR"),
                service_template=os.getenv("TRADER_SERVICE_TEMPLATE", "trader-template"),
            )
        self.settings = settings

    def create_trader_service(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        # NOTE: 실제 운영에서는 docker compose override 파일 생성 + up -d 방식 권장
        # 여기서는 스켈레톤: 호출 명령만 구성해서 반환
        trader_name = payload["trader_name"]
        env = {
            "TRADER_NAME": trader_name,
            "STRATEGY": payload.get("strategy"),
            "RISK_MODE": payload.get("risk_mode"),
            "RUN_MODE": payload.get("run_mode"),
            "SEED_KRW": str(payload.get("seed_krw") or ""),
        }
        cmd = ["docker", "compose", "up", "-d", "--no-deps", "--scale", f"{self.settings.service_template}=1"]
        return {
            "note": "skeleton - integrate with your compose/labels approach",
            "compose_project_dir": self.settings.compose_project_dir,
            "service_template": self.settings.service_template,
            "env": env,
            "cmd": cmd,
        }

    def delete_trader_service(self, trader_name: str) -> Dict[str, Any]:
        cmd = ["docker", "compose", "rm", "-sf", trader_name]
        return {
            "note": "skeleton - integrate with your compose/labels approach",
            "compose_project_dir": self.settings.compose_project_dir,
            "cmd": cmd,
        }
