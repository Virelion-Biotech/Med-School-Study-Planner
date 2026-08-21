(() => {
  const apply = () => {
    const m = localStorage.getItem('planner-ui-mode') || 'simple';
    const allowed = ['simple', 'normal', 'advanced'];
    document.documentElement.dataset.uiMode = allowed.includes(m) ? m : 'simple';
  };
  const style = document.createElement('style');
  style.textContent = `
    html[data-ui-mode="simple"] .smart-why,
    html[data-ui-mode="simple"] .change-strip,
    html[data-ui-mode="simple"] .smart-readiness small { display:none !important; }
    html[data-ui-mode="simple"] .panel-head span,
    html[data-ui-mode="simple"] .stat small { display:none; }
    html[data-ui-mode="advanced"] .sidebar-status,
    html[data-ui-mode="advanced"] .change-strip { display:flex; }
    html[data-ui-mode="advanced"] .panel-head span,
    html[data-ui-mode="advanced"] .stat small { opacity:1; }
    html[data-ui-mode="normal"] .change-strip { display:flex; }
  `;
  document.head.appendChild(style);
  apply();
  window.addEventListener('DOMContentLoaded', apply);
  window.addEventListener('planner:ready', apply);
})();
