(() => {
  const api=(path,opt={})=>fetch(window.plannerApiUrl(path),{headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt}).then(async r=>{let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});
  const originalEnhance=window.__productEnhance;
  async function sync(){try{window.__plannerSnapshot=await api('/snapshot');window.__plannerProfile=await api('/profile')}catch{} }
  const oldLoad=window.load;
  if(oldLoad&&!window.__suiteLoadPatched){window.load=async(...args)=>{const r=await oldLoad(...args);await sync();document.dispatchEvent(new CustomEvent('planner:ready'));return r};window.__suiteLoadPatched=true}
  window.addEventListener('planner:ready',()=>setTimeout(sync,0));
  sync();
})();