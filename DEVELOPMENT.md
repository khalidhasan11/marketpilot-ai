# Development — MarketPilot AI

## Setup
```bash
git clone https://github.com/khalidhasan11/marketpilot-ai && cd marketpilot-ai
python3 -m venv .venv && .venv/bin/pip install -r backend/requirements.txt
cp .env.example .env   # optional keys only; Binance needs none
```

## Run
```bash
.venv/bin/uvicorn backend.app.main:app --port 8000 --reload   # API + /docs
python3 -m http.server 8080 --directory frontend              # dashboard
.venv/bin/python -m pytest backend/tests/ -q                  # tests (16)
node --check frontend/app.js                                  # frontend syntax
```

## Layout
- `backend/app/` — providers, indicators, news_engine, scanner, prediction, risk, backtest, paper, db, main
- `backend/migrations/001_init.sql` — schema notes (runtime DDL in `db.py`)
- `backend/tests/test_all.py` — indicator known-values, aggregation, risk, auth hashing, news, NO-TRADE gate, backtest no-look-ahead
- `frontend/` — static terminal (index.html, app.js, style.css)
- `extension/` — MV3 (manifest, popup, options, service worker)

## Rules for contributors
- Never add simulated/fake market data paths. Key-gated providers return status, not data.
- Indicators must be no-look-ahead and unit-tested with known values.
- Any accuracy number must come from recorded out-of-sample outcomes (see MODEL_VALIDATION.md).
- Secrets only via `.env`; `.env.example` lists names only.
