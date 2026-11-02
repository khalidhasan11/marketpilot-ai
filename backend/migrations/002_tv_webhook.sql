-- MarketPilot AI migration 002 — TradingView webhook alerts (confirmation-only).
-- Applied automatically by init_db() (CREATE TABLE IF NOT EXISTS in db.py SCHEMA);
-- kept as a standalone SQL file for Postgres-profile parity.
CREATE TABLE IF NOT EXISTS tv_webhook_events(
  id INTEGER PRIMARY KEY,
  event_key TEXT UNIQUE NOT NULL,
  symbol_raw TEXT,
  symbol TEXT,
  action TEXT,
  price REAL,
  status TEXT NOT NULL,           -- accepted | duplicate | rejected_bad_secret | rejected_stale_timestamp | rejected_bad_timestamp | rejected_unknown_symbol
  payload TEXT,
  ip TEXT,
  ts INTEGER
);
CREATE INDEX IF NOT EXISTS idx_tv_events_ts ON tv_webhook_events(ts);
CREATE TABLE IF NOT EXISTS signal_confirmations(
  id INTEGER PRIMARY KEY,
  source TEXT NOT NULL,           -- 'tradingview_alert'
  symbol TEXT,
  action TEXT,
  price REAL,
  confirmation_only INTEGER NOT NULL DEFAULT 1,  -- alerts NEVER alter a decision
  event_id INTEGER,               -- -> tv_webhook_events.id
  ts INTEGER
);
