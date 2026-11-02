"""Pure-Python technical indicators. No look-ahead: every output at index i
uses only data up to i. All functions return lists aligned to input length
with None where insufficient data."""
import math

def sma(values, period):
    out=[None]*len(values); s=0.0
    for i,v in enumerate(values):
        s+=v
        if i>=period: s-=values[i-period]
        if i>=period-1: out[i]=s/period
    return out

def ema(values, period):
    out=[None]*len(values)
    if len(values)<period: return out
    k=2/(period+1); e=sum(values[:period])/period; out[period-1]=e
    for i in range(period,len(values)):
        e=values[i]*k+e*(1-k); out[i]=e
    return out

def ema_last(values, period):
    a=ema(values,period)
    for v in reversed(a):
        if v is not None: return v
    return None

def rsi(closes, period=14):
    out=[None]*len(closes)
    if len(closes)<=period: return out
    gains=[]; losses=[]
    for i in range(1,len(closes)):
        d=closes[i]-closes[i-1]; gains.append(max(d,0)); losses.append(max(-d,0))
    ag=sum(gains[:period])/period; al=sum(losses[:period])/period
    out[period]=100.0 if al==0 else 100-100/(1+ag/al)
    for i in range(period,len(gains)):
        ag=(ag*(period-1)+gains[i])/period; al=(al*(period-1)+losses[i])/period
        out[i+1]=100.0 if al==0 else 100-100/(1+ag/al)
    return out

def macd(closes, fast=12, slow=26, signal=9):
    ef=ema(closes,fast); es=ema(closes,slow)
    line=[(a-b) if a is not None and b is not None else None for a,b in zip(ef,es)]
    # signal EMA over non-None segment
    idx=next((i for i,v in enumerate(line) if v is not None), None)
    sig=[None]*len(closes); hist=[None]*len(closes)
    if idx is None: return line,sig,hist
    sub=[v for v in line[idx:]]
    se=ema(sub,signal)
    for i,v in enumerate(se): sig[idx+i]=v
    for i in range(len(closes)):
        if line[i] is not None and sig[i] is not None: hist[i]=line[i]-sig[i]
    return line,sig,hist

def bollinger(closes, period=20, mult=2.0):
    mid=sma(closes,period); upper=[None]*len(closes); lower=[None]*len(closes)
    for i in range(len(closes)):
        if mid[i] is None: continue
        w=closes[i-period+1:i+1]; var=sum((x-mid[i])**2 for x in w)/period; sd=math.sqrt(var)
        upper[i]=mid[i]+mult*sd; lower[i]=mid[i]-mult*sd
    return mid,upper,lower

def atr(highs,lows,closes,period=14):
    n=len(closes); tr=[0.0]*n
    for i in range(1,n):
        tr[i]=max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
    out=[None]*n
    if n<=period: return out
    a=sum(tr[1:period+1])/period; out[period]=a
    for i in range(period+1,n):
        a=(a*(period-1)+tr[i])/period; out[i]=a
    return out

def vwap(highs,lows,closes,volumes):
    out=[None]*len(closes); cv=0.0; vv=0.0
    for i in range(len(closes)):
        tp=(highs[i]+lows[i]+closes[i])/3; cv+=tp*volumes[i]; vv+=volumes[i]
        out[i]=cv/vv if vv>0 else None
    return out

def adx(highs,lows,closes,period=14):
    n=len(closes); tr=[0.0]*n; pdm=[0.0]*n; mdm=[0.0]*n
    for i in range(1,n):
        tr[i]=max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
        up=highs[i]-highs[i-1]; dn=lows[i-1]-lows[i]
        pdm[i]=up if (up>dn and up>0) else 0.0; mdm[i]=dn if (dn>up and dn>0) else 0.0
    def smooth(a):
        o=[None]*n
        if n<=period: return o
        s=sum(a[1:period+1]); o[period]=s
        for i in range(period+1,n): s=s-s/period+a[i]; o[i]=s
        return o
    st,sp,sm=smooth(tr),smooth(pdm),smooth(mdm)
    pdi=[None]*n; mdi=[None]*n; dx=[None]*n
    for i in range(n):
        if st[i]:
            pdi[i]=sp[i]/st[i]*100; mdi[i]=sm[i]/st[i]*100
            dx[i]=0 if (pdi[i]+mdi[i])==0 else abs(pdi[i]-mdi[i])/(pdi[i]+mdi[i])*100
    out=[None]*n; valid=[(i,v) for i,v in enumerate(dx) if v is not None]
    if len(valid)>period:
        a=sum(v for _,v in valid[:period])/period; out[valid[period-1][0]]=a
        for j in range(period,len(valid)):
            a=(a*(period-1)+valid[j][1])/period; out[valid[j][0]]=a
    return out,pdi,mdi

