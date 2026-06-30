# Software Architecture Document
## AI-Powered Options Trading Research Platform — Indian Markets (NSE/BSE)

**Version**: 2.0 | **Date**: 2026-06-30 | **Classification**: Personal Research Tool

### Key Decisions vs v1.0
- Personal use → true monolith, Docker Compose on Mac Mini
- Mac Mini (owned) → $0 compute cost
- Kafka removed → Redis pub/sub
- ClickHouse removed → TimescaleDB handles personal-scale backtesting
- K8s/EKS removed → Docker Compose
- Kong removed → nginx
- RDS/ElastiCache removed → local PostgreSQL + Redis in Docker
- LLM split: Claude Sonnet (strategy + eval), Claude Haiku (risk), Groq free (research + monitor), Ollama (local backup)
- Access: Cloudflare Tunnel (free, no port forwarding)
- Frontend: Vercel free tier

---

## 1. High-Level Architecture

```mermaid
graph TB
    subgraph MAC ["Mac Mini — Docker Compose"]
        NGINX["nginx\nSSL + reverse proxy"]
        APP["FastAPI Monolith\nall services in one process"]
        CELERY["Celery Workers\nmarket data · agents · monitor"]
        BEAT["Celery Beat\nscheduler"]
        PG[("PostgreSQL 16\n+ TimescaleDB\n+ pgvector")]
        REDIS[("Redis\ncache · pub/sub · celery broker")]
        OLLAMA["Ollama\nLlama 3.3 70B\nlocal fallback LLM"]
    end

    subgraph EXTERNAL ["External Services"]
        KITE["Zerodha Kite\nConnect API"]
        NSE["NSE India\nOptions Chain · FII/DII"]
        NEWS["News\nET · MoneyControl"]
        GROQ["Groq API\nLlama 3.3 70B free\nResearch · Monitor agents"]
        CLAUDE_H["Anthropic Haiku 4.5\nRisk Assessment agent"]
        CLAUDE_S["Anthropic Sonnet 4.6\nStrategy + Evaluator agents"]
        SEBI["SEBI / RBI\nAnnouncements"]
    end

    subgraph ACCESS ["Access Layer"]
        CF["Cloudflare Tunnel\nfree · no port forwarding"]
        VERCEL["Vercel\nNext.js frontend · free tier"]
    end

    VERCEL --> CF
    CF --> NGINX
    NGINX --> APP
    APP --> PG
    APP --> REDIS
    CELERY --> PG
    CELERY --> REDIS
    CELERY --> OLLAMA
    BEAT --> REDIS

    CELERY --> KITE
    CELERY --> NSE
    CELERY --> NEWS
    CELERY --> SEBI
    CELERY --> GROQ
    CELERY --> CLAUDE_H
    CELERY --> CLAUDE_S
```

**Monthly cost: ₹2,700 (Kite ₹2,000 + Claude API ₹500 + electricity ₹200)**

---

## 2. Service Architecture

### Monolith Module Decomposition

Single FastAPI process. Modules are Python packages, not separate services.

```mermaid
graph TB
    subgraph MONOLITH ["FastAPI Monolith (app/)"]
        API["api/\nREST routers + WebSocket"]
        MKT["market_data/\nKite connector · NSE scraper"]
        ANALYTICS["analytics/\nGreeks · IV surface · OI · PCR"]
        AGENTS["agents/\norchestrator · 5 agents"]
        SIGNAL["signal/\ndetectors · filters · scorer"]
        RISK["risk/\nposition sizer · VaR · pre-trade"]
        PAPER["paper_trader/\nfill engine · MTM P&L"]
        BACKTEST["backtester/\nevent-driven engine"]
        MONITOR["monitor/\nstop-loss · Greeks watch"]
        NOTIF["notification/\nTelegram · email"]
    end

    subgraph WORKERS ["Celery Workers (tasks/)"]
        W_MKT["market_data tasks"]
        W_AI["agent tasks\n(rate-limited queue)"]
        W_MON["monitor tasks\n(high priority)"]
        W_BT["backtest tasks\n(low priority)"]
    end

    API --> MKT
    API --> ANALYTICS
    API --> SIGNAL
    API --> PAPER
    API --> BACKTEST
    API --> MONITOR

    W_MKT --> MKT
    W_AI --> AGENTS
    W_AI --> SIGNAL
    W_MON --> MONITOR
    W_MON --> RISK
    W_BT --> BACKTEST

    AGENTS --> ANALYTICS
    AGENTS --> SIGNAL
    SIGNAL --> RISK
    RISK --> PAPER
```

### Communication Within Monolith

- Module-to-module: direct Python function calls
- Async work: Celery tasks via Redis
- Real-time push to dashboard: Redis pub/sub → WebSocket

No HTTP between internal modules. No Kafka.

---

## 3. Folder Structure

