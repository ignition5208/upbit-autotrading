---

# 🚀 Upbit Auto-Trading Platform

# 📘 기능명세서 v1.8-0010 (UI 고정 안정화 버전)

---

# 0) 목표

Upbit 단일 거래소 기반의 멀티 Trader 자동매매 플랫폼.

각 Trader는:

* 하나의 **Score-Strategy**
* 하나의 **Risk Profile**
* 하나의 **운영 모드 (LIVE / PAPER)**

를 선택하여 자동매매를 수행한다.

---

## v1.8-0010 포함 범위

* Score-Strategy 구조
* Regime Engine v1.0
* AI 자동 튜닝 (OPT-0001 ~ 0004)
* Multi-Armed Bandit 메타전략
* 안정성 설계 (STAB-0001 ~ 0003)
* Telegram 알람 시스템
* UI 메뉴 완전 고정 (웹 구조 불변화)

---

# 1) 핵심 고정 사항 (변경 불가)

1. 거래소: **Upbit**
2. DB: **MariaDB (named volume 필수)**
3. 배포: **docker-compose**
4. 초기 실행 시 trader 컨테이너 0개
5. trader는 UI에서 추가 시 동적 생성
6. 동일 코인 중복 매수 허용
7. 운영 모드: LIVE / PAPER
8. LIVE는 ARM 이후 거래 가능
9. 전략 구조: **Score = Strategy**
10. Risk Profile:

* SAFETY FIRST
* STANDARD
* PROFIT FIRST
* CRAZY
* AI MODE

11. dashboard-api는 주문 호출 금지
12. 전략 코드 반영은 recreate 방식만 허용
13. UI 메뉴 구조는 고정 (변경 금지)

---

# 2) 시스템 구성

```
docker-compose
 ├── mariadb
 ├── dashboard-api
 ├── dashboard-web
 ├── trader (동적)
 └── trainer (AI 전용)
```

---

# 3) 전략 구조 (Score-Strategy)

각 전략은 반드시 포함해야 한다:

* Universe 선정
* Feature 계산
* Base Score 계산
* Entry / Exit 규칙
* Risk Profile 적용
* Regime 가중치 적용
* Bandit 가중치 적용

---

## 최종 스코어 계산식

```
final_score =
base_score
× regime_weight
× bandit_weight
× risk_multiplier
```

---

# 4) Regime Engine v1.0

## 4.1 레짐 라벨

* BREAKOUT_ROTATION
* TREND
* RANGE
* CHOP
* PANIC

---

## 4.2 레짐 입력 지표 (6개 고정)

* btc_adx_4h
* btc_atr_pct_4h
* breadth_up_1h
* dispersion_1h
* top5_value_share_1h
* whipsaw_5m

---

## 4.3 레짐 가중치 적용

```
applied_weight = 1 + (w - 1) × (regime_score / 100)
```

### 특수 규칙

* CHOP → 신규 진입 금지
* PANIC → 신규 진입 금지 + 기존 포지션 축소 가능

---

# 5) AI 지속 학습 시스템

AI는 **전략을 대체하지 않는다.**
AI는 전략을 보조 최적화한다.

---

## OPT-0001 데이터 파이프라인

### 신규 테이블

* scan_runs
* feature_snapshots

### 라벨

* label_ret_60m
* label_ret_240m
* label_mfe_240m
* label_mae_240m
* label_dd_240m

### 비용 반영 수익

```
r_net = r - (2 × fee + 2 × slippage)
```

---

## OPT-0002 평가 & 게이트

평가 지표:

* E (mean r_net)
* Sharpe
* Q05 / Q01
* MAE_mean / MAE_95
* SPD (signals per day)

### 상태 결정

* PASS
* HOLD
* REJECT

하드 실패 조건 존재 (문서화 필요)

---

## OPT-0003 자동 튜닝

튜닝 대상:

* feature_weights
* penalty_weights
* score_threshold
* topn
* regime_policy multiplier

탐색:

* TPE / Bayesian Optimization
* 후보 수 K=60

