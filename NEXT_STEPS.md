# Next Steps — MarketPilot AI

## Khalid-only actions (exact)
1. **Demo backend (optional, free):** Render.com → sign up free → New → Web Service →
   connect `khalidhasan11/marketpilot-ai` → Deploy (render.yaml is auto-detected).
   Then paste the Render URL into dashboard Settings → API base. Note: free service
   sleeps when idle and its SQLite resets on redeploy — demo-grade only.
2. **Free data keys (optional):** create free TwelveData and/or Finnhub accounts,
   put keys in a local `.env` (never in chat/GitHub) to unlock forex/stocks status
   from `requires_api_key` → configured.

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
