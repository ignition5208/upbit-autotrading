"""
Order Executor
지침: 시장가 우선, 분할진입, 주문 재시도 로직, 블랙리스트 관리
"""
import time
import random
import pyupbit
from typing import Dict, Optional
from datetime import datetime
import httpx
from market_data import get_ticker


# 블랙리스트 차단 시간 (초)
BLACKLIST_DURATION_SEC = 600  # 10분


class OrderExecutor:
    """주문 실행기 — PAPER/LIVE 통합"""

    def __init__(
        self,
        access_key: str,
        secret_key: str,
        is_paper: bool = True,
        dashboard_api_base: str = "http://dashboard-api:8000",
    ):
        self.access_key = access_key or ""
        self.secret_key = secret_key or ""
        self.is_paper = is_paper
        self.dashboard_api_base = dashboard_api_base
        self.upbit: Optional[pyupbit.Upbit] = None

        # 블랙리스트: {market: 해제_timestamp}
        self._blacklist: Dict[str, float] = {}

        if not is_paper and self.access_key and self.secret_key:
            try:
                self.upbit = pyupbit.Upbit(self.access_key, self.secret_key)
                print("[executor] Upbit LIVE client initialized")
            except Exception as e:
                print(f"[executor] Failed to init Upbit client: {e}")

    # ─────────────────────────────────────────────────
    # 공개 인터페이스
    # ─────────────────────────────────────────────────

    def execute_order(
        self,
        trader_name: str,
        symbol: str,
        side: str,          # 'BUY' | 'SELL'
        price: float,
        size: float,        # BUY: KRW 금액, SELL: 코인 수량
        split_count: int = 1,
        max_retries: int = 3,
    ) -> Dict:
        """
        주문 실행 (블랙리스트 체크 → Paper/LIVE 분기)

        Returns:
            {'success': bool, 'order_id': str, 'filled_qty': float,
             'avg_price': float, 'error': str | None}
        """
        # 블랙리스트 체크
        if self._is_blacklisted(symbol):
            return self._fail(f"{symbol} 블랙리스트 차단 (10분)")

        if self.is_paper:
            return self._execute_paper_order(trader_name, symbol, side, price, size)

        return self._execute_live_order(
            trader_name, symbol, side, price, size,
            split_count=split_count,
            max_retries=max_retries,
        )

    def cancel_order(self, order_id: str) -> bool:
        if self.is_paper:
            return True
        if self.upbit:
            try:
                self.upbit.cancel_order(order_id)
                return True
            except Exception as e:
                print(f"[executor] Cancel failed: {e}")
        return False

    # ─────────────────────────────────────────────────
    # PAPER 모드
    # ─────────────────────────────────────────────────

    def _execute_paper_order(
        self,
        trader_name: str,
        symbol: str,
        side: str,
        price: float,
        size: float,
    ) -> Dict:
        """Paper 모드 가상 주문 실행 (슬리피지 시뮬레이션 포함)"""
        try:
            ticker = get_ticker(symbol)
            if not ticker:
                return self._fail("티커 조회 실패")

            current_price = ticker.get('trade_price', price)
            slippage = random.uniform(-0.001, 0.001)
            fill_price = current_price * (1 + slippage)
            filled_qty = (size / fill_price) if side == 'BUY' and fill_price > 0 else size

            order_id = f"PAPER_{trader_name}_{symbol}_{int(time.time())}"

            self._record_order(
                trader_name=trader_name,
                order_id=order_id,
                symbol=symbol,
                side=side,
                price=price,
                size=size,
                fill_price=fill_price,
                filled_qty=filled_qty,
            )

            return {
                'success':    True,
                'order_id':   order_id,
                'filled_qty': filled_qty,
                'avg_price':  fill_price,
                'error':      None,
            }
        except Exception as e:
            return self._fail(str(e))

    # ─────────────────────────────────────────────────
    # LIVE 모드
    # ─────────────────────────────────────────────────

    def _execute_live_order(
        self,
        trader_name: str,
        symbol: str,
        side: str,
        price: float,
        size: float,
        split_count: int = 1,
        max_retries: int = 3,
    ) -> Dict:
        """LIVE 실주문 (분할 진입 + 재시도 + 블랙리스트)"""
        if not self.upbit:
            return self._fail("Upbit 클라이언트 미초기화 (access_key/secret_key 확인)")

        parts = max(1, split_count)
        partial_size = size / parts
        filled_qty = 0.0
        last_price = 0.0
        last_error = None

        for part_idx in range(parts):
            success = False
            for attempt in range(max_retries):
                try:
                    if side == 'BUY':
                        # 시장가 매수: KRW 금액
                        resp = self.upbit.buy_market_order(symbol, partial_size)
                    else:
                        # 시장가 매도: 코인 수량
                        resp = self.upbit.sell_market_order(symbol, partial_size)

                    if resp and 'error' not in str(resp):
                        # 체결 확인
                        exec_price = float(resp.get('price') or resp.get('avg_price') or price)
                        exec_qty   = float(resp.get('volume') or resp.get('executed_volume') or partial_size)
                        filled_qty += exec_qty
                        last_price = exec_price
                        order_id   = resp.get('uuid', f"LIVE_{int(time.time())}_{part_idx}")
                        self._record_order(
                            trader_name=trader_name,
                            order_id=order_id,
                            symbol=symbol,
                            side=side,
                            price=price,
                            size=partial_size,
                            fill_price=exec_price,
                            filled_qty=exec_qty,
                        )
                        print(f"[executor] LIVE {side} {symbol} part{part_idx+1}/{parts} OK @ {exec_price}")
                        success = True
                        break
                    else:
                        last_error = str(resp)
                        print(f"[executor] LIVE order error (attempt {attempt+1}): {last_error}")
                        time.sleep(1)

                except Exception as e:
                    last_error = str(e)
                    print(f"[executor] LIVE order exception (attempt {attempt+1}): {e}")
                    time.sleep(1)

            if not success:
                # 분할 도중 실패 → 블랙리스트 등록
                self._add_blacklist(symbol)
                print(f"[executor] {symbol} blacklisted for {BLACKLIST_DURATION_SEC}s after {max_retries} failures")
                if filled_qty == 0:
                    return self._fail(f"주문 실패 ({max_retries}회): {last_error}")
                break  # 일부 체결됐으면 부분 성공 반환

            if parts > 1:
                time.sleep(1)  # 분할 주문 간 간격

        return {
            'success':    filled_qty > 0,
            'order_id':   f"LIVE_{symbol}_{int(time.time())}",
            'filled_qty': filled_qty,
            'avg_price':  last_price,
            'error':      last_error if filled_qty == 0 else None,
        }

    # ─────────────────────────────────────────────────
    # 블랙리스트 관리
    # ─────────────────────────────────────────────────

    def _is_blacklisted(self, symbol: str) -> bool:
        unblock_at = self._blacklist.get(symbol)
        if unblock_at is None:
            return False
        if time.time() >= unblock_at:
            del self._blacklist[symbol]
            return False
        return True

    def _add_blacklist(self, symbol: str) -> None:
        self._blacklist[symbol] = time.time() + BLACKLIST_DURATION_SEC

    # ─────────────────────────────────────────────────
    # 헬퍼
    # ─────────────────────────────────────────────────

    @staticmethod
    def _fail(msg: str) -> Dict:
        return {'success': False, 'order_id': None, 'filled_qty': 0.0, 'avg_price': None, 'error': msg}

    def _record_order(
        self,
        trader_name: str,
        order_id: str,
        symbol: str,
        side: str,
        price: float,
        size: float,
        fill_price: float,
        filled_qty: float,
    ) -> None:
        """체결 내역 Dashboard API에 기록"""
        try:
            httpx.post(
                f"{self.dashboard_api_base}/api/trades/order",
                json={
                    'trader_name': trader_name,
                    'order_id':    order_id,
                    'symbol':      symbol,
                    'side':        side,
                    'price':       price,
                    'size':        size,
                    'status':      'FILLED',
                    'filled_qty':  filled_qty,
                    'avg_price':   fill_price,
                },
                timeout=5.0,
            )
        except Exception as e:
            print(f"[executor] Failed to record order: {e}")