게이트 통과 후보만 채택.

---

## OPT-0004 Bandit 메타전략

State = regime_label

전략 reward 기반 Thompson Sampling.

bandit_weight 범위:

```
0.5 ~ 1.5
```

CHOP / PANIC 에서는 비활성화.

---

# 6) 안정성 설계

## STAB-0001 Runtime Guard

* Daily Loss Limit
* Consecutive Loss Limit
* Slippage anomaly detection
* API/DB 장애 시 신규 진입 금지
* PANIC 자동 차단

---

## STAB-0002 Baseline & Drift

* baseline_model_id 유지
* 14일 baseline reference window
* 24h rolling metrics
* DRIFT_WARN
* AUTO_ROLLBACK

### 자동 롤백 조건

* net_return_24h < -2%
* drift_warn 3회 연속
* consecutive_losses ≥ 5

---

## STAB-0003 Telegram 알람

중요 이벤트 Telegram 전송.

레벨:

* INFO
* WARN
* CRITICAL

### 강제 정책

* 새 전략은 24시간 PAPER 보호기간 필수
* 보호기간 중 LIVE 전환 금지

---

# 7) 모델 배포 절차

```
DRAFT
→ VALIDATED (PASS)
→ PAPER_DEPLOYED (24h)
→ LIVE_ELIGIBLE
→ LIVE_ARMED
```

롤백:

* AUTO_ROLLBACK
* MANUAL_ROLLBACK

재배포 쿨다운: 24시간

---

# 8) DB 보존 정책

down/up 이후에도 유지:

* traders
* market_regimes
* model_versions
* model_candidates
* feature_snapshots
* scan_runs
* trader_safety_state
* bandit_states
* config_versions
* events

---

# 9) UI 구조 (완전 고정)

⚠ 이 메뉴 구조는 변경 불가.

---

## 9.1 상단 NAV BAR (가로형)

* DASHBOARD
* TRADERS
* STRATEGY
* CONFIG

---

## 9.2 DASHBOARD 메뉴

### 표시 항목

* CURRENT REGIME
* TOTAL TRADER
* PAPER TRADER
* LIVE TRADER
* PROFIT CHART
  → 모든 Trader 수익률을 하나의 차트에 표시
* TRADERS ACTION LOG
  → 실시간 액션 로그 출력

---

## 9.3 TRADERS 메뉴

### (1) TRADER ADD 버튼

팝업 입력 후 CREATE

입력 항목:

* NAME
* STRATEGY (STRATEGY 메뉴에서 등록된 전략)
* SEED MONEY
* CREDENTIAL

---

### (2) Trader 리스트 테이블

| 항목                | 설명                      |
| ----------------- | ----------------------- |
| TRADER NAME       | 이름                      |
| TRADER SEED       | 초기 자본                   |
| TRADER STRATEGY   | 선택 전략                   |
| TRADER PROFIT     | 수익                      |
| TRADER RUN        | LIVE / PAPER 선택 후 APPLY |
| TRADER MANAGEMENT | RUN / STOP / REMOVE     |

모든 실행은 팝업 APPLY / CANCEL 구조.

---

## 9.4 STRATEGY 메뉴

전략 프로파일 선택 화면

* SAFETY FIRST
* STANDARD
* PROFIT FIRST
* CRAZY
* AI MODE

⚠ 전략 프로파일 수정은 여기서만 가능.

---

## 9.5 CONFIG 메뉴

### CREDENTIAL 리스트

* ADD
* DELETE

---

# 10) 완료 조건

1. 레짐 기반 전략 가중치 적용
2. Bandit 가중치 동적 적용
3. AI 자동 튜닝 + 게이트 검증
4. 24h PAPER 보호기간 강제
5. Drift 감지 + 자동 롤백
6. Telegram 실시간 알람
7. LIVE는 ARM 전 주문 금지
8. UI 메뉴 구조 변경 금지

---

# 🎯 v1.8-0010 아키텍처 철학

