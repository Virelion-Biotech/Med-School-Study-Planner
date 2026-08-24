(() => {
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function installStyle() {
    if (document.querySelector('#activity-ui-style')) return;
    const style = document.createElement('style');
    style.id = 'activity-ui-style';
    style.textContent = `
      .activity-summary{display:flex;gap:7px;flex-wrap:wrap;margin:8px 0 14px}
      .activity-summary-chip{font-size:9px;font-weight:850;color:#0f766e;background:#eaf5f2;border:1px solid #d6ebe7;border-radius:999px;padding:6px 8px;text-transform:capitalize}
      .session-activity{display:inline-block;margin-top:5px;font-size:9px;color:#0f766e;font-weight:850;text-transform:capitalize}
    `;
    document.head.appendChild(style);
  }

  function normalizeModal() {
    installStyle();
    const modal = document.querySelector('.modal-card');
    const id = window.__adaptiveActiveSessionId;
    const state = window.__plannerSnapshot || {};
    const session = (state.sessions || []).find(s => Number(s.id) === Number(id));
    if (!modal || !session) return;
    const topic = (state.topics || []).find(t => t.id === session.topic_id);
    const subject = (state.subjects || []).find(s => s.id === topic?.subject_id);
    const activity = String(session.activity_type || session.activity || 'mixed').replace(/_/g, ' ');
    const paragraph = modal.querySelector('p');
    if (paragraph) paragraph.innerHTML = `${esc(subject?.name || '')} · ${Number(session.planned_minutes || 0)} minutes · <span class="session-activity">${esc(activity)}</span>`;
  }

  const originalOpen = window.openSession;
  if (originalOpen && !window.__activityUiWrapped) {
    window.openSession = function(id) {
      window.__adaptiveActiveSessionId = Number(id);
      const result = originalOpen.apply(this, arguments);
      setTimeout(normalizeModal, 0);
      return result;
    };
    window.__activityUiWrapped = true;
  }

  const originalRender = window.render;
  if (originalRender && !window.__activityUiRenderWrapped) {
    window.render = function(...args) {
      const result = originalRender.apply(this, args);
      setTimeout(normalizeModal, 0);
      return result;
    };
    window.__activityUiRenderWrapped = true;
  }

  installStyle();
})();
