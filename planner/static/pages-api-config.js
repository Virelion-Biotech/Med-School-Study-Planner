/* Build-time configuration for the GitHub Pages deployment. */
(() => {
  const configured = '__PLANNER_API_BASE__';
  if (window.location.hostname.endsWith('.github.io') && configured !== '__PLANNER_API_BASE__') {
    window.PLANNER_API_BASE = configured.replace(/\/$/, '');
  }
})();
