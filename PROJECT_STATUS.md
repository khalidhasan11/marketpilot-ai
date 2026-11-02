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

## TradingView addendum (Nov 2 2026, late) — done & verified
- [x] Licensing research from official sources → `docs/TRADINGVIEW_INTEGRATION.md`
      (Lightweight Charts Apache-2.0 SELECTED; widgets free/display-only with attribution;
      Advanced Charts BLOCKED — approval-gated + prohibited in public repos; TV has no
      data API and nothing is scraped).
- [x] Primary chart = Lightweight Charts **5.2.1** (pinned unpkg, verified 200) fed by
      `frontend/tv-datafeed.js` (Binance-only, Datafeed-API-shaped: onReady/searchSymbols/
      resolveSymbol/getBars/subscribeBars/unsubscribeBars; 5s/15s/30s aggregated from real
      1s klines; live via Binance kline WebSocket). Candles + volume, EMA 20/50, BUY/SELL/
      TP/SL markers from the independent EMA-cross+RSI logic, entry/SL/TP price lines.
      Canvas chart kept as automatic fallback if the CDN fails.
- [x] Asset Comparison view (normalised-% lines, own data) + watchlist sparklines (LWC, own data).
- [x] Display-only TV widgets, fenced + labelled + attribution intact: Ticker Tape (Overview),
      Crypto Heatmap (Rankings), Economic Calendar (Calendar — real events shown by TV;
      own types-only list remains as fallback). No JS reads widget output.
- [x] Backend webhook `POST /api/v1/webhooks/tradingview`: secret (constant-time; 503 when
      unconfigured), ±5 min timestamp window, dedupe by event_id/payload hash, 30/min/IP rate
      limit, symbol mapping, full audit + `tv_webhook_events`/`signal_confirmations`
      (confirmation_only=1). `GET …/events` is auth-protected. Migration `002_tv_webhook.sql`.
- [x] Extension options page: one-line note that TV alerts are confirmation-only (only change).

### Addendum test results (real, executed)
- pytest: **23 passed** (16 previous + 7 new webhook tests: 503 unconfigured, 401 wrong
  secret, 400 stale timestamp, 422 unknown symbol, symbol mapping, accept→dedupe→
  confirmation-only with proof no signal/prediction was created, events require auth).
  A real bug was caught + fixed by these tests (malformed signal_confirmations INSERT).
- Live curl smoke (uvicorn :8023, test secret): health ok; wrong secret 401; stale 400;
  unknown symbol 422; accept → `{"accepted":true,"symbol":"BTCUSDT","confirmation_only":true}`;
  repeat → `{"duplicate":true}`; events listed with auth (401 without).
- Frontend served locally: page contains the pinned LWC CDN, all three widget containers,
  the LWC container + canvas fallback, Compare view; all new JS files return 200 and pass
  `node --check`. Engine independence verified by grep: `prediction.py`, `scanner.py`,
  `backtest.py` contain **zero** TradingView references.
- Honest caveat: TradingView *delivers* webhooks only on paid plans (Essential+, 2FA
  required) — with Khalid's free-only rule the receiver is ready but no real TV alert
  can fire until/unless he ever has a paid TV plan. Not promised as free anywhere.

## Known limitations
- Forex/stocks/indices/metals live data: key-gated (no free real-time source) — UNAVAILABLE, not faked.
- Backend not on a public host yet (blocked step documented). Frontend runs standalone meanwhile.
- Password reset by email: not implemented (no mail provider) — documented in SECURITY.md.
- WebSocket proxies Binance by 5s polling; true upstream WS streaming is a drop-in upgrade.
- Prediction probability is score-mapped, NOT calibrated — labelled as such everywhere.

## 1-Second Live Mode (Nov 3 2026) — done & verified
- [x] `frontend/live1s.js`: Binance **aggTrade WebSocket** for the selected symbol folds
      real trades into the FORMING candle only (close = last trade, high/low expand,
      volume = seeded bar volume + real traded quantities received). Chart repaints
      throttled to 4/sec, header price to 1/sec with green/red flash. Nothing is
      interpolated or smoothed.
- [x] Header/toolbar: "Live 1s" toggle (ON by default, persisted), `● LIVE 1s`
      indicator, live price, and a candle-close countdown (UTC-aligned; 0.1s
      resolution on the 1s timeframe). Note beside it: "Signals use closed candles only."
- [x] Seconds timeframes (1s/5s/15s/30s): forming bar is built from the trade stream
      with the same bucket aggregation as the REST path (pure core shared/tested).
- [x] Resilience: no WS message within 5 s → automatic 1-second REST polling fallback
      (indicator shows "● LIVE 1s (polling)"); WS wins again if it later delivers;
      one reconnect attempt on socket error/close before falling back. Symbol/TF
      switches resubscribe cleanly; toggle-off closes the socket and restores the
      previous kline/poll behaviour (tv-chart.js defers its kline subscription to
      Live 1s while it is ON; single shared callback `MPHandleLiveBar` feeds both
      the Lightweight Charts series and the canvas fallback).
- [x] Prediction integrity unchanged: live ticks repaint only the forming bar;
      signals/markers still compute on closed candles only (no repaint).

### Live-mode test results (real, executed)
- `node tests/live1s.test.js`: **8 passed** — timeframe mapping, UTC bucket alignment,
  first-trade bar creation, in-bucket high/low/close/volume accumulation, bucket
  rollover (closed bar preserved, new bar opens at the trade price), multi-bucket
  gap handling, late-trade rejection, 1s rollover.
- `node --check` passes for all frontend JS. Frontend served locally: 200, all live
  elements present (`live1sToggle`, `liveInd`, `livePrice`, `liveCountdown`).
- REST fallback endpoints verified live from this VM (ticker/price + 1s klines 200).
- **Honest caveat:** WebSocket delivery could NOT be observed from this VM's network —
  a probe of both `stream.binance.com` and `data-stream.binance.vision` aggTrade
  streams received **0 messages in 6 s** (the known silent-WS behaviour on this
  network). The polling fallback therefore is the active path here and was verified
  in code, unit tests, and live REST responses; on networks where WS delivers
  (typical home/mobile), the trade stream takes over automatically.
