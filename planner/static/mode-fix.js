(() => {
  const modal = html => {
    const m = document.querySelector('#modal');
    if (!m) return;
    m.innerHTML = `<div class="modal-card setup-modal mode-fix-card">${html}</div>`;
    m.classList.remove('hidden');
  };

  const openChooser = () => {
    modal(`
      <div class="setup-kicker">CHOOSE YOUR PLAN</div>
      <h2>What are you studying for?</h2>
      <p class="setup-copy">Pick one. The planner will use the right starting point for you.</p>
      <div class="mode-grid mode-fix-grid">
        <button type="button" class="mode-choice" id="mf-usmle">
          <strong>USMLE Step 1</strong>
          <span>Official Step 1 blueprint and your current block.</span>
          <b>Use USMLE →</b>
        </button>
        <button type="button" class="mode-choice" id="mf-school">
          <strong>My medical school</strong>
          <span>Use your school's courses and study level.</span>
          <b>Choose school →</b>
        </button>
        <button type="button" class="mode-choice" id="mf-personal">
          <strong>Personal Planner</strong>
          <span>Use your own subjects, lectures, slides and exams.</span>
          <b>Build my plan →</b>
        </button>
      </div>
    `);

    document.querySelector('#mf-usmle')?.addEventListener('click', () => {
      if (typeof window.startStep1 === 'function') window.startStep1();
    });
    document.querySelector('#mf-school')?.addEventListener('click', () => {
      if (typeof window.openSchoolPicker === 'function') window.openSchoolPicker();
    });
    document.querySelector('#mf-personal')?.addEventListener('click', () => {
      if (typeof window.startPersonalPlanner === 'function') window.startPersonalPlanner();
    });
  };

  window.openPlannerSetup = openChooser;
  window.openPlanChooser = openChooser;

  const bind = () => {
    const b = document.querySelector('#mode-btn');
    if (b) {
      b.type = 'button';
      b.textContent = 'Change plan';
      b.onclick = e => { e.preventDefault(); openChooser(); };
    }

    const view = document.querySelector('#view');
    if (view && !document.querySelector('#school-direct-entry')) {
      const existing = view.querySelector('.hero-actions');
      if (existing) {
        const school = document.createElement('button');
        school.type = 'button';
        school.className = 'btn secondary big';
        school.id = 'school-direct-entry';
        school.textContent = 'Use my school';
        school.addEventListener('click', () => {
          if (typeof window.openSchoolPicker === 'function') window.openSchoolPicker();
        });
        existing.appendChild(school);
      }
    }
  };

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bind, {once:true});
  } else {
    bind();
  }
  setTimeout(bind, 250);
})();
