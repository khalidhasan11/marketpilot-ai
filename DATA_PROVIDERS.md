# Data Providers — research summary (verified Nov 2026 build)

## Working now (free, no key)
- **Binance public REST** (`data-api.binance.vision`): spot tickers, klines (1s–1M),
  depth, trades. CORS-open, generous public rate limits (weight-based, 6000/min IP).
  Genuinely real-time for crypto spot. Chosen as the primary provider.
- **RSS news**: CoinDesk, CoinTelegraph, Decrypt, Bitcoin Magazine, Google News RSS —
  free, permitted RSS use; dedupe + weighting applied in the news engine.
- **Fear & Greed** (alternative.me) was used by the prototype; MarketPilot's context
  score uses 24h change + news instead, to reduce external dependencies.

## Key-gated (free tier exists; adapter stubbed, returns NO data until configured)
- **Twelve Data** — forex/stocks/indices/metals; free tier is limited credits/day and
  mostly delayed/EOD for many instruments — **not** assumed real-time.
- **Finnhub** — stocks/forex; free tier rate-limited, websocket limited.
- **Alpaca** — US stocks; free data is IEX-only (partial volume), paper trading free.
Set keys in `.env` (see `.env.example`) to enable; the provider layer reports
`requires_api_key` until then. Nothing is simulated in their place.

## Not available honestly
- **Quotex OTC**: no official API, broker-made prices → module is data-limited/unsupported.
- **True real-time forex/stocks on $0**: no free provider offers full real-time
  licensed feeds; the UI labels such markets UNAVAILABLE rather than faking "live".

## Data-quality handling
Stale-feed detection (candle-age checks), spread gate (>50bps blocks predictions),
candle-gap counting in Market Quality Score, duplicate-news dedupe by content hash,
timestamp normalisation to UTC epoch ms throughout.
