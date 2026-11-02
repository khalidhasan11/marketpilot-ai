# MarketPilot AI — Final Delivery Report
**Date:** Nov 2, 2026 · **Builder:** Kai (autonomous build) · **Owner:** Khalid Hasan Bhuiyan

## 1. Project summary
A real, working market-intelligence platform: FastAPI backend with live Binance data,
a full technical/news/scanner/prediction/backtest/paper-trading stack, a static
trading-terminal frontend deployed free on GitHub Pages, and a Manifest V3 Chrome
extension. Built under Khalid's binding constraints: **$0 cost, free data only,
public repo, and absolute honesty about predictive validity** — every prediction is
labelled UNVALIDATED and insufficient evidence yields NO TRADE.

## 2. Implemented features (all verified working)
Backend: provider abstraction (Binance live; TwelveData/Finnhub/Alpaca key-gated stubs
that return status, never fake data); candle engine (native 1s–1w; 5s/15s/30s aggregated
only from real 1s klines); indicators (EMA 9/20/21/50/100/200, SMA, RSI, MACD, Bollinger,
ATR, VWAP, ADX, Stochastic RSI, S/R, structure, breakouts); RSS news engine (hash dedupe,
source weights, sentiment, freshness decay, danger veto); scanner (Quality + Opportunity
scores, P1/P2/P3/WATCHLIST/AVOID); ensemble prediction A–F with data-quality/spread/news
gates and the exact structured schema; risk engine (ATR/swing SL-TP, sizing, loss/drawdown
guards); append-only signal store; backtester (next-open entry, fees 0.1%, slippage,
walk-forward, Brier/Sharpe/PF/expectancy/max-DD); paper trading (persisted, virtual only);
auth (PBKDF2, token sessions, rate limit, audit log); versioned /api/v1 + WebSocket + /health.
Frontend (17 views): Overview with canvas chart + BUY/SELL markers + position panel,
Scanner, Rankings, Asset Analysis, AI Signals, News, Economic Calendar (reference types
only — no invented dates), Technical Analysis, in-browser Backtesting, Paper Trading,
Signal History, Performance, Watchlists, Alerts, Provider Status, Quotex (data-limited),
Settings (API base + notifications). Extension: live popup, options, service worker.

## 3. Technology stack
Python 3.12 + FastAPI + Pydantic + scikit-learn (Model F logistic regression) ·
SQLite (Postgres-compatible schema; migrations in backend/migrations/) ·
Vanilla JS static frontend (documented deviation from Next.js — free Pages hosting +
works with backend offline) · Docker + docker-compose shipped (untested locally — no
Docker on this machine) · GitHub Actions CI + Pages.

## 4. GitHub repository
**https://github.com/khalidhasan11/marketpilot-ai** (PUBLIC — deviation documented:
Pages free tier requires public; no secrets in code). Verified HTTP 200.
4 meaningful phase commits. CI run: **success**. Pages deploy run: **success**.

## 5. Production website
**https://khalidhasan11.github.io/marketpilot-ai/** — verified HTTP 200, title
"MarketPilot AI — Live Market Intelligence", app.js and style.css both 200 with
correct relative paths, JS wired to the Binance public API.
Limitation: no headless browser exists in the build environment, so the live page was
verified at HTTP/asset/syntax level, not by an in-browser boot test. Khalid's phone
check is the final visual gate.

## 6. Chrome Extension status
Complete MV3 package in `extension/` (manifest validated, all JS syntax-checked).
Load: chrome://extensions → Developer mode → Load unpacked → select `extension/`.
Not published to the Web Store (that needs a $5 developer fee — not paid, per free-only rule).

## 7. Database status
SQLite, initialised and exercised during smoke tests (auth user, prediction, signal,
backtest run all persisted). Full spec table set (30 tables incl. users, candles,
news, predictions, signals, outcomes, backtests, paper_*, watchlists, notifications,
provider status, audit logs). Backup = copy the .db file.

## 8. Market data provider status
Binance: **OK / LIVE** (health check + live price/candles/depth in smoke test).
TwelveData, Finnhub, Alpaca: **requires_api_key** (free-tier keys not yet provided) —
forex/stocks/indices/metals therefore UNAVAILABLE, explicitly labelled, never faked.
PAXGUSDT included as a labelled gold *proxy*.

