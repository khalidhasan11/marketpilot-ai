"""Provider abstraction layer. Binance public = working, no key.
TwelveData/Finnhub/Alpaca = config-gated stubs returning explicit status, never fake data."""
import os, time, json, urllib.request, urllib.error

BINANCE = "https://data-api.binance.vision"
UA = {"User-Agent": "MarketPilotAI/1.0"}

ASSETS = [
    {"symbol":"BTCUSDT","base":"BTC","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"ETHUSDT","base":"ETH","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"BNBUSDT","base":"BNB","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"SOLUSDT","base":"SOL","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"XRPUSDT","base":"XRP","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"ADAUSDT","base":"ADA","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"DOGEUSDT","base":"DOGE","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"LINKUSDT","base":"LINK","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"LTCUSDT","base":"LTC","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"MATICUSDT","base":"MATIC","quote":"USDT","type":"crypto","exchange":"binance"},
    {"symbol":"PAXGUSDT","base":"PAXG (Gold proxy)","quote":"USDT","type":"commodity_proxy","exchange":"binance"},
]
NATIVE_INTERVALS = {"1s","1m","3m","5m","15m","30m","1h","2h","4h","6h","8h","12h","1d","3d","1w","1M"}
AGGREGATED = {"5s":5,"15s":15,"30s":30}

def _get(url, timeout=15):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())

class BinanceProvider:
    name="binance"; data_label="LIVE"
    def ticker(self, symbol):
        d=_get(f"{BINANCE}/api/v3/ticker/24hr?symbol={symbol}")
        return {"symbol":symbol,"price":float(d["lastPrice"]),"change_pct":float(d["priceChangePercent"]),
                "high":float(d["highPrice"]),"low":float(d["lowPrice"]),"volume":float(d["volume"]),
                "bid":float(d.get("bidPrice") or 0),"ask":float(d.get("askPrice") or 0),
                "data_label":"LIVE","source":"binance","ts":int(time.time()*1000)}
    def klines(self, symbol, interval, limit=300):
        from .indicators import aggregate_candles
        if interval in AGGREGATED:
            factor=AGGREGATED[interval]
            raw=_get(f"{BINANCE}/api/v3/klines?symbol={symbol}&interval=1s&limit={min(1000,limit*factor)}")
            ones=[{"t":int(k[0]),"o":float(k[1]),"h":float(k[2]),"l":float(k[3]),"c":float(k[4]),"v":float(k[5])} for k in raw]
            return aggregate_candles(ones,factor)[-limit:]
        if interval not in NATIVE_INTERVALS:
            raise ValueError(f"Unsupported interval {interval}")
        data=_get(f"{BINANCE}/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}")
        return [{"t":int(k[0]),"o":float(k[1]),"h":float(k[2]),"l":float(k[3]),"c":float(k[4]),"v":float(k[5])} for k in data]
    def depth(self, symbol, limit=20):
        d=_get(f"{BINANCE}/api/v3/depth?symbol={symbol}&limit={limit}")
        bids=[{"price":float(p),"qty":float(q)} for p,q in d.get("bids",[])]
        asks=[{"price":float(p),"qty":float(q)} for p,q in d.get("asks",[])]
        spread=(asks[0]["price"]-bids[0]["price"]) if bids and asks else None
        mid=((asks[0]["price"]+bids[0]["price"])/2) if bids and asks else None
        spread_bps=(spread/mid*10000) if spread and mid else None
        return {"bids":bids,"asks":asks,"spread":spread,"spread_bps":spread_bps,"data_label":"LIVE"}
    def trades(self, symbol, limit=50):
        d=_get(f"{BINANCE}/api/v3/trades?symbol={symbol}&limit={limit}")
        return [{"id":t["id"],"price":float(t["price"]),"qty":float(t["qty"]),"time":t["time"],"is_buyer_maker":t["isBuyerMaker"]} for t in d]
    def status(self):
        try:
            _get(f"{BINANCE}/api/v3/ping", timeout=8)
            return {"provider":"binance","status":"ok","data_label":"LIVE","requires_key":False,"note":"Public REST, no key. Real-time for crypto spot."}
        except Exception as e:
            return {"provider":"binance","status":"error","error":str(e)[:200],"data_label":"UNAVAILABLE","requires_key":False}

class KeyGatedProvider:
    def __init__(self, name, env_var, covers):
        self.name=name; self.env_var=env_var; self.covers=covers
    def status(self):
        has=bool(os.environ.get(self.env_var))
        return {"provider":self.name,"status":"configured" if has else "requires_api_key",
                "data_label":"LIVE" if has else "UNAVAILABLE","requires_key":True,
                "env_var":self.env_var,"covers":self.covers,
                "note":"Set a free-tier API key in .env to enable. No data is faked while unconfigured."}
    def klines(self, *a, **k):
        raise RuntimeError(f"{self.name} requires free API key ({self.env_var}) — not configured")

def all_providers():
    return [BinanceProvider(),
            KeyGatedProvider("twelvedata","TWELVEDATA_API_KEY","forex, stocks, indices, metals"),
            KeyGatedProvider("finnhub","FINNHUB_API_KEY","stocks, forex, news"),
            KeyGatedProvider("alpaca","ALPACA_API_KEY","US stocks (paper/live data)")]

def provider_statuses():
    out=[]
    for p in all_providers():
        try: out.append(p.status())
        except Exception as e: out.append({"provider":getattr(p,'name','?'),"status":"error","error":str(e)[:150]})
    return out

def timeframe_support(interval):
    if interval in AGGREGATED:
        return {"supported":True,"method":"aggregated_from_1s_trades/klines","note":"Built only from real 1s Binance klines."}
    if interval in NATIVE_INTERVALS:
        return {"supported":True,"method":"native","note":"Native Binance interval."}
    if interval in ("1s",):
        return {"supported":True,"method":"native","note":"Native 1s klines."}
    return {"supported":False,"method":None,"note":f"Interval {interval} not supplied by provider at sufficient resolution — predictions disabled for it."}
