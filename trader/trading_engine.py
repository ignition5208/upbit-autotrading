"""
Trading Engine - 전체 워크플로우 통합
지침: 스크리닝 → 레짐 판단 → 스코어링 → 진입 전 검사 → 주문 실행 → 포지션 관리
"""
import os
import time
import httpx
import pyupbit
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional

from screener import screen_markets
from scoring import (
    score_trend_pullback,
    score_volatility_contraction_breakout,
    score_liquidity_sweep_reversal,
    score_leader_follower,
    score_regime_modifier,
)
from score_aggregator import ScoreAggregator
from position_sizer import PositionSizer
from pre_trade_check import PreTradeChecker
from order_executor import OrderExecutor
from position_manager import PositionManager


class TradingEngine:
    """거래 엔진"""
    
    def __init__(
        self,
        trader_name: str,
        strategy: str,
        risk_mode: str,
        seed_krw: float,
        credential_name: Optional[str],
        dashboard_api_base: str = "http://dashboard-api:8000",
        is_paper: bool = True,
    ):
        self.trader_name = trader_name
        self.strategy = strategy
        self.risk_mode = risk_mode
        self.seed_krw = seed_krw
        self.credential_name = credential_name
        self.dashboard_api_base = dashboard_api_base
        self.is_paper = is_paper
        
        # 모듈 초기화
        self.score_aggregator = ScoreAggregator()
        self.position_sizer = PositionSizer(equity=seed_krw)
        self.pre_trade_checker = PreTradeChecker()
        self.position_manager = PositionManager(trader_name, dashboard_api_base)
        
        # 자격증명 로드
        self.access_key = None
        self.secret_key = None
        if credential_name:
            self._load_credentials()
        
        self.order_executor = OrderExecutor(
            access_key=self.access_key,
            secret_key=self.secret_key,
            is_paper=is_paper,
            dashboard_api_base=dashboard_api_base,
        )
        
        # 상태
        self.current_regime = None
        self.open_positions = []
        self.equity = seed_krw
    
    def _load_credentials(self):
        """자격증명 로드"""
        try:
            resp = httpx.get(
                f"{self.dashboard_api_base}/api/credentials",
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('items', [])
                cred = next((c for c in items if c.get('name') == self.credential_name), None)
                if cred:
                    # 복호화 필요 (나중에 구현)
                    # 현재는 암호화된 값 그대로 사용 (실제로는 복호화 필요)
                    # credentials 서비스가 반환하는 형식에 맞춤
                    self.access_key = cred.get('access_key_enc') or cred.get('access_key', '')
                    self.secret_key = cred.get('secret_key_enc') or cred.get('secret_key', '')
        except Exception as e:
            print(f"[engine] Failed to load credentials: {e}")
    
    def _get_current_regime(self) -> Dict:
        """현재 Regime 조회"""
        try:
            resp = httpx.get(
                f"{self.dashboard_api_base}/api/regimes/snapshots?limit=1",
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                items = data.get('items', [])
                if items:
                    return {
                        'regime_label': items[0].get('regime_label', 'RANGE'),
                        'confidence': items[0].get('confidence', 0.5),
                    }
        except Exception as e:
            print(f"[engine] Failed to get regime: {e}")
        
        return {'regime_label': 'RANGE', 'confidence': 0.5}
    
    def _get_btc_data(self) -> Optional[pd.DataFrame]:
        """BTC 데이터 가져오기 (LF 스코어링용)"""
        try:
            df = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=200)
            return df
        except Exception as e:
            print(f"[engine] Failed to get BTC data: {e}")
            return None
    
    def run_cycle(self):
        """거래 사이클 실행"""
        print(f"[engine] Starting trading cycle for {self.trader_name}")
        
        # 1. Regime 조회
        regime_info = self._get_current_regime()
        self.current_regime = regime_info['regime_label']
        print(f"[engine] Current regime: {self.current_regime}")
        
        # 2. 스크리닝
        candidates = screen_markets(top_n=30)
        print(f"[engine] Screened {len(candidates)} candidates")
        
        # 3. BTC 데이터 로드 (LF용)
        btc_df = self._get_btc_data()
        
        # 4. 스코어링
        scored_candidates = []
        for candidate in candidates:
            symbol = candidate['symbol']
            
            try:
                # OHLCV 데이터 가져오기
                df = pyupbit.get_ohlcv(symbol, interval="minute60", count=200)
                if df is None or df.empty:
                    continue
                
                # 각 스코어 모듈 실행
                tp_score, tp_reasons, tp_metrics = score_trend_pullback(symbol, df)
                vcb_score, vcb_reasons, vcb_metrics = score_volatility_contraction_breakout(symbol, df)
                lsr_score, lsr_reasons, lsr_metrics = score_liquidity_sweep_reversal(symbol, df)
                lf_score, lf_reasons, lf_metrics = score_leader_follower(symbol, df, btc_df)
                regime_score, regime_reasons, regime_metrics = score_regime_modifier(
                    regime_info['regime_label'],
                    regime_info['confidence'],
                )
                
                scores = {
                    'tp': tp_score,
                    'vcb': vcb_score,
                    'lsr': lsr_score,
                    'lf': lf_score,
                    'regime': regime_score,
                }
                
                reason_codes = {
                    'tp': tp_reasons,
                    'vcb': vcb_reasons,
                    'lsr': lsr_reasons,
                    'lf': lf_reasons,
                    'regime': regime_reasons,
                }
                
                # 점수 집계
                aggregated = self.score_aggregator.aggregate(symbol, scores, reason_codes)
                
                scored_candidates.append({
                    **candidate,
                    'total_score': aggregated['total_score'],
                    'smoothed_score': aggregated['smoothed_score'],
                    'scores': scores,
                    'reason_codes': aggregated['all_reason_codes'],
                    'raw_metrics': {
                        **tp_metrics,
                        **vcb_metrics,
                        **lsr_metrics,
                        **lf_metrics,
                        **regime_metrics,
                    },
                })
            except Exception as e:
                print(f"[engine] Error scoring {symbol}: {e}")
                continue
        
        # 점수 순으로 정렬
        scored_candidates.sort(key=lambda x: x['smoothed_score'], reverse=True)
        
        # 5. 진입 검토 (상위 후보만)
        for candidate in scored_candidates[:10]:  # 상위 10개만 검토
            symbol = candidate['symbol']
            total_score = candidate['smoothed_score']
            
            # 이미 포지션이 있으면 스킵
            if any(p['symbol'] == symbol for p in self.open_positions):
                continue
            
            # Pre-trade 체크
            current_positions_risk = sum(
                abs(p.get('unreal_pnl_pct', 0)) / 100 for p in self.open_positions
            )
            
            passed, failed_reasons = self.pre_trade_checker.check_all(
                symbol=symbol,
                total_score=total_score,
                regime=self.current_regime,
                expected_order_krw=candidate.get('avg_depth5', 0) * 0.3,
                avg_depth5=candidate.get('avg_depth5', 0),
                remaining_budget=self.equity * 0.9,
                risk_per_trade=self.position_sizer.risk_per_trade,
                open_positions=self.open_positions,
                api_health=True,
            )
            
            if not passed:
                print(f"[engine] {symbol} failed pre-trade check: {failed_reasons}")
                continue
            
            # 포지션 사이징
            entry_price = candidate['current_price']
            stop_price = entry_price * 0.98  # 2% 손절 (간단화)
            
            sizing = self.position_sizer.calculate_position_size(
                entry_price=entry_price,
                stop_price=stop_price,
                current_open_positions_risk=current_positions_risk,
            )
            
            if sizing['position_size'] <= 0:
                print(f"[engine] {symbol} position size is 0")
                continue
            
            # 주문 실행
            result = self.order_executor.execute_order(
                trader_name=self.trader_name,
                symbol=symbol,
                side='BUY',
                price=entry_price,
                size=sizing['position_size'],
            )
            
            if result['success']:
                # 포지션 추가
                position = {
                    'symbol': symbol,
                    'avg_entry_price': result['avg_price'],
                    'size': result['filled_qty'],
                    'stop_price': sizing['stop_price'],
                    'take_prices': sizing['take_prices'],
                    'entry_score': total_score,
                    'status': 'OPEN',
                }
                self.open_positions.append(position)
                
                # 신호 기록
                self._log_signal(symbol, total_score, scores, 'ENTRY', candidate['reason_codes'])
                
                print(f"[engine] Entry: {symbol} @ {result['avg_price']:.0f}, size: {result['filled_qty']:.6f}")
            else:
                print(f"[engine] Order failed for {symbol}: {result.get('error')}")
        
        # 6. 포지션 관리
        self._manage_positions()
    
    def _manage_positions(self):
        """포지션 관리"""
        current_prices = {}
        
        # 현재가 조회
        for pos in self.open_positions:
            symbol = pos['symbol']
            try:
                ticker = pyupbit.get_ticker(symbol)
                if ticker:
                    current_prices[symbol] = ticker.get('trade_price', 0)
            except Exception as e:
                print(f"[engine] Failed to get price for {symbol}: {e}")
        
        # 포지션 업데이트
        updated_positions = self.position_manager.update_positions(
            positions=self.open_positions,
            current_prices=current_prices,
            regime=self.current_regime,
        )
        
        # 청산 체크
        closed_positions = []
        for pos in updated_positions:
            if pos['status'] == 'CLOSED':
                closed_positions.append(pos)
                should_close, reason = self.position_manager.should_close_position(
                    position=pos,
                    current_price=current_prices.get(pos['symbol'], 0),
                    regime=self.current_regime,
                )
                
                if should_close:
                    # 청산 주문
                    self.order_executor.execute_order(
                        trader_name=self.trader_name,
                        symbol=pos['symbol'],
                        side='SELL',
                        price=current_prices.get(pos['symbol'], pos['avg_entry_price']),
                        size=pos['size'],
                    )
                    
                    # 신호 기록
                    self._log_signal(pos['symbol'], 0, {}, 'EXIT', [reason])
        
        # 오픈 포지션만 유지
        self.open_positions = [p for p in updated_positions if p['status'] == 'OPEN']
    
    def _log_signal(
        self,
        symbol: str,
        total_score: float,
        scores: Dict[str, float],
        action: str,
        reason_codes: List[str],
    ):
        """신호 기록"""
        try:
            httpx.post(
                f"{self.dashboard_api_base}/api/trades/signal",
                json={
                    'trader_name': self.trader_name,
                    'symbol': symbol,
                    'total_score': total_score,
                    'scores_json': scores,
                    'regime': self.current_regime,
                    'action': action,
                    'reason_codes': reason_codes,
                },
                timeout=5.0,
            )
        except Exception as e:
            print(f"[engine] Failed to log signal: {e}")
