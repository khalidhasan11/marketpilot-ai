'use strict';
/* MarketPilot AI — primary chart: TradingView Lightweight Charts (Apache-2.0)
 * fed EXCLUSIVELY by our own Binance datafeed (tv-datafeed.js).
 * Markers and price lines come from MarketPilot's independent EMA-cross+RSI
 * logic (computeSignals in app.js) running on Binance candles — never from
 * any TradingView rating, widget, or summary. If the CDN library fails to
 * load, app.js automatically keeps using the built-in canvas chart.
 */
(function(){
const DARK={layout:{background:{color:'#0a0f1a'},textColor:'#8fa3c0',attributionLogo:true},
  grid:{vertLines:{color:'#1b2740'},horzLines:{color:'#1b2740'}},
  rightPriceScale:{borderColor:'#22304a'},timeScale:{borderColor:'#22304a',timeVisible:true,secondsVisible:true}};
let chart=null,candleSeries=null,volSeries=null,ema20Series=null,ema50Series=null,markersPlugin=null;
let curKey=null,priceLines=[],lastBarTime=0,subGuid=null;

function available(){return typeof window.LightweightCharts!=='undefined'&&!!window.MPDatafeed}
function toBars(candles){return candles.map(k=>({time:Math.floor(k.t/1000),open:k.o,high:k.h,low:k.l,close:k.c,volume:k.v}))}
function emaLine(candles,period,color,width){
  const closes=candles.map(k=>k.c);const e=emaA(closes,period);const out=[];
  for(let i=0;i<candles.length;i++)if(e[i]!=null)out.push({time:Math.floor(candles[i].t/1000),value:e[i]});
  return out}

function ensureChart(){
  if(chart||!available())return available();
  const el=document.getElementById('lwcChart');if(!el)return false;
  const LC=window.LightweightCharts;
  chart=LC.createChart(el,Object.assign({width:el.clientWidth||900,height:360},DARK));
  candleSeries=chart.addSeries(LC.CandlestickSeries,{upColor:'#22c55e',downColor:'#ef4444',borderVisible:false,wickUpColor:'#22c55e',wickDownColor:'#ef4444'});
  volSeries=chart.addSeries(LC.HistogramSeries,{priceFormat:{type:'volume'},priceScaleId:''});
  chart.priceScale('').applyOptions({scaleMargins:{top:0.82,bottom:0}});
  ema20Series=chart.addSeries(LC.LineSeries,{color:'#38bdf8',lineWidth:1,priceLineVisible:false,lastValueVisible:false});
  ema50Series=chart.addSeries(LC.LineSeries,{color:'#f59e0b',lineWidth:1,priceLineVisible:false,lastValueVisible:false});
  markersPlugin=LC.createSeriesMarkers(candleSeries,[]);
  window.addEventListener('resize',()=>{if(chart&&el.clientWidth)chart.applyOptions({width:el.clientWidth})});
  return true;
}

function setPriceLines(open){
  if(!candleSeries)return;
  for(const pl of priceLines){try{candleSeries.removePriceLine(pl)}catch(e){}}
  priceLines=[];
  if(!open)return;
  const mk=(price,color,title)=>priceLines.push(candleSeries.createPriceLine({price,color,lineWidth:1,lineStyle:window.LightweightCharts.LineStyle.Dashed,axisLabelVisible:true,title}));
  mk(open.entry,'#94a3b8','ENTRY');mk(open.sl,'#ef4444','SL');mk(open.tp,'#22c55e','TP');
}

function markersFor(candles){
  const closed=candles.slice(0,-1);if(closed.length<40||typeof computeSignals!=='function')return{markers:[],open:null};
  const sig=computeSignals(closed);const out=[];
  for(const ev of sig.events){const cd=closed[ev.i];if(!cd)continue;const t=Math.floor(cd.t/1000);
    if(ev.type==='BUY')out.push({time:t,position:'belowBar',shape:'arrowUp',color:'#22c55e',text:'BUY'});
    else if(ev.type==='SELL')out.push({time:t,position:'aboveBar',shape:'arrowDown',color:'#ef4444',text:'SELL'});
    else if(ev.type==='TP')out.push({time:t,position:'aboveBar',shape:'circle',color:'#16a34a',text:'TP'});
    else if(ev.type==='SL')out.push({time:t,position:'belowBar',shape:'circle',color:'#dc2626',text:'SL'})}
  out.sort((a,b)=>a.time-b.time);
  return{markers:out,open:sig.open};
}

async function render(state){
  if(!ensureChart())return false;
  document.getElementById('lwcChart').style.display='block';
  const cv=document.getElementById('chart');if(cv)cv.style.display='none';
  const tag=document.getElementById('chartEngine');if(tag)tag.textContent='Chart engine: TradingView Lightweight Charts (our Binance data) · EMA 20/50 · markers = independent EMA 5/13 + RSI logic';
  const key=state.symbol+'|'+state.tf;
  const bars=toBars(state.candles);
  if(!bars.length)return true;
  if(key!==curKey){
    curKey=key;lastBarTime=0;
    candleSeries.setData(bars);
    volSeries.setData(bars.map(b=>({time:b.time,value:b.volume,color:b.close>=b.open?'rgba(34,197,94,0.45)':'rgba(239,68,68,0.45)'})));
    ema20Series.setData(emaLine(state.candles,20));ema50Series.setData(emaLine(state.candles,50));
    const m=markersFor(state.candles);markersPlugin.setMarkers(m.markers);setPriceLines(m.open);
    chart.timeScale().scrollToRealTime();
    if(subGuid){window.MPDatafeed.unsubscribeBars(subGuid);subGuid=null}
    /* 1-Second Live Mode owns the forming bar while it is ON — don't let the
       kline subscription fight it. When Live 1s is off, subscribe as before. */
    const liveOn=window.MPLive1s&&window.MPLive1s.isOn&&window.MPLive1s.isOn();
    if(!liveOn){
      subGuid='mp-'+Date.now();
      const res=window.MPDatafeed.resolutions[state.tf]||'5';
      window.MPDatafeed.subscribeBars({ticker:state.symbol,name:state.symbol},res,bar=>{
        if(!candleSeries||bar.time<lastBarTime)return;lastBarTime=Math.max(lastBarTime,bar.time);
        try{candleSeries.update(bar);volSeries.update({time:bar.time,value:bar.volume,color:bar.close>=bar.open?'rgba(34,197,94,0.45)':'rgba(239,68,68,0.45)'})}catch(e){}
      },subGuid);
    }
  }else{
    const lastBar=bars[bars.length-1];
    if(lastBar.time>=lastBarTime){lastBarTime=lastBar.time;
      try{candleSeries.update(lastBar);volSeries.update({time:lastBar.time,value:lastBar.volume,color:lastBar.close>=lastBar.open?'rgba(34,197,94,0.45)':'rgba(239,68,68,0.45)'})}catch(e){}}
  }
  return true;
}

/* ---------- asset comparison: normalised % lines, own Binance data ---------- */
let cmpChart=null,cmpSeries={};
async function renderComparison(){
  if(!available()){const n=document.getElementById('cmpNote');if(n)n.textContent='Lightweight Charts failed to load — comparison unavailable, everything else still works.';return}
  const el=document.getElementById('compareChart');if(!el)return;
  const LC=window.LightweightCharts;
  if(!cmpChart){
    cmpChart=LC.createChart(el,Object.assign({width:el.clientWidth||900,height:340},DARK));
    window.addEventListener('resize',()=>{if(cmpChart&&el.clientWidth)cmpChart.applyOptions({width:el.clientWidth})});
  }
  const picks=[['cmpA','#38bdf8'],['cmpB','#f59e0b'],['cmpC','#a78bfa']];
  for(const[id,color]of picks){
    const sel=document.getElementById(id);if(!sel)continue;const sym=sel.value;
    if(cmpSeries[id]){try{cmpChart.removeSeries(cmpSeries[id])}catch(e){}delete cmpSeries[id]}
    if(!sym)continue;
    try{
      const bars=await window.MPDatafeed.getBarsFor(sym,'1h',300);if(!bars.length)continue;
      const base=bars[0].close;const s=cmpChart.addSeries(LC.LineSeries,{color,lineWidth:2,priceLineVisible:false,title:sym});
      s.setData(bars.map(b=>({time:b.time,value:(b.close/base-1)*100})));
      cmpSeries[id]=s;
    }catch(e){}
  }
  if(cmpChart)cmpChart.timeScale().fitContent();
}

/* ---------- watchlist sparklines: mini Lightweight Charts, own data ---------- */
const sparkCharts={};
async function renderSparklines(symbols){
  if(!available())return;
  const LC=window.LightweightCharts;
  for(const sym of symbols){
    const el=document.getElementById('spark-'+sym);if(!el)continue;
    try{
      const bars=await window.MPDatafeed.getBarsFor(sym,'1h',48);if(!bars.length)continue;
      if(sparkCharts[sym]){try{sparkCharts[sym].remove()}catch(e){}delete sparkCharts[sym]}
      el.innerHTML='';
      const ch=LC.createChart(el,{width:120,height:40,layout:{background:{color:'transparent'},textColor:'transparent',attributionLogo:false},
        grid:{vertLines:{visible:false},horzLines:{visible:false}},rightPriceScale:{visible:false},timeScale:{visible:false},crosshair:{mode:2}});
      const up=bars[bars.length-1].close>=bars[0].close;
      const s=ch.addSeries(LC.LineSeries,{color:up?'#22c55e':'#ef4444',lineWidth:1,priceLineVisible:false,lastValueVisible:false,crosshairMarkerVisible:false});
      s.setData(bars.map(b=>({time:b.time,value:b.close})));ch.timeScale().fitContent();
      sparkCharts[sym]=ch;
    }catch(e){}
  }
}

/* Live 1s: repaint the forming bar from a real trade/poll update. */
function updateLiveBar(bar){
  if(!candleSeries||!bar||bar.time<lastBarTime)return;
  lastBarTime=Math.max(lastBarTime,bar.time);
  try{candleSeries.update(bar);volSeries.update({time:bar.time,value:bar.volume,color:bar.close>=bar.open?'rgba(34,197,94,0.45)':'rgba(239,68,68,0.45)'})}catch(e){}
}
/* Forget the current key/subscription so the next render() re-seeds and
   re-subscribes (used when Live 1s is toggled on/off). */
function resetSubscription(){
  curKey=null;
  if(subGuid&&window.MPDatafeed){try{window.MPDatafeed.unsubscribeBars(subGuid)}catch(e){}subGuid=null}
}

window.MPTV={get active(){return available()},render,renderComparison,renderSparklines,updateLiveBar,resetSubscription};
})();
