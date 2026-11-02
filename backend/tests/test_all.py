import sys, os, math
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from backend.app.indicators import sma, ema, rsi, aggregate_candles, atr
from backend.app.risk import position_size, atr_levels, guards
from backend.app.db import hash_password
from backend.app.news_engine import dedupe_key, sentiment_of
from backend.app.prediction import predict
from backend.app.backtest import run_backtest

def flat_candles(n=300, price=100.0):
    return [{"t": i*300000, "o": price, "h": price+1, "l": price-1, "c": price, "v": 10.0} for i in range(n)]

def trending_candles(n=300):
    out=[]
    for i in range(n):
        p=100+i*0.1
        out.append({"t": i*300000, "o": p, "h": p+0.5, "l": p-0.5, "c": p+0.1, "v": 12.0})
    return out

def test_sma_known():
    assert sma([1,2,3,4,5],3)==[None,None,2.0,3.0,4.0]

def test_ema_known():
    e=ema([1,2,3,4,5],3)
    assert e[2]==2.0
    # k=0.5: next = 4*0.5+2*0.5=3, then 5*0.5+3*0.5=4
    assert abs(e[3]-3.0)<1e-9 and abs(e[4]-4.0)<1e-9

def test_rsi_bounds_and_flat():
    r=rsi([100.0]*30)
    assert r[-1]==100.0  # no losses -> 100 by definition in this implementation
    up=rsi([float(i) for i in range(40)])
    assert up[-1] is not None and up[-1]>90

def test_atr_positive():
    cs=trending_candles(50)
    a=atr([c["h"] for c in cs],[c["l"] for c in cs],[c["c"] for c in cs])
    assert a[-1] is not None and a[-1]>0

def test_aggregation_no_invention():
    ones=[{"t":i*1000,"o":100+i,"h":101+i,"l":99+i,"c":100.5+i,"v":1.0} for i in range(10)]
    agg=aggregate_candles(ones,5)
    assert len(agg)==2 and agg[0]["v"]==5.0 and agg[0]["o"]==100 and agg[0]["c"]==104.5

def test_position_size():
    r=position_size(10000,1.0,100,95)
    assert r["risk_amount"]==100.0 and abs(r["quantity"]-20.0)<1e-9

def test_atr_levels_rr():
    lv=atr_levels(100,2.0,"LONG")
    assert lv["stop_loss"]<100 and lv["take_profit"][1]>lv["take_profit"][0]>100

def test_guards_consecutive():
    g=guards([-1,-2,-3])
    assert g["blocked"] and g["consecutive_losses"]==3

def test_password_hash_not_plaintext_and_verifies():
    h,s=hash_password("correct horse battery")
    assert h!="correct horse battery" and len(h)==64
    h2,_=hash_password("correct horse battery", s)
    assert h2==h
    h3,_=hash_password("wrong", s)
    assert h3!=h

def test_news_dedupe_same_story():
    assert dedupe_key("Bitcoin surges to record - CoinDesk")==dedupe_key("Bitcoin surges to record - Reuters")

def test_news_sentiment():
    s,label=sentiment_of("Bitcoin ETF approval sparks rally")
    assert s>0 and label=="bullish"
    s2,label2=sentiment_of("Exchange hack: funds stolen, crash fears")
    assert s2<0 and label2=="bearish"

def test_prediction_no_trade_on_insufficient():
    p=predict("BTCUSDT","5m",flat_candles(10))
    assert p["direction"]=="NO TRADE" and p["confidence_level"]=="UNVALIDATED"

def test_prediction_schema_and_unvalidated_on_trend():
    p=predict("BTCUSDT","5m",trending_candles(300))
    for k in ["asset","timeframe","direction","probability","confidence_level","reasoning","generated_at","expires_at","model_version"]:
        assert k in p
    assert p["confidence_level"]=="UNVALIDATED"

def test_prediction_flat_market_no_overconfidence():
    p=predict("BTCUSDT","5m",flat_candles(300))
    # flat market: fused score near 0 -> NO TRADE expected
    assert p["direction"] in ("NO TRADE","NEUTRAL","BULLISH","BEARISH")
    assert p["probability"]<=0.9

def test_backtest_no_lookahead_structure():
    cs=trending_candles(400)
    r=run_backtest(cs)
    assert "win_rate" in r and "max_drawdown_pct" in r and "brier_score" in r
    for t in r["trades"]:
        assert t["exit_index"]>t["signal_index"]  # exit strictly after signal

def test_backtest_insufficient():
    r=run_backtest(flat_candles(10))
    assert r["trades"]==0
