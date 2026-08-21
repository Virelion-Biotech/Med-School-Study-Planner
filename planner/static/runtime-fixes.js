(() => {
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options}).then(async r => {let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});

  // The core app keeps its state in a lexical const, so feature modules cannot see it.
  // Keep a small public mirror for optional modules instead of coupling them to internals.
  async function syncPublicState() {
    try {
      window.__plannerSnapshot = await api('/snapshot');
      window.__plannerProfile = await api('/profile');
      return true;
    } catch (_) { return false; }
  }

  // Make the notification API available to feature modules.
  window.toast = window.toast || function(message) {
    const el = document.querySelector('#toast');
    if (!el) return;
    el.textContent = String(message || 'Done');
    el.classList.add('show');
    clearTimeout(window.__runtimeToastTimer);
    window.__runtimeToastTimer = setTimeout(() => el.classList.remove('show'), 2600);
  };

  // A reliable mode chooser. It does not depend on inline handlers or script order.
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
      modal.classList.add('hidden');
      if (mode === 'usmle' && typeof window.startStep1 === 'function') window.startStep1();
      else if (mode === 'school' && typeof window.openSchoolPicker === 'function') window.openSchoolPicker();
      else if (mode === 'personal' && typeof window.startPersonalPlanner === 'function') window.startPersonalPlanner();
      else window.toast('This setup is still loading. Try again in a moment.');
    }));
  };

  // Ensure Change plan and Change mode always open the same reliable chooser.
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
    // Product-suite enhancements use this mirror and can now initialize reliably.
    if (typeof window.load === 'function') {
      try { await window.load(); } catch (_) {}
    }
    bindModeButtons();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot, {once:true});
  else boot();
})();
