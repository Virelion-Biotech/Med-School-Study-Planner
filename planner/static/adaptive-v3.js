(() => {
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {
    headers: {'Content-Type':'application/json', ...(options.headers || {})}, ...options,
  }).then(async r => { let b={}; try { b=await r.json(); } catch {} if (!r.ok) throw Error(b.detail || `HTTP ${r.status}`); return b; });
  const today = () => new Date().toISOString().slice(0,10);

  async function metrics() {
    const snap = await api('/snapshot');
    const analytics = await api('/analytics');
    let readiness = null;
    try { readiness = await api('/v2/readiness'); } catch (_) {}
    const todayRows = (snap.sessions || []).filter(s => s.session_date === today());
    const plannedToday = todayRows.reduce((n,s) => n + Number(s.planned_minutes || 0), 0);
    const completedToday = todayRows.filter(s => s.completed).reduce((n,s) => n + Number(s.actual_minutes || s.planned_minutes || 0), 0);
    const mastery = snap.topics?.length ? snap.topics.reduce((n,t)=>n + Number(t.mastery || 0),0) / snap.topics.length : 0;
    const due = (snap.topics || []).filter(t => t.next_review_due && t.next_review_due <= today()).length;
    const remaining = Math.max(0, plannedToday - completedToday);
    return {snap, analytics, readiness, plannedToday, completedToday, mastery, due, remaining};
  }

  function readiness(m) {
    if (m.readiness) return {score: Math.round(m.readiness.score * 100), label: m.readiness.label, components: m.readiness.components};
    const coverage = m.snap.topics?.length ? new Set(m.snap.sessions?.filter(s => s.completed).map(s => s.topic_id)).size / m.snap.topics.length : 0;
    const performance = m.analytics.mean_performance ?? 0.5;
    const retentionProxy = Math.max(0, 1 - Math.min(1, m.due / Math.max(1, m.snap.topics?.length || 1)));
    const score = Math.round((0.30*m.mastery + 0.20*retentionProxy + 0.20*coverage + 0.20*performance + 0.10*Math.min(1, 1 - (m.remaining / Math.max(1, m.plannedToday)))) * 100);
    return {score, label: score >= 80 ? 'Strong' : score >= 65 ? 'Good' : score >= 50 ? 'Moderate' : score >= 35 ? 'At risk' : 'Low', components: {knowledge:m.mastery,retention:retentionProxy,coverage,practice:performance,deadline_protection:Math.min(1,1-m.remaining/Math.max(1,m.plannedToday))}};
  }

  function panelHTML(m) {
    const r = readiness(m);
    const behind = m.remaining > 0;
    return `<section class="panel adaptive-panel" id="adaptive-panel">
      <div class="panel-head"><div><div class="kicker">ADAPTIVE ENGINE</div><h2>Your study state</h2><span>Learning, retention, workload, practice, and deadline pressure are tracked separately.</span></div>
      <div class="adaptive-score"><strong>${r.score}%</strong><small>${r.label} planning readiness</small></div></div>
      <div class="adaptive-grid">
        <div><span>Knowledge</span><strong>${Math.round((r.components.knowledge ?? m.mastery)*100)}%</strong><small>current mastery signal</small></div>
        <div><span>Retention</span><strong>${Math.round((r.components.retention ?? 0)*100)}%</strong><small>memory protection</small></div>
        <div><span>Practice</span><strong>${Math.round((r.components.practice ?? 0)*100)}%</strong><small>recent performance</small></div>
        <div><span>Review pressure</span><strong>${m.due}</strong><small>due today</small></div>
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
        const button = document.querySelector('#adaptive-minimum');
        let profile = null;
        let temporaryApplied = false;
        try {
          button?.setAttribute('disabled','disabled');
          profile = await api('/profile');
          await api('/profile',{method:'PUT',body:JSON.stringify({...profile, daily_available_minutes:45, max_session_minutes:45})});
          temporaryApplied = true;
          await api('/replan',{method:'POST',body:JSON.stringify({start_date:today(),days:1,optimizer:true,locked_session_ids:[]})});
          await api('/profile',{method:'PUT',body:JSON.stringify(profile)});
          temporaryApplied = false;
          await window.load(); window.toast?.('Minimum-day plan created without changing your normal capacity');
        } catch(e) {
          window.toast?.(e.message);
        } finally {
          if (temporaryApplied && profile) { try { await api('/profile',{method:'PUT',body:JSON.stringify(profile)}); } catch (_) {} }
          button?.removeAttribute('disabled');
        }
      });
      document.querySelector('#adaptive-export')?.addEventListener('click', async () => {
        try {
          const blob = new Blob([JSON.stringify(m,null,2)], {type:'application/json'});
          const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = 'planner-learning-state.json'; a.click(); URL.revokeObjectURL(a.href);
        } catch(e) { window.toast?.(e.message); }
      });
    } catch(e) { console.warn('adaptive-v3', e); }
  }

  function bindAdaptiveCompletion() {
    const originalOpenSession = window.openSession;
    if (originalOpenSession && !window.__adaptiveOpenWrapped) {
      window.openSession = function(id) {
        window.__adaptiveActiveSessionId = Number(id);
        return originalOpenSession.apply(this, arguments);
      };
      window.__adaptiveOpenWrapped = true;
    }
    const originalCompleteSession = window.completeSession;
    if (originalCompleteSession && !window.__adaptiveCompleteWrapped) {
      window.completeSession = async function(replanRequested) {
        const id = window.__adaptiveActiveSessionId;
        const snapshotSession = (window.__plannerSnapshot?.sessions || []).find(s => Number(s.id) === Number(id));
        const actual = Number(document.querySelector('#m-min')?.value);
        const score = Number(document.querySelector('#m-score')?.value);
        const topicId = snapshotSession?.topic_id;
        let adaptiveError = null;
        try {
          await originalCompleteSession.call(this, false);
          if (topicId && Number.isFinite(actual) && Number.isFinite(score) && score >= 0 && score <= 1) {
            await api(`/v2/topic/${encodeURIComponent(topicId)}/session-observation`, {
              method:'POST',
              body:JSON.stringify({actual_minutes:actual, performance_score:score}),
            });
          }
          if (replanRequested) await window.replanWeek();
          if (topicId) window.toast?.('Session complete · adaptive state updated');
        } catch (e) {
          adaptiveError = e;
          window.toast?.(e.message || 'Adaptive update failed');
        } finally {
          window.__adaptiveActiveSessionId = null;
        }
        return adaptiveError ? undefined : true;
      };
      window.__adaptiveCompleteWrapped = true;
    }
  }

  const originalRender = window.render;
  window.render = function(...args) {
    bindAdaptiveCompletion();
    const result = originalRender?.apply(this,args);
    setTimeout(() => { bindAdaptiveCompletion(); renderPanel(); }, 0);
    return result;
  };
  bindAdaptiveCompletion();
  window.addEventListener('load', () => { bindAdaptiveCompletion(); setTimeout(renderPanel, 100); });
})();
