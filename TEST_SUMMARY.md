# 단위 테스트 요약

## 생성된 테스트 파일

### Regime Engine
- ✅ `services/regime-engine/tests/test_indicators.py` (약 20개 테스트 함수)

### Dashboard API
- ✅ `services/dashboard-api/tests/conftest.py` (공통 fixtures)
- ✅ `services/dashboard-api/tests/test_regime.py` (약 10개 테스트 함수)
- ✅ `services/dashboard-api/tests/test_safety_guard.py` (약 15개 테스트 함수)
- ✅ `services/dashboard-api/tests/test_drift_detection.py` (약 10개 테스트 함수)
- ✅ `services/dashboard-api/tests/test_model_evaluation.py` (약 15개 테스트 함수)
- ✅ `services/dashboard-api/tests/test_data_pipeline.py` (약 10개 테스트 함수)

**총 테스트 파일**: 6개
**예상 테스트 함수 수**: 약 80개 이상

## 테스트 커버리지

### ✅ 완료된 테스트 영역

1. **Regime Engine 지표 계산**
   - ADX, ATR, Breadth, Dispersion, Top5 Share, Whipsaw 계산
   - Regime 분류 (PANIC, CHOP, TREND, RANGE)

2. **Regime 가중치 및 특수 규칙**
   - 가중치 계산 공식 검증
   - CHOP/PANIC 진입 차단
   - 포지션 축소 로직

3. **Runtime Guard**
   - Slippage 이상 감지
   - API/DB 에러 기록 및 차단
   - PANIC 자동 차단

4. **Baseline & Drift 감지**
   - Baseline 생성 및 관리
   - 24시간 메트릭 기록
   - Drift 감지 및 경고
   - 자동 롤백 조건 확인

5. **모델 평가**
   - 평가 지표 계산 (E, Sharpe, Q05/Q01, MAE, SPD)
   - PASS/HOLD/REJECT 상태 결정
   - 하드 실패 조건 확인

6. **데이터 파이프라인**
   - 라벨 계산 (60m, 240m)
   - Feature 계산
   - 기술적 지표 (RSI, MACD, EMA, 볼린저 밴드)

## 테스트 실행 방법

```bash
# 1. 의존성 설치
cd services/dashboard-api
pip install -r requirements.txt

# 2. Regime Engine 테스트
cd ../regime-engine
pip install -r requirements.txt pytest
pytest tests/test_indicators.py -v

# 3. Dashboard API 테스트
cd ../dashboard-api
pytest tests/ -v

# 4. 커버리지 포함
pytest tests/ --cov=app --cov-report=html
```

## 주요 테스트 시나리오

### 1. Regime 분류
- ✅ PANIC: 높은 변동성 + 낮은 상승 비율
- ✅ CHOP: 높은 휩소 + 낮은 ADX
- ✅ TREND: 높은 ADX + 낮은 휩소
- ✅ RANGE: 기본값

### 2. 안전성 검증
- ✅ Slippage 이상 3회 → 블록
- ✅ API 에러 5회 → 블록
- ✅ DB 에러 3회 → 블록
- ✅ PANIC 레짐 → 자동 차단

### 3. Drift 감지
- ✅ Sharpe 30% 하락 → 경고
- ✅ 수익률 50% 하락 → 경고
- ✅ 경고 3회 연속 → 롤백
- ✅ 24h 수익률 -2% → 롤백

### 4. 모델 평가
- ✅ PASS: 수익률 > 1%, Sharpe > 0.5
- ✅ REJECT: 수익률 < -5%, Sharpe < -1.0
- ✅ 하드 실패: 수익률 < -10%, Sharpe < -2.0

## 다음 단계

1. **통합 테스트**: API 엔드포인트 통합 테스트 추가
2. **성능 테스트**: 대용량 데이터 처리 테스트
3. **E2E 테스트**: 전체 워크플로우 테스트
4. **CI/CD 통합**: GitHub Actions 등에 테스트 자동화

## 참고

자세한 테스트 가이드는 `TESTING.md`를 참고하세요.
