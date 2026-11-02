"""Backtester: historical replay, EMA-cross+RSI (proven logic from crypto-signal),
fees, slippage, chronological split, walk-forward, honest metrics. No look-ahead:
signals use closed candles only; entry at next candle open."""
import math
from .indicators import ema, rsi

def _signals(candles):
    closes=[c["c"] for c in candles]
    e5=ema(closes,5); e13=ema(closes,13); r=rsi(closes)
    out=[]  # (index, direction) signal confirmed at close of index
    for i in range(30,len(candles)):
        if None in (e5[i],e13[i],e5[i-1],e13[i-1],r[i]): continue
        if e5[i-1]<=e13[i-1] and e5[i]>e13[i] and r[i]<70: out.append((i,"LONG"))
        elif e5[i-1]>=e13[i-1] and e5[i]<e13[i] and r[i]>30: out.append((i,"SHORT"))
    return out

def run_backtest(candles, fee_pct=0.1, slippage_pct=0.02, rr=3.0, swing=14, initial=10000.0, risk_pct=1.0):
    if not candles or len(candles)<100:
        return {"error":"insufficient candles","trades":0}
    sigs=_signals(candles)
    equity=initial; peak=initial; max_dd=0.0; trades=[]
    probs=[]; outcomes=[]
    open_until=-1
    for idx,direction in sigs:
        if idx<=open_until or idx+1>=len(candles): continue
        entry_c=candles[idx]; entry_price=candles[idx+1]["o"]  # next open, no look-ahead
        window=candles[max(0,idx-swing):idx+1]
        if direction=="LONG":
            sl=min(c["l"] for c in window)
            if not sl<entry_price: sl=entry_price*0.99
            risk=entry_price-sl; tp=entry_price+rr*risk
        else:
            sl=max(c["h"] for c in window)
            if not sl>entry_price: sl=entry_price*1.01
            risk=sl-entry_price; tp=entry_price-rr*risk
        risk_amount=equity*(risk_pct/100); qty=risk_amount/risk if risk>0 else 0
        exit_price=None; outcome=None; exit_i=None
        for j in range(idx+1,len(candles)):
            cd=candles[j]
            if direction=="LONG":
                if cd["l"]<=sl: exit_price, outcome = sl, "SL"
                elif cd["h"]>=tp: exit_price, outcome = tp, "TP"
            else:
                if cd["h"]>=sl: exit_price, outcome = sl, "SL"
                elif cd["l"]<=tp: exit_price, outcome = tp, "TP"
            if outcome: exit_i=j; break
        if exit_price is None:
            exit_price=candles[-1]["c"]; outcome="OPEN_END"; exit_i=len(candles)-1
        slip=exit_price*(slippage_pct/100)*(1 if direction=="LONG" else -1)
        eff_exit=exit_price-slip
        pnl=(eff_exit-entry_price)*qty if direction=="LONG" else (entry_price-eff_exit)*qty
        fees=(entry_price+eff_exit)*qty*(fee_pct/100)
        pnl-=fees; equity+=pnl; peak=max(peak,equity)
        if peak>0: max_dd=max(max_dd,(peak-equity)/peak*100)
        trades.append({"signal_index":idx,"direction":direction,"entry":entry_price,"sl":sl,"tp":tp,
                       "exit":eff_exit,"outcome":outcome,"pnl":round(pnl,2),"exit_index":exit_i})
        # Brier: predicted prob fixed 0.55 for directional call (documented, uncalibrated)
        probs.append(0.55); outcomes.append(1 if pnl>0 else 0)
        open_until=exit_i
    wins=[t for t in trades if t["pnl"]>0]; losses=[t for t in trades if t["pnl"]<=0]
    gross_w=sum(t["pnl"] for t in wins); gross_l=abs(sum(t["pnl"] for t in losses))
    rets=[t["pnl"]/initial for t in trades]
    sharpe=0.0
    if len(rets)>1:
        mean=sum(rets)/len(rets); var=sum((x-mean)**2 for x in rets)/len(rets); sd=math.sqrt(var)
        sharpe=round(mean/sd*math.sqrt(len(rets)),3) if sd>0 else 0.0
    brier=round(sum((p-o)**2 for p,o in zip(probs,outcomes))/len(probs),4) if probs else None
    return {"trades_count":len(trades),"wins":len(wins),"losses":len(losses),
        "win_rate":round(len(wins)/len(trades)*100,2) if trades else 0.0,
        "profit_factor":round(gross_w/gross_l,3) if gross_l>0 else None,
        "expectancy":round(sum(t["pnl"] for t in trades)/len(trades),2) if trades else 0.0,
        "net_pnl":round(equity-initial,2),"final_equity":round(equity,2),
        "max_drawdown_pct":round(max_dd,2),"sharpe":sharpe,"brier_score":brier,
        "coverage_signals":len(sigs),"fee_pct":fee_pct,"slippage_pct":slippage_pct,
        "breakeven_note":"For spot R:R 3:1, break-even win rate is 25% before fees. For binary 85% payout it is 54.05% — do not confuse the two.",
        "trades":trades[:200],
        "disclaimer":"In-sample replay on supplied candles. Past results do not prove future edge. Prior prototype BTC 5m directional win rate was 51.74% (below binary break-even)."}

def walk_forward(candles, folds=3, **kw):
    if not candles or len(candles)<300: return {"error":"need >=300 candles for walk-forward"}
    size=len(candles)//(folds+1); results=[]
    for f in range(folds):
        test=candles[size*(f+1):size*(f+2)] if f<folds-1 else candles[size*(f+1):]
        results.append({"fold":f+1,"candles":len(test),"result":run_backtest(test,**kw) if len(test)>=100 else {"error":"fold too small"}})
    return {"folds":results,"method":"chronological walk-forward, no shuffling, no leakage"}
