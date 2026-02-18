import os
import time
import json
from sqlalchemy import create_engine, text

from presets.loader import load_preset, deep_merge
from indicators.ta import build_features
from logging.db_events import log_event, save_scores
from scoring import compute as compute_score
from strategies.registry import eval_buy
from upbit_public import market_all, ticker, orderbook, candles_minutes

TRADER_ID = os.getenv("TRADER_ID", "trader-unknown")
DB_HOST = os.getenv("DB_HOST", "mariadb")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_NAME = os.getenv("DB_NAME", "upbit")
DB_USER = os.getenv("DB_USER", "upbit")
DB_PASS = os.getenv("DB_PASS", "upbitpass")

DB_URL = f"mysql+pymysql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
engine = create_engine(DB_URL, pool_pre_ping=True, pool_recycle=1800)


def heartbeat():
    with engine.begin() as conn:
        conn.execute(text("UPDATE traders SET heartbeat_at=NOW() WHERE trader_id=:tid"), {"tid": TRADER_ID})


def load_current_config_json():
    with engine.begin() as conn:
        r = conn.execute(
            text("SELECT config_json, version FROM config_current WHERE trader_id=:tid"), {"tid": TRADER_ID}
        ).fetchone()
        return (r[0], int(r[1])) if r else (None, None)


def load_trader_flags():
    with engine.begin() as conn:
        r = conn.execute(
            text(
                "SELECT mode, strategy_mode, is_paused, trade_enabled FROM traders WHERE trader_id=:tid"
            ),
            {"tid": TRADER_ID},
        ).fetchone()
        if not r:
            return {"mode": "PAPER", "strategy_mode": "STANDARD", "is_paused": 1, "trade_enabled": 0}
        return {
            "mode": r[0],
            "strategy_mode": r[1],
            "is_paused": int(r[2]),
            "trade_enabled": int(r[3]),
        }


def _parse_cfg(cfg_json: str | None, strategy_mode: str) -> dict:
    base = load_preset(strategy_mode)
    if not cfg_json:
        return base
    try:
        user_cfg = json.loads(cfg_json)
        # dashboard가 full-config를 저장하든, override만 저장하든 둘 다 수용
        if "preset" in user_cfg and isinstance(user_cfg.get("preset"), str):
            base = load_preset(user_cfg["preset"])
        if "overrides" in user_cfg and isinstance(user_cfg.get("overrides"), dict):
            return deep_merge(base, user_cfg["overrides"])
        return deep_merge(base, user_cfg)
    except Exception:
        return base


def _unit_from_timeframe(tf: str) -> int:
    # "1m" "3m" "5m" only
    if not tf:
        return 3
    if tf.endswith("m"):
        return int(tf[:-1])
    return 3


