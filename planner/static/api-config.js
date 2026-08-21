/* Public API routing for local FastAPI and GitHub Pages. */
window.PLANNER_API_BASE = window.PLANNER_API_BASE ||
  (window.location.hostname.endsWith('.github.io')
    ? 'https://REPLACE_WITH_YOUR_BACKEND_URL'
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
window.plannerApiUrl = path => `${String(window.PLANNER_API_BASE).replace(/\/$/, '')}${path}`;
const nativeFetch = window.fetch.bind(window);
const API_PREFIXES = ['/health','/profile','/subjects','/topics','/exams','/plan','/replan','/setup','/presets','/sessions','/analytics','/memory','/calibrate','/snapshot','/export'];
const isPlannerApi = input => typeof input === 'string' && (
  API_PREFIXES.some(p => input === p || input.startsWith(`${p}/`)) ||
  input.startsWith(String(window.PLANNER_API_BASE).replace(/\/$/, '') + '/')
);
window.fetch = (input, init = {}) => {
  if (!isPlannerApi(input)) return nativeFetch(input, init);
  const headers = new Headers(init.headers || {});
  headers.set('X-Planner-User', window.PLANNER_USER_ID);
  if (!headers.has('Content-Type') && init.body) headers.set('Content-Type', 'application/json');
  const target = typeof input === 'string' && input.startsWith('/') ? window.plannerApiUrl(input) : input;
  return nativeFetch(target, {...init, headers});
};
