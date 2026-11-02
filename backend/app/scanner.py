"""Scanner: Market Quality Score + Opportunity Score from real candles/depth."""
from .indicators import compute_all, ema

def market_quality(candles, spread_bps, data_age_sec=0):
    if not candles or len(candles)<30: return 0.0, ["insufficient candles"]
    closes=[c["c"] for c in candles]; vols=[c["v"] for c in candles]
    reasons=[]; score=50.0
    avg_vol=sum(vols[-20:])/max(1,len(vols[-20:]))
    if avg_vol>0: score+=15; reasons.append("adequate volume")
    else: score-=20; reasons.append("no volume")
    if spread_bps is not None:
        if spread_bps<5: score+=20; reasons.append(f"tight spread {spread_bps:.1f}bps")
        elif spread_bps<20: score+=5; reasons.append(f"moderate spread {spread_bps:.1f}bps")
        else: score-=25; reasons.append(f"wide spread {spread_bps:.1f}bps")
    else: score-=5; reasons.append("spread unknown")
    if data_age_sec>120: score-=30; reasons.append("stale data")
    # candle completeness
    gaps=sum(1 for a,b in zip(candles,candles[1:]) if b["t"]-a["t"]> (candles[1]["t"]-candles[0]["t"])*2.5) if len(candles)>2 else 0
    if gaps>3: score-=15; reasons.append(f"{gaps} candle gaps")
    return max(0.0,min(100.0,round(score,1))), reasons

def opportunity_score(candles, ind=None):
    if not candles or len(candles)<60: return 0.0, "INSUFFICIENT", []
    from .indicators import compute_all
    ind=ind or compute_all(candles)
    closes=[c["c"] for c in candles]; price=closes[-1]; score=0.0; reasons=[]
    if ind.get("ema50"):
        if price>ind["ema50"]: score+=22; reasons.append("price above EMA50")
        else: score-=22; reasons.append("price below EMA50")
    if ind.get("ema9") and ind.get("ema21"):
        if ind["ema9"]>ind["ema21"]: score+=18; reasons.append("EMA9>EMA21")
        else: score-=18; reasons.append("EMA9<EMA21")
    if ind.get("macd_hist") is not None:
        score+= 14 if ind["macd_hist"]>0 else -14; reasons.append("MACD bullish" if ind["macd_hist"]>0 else "MACD bearish")
    r=ind.get("rsi")
    if r is not None:
        if 55<=r<=70: score+=10; reasons.append(f"RSI {r:.0f} bullish momentum")
        elif r>70: score-=8; reasons.append(f"RSI {r:.0f} overbought caution")
        elif 30<=r<45: score-=10; reasons.append(f"RSI {r:.0f} bearish momentum")
        elif r<30: score+=8; reasons.append(f"RSI {r:.0f} oversold")
    if ind.get("breakout")=="BREAKOUT_UP": score+=8; reasons.append("breakout up")
    if ind.get("breakout")=="BREAKOUT_DOWN": score-=8; reasons.append("breakout down")
    score=max(-100.0,min(100.0,round(score,1)))
    return score, ind.get("structure"), reasons

def tier_for(quality, opp):
    a=abs(opp)
    if quality<40: return "AVOID"
    if a>=55 and quality>=70: return "P1"
    if a>=40 and quality>=60: return "P2"
    if a>=25: return "P3"
    if a>=12: return "WATCHLIST"
    return "AVOID" if quality<50 else "WATCHLIST"

def scan_symbol(symbol, candles, spread_bps=None, timeframe="5m"):
    q,qr=market_quality(candles,spread_bps)
    opp,struct,orr=opportunity_score(candles)
    return {"symbol":symbol,"timeframe":timeframe,"market_quality_score":q,"opportunity_score":opp,
            "tier":tier_for(q,opp),"structure":struct,"reasons":qr+orr,
            "volatility_note":"volatility alone is not an opportunity — scores require trend+momentum agreement",
            "data_label":"LIVE"}
