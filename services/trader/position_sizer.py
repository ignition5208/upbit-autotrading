"""
Position Sizer & Risk Engine
지침 4번: 포지션·리스크 규칙
"""
from typing import Dict, Optional
import math


class PositionSizer:
    """포지션 사이징 및 리스크 계산"""
    
    def __init__(
        self,
        equity: float,
        risk_per_trade: float = 0.01,  # 1%
        max_portfolio_risk: float = 0.05,  # 5%
        slippage_limit: float = 0.005,  # 0.5%
    ):
        self.equity = equity
        self.risk_per_trade = risk_per_trade
        self.max_portfolio_risk = max_portfolio_risk
        self.slippage_limit = slippage_limit
    
    def calculate_position_size(
        self,
        entry_price: float,
        stop_price: float,
        current_open_positions_risk: float = 0.0,
    ) -> Dict:
        """
        포지션 사이즈 계산
        
        Args:
            entry_price: 진입 목표 가격
            stop_price: 손절 가격
            current_open_positions_risk: 현재 오픈 포지션의 총 리스크 (%)
        
        Returns:
            {
                'position_size': float,
                'dollar_risk': float,
                'expected_order_krw': float,
                'stop_price': float,
                'take_prices': List[float],
                'estimated_fee': float,
                'max_position_size': float,
            }
        """
        if entry_price <= 0 or stop_price <= 0:
            return {
                'position_size': 0.0,
                'dollar_risk': 0.0,
                'expected_order_krw': 0.0,
                'stop_price': stop_price,
                'take_prices': [],
                'estimated_fee': 0.0,
                'max_position_size': 0.0,
            }
        
        # 손절 거리
        stop_distance = abs(entry_price - stop_price) / entry_price
        
        if stop_distance == 0:
            return {
                'position_size': 0.0,
                'dollar_risk': 0.0,
                'expected_order_krw': 0.0,
                'stop_price': stop_price,
                'take_prices': [],
                'estimated_fee': 0.0,
                'max_position_size': 0.0,
            }
        
        # 트레이드당 달러 리스크
        dollar_risk = self.equity * self.risk_per_trade
        
        # 포지션 사이즈 계산: position_size = dollar_risk / (entry_price - stop_price)
        price_risk_per_unit = abs(entry_price - stop_price)
        position_size = dollar_risk / price_risk_per_unit
        
        # 포트폴리오 리스크 제한 확인
        remaining_portfolio_risk = self.max_portfolio_risk - current_open_positions_risk
        if remaining_portfolio_risk <= 0:
            position_size = 0.0
        else:
            max_dollar_risk = self.equity * remaining_portfolio_risk
            max_position_size = max_dollar_risk / price_risk_per_unit
            position_size = min(position_size, max_position_size)
        
        # 예상 주문 금액
        expected_order_krw = position_size * entry_price
        
        # 수수료 계산 (Upbit: 0.05%)
        estimated_fee = expected_order_krw * 0.0005 * 2  # 매수+매도
        
        # 익절 가격 (스케일아웃 계획)
        take_prices = []
        if entry_price > stop_price:  # 롱 포지션
            take1 = entry_price + (entry_price - stop_price) * 1.5
            take2 = entry_price + (entry_price - stop_price) * 2.5
            take3 = entry_price + (entry_price - stop_price) * 4.0
            take_prices = [take1, take2, take3]
        else:  # 숏 포지션 (현물에서는 거의 없음)
            take1 = entry_price - (stop_price - entry_price) * 1.5
            take2 = entry_price - (stop_price - entry_price) * 2.5
            take3 = entry_price - (stop_price - entry_price) * 4.0
            take_prices = [take1, take2, take3]
        
        return {
            'position_size': float(position_size),
            'dollar_risk': float(dollar_risk),
            'expected_order_krw': float(expected_order_krw),
            'stop_price': float(stop_price),
            'take_prices': [float(tp) for tp in take_prices],
            'estimated_fee': float(estimated_fee),
            'max_position_size': float(max_position_size),
        }
    
    def check_slippage(
        self,
        expected_price: float,
        actual_price: float,
    ) -> tuple[bool, float]:
        """
        슬리피지 확인
        
        Returns:
            (is_acceptable, slippage_pct)
        """
        if expected_price == 0:
            return False, 999.0
        
        slippage_pct = abs((actual_price - expected_price) / expected_price)
        is_acceptable = slippage_pct <= self.slippage_limit
        
        return is_acceptable, slippage_pct
