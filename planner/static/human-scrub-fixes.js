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

  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {
    headers: {'Content-Type': 'application/json', ...(options.headers || {})},
    ...options,
  }).then(async response => {
    let body = {};
    try { body = await response.json(); } catch {}
    if (!response.ok) throw new Error(body.detail || `HTTP ${response.status}`);
    return body;
  });

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
      patchHeaderButtons();
      patchToolsNavigation();
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

  function patchHeaderButtons() {
    const replan = document.querySelector('#replan-btn');
    if (replan) {
      replan.onclick = (event) => {
        event?.preventDefault?.();
        if (typeof window.replanWeek === 'function') return window.replanWeek();
      };
    }

    const reset = document.querySelector('#reset-btn');
    if (reset) {
      reset.onclick = (event) => {
        event?.preventDefault?.();
        if (typeof window.openPlannerSetup === 'function') return window.openPlannerSetup();
        showToast('Plan chooser is unavailable');
      };
    }

    const mode = document.querySelector('#mode-btn');
    if (mode) {
      mode.onclick = (event) => {
        event?.preventDefault?.();
        if (typeof window.openPlannerSetup === 'function') return window.openPlannerSetup();
        showToast('Mode chooser is unavailable');
      };
    }
  }

  function patchToolsNavigation() {
    const tools = document.querySelector('#smart-tools');
    if (!tools) return;
    // Tools is a command launcher, not a planner view. Giving it data-view causes
    // the legacy nav handler to momentarily switch the main view to Today.
    tools.removeAttribute('data-view');
    tools.onclick = (event) => {
      event.preventDefault();
      event.stopPropagation();
      if (typeof window.openTools === 'function') window.openTools();
      else showToast('Tools are unavailable');
    };
  }

  function patchCustomTopic() {
    if (typeof window.addCustomTopic !== 'function' || window.__humanTopicPatched) return;
    window.__humanTopicPatched = true;
    window.addCustomTopic = () => {
      const modal = document.querySelector('#modal');
      if (!modal) return;
      const subjects = window.__plannerActiveSnapshot?.subjects || window.state?.snapshot?.subjects || [];
      if (!subjects.length) return showToast('Add a subject first.');
      modal.innerHTML = `<div class="modal-card"><div class="kicker">CURRICULUM</div><h2>Add a topic</h2><p>Choose the subject this topic belongs to.</p><div class="form-grid"><div class="field"><label>Topic name</label><input id="human-topic-name" placeholder="e.g. Heart failure"></div><div class="field"><label>Subject</label><select id="human-topic-subject">${subjects.map(s => `<option value="${String(s.id).replace(/"/g, '&quot;')}">${String(s.name).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]))}</option>`).join('')}</select></div></div><div class="drawer-actions"><button class="btn primary" id="human-topic-save">Add topic</button><button class="btn ghost" id="human-topic-cancel">Cancel</button></div></div>`;
      modal.classList.remove('hidden');
      document.querySelector('#human-topic-cancel').onclick = () => window.closeModal?.();
      document.querySelector('#human-topic-save').onclick = async () => {
        const name = document.querySelector('#human-topic-name').value.trim();
        const subjectId = document.querySelector('#human-topic-subject').value;
        if (!name) return showToast('Enter a topic name.');
        const base = name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
        const id = `${subjectId}-${base}`;
        try {
          await api('/topics', {method: 'POST', body: JSON.stringify({id, subject_id: subjectId, name, estimated_hours: 1, complexity: .5, mastery: 0, self_difficulty: 3, volume: .5, cognitive_load: .5})});
          window.closeModal?.();
          await window.load?.();
          if (window.setView) window.setView('curriculum');
          showToast('Topic added to the selected subject');
        } catch (error) {
          showToast(error.message);
        }
      };
    };
  }

  function patchStartNext() {
    if (typeof window.startNext !== 'function' || window.__humanStartNextPatched) return;
    window.__humanStartNextPatched = true;
    window.startNext = () => {
      const snapshot = window.__plannerActiveSnapshot || window.state?.snapshot || {sessions: []};
      const today = new Date().toISOString().slice(0, 10);
      const candidates = (snapshot.sessions || [])
        .filter(s => s.session_date === today && !s.completed)
        .sort((a, b) => Number(a.id || 0) - Number(b.id || 0));
      const next = candidates[0];
      if (!next) return showToast('Nothing else is scheduled today.');
      if (typeof window.openSession === 'function') window.openSession(Number(next.id));
    };
  }

  const observer = new MutationObserver(() => {
    patchOwnPlanButton();
    patchHeaderButtons();
    patchToolsNavigation();
    patchCustomTopic();
    patchStartNext();
  });

  const start = () => {
    const root = document.querySelector('#view');
    if (root) observer.observe(root, {childList: true, subtree: true});
    patchOwnPlanButton();
    patchHeaderButtons();
    patchToolsNavigation();
    patchCustomTopic();
    patchStartNext();
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, {once: true});
  else start();
})();
