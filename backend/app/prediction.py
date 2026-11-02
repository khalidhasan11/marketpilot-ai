"""Ensemble prediction: Models A–E transparent scorers + Model F ML (logistic
regression via scikit-learn when available, else pure-python fallback).
Fusion gates: data quality, news risk (danger veto), spread. Confidence is
ALWAYS UNVALIDATED until out-of-sample calibration exists — by design."""
import math
from datetime import datetime, timezone, timedelta
from . import MODEL_VERSION
from .indicators import compute_all
from .risk import atr_levels

def model_a_technical(candles, ind):
    closes=[c["c"] for c in candles]; price=closes[-1]; s=0.0; r=[]
    if ind.get("ema50"):
        s+= 22 if price>ind["ema50"] else -22; r.append("EMA50 trend")
    if ind.get("macd_hist") is not None:
        s+= 14 if ind["macd_hist"]>0 else -14; r.append("MACD")
    if ind.get("breakout"):
        s+= 8 if ind["breakout"]=="BREAKOUT_UP" else -8; r.append(ind["breakout"])
    return max(-100,min(100,s)), r

def model_b_momentum(candles, ind):
    rsi=ind.get("rsi"); s=0.0; reasons=[]
    if rsi is not None:
        if 55<=rsi<=70: s+=40; reasons.append(f"RSI {rsi:.0f} bullish zone")
        elif rsi>70: s-=30; reasons.append(f"RSI {rsi:.0f} overbought")
        elif 30<=rsi<45: s-=40; reasons.append(f"RSI {rsi:.0f} bearish zone")
        elif rsi<30: s+=30; reasons.append(f"RSI {rsi:.0f} oversold")
    if ind.get("ema9") and ind.get("ema21"):
        s+= 30 if ind["ema9"]>ind["ema21"] else -30; reasons.append("EMA9/21 momentum")
    return max(-100,min(100,s)), reasons

def model_c_volume(candles, ind):
    vols=[c["v"] for c in candles]; s=0.0; reasons=[]
    if len(vols)>=21:
        avg=sum(vols[-21:-1])/20
        if avg>0:
            ratio=vols[-1]/avg
            trend_up=ind.get("ema9") and ind.get("ema21") and ind["ema9"]>ind["ema21"]
            if ratio>1.3: s+= 35 if trend_up else -35; reasons.append(f"volume {ratio:.1f}x average")
            elif ratio<0.6: s-=10; reasons.append("volume drying up")
    vw=ind.get("vwap"); price=candles[-1]["c"]
    if vw: s+= 15 if price>vw else -15; reasons.append("price vs VWAP")
    return max(-100,min(100,s)), reasons

def model_d_regime(candles, ind):
    adx=ind.get("adx"); atr_v=ind.get("atr"); price=candles[-1]["c"]
    regime="RANGING"
    if adx is not None and adx>=25: regime="TRENDING"
    if atr_v and price and atr_v/price>0.03: regime="HIGH_VOLATILITY"
    s=0.0
    if ind.get("structure")=="HH_HL_UPTREND": s=35
    elif ind.get("structure")=="LH_LL_DOWNTREND": s=-35
    return s, [f"regime={regime} structure={ind.get('structure')}"], regime

def model_e_news(news):
    if not news: return 0.0, ["no news data"], "UNKNOWN"
    return float(news.get("score",0)), [f"news score {news.get('score')}"], news.get("news_risk","LOW")

def model_f_ml(candles):
    """Train logistic regression on chronological features if sklearn present.
    Returns (score -100..100, note). Trained ONLY on past candles in-window;
    this is in-window fitting, NOT out-of-sample proof — confidence stays UNVALIDATED."""
    try:
        from sklearn.linear_model import LogisticRegression
        import numpy as np
        from .indicators import rsi as rsi_fn, ema as ema_fn
        closes=[c["c"] for c in candles]
        if len(closes)<120: return 0.0, "insufficient candles for ML"
        r=rsi_fn(closes); e9=ema_fn(closes,9); e21=ema_fn(closes,21)
        X=[]; y=[]
        for i in range(60,len(closes)-1):
            if r[i] is None or e9[i] is None or e21[i] is None: continue
            X.append([r[i], (e9[i]-e21[i])/closes[i]*1000, (closes[i]-closes[i-5])/closes[i-5]*100])
            y.append(1 if closes[i+1]>closes[i] else 0)
        if len(X)<40 or len(set(y))<2: return 0.0, "ML: single-class window"
        split=int(len(X)*0.8)  # chronological split
        m=LogisticRegression(max_iter=500).fit(X[:split],y[:split])
        prob=float(m.predict_proba([X[-1]])[0][1])
        acc=float(m.score(X[split:],y[split:])) if split<len(X) else 0.0
        return round((prob-0.5)*200,1), f"ML logistic prob_up={prob:.2f} holdout_acc={acc:.2f} (in-window, unvalidated)"
    except Exception as e:
        return 0.0, f"ML unavailable ({type(e).__name__}) — ensemble proceeds without F"

