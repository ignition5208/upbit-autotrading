"""
Trading Engine - 전체 워크플로우 통합
지침: 스크리닝 → 레짐 판단 → 스코어링 → 진입 전 검사 → 주문 실행 → 포지션 관리
Final Score = base_score × regime_weight × bandit_weight × risk_multiplier
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

# 리스크 모드별 최종 점수 배율
RISK_MULTIPLIER: Dict[str, float] = {
    'SAFE':     0.3,
    'STANDARD': 0.5,
    'PROFIT':   0.7,
    'CRAZY':    1.0,
}

# 레짐별 기본 가중치 (API 응답 없을 때 fallback)
DEFAULT_REGIME_WEIGHT: Dict[str, float] = {
    'TREND':              1.2,
    'BREAKOUT_ROTATION':  1.1,
    'RANGE':              1.0,
    'CHOP':               0.3,
    'PANIC':              0.0,
}


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

        # 자격증명 로드 (복호화 API 사용)
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

    # ─────────────────────────────────────────────────
    # 내부 헬퍼
    # ─────────────────────────────────────────────────

    def _load_credentials(self):
        """Credential 복호화 API를 통해 키 로드"""
        try:
            resp = httpx.get(
                f"{self.dashboard_api_base}/api/credentials/{self.credential_name}/decrypt",
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                self.access_key = data.get("access_key", "")
                self.secret_key = data.get("secret_key", "")
                print(f"[engine] Credentials loaded for {self.credential_name}")
            else:
                print(f"[engine] Failed to decrypt credentials: HTTP {resp.status_code}")
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
                items = resp.json().get('items', [])
                if items:
                    return {
                        'regime_label': items[0].get('regime_label', 'RANGE'),
                        'confidence': items[0].get('confidence', 0.5),
                    }
        except Exception as e:
            print(f"[engine] Failed to get regime: {e}")
        return {'regime_label': 'RANGE', 'confidence': 0.5}

    def _get_regime_weight(self, regime_label: str) -> float:
        """레짐별 가중치 조회"""
        try:
            resp = httpx.get(
                f"{self.dashboard_api_base}/api/regimes/regime-weight/{regime_label}",
                timeout=5.0,
            )
            if resp.status_code == 200:
                data = resp.json()
                return float(data.get('applied_weight', data.get('weight', 1.0)))
        except Exception:
            pass
        return DEFAULT_REGIME_WEIGHT.get(regime_label, 1.0)

    def _get_bandit_weight(self, regime_label: str, strategy_id: str) -> float:
        """Bandit 가중치 조회"""
        try:
            resp = httpx.get(
                f"{self.dashboard_api_base}/api/regimes/weight/{regime_label}/{strategy_id}",
                timeout=5.0,
            )
            if resp.status_code == 200:
                return float(resp.json().get('weight', 1.0))
        except Exception:
            pass
        return 1.0

    def _get_btc_data(self) -> Optional[pd.DataFrame]:
        """BTC 데이터 가져오기 (LF 스코어링용)"""
        try:
            df = pyupbit.get_ohlcv("KRW-BTC", interval="minute60", count=200)
            return df
        except Exception as e:
            print(f"[engine] Failed to get BTC data: {e}")
            return None

    # ─────────────────────────────────────────────────
    # 메인 사이클
    # ─────────────────────────────────────────────────

    def run_cycle(self):
        """거래 사이클 실행"""
        print(f"[engine] Starting trading cycle for {self.trader_name}")

        # 1. Regime 조회
        regime_info = self._get_current_regime()
        self.current_regime = regime_info['regime_label']
        print(f"[engine] Current regime: {self.current_regime}")

        # 2. 레짐/밴딧 가중치 + 리스크 배율
        regime_weight = self._get_regime_weight(self.current_regime)
        bandit_weight = self._get_bandit_weight(self.current_regime, self.strategy)
        risk_mult = RISK_MULTIPLIER.get(self.risk_mode, 0.5)
        print(
            f"[engine] regime_weight={regime_weight:.2f}, "
            f"bandit_weight={bandit_weight:.2f}, risk_mult={risk_mult:.2f}"
        )

        # PANIC → 신규 진입 금지, 포지션 50% 축소
        if self.current_regime == 'PANIC':
            print("[engine] PANIC regime — skipping new entries, reducing positions")
            self._manage_positions(reduce_only=True)
            return

        # 3. 스크리닝
        candidates = screen_markets(top_n=30)
        print(f"[engine] Screened {len(candidates)} candidates")

        # 4. BTC 데이터 로드
        btc_df = self._get_btc_data()

        # 5. 스코어링 + Final Score 계산
        scored_candidates = []
        for candidate in candidates:
            symbol = candidate['symbol']
            try:
                df = pyupbit.get_ohlcv(symbol, interval="minute60", count=200)
                if df is None or df.empty:
                    continue

                tp_score,  tp_reasons,  tp_metrics  = score_trend_pullback(symbol, df)
                vcb_score, vcb_reasons, vcb_metrics = score_volatility_contraction_breakout(symbol, df)
                lsr_score, lsr_reasons, lsr_metrics = score_liquidity_sweep_reversal(symbol, df)
                lf_score,  lf_reasons,  lf_metrics  = score_leader_follower(symbol, df, btc_df)
                regime_score, regime_reasons, regime_metrics = score_regime_modifier(
                    regime_info['regime_label'],
                    regime_info['confidence'],
                )

                scores = {
                    'tp':     tp_score,
                    'vcb':    vcb_score,
                    'lsr':    lsr_score,
                    'lf':     lf_score,
                    'regime': regime_score,
                }
                reason_codes = {
                    'tp':     tp_reasons,
                    'vcb':    vcb_reasons,
                    'lsr':    lsr_reasons,
                    'lf':     lf_reasons,
                    'regime': regime_reasons,
                }

                aggregated = self.score_aggregator.aggregate(symbol, scores, reason_codes)

                # ── Final Score = base × regime_weight × bandit_weight × risk_multiplier ──
                final_score = (
                    aggregated['smoothed_score']
                    * regime_weight
                    * bandit_weight
                    * risk_mult
                )

                scored_candidates.append({
                    **candidate,
                    'total_score':   final_score,
                    'base_score':    aggregated['smoothed_score'],
                    'regime_weight': regime_weight,
                    'bandit_weight': bandit_weight,
                    'risk_mult':     risk_mult,
                    'scores':        scores,
                    'reason_codes':  aggregated['all_reason_codes'],
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

        scored_candidates.sort(key=lambda x: x['total_score'], reverse=True)

        # 6. 진입 검토 (상위 10개)
        for candidate in scored_candidates[:10]:
            symbol = candidate['symbol']
            total_score = candidate['total_score']

            if any(p['symbol'] == symbol for p in self.open_positions):
                continue

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
                print(f"[engine] {symbol} failed pre-trade: {failed_reasons}")
                continue

            entry_price = candidate['current_price']
            stop_price  = entry_price * 0.98

            sizing = self.position_sizer.calculate_position_size(
                entry_price=entry_price,
                stop_price=stop_price,
                current_open_positions_risk=current_positions_risk,
            )

            if sizing['position_size'] <= 0:
                continue

            result = self.order_executor.execute_order(
                trader_name=self.trader_name,
                symbol=symbol,
                side='BUY',
                price=entry_price,
                size=sizing['position_size'],
            )

            if result['success']:
                position = {
                    'symbol':          symbol,
                    'avg_entry_price': result['avg_price'],
                    'size':            result['filled_qty'],
                    'stop_price':      sizing['stop_price'],
                    'take_prices':     sizing['take_prices'],
                    'entry_score':     total_score,
                    'status':          'OPEN',
                }
                self.open_positions.append(position)
                self._log_signal(
                    symbol,
                    total_score,
                    candidate['scores'],
                    'ENTRY',
                    candidate['reason_codes'],
                )
                print(f"[engine] Entry: {symbol} @ {result['avg_price']:.0f}, score={total_score:.2f}")
            else:
                print(f"[engine] Order failed for {symbol}: {result.get('error')}")

        # 7. 포지션 관리
        self._manage_positions()

    # ─────────────────────────────────────────────────
    # 포지션 관리
    # ─────────────────────────────────────────────────

    def _manage_positions(self, reduce_only: bool = False):
        """포지션 업데이트 및 청산 실행"""
        current_prices: Dict[str, float] = {}

        for pos in self.open_positions:
            symbol = pos['symbol']
            try:
                ticker = pyupbit.get_ticker(symbol)
                if ticker:
                    current_prices[symbol] = ticker.get('trade_price', 0)
            except Exception as e:
                print(f"[engine] Failed to get price for {symbol}: {e}")

        if reduce_only:
            reduced_positions = []
            for pos in self.open_positions:
                symbol = pos['symbol']
                sell_size = pos['size'] * 0.5
                if sell_size <= 0:
                    continue
                reduce_result = self.order_executor.execute_order(
                    trader_name=self.trader_name,
                    symbol=symbol,
                    side='SELL',
                    price=current_prices.get(symbol, pos['avg_entry_price']),
                    size=sell_size,
                )
                if reduce_result['success']:
                    remaining = pos['size'] - reduce_result.get('filled_qty', 0.0)
                    if remaining > 0:
                        pos['size'] = remaining
                        reduced_positions.append(pos)
                    self._log_signal(symbol, 0, {}, 'EXIT', ['PANIC 50% REDUCE'])
                else:
                    reduced_positions.append(pos)
                    print(f"[engine] PANIC reduce failed for {symbol}: {reduce_result.get('error')}")
            self.open_positions = reduced_positions
            return

        updated_positions = self.position_manager.update_positions(
            positions=self.open_positions,
            current_prices=current_prices,
            regime=self.current_regime,
        )

        still_open = []
        for pos in updated_positions:
            should_close, reason = self.position_manager.should_close_position(
                position=pos,
                current_price=current_prices.get(pos['symbol'], 0),
                regime=self.current_regime,
            )

            if should_close or pos.get('status') == 'CLOSED':
                close_result = self.order_executor.execute_order(
                    trader_name=self.trader_name,
                    symbol=pos['symbol'],
                    side='SELL',
                    price=current_prices.get(pos['symbol'], pos['avg_entry_price']),
                    size=pos['size'],
                )
                self._log_signal(pos['symbol'], 0, {}, 'EXIT', [reason])
                print(f"[engine] Exit: {pos['symbol']} reason={reason} ok={close_result['success']}")
            else:
                still_open.append(pos)

        self.open_positions = still_open

    # ─────────────────────────────────────────────────
    # 신호 기록
    # ─────────────────────────────────────────────────

    def _log_signal(
        self,
        symbol: str,
        total_score: float,
        scores: Dict[str, float],
        action: str,
        reason_codes: List[str],
    ):
        """신호 기록 (DB 저장)"""
        try:
            httpx.post(
                f"{self.dashboard_api_base}/api/trades/signal",
                json={
                    'trader_name':  self.trader_name,
                    'symbol':       symbol,
                    'total_score':  total_score,
                    'scores_json':  scores,
                    'regime':       self.current_regime or 'UNKNOWN',
                    'action':       action,
                    'reason_codes': reason_codes,
                },
                timeout=5.0,
            )
        except Exception as e:
            print(f"[engine] Failed to log signal: {e}")
