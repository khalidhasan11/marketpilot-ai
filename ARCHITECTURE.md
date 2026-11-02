# Architecture — MarketPilot AI

## Overview
Modular monolith (deliberately not microservices): one FastAPI backend, one static
frontend, one MV3 extension. The frontend works standalone (direct Binance public API)
and upgrades to backend mode when `API_BASE` is configured.

```
Browser ──► GitHub Pages (frontend/) ──► Binance public REST (direct mode)
   │                └──────────────────► FastAPI backend (/api/v1, /ws) ──► Binance REST
Extension ──► Binance public REST                 ├──► RSS feeds (news engine)
                                                  ├──► SQLite (persistence)
                                                  └──► key-gated providers (TwelveData/Finnhub/Alpaca)
```

## Backend modules (`backend/app/`)
- `providers.py` — provider abstraction: `BinanceProvider` (working) + `KeyGatedProvider`
  stubs that report status and never return fake data. `ASSETS` registry, timeframe support matrix.
- `indicators.py` — pure-Python indicators; index-aligned outputs; no look-ahead.
- `news_engine.py` — RSS ingestion, sha256 dedupe, sentiment, freshness decay, danger veto.
- `scanner.py` — Market Quality Score, Opportunity Score, tier assignment.
- `prediction.py` — ensemble A–F + fusion gates → structured prediction schema.
- `risk.py` — ATR/swing levels, position sizing, consecutive-loss & drawdown guards.
- `backtest.py` — replay engine + chronological walk-forward.
- `paper.py` — paper accounts/orders/positions (virtual only).
- `db.py` — sqlite3 persistence; full table set from the spec; PBKDF2 hashing; audit log.
- `main.py` — versioned REST API + `/ws/prices/{symbol}` WebSocket (5s poll proxy of
  Binance REST; a true Binance WS upstream is a drop-in upgrade), CORS, rate limiting.

## TradingView layer (display only — see docs/TRADINGVIEW_INTEGRATION.md)
- **Primary chart**: TradingView Lightweight Charts 5.2.1 (Apache-2.0, pinned CDN) in
  `frontend/tv-chart.js`, fed by `frontend/tv-datafeed.js` — a Binance-only datafeed
  shaped after the TradingView Datafeed API (`onReady/searchSymbols/resolveSymbol/
  getBars/subscribeBars/unsubscribeBars`) so an Advanced Charts swap stays possible
  if approval + private hosting ever exist. Advanced Charts itself is BLOCKED:
  approval-gated and prohibited in public repositories.
- **Widgets**: official TV embeds (ticker tape, crypto heatmap, economic calendar)
  via `frontend/tv-widgets.js`, each in a labelled display-only fence with TV
  attribution intact. No code reads widget DOM or values.
- **Alerts**: `backend/app/tv_webhook.py` + endpoints in `main.py`. Accepted alerts
  land in `tv_webhook_events` / `signal_confirmations` (confirmation_only=1) +
  notifications. **The prediction/scanner/backtest modules contain no TradingView
  reference at all** — the engine runs identically with every TV component removed,
  and the frontend falls back to its built-in canvas chart if the LWC CDN fails.

## Data integrity rules
- Signals/predictions are append-only; history is never rewritten. Status changes go
  through `signal_updates`; outcomes through `signal_outcomes`.
- Every payload carries `data_label` (LIVE / REFERENCE / UNAVAILABLE) and timestamps.
- Second-level timeframes are built only from real 1s klines; insufficient resolution
  disables prediction for that timeframe with an explicit reason.

## Deviations (also in README)
Public repo (Pages free tier), static frontend instead of Next.js (free hosting +
offline resilience), SQLite default instead of Postgres (zero cost; schema is
Postgres-compatible), Redis optional. Each deviation trades spec-literal compliance
for the binding constraints: **$0 cost and honest data**.
