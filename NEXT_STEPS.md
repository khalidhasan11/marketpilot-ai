# Next Steps — MarketPilot AI

## Khalid-only actions (exact)
1. **Demo backend (optional, free):** Render.com → sign up free → New → Web Service →
   connect `khalidhasan11/marketpilot-ai` → Deploy (render.yaml is auto-detected).
   Then paste the Render URL into dashboard Settings → API base. Note: free service
   sleeps when idle and its SQLite resets on redeploy — demo-grade only.
2. **Free data keys (optional):** create free TwelveData and/or Finnhub accounts,
   put keys in a local `.env` (never in chat/GitHub) to unlock forex/stocks status
   from `requires_api_key` → configured.

## TradingView follow-ups (from the Nov 2 addendum)
- **Advanced Charts**: only if Khalid (a) applies on TradingView's Advanced Charts
  landing page and is approved, AND (b) moves the frontend to private hosting (the
  licence prohibits public repos). The Binance datafeed already mirrors the Datafeed
  API contract for that swap. Until both happen: BLOCKED, do not download it.
- **Real webhook alerts**: require a paid TradingView plan (Essential+) + 2FA — against
  the current free-only rule. The receiver endpoint is deployed-ready; nothing to build.
- Economic-calendar widget now shows real events (display-only, by TradingView);
  backlog item 5 below is therefore optional, not a gap.

## Engineering backlog (in priority order)
1. Forward paper-trading log: run the backend daily, let predictions accumulate
   outcomes for 4+ weeks, then produce the first honest calibration report.
2. Binance WebSocket upstream for /ws (replace 5s polling) + frontend WS client.
3. TwelveData/Finnhub live adapters once keys exist (with delayed-data labelling).
4. Signal lifecycle auto-updater: expire signals, evaluate outcomes vs SL/TP on new candles.
5. Economic calendar from a verifiable free source (official release RSS) — only when dates can be sourced, never hand-typed.
6. Postgres/TimescaleDB profile if a VPS is ever approved (docker-compose `prod` profile stubs exist).

## Explicitly NOT planned
- Real-money / auto trading. Quotex scraping or automation. Paid data or hosting
  without Khalid's explicit approval from future earnings.

## Done since (Nov 3 2026)
- 1-Second Live Mode shipped (aggTrade trade stream + 1s REST polling fallback,
  countdown, price flash, Live 1s toggle). Note: this VM's network silently drops
  Binance WS, so the polling path is what runs here; WS auto-takes-over where it
  delivers. Backlog item 2 (frontend WS client) is therefore partially done —
  the backend /ws proxy upgrade remains open.
