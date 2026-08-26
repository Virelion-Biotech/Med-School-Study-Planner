(() => {
  // Real-user compatibility fixes kept outside the legacy app bundle.
  const showToast = (message) => {
    const toast = document.querySelector('#toast');
    if (toast) {
      toast.textContent = String(message || '');
      toast.classList.add('show');
      setTimeout(() => toast.classList.remove('show'), 2600);
    }
  };

  const fixSessionSubject = async (id) => {
    const modal = document.querySelector('#modal');
    if (!modal) return;
    const subject = modal.querySelector('.modal-card p');
    if (!subject || !subject.textContent.includes('[object Object]')) return;

    if (!window.__plannerActiveSnapshot) {
      try {
        const response = await fetch(window.plannerApiUrl('/snapshot'));
        if (response.ok) window.__plannerActiveSnapshot = await response.json();
      } catch {}
    }
    const raw = String(subject.textContent);
    const parts = raw.split(' · ');
    const session = window.__plannerActiveSnapshot?.sessions?.find?.(s => Number(s.id) === Number(id));
    const topic = window.__plannerActiveSnapshot?.topics?.find?.(t => t.id === session?.topic_id);
    const subjectRow = window.__plannerActiveSnapshot?.subjects?.find?.(s => s.id === topic?.subject_id);
    subject.textContent = `${subjectRow?.name || 'Subject'} · ${parts.slice(1).join(' · ')}`;
  };

  const originalOpenSession = window.openSession;
  if (typeof originalOpenSession === 'function') {
    window.openSession = (id) => {
      originalOpenSession(id);
      queueMicrotask(() => { void fixSessionSubject(id); });
    };
  }

  const patchOwnPlanButton = () => {
    document.querySelectorAll('#view button').forEach((button) => {
      if (button.textContent.trim() === 'Build my own plan') {
        button.removeAttribute('onclick');
        button.onclick = () => {
          if (typeof window.startPersonalPlanner === 'function') window.startPersonalPlanner();
          else showToast('Personal planner is unavailable');
        };
      }
    });
  };

  const originalLoad = window.load;
  if (typeof originalLoad === 'function') {
    window.load = async (...args) => {
      const result = await originalLoad(...args);
      try {
        const response = await fetch(window.plannerApiUrl('/snapshot'));
        if (response.ok) window.__plannerActiveSnapshot = await response.json();
      } catch {}
      patchOwnPlanButton();
      return result;
    };
  }

  window.replanWeek = async () => {
    try {
      const today = new Date().toISOString().slice(0, 10);
      const response = await fetch(window.plannerApiUrl('/v2/plan/persist'), {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
          start_date: today,
          days: 7,
          current_block: null,
          weights: {},
          blocked_minutes_by_day: {},
          preallocated_subject_minutes: {},
          preallocated_topic_minutes: {},
        }),
      });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
      if (typeof window.load === 'function') await window.load();
      showToast('Week replanned with the adaptive engine');
    } catch (error) {
      showToast(error.message || 'Could not rebuild the week');
    }
  };

  const observer = new MutationObserver(patchOwnPlanButton);
  const start = () => {
    const root = document.querySelector('#view');
    if (root) observer.observe(root, {childList: true, subtree: true});
    patchOwnPlanButton();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