def scan_and_score(cfg: dict) -> list[dict]:
    tf = cfg["scanner"]["timeframe"]
    unit = _unit_from_timeframe(tf)
    top_n = int(cfg["scanner"]["top_n"])
    min_vol = float(cfg["scanner"]["min_krw_volume_24h"])
    max_spread_bp = float(cfg["scanner"]["max_spread_bp"])
    model = cfg.get("scoring", {}).get("model", "SCORE_A")

    log_event(engine, TRADER_ID, "INFO", "SCAN_START", f"scan start tf={tf} top_n={top_n}", {"timeframe": tf, "top_n": top_n})

    markets = [m["market"] for m in market_all() if m.get("market", "").startswith("KRW-")]
    if not markets:
        log_event(engine, TRADER_ID, "WARN", "SCAN_NO_MARKETS", "no KRW markets", {})
        return []

    # batch size to reduce URL length
    candidates: list[dict] = []
    checked = 0
    rejected = {"low_volume": 0, "spread": 0, "candle": 0}

    for i in range(0, len(markets), 100):
        batch = markets[i : i + 100]
        tks = {x["market"]: x for x in ticker(batch)}
        obs = {x["market"]: x for x in orderbook(batch)}

        for mk in batch:
            checked += 1
            tk = tks.get(mk)
            ob = obs.get(mk)
            if not tk or not ob:
                continue

            vol24 = float(tk.get("acc_trade_price_24h") or 0.0)
            if vol24 < min_vol:
                rejected["low_volume"] += 1
                continue

            units = (ob.get("orderbook_units") or [])
            if not units:
                rejected["spread"] += 1
                continue
            best_ask = float(units[0].get("ask_price") or 0.0)
            best_bid = float(units[0].get("bid_price") or 0.0)
            if best_ask <= 0 or best_bid <= 0:
                rejected["spread"] += 1
                continue
            spread_bp = (best_ask - best_bid) / best_bid * 10_000
            if spread_bp > max_spread_bp:
                rejected["spread"] += 1
                continue

            # candles
            try:
                cds = candles_minutes(mk, unit, count=60)
            except Exception:
                rejected["candle"] += 1
                continue
            if not cds or len(cds) < 30:
                rejected["candle"] += 1
                continue

            # Upbit returns newest first
            cds = list(reversed(cds))
            highs = [float(c["high_price"]) for c in cds]
            lows = [float(c["low_price"]) for c in cds]
            closes = [float(c["trade_price"]) for c in cds]

            feats = build_features(highs, lows, closes)

            prev_high = max(highs[-20:-1]) if len(highs) >= 21 else max(highs[:-1])
            prev_close = closes[-2]
            last = closes[-1]
            breakout_pct = (last - prev_high) / prev_high * 100 if prev_high > 0 else 0.0

            st = {
                "symbol": mk,
                "last": last,
                "prev_high": prev_high,
                "prev_close": prev_close,
                "acc_trade_price_24h": vol24,
                "spread_bp": spread_bp,
                "ema20": feats.ema20,
                "ema50": feats.ema50,
                "rsi14": feats.rsi14,
                "atr14": feats.atr14,
                "breakout_pct": breakout_pct,
            }
            st["score"] = float(compute_score(model, st))
            candidates.append(st)

    if not candidates:
        log_event(
            engine,
            TRADER_ID,
            "WARN",
            "SCAN_NO_CANDIDATE",
            "no candidate after filters",
            {"checked": checked, "rejected": rejected, "min_vol": min_vol, "max_spread_bp": max_spread_bp},
        )
        return []

    candidates.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    top = candidates[:top_n]

    save_scores(engine, TRADER_ID, [{"symbol": x["symbol"], "score": x["score"]} for x in top])

    log_event(
        engine,
        TRADER_ID,
        "INFO",
        "SCORES_SAVED",
        f"saved {len(top)} scores",
        {
            "model": model,
            "checked": checked,
            "rejected": rejected,
            "top": [
                {
                    "symbol": x["symbol"],
                    "score": x["score"],
                    "spread_bp": round(x["spread_bp"], 1),
                    "acc_trade_price_24h": x["acc_trade_price_24h"],
                }
                for x in top
            ],
        },
    )
    return top


def evaluate_buy(cfg: dict, top: list[dict]):
    buy_plugins = cfg.get("plugins", {}).get("buy", [])
    if not buy_plugins:
        log_event(engine, TRADER_ID, "WARN", "BUY_NO_PLUGIN", "no buy plugins configured", {})
        return

    # 후보 상위 5개에 대해만 전략 평가 로그 남김
    for st in top[:5]:
        st = dict(st)
        for plug in buy_plugins:
            res = eval_buy(plug, st, cfg)
            log_event(
                engine,
                TRADER_ID,
                "INFO",
                "BUY_EVAL",
                f"{plug}:{res.signal}",
                {"plugin": plug, "signal": res.signal, "reason": res.reason, "evidence": res.evidence},
            )
            if res.signal == "BUY":
                # 실제 주문은 v1.7.0에서 '로그만' 남기고 종료
                log_event(
                    engine,
                    TRADER_ID,
                    "INFO",
                    "BUY_INTENT",
                    "buy intent generated (order execution disabled in this build)",
                    {"plugin": plug, "order_intent": res.order_intent.__dict__ if res.order_intent else None, "evidence": res.evidence},
                )
                return

    log_event(engine, TRADER_ID, "INFO", "BUY_NO_SIGNAL", "no buy signal from plugins", {"checked": min(5, len(top))})


def main():
    print(f"[{TRADER_ID}] started (v1.7.0)")
    last_cfg_ver = None
    while True:
        try:
            heartbeat()
            flags = load_trader_flags()
            cfg_json, ver = load_current_config_json()

            if ver != last_cfg_ver:
                log_event(engine, TRADER_ID, "INFO", "CONFIG_SEEN", "current config loaded", {"version": ver})
                last_cfg_ver = ver

            if not cfg_json:
                time.sleep(2)
                continue

            if flags.get("is_paused") == 1:
                time.sleep(2)
                continue

            cfg = _parse_cfg(cfg_json, flags.get("strategy_mode") or "STANDARD")

            top = scan_and_score(cfg)
            if top:
                evaluate_buy(cfg, top)

            time.sleep(int(cfg["scanner"]["scan_interval_sec"]))
        except Exception as e:
            try:
                log_event(engine, TRADER_ID, "ERROR", "TRADER_LOOP_ERROR", str(e), {})
            except Exception:
                pass
            time.sleep(5)


if __name__ == "__main__":
    main()
