"""
데이터 파이프라인 테스트
"""
import pytest
import numpy as np
from datetime import datetime, timedelta
from app.services.data_pipeline import (
    calculate_labels,
    calculate_features,
    calculate_rsi,
    calculate_macd,
    calculate_ema,
    calculate_bollinger_upper,
    calculate_bollinger_lower,
)
import pandas as pd


class TestLabels:
    """라벨 계산 테스트"""
    
    def test_calculate_labels_60m(self):
        """60분 라벨 계산"""
        entry_price = 1000000.0
        current_price = 1010000.0  # 1% 상승
        high_price = 1020000.0
        low_price = 1005000.0
        entry_time = datetime.utcnow() - timedelta(minutes=70)
        current_time = datetime.utcnow()
        
        labels = calculate_labels(
            entry_price,
            current_price,
            high_price,
            low_price,
            entry_time,
            current_time,
        )
        
        assert labels['label_ret_60m'] is not None
        assert labels['label_ret_60m'] == pytest.approx(0.01, rel=0.01)
    
    def test_calculate_labels_240m(self):
        """240분 라벨 계산"""
        entry_price = 1000000.0
        current_price = 1020000.0  # 2% 상승
        high_price = 1030000.0
        low_price = 1005000.0
        entry_time = datetime.utcnow() - timedelta(minutes=250)
        current_time = datetime.utcnow()
        
        labels = calculate_labels(
            entry_price,
            current_price,
            high_price,
            low_price,
            entry_time,
            current_time,
        )
        
        assert labels['label_ret_240m'] is not None
        assert labels['label_ret_240m'] == pytest.approx(0.02, rel=0.01)
        assert labels['label_mfe_240m'] is not None
        assert labels['label_mae_240m'] is not None
    
    def test_calculate_labels_insufficient_time(self):
        """시간 부족 시 None"""
        entry_price = 1000000.0
        current_price = 1010000.0
        high_price = 1020000.0
        low_price = 1005000.0
        entry_time = datetime.utcnow() - timedelta(minutes=30)
        current_time = datetime.utcnow()
        
        labels = calculate_labels(
            entry_price,
            current_price,
            high_price,
            low_price,
            entry_time,
            current_time,
        )
        
        assert labels['label_ret_60m'] is None
        assert labels['label_ret_240m'] is None


class TestFeatures:
    """Feature 계산 테스트"""
    
    @pytest.fixture
    def sample_ohlcv(self):
        """샘플 OHLCV 데이터"""
        dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
        np.random.seed(42)
        
        base_price = 100000000
        prices = []
        for i in range(50):
            change = np.random.normal(0, 0.01)
            base_price *= (1 + change)
            prices.append(base_price)
        
        df = pd.DataFrame({
            'open': prices,
            'high': [p * 1.01 for p in prices],
            'low': [p * 0.99 for p in prices],
            'close': prices,
            'volume': np.random.uniform(100, 1000, 50),
        })
        df.index = dates
        return df
    
    def test_calculate_features(self, sample_ohlcv):
        """Feature 계산"""
        features = calculate_features(sample_ohlcv)
        
        assert 'price' in features
        assert 'volume_ma_20' in features
        assert 'rsi_14' in features
        assert 'macd' in features
        assert 'bb_upper' in features
        assert 'bb_lower' in features
    
    def test_calculate_features_insufficient_data(self):
        """데이터 부족"""
        df = pd.DataFrame({
            'close': [100],
            'volume': [1000],
        })
        features = calculate_features(df)
        assert features == {}


class TestTechnicalIndicators:
    """기술적 지표 테스트"""
    
    def test_calculate_rsi(self):
        """RSI 계산"""
        prices = np.array([100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110,
                           111, 112, 113, 114, 115])
        rsi = calculate_rsi(prices, period=14)
        assert 0 <= rsi <= 100
    
    def test_calculate_rsi_insufficient_data(self):
        """데이터 부족"""
        prices = np.array([100, 101])
        rsi = calculate_rsi(prices, period=14)
        assert rsi == 50.0
    
    def test_calculate_macd(self):
        """MACD 계산"""
        prices = np.array([100 + i for i in range(30)])
        macd = calculate_macd(prices)
        assert isinstance(macd, float)
    
    def test_calculate_ema(self):
        """EMA 계산"""
        prices = np.array([100 + i for i in range(20)])
        ema = calculate_ema(prices, period=10)
        assert isinstance(ema, float)
        assert ema > 0
    
    def test_calculate_bollinger_bands(self):
        """볼린저 밴드 계산"""
        prices = np.array([100 + i * 0.5 + np.random.normal(0, 1) for i in range(30)])
        upper = calculate_bollinger_upper(prices, period=20)
        lower = calculate_bollinger_lower(prices, period=20)
        
        assert upper > lower
        assert isinstance(upper, float)
        assert isinstance(lower, float)
