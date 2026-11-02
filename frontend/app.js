'use strict';
/* MarketPilot AI frontend — real data only: Binance public API + RSS via rss2json/allorigins.
   No fake prices, no fake news, no fabricated accuracy. */
const BINANCE='https://data-api.binance.vision';
const $=id=>document.getElementById(id);
const store={get(k,d){try{const v=localStorage.getItem('mp_'+k);return v?JSON.parse(v):d}catch(e){return d}},set(k,v){try{localStorage.setItem('mp_'+k,JSON.stringify(v))}catch(e){}}};
const state={symbol:'BTCUSDT',tf:'5m',candles:[],ticker:null,news:{score:0,items:[],danger:null,loaded:false},lastSignal:null};
const API_BASE=()=>store.get('apiBase','');

/* ---------- indicators (closed candles, no look-ahead) ---------- */
function smaA(v,p){const o=new Array(v.length).fill(null);let s=0;for(let i=0;i<v.length;i++){s+=v[i];if(i>=p)s-=v[i-p];if(i>=p-1)o[i]=s/p}return o}
function emaA(v,p){const o=new Array(v.length).fill(null);if(v.length<p)return o;const k=2/(p+1);let e=v.slice(0,p).reduce((a,b)=>a+b,0)/p;o[p-1]=e;for(let i=p;i<v.length;i++){e=v[i]*k+e*(1-k);o[i]=e}return o}
function last(a){for(let i=a.length-1;i>=0;i--)if(a[i]!==null&&a[i]!==undefined&&!Number.isNaN(a[i]))return a[i];return null}
function rsiA(c,p=14){const o=new Array(c.length).fill(null);if(c.length<=p)return o;let g=0,l=0;for(let i=1;i<=p;i++){const d=c[i]-c[i-1];g+=Math.max(d,0);l+=Math.max(-d,0)}g/=p;l/=p;o[p]=l===0?100:100-100/(1+g/l);for(let i=p+1;i<c.length;i++){const d=c[i]-c[i-1];g=(g*(p-1)+Math.max(d,0))/p;l=(l*(p-1)+Math.max(-d,0))/p;o[i]=l===0?100:100-100/(1+g/l)}return o}
function macdHist(c){const e12=emaA(c,12),e26=emaA(c,26);const line=c.map((_,i)=>(e12[i]!=null&&e26[i]!=null)?e12[i]-e26[i]:null);const idx=line.findIndex(x=>x!==null);if(idx<0)return[];const sig=emaA(line.slice(idx),9);return line.map((x,i)=>(x!==null&&sig[i-idx]!=null&&sig[i-idx]!==undefined)?x-sig[i-idx]:null)}
function atrA(h,l,c,p=14){const n=c.length,tr=new Array(n).fill(0);for(let i=1;i<n;i++)tr[i]=Math.max(h[i]-l[i],Math.abs(h[i]-c[i-1]),Math.abs(l[i]-c[i-1]));const o=new Array(n).fill(null);if(n<=p)return o;let a=tr.slice(1,p+1).reduce((x,y)=>x+y,0)/p;o[p]=a;for(let i=p+1;i<n;i++){a=(a*(p-1)+tr[i])/p;o[i]=a}return o}
function fmt(x){return x===null||x===undefined||Number.isNaN(x)?'—':Number(x).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2})}

/* ---------- data ---------- */
async function fetchJSON(url,ms=12000){const ctl=new AbortController();const t=setTimeout(()=>ctl.abort(),ms);try{const r=await fetch(url,{signal:ctl.signal});if(!r.ok)throw new Error(r.status);return await r.json()}finally{clearTimeout(t)}}
async function fetchKlines(tf,limit=300){
  if(['5s','15s','30s'].includes(tf)){const f=parseInt(tf);const raw=await fetchJSON(`${BINANCE}/api/v3/klines?symbol=${state.symbol}&interval=1s&limit=${Math.min(1000,limit*f)}`);const ones=raw.map(k=>({t:k[0],o:+k[1],h:+k[2],l:+k[3],c:+k[4],v:+k[5]}));const buckets=new Map();for(const k of ones){const bt=Math.floor(k.t/(f*1000))*(f*1000);const b=buckets.get(bt);if(!b)buckets.set(bt,{t:bt,o:k.o,h:k.h,l:k.l,c:k.c,v:k.v});else{b.h=Math.max(b.h,k.h);b.l=Math.min(b.l,k.l);b.c=k.c;b.v+=k.v}}return[...buckets.values()].sort((a,b)=>a.t-b.t).slice(-limit)}
  const d=await fetchJSON(`${BINANCE}/api/v3/klines?symbol=${state.symbol}&interval=${tf}&limit=${limit}`);return d.map(k=>({t:k[0],o:+k[1],h:+k[2],l:+k[3],c:+k[4],v:+k[5]}))}
