(() => {
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {
    headers: {'Content-Type':'application/json', ...(options.headers || {})}, ...options,
  }).then(async r => { let b={}; try { b=await r.json(); } catch {} if (!r.ok) throw Error(b.detail || `HTTP ${r.status}`); return b; });
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const today = () => new Date().toISOString().slice(0,10);

  async function metrics() {
    const snap = await api('/snapshot');
    const analytics = await api('/analytics');
    const todayRows = (snap.sessions || []).filter(s => s.session_date === today());
    const plannedToday = todayRows.reduce((n,s) => n + Number(s.planned_minutes || 0), 0);
    const completedToday = todayRows.filter(s => s.completed).reduce((n,s) => n + Number(s.actual_minutes || s.planned_minutes || 0), 0);
    const mastery = snap.topics?.length ? snap.topics.reduce((n,t)=>n + Number(t.mastery || 0),0) / snap.topics.length : 0;
    const due = (snap.topics || []).filter(t => t.next_review_due && t.next_review_due <= today()).length;
    const remaining = Math.max(0, plannedToday - completedToday);
    return {snap, analytics, plannedToday, completedToday, mastery, due, remaining};
  }

  function readiness(m) {
    const coverage = m.snap.topics?.length ? new Set(m.snap.sessions?.filter(s => s.completed).map(s => s.topic_id)).size / m.snap.topics.length : 0;
    const performance = m.analytics.mean_performance ?? 0.5;
    const retentionProxy = Math.max(0, 1 - Math.min(1, m.due / Math.max(1, m.snap.topics?.length || 1)));
    const score = Math.round((0.40*m.mastery + 0.25*performance + 0.20*coverage + 0.15*retentionProxy) * 100);
    return {score, coverage, performance, retentionProxy};
  }

  function panelHTML(m) {
    const r = readiness(m);
    const behind = m.remaining > 0;
    return `<section class="panel adaptive-panel" id="adaptive-panel">
      <div class="panel-head"><div><div class="kicker">ADAPTIVE ENGINE</div><h2>Your study state</h2><span>The planner now separates learning, retention, workload, and deadline pressure.</span></div>
      <div class="adaptive-score"><strong>${r.score}%</strong><small>planning readiness</small></div></div>
      <div class="adaptive-grid">
        <div><span>Knowledge</span><strong>${Math.round(m.mastery*100)}%</strong><small>legacy mastery signal</small></div>
        <div><span>Performance</span><strong>${Math.round(r.performance*100)}%</strong><small>recent completed sessions</small></div>
        <div><span>Review pressure</span><strong>${m.due}</strong><small>due today</small></div>
        <div><span>Today</span><strong>${m.completedToday}/${m.plannedToday}m</strong><small>actual / planned</small></div>
      </div>
      ${behind ? `<div class="adaptive-warning"><div><b>You're ${m.remaining} minutes behind today's plan.</b><span>Don't automatically cram it into tonight. Replan around the remaining high-value work.</span></div><button class="btn primary small" id="adaptive-catchup">Rebalance</button></div>` : ''}
      <div class="adaptive-actions"><button class="btn secondary small" id="adaptive-minimum">Minimum day (45m)</button><button class="btn secondary small" id="adaptive-export">Export learning state</button></div>
    </section>`;
  }

  async function renderPanel() {
    const view = document.querySelector('#view');
    if (!view || !window.__plannerSnapshot?.topics?.length) return;
    try {
      const m = await metrics();
      document.querySelector('#adaptive-panel')?.remove();
      view.insertAdjacentHTML('beforeend', panelHTML(m));
      document.querySelector('#adaptive-catchup')?.addEventListener('click', async () => {
        try { await api('/replan',{method:'POST',body:JSON.stringify({start_date:today(),days:7,optimizer:true,locked_session_ids:[]})}); await window.load(); window.toast?.('Week rebalanced around what remains'); } catch(e) { window.toast?.(e.message); }
      });
      document.querySelector('#adaptive-minimum')?.addEventListener('click', async () => {
        try {
          const profile = await api('/profile');
          await api('/profile',{method:'PUT',body:JSON.stringify({...profile,daily_available_minutes:45,max_session_minutes:45})});
          await api('/replan',{method:'POST',body:JSON.stringify({start_date:today(),days:1,optimizer:true,locked_session_ids:[]})});
          await window.load(); window.toast?.('Minimum-day plan created');
        } catch(e) { window.toast?.(e.message); }
      });
      document.querySelector('#adaptive-export')?.addEventListener('click', async () => {
        try {
          const blob = new Blob([JSON.stringify(m,{null:2},2)], {type:'application/json'});
          const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'planner-learning-state.json'; a.click(); URL.revokeObjectURL(a.href);
        } catch(e) { window.toast?.(e.message); }
      });
    } catch(e) { console.warn('adaptive-v3', e); }
  }

  const originalRender = window.render;
  window.render = function(...args) { const result = originalRender?.apply(this,args); setTimeout(renderPanel, 0); return result; };
  window.addEventListener('load', () => setTimeout(renderPanel, 100));
})();
