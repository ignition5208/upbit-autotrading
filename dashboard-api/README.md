# dashboard-api (v1.8-0001)

FastAPI 기반 대시보드/관리 API 모듈입니다.

## 핵심 원칙 (v1.8-0001)
- **dashboard-api는 주문(매수/매도) 호출 금지**: 읽기/관리/트레이더 생성(오케스트레이션)만 담당합니다.
- 트레이더 컨테이너는 UI 요청에 의해 동적으로 생성/삭제되며, 실제 매매는 trader 컨테이너에서 수행합니다.
- DB는 MariaDB를 사용합니다(프로젝트 루트 docker-compose에서 named volume 권장).

## 실행 (로컬)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 환경변수 예시
- `DATABASE_URL` : 예) `mysql+pymysql://root:password@mariadb:3306/trading`
- `API_KEY` : 간단 보호용(옵션)
- `TRADER_COMPOSE_PROJECT_DIR` : docker-compose.yml 디렉토리(옵션)
- `TRADER_SERVICE_TEMPLATE` : 트레이더 서비스 템플릿 이름(옵션)

## 엔드포인트
- `GET /health`
- `GET /traders`
- `POST /traders`
- `DELETE /traders/{trader_name}`
- `GET /metrics/overview`
- `GET /models/versions`
- `GET /regimes/current`
- `GET /bandit/states`
- `GET /events`
- `GET /configs/versions`

> NOTE: 실제 스키마/쿼리는 shared/db 레이어와 통합될 때 확장됩니다.
