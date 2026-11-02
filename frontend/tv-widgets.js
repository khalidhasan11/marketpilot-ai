'use strict';
/* MarketPilot AI — TradingView WIDGETS: display-only embeds.
 *
 * These are TradingView's own hosted widgets with TradingView's own data and
 * branding (attribution kept intact, per their terms). They are fenced:
 * NO MarketPilot code reads widget DOM, values, or output — widgets can never
 * influence a score, prediction, or signal. If a widget script is blocked,
 * the labelled container simply stays empty and the app works without it.
 * Licensing basis: docs/TRADINGVIEW_INTEGRATION.md
 */
(function(){
const SRC='https://s3.tradingview.com/external-embedding/';
const loaded={};
const COPYRIGHT='<div class="tradingview-widget-copyright"><a href="https://www.tradingview.com/" rel="noopener nofollow" target="_blank"><span class="blue-text">Track all markets on TradingView</span></a></div>';

const WIDGETS={
  tape:{container:'tvTape',script:'embed-widget-ticker-tape.js',config:{
    symbols:[{proName:'BINANCE:BTCUSDT',title:'Bitcoin'},{proName:'BINANCE:ETHUSDT',title:'Ethereum'},
      {proName:'BINANCE:BNBUSDT',title:'BNB'},{proName:'BINANCE:SOLUSDT',title:'Solana'},
      {proName:'BINANCE:XRPUSDT',title:'XRP'},{proName:'TVC:GOLD',title:'Gold'}],
    showSymbolLogo:false,colorTheme:'dark',isTransparent:true,displayMode:'adaptive',locale:'en'}},
  heatmap:{container:'tvHeatmap',script:'embed-widget-crypto-coins-heatmap.js',config:{
    dataSource:'Crypto',blockSize:'market_cap_calc',blockColor:'change',locale:'en',symbolUrl:'',
    colorTheme:'dark',hasTopBar:false,isDataSetContain:false,isZoomEnabled:true,hasSymbolTooltip:true,
    isMonoSize:false,width:'100%',height:490}},
  calendar:{container:'tvCalendar',script:'embed-widget-events.js',config:{
    colorTheme:'dark',isTransparent:false,width:'100%',height:560,locale:'en',
    importanceFilter:'-1,0,1',countryFilter:'us,eu,gb,jp,ca,au,ch,cn'}}
};

function mount(name){
  if(loaded[name])return;const w=WIDGETS[name];if(!w)return;
  const box=document.getElementById(w.container);if(!box)return;loaded[name]=true;
  const inner=document.createElement('div');inner.className='tradingview-widget-container';
  inner.style.height='100%';inner.style.width='100%';
  const widgetDiv=document.createElement('div');widgetDiv.className='tradingview-widget-container__widget';
  widgetDiv.style.height='calc(100% - 32px)';widgetDiv.style.width='100%';
  inner.appendChild(widgetDiv);
  const holder=document.createElement('div');holder.innerHTML=COPYRIGHT;inner.appendChild(holder.firstChild);
  const script=document.createElement('script');script.type='text/javascript';script.async=true;
  script.src=SRC+w.script;script.innerHTML=JSON.stringify(w.config);
  inner.appendChild(script);
  box.appendChild(inner);
}

function mountForView(view){
  if(view==='overview')mount('tape');
  if(view==='rankings')mount('heatmap');
  if(view==='calendar')mount('calendar');
}
document.addEventListener('DOMContentLoaded',()=>mount('tape'));
const nav=document.getElementById('mainNav');
if(nav)nav.addEventListener('click',e=>{const b=e.target.closest('[data-view]');if(b)setTimeout(()=>mountForView(b.dataset.view),50)});
window.MPTVWidgets={mount,mountForView};
})();