* 전략은 deterministic
* AI는 보조 계층
* 모든 자동 변경은 rollback 가능
* 수익보다 생존 우선
* 레짐 적응 + 리스크 통제 + 검증 기반 진화
* UI는 고정, 내부 로직만 진화

---

# 전체 개요

목표: 스크리닝 → 레짐 판단 → 스코어링(5개 기법) → 진입 전 유동성/리스크 검사 → 주문 실행 → 포지션 관리 → 로그/모니터링.
모듈은 독립성(plug-in)이 있어야 하며, 각 모듈은 입력/출력 인터페이스를 명확히 가져야 한다.

# 1. 시스템 아키텍처 (모듈 구성)

1. 데이터 레이어

   * 시계열 저장(원시 캔들/틱), 호가 depth, 체결 스트림, 계좌/포지션 상태.
   * 주 DB: MariaDB (신호/거래 로그), 보조 TSDB(예: Prometheus/Influx) 권장.

2. 인제스트(collector)

   * 거래소 API / WebSocket으로 OHLCV, depth, trades, 주문/체결 스트림 수집.
   * TTL·리트라이·백프레셔 처리 필요.

3. 스크리너 (Screener)

   * 전체 마켓 → 후보(예: top N 거래대금) 필터링.
   * 출력: 후보 리스트 + 필터 리즌(메타데이터).

4. 레짐 평가기 (Regime Engine)

   * 입력: BTC/시장 지표, ADX, VIX-like, ATR, recent returns.
   * 출력: `regime ∈ {STRONG_UP, TREND_UP, RANGE, WEAK, TREND_DOWN, HIGH_RISK}` + score/confidence.

5. 스코어 모듈(플러그인 형태, 각 모듈은 0–100 정규화 점수 반환)

   * Trend Pullback (TP)
   * Volatility Contraction Breakout (VCB)
   * Liquidity Sweep Reversal (LSR)
   * Leader-Follower (LF)
   * Regime Modifier (global)
   * 각 모듈은 “설명 가능한 이유(reason codes)” 반환(예: EMA50>EMA200, fib pull 0.382 충족 등).

6. 종합 점수 엔진 (Score Aggregator)

   * 가중치 합: `total_score = Σ (w_i * norm_score_i)`
   * 정규화 + 캘리브(예: 지수 가중 이동 평균으로 스코어 평활화) 제공.

7. 포지션 사이징 & 리스크 엔진

   * 입력: equity, RISK_PER_TRADE, MAX_PORTFOLIO_RISK, SL 거리, 예상 슬리피지/호가 depth.
   * 출력: position_size, expected_order_krw, stop_price, take_prices(스케일아웃 계획).

8. 유동성·상관검사 (Pre-trade checks)

   * 호가 depth 대비 expected_order_krw → liquidity_ratio 계산.
   * 현재 오픈 포지션과 후보의 avg_pairwise_corr 계산 → corr_factor.
   * 규칙 위반 시 `REJECT` + reason.

9. 주문 실행기 (Order Executor)

   * 지정가 우선, 분할진입, IOC/POC 옵션, 주문 재시도 로직, 부분체결 처리, 체결 감시.
   * 체결 실패시 롤백 정책(예: 잔량 취소 후 로그 + 알람).

10. 포지션 매니저 (Position Manager)

    * 트레일링, 스케일아웃, 자동 SL/TP, regime 변화시 자동 축소/청산.
    * 포지션 상태는 주 DB에 실시간 업데이트.

11. 로깅·감사 (Audit)

    * signals, orders, fills, position changes, config changes 모두 불변 로그로 기록.

12. 모니터링·알람

    * 핵심 메트릭: max_positions, open_positions_count, remaining_budget, avg_corr, avg_depth_ratio, slippage, failed_orders, PnL.
    * 알람 채널: Telegram/Slack + 대시보드 배지. (마스터 킬스위치 포함)

# 2. 모듈 인터페이스 사양 (입출력 예시)

