'use strict';
const B='https://data-api.binance.vision';
const fmt=x=>Number(x).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
function emaLast(v,p){if(v.length<p)return null;const k=2/(p+1);let e=v.slice(0,p).reduce((a,b)=>a+b,0)/p;for(let i=p;i<v.length;i++)e=v[i]*k+e*(1-k);return e}
async function main(){
  try{
    const syms=['BTCUSDT','ETHUSDT','SOLUSDT','BNBUSDT'];
    const rows=[];
    for(const s of syms){
      const t=await (await fetch(`${B}/api/v3/ticker/24hr?symbol=${s}`)).json();
      rows.push(`<div class="row"><span>${s}</span><span>$${fmt(t.lastPrice)} <span class="${+t.priceChangePercent>=0?'up':'down'}">${(+t.priceChangePercent).toFixed(2)}%</span></span></div>`);
    }
    document.getElementById('prices').innerHTML=rows.join('');
    const opps=[];
    for(const s of syms){
      const k=await (await fetch(`${B}/api/v3/klines?symbol=${s}&interval=5m&limit=120`)).json();
      const closes=k.map(x=>+x[4]);const price=closes[closes.length-1];
      const e50=emaLast(closes,50),e9=emaLast(closes,9),e21=emaLast(closes,21);
      let score=0;if(e50)score+=price>e50?22:-22;if(e9&&e21)score+=e9>e21?18:-18;
      opps.push({s,score,dir:score>=25?'BULLISH':score<=-25?'BEARISH':'NO TRADE'});
    }
    opps.sort((a,b)=>Math.abs(b.score)-Math.abs(a.score));
    document.getElementById('opps').innerHTML=opps.map(o=>`<div class="row"><span>${o.s}</span><span class="${o.dir==='BULLISH'?'up':o.dir==='BEARISH'?'down':''}">${o.dir} (${o.score})</span></div>`).join('');
  }catch(e){document.getElementById('prices').textContent='Data unavailable — check connection. Nothing is faked.'}
}
document.getElementById('openSite').addEventListener('click',()=>chrome.tabs.create({url:'https://khalidhasan11.github.io/marketpilot-ai/'}));
main();
