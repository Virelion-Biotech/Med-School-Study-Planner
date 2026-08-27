/* Build-time configuration for the GitHub Pages deployment. */
(() => {
  const configured = '__PLANNER_API_BASE__';
  const defaultBackend = 'https://med-school-study-planner-api.onrender.com';
  if (window.location.hostname.endsWith('.github.io')) {
    const base = configured !== '__PLANNER_API_BASE__' && configured.trim()
      ? configured.trim()
      : defaultBackend;
    window.PLANNER_API_BASE = base.replace(/\/$/, '');
  }
})();