def stoch_rsi(closes, period=14, smooth_k=3, smooth_d=3):
    r=rsi(closes,period); raw=[None]*len(closes)
    for i in range(len(closes)):
        if i<period+13: continue
        w=r[i-13:i+1]
        if any(v is None for v in w): continue
        mx,mn=max(w),min(w); raw[i]=50.0 if mx==mn else (r[i]-mn)/(mx-mn)*100
    # simple smoothing ignoring None
    def smooth(vals,p):
        out=[None]*len(vals)
        for i in range(len(vals)):
            w=[v for v in vals[max(0,i-p+1):i+1] if v is not None]
            if len(w)==p: out[i]=sum(w)/p
        return out
    k=smooth(raw,smooth_k); d=smooth(k,smooth_d)
    return k,d

def support_resistance(highs,lows,lookback=50):
    h=highs[-lookback:]; l=lows[-lookback:]
    return min(l), max(h)

def structure(highs,lows):
    """Return HH/HL/LH/LL label for last swing comparison (simple, objective)."""
    if len(highs)<6: return "INSUFFICIENT"
    h1=max(highs[-6:-3]); h2=max(highs[-3:]); l1=min(lows[-6:-3]); l2=min(lows[-3:])
    if h2>h1 and l2>l1: return "HH_HL_UPTREND"
    if h2<h1 and l2<l1: return "LH_LL_DOWNTREND"
    if h2>h1 and l2<l1: return "EXPANDING_RANGE"
    return "HL_LH_CONTRACTION"

def detect_breakout(closes,highs,lows,lookback=20):
    if len(closes)<lookback+1: return None
    prior_high=max(highs[-lookback-1:-1]); prior_low=min(lows[-lookback-1:-1])
    c=closes[-1]
    if c>prior_high: return "BREAKOUT_UP"
    if c<prior_low: return "BREAKOUT_DOWN"
    return None

def compute_all(candles):
    """candles: list of dicts with o,h,l,c,v. Uses CLOSED candles as given."""
    closes=[c["c"] for c in candles]; highs=[c["h"] for c in candles]
    lows=[c["l"] for c in candles]; vols=[c["v"] for c in candles]
    def last(a):
        for v in reversed(a):
            if v is not None: return v
        return None
    _,bu,bl=bollinger(closes)
    ml,ms,mh=macd(closes)
    adx_v,_,_=adx(highs,lows,closes)
    srk,srd=stoch_rsi(closes)
    sup,res=support_resistance(highs,lows)
    return {
        "ema9":last(ema(closes,9)),"ema20":last(ema(closes,20)),"ema21":last(ema(closes,21)),
        "ema50":last(ema(closes,50)),"ema100":last(ema(closes,100)),"ema200":last(ema(closes,200)),
        "sma20":last(sma(closes,20)),"sma50":last(sma(closes,50)),
        "rsi":last(rsi(closes)),"macd_line":last(ml),"macd_signal":last(ms),"macd_hist":last(mh),
        "bollinger_upper":last(bu),"bollinger_lower":last(bl),
        "atr":last(atr(highs,lows,closes)),"vwap":last(vwap(highs,lows,closes,vols)),
        "adx":last(adx_v),"stoch_rsi_k":last(srk),"stoch_rsi_d":last(srd),
        "support":sup,"resistance":res,"structure":structure(highs,lows),
        "breakout":detect_breakout(closes,highs,lows),
    }

def aggregate_candles(candles_1s, factor_seconds):
    """Aggregate 1s candles (dicts with t in ms) into factor-second buckets."""
    buckets={}
    span=factor_seconds*1000
    for k in sorted(candles_1s, key=lambda x:x["t"]):
        bt=(k["t"]//span)*span
        if bt not in buckets:
            buckets[bt]={"t":bt,"o":k["o"],"h":k["h"],"l":k["l"],"c":k["c"],"v":k["v"]}
        else:
            b=buckets[bt]; b["h"]=max(b["h"],k["h"]); b["l"]=min(b["l"],k["l"]); b["c"]=k["c"]; b["v"]+=k["v"]
    return [buckets[k] for k in sorted(buckets)]
