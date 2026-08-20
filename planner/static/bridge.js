// Keeps the administration panels synchronized with the core planner's state object.
setInterval(() => {
  try {
    if (typeof state !== 'undefined' && state.snapshot) window.__plannerSnapshot = state.snapshot;
  } catch (_) {}
}, 250);
