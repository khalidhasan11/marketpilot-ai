'use strict';
async function load(){const v=await chrome.storage.local.get(['mpApiBase','mpNotify']);document.getElementById('apiBase').value=v.mpApiBase||'';document.getElementById('notify').checked=!!v.mpNotify}
document.getElementById('save').addEventListener('click',async()=>{await chrome.storage.local.set({mpApiBase:document.getElementById('apiBase').value.trim(),mpNotify:document.getElementById('notify').checked});document.getElementById('msg').textContent='Saved.'});
load();