* Screener → Candidate: `[{symbol, 24h_volume, spread, avg_depth5, volatility, reason_flags}]`
* Regime Engine → any: `{regime, confidence, adx, btc_24h_pct, vix_like}`
* Score Module (each) → Aggregator: `{symbol, score:0-100, reason_codes:[...], raw_metrics:{...}}`
* Position Sizer → Executor: `{symbol, size, entry_price_target, stop_price, take_prices[], estimated_fee, expected_order_krw}`
* Executor → DB: `{order_id, symbol, side, price, size, status, filled_qty, avg_price, timestamp}`

# 3. 스코어링 규칙 (정규화 & 가중치)

1. 정규화: 각 모듈은 자체 raw metric → 0~100 선형 또는 logistic 스케일로 변환.
2. 기본 가중치 (권장)

   * TP: 0.30, VCB: 0.25, Regime: 0.20, LSR: 0.15, LF: 0.10
   * 가중치는 config로 동적 조정 가능.
3. Aggregator는 `total_score` 산출 후, 점수 안정화를 위해 `EMA(total_score, α=0.3)` 적용(노이즈 완화).
4. Entry threshold default: `ENTRY_THRESHOLD = 70`, Exit threshold: `EXIT_THRESHOLD = 40`.
5. 점수 근거(Explainability): 모든 진입 신호와 핵심 수치(예: EMA 차이, 볼린저 폭, ATR 비율, volume spike %)를 함께 저장.

# 4. 포지션·리스크 규칙(정책)

* `RISK_PER_TRADE`: 기본 0.5% ~ 1.0% (config)
* `MAX_PORTFOLIO_RISK`: 기본 5% (동시 오픈 포지션 전체 예상 손실 합계)
* 포지션 사이징: `position_size = dollar_risk / (entry_price - stop_price)` (현물), 레버리지 경우는 마진 계산 포함.
* 슬ippage cap: 예상 슬리피지 > 0.5% 이면 포지션 축소/재검토.
* Max concurrent positions = computed `max_positions` (자동로직 적용, 아래 지침 참조).
* 동일 섹터 상한: 동일 sector(또는 상관>0.7) 내 포지션 상한 2개.
* 마스터 킬스위치: 하루 순손실 > `DAILY_LOSS_LIMIT`(예: 5%) 시 신규 진입 전면 중지.

# 5. 사전(진입 전) 체크리스트 — 반드시 통과해야 진입

1. total_score ≥ ENTRY_THRESHOLD
2. regime 허용(예: HIGH_RISK 시 롱 금지)
3. expected_order_krw ≤ avg_depth * LIQUIDITY_MIN_RATIO (기본 0.3)
4. remaining_budget ≥ RISK_PER_TRADE
5. 후보 심볼 avg_pairwise_corr 와 open positions 고려해 corr_factor 확인
6. rate_limit/API health 정상
7. trading hours / exchange maintenance 체크
8. risk manager 승인(자동)

# 6. 로그·DB 스키마(요약)

* `signals` (id, symbol, ts, total_score, scores_json, regime, action)
* `orders` (order_id, symbol, side, price, size, status, filled_qty, avg_price, error)
* `trades` (trade_id, symbol, entry_time, entry_price, entry_size, stop_price, exit_time, exit_price, pnl, mode)
* `positions` (symbol, open_time, avg_entry_price, size, current_price, unreal_pnl, stop_price, tags)
* 변경/설정 audit 테이블(누가 언제 config 변경했는지)

# 7. 모니터링·대시보드 항목 (우선순위)

* 실시간: `max_positions`, `open_positions_count`, `remaining_slots`
* 리스크: `current_portfolio_risk %`, `daily_pnl %`, `largest_unreal %`
* 유동성: `avg_depth_ratio` per candidate
* 안정성: 주문 실패율, 체결 지연 평균, API latency
* 시그널 품질: win_rate per strategy, avg holding time, PF(Profit Factor)
* 알람: remaining_budget < RISK_PER_TRADE, avg_corr > 0.75, failed_order_rate > 2%

# 8. 테스트·검증 절차

