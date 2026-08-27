(() => {
  const showToast = (message) => {
    const toast = document.querySelector('#toast');
    if (toast) {
      toast.textContent = String(message || '');
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 3200);
    }
  };

  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {
    headers: {'Content-Type': 'application/json', ...(options.headers || {})},
    ...options,
  }).then(async response => {
    let body = {};
    try { body = await response.json(); } catch {}
    return {response, body};
  });

  const isPages = () => window.location.hostname.endsWith('.github.io');
  const backendReady = () => {
    const base = String(window.PLANNER_API_BASE || '').replace(/\/$/, '');
    return !!base && (!isPages() || !base.includes('github.io'));
  };

  window.replanWeek = async () => {
    const today = new Date().toISOString().slice(0, 10);
    if (!backendReady()) {
      showToast('Planner backend is not configured. The app cannot rebuild a week yet.');
      return;
    }
    const request = {
      start_date: today,
      days: 7,
      current_block: null,
      weights: {},
      blocked_minutes_by_day: {},
      preallocated_subject_minutes: {},
      preallocated_topic_minutes: {},
    };
    try {
      const {response, body} = await api('/v2/plan/persist', {method: 'POST', body: JSON.stringify(request)});
      if (response.ok) {
        await window.load?.();
        showToast('Week replanned with the adaptive engine');
        return;
      }
      if (response.status !== 404 && response.status !== 405) {
        throw new Error(body.detail || `HTTP ${response.status}`);
      }

      const legacy = await api('/replan', {
        method: 'POST',
        body: JSON.stringify({start_date: today, days: 7, optimizer: true, locked_session_ids: []}),
      });
      if (!legacy.response.ok) {
        throw new Error(legacy.body.detail || `HTTP ${legacy.response.status}`);
      }
      await window.load?.();
      showToast('Week rebuilt successfully.');
    } catch (error) {
      showToast(error.message || 'Could not rebuild the week');
    }
  };

  const patchChooserClose = () => {
    const modal = document.querySelector('#modal');
    if (!modal || modal.classList.contains('hidden')) return;
    const card = modal.querySelector('.mode-fix-card');
    if (!card || card.querySelector('#mf-close')) return;
    const close = document.createElement('button');
    close.type = 'button';
    close.id = 'mf-close';
    close.className = 'modal-close';
    close.setAttribute('aria-label', 'Close plan chooser');
    close.textContent = '×';
    close.addEventListener('click', () => {
      modal.classList.add('hidden');
      modal.innerHTML = '';
    });
    card.prepend(close);
  };

  const style = document.createElement('style');
  style.textContent = '.mode-fix-card{position:relative}.modal-close{position:absolute;top:16px;right:16px;width:36px;height:36px;border:1px solid #dce8e6;border-radius:50%;background:#f3f7f6;color:#476067;font-size:22px;line-height:34px;cursor:pointer;z-index:3}.modal-close:hover{background:#e8f1ef;color:#163238}';
  document.head.appendChild(style);

  const observer = new MutationObserver(patchChooserClose);
  const start = () => {
    patchChooserClose();
    if (document.body) observer.observe(document.body, {childList: true, subtree: true});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
})();