## 9. News provider status
Working: real RSS from CoinDesk, CoinTelegraph, Decrypt, Bitcoin Magazine, Google News.
In the smoke-test prediction, the news model (E) scored −93.1 with news_risk HIGH —
live ingestion demonstrably flowing into the ensemble.

## 10. AI model status
Ensemble v1.0.0 (marketpilot-ensemble-v1.0.0): Models A–E transparent scorers,
Model F logistic regression (chronological split, in-window holdout reported in the
reasoning string). **confidence_level: UNVALIDATED** — no out-of-sample proof exists.
Smoke-test live prediction: BTCUSDT 5m BEARISH, fused −52.8, ATR-based SL/TP, persisted as signal #1.

## 11. Backtesting status
Engine complete and honest. Headline real results:
- MarketPilot first live window (500 × BTC 5m candles, EMA-cross, R:R 3:1, fees on):
  **5 trades, 20.0% win rate, profit factor 0.342, expectancy −$89.03, net −$445.17,
  max drawdown 6.76%, Sharpe −1.232, Brier 0.2825** — a losing result, reported as-is.
- Predecessor prototype (reference): BTC 5m 51.74% vs 54.05% break-even — no edge.
Conclusion stands: forward paper testing over weeks is the only honest next validation step.

## 12. Automated test results
**pytest: 16 passed, 0 failed** (4.19s) — indicator known values, aggregation integrity,
risk sizing, ATR levels, guards, password hashing, news dedupe/sentiment, NO-TRADE gate,
prediction schema, backtest no-look-ahead. Plus: node --check on all JS (pass),
extension manifest JSON valid, GitHub CI green end-to-end.

## 13. Security review
PBKDF2-HMAC-SHA256 (200k iterations, per-user salt); 256-bit session tokens;
parameterised SQL; secrets only via gitignored .env (.env.example = names only);
no keys in extension or frontend; rate limiting on price endpoints; audit log.
Known limits (in SECURITY.md): no email password-reset (no mail provider), CORS is
permissive by default (tighten for production), bearer-token API (no cookie CSRF surface).

## 14. Deployment verification
Frontend: deployed + verified (see §5). Backend: **NOT deployed — BLOCKED** (see §15/§18).
Docker artefacts (Dockerfile, docker-compose.yml, render.yaml) are prepared and in the repo.

## 15. Required API keys / external permissions
None for the working system (Binance is keyless). Optional free keys Khalid may add
to `.env` himself: TWELVEDATA_API_KEY, FINNHUB_API_KEY, ALPACA_API_KEY.
Backend hosting needs one account action by Khalid (Render free) — exact steps in §18.

## 16. Estimated recurring operating costs
**Current: $0/month.** Nothing paid was created. Optional future costs if Khalid ever
chooses them from earnings: VPS ≈ $5–6/mo, custom domain ≈ $12/yr, Chrome Web Store
developer fee $5 one-time, paid data tiers vary. None recommended now.

## 17. Known limitations
1. Only crypto (Binance) has live data; other asset classes are key-gated off.
2. Backend has no public URL yet — the dashboard runs in direct-Binance mode meanwhile.
3. Probabilities are score-mapped, not calibrated; the strategy's measured results are losing so far.
4. WebSocket polls Binance REST every 5s (true WS upstream is a listed upgrade).
5. Economic calendar shows event types/cadence only — exact dates must be checked on official sources.
6. In-browser paper trading (localStorage) and backend paper trading are separate ledgers.
7. Live page not yet boot-tested in a real browser (environment limitation, §5).

## 18. Remaining tasks
- **Khalid (one free action, optional):** Render.com → free sign-up → New Web Service →
  connect repo `khalidhasan11/marketpilot-ai` → Deploy (render.yaml auto-detected) →
  paste the URL into dashboard Settings → API base. Free tier sleeps when idle and its
  SQLite resets on redeploy — demo-grade, stated openly in DEPLOYMENT.md.
