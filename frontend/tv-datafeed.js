'use strict';
/* MarketPilot AI — Binance datafeed for TradingView Lightweight Charts.
 *
 * This module mirrors the TradingView Datafeed API contract (onReady /
 * searchSymbols / resolveSymbol / getBars / subscribeBars / unsubscribeBars)
 * so the chart layer can be swapped for Advanced Charts later IF TradingView
 * approval is ever obtained (see docs/TRADINGVIEW_INTEGRATION.md — currently
 * BLOCKED). Data comes ONLY from the Binance public API — our own authorised
 * source. Nothing here reads TradingView data, widgets, or ratings.
 */
(function(){
const BINANCE='https://data-api.binance.vision';
const WS_BASE='wss://stream.binance.com:9443/ws/';

/* MarketPilot timeframe -> datafeed resolution. Binance-native intervals map
   1:1; second resolutions are aggregated from real 1s klines ONLY. */
const RESOLUTIONS={
  '1s':'1s','5s':'5s','15s':'15s','30s':'30s',
  '1m':'1','5m':'5','15m':'15','30m':'30','1h':'60','4h':'240','1d':'1D','1w':'1W'};
const SUPPORTED=Object.values(RESOLUTIONS);
const SYMBOLS=['BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT','ADAUSDT','DOGEUSDT','LINKUSDT','LTCUSDT','PAXGUSDT'];

async function fetchJSON(url,ms=12000){const ctl=new AbortController();const t=setTimeout(()=>ctl.abort(),ms);try{const r=await fetch(url,{signal:ctl.signal});if(!r.ok)throw new Error('HTTP '+r.status);return await r.json()}finally{clearTimeout(t)}}

async function getBarsFor(symbol,tf,limit){
  limit=limit||300;
  if(['5s','15s','30s'].includes(tf)){
    const f=parseInt(tf);
    const raw=await fetchJSON(`${BINANCE}/api/v3/klines?symbol=${symbol}&interval=1s&limit=${Math.min(1000,limit*f)}`);
    const buckets=new Map();
    for(const k of raw){const bt=Math.floor(k[0]/(f*1000))*(f*1000);const b=buckets.get(bt);
      if(!b)buckets.set(bt,{time:bt/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4],volume:+k[5]});
      else{b.high=Math.max(b.high,+k[2]);b.low=Math.min(b.low,+k[3]);b.close=+k[4];b.volume+=+k[5]}}
    return[...buckets.values()].sort((a,b)=>a.time-b.time).slice(-limit);
  }
  const d=await fetchJSON(`${BINANCE}/api/v3/klines?symbol=${symbol}&interval=${tf}&limit=${limit}`);
  return d.map(k=>({time:k[0]/1000,open:+k[1],high:+k[2],low:+k[3],close:+k[4],volume:+k[5]}));
}

const subscriptions={}; // guid -> {ws, symbol, tf}

const Datafeed={
  /* TradingView Datafeed API shape (subset used by Lightweight Charts here). */
  onReady(callback){setTimeout(()=>callback({
    supported_resolutions:SUPPORTED, supports_search:true, supports_group_request:false,
    supports_marks:false, supports_timescale_marks:false,
    exchanges:[{value:'BINANCE',name:'Binance',desc:'Binance public API (our data source)'}],
    symbols_types:[{name:'crypto',value:'crypto'}]}),0)},
  async searchSymbols(userInput,exchange,symbolType,onResult){
    const q=(userInput||'').toUpperCase();
    onResult(SYMBOLS.filter(s=>s.includes(q)).map(s=>({symbol:s,full_name:'BINANCE:'+s,
      description:s+' / TetherUS',exchange:'BINANCE',ticker:s,type:'crypto'})))},
  resolveSymbol(symbolName,onResolved,onError){
    const s=(symbolName||'').split(':').pop().toUpperCase();
    if(!SYMBOLS.includes(s)){onError('unknown symbol');return}
    setTimeout(()=>onResolved({name:s,ticker:s,full_name:'BINANCE:'+s,description:s+' / TetherUS',
      type:'crypto',session:'24x7',timezone:'Etc/UTC',exchange:'BINANCE',listed_exchange:'BINANCE',
      format:'price',pricescale:100,minmov:1,has_intraday:true,has_seconds:true,
      supported_resolutions:SUPPORTED,volume_precision:2,data_status:'streaming'}),0)},
  /* getBars(symbolInfo, resolution, periodParams, onResult, onError) — TV contract.
     periodParams:{from,to,countBack,firstDataRequest}. Returns bars ascending. */
  async getBars(symbolInfo,resolution,periodParams,onResult,onError){
    const tf=Object.keys(RESOLUTIONS).find(k=>RESOLUTIONS[k]===resolution)||'5m';
    const symbol=(symbolInfo.ticker||symbolInfo.name||'BTCUSDT').toUpperCase();
    try{
      const bars=await getBarsFor(symbol,tf,Math.min(1000,(periodParams&&periodParams.countBack)||300));
      onResult(bars,{noData:bars.length===0});
    }catch(e){onError(String(e&&e.message||e))}},
  /* Live updates: Binance kline WebSocket for native intervals. For aggregated
     second resolutions the caller polls getBars (no fabricated sub-1s data). */
  subscribeBars(symbolInfo,resolution,onTick,listenerGuid){
    const tf=Object.keys(RESOLUTIONS).find(k=>RESOLUTIONS[k]===resolution)||'5m';
    const symbol=(symbolInfo.ticker||symbolInfo.name||'BTCUSDT').toUpperCase();
    if(['5s','15s','30s'].includes(tf)){subscriptions[listenerGuid]={ws:null,symbol,tf,poll:true};return}
    try{
      const ws=new WebSocket(`${WS_BASE}${symbol.toLowerCase()}@kline_${tf}`);
      ws.onmessage=ev=>{try{const k=JSON.parse(ev.data).k;if(!k)return;
        onTick({time:k.t/1000,open:+k.o,high:+k.h,low:+k.l,close:+k.c,volume:+k.v})}catch(e){}};
      ws.onerror=()=>{try{ws.close()}catch(e){}};
      subscriptions[listenerGuid]={ws,symbol,tf};
    }catch(e){subscriptions[listenerGuid]={ws:null,symbol,tf,poll:true}}
  },
  unsubscribeBars(listenerGuid){const s=subscriptions[listenerGuid];
    if(s&&s.ws){try{s.ws.close()}catch(e){}} delete subscriptions[listenerGuid]},

  /* Convenience helpers used directly by tv-chart.js */
  resolutions:RESOLUTIONS, supported:SUPPORTED, symbols:SYMBOLS, getBarsFor
};
window.MPDatafeed=Datafeed;
})();
