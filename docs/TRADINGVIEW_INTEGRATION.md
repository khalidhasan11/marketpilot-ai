# TradingView Integration — Architecture & Licensing Basis

*Verified against official TradingView sources on 2026-11-02. This document records
which TradingView technology MarketPilot AI uses, why, and what it must never do.*

## The one rule that governs everything

**TradingView is a display layer only.** MarketPilot AI's prediction engine reads
**only** authorised numerical data it fetches itself — the Binance public API
(prices, OHLCV, depth, trades) and RSS news feeds. No TradingView widget, chart,
indicator summary, "technical rating", or alert is ever an input to a model, a
score, or a BUY/SELL/NO TRADE decision. TradingView's own FAQ states it plainly:
*"We don't have an API that gives access to data"* and widgets *"come with built-in
data provided by TradingView"* for display — there is no licensed machine-readable
TradingView data feed to consume, and scraping one together would violate their
terms. If every TradingView component on the page vanished, the AI engine would
produce byte-identical predictions.

## Options compared

| Option | What it is | Licence / access | Data | Verdict |
|---|---|---|---|---|
| **Lightweight Charts™** | TradingView's open-source HTML5 chart library | **Apache-2.0**, free incl. commercial use; attribution required | **Yours** — you feed it your own bars | ✅ **SELECTED — primary chart** |
| **TradingView Widgets** | Hosted embeddable components (Ticker Tape, Heatmap, Economic Calendar…) | Free embed, **TradingView branding/attribution must stay**; no application needed | **TradingView's** — display only, cannot accept custom feeds | ✅ Display-only extras, fenced & labelled |
| **Advanced Charts / Charting Library** | Full self-hosted TradingView charting engine | **Application + TradingView approval**; private GitHub repo; **"The library is not redistributable. It is prohibited to use any part of the library in public repositories."** | Yours, via Datafeed API / UDF adapter | ⛔ **BLOCKED** — see below |
| TradingView website / private APIs | tradingview.com internals | Terms of Service | Theirs | ⛔ Never scraped, reverse-engineered, or repurposed — prohibited by the addendum and by TV terms |

