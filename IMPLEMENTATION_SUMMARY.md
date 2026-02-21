# 지침.md 기반 기능 구현 요약

## 구현 완료된 모듈

### 1. 시스템 아키텍처 (12개 모듈)

#### ✅ 데이터 레이어
- MariaDB 스키마 확장
- 거래 관련 테이블 추가 (signals, orders, trades, positions, config_audit)

#### ✅ 인제스트 (Collector)
- Regime Engine: 실제 지표 계산 (6개 지표)
- Upbit API 연동 (pyupbit)

#### ✅ 스크리너 (Screener)
- **파일**: `services/trader/screener.py`
- 전체 마켓 → 후보 필터링 (거래대금, 스프레드, 유동성)
- 출력: 후보 리스트 + 필터 리즌

#### ✅ 레짐 평가기 (Regime Engine)
- **파일**: `services/regime-engine/indicators.py`, `main.py`
- 6개 입력 지표 계산
- 5개 레짐 분류 (BREAKOUT_ROTATION, TREND, RANGE, CHOP, PANIC)

#### ✅ 스코어 모듈 (5개 기법)
- **파일**: `services/trader/scoring.py`
- **TP (Trend Pullback)**: EMA50/200, 피보나치 되돌림
- **VCB (Volatility Contraction Breakout)**: 볼린저 밴드 수축 후 돌파
- **LSR (Liquidity Sweep Reversal)**: 고점/저점 스위프 후 반전
- **LF (Leader-Follower)**: BTC 대비 상대 강도
- **Regime Modifier**: 레짐별 가중치

#### ✅ 종합 점수 엔진 (Score Aggregator)
- **파일**: `services/trader/score_aggregator.py`
- 가중치 합: `total_score = Σ (w_i * norm_score_i)`
- EMA 평활화 (α=0.3)
- 기본 가중치: TP(0.30), VCB(0.25), Regime(0.20), LSR(0.15), LF(0.10)

#### ✅ 포지션 사이징 & 리스크 엔진
- **파일**: `services/trader/position_sizer.py`
- RISK_PER_TRADE (기본 1%)
- MAX_PORTFOLIO_RISK (기본 5%)
- 슬리피지 제한 (0.5%)
- 스케일아웃 익절가 계산

#### ✅ 유동성·상관검사 (Pre-trade checks)
- **파일**: `services/trader/pre_trade_check.py`
- 8개 체크리스트 모두 구현:
  1. total_score ≥ ENTRY_THRESHOLD (70)
  2. regime 허용
  3. 유동성 체크 (expected_order_krw ≤ avg_depth * 0.3)
  4. remaining_budget ≥ RISK_PER_TRADE
  5. 상관관계 체크 (동일 심볼 중복 방지)
  6. API health
  7. trading hours (Upbit는 24시간)
  8. risk manager 승인 (자동)

#### ✅ 주문 실행기 (Order Executor)
- **파일**: `services/trader/order_executor.py`
- Paper 모드: 가상 실행 (슬리피지 시뮬레이션)
- LIVE 모드: 구조 준비 (실제 구현 필요)
- 주문 기록 및 상태 관리

#### ✅ 포지션 매니저 (Position Manager)
- **파일**: `services/trader/position_manager.py`
- 트레일링 스톱 (2% 이상 수익 시 활성화)
- 스케일아웃 (3단계 익절)
- 자동 SL/TP
- 레짐 변화 시 자동 축소/청산

#### ✅ 로깅·감사 (Audit)
- **파일**: `services/dashboard-api/app/models_trading.py`
- signals, orders, trades, positions 테이블
- config_audit 테이블 (설정 변경 이력)

#### ✅ 모니터링·알람
- Telegram 알람 시스템 (이미 구현됨)
- Dashboard API를 통한 실시간 모니터링

