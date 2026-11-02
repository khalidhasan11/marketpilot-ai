# Deployment — MarketPilot AI

## Frontend — LIVE (free)
GitHub Pages via `.github/workflows/pages.yml` (deploys `frontend/` on push to main).
URL: https://khalidhasan11.github.io/marketpilot-ai/ — verified 200 + "MarketPilot" in HTML.
Works with zero backend (direct Binance mode).

## Backend — prepared, NOT yet deployed (BLOCKED — needs Khalid's account action)
Free hosting reality (researched): always-on live-market infrastructure is **not**
truly free anywhere. Options:
- **Render free web service** (`render.yaml` included): spins down after ~15 min idle,
  ephemeral filesystem (SQLite resets on deploy/spin-down cycles lose history).
  Suitable as a demo API, not as durable infrastructure.
- **Railway / Fly.io**: free trials/credits only — become paid; do NOT use without budget.
- **A $5–6/mo VPS** would be the honest production answer — requires Khalid's explicit
  paid approval, which is out of scope under the free-only constraint.

**Exact one action for Khalid to get a demo backend:** create a free Render account →
New → Web Service → connect GitHub repo `marketpilot-ai` → Render auto-reads
`render.yaml` → Deploy. Then paste the service URL into the dashboard Settings
(API base) and extension options. No payment method is needed for the free plan,
but the service will sleep when idle — that limitation is accepted and documented,
not hidden.

Local/self-host alternative (free, runs anywhere):
```bash
docker compose up -d   # or: .venv/bin/uvicorn backend.app.main:app --port 8000
```

## CI/CD
- `.github/workflows/ci.yml`: pytest + JS syntax checks + manifest validation on push/PR.
- `.github/workflows/pages.yml`: frontend deploy to Pages.

## Costs
Current recurring cost: **$0**. Optional future: custom domain (~$12/yr), VPS (~$60/yr),
paid data (TwelveData/Finnhub/Alpaca paid tiers) — none purchased, none required.
