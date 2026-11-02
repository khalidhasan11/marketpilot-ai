"""TradingView webhook alerts — SUPPLEMENTARY CONFIRMATION ONLY.

An accepted alert is stored as a notification + a row in signal_confirmations
(source='tradingview_alert', confirmation_only=1). Nothing in the prediction,
scanner, or signal engine reads these tables: a TradingView alert can never
create, modify, or validate a MarketPilot decision. See
docs/TRADINGVIEW_INTEGRATION.md for the licensing basis.

Security: shared secret (constant-time compare), timestamp skew check,
duplicate detection, per-IP rate limiting (in main.py), full audit logging.
"""
import hashlib, json
from datetime import datetime, timezone

from .providers import ASSETS

_KNOWN = {a["symbol"] for a in ASSETS}


def normalize_symbol(raw):
    """Map TradingView-style symbols to the internal registry.
    'BINANCE:BTCUSDT' -> 'BTCUSDT'; 'BTC/USDT' -> 'BTCUSDT'; 'btcusdt' -> 'BTCUSDT'.
    Returns None for anything not in the internal asset registry."""
    if not raw or not isinstance(raw, str):
        return None
    s = raw.strip().upper()
    if ":" in s:
        s = s.split(":")[-1]
    s = s.replace("/", "").replace("-", "").replace(" ", "")
    return s if s in _KNOWN else None


def parse_timestamp(value):
    """Accept epoch seconds, epoch milliseconds, or ISO-8601 strings.
    Returns epoch seconds (float). Raises ValueError on anything else."""
    if value is None:
        raise ValueError("missing timestamp")
    if isinstance(value, (int, float)):
        v = float(value)
        if v > 1e12:  # milliseconds
            v = v / 1000.0
        return v
    if isinstance(value, str):
        s = value.strip()
        if s.replace(".", "", 1).isdigit():
            return parse_timestamp(float(s))
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    raise ValueError("unparseable timestamp")


def event_key_for(body, raw_bytes):
    """Stable dedupe key: caller's event_id when provided, else a hash of
    (symbol, action, timestamp, price), else a hash of the raw payload."""
    eid = body.get("event_id")
    if eid:
        return f"eid:{eid}"
    parts = [str(body.get("symbol", "")), str(body.get("action") or body.get("alert") or ""),
             str(body.get("timestamp", "")), str(body.get("price", ""))]
    if any(parts):
        return "h:" + hashlib.sha256("|".join(parts).encode()).hexdigest()
    return "raw:" + hashlib.sha256(raw_bytes).hexdigest()


def store_event(c, *, event_key, symbol_raw, symbol, action, price, status, payload, ip):
    c.execute(
        "INSERT OR IGNORE INTO tv_webhook_events(event_key,symbol_raw,symbol,action,price,status,payload,ip,ts)"
        " VALUES (?,?,?,?,?,?,?,?,strftime('%s','now'))",
        (event_key, (symbol_raw or "")[:100], symbol, (action or "")[:200],
         price, status, json.dumps(payload)[:4000], (ip or "")[:64]))
