"""
Position Manager
지침: 트레일링, 스케일아웃, 자동 SL/TP, regime 변화시 자동 축소/청산
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import httpx


class PositionManager:
    """포지션 관리자"""
    
    def __init__(
        self,
        trader_name: str,
        dashboard_api_base: str = "http://dashboard-api:8000",
    ):
        self.trader_name = trader_name
        self.dashboard_api_base = dashboard_api_base
    
    def update_positions(
        self,
        positions: List[Dict],
        current_prices: Dict[str, float],
        regime: str,
    ) -> List[Dict]:
        """
        포지션 업데이트 및 관리
        
        Args:
            positions: 현재 포지션 리스트
            current_prices: {symbol: current_price}
            regime: 현재 레짐
        
        Returns:
            업데이트된 포지션 리스트
        """
        updated_positions = []
        
        for pos in positions:
            symbol = pos['symbol']
            current_price = current_prices.get(symbol)
            
            if not current_price:
                updated_positions.append(pos)
                continue
            
            entry_price = pos['avg_entry_price']
            size = pos['size']
            stop_price = pos.get('stop_price')
            
            # 미실현 손익 계산
            unreal_pnl = (current_price - entry_price) * size
            unreal_pnl_pct = (current_price / entry_price - 1) * 100 if entry_price > 0 else 0
            
            pos['current_price'] = current_price
            pos['unreal_pnl'] = unreal_pnl
            pos['unreal_pnl_pct'] = unreal_pnl_pct
            
            # 트레일링 스톱 업데이트
            if unreal_pnl_pct > 2.0:  # 2% 이상 수익 시 트레일링 활성화
                new_stop = entry_price * 1.01  # 진입가 +1%로 트레일링
                if stop_price is None or new_stop > stop_price:
                    pos['stop_price'] = new_stop
            
            # 스케일아웃 체크
            take_prices = pos.get('take_prices', [])
            if take_prices and unreal_pnl_pct > 0:
                # 첫 번째 익절가 도달 시 1/3 청산
                if current_price >= take_prices[0] and pos.get('scale_out_1', False) == False:
                    pos['scale_out_1'] = True
                    pos['size'] = size * 2/3  # 1/3 청산
                # 두 번째 익절가 도달 시 추가 1/3 청산
                elif current_price >= take_prices[1] and pos.get('scale_out_2', False) == False:
                    pos['scale_out_2'] = True
                    pos['size'] = size * 1/3  # 추가 1/3 청산
            
            # 레짐 변화 시 청산
            if regime == "CHOP":
                # CHOP 레짐: 손실 포지션만 청산
                if unreal_pnl_pct < -1.0:
                    pos['status'] = 'CLOSED'
                    continue
            
            # 손절 체크
            if stop_price and current_price <= stop_price:
                pos['status'] = 'CLOSED'
                continue
            
            updated_positions.append(pos)
        
        return updated_positions
    
    def should_close_position(
        self,
        position: Dict,
        current_price: float,
        regime: str,
        exit_threshold: float = 40.0,
    ) -> Tuple[bool, str]:
        """
        포지션 청산 여부 확인
        
        Returns:
            (should_close, reason)
        """
        entry_price = position['avg_entry_price']
        score = position.get('entry_score', 0)
        
        # Exit threshold 체크
        if score < exit_threshold:
            return True, f"점수 하락 ({score:.1f} < {exit_threshold})"
        
        # 손절 체크
        stop_price = position.get('stop_price')
        if stop_price and current_price <= stop_price:
            return True, f"손절 도달 ({current_price:.0f} <= {stop_price:.0f})"
        
        return False, ""
