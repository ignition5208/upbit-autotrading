# 단위 테스트 가이드

## 테스트 구조

```
services/
├── regime-engine/
│   └── tests/
│       └── test_indicators.py      # Regime Engine 지표 계산 테스트
└── dashboard-api/
    └── tests/
        ├── conftest.py             # 공통 fixtures
        ├── test_regime.py          # Regime 가중치 및 특수 규칙 테스트
        ├── test_safety_guard.py    # Runtime Guard 테스트
        ├── test_drift_detection.py # Baseline & Drift 감지 테스트
        ├── test_model_evaluation.py # 모델 평가 테스트
        └── test_data_pipeline.py   # 데이터 파이프라인 테스트
```

## 테스트 실행 방법

### 1. 의존성 설치

```bash
# Regime Engine
cd services/regime-engine
pip install -r requirements.txt pytest

# Dashboard API
cd services/dashboard-api
pip install -r requirements.txt
```

### 2. 테스트 실행

#### Regime Engine 테스트
```bash
cd services/regime-engine
pytest tests/test_indicators.py -v
```

#### Dashboard API 테스트
```bash
cd services/dashboard-api
pytest tests/ -v
```

#### 특정 테스트 파일 실행
```bash
pytest tests/test_regime.py -v
pytest tests/test_safety_guard.py -v
```

#### 특정 테스트 함수 실행
```bash
pytest tests/test_regime.py::TestRegimeWeight::test_calculate_regime_weight_normal -v
```

#### 커버리지 포함 실행
```bash
pytest tests/ --cov=app --cov-report=html
```

## 테스트 커버리지

### Regime Engine (test_indicators.py)
- ✅ ADX 계산 테스트
- ✅ ATR 퍼센트 계산 테스트
- ✅ Breadth (상승 비율) 계산 테스트
- ✅ Dispersion (분산도) 계산 테스트
- ✅ Top5 시가총액 비중 계산 테스트
- ✅ Whipsaw (휩소) 계산 테스트
- ✅ Regime 점수 계산 및 분류 테스트 (PANIC, CHOP, TREND, RANGE)

### Dashboard API

#### test_regime.py
- ✅ Regime 가중치 계산 테스트
- ✅ CHOP/PANIC 신규 진입 차단 테스트
- ✅ 포지션 축소 필요 여부 확인 테스트

#### test_safety_guard.py
- ✅ Slippage 이상 감지 테스트
- ✅ API/DB 에러 기록 및 차단 테스트
- ✅ PANIC 자동 차단 테스트
- ✅ 에러 카운트 리셋 테스트

#### test_drift_detection.py
- ✅ Baseline 생성 테스트
- ✅ 24시간 메트릭 기록 테스트
- ✅ Drift 감지 테스트 (Sharpe 하락, 수익률 하락)
- ✅ 자동 롤백 조건 확인 테스트

#### test_model_evaluation.py
- ✅ 평가 지표 계산 테스트 (E, Sharpe, Q05/Q01, MAE, SPD)
- ✅ 모델 평가 테스트 (PASS/HOLD/REJECT)
- ✅ 하드 실패 조건 확인 테스트

#### test_data_pipeline.py
- ✅ 라벨 계산 테스트 (60m, 240m)
- ✅ Feature 계산 테스트
- ✅ 기술적 지표 계산 테스트 (RSI, MACD, EMA, 볼린저 밴드)

## 테스트 통계

- **총 테스트 파일**: 7개
- **총 테스트 함수**: 약 50개 이상
- **커버리지 대상 모듈**:
  - `indicators.py` (Regime Engine)
  - `regime.py` (Regime 가중치)
  - `safety_guard.py` (Runtime Guard)
  - `drift_detection.py` (Drift 감지)
  - `model_evaluation.py` (모델 평가)
  - `data_pipeline.py` (데이터 파이프라인)

## 주요 테스트 시나리오

### 1. Regime 분류 테스트
- PANIC 감지: 높은 변동성 + 낮은 상승 비율
- CHOP 감지: 높은 휩소 + 낮은 ADX
- TREND 감지: 높은 ADX + 낮은 휩소 + 높은 상승 비율
- RANGE 기본값

### 2. 안전성 테스트
- Slippage 이상 3회 연속 감지 시 자동 블록
- API 에러 5회 연속 시 자동 블록
- DB 에러 3회 연속 시 자동 블록
- PANIC 레짐 자동 차단

### 3. Drift 감지 테스트
- Sharpe ratio 30% 이상 하락 시 Drift 경고
- 수익률 50% 이상 하락 시 Drift 경고
- Drift 경고 3회 연속 시 자동 롤백
- 24시간 수익률 -2% 미만 시 자동 롤백

### 4. 모델 평가 테스트
- PASS 조건: 평균 수익률 > 1%, Sharpe > 0.5, Q05 > -3%
- REJECT 조건: 평균 수익률 < -5%, Sharpe < -1.0, Q01 < -10%
- 하드 실패: 평균 수익률 < -10%, Sharpe < -2.0, Q01 < -20%

## CI/CD 통합

GitHub Actions 등 CI/CD 파이프라인에 통합하려면:

```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.11'
      - run: |
          cd services/dashboard-api
          pip install -r requirements.txt
          pytest tests/ -v --cov=app
```

## 문제 해결

### ImportError 발생 시
- `PYTHONPATH`에 프로젝트 루트 추가
- `conftest.py`의 경로 확인

### DB 연결 오류 시
- 테스트용 SQLite 사용 (인메모리)
- `conftest.py`의 DB 설정 확인

### 의존성 오류 시
- `requirements.txt`에 모든 의존성 포함 확인
- 가상환경 사용 권장
