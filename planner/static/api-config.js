/*
 * GitHub Pages / local API configuration.
 *
 * For production, set window.PLANNER_API_BASE to your public FastAPI URL
 * before app.js/admin.js load. For local development, localhost is used.
 */
window.PLANNER_API_BASE = window.PLANNER_API_BASE ||
  (window.location.hostname.endsWith('.github.io')
    ? 'https://REPLACE_WITH_YOUR_BACKEND_URL'
    : 'http://127.0.0.1:8000');

window.plannerApiUrl = function(path) {
  const base = String(window.PLANNER_API_BASE || '').replace(/\/$/, '');
  return `${base}${path}`;
};
