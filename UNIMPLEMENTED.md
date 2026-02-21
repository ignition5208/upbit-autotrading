# 미구현 기능 명세서

> 기준일: 2026-02-22
> 참조: 지침.md 전체 (§1~§10)

---

## 🔴 Critical — 핵심 거래 로직 미구현

### C-1. Final Score 계산식 미적용
**파일**: `trader/trading_engine.py`
**증상**: `base_score` 만 사용, `regime_weight × bandit_weight × risk_multiplier` 가 곱해지지 않음
**지침 참조**: §5.3 Score 계산식
**구현 목표**:
```python
regime_weight  = GET /api/regimes/weight/{regime_label}/{strategy_id}
bandit_weight  = sample_bandit_weight(regime, strategy_id)  # 0.5 ~ 1.5
risk_multiplier = { SAFE: 0.3, STANDARD: 0.5, PROFIT: 0.7, CRAZY: 1.0 }[risk_mode]
final_score = base_score * regime_weight * bandit_weight * risk_multiplier
```

---

### C-2. LIVE 모드 실주문 미구현
**파일**: `trader/order_executor.py`
**증상**: LIVE 분기에 `pass` 또는 로깅만 존재, `pyupbit.buy_market_order()` 미호출
**지침 참조**: §5.4 주문 실행
**구현 목표**:
```python
# 매수
upbit.buy_market_order(market, krw_amount)

# 매도
upbit.sell_market_order(market, coin_amount)

# 오류 시 3회 재시도, 실패 시 해당 마켓 10분 블랙리스트
```

---

### C-3. Credential 복호화 미구현
**파일**: `trader/main.py` (또는 `trader/boot.py`)
**증상**: 트레이더 컨테이너가 Upbit Access/Secret Key를 복호화하는 로직이 없음
**지침 참조**: §3 Credential 관리
**구현 목표**:
```python
# GET /api/credentials/{credential_name}/decrypt 호출
resp = httpx.get(f"{DASHBOARD_API_BASE}/api/credentials/{CREDENTIAL_NAME}/decrypt")
access_key = resp.json()["access_key"]
secret_key  = resp.json()["secret_key"]
upbit = pyupbit.Upbit(access_key, secret_key)
```
- `dashboard-api/app/routers/credentials.py` 에 `/decrypt` 엔드포인트 신규 추가 필요

---

### C-4. LIVE 포지션 실제 청산 미구현
**파일**: `trader/position_manager.py`
**증상**: 보유 포지션 청산 조건 체크는 존재하나, LIVE 모드에서 실제 `sell_market_order` 미호출
**지침 참조**: §5.5 청산 조건
**구현 목표**:
```python
# 손절 조건: loss > stop_loss
# 점수 하락: score < exit_threshold
# PANIC 감지: 기존 포지션 50% 강제 축소
upbit.sell_market_order(market, holding_amount * ratio)
```

---

## 🟡 High — 자동화 루프 미연결

### H-1. Trainer API 엔드포인트 미연결
**파일**: `trainer/main.py`, `dashboard-api/app/routers/trainer.py`
**증상**: `trainer/main.py`가 `/api/trainer/scan` 등을 호출하려 하지만 해당 라우터에 엔드포인트 없음
**지침 참조**: §8 OPT-0001 Feature 수집
**구현 목표**:
- `POST /api/trainer/scan` — ScanRun 생성 + FeatureSnapshot 저장
- `POST /api/trainer/evaluate` — OPT-0002 게이트 평가 (Sharpe > 0.5 등)
- `POST /api/trainer/bandit-update` — OPT-0004 Bandit alpha/beta 갱신

---

### H-2. OPT-0004 CHOP/PANIC 시 Bandit 비활성화 미구현
**파일**: `dashboard-api/app/services/bandit.py`
**증상**: CHOP, PANIC 레짐에서도 Bandit 가중치가 정상 적용됨
**지침 참조**: §8.4 Bandit 비활성화 조건
**구현 목표**:
```python
def sample_bandit_weight(db, regime, strategy_id) -> float:
    if regime in ("CHOP", "PANIC"):
        return 0.0  # 진입 자체를 막음
    ...
```

---

### H-3. 수익 차트 데이터 미연결
**파일**: `dashboard-web/app.js` → `loadChart()`
**증상**: `points: []` 빈 배열로 초기화, 실제 PnL 데이터 미조회
**지침 참조**: §2 대시보드 수익 차트
**구현 목표**:
```javascript
// GET /api/trades?trader_name=X&limit=200 로 체결 내역 조회
// cumulative PnL 계산 후 Canvas 차트에 렌더링
```
- `dashboard-api/app/routers/trades.py` 에 `?trader_name=` 필터 추가 필요

---

### H-4. 주문 재시도 + 블랙리스트 미구현
**파일**: `trader/order_executor.py`
**증상**: 주문 실패 시 즉시 포기, 재시도 없음
**지침 참조**: §5.4 주문 안전망
**구현 목표**:
```python
for attempt in range(3):
    try:
        result = upbit.buy_market_order(...)
        break
    except Exception:
        time.sleep(1)
else:
    blacklist[market] = time.time() + 600  # 10분 블랙리스트
```

---

### H-5. 신호 기록 DB 미저장
**파일**: `trader/trading_engine.py`
**증상**: 진입/청산 신호 계산 결과가 로그에만 출력, `trades` 테이블 미저장
**지침 참조**: §5.6 이력 관리
**구현 목표**:
```python
POST /api/trades {
  trader_name, market, side, qty, price, score,
  regime, strategy_id, ts
}
```

---