### Selected: Lightweight Charts 5.2.1 (pinned)
- Source: https://github.com/tradingview/lightweight-charts — repository licence is
  Apache License 2.0 (verified on the repo page and its `LICENSE` file:
  https://github.com/tradingview/lightweight-charts/blob/master/LICENSE).
- The library's README adds an attribution condition: *"This license requires
  specifying TradingView as the product creator. You shall add the 'attribution
  notice' from the NOTICE file and a link to https://www.tradingview.com/ …"* —
  MarketPilot keeps the chart's `attributionLogo` enabled (default) **and** shows a
  text attribution link under the chart.
- Loaded from a pinned CDN (verified HTTP 200 on 2026-11-02):
  `https://unpkg.com/lightweight-charts@5.2.1/dist/lightweight-charts.standalone.production.js`
  Pinning matters: v5 changed the API (`addSeries(CandlestickSeries)`,
  `createSeriesMarkers`) versus v4, so the version is locked, never `@latest`.
- Because the library renders **our** Binance bars, multi-timeframe display, EMA
  overlays, BUY/SELL markers, entry/SL/TP price lines, asset comparison and
  watchlist sparklines are all computed by MarketPilot from its own data — exactly
  the independence the addendum requires.
- **Graceful degradation:** if the CDN is unreachable, the app automatically falls
  back to the pre-existing built-in canvas chart. The product must operate with
  TradingView technology entirely unavailable — and it does.

### Widgets: display-only, fenced
- Sources: https://www.tradingview.com/widget/ and per-widget docs —
  Ticker Tape https://www.tradingview.com/widget-docs/widgets/tickers/ticker-tape/,
  Crypto Heatmap https://www.tradingview.com/widget-docs/widgets/heatmaps/crypto-heatmap/,
  Economic Calendar https://www.tradingview.com/widget-docs/widgets/calendars/economic-calendar/.
  Embed scripts are served from TradingView's official host
  `https://s3.tradingview.com/external-embedding/embed-widget-*.js` (all verified 200).
- TradingView's widget FAQ: widgets are provided **free with default TradingView
  branding**; the attribution must remain as designed. MarketPilot keeps the
  `tradingview-widget-copyright` attribution block intact on every widget.
- Every widget sits in a container labelled
  **"TradingView — display only. Not used by MarketPilot AI predictions."**
  No MarketPilot JavaScript reads widget DOM, iframe content, or widget values —
  there is no code path from a widget to any calculation. The Economic Calendar
  widget displays *real* events (an upgrade over our types-only reference list,
  which remains as fallback), but those events are shown by TradingView itself;
  the in-app news-risk gate still runs exclusively on our own RSS engine.

### BLOCKED: Advanced Charts / Charting Library
- Official "Get started" (https://www.tradingview.com/charting-library-docs/latest/quick-start):
  access requires submitting the request form on the Advanced Charts landing page
  and receiving a GitHub invitation to a **private** repository after approval;
  *"Obtaining the library from third-party services is strictly prohibited"* and
  *"The library is not redistributable. It is prohibited to use any part of the
  library in public repositories."*
- MarketPilot's repository is **public by necessity** (free GitHub Pages), so
  committing the library would breach the licence even if access were granted.
- **Status: BLOCKED on (1) a TradingView access application Khalid has not made,
  and (2) the public-repo redistribution prohibition.** It is not downloaded,
  vendored, mirrored, or approximated here. Our datafeed module
  (`frontend/tv-datafeed.js`) deliberately mirrors the Datafeed API contract
  (`onReady / searchSymbols / resolveSymbol / getBars / subscribeBars /
  unsubscribeBars`) so that *if* Khalid ever obtains approval and moves the
  frontend to private hosting, the chart engine can be swapped without touching
  the data layer or the AI engine.

## Webhook alerts — supplementary confirmation only
- Backend endpoint `POST /api/v1/webhooks/tradingview` (see API_DOCUMENTATION.md).
  Alerts are stored as notifications + `signal_confirmations` rows flagged
  `source='tradingview_alert', confirmation_only=1`. They **never create, modify,
  confirm-into-existence, or delete any prediction or trading signal** — the
  decision engine cannot see them.
- **Honest cost caveat:** TradingView webhook *delivery* is not free. TradingView's
  pricing page lists "Webhook notifications" for the paid Essential/Plus/Premium/
  Ultimate plans and **not** for the free Basic plan, and webhook alerts require
  2-factor authentication on the TradingView account (TradingView Help Center).
  The endpoint is built, tested, and ready — but Khalid cannot receive real
  TradingView webhooks without a paid TradingView plan, which his free-only rule
  excludes. No workaround is offered or attempted.
  Sources: https://www.tradingview.com/pricing/ ·
  https://www.tradingview.com/support/solutions/43000529348-webhooks/

## Data-independence guarantee (testable)
1. Prediction code imports only `providers` (Binance) + `news_engine` (RSS). No
   TradingView URL, payload, or alert appears in `prediction.py`, `scanner.py`,
   or `backtest.py` — grep the repo: `tradingview` occurs only in docs, the
   webhook module (inbound confirmation log), and frontend display code.
2. `signal_confirmations` is write-only from the engine's perspective: nothing
   reads it when scoring.
3. Frontend: scoring functions (`scoreCandles`, `fusion`, `computeSignals`) take
   Binance klines as input; widget containers are write-only DOM embeds.

## What TradingView is used for (final mapping)
- Professional candlestick chart + volume, multi-timeframe — **Lightweight Charts + own Binance datafeed**
- Indicator visualisation (EMA 20/50 overlays) — Lightweight Charts, our calculations
- Chart annotations (BUY/SELL markers, entry/SL/TP lines) — Lightweight Charts, from the independent EMA-cross+RSI logic on Binance data
- Asset comparison — Lightweight Charts normalised-% lines, own data
- Watchlist display — Lightweight Charts sparklines, own data
- Market heatmap — TV Crypto Heatmap widget (display-only, fenced)
- Ticker tape — TV widget (display-only, fenced)
- Economic calendar visualisation — TV Economic Calendar widget (display-only, fenced); own types-only reference remains as fallback
- Alerts — webhook receiver (confirmation-only, paid-TV-plan caveat above)