### 2. Trading Engine 통합
- **파일**: `services/trader/trading_engine.py`
- 전체 워크플로우 통합:
  1. Regime 조회
  2. 스크리닝
  3. 스코어링 (5개 모듈)
  4. 점수 집계 및 평활화
  5. 진입 검토 (Pre-trade 체크)
  6. 포지션 사이징
  7. 주문 실행
  8. 포지션 관리

### 3. Trader 서비스 메인
- **파일**: `services/trader/main.py`
- 설정 로드 및 동적 초기화
- STOP/RUN 상태 관리
- 주기적 거래 사이클 실행

### 4. API 엔드포인트
- **파일**: `services/dashboard-api/app/routers/trades.py`
- `/api/trades/signal` - 신호 기록
- `/api/trades/order` - 주문 기록
- `/api/trades/signals` - 신호 리스트
- `/api/trades/positions` - 포지션 리스트

## 생성된 파일 목록

### Trader 서비스
- `services/trader/screener.py` - 스크리닝 모듈
- `services/trader/scoring.py` - 5개 스코어 모듈
- `services/trader/score_aggregator.py` - 점수 집계
- `services/trader/position_sizer.py` - 포지션 사이징
- `services/trader/pre_trade_check.py` - 진입 전 체크
- `services/trader/order_executor.py` - 주문 실행
- `services/trader/position_manager.py` - 포지션 관리
- `services/trader/trading_engine.py` - 거래 엔진 통합
- `services/trader/requirements.txt` - 의존성
- `services/trader/main.py` - 메인 루프 (수정)

### Dashboard API
- `services/dashboard-api/app/models_trading.py` - 거래 관련 모델
- `services/dashboard-api/app/routers/trades.py` - 거래 API
- `services/dashboard-api/app/models.py` - 모델 import 추가
- `services/dashboard-api/app/migrate.py` - 마이그레이션 업데이트
- `services/dashboard-api/app/routers/traders.py` - GET /traders/{name} 추가

## 주요 기능

### 스코어링 규칙
- 각 모듈: 0-100 정규화 점수
- 기본 가중치: TP(0.30), VCB(0.25), Regime(0.20), LSR(0.15), LF(0.10)
- EMA 평활화 (α=0.3)
- ENTRY_THRESHOLD: 70
- EXIT_THRESHOLD: 40

### 포지션·리스크 규칙
- RISK_PER_TRADE: 1%
- MAX_PORTFOLIO_RISK: 5%
- 슬리피지 제한: 0.5%
- 트레일링 스톱: 2% 이상 수익 시 활성화
- 스케일아웃: 3단계 익절

### Pre-trade 체크리스트
1. ✅ total_score ≥ 70
2. ✅ regime 허용 (PANIC/CHOP 차단)
3. ✅ 유동성 체크 (depth ratio ≤ 0.3)
4. ✅ 예산 확인
5. ✅ 중복 포지션 방지
6. ✅ API health
7. ✅ Trading hours (24시간)
8. ✅ Risk manager 승인 (자동)

## 다음 단계

1. **DB 마이그레이션 실행**
   ```bash
   docker-compose up -d dashboard-api
   # Base.metadata.create_all()로 자동 생성됨
   ```

2. **Trader 서비스 테스트**
   ```bash
   docker-compose build trader
   docker-compose up trader
   ```

3. **실제 거래 연동** (LIVE 모드)
   - `order_executor.py`의 LIVE 모드 구현
   - Upbit API 실제 주문 연동
   - 자격증명 복호화 구현

4. **모니터링 강화**
   - Dashboard에 포지션/신호 표시
   - 실시간 수익률 차트 업데이트

## 참고사항

- Paper 모드는 가상 실행으로 구현됨
- LIVE 모드는 구조만 준비되어 있음 (실제 주문 연동 필요)
- 자격증명 복호화는 나중에 구현 필요
- 상관관계 계산은 간단화됨 (실제로는 과거 수익률 상관관계 계산 필요)
