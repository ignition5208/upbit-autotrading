"""
Trader 서비스 메인
지침 기반 전체 워크플로우 실행
"""
import os
import random
import time
from datetime import datetime
import httpx

NAME = os.getenv("TRADER_NAME", "trader")
BASE = os.getenv("DASHBOARD_API_BASE", "http://dashboard-api:8000")
INTERVAL = int(os.getenv("TRADING_INTERVAL_SEC", "300"))  # 기본 5분
TRADING_ENABLED = os.getenv("TRADING_ENABLED", "true").lower() == "true"
STARTUP_JITTER_SEC = int(os.getenv("TRADER_STARTUP_JITTER_SEC", "30"))

print(f"[trader] Starting {NAME}")
print(f"[trader] Dashboard API: {BASE}, Interval: {INTERVAL}s, Trading: {TRADING_ENABLED}")


def post_event(level: str, kind: str, message: str):
    try:
        httpx.post(
            f"{BASE}/api/events",
            json={
                "trader_name": NAME,
                "level": level,
                "kind": kind,
                "message": message,
            },
            timeout=5.0,
        )
    except Exception:
        pass


def load_trader_config():
    """Trader 설정 로드"""
    try:
        resp = httpx.get(f"{BASE}/api/traders/{NAME}", timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            seed_krw = data.get('seed_krw')
            if seed_krw is None:
                seed_krw = 1000000.0
            return {
                'strategy': data.get('strategy', 'standard'),
                'risk_mode': data.get('risk_mode', 'STANDARD'),
                'seed_krw': float(seed_krw),
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
    post_event("INFO", "lifecycle", f"trader process started interval={INTERVAL}s enabled={TRADING_ENABLED}")
    if STARTUP_JITTER_SEC > 0:
        jitter = random.randint(0, STARTUP_JITTER_SEC)
        print(f"[trader] Startup jitter sleep: {jitter}s")
        time.sleep(jitter)
    
    while True:
        try:
            # Trader 설정 로드
            config = load_trader_config()
            
            if not config:
                print("[trader] Failed to load config, retrying...")
                post_event("WARN", "config", "failed to load trader config, retrying")
                time.sleep(10)
                continue
            
            # STOP 상태면 거래 중지
            if config['status'] == 'STOP':
                if trading_engine:
                    print("[trader] Trader stopped, clearing engine")
                    post_event("INFO", "lifecycle", "status=STOP, trading engine cleared")
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
                post_event(
                    "INFO",
                    "config",
                    (
                        f"engine initialized strategy={config['strategy']} "
                        f"risk_mode={config['risk_mode']} run_mode={config['run_mode']}"
                    ),
                )
            
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
                    "message": (
                        f"{datetime.utcnow().isoformat()} "
                        f"status={config['status']} run_mode={config['run_mode']}"
                    ),
                },
                timeout=5.0,
            )
            
        except KeyboardInterrupt:
            print("[trader] Shutting down...")
            post_event("INFO", "lifecycle", "trader process shutdown by keyboard interrupt")
            break
        except Exception as e:
            print(f"[trader] Error in main loop: {e}")
            import traceback
            traceback.print_exc()
            post_event("ERROR", "runtime", f"main loop error: {e}")
        
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
