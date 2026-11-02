# MarketPilot AI

AI-powered live market intelligence, multi-asset analysis & trading-signal platform.
**Live dashboard:** https://khalidhasan11.github.io/marketpilot-ai/
**Backend API docs (when running):** `http://localhost:8000/docs` (FastAPI OpenAPI)

> ⚠️ **Honesty is the product.** Every prediction is labelled **UNVALIDATED** — there is
> no out-of-sample proof of an edge. The predecessor prototype's honest backtest found
> BTC 5-minute win rate **51.74%**, *below* the 54.05% break-even for an 85%-payout
> binary — i.e. **no proven edge**. MarketPilot never fabricates prices, news, signals,
> or accuracy. When evidence is insufficient, the answer is **NO TRADE**. Educational
> tool — not financial advice, never a profit guarantee.

## What works today (verified)
- **Live crypto data** from the Binance public API (no key): prices, OHLCV candles,
  order-book depth/spread, recent trades — labelled LIVE everywhere.
- **Timeframes** 1s–1w; 5s/15s/30s are aggregated **only** from real 1s klines;
  unsupported resolutions are disabled with a reason.
- **Technical engine** (pure Python, unit-tested, closed candles only): EMA 9/20/21/50/100/200,
  SMA, RSI, MACD, Bollinger, ATR, VWAP, ADX, Stochastic RSI, support/resistance,
  HH/HL/LH/LL structure, breakout detection.
- **News intelligence**: real RSS (CoinDesk, CoinTelegraph, Decrypt, Bitcoin Magazine,
  Google News) with hash dedupe, source-reliability weights, keyword sentiment,
  freshness decay (3h half-life), asset mapping, and a danger-event veto.
- **Scanner**: Market Quality Score + Opportunity Score → tiers P1/P2/P3/WATCHLIST/AVOID.
- **Ensemble prediction** (Models A–E transparent scorers + Model F logistic-regression ML):
  structured output with entry zone, ATR/swing stop-loss, take-profits, R:R, regime,
  reasoning, invalidation conditions, expiry. Gates: data quality, spread > 50bps,
  danger-news veto, |score| < 25 → NO TRADE.
- **Backtester**: EMA 5/13-cross + RSI replay on real candles, next-open entry
  (no look-ahead), 0.1% fees, slippage, walk-forward; reports win rate, profit factor,
  expectancy, max drawdown, Sharpe, Brier — including when the result is losing.
- **Paper trading**: virtual $10,000 account, orders/positions, fees+slippage, PnL — persisted
  (backend SQLite) and mirrored in the web UI via localStorage. No real money, ever.
- **Auth**: register/login, PBKDF2-HMAC-SHA256 password hashing, bearer-token sessions,
  protected routes, basic rate limiting, audit log.
- **Chrome Extension (MV3)**: live prices + top scores, options, notifications. No keys inside.
- **Quotex module**: **DATA-LIMITED / UNSUPPORTED for OTC** — see below.

## Documented deviations from the original spec (with reasons)
1. **Repo is PUBLIC, not private** — GitHub Pages free tier requires a public repo, and
   no secrets exist in code (secrets live only in a gitignored `.env`).
2. **Frontend is a static app, not Next.js** — static deploys free on GitHub Pages and
   keeps working (direct Binance mode) even with the backend offline. It uses the
   backend API when `API_BASE` is configured in Settings.
3. **SQLite by default, not Postgres/TimescaleDB** — zero-cost and runs anywhere;
   the schema is Postgres-compatible in design (see `backend/migrations/001_init.sql`).
   Redis is optional, not required.
4. **Forex / stocks / indices / real metals are key-gated, not faked** — TwelveData,
   Finnhub and Alpaca adapters exist as config-gated providers that report
   `requires_api_key` and return **no data** until Khalid adds a free-tier key.
   PAXGUSDT (tokenised gold on Binance) is included as a labelled commodity *proxy*.

## Quotex
No official Quotex API exists; OTC prices are broker-generated and differ from exchange
prices. MarketPilot does **not** scrape, bypass logins/CAPTCHAs, or reverse-engineer
private APIs, and issues **no signals for Quotex OTC**. The Quotex page offers a
manual-observation log so the displayed-vs-exchange gap can be measured honestly.

## Quick start
```bash
# Backend
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
.venv/bin/uvicorn backend.app.main:app --port 8000   # http://localhost:8000/docs
# Tests
.venv/bin/python -m pytest backend/tests/ -q
# Frontend: open frontend/index.html or serve it
python3 -m http.server 8080 --directory frontend
# Extension: chrome://extensions → Developer mode → Load unpacked → extension/
```

## Docs
ARCHITECTURE.md · API_DOCUMENTATION.md · DEPLOYMENT.md · DEVELOPMENT.md ·
DATA_PROVIDERS.md · MODEL_VALIDATION.md · CONTRIBUTING.md · SECURITY.md ·
PROJECT_STATUS.md · NEXT_STEPS.md
