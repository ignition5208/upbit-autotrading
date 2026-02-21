"""
Trading Engine - 전체 워크플로우 통합
지침: 스크리닝 → 레짐 판단 → 스코어링 → 진입 전 검사 → 주문 실행 → 포지션 관리
Final Score = base_score × regime_weight × bandit_weight × risk_multiplier
"""
import os
import time
import json
import httpx
import pyupbit
import pandas as pd
from datetime import datetime
from typing import Dict, List, Optional
from market_data import get_ticker

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

DEFAULT_STRATEGY_PARAMS: Dict[str, Dict[str, float]] = {
    "safety_first": {
        "entry_threshold": 55.0,
        "exit_threshold": 35.0,
        "risk_per_trade": 0.005,
        "max_portfolio_risk": 0.03,
        "slippage_limit": 0.003,
        "allow_add_buy": 1.0,
        "max_add_count": 1.0,
        "add_position_ratio": 0.15,
        "add_min_base_score": 72.0,
    },
    "standard": {
        "entry_threshold": 60.0,
        "exit_threshold": 40.0,
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "slippage_limit": 0.005,
        "allow_add_buy": 1.0,
        "max_add_count": 2.0,
        "add_position_ratio": 0.25,
        "add_min_base_score": 70.0,
    },
    "profit_first": {
        "entry_threshold": 58.0,
        "exit_threshold": 45.0,
        "risk_per_trade": 0.015,
        "max_portfolio_risk": 0.08,
        "slippage_limit": 0.007,
        "allow_add_buy": 1.0,
        "max_add_count": 3.0,
        "add_position_ratio": 0.35,
        "add_min_base_score": 68.0,
    },
    "crazy": {
        "entry_threshold": 52.0,
        "exit_threshold": 50.0,
        "risk_per_trade": 0.025,
        "max_portfolio_risk": 0.15,
        "slippage_limit": 0.01,
        "allow_add_buy": 1.0,
        "max_add_count": 4.0,
        "add_position_ratio": 0.5,
        "add_min_base_score": 65.0,
    },
    "ai_mode": {
        "entry_threshold": 60.0,
        "exit_threshold": 40.0,
        "risk_per_trade": 0.01,
        "max_portfolio_risk": 0.05,
        "slippage_limit": 0.005,
        "allow_add_buy": 1.0,
        "max_add_count": 2.0,
        "add_position_ratio": 0.3,
        "add_min_base_score": 70.0,
    },
}
OHLCV_CALL_INTERVAL_SEC = float(os.getenv("UPBIT_OHLCV_CALL_INTERVAL_SEC", "0.14"))


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
        self.seed_krw = float(seed_krw) if seed_krw is not None else 1000000.0
        self.credential_name = credential_name
        self.dashboard_api_base = dashboard_api_base
        self.is_paper = is_paper

        # 모듈 초기화
        self.score_aggregator = ScoreAggregator()
        self.position_sizer = PositionSizer(equity=self.seed_krw)
        self.pre_trade_checker = PreTradeChecker()
        self.position_manager = PositionManager(trader_name, dashboard_api_base)

        # 자격증명 로드 (복호화 API 사용)
        self.access_key = None
        self.secret_key = None
        if credential_name and not is_paper:
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
        self.equity = self.seed_krw
        self.strategy_params = DEFAULT_STRATEGY_PARAMS.get(self.strategy, DEFAULT_STRATEGY_PARAMS["standard"]).copy()

    def _post_event(self, level: str, kind: str, message: str) -> None:
        """Dashboard events에 트레이더 액션 기록"""
        try:
            httpx.post(
                f"{self.dashboard_api_base}/api/events",
                json={
                    "trader_name": self.trader_name,
                    "level": level,
                    "kind": kind,
                    "message": message,
                },
                timeout=3.0,
            )
        except Exception:
            pass

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

    def _get_held_symbols(self) -> set[str]:
        """
        DB에 기록된 체결 기준 현재 보유 심볼 조회.
        컨테이너 재시작으로 open_positions 메모리가 비어도 중복 진입을 방지한다.
        """
        try:
            resp = httpx.get(
                f"{self.dashboard_api_base}/api/trades/holdings",
                params={"trader_name": self.trader_name},
                timeout=5.0,
            )
            if resp.status_code != 200:
                return set()
            items = resp.json().get("items", [])
            return {str(i.get("market")) for i in items if i.get("market")}
        except Exception:
            return set()

    def _load_strategy_params(self) -> Dict[str, float]:
        """
        dashboard-api의 active config에서 전략 파라미터 로드.
        실패하면 전략 기본값 사용.
        """
        params = DEFAULT_STRATEGY_PARAMS.get(self.strategy, DEFAULT_STRATEGY_PARAMS["standard"]).copy()
        try:
            resp = httpx.get(f"{self.dashboard_api_base}/api/configs", timeout=5.0)
            if resp.status_code != 200:
                return params
            items = resp.json().get("items", [])
            active = None
            for item in items:
                if item.get("strategy_id") == self.strategy and item.get("is_active") is True:
                    active = item
                    break
            if active and active.get("params"):
                cfg_params = json.loads(active["params"])
                if isinstance(cfg_params, dict):
                    params.update(cfg_params)
        except Exception:
            pass
        return params

    def _apply_strategy_params(self) -> None:
        """로드된 전략 파라미터를 체커/사이저에 반영"""
        self.strategy_params = self._load_strategy_params()
        self.pre_trade_checker.entry_threshold = float(self.strategy_params.get("entry_threshold", 60.0))
        self.position_sizer.risk_per_trade = float(self.strategy_params.get("risk_per_trade", 0.01))
        self.position_sizer.max_portfolio_risk = float(self.strategy_params.get("max_portfolio_risk", 0.05))
        self.position_sizer.slippage_limit = float(self.strategy_params.get("slippage_limit", 0.005))

    # ─────────────────────────────────────────────────
    # 메인 사이클
    # ─────────────────────────────────────────────────

    def run_cycle(self):
        """거래 사이클 실행"""
        print(f"[engine] Starting trading cycle for {self.trader_name}")
        self._post_event("INFO", "cycle", "trading cycle started")
        self._apply_strategy_params()

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
        self._post_event(
            "INFO",
            "regime",
            (
                f"regime={self.current_regime} confidence={regime_info['confidence']:.2f} "
                f"regime_w={regime_weight:.2f} bandit_w={bandit_weight:.2f} risk_w={risk_mult:.2f}"
            ),
        )
        self._post_event(
            "INFO",
            "config",
            (
                f"strategy={self.strategy} entry={self.pre_trade_checker.entry_threshold:.1f} "
                f"exit={float(self.strategy_params.get('exit_threshold', 40.0)):.1f} "
                f"risk_per_trade={self.position_sizer.risk_per_trade:.4f}"
            ),
        )

        # PANIC → 신규 진입 금지, 포지션 50% 축소
        if self.current_regime == 'PANIC':
            print("[engine] PANIC regime — skipping new entries, reducing positions")
            self._post_event("WARN", "risk", "PANIC detected: reducing positions by 50% and blocking new entries")
            self._manage_positions(reduce_only=True)
            return

        # 3. 스크리닝
        candidates = screen_markets(top_n=30)
        print(f"[engine] Screened {len(candidates)} candidates")
        self._post_event("INFO", "screen", f"screened candidates={len(candidates)}")

        # 4. BTC 데이터 로드
        btc_df = self._get_btc_data()
        held_symbols = self._get_held_symbols()

        # 5. 스코어링 + Final Score 계산
        scored_candidates = []
        for candidate in candidates:
            symbol = candidate['symbol']
            try:
                if OHLCV_CALL_INTERVAL_SEC > 0:
                    time.sleep(OHLCV_CALL_INTERVAL_SEC)
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
            base_score = candidate['base_score']
            existing_pos = next((p for p in self.open_positions if p['symbol'] == symbol), None)
            is_held = existing_pos is not None or symbol in held_symbols
            is_add_buy = False
            size_multiplier = 1.0

            if is_held:
                allow_add_buy = float(self.strategy_params.get("allow_add_buy", 0.0)) > 0
                max_add_count = int(float(self.strategy_params.get("max_add_count", 0.0)))
                add_min_base_score = float(self.strategy_params.get("add_min_base_score", 999.0))
                add_position_ratio = float(self.strategy_params.get("add_position_ratio", 0.0))

                # 컨테이너 재시작 등으로 메모리에 없는 보유 포지션은 중복 진입 방지 우선
                if existing_pos is None:
                    continue
                buy_count = int(existing_pos.get("buy_count", 1))

                if (not allow_add_buy) or (buy_count >= 1 + max_add_count):
                    continue
                if base_score < add_min_base_score:
                    continue
                if add_position_ratio <= 0:
                    continue

                is_add_buy = True
                size_multiplier = add_position_ratio

            current_positions_risk = sum(
                abs(p.get('unreal_pnl_pct', 0)) / 100 for p in self.open_positions
            )

            passed, failed_reasons = self.pre_trade_checker.check_all(
                symbol=symbol,
                total_score=base_score,
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

            order_size = sizing['position_size'] * size_multiplier
            if order_size <= 0:
                continue

            result = self.order_executor.execute_order(
                trader_name=self.trader_name,
                symbol=symbol,
                side='BUY',
                price=entry_price,
                size=order_size,
            )

            if result['success']:
                if existing_pos is not None:
                    prev_size = float(existing_pos.get('size', 0.0))
                    prev_avg = float(existing_pos.get('avg_entry_price', result['avg_price']))
                    add_size = float(result['filled_qty'])
                    new_size = prev_size + add_size
                    existing_pos['avg_entry_price'] = (
                        ((prev_avg * prev_size) + (result['avg_price'] * add_size)) / new_size
                        if new_size > 0 else result['avg_price']
                    )
                    existing_pos['size'] = new_size
                    existing_pos['entry_score'] = base_score
                    existing_pos['buy_count'] = int(existing_pos.get('buy_count', 1)) + 1
                else:
                    position = {
                        'symbol':          symbol,
                        'avg_entry_price': result['avg_price'],
                        'size':            result['filled_qty'],
                        'stop_price':      sizing['stop_price'],
                        'take_prices':     sizing['take_prices'],
                        'entry_score':     base_score,
                        'buy_count':       1,
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
                self._post_event(
                    "INFO",
                    "order",
                    (
                        f"{'ADD' if is_add_buy else 'ENTRY'} {symbol} "
                        f"base_score={base_score:.2f} final_score={total_score:.2f} "
                        f"price={result['avg_price']:.0f} size={result['filled_qty']:.6f}"
                    ),
                )
            else:
                print(f"[engine] Order failed for {symbol}: {result.get('error')}")
                self._post_event("ERROR", "order", f"ENTRY FAILED {symbol}: {result.get('error')}")

        # 7. 포지션 관리
        self._manage_positions()
        self._post_event("INFO", "cycle", f"trading cycle finished open_positions={len(self.open_positions)}")

    # ─────────────────────────────────────────────────
    # 포지션 관리
    # ─────────────────────────────────────────────────

    def _manage_positions(self, reduce_only: bool = False):
        """포지션 업데이트 및 청산 실행"""
        current_prices: Dict[str, float] = {}

        for pos in self.open_positions:
            symbol = pos['symbol']
            try:
                ticker = get_ticker(symbol)
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
                    self._post_event(
                        "WARN",
                        "order",
                        f"PANIC REDUCE {symbol} sold={reduce_result.get('filled_qty', 0.0):.6f}",
                    )
                else:
                    reduced_positions.append(pos)
                    print(f"[engine] PANIC reduce failed for {symbol}: {reduce_result.get('error')}")
                    self._post_event("ERROR", "order", f"PANIC REDUCE FAILED {symbol}: {reduce_result.get('error')}")
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
                exit_threshold=float(self.strategy_params.get("exit_threshold", 40.0)),
                strategy=self.strategy,
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
                if close_result['success']:
                    self._post_event("INFO", "order", f"EXIT {pos['symbol']} reason={reason}")
                else:
                    self._post_event("ERROR", "order", f"EXIT FAILED {pos['symbol']} reason={reason}")
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
