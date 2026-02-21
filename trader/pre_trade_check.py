"""
Pre-trade 체크리스트
지침 5번: 사전(진입 전) 체크리스트
"""
from typing import Dict, List, Tuple
import httpx


class PreTradeChecker:
    """진입 전 체크리스트 검증"""
    
    def __init__(
        self,
        entry_threshold: float = 70.0,
        liquidity_min_ratio: float = 0.3,
        corr_high: float = 0.7,
    ):
        self.entry_threshold = entry_threshold
        self.liquidity_min_ratio = liquidity_min_ratio
        self.corr_high = corr_high
    
    def check_all(
        self,
        symbol: str,
        total_score: float,
        regime: str,
        expected_order_krw: float,
        avg_depth5: float,
        remaining_budget: float,
        risk_per_trade: float,
        open_positions: List[Dict],
        api_health: bool = True,
    ) -> Tuple[bool, List[str]]:
        """
        모든 체크리스트 검증
        
        Args:
            symbol: 심볼
            total_score: 총 점수
            regime: 레짐 라벨
            expected_order_krw: 예상 주문 금액
            avg_depth5: 평균 depth (상위 5개 호가)
            remaining_budget: 남은 예산
            risk_per_trade: 트레이드당 리스크
            open_positions: 현재 오픈 포지션 리스트 [{'symbol': str, 'size': float, ...}]
            api_health: API 상태
        
        Returns:
            (is_passed, failed_reasons)
        """
        failed_reasons = []
        
        # 1. total_score ≥ ENTRY_THRESHOLD
        if total_score < self.entry_threshold:
            failed_reasons.append(f"점수 부족 ({total_score:.1f} < {self.entry_threshold})")
        
        # 2. regime 허용 (HIGH_RISK/PANIC 시 롱 금지)
        if regime in ("PANIC", "CHOP"):
            failed_reasons.append(f"레짐 차단 ({regime})")
        
        # 3. 유동성 체크: expected_order_krw ≤ avg_depth * LIQUIDITY_MIN_RATIO
        if avg_depth5 > 0:
            liquidity_ratio = expected_order_krw / avg_depth5
            if liquidity_ratio > self.liquidity_min_ratio:
                failed_reasons.append(f"유동성 부족 (ratio: {liquidity_ratio:.2f} > {self.liquidity_min_ratio})")
        else:
            failed_reasons.append("유동성 데이터 없음")
        
        # 4. remaining_budget ≥ RISK_PER_TRADE
        if remaining_budget < risk_per_trade:
            failed_reasons.append(f"예산 부족 ({remaining_budget:.0f} < {risk_per_trade:.0f})")
        
        # 5. 상관관계 체크 (간단화: 동일 심볼 중복 체크)
        for pos in open_positions:
            if pos.get('symbol') == symbol:
                failed_reasons.append("동일 심볼 중복 포지션")
                break
        
        # 6. rate_limit/API health 정상
        if not api_health:
            failed_reasons.append("API 상태 불량")
        
        # 7. trading hours 체크 (Upbit는 24시간 거래 가능)
        # 생략
        
        # 8. risk manager 승인 (자동)
        # 항상 통과
        
        is_passed = len(failed_reasons) == 0
        return is_passed, failed_reasons
    
    def check_liquidity(
        self,
        expected_order_krw: float,
        avg_depth5: float,
    ) -> Tuple[bool, float]:
        """유동성 체크만 수행"""
        if avg_depth5 == 0:
            return False, 999.0
        
        liquidity_ratio = expected_order_krw / avg_depth5
        is_acceptable = liquidity_ratio <= self.liquidity_min_ratio
        
        return is_acceptable, liquidity_ratio
    
    def check_correlation(
        self,
        symbol: str,
        open_positions: List[Dict],
    ) -> Tuple[bool, float]:
        """
        상관관계 체크 (간단화)
        실제로는 과거 수익률 상관관계 계산 필요
        """
        # 동일 심볼 체크만 수행
        for pos in open_positions:
            if pos.get('symbol') == symbol:
                return False, 1.0  # 완전 상관
        
        return True, 0.0