```
options-research-platform/
├── app/
│   ├── api/
│   │   ├── routers/           # FastAPI routers per domain
│   │   ├── schemas/           # Pydantic request/response schemas
│   │   ├── websocket/         # WS handlers (ticks, P&L, alerts)
│   │   └── main.py            # FastAPI app init + router registration
│   ├── market_data/
│   │   ├── kite.py            # Kite Connect WebSocket + REST
│   │   ├── nse.py             # NSE options chain scraper
│   │   ├── news.py            # ET / MoneyControl scraper
│   │   └── normalizer.py      # Unified tick/chain schema
│   ├── analytics/
│   │   ├── greeks.py          # py_vollib Greeks computation
│   │   ├── iv_surface.py      # Vol surface construction
│   │   ├── oi_analysis.py     # OI, PCR, max pain
│   │   └── chain.py           # Options chain processor
│   ├── agents/
│   │   ├── orchestrator.py    # Agent run coordinator
│   │   ├── market_research.py # Groq Llama — news + FII synthesis
│   │   ├── strategy.py        # Claude Sonnet — strike/strategy selection
│   │   ├── risk_assessment.py # Claude Haiku — pre-trade risk check
│   │   ├── monitor.py         # Groq Llama — position health
│   │   ├── evaluator.py       # Claude Sonnet — self-improvement
│   │   ├── tools.py           # Tool definitions (Anthropic + OpenAI format)
│   │   ├── memory.py          # pgvector RAG interface
│   │   └── prompts/           # System prompts per agent
│   ├── signal/
│   │   ├── detectors/         # Pattern detectors per strategy
│   │   ├── filters.py         # Liquidity + statistical filters
│   │   └── scorer.py          # Composite signal score
│   ├── risk/
│   │   ├── sizer.py           # Kelly + fixed-fraction sizing
│   │   ├── var.py             # Historical simulation VaR
│   │   └── gates.py           # Pre-trade check layers
│   ├── paper_trader/
│   │   ├── fill_engine.py     # Slippage model + fill simulation
│   │   ├── portfolio.py       # Holdings + cash + MTM
│   │   └── pnl.py             # Greeks-decomposed P&L
│   ├── backtester/
│   │   ├── engine.py          # Event-driven backtest loop
│   │   ├── clock.py           # Simulation clock (injectable)
│   │   ├── broker.py          # Historical fill simulator
│   │   ├── strategies/        # BaseStrategy + implementations
│   │   └── metrics.py         # Sharpe, Sortino, drawdown, win-rate
│   ├── monitor/
│   │   ├── watcher.py         # Stop-loss + expiry proximity
│   │   └── greeks_live.py     # Real-time portfolio Greeks
│   ├── notification/
│   │   ├── telegram.py
│   │   └── email.py
│   └── core/
│       ├── config.py          # pydantic-settings from .env
│       ├── db.py              # SQLAlchemy async engine
│       ├── redis.py           # Redis client singleton
│       ├── calendar.py        # NSE market calendar + hours check
│       └── constants.py       # NSE lot sizes, expiry rules
├── tasks/
│   ├── market_data.py         # Celery tasks: chain refresh, tick ingest
│   ├── agents.py              # Celery tasks: daily research cycle
│   ├── monitor.py             # Celery tasks: stop-loss, Greeks refresh
│   └── backtest.py            # Celery tasks: async backtest run
├── models/                    # SQLAlchemy ORM models
├── migrations/                # Alembic migrations
├── frontend/                  # Next.js app (deployed to Vercel)
│   ├── src/
│   │   ├── app/               # App Router pages
│   │   ├── components/
│   │   │   ├── charts/        # TradingView, payoff, IV surface
│   │   │   ├── options-chain/
│   │   │   └── positions/
│   │   ├── hooks/
│   │   ├── stores/            # Zustand
│   │   └── lib/               # API + WebSocket client
│   └── public/
├── scripts/
│   ├── backfill.py            # Historical OHLCV + chain backfill
│   └── market_calendar.py     # Sync NSE holiday calendar
├── docker-compose.yml         # 6 containers (see Section 19)
├── nginx/
│   └── nginx.conf
├── .env                       # secrets (local only, never committed)
└── .github/workflows/         # CI: lint + test only
```

---

## 4. Database Design

### Single Store: PostgreSQL 16 + TimescaleDB + pgvector

No ClickHouse. TimescaleDB with compression handles personal-scale backtesting. pgvector handles embeddings. One DB, one connection pool.

```mermaid
erDiagram
    INSTRUMENTS {
        uuid id PK
        string symbol
        string exchange
        string instrument_type
        string underlying
        date expiry
        float strike
        string option_type
        int lot_size
        timestamp created_at
    }

    OHLCV_1MIN {
        uuid instrument_id FK
        timestamp time
        float open
        float high
        float low
        float close
        bigint volume
        bigint oi
    }

    OPTIONS_CHAIN_SNAPSHOT {
        uuid id PK
        string underlying
        date expiry
        timestamp snapshot_time
        jsonb chain_data
    }

    SIGNALS {
        uuid id PK
        uuid instrument_id FK
        uuid agent_run_id FK
        timestamp generated_at
        string strategy_type
        float score
        float confidence
        jsonb parameters
        string status
    }

    AGENT_RUNS {
        uuid id PK
        string agent_name
        string model_used
        timestamp started_at
        timestamp completed_at
        jsonb input_context
        jsonb output
        string status
        int tokens_in
        int tokens_out
        float cost_usd
        float latency_ms
    }

    PAPER_TRADES {
        uuid id PK
        uuid signal_id FK
        uuid instrument_id FK
        string action
        float entry_price
        int quantity
        timestamp entered_at
        float exit_price
        timestamp exited_at
        float realized_pnl
        float unrealized_pnl
        string exit_reason
        jsonb metadata
    }

    POSITIONS {
        uuid id PK
        uuid paper_trade_id FK
        float current_price
        float delta
        float gamma
        float theta
        float vega
        float iv
        timestamp updated_at
    }

    BACKTEST_RUNS {
        uuid id PK
        string strategy_name
        jsonb parameters
        date from_date
        date to_date
        float total_return
        float sharpe_ratio
        float max_drawdown
        float win_rate
        int total_trades
        timestamp ran_at
        jsonb full_metrics
    }

    MARKET_RESEARCH {
        uuid id PK
        timestamp created_at
        string source_type
        string underlying
        text summary
        jsonb structured_analysis
        vector embedding
        string sentiment
    }

    INSTRUMENTS ||--o{ OHLCV_1MIN : "has"
    INSTRUMENTS ||--o{ SIGNALS : "generates"
    AGENT_RUNS ||--o{ SIGNALS : "produces"
    SIGNALS ||--o{ PAPER_TRADES : "creates"
    PAPER_TRADES ||--|| POSITIONS : "has"
```

### TimescaleDB Config

```
OHLCV_1MIN             → hypertable, chunk_interval=1day, retention=5years
OPTIONS_CHAIN_SNAPSHOT → hypertable, chunk_interval=4hours, retention=2years
```

Compression after 7 days. For personal watchlist (~30 instruments):
- OHLCV: ~2.8M rows/year → compressed ~30MB/year (trivial)
- Chain snapshots: ~12,500/year → ~6GB/year uncompressed, ~600MB compressed

No ClickHouse needed at this scale.

### Redis Key Patterns

| Key | TTL | Purpose |
|-----|-----|---------|
| `market:tick:{symbol}` | 5s | Latest tick |
| `options:chain:{underlying}:{expiry}` | 30s | Chain cache |
| `signal:pending:{id}` | 1hr | Unprocessed signal |
| `position:pnl:{trade_id}` | 60s | Live MTM |
| `agent:context:{run_id}` | 2hr | Agent working memory |
| `ratelimit:kite:{endpoint}` | 1s | API rate bucket |
| `job:lock:{job_name}` | job_timeout | Duplicate job prevention |
| `pubsub:tick:{symbol}` | — | WebSocket broadcast channel |
| `pubsub:pnl` | — | P&L broadcast channel |
| `pubsub:signal:new` | — | Signal notification channel |

---

## 5. Monolith Decision

**Decision: True Monolith. No microservices.**

