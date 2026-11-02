'use strict';
/* MarketPilot AI — 1-Second Live Mode.
 *
 * Streams REAL Binance trades (aggTrade WebSocket) for the selected symbol and
 * folds them into the CURRENT (forming) candle only: close = last trade price,
 * high/low expand, volume accumulates the real traded quantities received
 * since the bar was seeded. Nothing is interpolated, smoothed, or invented.
 *
 * Resilience: if the WebSocket delivers nothing within 5 s (some networks
 * silently drop WS), we fall back to 1-second REST polling of the real current
 * kline and label the indicator "(polling)". If WS trades later arrive, WS
 * wins again. One reconnect attempt is made on socket error/close first.
 *
 * Prediction integrity: this module NEVER touches closed candles or signals.
 * Markers/signals continue to compute on closed candles only (no repaint);
 * live ticks only repaint the forming bar's display.
 *
 * The pure bar-aggregation core (bucketStartMs / createBar / applyTrade) is
 * environment-free and unit-tested in tests/live1s.test.js.
 */

/* ================= pure core (also exported for Node tests) ================= */
const TF_SECONDS={'1s':1,'5s':5,'15s':15,'30s':30,'1m':60,'5m':300,'15m':900,
  '30m':1800,'1h':3600,'4h':14400,'1d':86400,'1w':604800};

function tfSecondsFor(tf){return TF_SECONDS[tf]||300}
function bucketStartMs(ms,tfSec){return Math.floor(ms/(tfSec*1000))*tfSec*1000}
function createBar(bucketMs,price,qty){
  return{time:bucketMs/1000,open:price,high:price,low:price,close:price,volume:qty||0}}
/* Fold one real trade into the forming bar.
 * Returns {bar, rolled, closedBar}: when the trade belongs to a NEWER bucket,
 * the old bar is returned as closedBar and a fresh bar starts at the trade's
 * own bucket (open = that trade's price — gaps are left as gaps, never filled).
 * Trades from an OLDER bucket (late/out-of-order) are ignored. */
function applyTrade(bar,price,qty,tradeMs,tfSec){
  if(!bar)return{bar:createBar(bucketStartMs(tradeMs,tfSec),price,qty),rolled:false,closedBar:null};
  const b=bucketStartMs(tradeMs,tfSec);
  if(b>bar.time*1000)return{bar:createBar(b,price,qty),rolled:true,closedBar:bar};
  if(b<bar.time*1000)return{bar,rolled:false,closedBar:null};
  bar.close=price;
  if(price>bar.high)bar.high=price;
  if(price<bar.low)bar.low=price;
  bar.volume+=(qty||0);
  return{bar,rolled:false,closedBar:null};
}

/* ================= browser controller ================= */
const Live1sCore={TF_SECONDS,tfSecondsFor,bucketStartMs,createBar,applyTrade};
if(typeof module!=='undefined'&&module.exports)module.exports=Live1sCore;