1. 유닛 테스트: 각 score 모듈의 경계값, extreme inputs 테스트 (예: zero volume, NaN inputs)
2. 통합 테스트: 스크리닝 → 점수 → sizing → 가상 order flow(모의 체결)
3. 백테스트: 과거 6~24개월, 시나리오별(강세, 약세, 유동성 축소)
4. 전방테스트(Forward Test): PAPER 모드에서 2~4주 실거래 시뮬레이션
5. 레그레션: config 변경 시 성능 하락 여부 자동 리포팅
6. 성능 테스트: 수집/계산 파이프가 N symbols × M frequency(예: 500 sym × 1min) 처리 가능한지 측정

# 9. 장애 대응·운영 룰북 (Runbook)

* 주문 반복 실패 → 3회 재시도 후 해당 심볼 블랙리스트 10분, 관리자 알람.
* DB 연결 불가 → 모든 신규 주문 중지, 모니터링 알람, 복구 로그.
* API rate limit 발동 → 스크리너/점수 빈도 감축(백오프).
* 마스터 킬스위치 발동(예: 대규모 손실) → 모든 포지션 자동 청산(옵션), 알람 및 수동 확인.
* 정기 건강체크: 매일 00:00 UTC 시스템 self-test 실행(수집/exec/test order).

# 10. 운영 파라미터(초기 권장값 — 운영자가 바로 조정 가능)

* `ENTRY_THRESHOLD = 70`
* `EXIT_THRESHOLD = 40`
* `RISK_PER_TRADE = 0.01` (1%)
* `MAX_PORTFOLIO_RISK = 0.05` (5%)
* `BASE_BY_REGIME` = {STRONG_UP:7, TREND_UP:5, RANGE:3, WEAK:2, TREND_DOWN:1}
* `LIQUIDITY_MIN_RATIO = 0.3`
* `ABSOLUTE_MAX_POSITIONS = 10`
* `CORR_HIGH = 0.7` (동일 섹터/상관 판단 기준)
* `SLIPPAGE_LIMIT = 0.005` (0.5%)

# 11. 운영 체크포인트(데일리/위클리)

* 매일: 시그널 품질 리포트(전일 trades, win_rate, avg_pnl)
* 매주: 파라미터 튜닝 제안(ENTRY/EXIT threshold, weights)
* 매월: 백테스트 리런(새 데이터 포함), ADR(annualized drawdown) 리뷰

# 12. 보안·규정·윤리

* API 키 관리: 권한 최소화(트레이드 전용), 키 로테이션 정책, 비밀관리(Sealed Vault).
* 거래소(Upbit) 규정 준수: 거래 제한, 상장/상장폐지 알림 반영.
* 로그 보존: 거래 로그 7년(회계/규정에 따른 보관 권장).

# 13. 배포·운영 권장 (엔지니어링)

* 각 모듈을 컨테이너화(Docker) → 오케스트레이션(Kubernetes)으로 배포.
* 각 Score Module은 독립 서비스(플러그인)로 배포하여 A/B 테스트 용이.
* CI: 유닛·통합·백테스트 파이프라인(머지 전 자동 실행).
* Canary release: 파라미터 바꿀 때는 소수 트레이더 인스턴스에서 캔서리 적용 후 전체 롤아웃.

# 14. 실행 예시 시나리오(요약)

1. Screener가 후보 30개 추출.
2. Regime Engine이 TREND_UP 판정 → base=5.
3. 각 심볼에 대해 TP/VCB/LSR/LF 스코어 산출 → Aggregator에서 total_score 계산.
4. 상위 score 심볼을 pre-trade 체크 진행 → liquidity, corr, risk 검사 통과 시 position_sizer가 size 산출.
5. Executor가 분할 지정가 주문으로 진입 → Position Manager가 SL/TP 및 트레일 활성화.
6. 포지션 모니터링: regime 변화 또는 score 하락 시 부분/전체 청산.

# 15. 문서·운영 템플릿 (권장)

* API 명세서(모듈별)
* Config 참조문서 (설정 값 설명)
* Runbook(장애 절차)
* 체크리스트(진입 전 8개 항목) — UI에 바로 붙일 수 있도록 텍스트 파일로 준비

---