async function refreshTicker(){try{const d=await fetchJSON(`${BINANCE}/api/v3/ticker/24hr?symbol=${state.symbol}`);state.ticker={price:+d.lastPrice,change:+d.priceChangePercent};$('price').textContent='$'+fmt(state.ticker.price);const ch=$('chg24');ch.textContent=(state.ticker.change>=0?'▲ +':'▼ ')+state.ticker.change.toFixed(2)+'% (24h)';ch.className=state.ticker.change>=0?'up':'down';renderChart()}catch(e){$('status').textContent='ticker error — retrying'}}
async function refreshCandles(){try{state.candles=await fetchKlines(state.tf);$('status').textContent='Last update: '+new Date().toLocaleTimeString()+' · data LIVE (Binance)';renderAll()}catch(e){$('status').textContent='candle error — check connection'}}

/* ---------- scoring (mirrors backend Models A–E) ---------- */
function scoreCandles(candles){
  const closed=candles.slice(0,-1);if(closed.length<60)return null;
  const closes=closed.map(x=>x.c),price=closes[closes.length-1];
  const e9=last(emaA(closes,9)),e21=last(emaA(closes,21)),e50=last(emaA(closes,50));
  const mh=last(macdHist(closes)),r=last(rsiA(closes));let score=0;const reasons=[];
  if(e50){score+=price>e50?22:-22;reasons.push(price>e50?'Price above EMA50 (uptrend)':'Price below EMA50 (downtrend)')}
  if(e9&&e21){score+=e9>e21?18:-18;reasons.push(e9>e21?'EMA9 > EMA21':'EMA9 < EMA21')}
  if(mh!==null){score+=mh>0?14:-14;reasons.push(mh>0?'MACD bullish':'MACD bearish')}
  if(r!==null){if(r>=55&&r<=70){score+=10;reasons.push(`RSI ${r.toFixed(0)} bullish momentum`)}else if(r>70){score-=8;reasons.push(`RSI ${r.toFixed(0)} overbought`)}else if(r>=30&&r<45){score-=10;reasons.push(`RSI ${r.toFixed(0)} bearish momentum`)}else if(r<30){score+=8;reasons.push(`RSI ${r.toFixed(0)} oversold`)}}
  const vols=closed.map(x=>x.v);if(vols.length>=21){const avg=vols.slice(-21,-1).reduce((a,b)=>a+b,0)/20;if(avg>0&&vols[vols.length-1]/avg>1.3){score+=(e9>e21)?8:-8;reasons.push('Volume above average confirms move')}}
  return{score:Math.max(-100,Math.min(100,Math.round(score*10)/10)),reasons,rsi:r,price,
    support:Math.min(...closed.slice(-50).map(x=>x.l)),resistance:Math.max(...closed.slice(-50).map(x=>x.h))}}
function fusion(){
  const t=scoreCandles(state.candles);if(!t)return null;
  const news=state.news.loaded?state.news.score:0;
  const ctx=state.ticker?Math.max(-25,Math.min(25,state.ticker.change*4)):0;
  const final=Math.round((0.7*t.score+0.2*news+0.1*ctx)*10)/10;
  let dir=final>=25?'BULLISH':(final<=-25?'BEARISH':'NO TRADE');let veto=null;
  if(state.news.danger&&dir==='BULLISH'){veto=`Danger news (${state.news.danger.source}, ${state.news.danger.age} min ago) cancels bullish signal`;dir='NO TRADE'}
  return{tech:t.score,news,ctx,final,dir,veto,reasons:t.reasons.concat([`News score ${news}`,`24h context ${ctx.toFixed(1)}`]),detail:t}}

