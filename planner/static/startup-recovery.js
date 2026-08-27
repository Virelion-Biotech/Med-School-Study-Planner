(() => {
  const qs = (selector, root = document) => [...root.querySelectorAll(selector)];
  const toast = message => window.toast && window.toast(String(message || ''));

  function showOfflineRecovery() {
    const view = document.querySelector('#view');
    if (!view) return;
    const danger = view.querySelector('.hero.danger');
    if (!danger || danger.dataset.recoveryPatched === '1') return;
    danger.dataset.recoveryPatched = '1';
    const copy = danger.querySelector('div:first-child');
    if (!copy) return;
    const p = copy.querySelector('p');
    if (p) p.textContent = 'The planner could not reach its backend. You can still choose a planning mode; retry when the connection is available.';
    const actions = document.createElement('div');
    actions.className = 'hero-actions';
    actions.innerHTML = '<button class="btn primary" type="button" id="offline-school">Medical school</button><button class="btn secondary" type="button" id="offline-usmle">USMLE Step 1</button><button class="btn ghost" type="button" id="offline-personal">Personal planner</button><button class="btn ghost" type="button" id="offline-retry">Retry connection</button>';
    copy.appendChild(actions);
    actions.querySelector('#offline-school').onclick = () => window.openSchoolPicker?.();
    actions.querySelector('#offline-usmle').onclick = () => window.openStep1BlockPicker?.();
    actions.querySelector('#offline-personal').onclick = () => window.startPersonalPlanner?.();
    actions.querySelector('#offline-retry').onclick = () => window.load?.();
    danger.querySelector('.hero-actions')?.remove?.();
  }

  function bindSchoolButtons() {
    const selectors = '#mf-school, [data-runtime-mode="school"], #first-school, #school-direct-entry';
    qs(selectors).forEach(button => {
      if (button.dataset.schoolCaptureBound === '1') return;
      button.dataset.schoolCaptureBound = '1';
      button.addEventListener('click', event => {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (typeof window.openSchoolPicker === 'function') window.openSchoolPicker();
        else toast('Medical school setup is still loading. Please try again.');
      }, true);
    });
  }

  function startup() {
    showOfflineRecovery();
    bindSchoolButtons();
    const observer = new MutationObserver(() => {
      showOfflineRecovery();
      bindSchoolButtons();
    });
    if (document.body) observer.observe(document.body, { childList: true, subtree: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startup, { once: true });
  else startup();
})();