### H-6. OPT-0003 자동 튜닝 실 미구현
**파일**: `trainer/main.py` → `auto_tuning()` 함수
**증상**: 스텁(stub) 상태, 실제 파라미터 최적화 알고리즘 없음
**지침 참조**: §8.3 OPT-0003
**구현 목표**:
- 최근 7일 FeatureSnapshot 로드
- Sharpe / E(r_net) 기준으로 파라미터 그리드 서치
- 최적 파라미터 → `POST /api/configs` + activate

---

## 🟠 Medium — 지표 / 안전장치 정밀도 개선

### M-1. ADX 계산 단순화
**파일**: `regime-engine/indicators.py`
**증상**: ADX 계산이 모든 타임스탬프에 동일 값 반환 (간소화된 스텁)
**구현 목표**: Wilder's Smoothing 방식의 표준 ADX(14) 구현

---

### M-2. Drift 감지 통계 미흡
**파일**: `dashboard-api/app/services/drift_detection.py`
**증상**: 단순 평균 비교만 사용, KL-divergence 또는 KS-test 미적용
**지침 참조**: §9 STAB-0002
**구현 목표**: `scipy.stats.ks_2samp` 또는 KL-divergence 기반 drift score 계산

---

### M-3. 상관관계 체크 단순화
**파일**: `trader/position_manager.py`
**증상**: 포지션 간 상관관계 체크가 고정 임계값 비교만 수행
**지침 참조**: §5.5.2 포트폴리오 리스크
**구현 목표**: Pearson 상관계수 기반 포지션 집중도 제한

---

### M-4. 시가총액 근사치 부정확
**파일**: `regime-engine/main.py` → universe 선정 로직
**증상**: KRW 거래량을 시가총액 대리 지표로 사용하는 근사치
**구현 목표**: Upbit `GET /v1/ticker?markets=...` 의 `acc_trade_price_24h` 사용 + 상위 20 정확히 선정

---

### M-5. 분할 진입 (Slippage 제한) 미구현
**파일**: `trader/order_executor.py`
**증상**: 일괄 시장가 주문, 슬리피지 제한 및 분할 주문 없음
**지침 참조**: §5.4.3 슬리피지
**구현 목표**:
```python
# slippage_limit 초과 시 주문 분할 (2~3회)
if estimated_slippage > slippage_limit:
    split_order(market, amount, parts=3)
```

---

## 🔵 Low — UI / 편의 기능

### L-1. Strategy EDIT 후 트레이더 재배포 없음
**파일**: `dashboard-web/app.js` → `openStrategyEdit()`
**증상**: 전략 파라미터 저장 후 해당 전략을 사용하는 트레이더 컨테이너가 재시작되지 않음
**구현 목표**:
```javascript
// ConfigVersion 저장 후
for (const trader of traders.filter(t => t.strategy === s)) {
  await api('POST', `/api/traders/${trader.name}/restart`);
}
```

---

### L-2. CONFIG 탭 Telegram 설정 섹션 없음
**파일**: `dashboard-web/app.js` → `renderConfig()`
**증상**: CONFIG 탭에 BOT TOKEN / CHAT ID 입력란이 없음
**지침 참조**: §H-2
**구현 목표**:
- BOT TOKEN, CHAT ID 입력 필드 (마스킹)
- 저장 → `POST /api/configs` (telegram 파라미터 포함)
- 테스트 알람 버튼

---

### L-3. 완료 조건 체크리스트 UI 없음
**파일**: `dashboard-web/app.js` (신규 탭 또는 모달)
**증상**: 트레이더 PAPER → ARM → LIVE 전환 조건 체크리스트 UI 없음
**구현 목표**:
- 보호기간 경과 ✅ / ⬜
- 최소 거래 횟수 달성 ✅ / ⬜
- Sharpe Ratio 0.5 이상 ✅ / ⬜
- 드리프트 없음 ✅ / ⬜

---

## 구현 우선순위 요약

| 우선순위 | 항목 | 파일 |
|---------|------|------|
| 🔴 C-1 | Final Score 계산식 | `trader/trading_engine.py` |
| 🔴 C-2 | LIVE 실주문 | `trader/order_executor.py` |
| 🔴 C-3 | Credential 복호화 | `trader/main.py` + `credentials.py` |
| 🔴 C-4 | LIVE 포지션 청산 | `trader/position_manager.py` |
| 🟡 H-1 | Trainer API 연결 | `dashboard-api/routers/trainer.py` |
| 🟡 H-2 | Bandit CHOP/PANIC 비활성화 | `services/bandit.py` |
| 🟡 H-3 | 수익 차트 데이터 | `dashboard-web/app.js` |
| 🟡 H-4 | 주문 재시도 | `trader/order_executor.py` |
| 🟡 H-5 | 신호 기록 저장 | `trader/trading_engine.py` |
| 🟡 H-6 | OPT-0003 자동 튜닝 | `trainer/main.py` |
| 🟠 M-1 | ADX 표준 계산 | `regime-engine/indicators.py` |
| 🟠 M-2 | Drift KS-test | `services/drift_detection.py` |
| 🟠 M-3 | 상관관계 Pearson | `trader/position_manager.py` |
| 🟠 M-4 | Universe 정확한 선정 | `regime-engine/main.py` |
| 🟠 M-5 | 분할 주문 | `trader/order_executor.py` |
| 🔵 L-1 | Strategy EDIT → 재배포 | `dashboard-web/app.js` |
| 🔵 L-2 | Telegram CONFIG UI | `dashboard-web/app.js` |
| 🔵 L-3 | 완료 조건 체크리스트 | `dashboard-web/app.js` |