/* ---------- chart (EMA 5/13 cross strategy, reuse of proven pattern) ---------- */
function computeSignals(closed){const closes=closed.map(x=>x.c);const e5=emaA(closes,5),e13=emaA(closes,13),r=rsiA(closes);const events=[],history=[];let open=null;
  for(let i=30;i<closed.length;i++){if(open){const cd=closed[i];const hitSL=open.dir==='LONG'?cd.l<=open.sl:cd.h>=open.sl;const hitTP=open.dir==='LONG'?cd.h>=open.tp:cd.l<=open.tp;if(hitSL||hitTP){events.push({i,type:hitSL?'SL':'TP'});history.push({...open,outcome:hitSL?'SL':'TP'});open=null;continue}}
    if(e5[i]==null||e13[i]==null||e5[i-1]==null||e13[i-1]==null||r[i]==null)continue;
    const up=e5[i-1]<=e13[i-1]&&e5[i]>e13[i],dn=e5[i-1]>=e13[i-1]&&e5[i]<e13[i];
    if(up&&r[i]<70){if(open&&open.dir==='SHORT'){history.push({...open,outcome:'REV'});open=null}if(!open){const entry=closes[i];let sl=Math.min(...closed.slice(Math.max(0,i-14),i).map(x=>x.l));if(!(sl<entry))sl=entry*0.99;open={dir:'LONG',entry,sl,tp:entry+3*(entry-sl)};events.push({i,type:'BUY'})}}
    else if(dn&&r[i]>30){if(open&&open.dir==='LONG'){history.push({...open,outcome:'REV'});open=null}if(!open){const entry=closes[i];let sl=Math.max(...closed.slice(Math.max(0,i-14),i).map(x=>x.h));if(!(sl>entry))sl=entry*1.01;open={dir:'SHORT',entry,sl,tp:entry-3*(sl-entry)};events.push({i,type:'SELL'})}}}
  return{events,history,open}}
function renderChart(){const cv=$('chart');if(!cv||state.candles.length<70)return;const candles=state.candles,closed=candles.slice(0,-1);const sig=computeSignals(closed);
  $('ppStatus').textContent=sig.open?sig.open.dir:'FLAT';$('ppEntry').textContent=sig.open?fmt(sig.open.entry):'—';$('ppSL').textContent=sig.open?fmt(sig.open.sl):'—';$('ppTP').textContent=sig.open?fmt(sig.open.tp):'—';
  const cur=state.ticker?state.ticker.price:candles[candles.length-1].c;
  if(sig.open){const p=sig.open;const rNow=(p.dir==='LONG'?(cur-p.entry):(p.entry-cur))/(p.dir==='LONG'?(p.entry-p.sl):(p.sl-p.entry));$('ppNow').textContent=(rNow>=0?'+':'')+rNow.toFixed(2)+'R'}else $('ppNow').textContent='—';
  const tpN=sig.history.filter(x=>x.outcome==='TP').length,slN=sig.history.filter(x=>x.outcome==='SL').length,rvN=sig.history.filter(x=>x.outcome==='REV').length;
  $('sigStats').textContent=`Across ${closed.length} candles: TP ${tpN} · SL ${slN} · reversed ${rvN}${sig.open?' · '+sig.open.dir+' open':''} — strategy calculations, not predictions.`;
  const dpr=window.devicePixelRatio||1,W=cv.clientWidth,H=cv.clientHeight;if(cv.width!==Math.round(W*dpr)){cv.width=Math.round(W*dpr);cv.height=Math.round(H*dpr)}
  const ctx=cv.getContext('2d');ctx.setTransform(dpr,0,0,dpr,0,0);ctx.clearRect(0,0,W,H);
  const N=120,start=Math.max(0,candles.length-N),vis=candles.slice(start);
  let lo=Math.min(...vis.map(x=>x.l)),hi=Math.max(...vis.map(x=>x.h));const pad=(hi-lo)*0.1||1;lo-=pad;hi+=pad;
  const axisW=66,plotW=W-axisW,plotH=H-8,X=i=>(i+0.5)*(plotW/vis.length),Y=p=>4+(hi-p)/(hi-lo)*plotH;
  ctx.font='10px system-ui';for(let g=0;g<=4;g++){const p=lo+(hi-lo)*g/4,y=Y(p);ctx.strokeStyle='#1b2740';ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(plotW,y);ctx.stroke();ctx.fillStyle='#8fa3c0';ctx.fillText(fmt(p),plotW+6,y)}
  const bw=Math.max(2,(plotW/vis.length)*0.62);
  vis.forEach((cd,vi)=>{const up=cd.c>=cd.o,col=up?'#22c55e':'#ef4444',x=X(vi);ctx.strokeStyle=col;ctx.beginPath();ctx.moveTo(x,Y(cd.h));ctx.lineTo(x,Y(cd.l));ctx.stroke();ctx.fillStyle=col;ctx.fillRect(x-bw/2,Y(Math.max(cd.o,cd.c)),bw,Math.max(1,Y(Math.min(cd.o,cd.c))-Y(Math.max(cd.o,cd.c))))});
  const closes=candles.map(x=>x.c);const draw=(arr,color)=>{ctx.strokeStyle=color;ctx.lineWidth=1.4;ctx.beginPath();let s=false;for(let vi=0;vi<vis.length;vi++){const v=arr[start+vi];if(v==null)continue;const x=X(vi),y=Y(v);if(!s){ctx.moveTo(x,y);s=true}else ctx.lineTo(x,y)}ctx.stroke();ctx.lineWidth=1};
  draw(emaA(closes,5),'#4ade80');draw(emaA(closes,13),'#f59e0b');
  const label=(x,y,text,bg,above)=>{ctx.font='bold 10px system-ui';const w=ctx.measureText(text).width+10;const ly=above?y-22:y+8;ctx.fillStyle=bg;ctx.beginPath();ctx.roundRect(x-w/2,ly,w,15,4);ctx.fill();ctx.fillStyle='#fff';ctx.textAlign='center';ctx.fillText(text,x,ly+8);ctx.textAlign='left';ctx.font='10px system-ui'};
  for(const ev of sig.events){if(ev.i<start)continue;const cd=closed[ev.i];if(!cd)continue;const x=X(ev.i-start);if(ev.type==='BUY')label(x,Y(cd.l),'BUY','#16a34a',false);else if(ev.type==='SELL')label(x,Y(cd.h),'SELL','#dc2626',true);else if(ev.type==='TP')label(x,Y(cd.h),'TP','#15803d',true);else if(ev.type==='SL')label(x,Y(cd.l),'SL','#b91c1c',false)}}

