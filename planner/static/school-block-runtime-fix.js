(() => {
  const toast = message => window.toast && window.toast(String(message || ''));
  const api = async (path, options = {}) => {
    const response = await fetch(window.plannerApiUrl(path), {
      headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
      ...options,
    });
    let body = {};
    try { body = await response.json(); } catch {}
    if (!response.ok) {
      const detail = typeof body.detail === 'string' ? body.detail : body.detail?.message;
      const error = new Error(detail || `HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return body;
  };

  // Never leave a successful school/block selection looking like a generic load failure.
  const originalLoad = window.load;
  if (typeof originalLoad === 'function' && !window.__schoolLoadRecoveryInstalled) {
    window.__schoolLoadRecoveryInstalled = true;
    window.load = async function (...args) {
      try {
        return await originalLoad(...args);
      } catch (error) {
        try {
          await api('/health', { headers: { 'Cache-Control': 'no-cache' } });
        } catch (healthError) {
          toast(`Planner backend unavailable (${healthError.status ? `HTTP ${healthError.status}` : healthError.message}). Your selection was saved; retry when the backend is available.`);
          return null;
        }
        toast(`Dashboard refresh failed (${error.status ? `HTTP ${error.status}` : error.message}). Your school/block selection was saved. Tap Retry to reload.`);
        const toastNode = document.querySelector('#toast');
        if (toastNode && !document.querySelector('#school-load-retry')) {
          const retry = document.createElement('button');
          retry.id = 'school-load-retry';
          retry.type = 'button';
          retry.className = 'text-btn';
          retry.textContent = 'Retry';
          retry.onclick = async () => { retry.remove(); await window.load(); };
          toastNode.appendChild(retry);
        }
        return null;
      }
    };
  }

  const guard = () => document.querySelectorAll('[data-school-course]').forEach(button => {
    if (button.dataset.schoolRuntimeGuard === '1') return;
    button.dataset.schoolRuntimeGuard = '1';
    button.setAttribute('aria-label', `Choose ${button.querySelector('strong')?.textContent || 'this course'} as your current block`);
  });
  guard();
  new MutationObserver(guard).observe(document.body, { childList: true, subtree: true });
})();
