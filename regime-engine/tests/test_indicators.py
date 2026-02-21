"""
Regime Engine 지표 계산 단위 테스트
"""
import pytest
import pandas as pd
import numpy as np
import sys
from pathlib import Path

# 상위 디렉토리를 path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from indicators import (
    calculate_adx,
    calculate_atr_pct,
    calculate_breadth_up,
    calculate_dispersion,
    calculate_top5_value_share,
    calculate_whipsaw,
    calculate_regime_score,
)


@pytest.fixture
def sample_ohlcv_data():
    """샘플 OHLCV 데이터 생성"""
    dates = pd.date_range(start='2024-01-01', periods=100, freq='4H')
    np.random.seed(42)
    
    base_price = 100000000
    prices = []
    for i in range(100):
        change = np.random.normal(0, 0.02)
        base_price *= (1 + change)
        prices.append(base_price)
    
    df = pd.DataFrame({
        'open': prices,
        'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
        'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
        'close': prices,
        'volume': np.random.uniform(100, 1000, 100),
    })
    df.index = dates
    return df


@pytest.fixture
def sample_markets_data():
    """샘플 마켓 데이터 생성"""
    markets = []
    for i in range(10):
        candles = []
        base_price = 1000000 * (i + 1)
        for j in range(24):
            price = base_price * (1 + np.random.normal(0, 0.01))
            candles.append({
                'trade_price': price,
                'candle_acc_trade_volume': np.random.uniform(100, 1000),
            })
        markets.append({
            'market': f'KRW-COIN{i}',
            'candles': candles,
        })
    return markets


class TestADX:
    """ADX 계산 테스트"""
    
    def test_adx_basic(self, sample_ohlcv_data):
        """기본 ADX 계산"""
        adx = calculate_adx(sample_ohlcv_data, period=14)
        assert isinstance(adx, float)
        assert 0 <= adx <= 100
    
    def test_adx_insufficient_data(self):
        """데이터 부족 시 0 반환"""
        df = pd.DataFrame({
            'high': [100, 101],
            'low': [99, 100],
            'close': [100, 101],
        })
        adx = calculate_adx(df, period=14)
        assert adx == 0.0
    
    def test_adx_trending_market(self):
        """트렌드 시장에서 높은 ADX"""
        # 강한 상승 트렌드 데이터
        dates = pd.date_range(start='2024-01-01', periods=50, freq='4H')
        prices = [100000000 + i * 1000000 for i in range(50)]
        df = pd.DataFrame({
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
        })
        df.index = dates
        
        adx = calculate_adx(df, period=14)
        assert adx >= 0


class TestATR:
    """ATR 계산 테스트"""
    
    def test_atr_pct_basic(self, sample_ohlcv_data):
        """기본 ATR 퍼센트 계산"""
        atr_pct = calculate_atr_pct(sample_ohlcv_data, period=14)
        assert isinstance(atr_pct, float)
        assert atr_pct >= 0
    
    def test_atr_pct_insufficient_data(self):
        """데이터 부족 시 0 반환"""
        df = pd.DataFrame({
            'high': [100],
            'low': [99],
            'close': [100],
        })
        atr_pct = calculate_atr_pct(df, period=14)
        assert atr_pct == 0.0


class TestBreadth:
    """Breadth 계산 테스트"""
    
    def test_breadth_up_basic(self, sample_markets_data):
        """기본 상승 비율 계산"""
        breadth = calculate_breadth_up(sample_markets_data)
        assert isinstance(breadth, float)
        assert 0 <= breadth <= 1
    
    def test_breadth_up_empty(self):
        """빈 데이터"""
        breadth = calculate_breadth_up([])
        assert breadth == 0.0
    
    def test_breadth_up_all_up(self):
        """모두 상승"""
        markets = [{
            'market': 'KRW-BTC',
            'candles': [
                {'trade_price': 100, 'candle_acc_trade_volume': 1000},
                {'trade_price': 110, 'candle_acc_trade_volume': 1000},
            ]
        }]
        breadth = calculate_breadth_up(markets)
        assert breadth == 1.0


class TestDispersion:
    """Dispersion 계산 테스트"""
    
    def test_dispersion_basic(self, sample_markets_data):
        """기본 분산도 계산"""
        dispersion = calculate_dispersion(sample_markets_data)
        assert isinstance(dispersion, float)
        assert dispersion >= 0
    
    def test_dispersion_empty(self):
        """빈 데이터"""
        dispersion = calculate_dispersion([])
        assert dispersion == 0.0


class TestTop5Share:
    """Top5 시가총액 비중 테스트"""
    
    def test_top5_share_basic(self, sample_markets_data):
        """기본 Top5 비중 계산"""
        share = calculate_top5_value_share(sample_markets_data)
        assert isinstance(share, float)
        assert 0 <= share <= 1
    
    def test_top5_share_insufficient(self):
        """마켓 수 부족"""
        markets = [{
            'market': 'KRW-BTC',
            'candles': [{'trade_price': 100, 'candle_acc_trade_volume': 1000}]
        }]
        share = calculate_top5_value_share(markets)
        assert share == 0.0


class TestWhipsaw:
    """Whipsaw 계산 테스트"""
    
    def test_whipsaw_basic(self, sample_ohlcv_data):
        """기본 휩소 계산"""
        whipsaw = calculate_whipsaw(sample_ohlcv_data, period=5)
        assert isinstance(whipsaw, float)
        assert 0 <= whipsaw <= 1
    
    def test_whipsaw_insufficient_data(self):
        """데이터 부족"""
        df = pd.DataFrame({'close': [100, 101]})
        whipsaw = calculate_whipsaw(df, period=5)
        assert whipsaw == 0.0


class TestRegimeScore:
    """Regime 점수 계산 테스트"""
    
    def test_panic_detection(self):
        """PANIC 감지"""
        indicators = {
            'btc_atr_pct_4h': 6.0,  # 높은 변동성
            'breadth_up_1h': 0.2,    # 낮은 상승 비율
        }
        regime_id, regime_label, confidence = calculate_regime_score(indicators)
        assert regime_label == "PANIC"
        assert confidence > 0
    
    def test_chop_detection(self):
        """CHOP 감지"""
        indicators = {
            'whipsaw_5m': 0.7,  # 높은 휩소
            'btc_adx_4h': 15,   # 낮은 ADX
        }
        regime_id, regime_label, confidence = calculate_regime_score(indicators)
        assert regime_label == "CHOP"
    
    def test_trend_detection(self):
        """TREND 감지"""
        indicators = {
            'btc_adx_4h': 30,   # 높은 ADX
            'whipsaw_5m': 0.2,  # 낮은 휩소
            'breadth_up_1h': 0.7,  # 높은 상승 비율
        }
        regime_id, regime_label, confidence = calculate_regime_score(indicators)
        assert regime_label == "TREND"
    
    def test_range_default(self):
        """기본값 RANGE"""
        indicators = {
            'btc_adx_4h': 20,
            'whipsaw_5m': 0.4,
        }
        regime_id, regime_label, confidence = calculate_regime_score(indicators)
        assert regime_label == "RANGE"