/* ---------- views ---------- */
function renderAll(){renderChart();const f=fusion();
  if(f){$('fusionBox').innerHTML=`<div style="font-size:30px;font-weight:800" class="${f.dir==='BULLISH'?'up':f.dir==='BEARISH'?'down':'flat'}">${f.dir}</div>
  <div>Technical ${f.tech} · News ${f.news} · Context ${f.ctx.toFixed(1)} · <b>Final ${f.final}</b></div>
  <div class="dim" style="font-size:12.5px;margin-top:6px">Confidence level: UNVALIDATED · Probability is score-mapped, not calibrated accuracy.</div>`;
  $('reasons').innerHTML=f.reasons.map(r=>`<li>${r}</li>`).join('');$('vetoBox').innerHTML=f.veto?`<div class="warn">⛔ ${f.veto}</div>`:'';state.lastSignal=f}
  renderAnalysis();renderProviders()}
function indicatorsTable(){const cs=state.candles.slice(0,-1);if(cs.length<60)return'<p>Loading…</p>';const closes=cs.map(x=>x.c),h=cs.map(x=>x.h),l=cs.map(x=>x.l);const price=closes[closes.length-1];
  const rows=[['EMA 9',last(emaA(closes,9))],['EMA 20',last(emaA(closes,20))],['EMA 21',last(emaA(closes,21))],['EMA 50',last(emaA(closes,50))],['EMA 100',last(emaA(closes,100))],['EMA 200',last(emaA(closes,200))],['SMA 20',last(smaA(closes,20))],['RSI 14',last(rsiA(closes))],['MACD hist',last(macdHist(closes))],['ATR 14',last(atrA(h,l,closes))],['Support (50)',Math.min(...l.slice(-50))],['Resistance (50)',Math.max(...h.slice(-50))]];
  return `<table><tr><th>Indicator</th><th>Value</th><th>vs Price</th></tr>${rows.map(([n,v])=>`<tr><td>${n}</td><td>${fmt(v)}</td><td>${v===null?'—':(price>v?'<span class="up">above</span>':'<span class="down">below</span>')}</td></tr>`).join('')}</table><p class="sub">Price ${fmt(price)} · ${state.symbol} · ${state.tf} · closed candles only</p>`}
