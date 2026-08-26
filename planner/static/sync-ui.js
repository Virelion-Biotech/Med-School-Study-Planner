(() => {
  const REVISION_KEY = 'med-school-planner-revision';
  const USER_KEY = 'med-school-planner-user-id';
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  });

  const getRevision = () => Number(localStorage.getItem(REVISION_KEY) || '0');
  const setRevision = value => {
    const n = Number(value);
    if (Number.isFinite(n) && n >= 0) localStorage.setItem(REVISION_KEY, String(n));
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

  async function state() {
    const response = await api('/workspace/state', {
      headers: { 'X-Planner-User': ensureUser() },
    });
    applyRevision(response);
    if (!response.ok) throw new Error(`Workspace state failed (${response.status})`);
    const data = await response.json();
    if (data.revision != null) setRevision(data.revision);
    window.__plannerWorkspaceState = data;
    return data;
  }

  async function reconcile(payload) {
    const response = await api('/v2/reconcile/sessions', {
      method: 'POST',
      headers: {
        'X-Planner-User': ensureUser(),
        'X-Planner-Revision': String(getRevision()),
      },
      body: JSON.stringify(payload),
    });
    applyRevision(response);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw Object.assign(new Error(data.detail || `Reconcile failed (${response.status})`), { status: response.status, data });
    return data;
  }

  function showConflict(detail) {
    const current = Number(detail?.current);
    if (Number.isFinite(current)) setRevision(current);
    const conflicts = Array.isArray(detail?.conflicts) ? detail.conflicts : [];
    const suffix = conflicts.length ? ` ${conflicts.length} session conflict${conflicts.length === 1 ? '' : 's'} need review.` : '';
    notify(`Your plan changed on another device. Refreshing the latest state.${suffix}`, 'error');
    window.dispatchEvent(new CustomEvent('planner:workspace-conflict', { detail }));
  }

  async function refresh() {
    try {
      return await state();
    } catch (error) {
      notify(error.message || 'Could not refresh planner state.', 'error');
      return null;
    }
  }

  window.plannerSync = {
    get revision() { return getRevision(); },
    get userId() { return ensureUser(); },
    setRevision,
    state,
    refresh,
    reconcile,
    applyRevision,
    showConflict,
  };

  window.addEventListener('planner:api-response', event => {
    const response = event.detail?.response;
    if (response) applyRevision(response);
  });

  window.addEventListener('planner:mutation-conflict', event => showConflict(event.detail));

  document.addEventListener('DOMContentLoaded', async () => {
    ensureUser();
    await refresh();
  });
})();