Personal app. One user. One Mac Mini. Complexity of microservices = pure overhead with zero benefit.

```mermaid
graph LR
    subgraph MONOLITH ["Single Python Process"]
        ALL["All modules\nDirect function calls\nShared DB pool\nShared Redis client"]
    end

    subgraph WORKERS ["Celery Worker Processes"]
        CW["2-4 Celery workers\nSpawned by Docker Compose\nSame codebase as monolith"]
    end

    subgraph IF_NEEDED ["Extract Only If Mac Mini CPU > 80% sustained"]
        MS["Backtester\nas separate process"]
    end

    MONOLITH -->|"enqueue heavy tasks"| WORKERS
    MONOLITH -.->|"future only if needed"| IF_NEEDED
```

Internal module calls are function calls, not HTTP. Zero serialization overhead. Shared SQLAlchemy session pool. No service discovery needed.

---

## 6. API Architecture

### Design

- REST for all resource endpoints
- WebSocket for real-time ticks, P&L, alerts
- nginx handles SSL termination + static file serving
- No API gateway, no rate limiting beyond nginx basic limits

### Endpoint Inventory

```
Auth
  POST   /api/v1/auth/login
  POST   /api/v1/auth/refresh
  POST   /api/v1/auth/logout

Market Data
  GET    /api/v1/market/instruments
  GET    /api/v1/market/quote/{symbol}
  GET    /api/v1/market/ohlcv/{symbol}?interval=1m&from=&to=
  GET    /api/v1/market/options-chain/{underlying}/{expiry}
  WS     /ws/market/ticks/{symbol}

Analytics
  GET    /api/v1/analytics/iv-surface/{underlying}
  GET    /api/v1/analytics/greeks/{instrument_id}
  GET    /api/v1/analytics/oi-analysis/{underlying}
  GET    /api/v1/analytics/pcr/{underlying}
  GET    /api/v1/analytics/max-pain/{underlying}/{expiry}

AI Research
  POST   /api/v1/research/trigger
  GET    /api/v1/research/runs
  GET    /api/v1/research/runs/{run_id}
  GET    /api/v1/research/insights/{underlying}

Signals
  GET    /api/v1/signals
  GET    /api/v1/signals/{id}
  POST   /api/v1/signals/{id}/approve
  POST   /api/v1/signals/{id}/reject

Paper Trading
  GET    /api/v1/paper/portfolio
  GET    /api/v1/paper/trades
  GET    /api/v1/paper/trades/{id}
  POST   /api/v1/paper/trades/{signal_id}/execute
  POST   /api/v1/paper/trades/{id}/close
  WS     /ws/paper/pnl

Backtesting
  POST   /api/v1/backtest/run
  GET    /api/v1/backtest/runs
  GET    /api/v1/backtest/runs/{id}
  GET    /api/v1/backtest/runs/{id}/trades

Positions
  GET    /api/v1/positions
  GET    /api/v1/positions/{id}
  WS     /ws/positions/alerts
```

### nginx Config Role

```
HTTPS termination (Let's Encrypt via Certbot)
Proxy /api/ and /ws/ → FastAPI :8000
Serve /static/ → local files
Cloudflare Tunnel connects here
```

---

## 7. Authentication Architecture

Single user app. Simple JWT middleware in FastAPI. No separate auth service.

```mermaid
sequenceDiagram
    participant U as Browser/App
    participant CF as Cloudflare Tunnel
    participant NGINX as nginx
    participant APP as FastAPI

    U->>CF: POST /api/v1/auth/login {email, password}
    CF->>NGINX: forward
    NGINX->>APP: forward
    APP->>APP: bcrypt verify against .env ADMIN_PASSWORD_HASH
    APP->>APP: sign JWT (HS256, secret from .env)
    APP-->>U: {access_token 24hr, refresh_token 30d}

    U->>CF: GET /api/v1/signals [Bearer token]
    CF->>NGINX: forward
    NGINX->>APP: forward
    APP->>APP: FastAPI dependency: verify_jwt()
    APP-->>U: response
```

**Design choices:**
- HS256 (symmetric): simpler, single server, no key distribution needed
- Access token 24hr TTL: longer than enterprise because personal use, no session risk
- Refresh token 30d in Redis: revocable on logout
- Password: single admin password hash stored in `.env`
- No OAuth, no user management, no RBAC: one user

---

## 8. Background Jobs

| Job | Trigger | Schedule | Celery Queue |
|-----|---------|----------|--------------|
| Options chain refresh | Scheduled | Every 3 min, market hours | market |
| Historical tick backfill | Manual | On demand | market |
| FII/DII data fetch | Scheduled | Daily 18:00 IST | market |
| NSE circular scrape | Scheduled | Daily 07:00 IST | ai |
| Daily market research | Scheduled | Daily 08:30 IST | ai |
| IV surface recompute | On chain update (Redis pub/sub) | Triggered | analytics |
| Signal generation | On analytics update | Triggered | analytics |
| Position Greeks refresh | Scheduled | Every 5 min, market hours | monitor |
| Stop-loss checker | Scheduled | Every 1 min, market hours | monitor |
| Daily P&L reconciliation | Scheduled | 16:00 IST | monitor |
| Signal outcome evaluator | Scheduled | Daily 16:30 IST | ai |
| Expiry rollover detector | Scheduled | Daily 09:00 IST | market |

```mermaid
graph TB
    BEAT["Celery Beat\n(in Docker container)"] --> REDIS[("Redis\nBroker")]
    REDIS --> WM["Worker: market\nconcurrency=2"]
    REDIS --> WAI["Worker: ai\nconcurrency=1\n(LLM rate-limited)"]
    REDIS --> WAN["Worker: analytics\nconcurrency=2"]
    REDIS --> WMON["Worker: monitor\nconcurrency=2, priority=high"]
    REDIS --> WBT["Worker: backtest\nconcurrency=4, priority=low"]

    WM --> PG[("PostgreSQL")]
    WAI --> PG
    WAN --> PG
    WMON --> PG
    WBT --> PG

    WAI --> GROQ["Groq API"]
    WAI --> CLAUDE_H["Claude Haiku"]
    WAI --> CLAUDE_S["Claude Sonnet"]
    WAI --> OLLAMA["Ollama (fallback)"]
```

Celery Beat and all workers share same codebase via Docker Compose volumes.

---

## 9. Scheduler Design

### Market-Hours-Aware

