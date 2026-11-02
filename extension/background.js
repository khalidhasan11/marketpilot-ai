'use strict';
// MarketPilot AI service worker: periodic BTC check, optional notification on strong score.
// No API keys. No page manipulation. No Quotex interaction of any kind.
chrome.runtime.onInstalled.addListener(()=>{chrome.alarms.create('mp-check',{periodInMinutes:15})});
chrome.alarms.onAlarm.addListener(async alarm=>{
  if(alarm.name!=='mp-check')return;
  const {mpNotify}=await chrome.storage.local.get('mpNotify');
  if(!mpNotify)return;
  try{
    const k=await (await fetch('https://data-api.binance.vision/api/v3/klines?symbol=BTCUSDT&interval=5m&limit=120')).json();
    const closes=k.map(x=>+x[4]);const price=closes[closes.length-1];
    const ema=(p)=>{const kk=2/(p+1);let e=closes.slice(0,p).reduce((a,b)=>a+b,0)/p;for(let i=p;i<closes.length;i++)e=closes[i]*kk+e*(1-kk);return e};
    const score=(price>ema(50)?22:-22)+(ema(9)>ema(21)?18:-18);
    if(Math.abs(score)>=40)chrome.notifications.create({type:'basic',iconUrl:'',title:'MarketPilot AI — BTC score '+score,message:'Direction bias '+(score>0?'BULLISH':'BEARISH')+' (UNVALIDATED). Open the dashboard to verify.'});
  }catch(e){/* silent: never fake a notification */}
});
