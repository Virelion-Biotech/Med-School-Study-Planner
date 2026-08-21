(() => {
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options}).then(async r => {let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});
  const today = () => new Date().toISOString().slice(0,10);
  const BACKUP_KEY = 'med-school-planner-backup-v1';

  async function syncPublicState() {
    try {
      let snapshot = await api('/snapshot');
      const profile = await api('/profile');
      // Render's free filesystem is ephemeral. Keep a browser-local curriculum backup
      // so a restart does not leave a returning student with an empty planner.
      if ((snapshot.topics||[]).length || (snapshot.subjects||[]).length) {
        localStorage.setItem(BACKUP_KEY, JSON.stringify({snapshot, profile, savedAt:new Date().toISOString()}));
      } else {
        const raw = localStorage.getItem(BACKUP_KEY);
        if (raw) {
          const backup = JSON.parse(raw);
          const s = backup.snapshot || {};
          for (const subject of (s.subjects||[])) await api('/subjects',{method:'POST',body:JSON.stringify({id:subject.id,name:subject.name,exam_weight:subject.exam_weight,category:subject.category})});
          for (const topic of (s.topics||[])) await api('/topics',{method:'POST',body:JSON.stringify({id:topic.id,subject_id:topic.subject_id,name:topic.name,complexity:topic.complexity,estimated_hours:topic.estimated_hours,mastery:topic.mastery,last_studied:topic.last_studied,next_review_due:topic.next_review_due,self_difficulty:topic.self_difficulty,volume:topic.volume,cognitive_load:topic.cognitive_load})});
          for (const exam of (s.exams||[])) await api('/exams',{method:'POST',body:JSON.stringify({id:exam.id,date:exam.exam_date,subject_ids:JSON.parse(exam.subject_ids_json||'[]'),topic_ids:JSON.parse(exam.topic_ids_json||'[]'),weight:exam.weight})});
          if (backup.profile) await api('/profile',{method:'PUT',body:JSON.stringify(backup.profile)});
          snapshot = await api('/snapshot');
        }
      }
      window.__plannerSnapshot = snapshot;
      window.__plannerProfile = profile;
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
    const blocks=[['cardio','Cardiovascular'],['resp-renal','Respiratory & Renal'],['gi','Gastrointestinal'],['repro-endo','Reproductive & Endocrine'],['neuro','Neuro / Behavioral'],['immune-blood','Blood & Immune'],['msk-skin','MSK / Skin'],['multisystem','Multisystem'],['development','Human Development'],['biostats','Biostats / Epidemiology'],['communication','Communication']];
    modal.innerHTML=`<div class="modal-card smart-tool"><div class="setup-kicker">USMLE STEP 1</div><h2>What are you studying right now?</h2><p>Pick your current block. It gets extra priority this week; the rest of Step 1 stays in the background.</p><div class="mode-grid">${blocks.map(([id,label])=>`<button class="mode-choice" type="button" data-step1-block="${id}"><strong>${label}</strong><span>Give this block extra time.</span><b>Study this →</b></button>`).join('')}</div></div>`;
    modal.classList.remove('hidden');
    modal.querySelectorAll('[data-step1-block]').forEach(b=>b.addEventListener('click',()=>chooseStep1Block(b.dataset.step1Block,b.querySelector('strong').textContent)));
  };

  window.openPlannerSetup = function() {
    const modal = document.querySelector('#modal');
    if (!modal) return;
    modal.innerHTML = `<div class="modal-card smart-tool"><div class="setup-kicker">PLAN TYPE</div><h2>What are you studying for?</h2><p>Pick one. We'll do the setup for you.</p><div class="mode-grid"><button class="mode-choice" type="button" data-runtime-mode="usmle"><strong>USMLE Step 1</strong><span>Use the Step 1 blueprint and choose your current block.</span><b>Start →</b></button><button class="mode-choice" type="button" data-runtime-mode="school"><strong>My medical school</strong><span>Choose your school, year, and current course.</span><b>Choose school →</b></button><button class="mode-choice" type="button" data-runtime-mode="personal"><strong>Personal planner</strong><span>Add subjects and what you actually have to study.</span><b>Build my plan →</b></button></div></div>`;
    modal.classList.remove('hidden');
    modal.querySelectorAll('[data-runtime-mode]').forEach(button => button.addEventListener('click', () => {
      const mode = button.dataset.runtimeMode;
      if (mode === 'usmle') window.openStep1BlockPicker();
      else if (mode === 'school' && typeof window.openSchoolPicker === 'function') window.openSchoolPicker();
      else if (mode === 'personal' && typeof window.startPersonalPlanner === 'function') window.startPersonalPlanner();
      else window.toast('This setup is still loading. Try again in a moment.');
    }));
  };

  function renderFirstRun() {
    const snap=window.__plannerSnapshot||{};
    if ((snap.topics||[]).length) return;
    const view=document.querySelector('#view');
    if(!view) return;
    view.innerHTML=`<div class="hero onboarding"><div><div class="kicker">START HERE</div><h2>Tell me what you're studying.</h2><p>You don't need to build a complicated curriculum. Pick USMLE, your medical school, or make a simple personal plan.</p><div class="hero-actions"><button class="btn primary big" type="button" id="first-usmle">USMLE Step 1</button><button class="btn secondary big" type="button" id="first-school">My medical school</button><button class="btn secondary big" type="button" id="first-personal">Personal planner</button></div><small>We'll create the first week for you.</small></div><div class="blueprint"><div class="blueprint-head"><strong>What you need to give us</strong><span>3 choices</span></div><div class="blueprint-row"><span>USMLE</span><b>current block</b></div><div class="blueprint-row"><span>School</span><b>year + course</b></div><div class="blueprint-row"><span>Personal</span><b>subjects + workload</b></div></div></div>`;
    document.querySelector('#first-usmle').onclick=window.openStep1BlockPicker;
    document.querySelector('#first-school').onclick=window.openSchoolPicker;
    document.querySelector('#first-personal').onclick=window.startPersonalPlanner;
  }

  function bindModeButtons() {
    ['#reset-btn','#mode-btn'].forEach(selector => {
      const button = document.querySelector(selector);
      if (!button || button.dataset.runtimeBound) return;
      button.dataset.runtimeBound='1';
      button.addEventListener('click', event => { event.preventDefault(); event.stopImmediatePropagation(); window.openPlannerSetup(); });
    });
  }

  async function boot() {
    bindModeButtons();
    await syncPublicState();
    if (typeof window.load==='function') { try { await window.load(); } catch (_) {} }
    renderFirstRun();
    bindModeButtons();
  }

  if (document.readyState==='loading') document.addEventListener('DOMContentLoaded', boot, {once:true});
  else boot();
})();