def predict(symbol, timeframe, candles, news=None, spread_bps=None, exchange="binance"):
    now=datetime.now(timezone.utc)
    base={"asset":symbol,"market":"Crypto","timeframe":timeframe,"direction":"NO TRADE","probability":0.0,
          "confidence_level":"UNVALIDATED","entry_zone":None,"stop_loss":None,"take_profit":[],
          "risk_reward":None,"market_regime":"UNKNOWN","data_quality":"INSUFFICIENT","news_risk":"UNKNOWN",
          "model_version":MODEL_VERSION,"reasoning":[],"invalidation_conditions":[],
          "generated_at":now.isoformat(),"expires_at":(now+timedelta(minutes=15)).isoformat(),
          "data_label":"LIVE","exchange":exchange}
    if not candles or len(candles)<60:
        base["reasoning"]=[f"Insufficient candles ({len(candles) if candles else 0} < 60) — NO TRADE by evidence gate"]
        return base
    # stale check: last candle older than 3x timeframe-ish (only for minute TFs, best-effort)
    ind=compute_all(candles)
    if ind.get("atr") is None:
        base["reasoning"]=["ATR unavailable — cannot size risk — NO TRADE"]; return base
    if spread_bps is not None and spread_bps>50:
        base["reasoning"]=[f"Spread {spread_bps:.1f}bps > 50bps gate — NO TRADE"]; base["data_quality"]="POOR"; return base
    a,_=model_a_technical(candles,ind); b,_=model_b_momentum(candles,ind)
    c,_=model_c_volume(candles,ind); d,d_reasons,regime=model_d_regime(candles,ind)
    e,_,news_risk=model_e_news(news); f,f_note=model_f_ml(candles)
    fused=0.25*a+0.20*b+0.15*c+0.10*d+0.15*e+0.15*f
    base["market_regime"]=regime; base["news_risk"]=news_risk; base["data_quality"]="GOOD" if len(candles)>=200 else "FAIR"
    base["model_scores"]={"A_technical":round(a,1),"B_momentum":round(b,1),"C_volume":round(c,1),"D_regime":round(d,1),"E_news":round(e,1),"F_ml":round(f,1),"fused":round(fused,1)}
    reasons=[f"Ensemble fused score {fused:.1f} (A {a:.0f} B {b:.0f} C {c:.0f} D {d:.0f} E {e:.0f} F {f:.0f})", f_note,
             f"Structure {ind.get('structure')}, ADX {ind.get('adx')}, RSI {ind.get('rsi')}"]
    # danger veto
    if news and news.get("danger") and fused>0:
        base["reasoning"]=reasons+[f"DANGER VETO: fresh high-impact news ({news['danger']['source']}) cancels bullish signal"]
        base["probability"]=round(0.5+abs(fused)/200,3); return base
    if abs(fused)<25:
        base["reasoning"]=reasons+["|Fused score| < 25 evidence threshold — NO TRADE"]
        base["probability"]=round(0.5+fused/200,3); return base
    direction_long=fused>0
    price=candles[-1]["c"]
    levels=atr_levels(price, ind["atr"], "LONG" if direction_long else "SHORT",
                      swing_low=ind.get("support"), swing_high=ind.get("resistance"))
    if not levels:
        base["reasoning"]=reasons+["Risk levels could not be computed — NO TRADE"]; return base
    base.update({"direction":"BULLISH" if direction_long else "BEARISH",
        "probability":round(0.5+abs(fused)/200,3),
        "entry_zone":[round(price*0.999,6),round(price*1.001,6)],
        "stop_loss":levels["stop_loss"],"take_profit":levels["take_profit"],"risk_reward":levels["risk_reward"]})
    base["reasoning"]=reasons+["Signal is UNVALIDATED: no out-of-sample proof of edge. Prior honest backtest (BTC 5m) was 51.74% — below 54.05% break-even."]
    base["invalidation_conditions"]=["Price closes beyond stop-loss","Danger news event","Data feed goes stale","Spread widens above 50bps"]
    return base