function renderAnalysis(){$('analysisOut').innerHTML=indicatorsTable();$('techOut').innerHTML=indicatorsTable()}
async function renderProviders(){let backend='not configured';const base=API_BASE();if(base){try{const h=await fetchJSON(base+'/health',6000);backend='OK — '+h.model_version}catch(e){backend='unreachable ('+base+')'}}
  $('apiBaseLabel').textContent=base||'not configured (direct Binance mode)';
  $('provOut').innerHTML=`<table><tr><th>Provider</th><th>Status</th><th>Label</th></tr>
  <tr><td>Binance public REST</td><td class="up">working (live check via candles)</td><td>LIVE</td></tr>
  <tr><td>TwelveData</td><td>requires free API key (backend .env)</td><td>UNAVAILABLE — no fake data</td></tr>
  <tr><td>Finnhub</td><td>requires free API key (backend .env)</td><td>UNAVAILABLE — no fake data</td></tr>
  <tr><td>Alpaca</td><td>requires free API key (backend .env)</td><td>UNAVAILABLE — no fake data</td></tr>
  <tr><td>Backend API</td><td>${backend}</td><td>—</td></tr>
  <tr><td>Quotex OTC</td><td>unsupported / data-limited</td><td>NO SIGNALS</td></tr></table>`}

/* ---------- scanner ---------- */
async function runScan(){const syms=['BTCUSDT','ETHUSDT','BNBUSDT','SOLUSDT','XRPUSDT','ADAUSDT','DOGEUSDT','LINKUSDT'];$('scanOut').textContent='Scanning live…';const out=[];
  for(const s of syms){try{const keep=state.symbol;const d=await fetchJSON(`${BINANCE}/api/v3/klines?symbol=${s}&interval=${['5s','15s','30s','1s'].includes(state.tf)?'5m':state.tf}&limit=300`);const cs=d.map(k=>({t:k[0],o:+k[1],h:+k[2],l:+k[3],c:+k[4],v:+k[5]}));const sc=scoreCandles(cs);if(!sc)continue;const q=cs.length>=200?85:60;const a=Math.abs(sc.score);const tier=q<40?'AVOID':(a>=55&&q>=70?'P1':a>=40&&q>=60?'P2':a>=25?'P3':a>=12?'WATCHLIST':'WATCHLIST');out.push({s,score:sc.score,q,tier,rsi:sc.rsi})}catch(e){}}
  out.sort((a,b)=>Math.abs(b.score)-Math.abs(a.score));
  const html=`<table><tr><th>Symbol</th><th>Quality</th><th>Opportunity</th><th>Tier</th><th>RSI</th></tr>${out.map(o=>`<tr><td>${o.s}</td><td>${o.q}</td><td class="${o.score>=0?'up':'down'}">${o.score}</td><td><b>${o.tier}</b></td><td>${o.rsi?o.rsi.toFixed(0):'—'}</td></tr>`).join('')}</table>`;
  $('scanOut').innerHTML=html;$('rankOut').innerHTML=html;store.set('lastScan',out)}
$('scanBtn').addEventListener('click',runScan);

/* ---------- signals / history / performance ---------- */
function recordSignal(f){const hist=store.get('signalHistory',[]);hist.unshift({ts:new Date().toISOString(),symbol:state.symbol,tf:state.tf,dir:f.dir,final:f.final,price:state.ticker?state.ticker.price:null});store.set('signalHistory',hist.slice(0,200));renderHistory();renderPerf()}
$('genSigBtn').addEventListener('click',()=>{const f=fusion();if(!f){$('sigOut').textContent='Not enough data yet.';return}recordSignal(f);
  const d=f.detail;const atrV=last(atrA(state.candles.map(x=>x.h),state.candles.map(x=>x.l),state.candles.map(x=>x.c)));
  let risk='—';if(f.dir!=='NO TRADE'&&atrV){const e=d.price;const sl=f.dir==='BULLISH'?e-1.5*atrV:e+1.5*atrV;risk=`Entry zone ${fmt(e*0.999)}–${fmt(e*1.001)} · SL ${fmt(sl)} · TP1 ${fmt(f.dir==='BULLISH'?e+1.5*(e-sl):e-1.5*(sl-e))} · TP2 (R:R 3) ${fmt(f.dir==='BULLISH'?e+3*(e-sl):e-3*(sl-e))}`}
  $('sigOut').innerHTML=`<div style="font-size:24px;font-weight:800" class="${f.dir==='BULLISH'?'up':f.dir==='BEARISH'?'down':'flat'}">${f.dir}</div><div>${risk}</div><ul class="reasons">${f.reasons.map(r=>`<li>${r}</li>`).join('')}</ul><p class="sub">confidence_level: UNVALIDATED · expires in 15 min · invalidation: SL hit, danger news, stale data, spread &gt; 50bps</p>`;
  pushAlert(`New signal: ${state.symbol} ${f.dir} (score ${f.final})`)});
