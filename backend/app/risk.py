"""Risk management: ATR stops, TP levels, R:R, position sizing, guards."""

def atr_levels(entry, atr_value, direction, swing_low=None, swing_high=None, rr=(1.5,3.0)):
    """direction: 'LONG'/'SHORT'. Stop = max(1.5*ATR, swing) logic, documented."""
    if entry is None or not atr_value or atr_value<=0: return None
    stop_dist=1.5*atr_value
    if direction=="LONG":
        sl=entry-stop_dist
        if swing_low is not None and swing_low<entry: sl=min(sl, swing_low) if swing_low<entry-stop_dist*0.5 else sl
        # keep swing stop only if it widens sensibly (<=3x ATR)
        if swing_low is not None and 0 < entry-swing_low <= 3*atr_value: sl=swing_low
        risk=entry-sl
        tps=[entry+risk*r for r in rr]
    else:
        sl=entry+stop_dist
        if swing_high is not None and 0 < swing_high-entry <= 3*atr_value: sl=swing_high
        risk=sl-entry
        tps=[entry-risk*r for r in rr]
    if risk<=0: return None
    return {"entry":round(entry,6),"stop_loss":round(sl,6),"take_profit":[round(t,6) for t in tps],
            "risk_per_unit":round(risk,6),"risk_reward":rr[1]}

def position_size(account_balance, risk_pct, entry, stop_loss):
    if not account_balance or risk_pct is None or entry==stop_loss: return None
    risk_amount=account_balance*(risk_pct/100.0)
    per_unit=abs(entry-stop_loss)
    qty=risk_amount/per_unit if per_unit>0 else 0
    return {"risk_amount":round(risk_amount,2),"quantity":qty,"notional":round(qty*entry,2),
            "risk_pct":risk_pct,"note":"Conservative default 1% risk. Never increase risk to recover losses."}

def guards(recent_outcomes, max_consecutive_losses=3, max_drawdown_pct=10.0, peak=None, current=None):
    """recent_outcomes: list of pnl floats, oldest->newest."""
    consec=0
    for p in reversed(recent_outcomes):
        if p<0: consec+=1
        else: break
    dd=None
    if peak and current is not None and peak>0: dd=(peak-current)/peak*100
    blocked=[]
    if consec>=max_consecutive_losses: blocked.append(f"{consec} consecutive losses >= limit {max_consecutive_losses}")
    if dd is not None and dd>=max_drawdown_pct: blocked.append(f"Drawdown {dd:.1f}% >= limit {max_drawdown_pct}%")
    return {"consecutive_losses":consec,"drawdown_pct":round(dd,2) if dd is not None else None,
            "blocked":bool(blocked),"reasons":blocked}
