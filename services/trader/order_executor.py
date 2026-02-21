"""
Order Executor
지침: 지정가 우선, 분할진입, IOC/POC 옵션, 주문 재시도 로직
"""
import time
import pyupbit
from typing import Dict, Optional, Tuple
from datetime import datetime
import httpx


class OrderExecutor:
    """주문 실행기"""
    
    def __init__(
        self,
        access_key: str,
        secret_key: str,
        is_paper: bool = True,
        dashboard_api_base: str = "http://dashboard-api:8000",
    ):
        self.access_key = access_key
        self.secret_key = secret_key
        self.is_paper = is_paper
        self.dashboard_api_base = dashboard_api_base
        self.upbit = None
        
        if not is_paper and access_key and secret_key:
            # 실제 거래용 (나중에 구현)
            pass
    
    def execute_order(
        self,
        trader_name: str,
        symbol: str,
        side: str,  # BUY, SELL
        price: float,
        size: float,
        split_count: int = 3,  # 분할 진입 횟수
        max_retries: int = 3,
    ) -> Dict:
        """
        주문 실행
        
        Returns:
            {
                'success': bool,
                'order_id': str,
                'filled_qty': float,
                'avg_price': float,
                'error': str,
            }
        """
        if self.is_paper:
            # Paper 모드: 가상 실행
            return self._execute_paper_order(trader_name, symbol, side, price, size)
        
        # LIVE 모드: 실제 주문 (나중에 구현)
        return {
            'success': False,
            'order_id': None,
            'filled_qty': 0.0,
            'avg_price': None,
            'error': 'LIVE 모드 미구현',
        }
    
    def _execute_paper_order(
        self,
        trader_name: str,
        symbol: str,
        side: str,
        price: float,
        size: float,
    ) -> Dict:
        """Paper 모드 가상 주문 실행"""
        try:
            # 현재가 조회 (실제 체결 시뮬레이션)
            ticker = pyupbit.get_ticker(symbol)
            if not ticker:
                return {
                    'success': False,
                    'error': '티커 조회 실패',
                }
            
            current_price = ticker.get('trade_price', price)
            
            # 슬리피지 시뮬레이션 (0.1% 이내 랜덤)
            import random
            slippage = random.uniform(-0.001, 0.001)
            fill_price = current_price * (1 + slippage)
            
            # 주문 ID 생성
            order_id = f"PAPER_{trader_name}_{symbol}_{int(time.time())}"
            
            # Dashboard API에 주문 기록
            try:
                httpx.post(
                    f"{self.dashboard_api_base}/api/trades/order",
                    json={
                        'trader_name': trader_name,
                        'order_id': order_id,
                        'symbol': symbol,
                        'side': side,
                        'price': price,
                        'size': size,
                        'status': 'FILLED',
                        'filled_qty': size,
                        'avg_price': fill_price,
                    },
                    timeout=5.0,
                )
            except Exception as e:
                print(f"[executor] Failed to log order: {e}")
            
            return {
                'success': True,
                'order_id': order_id,
                'filled_qty': size,
                'avg_price': fill_price,
                'error': None,
            }
        except Exception as e:
            return {
                'success': False,
                'order_id': None,
                'filled_qty': 0.0,
                'avg_price': None,
                'error': str(e),
            }
    
    def cancel_order(self, order_id: str) -> bool:
        """주문 취소"""
        if self.is_paper:
            return True  # Paper 모드에서는 항상 성공
        
        # LIVE 모드 구현 필요
        return False
    
    def get_order_status(self, order_id: str) -> Dict:
        """주문 상태 조회"""
        if self.is_paper:
            return {
                'status': 'FILLED',
                'filled_qty': 0.0,
                'avg_price': None,
            }
        
        # LIVE 모드 구현 필요
        return {'status': 'UNKNOWN'}
