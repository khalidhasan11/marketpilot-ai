# API Documentation — MarketPilot AI

Base: `/api/v1` · Interactive OpenAPI: `GET /docs` (FastAPI) · Health: `GET /health`

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | /health | – | status, DB, model version, provider statuses |
| GET | /api/v1/providers/status | – | all providers + Quotex unsupported notice |
| GET | /api/v1/assets | – | supported asset registry |
| GET | /api/v1/prices/{symbol} | – | live 24h ticker (Binance) |
| GET | /api/v1/candles/{symbol}?interval=&limit= | – | OHLCV; 5s/15s/30s aggregated from real 1s |
| GET | /api/v1/depth/{symbol} | – | order book + spread (bps) |
| GET | /api/v1/analysis/{symbol}?interval= | – | full indicator set, closed candles |
| GET | /api/v1/scanner?interval=&limit_symbols= | – | rankings with quality/opportunity/tier |
| GET | /api/v1/news?symbol= | – | RSS news, sentiment, danger flag |
| GET | /api/v1/predictions/{symbol}?interval= | – | ensemble prediction (structured schema); persisted; creates a signal unless NO TRADE |
| GET | /api/v1/signals | – | immutable signal history |
| POST | /api/v1/backtest/{symbol}?interval=&limit=&walk= | – | backtest or walk-forward on real candles |
| POST | /api/v1/auth/register | – | {email, password ≥ 8} |
| POST | /api/v1/auth/login | – | returns bearer token (7 days) |
| GET/POST | /api/v1/watchlists, /api/v1/watchlists/items | Bearer | per-user watchlist |
| GET | /api/v1/notifications | Bearer | user notifications |
| GET | /api/v1/paper/account | Bearer | paper portfolio |
| POST | /api/v1/paper/orders | Bearer | virtual order (fees+slippage) |
| POST | /api/v1/paper/close/{id}?price= | Bearer | close paper position |
| POST | /api/v1/risk/position-size | – | sizing from balance/risk%/entry/SL |
| GET | /api/v1/risk/guards | Bearer | consecutive-loss & drawdown guards |
| GET | /api/v1/performance | – | recorded counts; accuracy null until validated |
| GET | /api/v1/economic-calendar | – | event TYPES reference (no invented dates) |
| GET | /api/v1/quotex | – | data-limited explanation |
| WS | /ws/prices/{symbol} | – | live tick stream (5s cadence) |
| POST | /api/v1/webhooks/tradingview | Shared secret | TradingView alert receiver — confirmation ONLY (see below) |
| GET | /api/v1/webhooks/tradingview/events | Bearer | recent webhook events + confirmations |

### TradingView webhook (confirmation only — never a decision input)
Payload (JSON): `{"secret": "…", "event_id": "optional", "symbol": "BINANCE:BTCUSDT",
"action": "alert name / action", "price": 65000, "timestamp": 1793642239}` —
`timestamp` may be epoch seconds, epoch ms, or ISO-8601; the secret may also be sent
as header `X-Webhook-Secret`. Behaviour:
- `TRADINGVIEW_WEBHOOK_SECRET` unset on the server → **503** (endpoint refuses all traffic).
- Wrong secret → **401** (constant-time compare; attempt logged, secret never logged).
- Timestamp missing/unparseable → **400**; skew > ±5 min → **400**.
- Same `event_id` (or same symbol+action+timestamp+price hash) twice → **200
  `{"duplicate": true}`**, processed once.
- Symbol normalised (`BINANCE:BTCUSDT` / `BTC/USDT` / `BTCUSDT` → `BTCUSDT`);
  unknown symbol → **422**, logged.
- Rate limit: 30 requests/min per IP → **429**.
- Accepted alerts are stored in `tv_webhook_events` + `signal_confirmations`
  (`source='tradingview_alert', confirmation_only=1`) and as a notification.
  **They never create, modify, or validate any prediction or trading signal** —
  decisions are computed solely from Binance data + RSS news.
- **Setup reality check:** create the alert in TradingView with the webhook URL
  `https://<your-backend>/api/v1/webhooks/tradingview` and the JSON above as the
  alert message. TradingView delivers webhooks **only on paid plans (Essential+)
  with 2FA enabled** — on the free Basic plan the alert will never fire. This is a
  TradingView limitation, stated openly; the receiver itself is free and tested.

Prediction schema: exactly the spec's structure — asset, market, timeframe, direction
(BUY/SELL family: BULLISH/BEARISH/NEUTRAL/NO TRADE), probability (score-mapped,
uncalibrated), confidence_level (always UNVALIDATED until out-of-sample calibration),
entry_zone, stop_loss, take_profit[], risk_reward, market_regime, data_quality,
news_risk, model_version, reasoning[], invalidation_conditions[], generated_at, expires_at.
