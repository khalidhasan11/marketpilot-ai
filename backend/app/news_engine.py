"""News intelligence: real RSS ingestion, dedupe by hash, source weights,
keyword sentiment, freshness decay, asset mapping, danger veto.
Reuses proven logic from crypto-signal-prototype (English output)."""
import hashlib, math, re, urllib.request, xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEEDS=[
    ("CoinDesk",1.0,"https://www.coindesk.com/arc/outboundfeeds/rss/"),
    ("CoinTelegraph",0.8,"https://cointelegraph.com/rss"),
    ("Decrypt",0.8,"https://decrypt.co/feed"),
    ("Bitcoin Magazine",0.7,"https://bitcoinmagazine.com/feed"),
    ("Google News",0.6,"https://news.google.com/rss/search?q=bitcoin+cryptocurrency&hl=en-US&gl=US&ceid=US:en"),
]
BULLISH={"etf approval":3,"approved":1.5,"approval":1.5,"all-time high":2,"surge":2,"surg":1.5,"rally":2,"bullish":2,"adoption":1.5,"institutional":1,"inflow":2,"listing":1,"listed":1,"partnership":1.5,"soars":2,"soar":2,"jumps":1.5,"jump":1,"gains":1,"gain":1,"breakout":1.5,"accumulat":1.5,"buys":1,"buying":1,"record high":2,"upgrade":1,"integration":1,"reserve":1}
BEARISH={"hack":3,"exploit":3,"stolen":2.5,"ban":2.5,"bans":2.5,"lawsuit":2,"sues":2,"fraud":2.5,"scam":2,"bankrupt":3,"crash":2.5,"plunge":2.5,"plunges":2.5,"tumbles":2,"liquidation":2,"outflow":2,"bearish":2,"falls":1.5,"fall":1,"drops":1.5,"drop":1,"dumps":2,"sell-off":2,"selloff":2,"warning":1,"arrest":2,"probe":1.5,"investigat":1.5,"delist":2,"halt":1.5,"fears":1,"recession":1.5,"tariff":1,"sanction":1.5}
DANGER=["hack","exploit","bankrupt","stolen","fraud","crash","plunge","ban"]
ASSET_KEYS={"BTC":["bitcoin","btc"],"ETH":["ethereum","eth","ether"],"SOL":["solana","sol"],"XRP":["xrp","ripple"],"BNB":["bnb","binance"]}

def dedupe_key(title):
    t=title.lower()
    if " - " in t: t=t.rsplit(" - ",1)[0]
    t=re.sub(r"[^a-z0-9 ]","",t)[:60].strip()
    return hashlib.sha256(t.encode()).hexdigest()[:16]

def sentiment_of(title):
    text=title.lower(); s=0.0
    for k,v in BULLISH.items():
        if k in text: s+=v
    for k,v in BEARISH.items():
        if k in text: s-=v
    s=max(-4.0,min(4.0,s))/4.0
    label="bullish" if s>0.15 else ("bearish" if s<-0.15 else "neutral")
    return round(s,3), label

def affected_assets(title):
    text=title.lower(); out=[]
    for sym,keys in ASSET_KEYS.items():
        if any(k in text for k in keys): out.append(sym+"USDT")
    if not out and ("crypto" in text or "market" in text): out=["BTCUSDT","ETHUSDT"]
    return out

def _fetch_feed(name,weight,url,now):
    items=[]; req=urllib.request.Request(url,headers={"User-Agent":"MarketPilotAI/1.0"})
    with urllib.request.urlopen(req,timeout=12) as r: raw=r.read()
    root=ET.fromstring(raw)
    for item in root.iter("item"):
        title=(item.findtext("title") or "").strip(); link=(item.findtext("link") or "").strip()
        pub=item.findtext("pubDate") or item.findtext("{http://purl.org/dc/elements/1.1/}date")
        ts=now
        if pub:
            try: ts=parsedate_to_datetime(pub).astimezone(timezone.utc)
            except Exception: ts=now
        age=max(0.0,(now-ts).total_seconds()/60)
        if age>1440 or not title: continue
        items.append({"title":title,"link":link,"source":name,"weight":weight,"published_at":ts.isoformat(),"age_min":round(age,1)})
    return items

def fetch_news(symbol="BTCUSDT"):
    now=datetime.now(timezone.utc); raw=[]; errors=[]
    for name,w,url in FEEDS:
        try: raw.extend(_fetch_feed(name,w,url,now))
        except Exception as e: errors.append(f"{name}: {type(e).__name__}")
    seen=set(); uniq=[]
    for it in sorted(raw,key=lambda x:x["age_min"]):
        k=dedupe_key(it["title"])
        if k in seen: continue
        seen.add(k); it["dedupe_hash"]=k; uniq.append(it)
    base=symbol.replace("USDT","")
    agg=0.0; bull=bear=0; danger=None; scored=[]
    for it in uniq:
        s,label=sentiment_of(it["title"])
        relevant=any(k in it["title"].lower() for k in ASSET_KEYS.get(base,[]))
        general=("crypto" in it["title"].lower() or "market" in it["title"].lower()
                 or any(k in it["title"].lower() for ks in ASSET_KEYS.values() for k in ks))
        cw=1.0 if relevant else (0.6 if general else 0.25)
        fresh=0.5**(it["age_min"]/180.0)
        agg+=s*it["weight"]*cw*fresh
        if s>0.15: bull+=1
        elif s<-0.15: bear+=1
        if any(d in it["title"].lower() for d in DANGER) and s<-0.3 and it["age_min"]<=240:
            if danger is None or it["age_min"]<danger["age_min"]:
                danger={"title":it["title"],"source":it["source"],"age_min":it["age_min"]}
        it2=dict(it); it2["sentiment"]=s; it2["label"]=label; it2["affected_assets"]=affected_assets(it["title"])
        it2["verified_status"]="rss_source"; it2["impact"]="high" if abs(s)>=0.5 else ("medium" if abs(s)>=0.25 else "low")
        scored.append(it2)
    score=round(100*math.tanh(agg/3.0),1) if scored else 0.0
    return {"score":score,"items":scored[:30],"bullish_count":bull,"bearish_count":bear,
            "danger":danger,"feed_errors":errors,"total_seen":len(raw),
            "news_risk":"HIGH" if danger else ("MEDIUM" if abs(score)>40 else "LOW"),
            "data_label":"LIVE (RSS)","fetched_at":now.isoformat()}
