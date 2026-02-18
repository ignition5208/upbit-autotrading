```markdown
# 🚀 Upbit Auto-Trading Platform v1.7.0

Multi-Trader, Score-Strategy based Auto Trading System for Upbit  
Docker + MariaDB + Bootstrap Dashboard

---

## 📌 Overview

This platform allows you to run multiple independent trading bots (traders) against **Upbit**.

Each trader:

- Uses a single **Score-Strategy (Score = Strategy)**
- Runs in **LIVE or PAPER mode**
- Has configurable **Risk Modes (SAFE/STANDARD/PROFIT/CRAZY)**
- Runs in its own **Docker container**
- Stores all trading data in **MariaDB**

The dashboard allows you to:

- Create / Start / Stop traders
- Arm LIVE trading manually
- Compare performance
- Recreate containers to apply updated strategy code

---

# 🏗 Architecture

```

docker-compose
├── mariadb
├── dashboard-api
├── dashboard-web (Bootstrap)
└── trader (dynamic containers, 0 at startup)

```

### Key Design Principles

- 🔒 Only trader containers execute real orders
- 📊 Score = Strategy (no separated scoring layer)
- 🧠 Strategy code is bound to Docker image version
- 🛡 LIVE trading requires explicit ARM action
- 💾 All state persists in MariaDB (named volume)

---

# 🔄 Initial Startup Behavior

- `docker-compose up` starts:
  - mariadb
  - dashboard-api
  - dashboard-web
- ❌ No trader containers are started automatically
- Traders must be created from the UI

---

# 🧠 Score-Strategy Model

Score-Strategy includes:

- Universe selection
- Feature calculation
- Score ranking
- Entry rules
- Exit rules
- Risk application

### Built-in Strategies

- `STRAT_A` — Volume Spike + Breakout
- `STRAT_B` — Trend Stability / Momentum
- `STRAT_C` — Volatility Expansion

---

# 🎛 Risk Modes

| Mode | Description |
|------|------------|
| SAFE | Conservative |
| STANDARD | Balanced |
| PROFIT | Aggressive |
| CRAZY | High Risk |

⚠ CRAZY + LIVE requires double confirmation.

---

# 🔥 LIVE Mode Safety (ARM System)

LIVE trading has two states:

| State | Meaning |
|-------|--------|
| LIVE_READY | Live selected but trading blocked |
| LIVE_ARMED | Trading enabled |

LIVE trading starts only when:

```

mode == LIVE
AND live_armed == true

```

To enable:

```

POST /traders/{id}/arm_live

```

---

# 🐳 Trader Container Lifecycle

### Create Trader

```

POST /traders

```

Creates DB record + Docker container + starts it.

### Stop / Start

```

POST /traders/{id}/stop
POST /traders/{id}/start

```

### Recreate (Apply Updated Strategy Code)

```

POST /traders/{id}/recreate

```

Recreate process:

```

stop → remove → create (latest image) → start

```

> Restart does NOT guarantee updated code.
> Recreate is required.

---

# 🔄 docker-compose Down / Up Behavior

After `docker-compose down`:

- All database data is preserved
- Traders remain registered in DB
- Containers are NOT auto-started for safety
- Must manually start via UI

---

# 💰 Shared Account Policy

- Traders can share accounts
- `krw_allocation_limit` required
- Soft reservation (`reserved_krw`) prevents conflicts
- 2 consecutive failures may trigger `RISK_STOP`

---

# 📊 Database Core Tables

- `traders`
- `accounts`
- `scores`
- `orders`
- `trades`
- `positions`
- `config_versions`
- `config_current`
- `performance_daily`

All trading tables are separated by `trader_id`.

---

# 🎨 Dashboard UI

Built using **Bootstrap**.

Main Screens:

- Overview
- Trader List
- Trader Detail
- Orders / Trades
- Positions
- Scores
- Performance
- Settings

Initial screen shows:

```

No traders yet
[ Add Trader ]

````

---

# 🔐 Security

- API keys are AES encrypted
- No secrets exposed in logs
- LIVE trading requires manual ARM
- CRAZY mode requires double confirmation

---

# 📦 Requirements

- Docker
- Docker Compose
- Upbit API Key
- MariaDB (via container)

---

# 🏁 Quick Start

```bash
docker-compose up -d
````

Then open:

```
http://localhost:PORT
```

1. Add Account
2. Add Trader
3. Start Trader
4. (Optional) Switch to LIVE
5. ARM trading

---

# 🧪 Development Workflow

To update strategy logic:

```bash
docker compose build trader
docker compose up -d
```

Then from UI:

```
Recreate Trader Container
```

---

# 🏷 Version

**v1.7.0**

Stable architecture with:

* Dynamic container orchestration
* LIVE ARM safety system
* Strategy-code hot update via recreate
* Persistent DB state
* Bootstrap UI
* Multi-trader isolation

---

# 📄 License

Private / Internal Use (Customize as needed)

---

```

---