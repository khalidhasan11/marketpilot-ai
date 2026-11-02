# Security — MarketPilot AI

- Passwords: PBKDF2-HMAC-SHA256, 200,000 iterations, per-user random salt (stdlib).
- Sessions: random 256-bit bearer tokens, 7-day expiry, stored server-side, revocable by row deletion.
- Secrets: environment variables only; `.env` gitignored; `.env.example` contains names only.
  No key is ever logged; the extension contains no keys at all.
- API: basic per-key rate limiting on price endpoints, Pydantic-validated inputs,
  parameterised SQL everywhere (no string-built queries), CORS configured in `main.py`
  (tighten `allow_origins` to the Pages domain for production).
- Paper trading is fully isolated: no broker credentials exist in this codebase and
  no real-money order path exists.
- Quotex: no scraping, no credential handling, no automation — by design.
- Known limits (honest): no CSRF token layer (bearer-token API, no cookies for auth),
  no email-based password reset (reset flow requires a mail provider — marked limited;
  admin can reset via DB), SQLite file permissions are the operator's responsibility.
- Report issues privately to the repo owner before public disclosure.
