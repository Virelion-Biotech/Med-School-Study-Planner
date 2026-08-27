/* Public API routing for local FastAPI and GitHub Pages. */
window.PLANNER_API_BASE = window.PLANNER_API_BASE ||
  (window.location.hostname.endsWith('.github.io')
    ? ''
    : 'http://127.0.0.1:8000');
window.PLANNER_USER_ID = window.PLANNER_USER_ID || (() => {
  const key = 'med-school-planner-user-id';
  let value = localStorage.getItem(key);
  if (!value) {
    value = (window.crypto && crypto.randomUUID) ? crypto.randomUUID() : `u-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    localStorage.setItem(key, value);
  }
  return value;
})();
window.PLANNER_REVISION = window.PLANNER_REVISION || (() => {
  const key = 'med-school-planner-revision';
  const raw = localStorage.getItem(key);
  if (raw === null) return null;
  const value = Number(raw);
  return Number.isSafeInteger(value) && value >= 0 ? value : null;
})();
window.plannerApiUrl = path => `${String(window.PLANNER_API_BASE).replace(/\/$/, '')}${path}`;
const nativeFetch = window.fetch.bind(window);
const API_PREFIXES = ['/health','/profile','/subjects','/topics','/exams','/plan','/replan','/setup','/presets','/sessions','/analytics','/memory','/calibrate','/snapshot','/export','/workspace','/v2'];
const isPlannerApi = input => typeof input === 'string' && (
  API_PREFIXES.some(p => input === p || input.startsWith(`${p}/`)) ||
  (window.PLANNER_API_BASE && input.startsWith(String(window.PLANNER_API_BASE).replace(/\/$/, '') + '/'))
);
const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
window.fetch = async (input, init = {}) => {
  if (!isPlannerApi(input)) return nativeFetch(input, init);
  const headers = new Headers(init.headers || {});
  const method = String(init.method || 'GET').toUpperCase();
  headers.set('X-Planner-User', window.PLANNER_USER_ID);
  if (MUTATING_METHODS.has(method) && window.PLANNER_REVISION !== null && !headers.has('X-Planner-Revision')) {
    headers.set('X-Planner-Revision', String(window.PLANNER_REVISION));
  }
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json');
  const target = typeof input === 'string' && input.startsWith('/') ? window.plannerApiUrl(input) : input;
  const response = await nativeFetch(target, {...init, headers});
  const revision = response.headers.get('X-Planner-Revision');
  if (revision !== null && /^\d+$/.test(revision)) {
    window.PLANNER_REVISION = Number(revision);
    localStorage.setItem('med-school-planner-revision', revision);
  }
  return response;
};