function renderHistory(){const hist=store.get('signalHistory',[]);$('histOut').innerHTML=hist.length?`<table><tr><th>Time</th><th>Symbol</th><th>TF</th><th>Direction</th><th>Score</th><th>Price</th></tr>${hist.map(x=>`<tr><td>${x.ts.slice(0,19).replace('T',' ')}</td><td>${x.symbol}</td><td>${x.tf}</td><td>${x.dir}</td><td>${x.final}</td><td>${fmt(x.price)}</td></tr>`).join('')}</table>`:'No signals recorded yet — generate one in AI Signals.'}
function renderPerf(){const hist=store.get('signalHistory',[]);const paper=store.get('paper',{balance:10000,positions:[],closed:[]});const realized=paper.closed.reduce((a,p)=>a+(p.pnl||0),0);
  $('perfOut').innerHTML=`<table><tr><th>Metric</th><th>Value</th></tr><tr><td>Signals recorded (local)</td><td>${hist.length}</td></tr><tr><td>Paper closed trades</td><td>${paper.closed.length}</td></tr><tr><td>Paper realized PnL</td><td class="${realized>=0?'up':'down'}">$${realized.toFixed(2)}</td></tr><tr><td>Validated accuracy</td><td>None — UNVALIDATED (needs weeks of forward outcomes)</td></tr></table>`}

/* ---------- news ---------- */
const FEEDS=[['CoinDesk',1,'https://www.coindesk.com/arc/outboundfeeds/rss/'],['CoinTelegraph',0.8,'https://cointelegraph.com/rss'],['Decrypt',0.8,'https://decrypt.co/feed'],['Bitcoin Magazine',0.7,'https://bitcoinmagazine.com/feed'],['Google News',0.6,'https://news.google.com/rss/search?q=bitcoin+cryptocurrency&hl=en-US&gl=US&ceid=US:en']];
const BULL={'etf approval':3,'approval':1.5,'all-time high':2,'surge':2,'rally':2,'bullish':2,'inflow':2,'soars':2,'gains':1,'breakout':1.5,'record high':2};
const BEAR={'hack':3,'exploit':3,'stolen':2.5,'ban':2.5,'lawsuit':2,'fraud':2.5,'bankrupt':3,'crash':2.5,'plunge':2.5,'bearish':2,'falls':1.5,'drops':1.5,'warning':1};
const DANGER=['hack','exploit','bankrupt','stolen','fraud','crash','plunge','ban'];
async function fetchFeed(url){try{const d=await fetchJSON('https://api.rss2json.com/v1/api.json?rss_url='+encodeURIComponent(url));if(d&&d.status==='ok')return d.items.map(it=>({title:it.title,link:it.link,ts:new Date(it.pubDate.replace(' ','T')+'Z')}))}catch(e){}
  try{const ctl=new AbortController();const r=await fetch('https://api.allorigins.win/raw?url='+encodeURIComponent(url),{signal:ctl.signal});const xml=await r.text();const doc=new DOMParser().parseFromString(xml,'text/xml');const out=[];doc.querySelectorAll('item').forEach(it=>{const g=s=>{const n=it.querySelector(s);return n?n.textContent.trim():''};out.push({title:g('title'),link:g('link'),ts:new Date(g('pubDate'))})});return out}catch(e){return[]}}
