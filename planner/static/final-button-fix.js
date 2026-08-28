(() => {
  // Final authoritative button wiring. Loaded last so it wins over layered patches.
  const toast = (m) => {
    if (typeof window.toast === 'function') return window.toast(m);
    const el = document.querySelector('#toast');
    if (!el) return;
    el.textContent = String(m || '');
    el.classList.add('show');
    clearTimeout(window.__finalToast);
    window.__finalToast = setTimeout(() => el.classList.remove('show'), 2600);
  };

  function wireHeader() {
    const reset = document.querySelector('#reset-btn');
    if (reset) {
      reset.type = 'button';
      reset.textContent = 'Change plan';
      reset.onclick = (e) => {
        e?.preventDefault?.();
        e?.stopPropagation?.();
        if (typeof window.openPlannerSetup === 'function') window.openPlannerSetup();
        else toast('Plan chooser is unavailable');
      };
    }
    const mode = document.querySelector('#mode-btn');
    if (mode) {
      mode.type = 'button';
      mode.textContent = 'Change mode';
      mode.onclick = (e) => {
        e?.preventDefault?.();
        e?.stopPropagation?.();
        if (typeof window.openPlannerSetup === 'function') window.openPlannerSetup();
        else toast('Mode chooser is unavailable');
      };
    }
    const replan = document.querySelector('#replan-btn');
    if (replan) {
      replan.type = 'button';
      replan.removeAttribute('onclick');
      replan.onclick = (e) => {
        e?.preventDefault?.();
        e?.stopPropagation?.();
        if (typeof window.replanWeek === 'function') window.replanWeek();
        else toast('Rebuild is unavailable');
      };
    }
  }

  function wireNav() {
    document.querySelectorAll('#nav .nav').forEach((btn) => {
      if (!btn.dataset.view) return;
      btn.onclick = (e) => {
        e?.preventDefault?.();
        if (typeof window.setView === 'function') window.setView(btn.dataset.view);
        else {
          const state = window.state;
          if (state) { state.view = btn.dataset.view; }
          if (typeof window.render === 'function') window.render();
        }
      };
    });
    const tools = document.querySelector('#smart-tools');
    if (tools) {
      tools.removeAttribute('data-view');
      tools.onclick = (e) => {
        e?.preventDefault?.();
        e?.stopPropagation?.();
        if (typeof window.openTools === 'function') window.openTools();
        else toast('Tools are unavailable');
      };
    }
  }

  function wireFirstRun() {
    const bind = (sel, fn) => {
      document.querySelectorAll(sel).forEach((b) => {
        if (b.dataset.finalBound === '1') return;
        b.dataset.finalBound = '1';
        b.addEventListener('click', (e) => {
          e.preventDefault();
          e.stopPropagation();
          fn();
        }, true);
      });
    };
    bind('#first-usmle, #rf-usmle, #mf-usmle, #offline-usmle', () => {
      if (typeof window.openStep1BlockPicker === 'function') window.openStep1BlockPicker();
      else if (typeof window.startStep1 === 'function') window.startStep1();
      else toast('USMLE setup is unavailable');
    });
    bind('#first-school, #rf-school, #mf-school, #offline-school, #school-direct-entry', () => {
      if (typeof window.openSchoolWhenReady === 'function') window.openSchoolWhenReady();
      else if (typeof window.openSchoolPicker === 'function') window.openSchoolPicker();
      else toast('School setup is unavailable');
    });
    bind('#first-personal, #rf-personal, #mf-personal, #offline-personal', () => {
      if (typeof window.startPersonalPlanner === 'function') window.startPersonalPlanner();
      else toast('Personal planner is unavailable');
    });
    document.querySelectorAll('#view button').forEach((b) => {
      if (b.textContent.trim() !== 'Build my own plan') return;
      if (b.dataset.finalBound === '1') return;
      b.dataset.finalBound = '1';
      b.removeAttribute('onclick');
      b.addEventListener('click', (e) => {
        e.preventDefault();
        if (typeof window.startPersonalPlanner === 'function') window.startPersonalPlanner();
        else if (typeof window.setView === 'function') window.setView('curriculum');
      }, true);
    });
  }

  function applyAll() {
    wireHeader();
    wireNav();
    wireFirstRun();
  }

  const start = () => {
    applyAll();
    const obs = new MutationObserver(() => applyAll());
    if (document.body) obs.observe(document.body, { childList: true, subtree: true });
  };

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start, { once: true });
  else start();
  setTimeout(applyAll, 0);
  setTimeout(applyAll, 250);
  setTimeout(applyAll, 1000);
})();
