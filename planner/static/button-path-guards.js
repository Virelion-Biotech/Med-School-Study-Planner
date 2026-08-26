(() => {
  function guard() {
    const tools = document.querySelector('#smart-tools');
    if (tools) {
      tools.removeAttribute('data-view');
      tools.onclick = (event) => {
        event.preventDefault();
        event.stopPropagation();
        if (typeof window.openTools === 'function') window.openTools();
      };
    }

    const replan = document.querySelector('#replan-btn');
    if (replan && typeof window.replanWeek === 'function') {
      replan.onclick = (event) => {
        event.preventDefault();
        return window.replanWeek();
      };
    }

    const reset = document.querySelector('#reset-btn');
    if (reset && typeof window.openPlannerSetup === 'function') {
      reset.onclick = (event) => {
        event.preventDefault();
        return window.openPlannerSetup();
      };
    }

    const mode = document.querySelector('#mode-btn');
    if (mode && typeof window.openPlannerSetup === 'function') {
      mode.onclick = (event) => {
        event.preventDefault();
        return window.openPlannerSetup();
      };
    }
  }

  guard();
  const observer = new MutationObserver(guard);
  const start = () => {
    if (document.body) observer.observe(document.body, {childList: true, subtree: true});
    guard();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