```mermaid
graph TB
    BEAT["Celery Beat / APScheduler"] --> CHK{"market_open()\nIST clock\n+ NSE holidays table"}

    CHK -->|"Yes 09:15-15:30 IST"| MH["Market-Hours Tasks"]
    CHK -->|"No"| AMH["After-Hours Tasks"]

    MH --> J1["chain_refresh: every 3min"]
    MH --> J2["greeks_update: every 5min"]
    MH --> J3["stoploss_check: every 1min"]
    MH --> J4["kite_tick_stream: continuous"]

    AMH --> J5["market_research: 08:30 IST"]
    AMH --> J6["fii_dii_fetch: 18:00 IST"]
    AMH --> J7["signal_evaluator: 16:30 IST"]
    AMH --> J8["pnl_reconcile: 16:00 IST"]
```

### Mac Mini Wake/Sleep (Power Save)

```bash
# wake at 08:45 IST on weekdays
sudo pmset repeat wakeorpoweron MTWRF 03:15:00  # 08:45 IST = 03:15 UTC

# sleep at 16:15 IST
sudo pmset repeat sleep MTWRF 10:45:00           # 16:15 IST = 10:45 UTC
```

Saves ~18hr/day idle electricity. Mac Mini at load: ~30W → ~10W avg → ₹150/month.

### Distributed Lock (prevent duplicate jobs on restart)

```
Redis SETNX job:lock:{job_name} {pid} EX {max_duration_seconds}
```

---

## 10. Event-Driven Architecture

### Redis Pub/Sub (replaces Kafka)

No Kafka. Redis pub/sub handles all internal events. Sufficient for personal scale (one user, ~30 instruments, low event volume).

```mermaid
graph LR
    subgraph PUBLISHERS ["Publishers (Celery Tasks)"]
        MKT["Market Data Task"]
        ANALYTICS["Analytics Task"]
        SIGNAL["Signal Task"]
        MONITOR["Monitor Task"]
    end

    subgraph CHANNELS ["Redis Pub/Sub Channels"]
        C1["channel: market:chain:updated\npayload: underlying, expiry"]
        C2["channel: analytics:computed\npayload: underlying"]
        C3["channel: signal:generated\npayload: signal_id, score"]
        C4["channel: position:alert\npayload: trade_id, type"]
        C5["channel: market:tick:{symbol}\npayload: price, timestamp"]
    end

    subgraph SUBSCRIBERS ["Subscribers"]
        SUB_A["Analytics task subscriber"]
        SUB_S["Signal task subscriber"]
        SUB_N["Notification subscriber"]
        SUB_WS["WebSocket relay\n(FastAPI background task)"]
    end

    MKT -->|"publish"| C1
    MKT -->|"publish"| C5
    ANALYTICS -->|"publish"| C2
    SIGNAL -->|"publish"| C3
    MONITOR -->|"publish"| C4

    C1 --> SUB_A
    C2 --> SUB_S
    C3 --> SUB_N
    C3 --> SUB_WS
    C4 --> SUB_N
    C4 --> SUB_WS
    C5 --> SUB_WS
```

**Trade-off vs Kafka:**
- No message replay (acceptable: DB is source of truth, events are triggers only)
- No consumer group offset management (one subscriber per channel, personal use)
- No durability guarantee (if task missed, Celery Beat re-triggers on next schedule)

---

## 11. AI Agent Architecture

### Model Assignment

| Agent | Model | Provider | Cost | Reason |
|-------|-------|----------|------|--------|
| Market Research | Llama 3.3 70B | Groq (free) | $0 | News synthesis, no complex reasoning |
| **Strategy** | **claude-sonnet-4-6** | Anthropic | ~$0.08/day | Core value — strike selection, strategy design |
| Risk Assessment | claude-haiku-4-5 | Anthropic | ~$0.007/day | Reliable tool use, structured output |
| Monitor | Llama 3.3 70B | Groq (free) | $0 | Simple position check, no deep reasoning |
| **Evaluator** | **claude-sonnet-4-6** | Anthropic | ~$0.11/day | Self-improvement loop, calibration analysis |
| Fallback (all) | Qwen2.5 14B / Llama 3.1 8B | Ollama (local) | $0 | Groq/Anthropic outage |

**Daily total: ~$0.20/day = ₹500/month**

### Agent Architecture

```mermaid
graph TB
    subgraph ORCH ["Orchestrator (orchestrator.py)"]
        O["async task coordinator\nruns via Celery ai queue"]
    end

    subgraph AGENTS ["Agents"]
        MRA["market_research.py\nGroq Llama 3.3 70B"]
        SA["strategy.py\nClaude Sonnet 4.6"]
        RAA["risk_assessment.py\nClaude Haiku 4.5"]
        MON["monitor.py\nGroq Llama 3.3 70B"]
        EVAL["evaluator.py\nClaude Sonnet 4.6"]
    end

    subgraph TOOLS ["tools.py — shared tool definitions"]
        TL1["get_options_chain(underlying, expiry)"]
        TL2["get_ohlcv(symbol, interval, n_bars)"]
        TL3["get_greeks(instrument_id)"]
        TL4["get_oi_analysis(underlying)"]
        TL5["search_news(query, date_range)"]
        TL6["get_fii_dii_data(date)"]
        TL7["get_past_signals(filters)"]
        TL8["get_position_pnl(trade_id)"]
        TL9["get_iv_surface(underlying)"]
    end

    subgraph MEM ["memory.py"]
        STM["Short-term: Redis\nper-run context TTL 2hr"]
        LTM["Long-term: pgvector RAG\nmarket knowledge base"]
        EPI["Episodic: PostgreSQL\nsignal outcomes"]
    end

    subgraph CLIENTS ["LLM Clients (OpenAI-compatible interface)"]
        GROQ_C["Groq client\nbase_url: api.groq.com/openai/v1"]
        ANT_C["Anthropic client\nnative SDK"]
        OLLAMA_C["Ollama client\nbase_url: localhost:11434/v1"]
    end

    O --> MRA & SA & RAA & MON & EVAL

    MRA --> TL5 & TL6 & TL2
    SA --> TL1 & TL3 & TL4 & TL9
    RAA --> TL3 & TL2
    MON --> TL8 & TL2
    EVAL --> TL7 & TL8

    MRA --> GROQ_C
    MON --> GROQ_C
    SA --> ANT_C
    EVAL --> ANT_C
    RAA --> ANT_C

    GROQ_C -.->|"outage fallback"| OLLAMA_C
    ANT_C -.->|"outage fallback"| OLLAMA_C

    MRA <--> STM
    SA <--> STM
    MRA <--> LTM
    EVAL <--> EPI
```

### Daily Research Cycle

