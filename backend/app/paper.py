"""Paper trading: virtual only, fees+slippage, fully separate from real money."""
import time
from .db import conn

def get_or_create_account(user_id):
    c=conn(); row=c.execute("SELECT * FROM paper_accounts WHERE user_id=?",(user_id,)).fetchone()
    if not row:
        c.execute("INSERT INTO paper_accounts(user_id,balance,equity,created_at) VALUES (?,?,?,?)",(user_id,10000.0,10000.0,int(time.time())))
        c.commit(); row=c.execute("SELECT * FROM paper_accounts WHERE user_id=?",(user_id,)).fetchone()
    c.close(); return dict(row)

def place_order(user_id, symbol, side, qty, price, sl=None, tp=None, fee_pct=0.1, slippage_pct=0.02):
    acct=get_or_create_account(user_id)
    eff=price*(1+slippage_pct/100) if side=="BUY" else price*(1-slippage_pct/100)
    fee=eff*qty*(fee_pct/100); notional=eff*qty
    if side=="BUY" and notional+fee>acct["balance"]:
        return {"error":"insufficient paper balance"}
    c=conn()
    c.execute("INSERT INTO paper_orders(account_id,symbol,side,qty,price,status,ts) VALUES (?,?,?,?,?,?,?)",(acct["id"],symbol,side,qty,eff,"filled",int(time.time())))
    c.execute("INSERT INTO paper_positions(account_id,symbol,side,qty,entry,sl,tp,status,opened_at) VALUES (?,?,?,?,?,?,?,'open',?)",(acct["id"],symbol,"LONG" if side=="BUY" else "SHORT",qty,eff,sl,tp,int(time.time())))
    new_bal=acct["balance"]-fee-(notional if side=="BUY" else 0)
    # For simplicity balance tracks cash after fee; equity updated on close / mark.
    c.execute("UPDATE paper_accounts SET balance=? WHERE id=?",(round(new_bal,2),acct["id"]))
    c.commit(); c.close()
    return {"status":"filled","effective_price":round(eff,6),"fee":round(fee,4),"account":get_or_create_account(user_id)}

def close_position(user_id, position_id, price, fee_pct=0.1):
    acct=get_or_create_account(user_id); c=conn()
    pos=c.execute("SELECT * FROM paper_positions WHERE id=? AND account_id=? AND status='open'",(position_id,acct["id"])).fetchone()
    if not pos: c.close(); return {"error":"open position not found"}
    pos=dict(pos)
    pnl=(price-pos["entry"])*pos["qty"] if pos["side"]=="LONG" else (pos["entry"]-price)*pos["qty"]
    fee=price*pos["qty"]*(fee_pct/100); pnl-=fee
    if pos["side"]=="LONG": cash_back=pos["entry"]*pos["qty"]+pnl
    else: cash_back=pnl  # short margin model simplified, documented
    c.execute("UPDATE paper_positions SET status='closed', pnl=?, closed_at=? WHERE id=?",(round(pnl,2),int(time.time()),position_id))
    c.execute("UPDATE paper_accounts SET balance=balance+? WHERE id=?",(round(cash_back,2),acct["id"]))
    c.commit(); c.close()
    return {"status":"closed","pnl":round(pnl,2),"account":get_or_create_account(user_id)}

def portfolio(user_id, prices=None):
    acct=get_or_create_account(user_id); c=conn()
    opens=[dict(r) for r in c.execute("SELECT * FROM paper_positions WHERE account_id=? AND status='open'",(acct["id"],)).fetchall()]
    closed=[dict(r) for r in c.execute("SELECT * FROM paper_positions WHERE account_id=? AND status='closed'",(acct["id"],)).fetchall()]
    c.close(); unreal=0.0
    prices=prices or {}
    for p in opens:
        cur=prices.get(p["symbol"])
        if cur: unreal+=(cur-p["entry"])*p["qty"] if p["side"]=="LONG" else (p["entry"]-cur)*p["qty"]
    realized=sum(p.get("pnl") or 0 for p in closed)
    return {"account":acct,"open_positions":opens,"closed_positions":closed,
            "realized_pnl":round(realized,2),"unrealized_pnl":round(unreal,2),
            "note":"Paper only — no real money, no broker connection."}
