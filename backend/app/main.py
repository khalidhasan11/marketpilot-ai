"""MarketPilot AI — FastAPI backend. Versioned /api/v1. OpenAPI at /docs."""
import os, time, json, secrets, asyncio
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Header, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from .db import init_db, conn, hash_password, audit
from .providers import BinanceProvider, ASSETS, provider_statuses, timeframe_support
from .indicators import compute_all
from .news_engine import fetch_news
from .scanner import scan_symbol
from .prediction import predict
from .backtest import run_backtest, walk_forward
from .risk import position_size, guards
from . import paper as paper_mod
from . import MODEL_VERSION

app = FastAPI(title="MarketPilot AI", version="1.0.0",
              description="Live market intelligence. Predictions are UNVALIDATED until out-of-sample proof exists. Educational tool — not financial advice.")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
binance = BinanceProvider()
_rate = {}

@app.on_event("startup")
def _startup(): init_db()

def rate_limit(key, limit=120, window=60):
    now = time.time(); hits = [t for t in _rate.get(key, []) if now - t < window]
    if len(hits) >= limit: raise HTTPException(429, "Rate limit exceeded")
    hits.append(now); _rate[key] = hits

def current_user(authorization: Optional[str] = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    tok = authorization[7:]; c = conn()
    row = c.execute("SELECT user_id, expires FROM sessions WHERE token=?", (tok,)).fetchone(); c.close()
    if not row or row["expires"] < int(time.time()): raise HTTPException(401, "Invalid or expired session")
    return row["user_id"]

class AuthIn(BaseModel): email: str; password: str
class PaperOrderIn(BaseModel): symbol: str; side: str; qty: float; price: float; sl: Optional[float]=None; tp: Optional[float]=None
class WatchIn(BaseModel): symbol: str
class SizeIn(BaseModel): balance: float; risk_pct: float = 1.0; entry: float; stop_loss: float

@app.get("/health")
def health():
    try:
        c = conn(); c.execute("SELECT 1"); c.close(); db = "ok"
    except Exception as e: db = f"error: {e}"
    return {"status": "ok" if db == "ok" else "degraded", "service": "marketpilot-ai", "model_version": MODEL_VERSION,
            "database": db, "cache": "in-process (Redis optional, not required)", "providers": provider_statuses(),
            "time": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/providers/status")
def providers(): return {"providers": provider_statuses(), "quotex": {"status": "unsupported_data_limited", "note": "No official Quotex API. OTC prices are broker-made. No scraping/bypass. Manual-observation mode only."}}

@app.get("/api/v1/assets")
def assets(): return {"assets": ASSETS, "data_label": "LIVE (Binance crypto) / key-gated for forex-stocks"}

@app.get("/api/v1/prices/{symbol}")
def price(symbol: str):
    rate_limit(f"price:{symbol}")
    try: return binance.ticker(symbol.upper())
    except Exception as e: raise HTTPException(502, f"Binance error: {e}")

@app.get("/api/v1/candles/{symbol}")
def candles(symbol: str, interval: str = "5m", limit: int = 300):
    sup = timeframe_support(interval)
    if not sup["supported"]: raise HTTPException(400, sup["note"])
    try:
        data = binance.klines(symbol.upper(), interval, min(limit, 1000))
        return {"symbol": symbol.upper(), "interval": interval, "candles": data, "support": sup, "data_label": "LIVE"}
    except Exception as e: raise HTTPException(502, f"Provider error: {e}")

@app.get("/api/v1/depth/{symbol}")
def depth(symbol: str):
    try: return binance.depth(symbol.upper())
    except Exception as e: raise HTTPException(502, str(e))

@app.get("/api/v1/analysis/{symbol}")
def analysis(symbol: str, interval: str = "5m"):
    try:
        cs = binance.klines(symbol.upper(), interval, 300); ind = compute_all(cs[:-1] if len(cs) > 1 else cs)
        return {"symbol": symbol.upper(), "interval": interval, "indicators": ind, "price": cs[-1]["c"] if cs else None, "data_label": "LIVE", "note": "Indicators use closed candles only."}
    except Exception as e: raise HTTPException(502, str(e))

@app.get("/api/v1/scanner")
def scanner(interval: str = "5m", limit_symbols: int = 6):
    out = []
    for a in ASSETS[:limit_symbols]:
        try:
            cs = binance.klines(a["symbol"], interval, 300)
            try: spread = binance.depth(a["symbol"], 5).get("spread_bps")
            except Exception: spread = None
            out.append(scan_symbol(a["symbol"], cs[:-1] if len(cs) > 1 else cs, spread, interval))
        except Exception as e: out.append({"symbol": a["symbol"], "error": str(e)[:150], "tier": "AVOID"})
    out.sort(key=lambda x: abs(x.get("opportunity_score") or 0), reverse=True)
    return {"rankings": out, "timeframe": interval, "data_label": "LIVE", "updated_at": datetime.now(timezone.utc).isoformat()}

@app.get("/api/v1/news")
def news(symbol: str = "BTCUSDT"):
    try:
        n = fetch_news(symbol.upper())
        c = conn()
        for it in n["items"][:30]:
            try: c.execute("INSERT OR IGNORE INTO news_articles(dedupe_hash,title,source,url,published_at,sentiment,payload,ts) VALUES (?,?,?,?,?,?,?,?)",
                           (it.get("dedupe_hash"), it["title"], it["source"], it["link"], it.get("published_at"), it.get("sentiment"), json.dumps(it)[:4000], int(time.time())))
            except Exception: pass
        c.commit(); c.close()
        return n
    except Exception as e: raise HTTPException(502, str(e))

@app.get("/api/v1/predictions/{symbol}")
def prediction(symbol: str, interval: str = "5m"):
    try:
        cs = binance.klines(symbol.upper(), interval, 300)
        try: spread = binance.depth(symbol.upper(), 5).get("spread_bps")
        except Exception: spread = None
        try: news = fetch_news(symbol.upper())
        except Exception: news = None
        p = predict(symbol.upper(), interval, cs[:-1] if len(cs) > 1 else cs, news=news, spread_bps=spread)
        c = conn(); c.execute("INSERT INTO model_predictions(symbol,timeframe,direction,probability,payload,ts,expires_at) VALUES (?,?,?,?,?,?,?)",
                              (symbol.upper(), interval, p["direction"], p["probability"], json.dumps(p)[:8000], int(time.time()), p["expires_at"]))
        if p["direction"] not in ("NO TRADE",):
            cur = c.execute("INSERT INTO trading_signals(symbol,timeframe,direction,status,payload,ts,updated_at) VALUES (?,?,?,'active',?,?,?)",
                            (symbol.upper(), interval, p["direction"], json.dumps(p)[:8000], int(time.time()), int(time.time())))
            p["signal_id"] = cur.lastrowid
        c.commit(); c.close()
        return p
    except HTTPException: raise
    except Exception as e: raise HTTPException(502, str(e))

@app.get("/api/v1/signals")
def signals(limit: int = 50):
    c = conn(); rows = [dict(r) for r in c.execute("SELECT id,symbol,timeframe,direction,status,ts FROM trading_signals ORDER BY id DESC LIMIT ?", (limit,)).fetchall()]; c.close()
    return {"signals": rows, "note": "Immutable history — signals are never rewritten; status transitions are appended via signal_updates."}

@app.post("/api/v1/backtest/{symbol}")
def backtest(symbol: str, interval: str = "5m", limit: int = 500, walk: bool = False):
    try:
        cs = binance.klines(symbol.upper(), interval, min(limit, 1000))
        closed = cs[:-1] if len(cs) > 1 else cs
        res = walk_forward(closed) if walk else run_backtest(closed)
        c = conn(); cur = c.execute("INSERT INTO backtest_runs(symbol,timeframe,payload,ts) VALUES (?,?,?,?)", (symbol.upper(), interval, json.dumps(res)[:8000], int(time.time())))
        c.execute("INSERT INTO backtest_results(run_id,metrics) VALUES (?,?)", (cur.lastrowid, json.dumps(res)[:8000])); c.commit(); c.close()
        return {"symbol": symbol.upper(), "interval": interval, "data_label": "LIVE historical (Binance)", "result": res}
    except Exception as e: raise HTTPException(502, str(e))

@app.post("/api/v1/auth/register")
def register(body: AuthIn):
    if len(body.password) < 8: raise HTTPException(400, "Password must be at least 8 characters")
    h, salt = hash_password(body.password); c = conn()
    try:
        cur = c.execute("INSERT INTO users(email,password_hash,salt,role,created_at) VALUES (?,?,?,'user',?)", (body.email.lower(), h, salt, int(time.time())))
        c.commit(); uid = cur.lastrowid
    except Exception: c.close(); raise HTTPException(409, "Email already registered")
    c.close(); audit(uid, "register"); return {"user_id": uid, "email": body.email.lower()}

@app.post("/api/v1/auth/login")
def login(body: AuthIn):
    c = conn(); row = c.execute("SELECT * FROM users WHERE email=?", (body.email.lower(),)).fetchone(); c.close()
    if not row: raise HTTPException(401, "Invalid credentials")
    h, _ = hash_password(body.password, row["salt"])
    if h != row["password_hash"]: raise HTTPException(401, "Invalid credentials")
    tok = secrets.token_urlsafe(32); exp = int(time.time()) + 86400 * 7
    c = conn(); c.execute("INSERT INTO sessions(token,user_id,expires) VALUES (?,?,?)", (tok, row["id"], exp)); c.commit(); c.close()
    audit(row["id"], "login"); return {"token": tok, "user_id": row["id"], "expires_at": exp}

@app.get("/api/v1/watchlists")
def get_watch(authorization: Optional[str] = Header(default=None)):
    uid = current_user(authorization); c = conn()
    wl = c.execute("SELECT * FROM watchlists WHERE user_id=?", (uid,)).fetchone()
    if not wl:
        c.execute("INSERT INTO watchlists(user_id,name) VALUES (?, 'Default')", (uid,)); c.commit()
        wl = c.execute("SELECT * FROM watchlists WHERE user_id=?", (uid,)).fetchone()
    items = [r["symbol"] for r in c.execute("SELECT symbol FROM watchlist_items WHERE watchlist_id=?", (wl["id"],)).fetchall()]; c.close()
    return {"watchlist_id": wl["id"], "items": items}

@app.post("/api/v1/watchlists/items")
def add_watch(body: WatchIn, authorization: Optional[str] = Header(default=None)):
    uid = current_user(authorization); w = get_watch(authorization)
    c = conn(); c.execute("INSERT OR IGNORE INTO watchlist_items(watchlist_id,symbol) VALUES (?,?)", (w["watchlist_id"], body.symbol.upper())); c.commit(); c.close()
    return get_watch(authorization)

@app.get("/api/v1/notifications")
def notifs(authorization: Optional[str] = Header(default=None)):
    uid = current_user(authorization); c = conn()
    rows = [dict(r) for r in c.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY id DESC LIMIT 50", (uid,)).fetchall()]; c.close()
    return {"notifications": rows}

@app.get("/api/v1/paper/account")
def paper_account(authorization: Optional[str] = Header(default=None)):
    uid = current_user(authorization); return paper_mod.portfolio(uid)

@app.post("/api/v1/paper/orders")
def paper_order(body: PaperOrderIn, authorization: Optional[str] = Header(default=None)):
    uid = current_user(authorization)
    if body.side not in ("BUY", "SELL"): raise HTTPException(400, "side must be BUY or SELL")
    return paper_mod.place_order(uid, body.symbol.upper(), body.side, body.qty, body.price, body.sl, body.tp)

@app.post("/api/v1/paper/close/{position_id}")
def paper_close(position_id: int, price: float = Query(...), authorization: Optional[str] = Header(default=None)):
    uid = current_user(authorization); return paper_mod.close_position(uid, position_id, price)

@app.post("/api/v1/risk/position-size")
def sizing(body: SizeIn): return position_size(body.balance, body.risk_pct, body.entry, body.stop_loss)

@app.get("/api/v1/risk/guards")
def risk_guards(authorization: Optional[str] = Header(default=None)):
    uid = current_user(authorization); pf = paper_mod.portfolio(uid)
    pnls = [p.get("pnl") or 0 for p in pf["closed_positions"]]
    return guards(pnls)

@app.get("/api/v1/performance")
def performance():
    c = conn()
    total = c.execute("SELECT COUNT(*) n FROM trading_signals").fetchone()["n"]
    bt = c.execute("SELECT COUNT(*) n FROM backtest_runs").fetchone()["n"]
    preds = c.execute("SELECT COUNT(*) n FROM model_predictions").fetchone()["n"]; c.close()
    return {"signals_recorded": total, "predictions_recorded": preds, "backtest_runs": bt,
            "accuracy": None, "accuracy_note": "No validated accuracy exists yet. Accuracy is only reported after out-of-sample outcomes accumulate — never fabricated.",
            "prior_prototype_reference": {"btc_5m_win_rate_pct": 51.74, "breakeven_pct": 54.05, "verdict": "below break-even, no proven edge"}}

@app.get("/api/v1/economic-calendar")
def econ_cal():
    return {"events": [
        {"name": "US CPI", "type": "inflation", "note": "Monthly, Bureau of Labor Statistics — check bls.gov for exact release date"},
        {"name": "US PPI", "type": "inflation", "note": "Monthly, BLS"},
        {"name": "Nonfarm Payrolls (NFP)", "type": "employment", "note": "First Friday of month, typically — verify on bls.gov"},
        {"name": "FOMC Decision", "type": "central_bank", "note": "8 meetings/year — verify on federalreserve.gov"},
        {"name": "GDP Advance", "type": "growth", "note": "Quarterly, BEA — verify on bea.gov"}],
        "disclaimer": "Reference schedule of event TYPES only. Exact dates must be verified on official sources — no dates are invented here.", "data_label": "REFERENCE"}

@app.get("/api/v1/quotex")
def quotex():
    return {"module": "Quotex Compatibility", "status": "DATA-LIMITED / UNSUPPORTED for OTC",
            "reasons": ["Quotex provides no official public API for OTC prices", "OTC prices are broker-generated and differ from Binance/exchange prices", "Scraping, login bypass and private-API reverse engineering are prohibited and not implemented"],
            "supported": ["Independent exchange-market analysis (Binance) shown separately", "Manual observation mode: user records displayed Quotex price + timestamp and compares manually"],
            "signals_for_quotex_otc": "DISABLED — required validated OTC data source is unavailable"}

@app.websocket("/ws/prices/{symbol}")
async def ws_prices(ws: WebSocket, symbol: str):
    await ws.accept()
    try:
        while True:
            try:
                t = binance.ticker(symbol.upper()); await ws.send_json(t)
            except Exception as e: await ws.send_json({"error": str(e)[:150], "data_label": "UNAVAILABLE"})
            await asyncio.sleep(5)
    except WebSocketDisconnect: pass