```mermaid
sequenceDiagram
    participant BEAT as Celery Beat 08:30 IST
    participant O as Orchestrator
    participant MRA as Market Research\n(Groq free)
    participant SA as Strategy Agent\n(Claude Sonnet)
    participant RAA as Risk Assessment\n(Claude Haiku)
    participant DB as PostgreSQL
    participant VEC as pgvector
    participant REDIS as Redis pub/sub

    BEAT->>O: trigger daily_research_cycle
    O->>MRA: run(date, watchlist)
    MRA->>MRA: fetch news, FII/DII, SEBI circulars
    MRA->>VEC: retrieve similar_past_conditions (top-5)
    MRA->>MRA: Groq: synthesize market_view per sector
    MRA->>DB: store research + embedding
    MRA-->>O: market_view_summary

    O->>SA: run(market_view, watchlist)
    SA->>SA: fetch options chain, IV surface, OI
    SA->>SA: Claude Sonnet: identify CE/PE/spread/straddle opportunities
    SA->>SA: Claude Sonnet: set strike, expiry, target, stop-loss
    SA-->>O: strategy_recommendations[]

    loop each recommendation
        O->>RAA: validate(recommendation)
        RAA->>RAA: Claude Haiku: risk/reward + portfolio check
        RAA-->>O: approved|rejected + reasoning
    end

    O->>DB: persist approved signals
    O->>REDIS: publish signal:generated
```

### Evaluator Agent (Self-Improvement Loop)

Runs daily 16:30 IST.

**Inputs:** Past 30 days signals + price outcomes + paper trade P&L + Greeks at entry/exit

**Outputs:**
- Win/loss by strategy type + market regime
- Confidence calibration score
- Prompt performance notes → stored to DB → retrieved by RAG in next research cycle
- Adjusts `confidence_multiplier` per strategy type in DB

---

## 12. Risk Management Architecture

### Risk Layers

```mermaid
graph TB
    SIGNAL["Signal from Strategy Agent"] --> L1

    subgraph L1 ["Layer 1 — Portfolio Checks"]
        L1A["Max open positions <= 5"]
        L1B["Sector concentration < 40%"]
        L1C["Net portfolio delta within band"]
        L1D["Capital utilization < 80%"]
    end

    L1 -->|"all pass"| L2

    subgraph L2 ["Layer 2 — Position Sizing"]
        L2A["Fractional Kelly: 0.25x"]
        L2B["Max 2% paper portfolio per trade"]
        L2C["99% 1-day VaR < 5% portfolio"]
    end

    L2 -->|"sized"| L3

    subgraph L3 ["Layer 3 — Trade Parameters (Claude Haiku validates)"]
        L3A["Stop-loss defined"]
        L3B["R:R >= 1.5:1"]
        L3C["Expiry > 7 days"]
        L3D["Bid-ask spread < 2%"]
    end

    L3 -->|"approved"| EXEC["Paper Trade"]
    L1 & L2 & L3 -->|"any fail"| REJECT["Rejected + reason logged"]

    subgraph RUNTIME ["Runtime (every 1min, market hours)"]
        SL["Stop-loss watcher"]
        THETA_W["Theta burn alert > -Rs2000/day"]
        EXP_W["Expiry < 3 days alert"]
        DELTA_W["Portfolio delta breach"]
    end

    EXEC --> RUNTIME
```

### Risk Metrics

| Metric | Alert Threshold |
|--------|----------------|
| Portfolio Delta | net > Rs50,000 |
| Portfolio Vega | net > Rs10,000 |
| Daily Theta Burn | < -Rs2,000/day |
| Max Drawdown | > 15% |
| Win Rate (30d) | < 40% triggers evaluator |
| VaR 99% 1-day | > 5% portfolio |

---

## 13. Paper Trading Architecture

```mermaid
sequenceDiagram
    participant U as User
    participant API as FastAPI
    participant RM as Risk Module
    participant MKT as Market Data Module
    participant DB as PostgreSQL
    participant REDIS as Redis

    U->>API: POST /paper/trades/{signal_id}/execute
    API->>RM: pre_trade_check(signal)
    RM-->>API: approved + sized_quantity
    API->>MKT: get_best_bid_ask(instrument)
    MKT-->>API: {bid, ask}
    API->>API: fill_price = slippage_model(bid, ask, qty)
    API->>DB: INSERT paper_trade
    API->>REDIS: PUBLISH position:pnl initial
    API-->>U: trade_confirmation

    loop Every 5 min (market hours via Celery)
        API->>MKT: get_mark_price(open_instruments)
        API->>API: unrealized_pnl + Greeks decomposition
        API->>DB: UPDATE positions
        API->>REDIS: PUBLISH position:pnl
    end
```

### Slippage Model

```
Liquid   (OI > 1,000, spread < 1%):   fill = mid + 0.5 × spread
Semi-liq (OI 200–1,000, spread 1-2%): fill = ask
Illiquid (OI < 200, spread > 2%):     fill = ask × 1.005, partial fill warning
```

---

## 14. Backtesting Architecture

TimescaleDB replaces ClickHouse. Personal watchlist = small data. TimescaleDB with chunk compression handles it.

```mermaid
graph TB
    subgraph IN ["Inputs"]
        CFG["Strategy Config\n(params, date range, paper capital)"]
        HIST["Historical Data\n(PostgreSQL + TimescaleDB)"]
    end

    subgraph ENGINE ["Backtest Engine (backtester/)"]
        FEED["Historical Data Feed\n(time-ordered events from TimescaleDB)"]
        CLOCK["Simulation Clock\n(injectable, overrides datetime.now)"]
        BROKER["Simulated Broker\n(historical bid/ask fills)"]
        PORT["Portfolio Manager\n(holdings, cash, MTM P&L)"]
        RM_BT["Risk Module\n(same code as live — no separate instance)"]
    end

    subgraph STRAT ["Strategies"]
        BASE["BaseStrategy"]
        S1["LongStraddle"]
        S2["BullCallSpread"]
        S3["IronCondor"]
        S4["ProtectivePut"]
        CUSTOM["AI-Strategy\n(replay AI recommendations)"]
    end

    subgraph OUT ["Outputs (stored in backtest_runs table)"]
        METRICS["Sharpe · Sortino · MDD · Win Rate"]
        TRADES["Trade log (JSONB in backtest_runs)"]
        EQUITY["Equity curve (JSONB)"]
        REPORT["HTML report served via /api/v1/backtest/runs/id"]
    end

    CFG & HIST --> FEED
    FEED --> CLOCK --> BASE
    BASE --> S1 & S2 & S3 & S4 & CUSTOM
    S1 -->|"orders"| BROKER
    BROKER -->|"fills"| PORT
    PORT --> RM_BT --> BASE
    PORT --> METRICS & TRADES & EQUITY --> REPORT
```