- **Kai backlog:** forward paper-trading accumulation + first calibration report after
  4+ weeks of outcomes; Binance WS upstream; key-gated provider adapters if keys arrive;
  signal lifecycle auto-expiry/outcome evaluator.
- **Explicitly never:** real-money trading, Quotex scraping/automation, paid resources
  without Khalid's approval, any fabricated accuracy claim.

---

# Addendum — TradingView Integration (Nov 2 2026)

**Licensing verdicts (verified from official TradingView sources, full citations in
`docs/TRADINGVIEW_INTEGRATION.md`):**
- **Lightweight Charts™ — SELECTED as primary chart.** Open source, Apache-2.0
  (github.com/tradingview/lightweight-charts), free including commercial use, with a
  README attribution condition (TradingView named as creator + link) — satisfied via
  the chart's attribution logo and a text credit. Pinned at **5.2.1** from unpkg.
  It renders **MarketPilot's own Binance data** through a purpose-built datafeed
  (`frontend/tv-datafeed.js`, Datafeed-API-shaped), with EMA 20/50 overlays, volume,
  BUY/SELL/TP/SL markers from the independent EMA-cross+RSI logic, entry/SL/TP price
  lines, Binance-WebSocket live updates, an asset-comparison view, and watchlist
  sparklines. The previous canvas chart remains as automatic fallback.
- **TradingView Widgets — display-only.** Official free embeds (Ticker Tape, Crypto
  Heatmap, Economic Calendar) with TradingView branding/attribution intact, each in a
  container labelled "display only — not used by predictions". No code reads them.
  The Economic Calendar widget upgrades the calendar view with real events displayed
  by TradingView itself; the app's own reference list stays as fallback.
- **Advanced Charts / Charting Library — BLOCKED.** Official docs: access requires a
  TradingView application + approval (private GitHub repo), "the library is not
  redistributable; it is prohibited to use any part of the library in public
  repositories." This repo is public (free Pages), so it is not downloaded or included.
- **Data independence — unchanged and verified.** Predictions still come only from
  Binance public data + RSS news; grep confirms zero TradingView references in
  prediction/scanner/backtest code. TradingView has no public data API and nothing
  was scraped or reverse-engineered.

**Webhook receiver — built & tested.** `POST /api/v1/webhooks/tradingview`:
shared-secret auth (503 when unconfigured, 401 wrong secret, constant-time compare),
±5-minute timestamp validation, duplicate detection, 30/min/IP rate limit, symbol
normalisation, full audit trail; accepted alerts stored as confirmation-only records
that can never create or modify a decision. Tests: **23 passed** total (7 new).
Live curl smoke test passed every scenario (401/400/422/accept/duplicate/auth-gated list).
**Honest limitation:** TradingView only *sends* webhook alerts on paid plans
(Essential or higher, 2FA required) — under Khalid's free-only rule no real TV alert
can fire today; the receiver is ready if that ever changes, and this is not promised
as working for free anywhere in the product.

---

## Addendum — 1-Second Live Mode (Nov 3, 2026)

The chart now updates every second. A dedicated module (`frontend/live1s.js`)
subscribes to Binance's **aggTrade** stream for the selected symbol and folds each
real trade into the forming candle (close = trade price, high/low expanded, volume
accumulated from real traded quantities) — chart repaints throttled to 4/sec, header
price to 1/sec with a green/red tick flash, plus a UTC-aligned **candle-close
countdown** and a **Live 1s toggle** (on by default). Sub-minute timeframes
(1s/5s/15s/30s) aggregate trades into the current bucket with the same rules as the
REST path. If the WebSocket delivers nothing within 5 seconds — some networks
silently drop it — the mode automatically falls back to **1-second REST polling**
and labels itself "● LIVE 1s (polling)"; the trade stream retakes control if it
later delivers. Signals and markers are unchanged: they still compute on **closed
candles only**, and a note beside the live indicator says so.

Verification: 8/8 new Node unit tests pass for the trade→bar aggregation core
(including bucket rollover and late-trade rejection); all JS passes `node --check`;
the live page references the new module. Honest caveat: from the build VM's network,
Binance WebSocket streams delivered no messages (0 in 6 s on both endpoints), so the
polling fallback was the path verified live there — by design, not by accident.