if(typeof window!=='undefined'){
(function(){
const WS_BASE='wss://stream.binance.com:9443/ws/'; // same base as tv-datafeed.js
const REST='https://data-api.binance.vision';       // same REST base as app.js
const $=id=>document.getElementById(id);

let enabled=true;
try{enabled=localStorage.getItem('mp_live1s')!=='0'}catch(e){}
let mode='off';              // 'ws' | 'poll' | 'off'
let ws=null,wsSymbol=null,gotMsg=false,reconnectTried=false,intentionalClose=false;
let watchdog=null,pollTimer=null,flushTimer=null,countTimer=null;
let curBar=null,seededFor=null,dirty=false,lastPrice=null,lastDir=0,lastHeaderAt=0;

function ctx(){const s=window.MPState;if(!s)return null;
  return{symbol:s.symbol,tf:s.tf,tfSec:tfSecondsFor(s.tf),
    lastCandle:s.candles&&s.candles.length?s.candles[s.candles.length-1]:null}}
function seed(force){
  const c=ctx();if(!c)return;
  const key=c.symbol+'|'+c.tf;
  if(!force&&seededFor===key&&curBar)return;
  seededFor=key;
  if(c.lastCandle){const lc=c.lastCandle;
    curBar={time:Math.floor(lc.t/1000),open:lc.o,high:lc.h,low:lc.l,close:lc.c,volume:lc.v};
    lastPrice=lc.c;
  }else curBar=null;
}
function setIndicator(){
  const el=$('liveInd');if(!el)return;
  if(!enabled){el.textContent='○ Live 1s off';el.className='live-ind off';return}
  el.textContent=mode==='poll'?'● LIVE 1s (polling)':'● LIVE 1s';
  el.className='live-ind '+(mode==='poll'?'poll':'on');
}
function flashPrice(price){
  /* Header at most 1 update/sec; direction is measured against the last
     price actually SHOWN (lastPrice is owned by this function). */
  const now=Date.now();
  if(lastPrice!==null&&price===lastPrice)return;
  if(now-lastHeaderAt<1000)return;
  const dir=lastPrice===null?0:(price>lastPrice?1:-1);
  lastPrice=price;lastHeaderAt=now;lastDir=dir;
  for(const id of['livePrice','price']){
    const el=$(id);if(!el)continue;
    el.textContent='$'+Number(price).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
    if(dir!==0){el.classList.remove('flash-up','flash-down');void el.offsetWidth;
      el.classList.add(dir>0?'flash-up':'flash-down')}
  }
}
function onTrade(price,qty,tradeMs){
  const c=ctx();if(!c)return;
  seed(false);
  const r=applyTrade(curBar,price,qty,tradeMs,c.tfSec);
  curBar=r.bar;dirty=true;
  flashPrice(price);
}
/* 4 chart renders/sec max — the trades themselves are real, only the
   repaint is throttled so the UI stays smooth. */
function flush(){
  if(!dirty||!curBar)return;dirty=false;
  if(typeof window.MPHandleLiveBar==='function')
    window.MPHandleLiveBar({time:curBar.time,open:curBar.open,high:curBar.high,
      low:curBar.low,close:curBar.close,volume:curBar.volume});
}
function stopPolling(){if(pollTimer){clearInterval(pollTimer);pollTimer=null}}
async function pollOnce(){
  const c=ctx();if(!c||!enabled)return;
  try{
    let bar=null;
    if(window.MPDatafeed&&window.MPDatafeed.getBarsFor){
      const bars=await window.MPDatafeed.getBarsFor(c.symbol,c.tf,2);
      if(bars&&bars.length)bar=bars[bars.length-1];
    }
    if(!bar){ // direct fallback: ticker price + current native/1s kline
      const t=await(await fetch(`${REST}/api/v3/ticker/price?symbol=${c.symbol}`)).json();
      const iv=['5s','15s','30s'].includes(c.tf)?'1s':c.tf;
      const ks=await(await fetch(`${REST}/api/v3/klines?symbol=${c.symbol}&interval=${iv}&limit=1`)).json();
      if(ks&&ks.length){const k=ks[0];bar={time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+t.price,volume:+k[5]}}
      else if(t&&t.price){onTrade(+t.price,0,Date.now());return}
    }
    if(bar&&enabled){curBar={time:bar.time,open:bar.open,high:bar.high,low:bar.low,close:bar.close,volume:bar.volume};
      seededFor=c.symbol+'|'+c.tf;dirty=true;flashPrice(bar.close)}
  }catch(e){/* keep last bar; next tick retries */}
}
function startPolling(){
  if(pollTimer||!enabled)return;
  mode='poll';setIndicator();
  pollOnce();pollTimer=setInterval(pollOnce,1000);
}
function closeWs(){intentionalClose=true;
  if(ws){try{ws.close()}catch(e){}ws=null}
  if(watchdog){clearTimeout(watchdog);watchdog=null}}
function armWatchdog(){
  if(watchdog)clearTimeout(watchdog);
  watchdog=setTimeout(()=>{if(enabled&&!gotMsg)startPolling()},5000);
}
function subscribe(){
  closeWs();stopPolling();if(!enabled){mode='off';setIndicator();return}
  const c=ctx();if(!c)return;
  mode='ws';gotMsg=false;seed(true);setIndicator();
  intentionalClose=false;
  try{
    ws=new WebSocket(`${WS_BASE}${c.symbol.toLowerCase()}@aggTrade`);wsSymbol=c.symbol;
    ws.onmessage=ev=>{
      gotMsg=true;reconnectTried=false;
      if(pollTimer){stopPolling();mode='ws';setIndicator()}  // WS wins over polling
      try{const d=JSON.parse(ev.data);if(d&&d.p)onTrade(+d.p,+d.q||0,d.T||Date.now())}catch(e){}
    };
    ws.onerror=()=>{try{ws.close()}catch(e){}};
    ws.onclose=()=>{
      if(intentionalClose||!enabled)return;
      if(!reconnectTried){reconnectTried=true;setTimeout(()=>{if(enabled)subscribe()},1000)}
      else startPolling();
    };
  }catch(e){startPolling()}
  armWatchdog();
}
function countdownTick(){
  const el=$('liveCountdown');if(!el)return;
  if(!enabled){el.textContent='';return}
  const c=ctx();if(!c){el.textContent='';return}
  const now=Date.now(),span=c.tfSec*1000;
  const rem=(Math.floor(now/span)+1)*span-now;
  if(c.tfSec===1)el.textContent=`· closes in ${(rem/1000).toFixed(1)}s`;
  else if(rem<60000)el.textContent=`· closes in ${Math.ceil(rem/1000)}s`;
  else el.textContent=`· closes in ${Math.floor(rem/60000)}m ${Math.ceil((rem%60000)/1000)}s`;
}
function startTimers(){
  if(!flushTimer)flushTimer=setInterval(flush,250);
  if(!countTimer)countTimer=setInterval(countdownTick,250);
}
function setEnabled(on){
  enabled=on;
  try{localStorage.setItem('mp_live1s',on?'1':'0')}catch(e){}
  const t=$('live1sToggle');if(t)t.checked=on;
  if(on){seed(true);subscribe()}
  else{closeWs();stopPolling();mode='off'}
  setIndicator();countdownTick();
  /* Let the chart layer restore/relinquish its own kline subscription. */
  if(window.MPTV&&window.MPTV.resetSubscription)window.MPTV.resetSubscription();
  if(typeof window.renderChart==='function')window.renderChart();
}

window.MPLive1s={
  isOn:()=>enabled,
  mode:()=>mode,
  resubscribe:()=>{seed(true);if(enabled)subscribe()},
  setEnabled,
  _test:{onTrade,core:Live1sCore,getBar:()=>curBar}
};

window.addEventListener('load',()=>{
  const t=$('live1sToggle');
  if(t){t.checked=enabled;t.addEventListener('change',()=>setEnabled(t.checked))}
  setIndicator();startTimers();
  if(enabled)subscribe();else mode='off',setIndicator();
});
})();
}