### Anti-Patterns Prevented

| Anti-Pattern | Prevention |
|-------------|------------|
| Look-ahead bias | Feed filters `t <= simulation_time` |
| Survivorship bias | Full instrument universe including expired contracts |
| Slippage ignored | Historical bid/ask from `options_chain_snapshot` |
| Overfitting | Walk-forward OOS test required before accepting strategy |
| Expiry not handled | Auto-close at NSE settlement price |
| Transaction costs ignored | STT + brokerage modeled |

---

## 15. Historical Replay Architecture

Same as backtesting engine but all live modules run against replayed data.

```mermaid
graph TB
    subgraph CTRL ["Replay Controller (UI-driven)"]
        RC["Replay Controller"]
        SPEED["Speed: 1x · 10x · 100x · jump-to"]
        CLOCK["SimulatedClock\n(injected into all modules)"]
    end

    subgraph FEED ["Historical Feed"]
        HF["Event Player\n(reads TimescaleDB, emits Redis pub/sub on replay channels)"]
    end

    subgraph MODULES ["Live Modules (Replay Mode)"]
        OAS["analytics module"]
        AI["agents module"]
        SIG["signal module"]
        PT["paper_trader module\n(isolated replay portfolio)"]
        DASH["Dashboard\n(shows past state)"]
    end

    RC --> CLOCK & SPEED
    SPEED --> HF
    HF -->|"publish replay:chain:* replay:tick:*"| REDIS_R["Redis\nreplay channels"]
    REDIS_R --> OAS & AI
    OAS --> SIG
    AI --> SIG
    SIG --> PT
    PT --> DASH
    CLOCK -.->|"datetime.now() override"| OAS & AI
```

Clock injection via `app/core/clock.py` — `ClockProvider` dependency. Live mode: `datetime.now(IST)`. Replay mode: `SimulatedClock.now()`. Results stored under isolated `replay_run_id`.

---

## 16. Dashboard Architecture

```mermaid
graph TB
    subgraph VERCEL ["Next.js on Vercel (free tier)"]
        HOME["/ — Market overview + portfolio summary"]
        SIG_PG["/signals — Pending · approved · rejected"]
        POS_PG["/positions — Open trades + live Greeks"]
        RES_PG["/research — AI market view + history"]
        BT_PG["/backtest — Run + results + equity curve"]
        SET_PG["/settings — Watchlist · risk params"]
    end

    subgraph COMPONENTS ["Key Components"]
        TV["PriceChart\n(TradingView Lightweight Charts)"]
        OC["OptionsChainTable\nstrike-wise CE/PE"]
        IV["IVSurface\n3D vol surface"]
        PO["PayoffDiagram\nstrategy P&L at expiry"]
        GP["GreeksPanel\nportfolio aggregated"]
        SC["SignalCard\nAI recommendation + reasoning"]
        EC["EquityCurve\nbacktest result"]
    end

    subgraph DATA ["Data Layer"]
        TQ["TanStack Query — REST + cache"]
        WS["WebSocket Client — Redis pub/sub relay"]
        ZS["Zustand — live state"]
    end

    HOME --> TV & GP
    SIG_PG --> SC & PO
    POS_PG --> OC & GP
    RES_PG --> IV
    BT_PG --> EC

    TQ <-->|"REST via Cloudflare Tunnel"| APP["FastAPI on Mac Mini"]
    WS <-->|"WSS via Cloudflare Tunnel"| APP
    ZS <--- TQ & WS
```

### Real-Time Updates

| Data | Mechanism | Frequency |
|------|-----------|-----------|
| Price ticks | WebSocket (Redis pub/sub relay) | On tick |
| Options chain | TanStack Query poll | 30 sec |
| Portfolio MTM P&L | WebSocket | 5 sec |
| Greeks | TanStack Query | 60 sec |
| New signals | WebSocket toast notification | On event |
| Stop-loss alerts | WebSocket modal | Immediate |

---

## 17. Monitoring

Simple setup. No Loki/Jaeger at personal scale. Prometheus + Grafana run in Docker Compose.

```mermaid
graph TB
    subgraph MAC ["Mac Mini Docker Compose"]
        APP["FastAPI\n(prometheus_client endpoint :9090/metrics)"]
        CELERY_W["Celery Workers\n(prometheus_client)"]
        PROM["Prometheus\n(scrape every 30s)"]
        GRAFANA["Grafana\n(:3000, local only)"]
    end

    subgraph ALERTS ["Alerts"]
        AM["AlertManager"]
        TG["Telegram Bot\n(personal channel)"]
    end

    APP --> PROM
    CELERY_W --> PROM
    PROM --> GRAFANA
    PROM --> AM --> TG
```

Grafana accessed via `localhost:3000` or via Cloudflare Tunnel if needed remotely.

### Key Metrics

**Market Data**
- `tick_ingest_rate` — ticks/sec
- `kite_api_latency_ms` — p50/p95
- `chain_staleness_seconds` — how old last chain fetch is

**AI Agents**
- `agent_run_duration_seconds{agent}` — per agent latency
- `llm_tokens_used_total{agent, provider}` — token tracking
- `llm_cost_usd_total{agent}` — cost tracking
- `signals_generated_total` / `signals_rejected_total`

**Portfolio**
- `open_positions_count`
- `portfolio_pnl_inr` — live gauge
- `portfolio_delta` — net delta gauge

**System**
- `redis_memory_bytes`
- `postgres_connections_active`
- `celery_queue_depth{queue}`
- Mac Mini CPU/memory via `node_exporter`

### Grafana Dashboards

1. Market Data Health — tick rate, chain freshness, Kite latency
2. AI Agent Activity — runs, tokens per model, cost trend
3. Portfolio Overview — P&L, positions, Greeks exposure
4. System Health — CPU, memory, disk, queue depth

---

## 18. Logging

Structured logging only. No Loki at personal scale — log files on disk, rotated daily.

```mermaid
graph LR
    APP["FastAPI\nCelery Workers"] -->|"structlog JSON"| STDOUT["stdout"]
    STDOUT -->|"Docker log driver"| FILES["Log files\n/var/log/app/\n(rotated daily, 30d retention)"]
    FILES -->|"optional: tail -f"| TERMINAL["Terminal\n(debugging)"]
    FILES -->|"optional future"| LOKI["Grafana Loki\n(add if log search needed)"]
```