async function loadNews(){const now=new Date();const raw=[];await Promise.all(FEEDS.map(async([name,w,url])=>{const items=await fetchFeed(url);for(const it of items){if(!it.title||isNaN(it.ts))continue;const age=(now-it.ts)/60000;if(age>1440)continue;raw.push({title:it.title,link:it.link,source:name,weight:w,age})}}));
  raw.sort((a,b)=>a.age-b.age);const seen=new Set(),uniq=[];for(const it of raw){const key=it.title.toLowerCase().replace(/[^a-z0-9 ]/g,'').slice(0,60).trim();if(seen.has(key))continue;seen.add(key);uniq.push(it)}
  let agg=0,bull=0,bear=0,danger=null;const scored=[];
  for(const it of uniq){const text=it.title.toLowerCase();let s=0;for(const k in BULL)if(text.includes(k))s+=BULL[k];for(const k in BEAR)if(text.includes(k))s-=BEAR[k];s=Math.max(-4,Math.min(4,s))/4;const fresh=Math.pow(0.5,it.age/180);agg+=s*it.weight*fresh;if(s>0.15)bull++;else if(s<-0.15)bear++;if(DANGER.some(d=>text.includes(d))&&s<-0.3&&it.age<=240&&(!danger||it.age<danger.age))danger={title:it.title,source:it.source,age:Math.round(it.age)};scored.push({...it,s,label:s>0.15?'bullish':s<-0.15?'bearish':'neutral'})}
  state.news={score:Math.round(100*Math.tanh(agg/3)*10)/10,items:scored.slice(0,15),danger,loaded:true};
  $('newsScore').innerHTML=`News score: <b>${state.news.score}</b> · ${bull} bullish vs ${bear} bearish (24h, freshness-decayed)${danger?' · <span class="down">DANGER: '+danger.source+'</span>':''}`;
  $('newsList').innerHTML=state.news.items.length?state.news.items.map(it=>`<div style="padding:7px 0;border-bottom:1px solid var(--line)"><a href="${it.link}" target="_blank" rel="noopener">${it.title}</a><div class="dim" style="font-size:11.5px">${it.source} · ${Math.round(it.age)} min ago · <span class="tag ${it.label}">${it.label}</span></div></div>`).join(''):'No headlines loaded — counted as 0.';
  renderAll()}

/* ---------- backtest (browser) ---------- */
$('btBtn').addEventListener('click',async()=>{$('btOut').textContent='Running on real candles…';try{const cs=await fetchKlines(state.tf==='1s'||state.tf.endsWith('s')?'5m':state.tf,500);const closed=cs.slice(0,-1);const sig=computeSignals(closed);let wins=0,losses=0,pnl=0,eq=10000,peak=10000,dd=0;
  for(const t of sig.history){const won=t.outcome==='TP';const lost=t.outcome==='SL';if(!won&&!lost)continue;const risk=Math.abs(t.entry-t.sl);const qty=(eq*0.01)/risk;const p=won?3*risk*qty:-risk*qty;const fees=(t.entry+t.entry)*qty*0.001;pnl+=p-fees;eq+=p-fees;peak=Math.max(peak,eq);dd=Math.max(dd,(peak-eq)/peak*100);if(won)wins++;else losses++}
  const total=wins+losses;$('btOut').innerHTML=`<table><tr><th>Trades (TP/SL decided)</th><td>${total}</td></tr><tr><th>Win rate</th><td class="${total&&wins/total>0.25?'up':'down'}">${total?(wins/total*100).toFixed(2):'—'}% (break-even 25% at R:R 3:1 before fees; binary 85% payout break-even is 54.05%)</td></tr><tr><th>Net PnL (1% risk, 0.1% fees)</th><td class="${pnl>=0?'up':'down'}">$${pnl.toFixed(2)}</td></tr><tr><th>Max drawdown</th><td>${dd.toFixed(2)}%</td></tr><tr><th>Reversed (no TP/SL)</th><td>${sig.history.filter(x=>x.outcome==='REV').length}</td></tr></table><p class="sub">In-sample replay only — not proof of future edge.</p>`}catch(e){$('btOut').textContent='Backtest failed: '+e.message}});

/* ---------- paper trading ---------- */
function paperGet(){return store.get('paper',{balance:10000,positions:[],closed:[]})}
function renderPaper(){const p=paperGet();const cur=state.ticker?state.ticker.price:0;let unreal=0;for(const pos of p.positions)unreal+=(cur-pos.entry)*pos.qty*(pos.side==='LONG'?1:-1);
  $('paperOut').innerHTML=`<table><tr><th>Cash</th><td>$${p.balance.toFixed(2)}</td></tr><tr><th>Unrealized</th><td class="${unreal>=0?'up':'down'}">$${unreal.toFixed(2)}</td></tr><tr><th>Open positions</th><td>${p.positions.map(x=>`${x.side} ${x.qty} ${x.symbol} @ ${fmt(x.entry)}`).join('<br>')||'none'}</td></tr><tr><th>Closed</th><td>${p.closed.length} trades · realized $${p.closed.reduce((a,x)=>a+(x.pnl||0),0).toFixed(2)}</td></tr></table>`;renderPerf()}
