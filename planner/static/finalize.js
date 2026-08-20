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

  const loadAnalytics = async () => {
    try { window.__plannerAnalytics = await fetch('/analytics').then(r => r.json()); } catch (_) {}
  };
  setInterval(loadAnalytics, 3000);
  loadAnalytics();
})();
