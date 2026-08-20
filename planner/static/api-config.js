/* Public API routing for local FastAPI and GitHub Pages. */
window.PLANNER_API_BASE = window.PLANNER_API_BASE ||
  (window.location.hostname.endsWith('.github.io')
    ? 'https://REPLACE_WITH_YOUR_BACKEND_URL'
    : 'http://127.0.0.1:8000');
window.plannerApiUrl = path => `${String(window.PLANNER_API_BASE).replace(/\/$/, '')}${path}`;
const nativeFetch = window.fetch.bind(window);
const API_PREFIXES = ['/health','/profile','/subjects','/topics','/exams','/plan','/replan','/setup','/presets','/sessions','/analytics','/memory','/calibrate','/snapshot','/export'];
window.fetch = (input, init) => {
  if (typeof input === 'string' && API_PREFIXES.some(p => input === p || input.startsWith(`${p}/`))) return nativeFetch(window.plannerApiUrl(input), init);
  return nativeFetch(input, init);
};
