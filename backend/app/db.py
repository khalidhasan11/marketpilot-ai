"""SQLite persistence (zero-cost, runs anywhere). Schema is Postgres-compatible
in design (see migrations/001_init.sql). Uses stdlib sqlite3 only."""
import sqlite3, os, json, time, hashlib, secrets

DB_PATH=os.environ.get("MARKETPILOT_DB", os.path.join(os.path.dirname(__file__),"..","marketpilot.db"))

def conn():
    c=sqlite3.connect(os.path.abspath(DB_PATH)); c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA foreign_keys=ON"); return c

SCHEMA="""
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, salt TEXT NOT NULL, role TEXT DEFAULT 'user', created_at INTEGER);
CREATE TABLE IF NOT EXISTS user_settings(user_id INTEGER PRIMARY KEY, settings TEXT DEFAULT '{}');
CREATE TABLE IF NOT EXISTS assets(symbol TEXT PRIMARY KEY, base TEXT, quote TEXT, type TEXT, exchange TEXT);
CREATE TABLE IF NOT EXISTS exchanges(name TEXT PRIMARY KEY, status TEXT);
CREATE TABLE IF NOT EXISTS market_candles(symbol TEXT, interval TEXT, t INTEGER, o REAL, h REAL, l REAL, c REAL, v REAL, PRIMARY KEY(symbol,interval,t));
CREATE TABLE IF NOT EXISTS market_prices(symbol TEXT PRIMARY KEY, price REAL, ts INTEGER, data_label TEXT);
CREATE TABLE IF NOT EXISTS technical_indicators(symbol TEXT, interval TEXT, ts INTEGER, payload TEXT);
CREATE TABLE IF NOT EXISTS market_regimes(symbol TEXT, ts INTEGER, regime TEXT, payload TEXT);
CREATE TABLE IF NOT EXISTS news_articles(id INTEGER PRIMARY KEY, dedupe_hash TEXT UNIQUE, title TEXT, source TEXT, url TEXT, published_at TEXT, sentiment REAL, payload TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS economic_events(id INTEGER PRIMARY KEY, name TEXT, type TEXT, scheduled_note TEXT);
CREATE TABLE IF NOT EXISTS news_asset_impacts(article_id INTEGER, symbol TEXT, impact TEXT);
CREATE TABLE IF NOT EXISTS prediction_models(version TEXT PRIMARY KEY, kind TEXT, trained_at INTEGER, notes TEXT);
CREATE TABLE IF NOT EXISTS model_predictions(id INTEGER PRIMARY KEY, symbol TEXT, timeframe TEXT, direction TEXT, probability REAL, payload TEXT, ts INTEGER, expires_at TEXT);
CREATE TABLE IF NOT EXISTS trading_signals(id INTEGER PRIMARY KEY, symbol TEXT, timeframe TEXT, direction TEXT, status TEXT DEFAULT 'candidate', payload TEXT, ts INTEGER, updated_at INTEGER);
CREATE TABLE IF NOT EXISTS signal_updates(id INTEGER PRIMARY KEY, signal_id INTEGER, note TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS signal_outcomes(id INTEGER PRIMARY KEY, signal_id INTEGER, outcome TEXT, pnl REAL, ts INTEGER);
CREATE TABLE IF NOT EXISTS backtest_runs(id INTEGER PRIMARY KEY, symbol TEXT, timeframe TEXT, payload TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS backtest_results(id INTEGER PRIMARY KEY, run_id INTEGER, metrics TEXT);
CREATE TABLE IF NOT EXISTS paper_accounts(id INTEGER PRIMARY KEY, user_id INTEGER, balance REAL DEFAULT 10000, equity REAL DEFAULT 10000, created_at INTEGER);
CREATE TABLE IF NOT EXISTS paper_orders(id INTEGER PRIMARY KEY, account_id INTEGER, symbol TEXT, side TEXT, qty REAL, price REAL, status TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS paper_positions(id INTEGER PRIMARY KEY, account_id INTEGER, symbol TEXT, side TEXT, qty REAL, entry REAL, sl REAL, tp REAL, status TEXT DEFAULT 'open', pnl REAL, opened_at INTEGER, closed_at INTEGER);
CREATE TABLE IF NOT EXISTS watchlists(id INTEGER PRIMARY KEY, user_id INTEGER, name TEXT DEFAULT 'Default');
CREATE TABLE IF NOT EXISTS watchlist_items(id INTEGER PRIMARY KEY, watchlist_id INTEGER, symbol TEXT, UNIQUE(watchlist_id,symbol));
CREATE TABLE IF NOT EXISTS notifications(id INTEGER PRIMARY KEY, user_id INTEGER, kind TEXT, message TEXT, ts INTEGER, read_flag INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS data_provider_status(provider TEXT PRIMARY KEY, status TEXT, payload TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS audit_logs(id INTEGER PRIMARY KEY, user_id INTEGER, action TEXT, detail TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER, expires INTEGER);
CREATE TABLE IF NOT EXISTS tv_webhook_events(id INTEGER PRIMARY KEY, event_key TEXT UNIQUE NOT NULL, symbol_raw TEXT, symbol TEXT, action TEXT, price REAL, status TEXT NOT NULL, payload TEXT, ip TEXT, ts INTEGER);
CREATE TABLE IF NOT EXISTS signal_confirmations(id INTEGER PRIMARY KEY, source TEXT NOT NULL, symbol TEXT, action TEXT, price REAL, confirmation_only INTEGER NOT NULL DEFAULT 1, event_id INTEGER, ts INTEGER);
CREATE TABLE IF NOT EXISTS trades(id INTEGER PRIMARY KEY, symbol TEXT, price REAL, qty REAL, ts INTEGER);
CREATE TABLE IF NOT EXISTS orderbook_snapshots(id INTEGER PRIMARY KEY, symbol TEXT, payload TEXT, ts INTEGER);
"""

def init_db():
    c=conn()
    c.executescript(SCHEMA)
    from .providers import ASSETS
    for a in ASSETS: c.execute("INSERT OR IGNORE INTO assets VALUES (?,?,?,?,?)",(a["symbol"],a["base"],a["quote"],a["type"],a["exchange"]))
    c.execute("INSERT OR IGNORE INTO prediction_models VALUES (?,?,?,?)",("marketpilot-ensemble-v1.0.0","ensemble A-F",int(time.time()),"UNVALIDATED — no out-of-sample proof"))
    c.commit(); c.close()

def hash_password(password, salt=None):
    salt=salt or secrets.token_hex(16)
    h=hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()
    return h, salt

def audit(user_id, action, detail=""):
    c=conn(); c.execute("INSERT INTO audit_logs(user_id,action,detail,ts) VALUES (?,?,?,?)",(user_id,action,detail[:500],int(time.time()))); c.commit(); c.close()
