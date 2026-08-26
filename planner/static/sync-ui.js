(() => {
  const REVISION_KEY = 'med-school-planner-revision';
  const USER_KEY = 'med-school-planner-user-id';
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {
    ...options,
    headers: {'Content-Type': 'application/json', ...(options.headers || {})},
  });
  const getRevision = () => Number(localStorage.getItem(REVISION_KEY) || '0');
  const setRevision = value => {
    const n = Number(value);
    if (Number.isFinite(n) && n >= 0) localStorage.setItem(REVISION_KEY, String(n));
    updateBadge();
  };
  function ensureUser() {
    let id = localStorage.getItem(USER_KEY);
    if (!id) {
      id = `web-${crypto?.randomUUID?.() || `${Date.now()}-${Math.random().toString(36).slice(2)}`}`;
      localStorage.setItem(USER_KEY, id);
    }
    return id;
  }
  function applyRevision(response) {
    const header = response.headers.get('X-Planner-Revision');
    if (header != null) setRevision(header);
  }
  function notify(message, kind = 'info') {
    if (typeof window.toast === 'function') window.toast(message);
    else console[kind === 'error' ? 'error' : 'log'](message);
  }
  function installStyle() {
    if (document.querySelector('#planner-sync-style')) return;
    const style = document.createElement('style');
    style.id = 'planner-sync-style';
    style.textContent = `.planner-sync-badge{display:inline-flex;align-items:center;gap:6px;margin-left:8px;padding:5px 8px;border:1px solid #d8e7e4;border-radius:999px;background:#f7fbfa;color:#49666a;font-size:10px;font-weight:700}.planner-sync-dot{width:7px;height:7px;border-radius:50%;background:#0f766e}.planner-sync-conflict{position:fixed;inset:auto 18px 18px auto;z-index:10000;max-width:360px;padding:16px;border:1px solid #e6d7bf;border-radius:14px;background:#fffaf2;box-shadow:0 12px 35px rgba(0,0,0,.12)}.planner-sync-conflict h3{margin:0 0 6px;font-size:14px}.planner-sync-conflict p{margin:0 0 12px;color:#66777b;font-size:12px;line-height:1.5}.planner-sync-conflict-actions{display:flex;gap:8px;justify-content:flex-end}`;
    document.head.appendChild(style);
  }
  function updateBadge() {
    const badge = document.querySelector('[data-planner-sync-badge]');
    if (badge) badge.textContent = `Synced · v${getRevision()}`;
  }
  function installBadge() {
    installStyle();
    const target = document.querySelector('.topbar .kicker');
    if (!target || document.querySelector('[data-planner-sync-badge]')) return;
    const badge = document.createElement('span');
    badge.className = 'planner-sync-badge';
    badge.dataset.plannerSyncBadge = '1';
    badge.innerHTML = '<span class="planner-sync-dot"></span> Synced';
    target.appendChild(badge);
    updateBadge();
  }
  async function state() {
    const response = await api('/workspace/state', {headers: {'X-Planner-User': ensureUser()}});
    applyRevision(response);
    if (!response.ok) throw new Error(`Workspace state failed (${response.status})`);
    const data = await response.json();
    if (data.revision != null) setRevision(data.revision);
    window.__plannerWorkspaceState = data;
    return data;
  }
  async function reconcile(payload) {
    const response = await api('/v2/reconcile/sessions', {
      method:'POST',
      headers:{'X-Planner-User':ensureUser(),'X-Planner-Revision':String(getRevision())},
      body:JSON.stringify(payload),
    });
    applyRevision(response);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw Object.assign(new Error(data.detail || `Reconcile failed (${response.status})`), {status:response.status,data});
    return data;
  }
  function showConflict(detail = {}) {
    const current = Number(detail.current);
    if (Number.isFinite(current)) setRevision(current);
    document.querySelector('[data-planner-sync-conflict]')?.remove();
    installStyle();
    const conflicts = Array.isArray(detail.conflicts) ? detail.conflicts : [];
    const box = document.createElement('section');
    box.className = 'planner-sync-conflict';
    box.dataset.plannerSyncConflict = '1';
    box.setAttribute('role', 'alertdialog');
    box.innerHTML = `<h3>Plan changed elsewhere</h3><p>Another tab or device changed your planner while this screen was open.${conflicts.length ? ` ${conflicts.length} session${conflicts.length === 1 ? '' : 's'} may need review.` : ''}</p><div class="planner-sync-conflict-actions"><button class="btn secondary" data-sync-dismiss type="button">Keep editing</button><button class="btn primary" data-sync-refresh type="button">Refresh plan</button></div>`;
    box.querySelector('[data-sync-dismiss]').addEventListener('click', () => box.remove());
    box.querySelector('[data-sync-refresh]').addEventListener('click', async () => {
      box.remove();
      await refresh();
      if (typeof window.render === 'function') window.render();
    });
    document.body.appendChild(box);
    window.dispatchEvent(new CustomEvent('planner:workspace-conflict', {detail}));
  }
  async function refresh() {
    try { return await state(); }
    catch (error) { notify(error.message || 'Could not refresh planner state.', 'error'); return null; }
  }
  window.plannerSync = {get revision(){return getRevision();},get userId(){return ensureUser();},setRevision,state,refresh,reconcile,applyRevision,showConflict};
  window.addEventListener('planner:api-response', event => {if(event.detail?.response) applyRevision(event.detail.response);});
  window.addEventListener('planner:mutation-conflict', event => showConflict(event.detail));
  document.addEventListener('DOMContentLoaded', async () => {ensureUser(); installBadge(); await refresh();});
})();
