"""
Trader 서비스 메인
지침 기반 전체 워크플로우 실행
"""
import os
import time
from datetime import datetime
import httpx

NAME = os.getenv("TRADER_NAME", "trader")
BASE = os.getenv("DASHBOARD_API_BASE", "http://dashboard-api:8000")
INTERVAL = int(os.getenv("TRADING_INTERVAL_SEC", "300"))  # 기본 5분
TRADING_ENABLED = os.getenv("TRADING_ENABLED", "true").lower() == "true"

print(f"[trader] Starting {NAME}")
print(f"[trader] Dashboard API: {BASE}, Interval: {INTERVAL}s, Trading: {TRADING_ENABLED}")


def load_trader_config():
    """Trader 설정 로드"""
    try:
        resp = httpx.get(f"{BASE}/api/traders/{NAME}", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            return {
                'strategy': data.get('strategy', 'standard'),
                'risk_mode': data.get('risk_mode', 'STANDARD'),
                'seed_krw': data.get('seed_krw', 1000000.0),
                'credential_name': data.get('credential_name'),
                'run_mode': data.get('run_mode', 'PAPER'),
                'status': data.get('status', 'STOP'),
            }
    except Exception as e:
        print(f"[trader] Failed to load config: {e}")
    
    return None


def main():
    """메인 루프"""
    trading_engine = None
    
    while True:
        try:
            # Trader 설정 로드
            config = load_trader_config()
            
            if not config:
                print("[trader] Failed to load config, retrying...")
                time.sleep(10)
                continue
            
            # STOP 상태면 거래 중지
            if config['status'] == 'STOP':
                if trading_engine:
                    print("[trader] Trader stopped, clearing engine")
                    trading_engine = None
                time.sleep(10)
                continue
            
            # Trading Engine 초기화/재초기화
            if trading_engine is None:
                from trading_engine import TradingEngine
                trading_engine = TradingEngine(
                    trader_name=NAME,
                    strategy=config['strategy'],
                    risk_mode=config['risk_mode'],
                    seed_krw=config['seed_krw'],
                    credential_name=config['credential_name'],
                    dashboard_api_base=BASE,
                    is_paper=(config['run_mode'] == 'PAPER'),
                )
                print(f"[trader] Trading engine initialized")
            
            # 거래 사이클 실행
            if TRADING_ENABLED:
                trading_engine.run_cycle()
            
            # Heartbeat
            httpx.post(
                f"{BASE}/api/events",
                json={
                    "trader_name": NAME,
                    "level": "INFO",
                    "kind": "heartbeat",
                    "message": datetime.utcnow().isoformat(),
                },
                timeout=5.0,
            )
            
        except KeyboardInterrupt:
            print("[trader] Shutting down...")
            break
        except Exception as e:
            print(f"[trader] Error in main loop: {e}")
            import traceback
            traceback.print_exc()
        
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
