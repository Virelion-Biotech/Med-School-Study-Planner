(() => {
  const nav = document.querySelector('#nav');
  const view = document.querySelector('#view');
  const title = document.querySelector('#page-title');
  if (!nav || !view) return;

  nav.addEventListener('click', event => {
    const button = event.target.closest('.nav-item');
    if (!button) return;
    const target = button.dataset.view;
    window.__plannerSnapshot = (typeof state !== 'undefined' ? state.snapshot : window.__plannerSnapshot) || {};
    if (target === 'curriculum' && window.renderAdminCurriculum) {
      title.textContent = 'Curriculum';
      window.renderAdminCurriculum(view);
    } else if (target === 'exams' && window.renderAdminExams) {
      title.textContent = 'Exams';
      window.renderAdminExams(view);
    }
  });

  const enhanceInsights = async () => {
    if (typeof state === 'undefined' || state.view !== 'insights') return;
    try {
      const data = await fetch('/analytics').then(r => r.json());
      if (!view.querySelector('.analytics-extra')) {
        const wrap = document.createElement('div');
        wrap.className = 'analytics-extra';
        wrap.innerHTML = `<div class="card"><div class="section-head"><h2>Execution analytics</h2><span>actual usage feedback</span></div><div class="grid stats"><div class="card"><div class="stat-label">Completion rate</div><div class="stat-value" id="a-completion">—</div></div><div class="card"><div class="stat-label">Mean performance</div><div class="stat-value" id="a-performance">—</div></div><div class="card"><div class="stat-label">Actual vs planned</div><div class="stat-value" id="a-error">—</div></div><div class="card"><div class="stat-label">Reviews due</div><div class="stat-value" id="a-reviews">—</div></div></div><div class="drawer-actions"><a class="btn ghost" href="/export/sessions.csv">Export sessions CSV</a><a class="btn ghost" href="/export/snapshot.json">Export full snapshot</a><button class="btn primary" id="a-calibrate">Recalibrate complexity</button></div></div>`;
        view.appendChild(wrap);
        document.querySelector('#a-calibrate').onclick = async () => {
          try { const r = await fetch('/calibrate',{method:'POST'}); const out = await r.json(); if(window.toast) window.toast(`${out.count} topic complexities recalibrated`); if(window.load) await window.load(); } catch(e) { if(window.toast) window.toast(e.message); }
        };
      }
      document.querySelector('#a-completion').textContent = `${Math.round(data.completion_rate*100)}%`;
      document.querySelector('#a-performance').textContent = data.mean_performance == null ? '—' : `${Math.round(data.mean_performance*100)}%`;
      document.querySelector('#a-error').textContent = `${data.planning_error_minutes >= 0 ? '+' : ''}${data.planning_error_minutes}m`;
      document.querySelector('#a-reviews').textContent = String(data.reviews_due);
    } catch (_) {}
  };
  setInterval(enhanceInsights, 1000);
  enhanceInsights();
})();
