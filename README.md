# Upbit Auto-Trading Platform (v1.8-0001) - Root Skeleton

이 ZIP은 프로젝트 루트 레벨의 스켈레톤입니다.
모듈별 ZIP(shared/trader/trainer/dashboard-api/dashboard-web/infra/configs)과 함께 사용하세요.

## 구성(예시)
- docker-compose.yml: mariadb + dashboard-api + dashboard-web + trainer (+ trader는 동적 생성)
- scripts/: 편의 스크립트
- docs/: 운영/설계 문서 스켈레톤
- .env.example: 환경변수 샘플

## 주의
- `dashboard-api`는 주문 호출 금지(컨테이너 생성/관리/조회만)
- LIVE는 ARM 이후만 주문 가능 (trader에서 강제)
