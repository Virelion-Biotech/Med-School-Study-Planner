(() => {
  const REVISION_KEY = 'med-school-planner-revision';
  const USER_KEY = 'med-school-planner-user-id';
  const originalFetch = window.fetch.bind(window);
  const getRevision = () => localStorage.getItem(REVISION_KEY) || '';
  const getUser = () => localStorage.getItem(USER_KEY) || '';
  const mutation = method => ['POST','PUT','PATCH','DELETE'].includes(String(method || 'GET').toUpperCase());

  window.fetch = async (input, init = {}) => {
    const headers = new Headers(init.headers || (input instanceof Request ? input.headers : undefined));
    const method = String(init.method || (input instanceof Request ? input.method : 'GET')).toUpperCase();
    const url = typeof input === 'string' ? input : input.url;
    if (url && mutation(method) && !headers.has('X-Planner-Revision')) {
      const revision = getRevision();
      if (revision) headers.set('X-Planner-Revision', revision);
    }
    if (url && !headers.has('X-Planner-User')) {
      const user = getUser();
      if (user) headers.set('X-Planner-User', user);
    }
    const response = await originalFetch(input, {...init, headers});
    const next = response.headers.get('X-Planner-Revision');
    if (next != null) localStorage.setItem(REVISION_KEY, next);
    if (response.status === 409) {
      let detail = {};
      try { detail = await response.clone().json(); } catch {}
      if (window.plannerSync?.showConflict) window.plannerSync.showConflict(detail);
      else window.dispatchEvent(new CustomEvent('planner:mutation-conflict', {detail}));
    }
    return response;
  };
})();
