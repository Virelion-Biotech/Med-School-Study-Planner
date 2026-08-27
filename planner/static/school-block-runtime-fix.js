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

  // A failed dashboard refresh must never erase a successful setup or leave the user trapped.
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
        toast(`Dashboard refresh failed (${error.status ? `HTTP ${error.status}` : error.message}). Your selection was saved. Tap Retry to reload.`);
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

  async function selectStep1Block(button) {
    const blockId = button.dataset.step1Block;
    const label = button.querySelector('strong')?.textContent?.trim() || blockId;
    try {
      button.disabled = true;
      toast(`Building Step 1 around ${label}…`);
      await api('/setup/step1', {
        method: 'POST',
        body: JSON.stringify({ start_date: new Date().toISOString().slice(0, 10), current_block: blockId }),
      });
      localStorage.setItem('planner-mode', 'usmle');
      localStorage.setItem('planner-step1-block', blockId);
      window.__plannerMode = 'usmle';
      window.__plannerBlock = label;
      const modal = document.querySelector('#modal');
      if (modal) { modal.classList.add('hidden'); modal.innerHTML = ''; }
      const loaded = await window.load();
      if (loaded !== null && loaded !== undefined) toast(`${label} is now your focus`);
    } catch (error) {
      button.disabled = false;
      const status = error.status ? `HTTP ${error.status}: ` : '';
      toast(`${status}${error.message || 'Could not load this block'}. Your previous plan was not replaced.`);
    }
  }

  // Intercept the Step 1 block action so there is exactly one authoritative handler.
  document.addEventListener('click', event => {
    const button = event.target?.closest?.('[data-step1-block]');
    if (!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    selectStep1Block(button);
  }, true);

  function guard() {
    document.querySelectorAll('[data-school-course], [data-step1-block]').forEach(button => {
      if (button.dataset.schoolRuntimeGuard === '1') return;
      button.dataset.schoolRuntimeGuard = '1';
      const label = button.querySelector('strong')?.textContent || 'this choice';
      button.setAttribute('aria-label', `Choose ${label} as your current block`);
    });

    const modal = document.querySelector('#modal');
    if (modal?.querySelector('[data-step1-block]') && !modal.querySelector('#step1-block-close')) {
      const card = modal.querySelector('.modal-card');
      if (card) {
        const close = document.createElement('button');
        close.type = 'button';
        close.id = 'step1-block-close';
        close.className = 'modal-close';
        close.setAttribute('aria-label', 'Close Step 1 block chooser');
        close.textContent = '×';
        close.addEventListener('click', () => {
          modal.classList.add('hidden');
          modal.innerHTML = '';
        });
        card.prepend(close);
      }
    }
  }

  guard();
  new MutationObserver(guard).observe(document.body, { childList: true, subtree: true });
})();
