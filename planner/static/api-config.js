/*
 * GitHub Pages / local API configuration.
 *
 * Set window.PLANNER_API_BASE to your public FastAPI URL for production.
 * Local FastAPI development defaults to http://127.0.0.1:8000.
 */
window.PLANNER_API_BASE = window.PLANNER_API_BASE ||
  (window.location.hostname.endsWith('.github.io')
    ? 'https://REPLACE_WITH_YOUR_BACKEND_URL'
    : 'http://127.0.0.1:8000');

window.plannerApiUrl = function(path) {
  const base = String(window.PLANNER_API_BASE || '').replace(/\/$/, '');
  return `${base}${path}`;
};

// The existing UI uses root-relative fetch('/api-path') throughout.
// Redirect API calls to the configured backend while leaving static assets alone.
const nativeFetch = window.fetch.bind(window);
const API_PREFIXES = [
  '/health', '/profile', '/subjects', '/topics', '/exams', '/plan', '/replan',
  '/sessions', '/analytics', '/memory', '/calibrate', '/snapshot', '/export'
];
window.fetch = function(input, init) {
  if (typeof input === 'string' && API_PREFIXES.some(prefix => input === prefix || input.startsWith(prefix + '/'))) {
    return nativeFetch(window.plannerApiUrl(input), init);
  }
  return nativeFetch(input, init);
};