### Log Schema

```json
{
  "timestamp": "2026-06-30T09:15:00.123Z",
  "level": "info",
  "module": "agents.strategy",
  "event": "agent_run_completed",
  "agent": "strategy_agent",
  "model": "claude-sonnet-4-6",
  "run_id": "uuid",
  "duration_ms": 4521,
  "tokens_in": 8432,
  "tokens_out": 1847,
  "cost_usd": 0.078,
  "signals_generated": 3
}
```

### Log Level Policy

| Level | Events |
|-------|--------|
| ERROR | Unhandled exceptions, API auth failures, DB errors |
| WARN | Kite rate limit, signal rejected, stop-loss triggered |
| INFO | Job start/end, signal approved, trade executed, agent run |
| DEBUG | Tick processed, Greeks computed (disabled by default) |

---

## 19. Deployment Architecture

Single `docker-compose.yml`. No K8s. No CI/CD pipeline for prod — deploy manually on Mac Mini.

### docker-compose.yml Services

```yaml
# 6 containers total

postgres:
  image: timescale/timescaledb-ha:pg16
  volumes: [./data/postgres:/var/lib/postgresql/data]
  env_file: .env

redis:
  image: redis:7-alpine
  volumes: [./data/redis:/data]
  command: redis-server --appendonly yes

app:
  build: .
  command: uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --workers 2
  depends_on: [postgres, redis]
  env_file: .env
  volumes: [.:/code]

celery:
  build: .
  command: celery -A tasks worker -Q market,ai,analytics,monitor,backtest --concurrency 4
  depends_on: [postgres, redis]
  env_file: .env

celery-beat:
  build: .
  command: celery -A tasks beat --scheduler celery.beat:PersistentScheduler
  depends_on: [redis]
  env_file: .env

nginx:
  image: nginx:alpine
  volumes: [./nginx/nginx.conf:/etc/nginx/nginx.conf, ./certs:/etc/nginx/certs]
  ports: ["80:80", "443:443"]
  depends_on: [app]
```

Ollama runs natively on Mac Mini (not in Docker — needs direct GPU/Metal access):

```bash
# install once
brew install ollama
ollama pull llama3.3:70b   # if 32GB+ RAM
ollama pull qwen2.5:14b    # if 16GB RAM
ollama serve               # runs on localhost:11434
```

### Cloudflare Tunnel Setup

```bash
# install once
brew install cloudflared
cloudflared tunnel login
cloudflared tunnel create options-research
cloudflared tunnel route dns options-research yourdomain.com
cloudflared tunnel run options-research   # add to launchd for autostart
```

Tunnel config (`~/.cloudflared/config.yml`):
```yaml
tunnel: <tunnel-id>
ingress:
  - hostname: yourdomain.com
    service: http://localhost:80
  - service: http_status:404
```

### Deployment Flow

```mermaid
sequenceDiagram
    participant DEV as You
    participant GH as GitHub
    participant MAC as Mac Mini

    DEV->>GH: git push (feature branch)
    GH->>GH: GitHub Actions: ruff + mypy + pytest
    DEV->>MAC: ssh mac-mini (or Tailscale)
    MAC->>MAC: git pull origin main
    MAC->>MAC: docker compose up -d --build
    MAC->>MAC: alembic upgrade head
```

No ArgoCD. No ECR. Pull code + rebuild locally.

---

## 20. Scalability Considerations

Personal app. Scaling is not a goal. Notes for future if needed:

| If This Happens | Do This |
|----------------|---------|
| Mac Mini CPU > 80% sustained | Move backtester to EC2 spot burst |
| Need 24/7 uptime without Mac Mini | Add Oracle Free Tier as always-on host |
| 70B model too slow on 16GB | Use Groq free API instead of Ollama |
| PostgreSQL slow on backtest queries | Add TimescaleDB continuous aggregates + indexes |
| Kite WebSocket disconnects frequently | Add reconnect logic + Redis tick cache |

### Data Volume (Personal Watchlist ~30 instruments)

| Table | Rows/Year | Size/Year (compressed) |
|-------|----------|------------------------|
| OHLCV_1MIN | ~2.8M | ~30 MB |
| OPTIONS_CHAIN snapshots | ~12,500 | ~600 MB |
| SIGNALS | ~2,500 | < 1 MB |
| PAPER_TRADES | ~750 | < 1 MB |

Mac Mini 256GB SSD holds 10+ years of data comfortably.

---

## 21. Failure Recovery

Personal app. Acceptable downtime during market hours = 15-30 min max (miss some ticks, not catastrophic — paper trading only).

```mermaid
graph TB
    F1["Kite API down"] --> R1["Fallback: NSE Python unofficial\nCache last chain in Redis\nAlert via Telegram"]
    F2["Groq API down"] --> R2["Fallback: Ollama local\nDegrade gracefully for research agent"]
    F3["Anthropic API down"] --> R3["Queue agent runs\nRetry every 15min up to 2hr\nSkip if research cycle stale"]
    F4["PostgreSQL down"] --> R4["Docker auto-restart\nData safe on volume\nAlert via Telegram"]
    F5["Mac Mini sleep/reboot"] --> R5["Docker restart=always\nServices auto-start on boot\npmset prevents sleep during market hours"]
    F6["Internet outage"] --> R6["Kite WebSocket reconnects\nCloudflare Tunnel reconnects\nLocal dashboard still works on LAN"]
```

### Mac Mini Resilience

```bash
# all containers restart on reboot
restart: always  # in docker-compose.yml

# prevent Mac Mini sleep during market hours
sudo pmset -a sleep 0       # disable sleep
caffeinate -di &            # keep display + disk awake
```

### Backup

| Data | Backup | Frequency |
|------|--------|-----------|
| PostgreSQL | `pg_dump` → local external drive + Backblaze B2 (~Rs100/month) | Daily 20:00 IST |
| Redis | AOF persistence on volume | Continuous |
| .env + configs | Encrypted note (1Password/Bitwarden) | On change |
| Code | GitHub | On push |

---

## 22. Technology Stack with Justification

### Core Runtime

| Technology | Justification |
|-----------|--------------|
| Python 3.12 | Best quant/ML ecosystem; asyncio native; py_vollib, pandas, scipy |
| FastAPI | Async; auto OpenAPI docs; Pydantic; WebSocket support |
| Pydantic v2 | Fast validation; shared schemas for API + internal |
| uvicorn | ASGI server; uvloop for performance |

