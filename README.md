# Upbit Auto-Trading Platform v1.7.0 (Refactor)

Included:
- MariaDB
- dashboard-api (FastAPI)
- dashboard-web (nginx static Bootstrap)
- trader image (built; containers spawned dynamically by dashboard-api via docker.sock)

## Quick start

```bash
cp .env.example .env
# set strong passwords + KEY_ENC_SECRET (DO NOT CHANGE after saving accounts)
docker compose --profile build-only build trader-image
docker compose up -d --build
```

Open:
- Web UI: http://127.0.0.1:8080/
- API docs: http://127.0.0.1:8000/docs

## v1.7.0 changes

- Trader 스캐너/스코어링/전략 프리셋(파일 분리) 구조 추가
- 스캔 시 "어떤 코인을 검토했는지" 이벤트 로그(SCAN_START / SCORES_SAVED / BUY_EVAL / BUY_NO_SIGNAL 등) 기록
- docker-compose에서 upbit-trader:latest 이미지를 항상 로컬에서 빌드/유지(trader-image 서비스)

## v1.6.2 changes
- Fixed CORS middleware order (after app creation).
- Config Apply uses MariaDB UPSERT to avoid (1020) "Record has changed since last read".
- Removed dependency on `ConfigVersion.is_draft` (not present in refactor schema).
- Added Trader delete:
  - If container exists: stop/remove container + DB cleanup.
  - If container missing: DB-only cleanup.
  - Supports deactivate (soft) vs hard delete (config/orders/trades/positions/scores).
- Traders are NOT auto-started on system boot; container is created on Apply.

## DB Note
UPSERT requires PRIMARY/UNIQUE(trader_id) on config_current. Provided in init SQL.


## v1.6.2 hotfix
- Fix Docker SDK connection: add requests-unixsocket and use DockerClient(base_url=unix:///var/run/docker.sock)
