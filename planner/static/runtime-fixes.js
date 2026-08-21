(() => {
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options}).then(async r => {let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});
  const today = () => new Date().toISOString().slice(0,10);

  async function syncPublicState() {
    try {
      window.__plannerSnapshot = await api('/snapshot');
      window.__plannerProfile = await api('/profile');
      return true;
    } catch (_) { return false; }
  }

  window.toast = window.toast || function(message) {
    const el = document.querySelector('#toast');
    if (!el) return;
    el.textContent = String(message || 'Done');
    el.classList.add('show');
    clearTimeout(window.__runtimeToastTimer);
    window.__runtimeToastTimer = setTimeout(() => el.classList.remove('show'), 2600);
  };

  async function chooseStep1Block(blockId, label) {
    try {
      window.toast(`Building Step 1 around ${label}…`);
      await api('/setup/step1', {method:'POST', body:JSON.stringify({start_date:today(), current_block:blockId})});
      localStorage.setItem('planner-mode','usmle');
      window.__plannerMode='usmle';
      window.__plannerBlock=label;
      const modal=document.querySelector('#modal');
      if(modal) modal.classList.add('hidden');
      if(typeof window.load==='function') await window.load();
      window.toast(`${label} is now your focus`);
    } catch (e) { window.toast(e.message); }
  }

  window.openStep1BlockPicker = function() {
    const modal=document.querySelector('#modal');
    if(!modal) return;
    const blocks=[
      ['cardio','Cardiovascular'],['resp-renal','Respiratory & Renal'],['gi','Gastrointestinal'],
      ['repro-endo','Reproductive & Endocrine'],['neuro','Neuro / Behavioral'],['immune-blood','Blood & Immune'],
      ['msk-skin','MSK / Skin'],['multisystem','Multisystem'],['development','Human Development'],
      ['biostats','Biostats / Epidemiology'],['communication','Communication']
    ];
    modal.innerHTML=`<div class="modal-card smart-tool"><div class="setup-kicker">USMLE STEP 1</div><h2>What are you studying right now?</h2><p>Pick your current block. It gets extra priority this week; the rest of Step 1 stays in the background.</p><div class="mode-grid">${blocks.map(([id,label])=>`<button class="mode-choice" type="button" data-step1-block="${id}"><strong>${label}</strong><span>Give this block extra time.</span><b>Study this →</b></button>`).join('')}</div></div>`;
    modal.classList.remove('hidden');
    modal.querySelectorAll('[data-step1-block]').forEach(b=>b.addEventListener('click',()=>chooseStep1Block(b.dataset.step1Block,b.querySelector('strong').textContent)));
  };

  window.openPlannerSetup = function() {
    const modal = document.querySelector('#modal');
    if (!modal) return;
    modal.innerHTML = `<div class="modal-card smart-tool">
      <div class="setup-kicker">PLAN TYPE</div>
      <h2>What are you studying for?</h2>
      <p>Pick one. We'll do the setup for you.</p>
      <div class="mode-grid">
        <button class="mode-choice" type="button" data-runtime-mode="usmle"><strong>USMLE Step 1</strong><span>Use the Step 1 blueprint and choose your current block.</span><b>Start →</b></button>
        <button class="mode-choice" type="button" data-runtime-mode="school"><strong>My medical school</strong><span>Choose your school, year, and current course.</span><b>Choose school →</b></button>
        <button class="mode-choice" type="button" data-runtime-mode="personal"><strong>Personal planner</strong><span>Add subjects and what you actually have to study.</span><b>Build my plan →</b></button>
      </div>
    </div>`;
    modal.classList.remove('hidden');
    modal.querySelectorAll('[data-runtime-mode]').forEach(button => button.addEventListener('click', () => {
      const mode = button.dataset.runtimeMode;
      if (mode === 'usmle') window.openStep1BlockPicker();
      else if (mode === 'school' && typeof window.openSchoolPicker === 'function') window.openSchoolPicker();
      else if (mode === 'personal' && typeof window.startPersonalPlanner === 'function') window.startPersonalPlanner();
      else window.toast('This setup is still loading. Try again in a moment.');
    }));
  };

  function bindModeButtons() {
    ['#reset-btn','#mode-btn'].forEach(selector => {
      const button = document.querySelector(selector);
      if (!button || button.dataset.runtimeBound) return;
      button.dataset.runtimeBound = '1';
      button.addEventListener('click', event => { event.preventDefault(); event.stopImmediatePropagation(); window.openPlannerSetup(); });
    });
  }

  async function boot() {
    bindModeButtons();
    await syncPublicState();
    if (typeof window.load === 'function') {
      try { await window.load(); } catch (_) {}
    }
    bindModeButtons();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once:true});
  else boot();
})();
