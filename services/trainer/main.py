"""
Trainer 서비스 - AI 자동 튜닝 시스템
OPT-0001 ~ OPT-0004 구현
"""
import os
import time
import httpx
from datetime import datetime

BASE = os.getenv("DASHBOARD_API_BASE", "http://dashboard-api:8000")
INTERVAL = int(os.getenv("TRAINER_INTERVAL_SEC", "3600"))  # 기본 1시간


def run_training_cycle():
    """훈련 사이클 실행"""
    try:
        # 1. 스캔 실행 (OPT-0001)
        print("[trainer] Running scan...")
        scan_response = httpx.post(
            f"{BASE}/api/trainer/scan",
            json={
                "strategy_id": "default",
                "markets": ["KRW-BTC", "KRW-ETH", "KRW-XRP"],
                "top_n": 5,
            },
            timeout=300.0,
        )
        
        if scan_response.status_code != 200:
            print(f"[trainer] Scan failed: {scan_response.status_code}")
            return
        
        scan_data = scan_response.json()
        scan_run_id = scan_data.get("scan_run_id")
        
        # 2. 라벨 업데이트 (OPT-0001)
        print("[trainer] Updating labels...")
        label_response = httpx.post(
            f"{BASE}/api/trainer/update-labels",
            json={"scan_run_id": scan_run_id},
            timeout=300.0,
        )
        
        if label_response.status_code != 200:
            print(f"[trainer] Label update failed: {label_response.status_code}")
            return
        
        # 3. 평가 및 게이트 (OPT-0002)
        print("[trainer] Evaluating models...")
        eval_response = httpx.post(
            f"{BASE}/api/trainer/evaluate",
            json={"strategy_id": "default"},
            timeout=300.0,
        )
        
        if eval_response.status_code != 200:
            print(f"[trainer] Evaluation failed: {eval_response.status_code}")
            return
        
        # 4. 자동 튜닝 (OPT-0003)
        print("[trainer] Running auto-tuning...")
        tune_response = httpx.post(
            f"{BASE}/api/trainer/tune",
            json={"strategy_id": "default"},
            timeout=600.0,  # 튜닝은 시간이 오래 걸릴 수 있음
        )
        
        if tune_response.status_code != 200:
            print(f"[trainer] Tuning failed: {tune_response.status_code}")
            return
        
        print("[trainer] Training cycle completed successfully")
        
    except Exception as e:
        print(f"[trainer] Error in training cycle: {e}")
        import traceback
        traceback.print_exc()


def main():
    print("[trainer] Starting Trainer service")
    print(f"[trainer] API Base: {BASE}, Interval: {INTERVAL}s")
    
    while True:
        run_training_cycle()
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
