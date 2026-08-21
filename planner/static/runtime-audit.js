(() => {
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {
    headers: {'Content-Type': 'application/json', ...(options.headers || {})},
    ...options,
  }).then(async response => {
    let body = {};
    try { body = await response.json(); } catch (_) {}
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  });

  async function sync() {
    try {
      const [snapshot, profile] = await Promise.all([api('/snapshot'), api('/profile')]);
      window.__plannerSnapshot = snapshot;
      window.__plannerProfile = profile;
      document.dispatchEvent(new CustomEvent('planner:ready'));
    } catch (_) {
      // The core app already renders its offline state; don't replace it here.
    }
  }

  function bindNavigationFallback() {
    const nav = document.querySelector('#nav');
    if (!nav || nav.dataset.runtimeBound) return;
    nav.dataset.runtimeBound = '1';
    nav.addEventListener('click', event => {
      const button = event.target.closest('.nav[data-view]');
      if (!button || !window.setView) return;
      window.setView(button.dataset.view);
    });
  }

  function bindModeFallback() {
    const button = document.querySelector('#mode-btn');
    if (!button || button.dataset.runtimeBound) return;
    button.dataset.runtimeBound = '1';
    button.addEventListener('click', () => {
      if (window.openPlannerSetup) window.openPlannerSetup();
      else if (window.openSchoolPicker) window.openSchoolPicker();
    });
  }

  function boot() {
    bindNavigationFallback();
    bindModeFallback();
    sync();
  }

  document.addEventListener('DOMContentLoaded', boot);
  window.addEventListener('load', () => setTimeout(boot, 50));
  document.addEventListener('planner:ready', () => {
    bindNavigationFallback();
    bindModeFallback();
  });
})();