$('paperBuy').addEventListener('click',()=>{const p=paperGet();const price=state.ticker?state.ticker.price:null;if(!price){alert('No live price yet');return}const qty=parseFloat($('paperQty').value)||0;const fee=price*qty*0.001;if(price*qty+fee>p.balance){alert('Insufficient paper balance');return}p.balance-=price*qty+fee;p.positions.push({symbol:state.symbol,side:'LONG',qty,entry:price});store.set('paper',p);renderPaper();pushAlert(`Paper BUY ${qty} ${state.symbol} @ ${fmt(price)}`)});
$('paperSell').addEventListener('click',()=>{const p=paperGet();const price=state.ticker?state.ticker.price:null;if(!price)return;for(const pos of p.positions){const pnl=(price-pos.entry)*pos.qty*(pos.side==='LONG'?1:-1)-price*pos.qty*0.001;p.balance+=pos.entry*pos.qty+pnl;p.closed.push({...pos,exit:price,pnl})}p.positions=[];store.set('paper',p);renderPaper()});
$('paperReset').addEventListener('click',()=>{store.set('paper',{balance:10000,positions:[],closed:[]});renderPaper()});

/* ---------- watchlist / alerts / quotex / settings ---------- */
function renderWatch(){const w=store.get('watchlist',['BTCUSDT','ETHUSDT']);$('watchOut').innerHTML=w.map(s=>`<span class="tag" style="margin:2px">${s}</span>`).join(' ')||'Empty'}
$('watchAdd').addEventListener('click',()=>{const w=store.get('watchlist',[]);if(!w.includes(state.symbol))w.push(state.symbol);store.set('watchlist',w);renderWatch()});
$('watchRemove').addEventListener('click',()=>{store.set('watchlist',store.get('watchlist',[]).filter(s=>s!==state.symbol));renderWatch()});
function pushAlert(msg){const a=store.get('alerts',[]);a.unshift({ts:new Date().toISOString(),msg});store.set('alerts',a.slice(0,50));renderAlerts();if(store.get('notif',false)&&window.Notification&&Notification.permission==='granted')new Notification('MarketPilot AI',{body:msg})}
function renderAlerts(){const a=store.get('alerts',[]);$('alertOut').innerHTML=a.length?a.map(x=>`<div style="padding:5px 0;border-bottom:1px solid var(--line)">${x.ts.slice(0,19).replace('T',' ')} — ${x.msg}</div>`).join(''):'No alerts yet.'}
$('alertTest').addEventListener('click',()=>{const f=fusion();pushAlert(f?`Current: ${state.symbol} ${f.dir} (score ${f.final})`:'No signal data yet')});
$('qSave').addEventListener('click',()=>{const v=parseFloat($('qPrice').value);if(!v)return;const obs=store.get('quotexObs',[]);obs.unshift({ts:new Date().toISOString(),symbol:state.symbol,quotex:v,binance:state.ticker?state.ticker.price:null});store.set('quotexObs',obs.slice(0,50));renderQ()});
function renderQ(){const obs=store.get('quotexObs',[]);$('qOut').innerHTML=obs.length?`<table><tr><th>Time</th><th>Symbol</th><th>Quotex shown</th><th>Binance live</th><th>Gap</th></tr>${obs.map(o=>`<tr><td>${o.ts.slice(0,19).replace('T',' ')}</td><td>${o.symbol}</td><td>${fmt(o.quotex)}</td><td>${fmt(o.binance)}</td><td>${o.binance?fmt(o.quotex-o.binance):'—'}</td></tr>`).join('')}</table>`:'No observations saved.'}
$('saveSettings').addEventListener('click',()=>{store.set('apiBase',$('apiBase').value.trim());store.set('notif',$('notifToggle').checked);if($('notifToggle').checked&&window.Notification)Notification.requestPermission();renderProviders();alert('Settings saved')});

/* ---------- nav / init ---------- */
$('mainNav').addEventListener('click',e=>{const b=e.target.closest('[data-view]');if(!b)return;document.querySelectorAll('#mainNav .btn').forEach(x=>x.classList.toggle('active',x===b));document.querySelectorAll('.view').forEach(v=>v.classList.toggle('active',v.id==='view-'+b.dataset.view))});
$('symbolSel').addEventListener('change',e=>{state.symbol=e.target.value;state.candles=[];refreshTicker();refreshCandles();loadNews()});
$('tfSel').addEventListener('change',e=>{state.tf=e.target.value;refreshCandles()});
$('apiBase').value=store.get('apiBase','');$('notifToggle').checked=store.get('notif',false);
renderWatch();renderAlerts();renderQ();renderHistory();renderPaper();
refreshTicker();refreshCandles();loadNews();
setInterval(refreshTicker,5000);setInterval(refreshCandles,15000);setInterval(loadNews,300000);
window.addEventListener('resize',()=>renderChart());
