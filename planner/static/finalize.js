(() => {
  const nav = document.querySelector('#nav');
  const view = document.querySelector('#view');
  const title = document.querySelector('#page-title');
  if (!nav || !view) return;

  const routeAdmin = event => {
    const button = event.target.closest('.nav-item');
    if (!button) return;
    const target = button.dataset.view;
    if (target === 'curriculum' && window.renderAdminCurriculum) {
      title.textContent = 'Curriculum';
      window.renderAdminCurriculum(view);
    }
    if (target === 'exams' && window.renderAdminExams) {
      title.textContent = 'Exams';
      window.renderAdminExams(view);
    }
  };
  nav.addEventListener('click', routeAdmin, true);

  const enhanceInsights = async () => {
    try {
      const data = await fetch('/analytics').then(r => r.json());
      if (!view.querySelector('.analytics-extra')) return;
      view.querySelector('.analytics-extra').innerHTML = `
        <div class="grid stats">
          <div class="card"><div class="stat-label">Completion rate</div><div class="stat-value">${Math.round(data.completion_rate*100)}%</div></div>
          <div class="card"><div class="stat-label">Mean performance</div><div class="stat-value">${data.mean_performance == null ? '—' : Math.round(data.mean_performance*100)+'%'}</div></div>
          <div class="card"><div class="stat-label">Actual vs planned</div><div class="stat-value">${data.planning_error_minutes >= 0 ? '+' : ''}${data.planning_error_minutes}m</div></div>
          <div class="card"><div class="stat-label">Mastery mean</div><div class="stat-value">${Math.round(data.mastery_mean*100)}%</div></div>
        </div>`;
    } catch (_) {}
  };
  const oldRender = window.render;
  window.__enhanceInsights = enhanceInsights;
  setInterval(() => {
    if (typeof state !== 'undefined' && state.view === 'insights') enhanceInsights();
  }, 1200);
})();