### AI / LLM

| Technology | Justification |
|-----------|--------------|
| Claude Sonnet 4.6 (Anthropic) | Strategy + Evaluator agents: best structured tool use, financial reasoning |
| Claude Haiku 4.5 (Anthropic) | Risk Assessment: reliable structured output, cheap |
| Llama 3.3 70B (Groq free API) | Research + Monitor: news synthesis, simple checks — free tier sufficient |
| Ollama (local Mac Mini) | Fallback for all agents during outages; 0 cost |
| pgvector | Vector similarity in existing PostgreSQL; avoids separate vector DB |
| py_vollib | Black-Scholes Greeks; Python-native; well-tested |
| scikit-learn + XGBoost | Signal feature scoring; interpretable; no GPU needed |

### Data Storage

| Technology | Justification |
|-----------|--------------|
| PostgreSQL 16 + TimescaleDB | Single DB for relational + time-series; joint queries trivial; chunk compression 90x; handles personal-scale backtesting |
| Redis 7 | Cache + pub/sub (replaces Kafka) + Celery broker + distributed locks; all in one |

### Frontend

| Technology | Justification |
|-----------|--------------|
| Next.js 15 (App Router) | SSR; file-based routing; deploys free to Vercel |
| TailwindCSS + shadcn/ui | Rapid consistent UI |
| TradingView Lightweight Charts | Free; purpose-built financial charts |
| TanStack Query | Server state + background refetch |
| Zustand | Minimal global state for WebSocket data |

### Infrastructure

| Technology | Justification |
|-----------|--------------|
| Mac Mini (Apple Silicon) | Already owned; runs all services + Ollama 70B efficiently |
| Docker Compose | Single command startup; no K8s complexity |
| nginx | SSL termination + reverse proxy; free |
| Cloudflare Tunnel | Remote access without port forwarding; free; TLS automatic |
| Vercel | Next.js hosting; free tier; global CDN |
| Let's Encrypt | Free TLS via Certbot |

### Background Processing

| Technology | Justification |
|-----------|--------------|
| Celery + Redis | Mature; beat scheduler; retry with backoff; multiple priority queues |
| APScheduler | In-process market-hours-aware scheduling; IST timezone |
| tenacity | Circuit breaker + retry for Kite, Groq, Anthropic APIs |

---

## Architecture Decision Records

### ADR-001: True Monolith (No Microservices)

**Status:** Accepted
**Decision:** Single FastAPI process. Modules are Python packages, not services.
**Reason:** Personal app, one user, one Mac Mini. Microservices = overhead with zero benefit. Direct function calls are faster, simpler, easier to debug.

### ADR-002: Redis Pub/Sub over Kafka

**Status:** Accepted
**Decision:** Redis pub/sub for all internal events.
**Reason:** Kafka requires 3 brokers minimum for durability, costs $460/month on MSK. Personal-scale event volume (tens/day, not millions) fits Redis trivially. No replay needed — DB is source of truth, events are triggers only.

### ADR-003: TimescaleDB over ClickHouse

**Status:** Accepted
**Decision:** TimescaleDB handles all time-series including backtesting.
**Reason:** Personal watchlist = ~2.8M OHLCV rows/year. TimescaleDB with chunk compression = ~30MB/year. ClickHouse unnecessary. Eliminates separate EC2 instance ($121/month saved).

### ADR-004: LLM Model Split (Claude + Groq + Ollama)

**Status:** Accepted
**Decision:** Claude Sonnet for strategy + evaluation (quality-critical), Claude Haiku for risk (reliability needed), Groq free for research + monitor, Ollama as universal fallback.
**Reason:** Claude quality is genuinely better for multi-leg options strategy reasoning. But research synthesis and position monitoring don't need it. Split optimizes cost (~Rs500/month) while keeping quality where it matters.

### ADR-005: Mac Mini over Cloud VPS

**Status:** Accepted
**Decision:** Run all infrastructure on owned Mac Mini.
**Reason:** Already owned = $0 compute. Apple Silicon runs Ollama 70B at ~35 tok/s via Metal. 5ms latency to Kite WebSocket (vs 150ms from Hetzner, 80ms from AWS Mumbai). Electricity ~Rs200/month vs Rs1,700-6,500/month VPS.

### ADR-006: Read-Only Broker Integration (No Live Trading)

**Status:** Firm Constraint
**Decision:** Kite Connect for market data only. No order placement.
**Reason:** SEBI algo-trading registration required for automated orders. Platform is research + paper trading only.

---

## Monthly Cost Summary

| Item | Cost |
|------|------|
| Mac Mini compute | Rs0 (owned) |
| PostgreSQL + Redis + nginx (Docker) | Rs0 |
| Ollama LLM (local) | Rs0 |
| Groq API (Llama 3.3 70B) | Rs0 (free tier) |
| Claude Sonnet 4.6 (strategy + eval) | ~Rs460 |
| Claude Haiku 4.5 (risk assessment) | ~Rs55 |
| Kite Connect live data | Rs2,000 |
| Cloudflare Tunnel | Rs0 |
| Vercel (Next.js) | Rs0 |
| Backblaze B2 backup | ~Rs100 |
| Electricity (Mac Mini ~20W avg) | ~Rs200 |
| Domain | ~Rs85 |
| **Total** | **~Rs2,900/month (~$35)** |

---

## Appendix: Indian Market Specifics

### NSE F&O Scope

- **Index options:** Nifty 50, Bank Nifty, Nifty Financial Services, Midcap Select
- **Stock options:** ~200 NSE-listed F&O securities (research subset: 20-30 on watchlist)
- **Weekly expiry:** Thursday (index options)
- **Monthly expiry:** Last Thursday of month
- **Lot sizes:** Nifty = 50, Bank Nifty = 15 (stored in `constants.py`)
- **Strike intervals:** Index Rs50/Rs100; Stock 2.5-5% of price
- **Market hours:** 09:15-15:30 IST, Mon-Fri, NSE holidays excluded

### Regulatory Constraints

| Rule | Enforcement |
|------|-------------|
| No live order placement | Paper Trader only; Kite API read-only |
| SEBI F&O position limits | Risk Manager Layer 1 check |
| No after-hours trading simulation | Market-hours scheduler blocks paper trades outside 09:15-15:30 |
| STT + transaction costs | Modeled in backtester broker simulation |

### NSE Holiday Calendar

- NSE publishes annual CSV
- `scripts/market_calendar.py` syncs to `market_holidays` DB table
- All schedulers call `calendar.market_open()` before running market-hours jobs
