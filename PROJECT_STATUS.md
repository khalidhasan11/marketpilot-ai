# Project Status — MarketPilot AI (as of build night, Nov 2 2026)

## Done & verified
- [x] Phase 1: architecture, repo scaffold, docs suite
- [x] Phase 2: FastAPI backend + SQLite schema (full spec table set) + auth (PBKDF2, sessions)
- [x] Phase 3: Binance live provider (ticker/klines/depth/trades), 1s→5s/15s/30s aggregation, provider abstraction + key-gated stubs
- [x] Phase 4: scanner (Quality + Opportunity + tiers), watchlists (API)
- [x] Phase 5: technical engine (all listed indicators, structure, breakouts) — unit-tested
- [x] Phase 6: RSS news engine (dedupe/sentiment/decay/danger veto); economic calendar = reference types only
- [x] Phase 7: ensemble A–F prediction with gates; confidence hard-set UNVALIDATED
- [x] Phase 8: risk engine (ATR levels, sizing, guards); signal store (append-only history)
- [x] Phase 9: backtester (no-look-ahead, fees/slippage, walk-forward) + paper trading
- [x] Phase 10: Chrome Extension MV3 (popup/options/service worker)
- [x] Phase 11: tests + security review (SECURITY.md)
- [x] Phase 12 (frontend): GitHub Pages deploy via Actions. Backend deploy: prepared
      (Dockerfile, render.yaml) but BLOCKED — needs Khalid's own free Render account action
      (see DEPLOYMENT.md). Not claimed as deployed.

## Test results (real, executed)
- pytest: **16 passed** in 4.19s (`backend/tests/test_all.py`): SMA/EMA/RSI/ATR known values,
  aggregation integrity, position sizing, ATR levels, loss guards, password hashing,
  news dedupe + sentiment, NO-TRADE gate, prediction schema, backtest no-look-ahead.
- JS: `node --check` passes for frontend/app.js and all extension scripts; manifest JSON valid.
- Frontend served locally: HTTP 200, contains "MarketPilot", all key element IDs present.

## Live smoke test (real Binance data, local uvicorn :8011)
- GET /health → status ok, DB ok, binance ok, 3 providers `requires_api_key`
- GET /api/v1/prices/BTCUSDT → real live price returned with bid/ask, label LIVE
- GET /api/v1/candles/BTCUSDT?interval=5m → 5 real candles
- GET /api/v1/predictions/BTCUSDT → BEARISH, fused −52.8 (A −44 B −70 C −50 D −35 E −93 F −19),
  SL/TP from ATR+swing, confidence UNVALIDATED, signal persisted (signal_id 1)
- GET /api/v1/scanner → BTC/ETH/BNB ranked with quality 85, tiers assigned
- POST /api/v1/backtest/BTCUSDT (500×5m) → **5 trades, win rate 20.0%, profit factor 0.342,
  expectancy −$89.03, net −$445.17, max DD 6.76%, Sharpe −1.232, Brier 0.2825** — losing, reported as-is
- Auth: register → user_id 1; login → bearer token issued

## Known limitations
- Forex/stocks/indices/metals live data: key-gated (no free real-time source) — UNAVAILABLE, not faked.
- Backend not on a public host yet (blocked step documented). Frontend runs standalone meanwhile.
- Password reset by email: not implemented (no mail provider) — documented in SECURITY.md.
- WebSocket proxies Binance by 5s polling; true upstream WS streaming is a drop-in upgrade.
- Prediction probability is score-mapped, NOT calibrated — labelled as such everywhere.
