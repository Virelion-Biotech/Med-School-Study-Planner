(() => {
  const showToast = (message) => {
    const toast = document.querySelector('#toast');
    if (toast) {
      toast.textContent = String(message || '');
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2600);
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

  window.replanWeek = async () => {
    const today = new Date().toISOString().slice(0, 10);
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
      if (response.status !== 405) {
        throw new Error(body.detail || `HTTP ${response.status}`);
      }

      // A stale backend may not expose the new persistence route yet. Fall back
      // only for an actual Method Not Allowed response and tell the user exactly
      // what happened instead of trapping them in a repeated 405 error.
      const legacy = await api('/replan', {
        method: 'POST',
        body: JSON.stringify({start_date: today, days: 7, optimizer: true, locked_session_ids: []}),
      });
      if (!legacy.response.ok) throw new Error(legacy.body.detail || `HTTP ${legacy.response.status}`);
      await window.load?.();
      showToast('Week rebuilt using the compatibility planner. Refresh after the backend update to use the full adaptive engine.');
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
  style.textContent = '.modal-close{position:absolute;top:10px;right:12px;width:36px;height:36px;border:0;border-radius:50%;background:#eef5f3;color:#37565e;font-size:24px;line-height:36px;cursor:pointer;z-index:3}.modal-close:hover{background:#dcebe8}.mode-fix-card{position:relative;padding-top:28px}';
  document.head.appendChild(style);

  const observer = new MutationObserver(patchChooserClose);
  const start = () => {
    patchChooserClose();
    if (document.body) observer.observe(document.body, {childList: true, subtree: true});
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once:true});
  else start();
})();
