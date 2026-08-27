(() => {
  const qs = (selector, root = document) => [...root.querySelectorAll(selector)];
  const toast = message => window.toast && window.toast(String(message || ''));
  const getModal = () => document.querySelector('#modal');

  const SCHOOLS = [
    {id:'bmc', name:'Batterjee Medical College', country:'Saudi Arabia', mark:'BMC', years:['Preparatory Year','Year 2','Year 3','Year 4','Year 5','Year 6','Year 7']},
    {id:'harvard', name:'Harvard Medical School', country:'United States', mark:'HMS', years:['Year 1','Year 2','Year 3','Year 4']},
    {id:'hopkins', name:'Johns Hopkins School of Medicine', country:'United States', mark:'JH', years:['Year 1','Year 2','Year 3','Year 4']},
    {id:'mayo', name:'Mayo Clinic Alix School of Medicine', country:'United States', mark:'MCA', years:['Year 1','Year 2','Year 3','Year 4']},
  ];

  function closeModal() {
    const m = getModal();
    if (!m) return;
    m.classList.add('hidden');
    m.replaceChildren();
  }

  function renderModal(html, onReady) {
    const m = getModal();
    if (!m) return null;
    m.innerHTML = `<div class="modal-card school-official startup-school-fallback"><button class="modal-close" id="startup-close" type="button" aria-label="Close">×</button>${html}</div>`;
    m.classList.remove('hidden');
    m.querySelector('#startup-close')?.addEventListener('click', closeModal);
    onReady?.(m);
    return m;
  }

  function openSchoolFallback() {
    const m = renderModal(`<div class="setup-kicker">MEDICAL SCHOOL</div><h2>Choose your medical school</h2><p class="school-copy">Choose a school, then year and current course.</p><div class="school-list">${SCHOOLS.map(s => `<button class="school-card" type="button" data-fallback-school="${s.id}"><span class="school-mark" aria-hidden="true">${s.mark}</span><span class="school-card-copy"><strong>${s.name}</strong><span>${s.country}</span><b>Choose school →</b></span></button>`).join('')}</div>`);
    m?.querySelectorAll('[data-fallback-school]').forEach(b => b.addEventListener('click', () => openYearFallback(b.dataset.fallbackSchool)));
  }

  function openYearFallback(id) {
    const school = SCHOOLS.find(s => s.id === id);
    if (!school) return openSchoolFallback();
    const m = renderModal(`<div class="setup-kicker">${school.name}</div><h2>Which year are you in?</h2><p class="school-copy">Pick your year.</p><div class="level-grid">${school.years.map(y => `<button class="mode-choice" type="button" data-fallback-year="${y}"><strong>${y}</strong><span>Continue to course selection</span><b>Select →</b></button>`).join('')}</div><button class="btn ghost school-back" id="fallback-back-school" type="button">← Back</button>`);
    m?.querySelectorAll('[data-fallback-year]').forEach(b => b.addEventListener('click', () => {
      localStorage.setItem('planner-mode','school');
      localStorage.setItem('planner-school',school.name);
      localStorage.setItem('planner-level',b.dataset.fallbackYear);
      openCourseFallback(id,b.dataset.fallbackYear);
    }));
    m?.querySelector('#fallback-back-school')?.addEventListener('click', openSchoolFallback);
  }

  function openCourseFallback(id, year) {
    const school = SCHOOLS.find(s => s.id === id);
    const courses = id === 'bmc'
      ? ['Respiration & Circulation','Digestion & Defense','Cognition & Action','Regulation & Integration','Growth & Development']
      : ['Foundations of Medicine','Integrated Medical Science','Clinical Foundations','Core Clinical Rotations','Advanced Clinical Experiences','Electives & Scholarly Work'];
    const m = renderModal(`<div class="setup-kicker">${school?.name || 'Medical school'} · ${year}</div><h2>What are you studying now?</h2><p class="school-copy">Choose the current course or block.</p><div class="course-grid">${courses.map(c => `<button class="course-choice" type="button" data-fallback-course="${c}"><strong>${c}</strong><span>Starter curriculum block</span><b>Study this →</b></button>`).join('')}</div><button class="btn ghost school-back" id="fallback-back-year" type="button">← Back</button>`);
    m?.querySelectorAll('[data-fallback-course]').forEach(b => b.addEventListener('click', () => {
      localStorage.setItem('planner-block', b.dataset.fallbackCourse);
      localStorage.setItem('planner-school-fallback','1');
      closeModal();
      toast(`${b.dataset.fallbackCourse} selected. Connect to the planner backend to generate and save the full adaptive schedule.`);
    }));
    m?.querySelector('#fallback-back-year')?.addEventListener('click', () => openYearFallback(id));
  }

  function openSchool() {
    if (typeof window.openSchoolPicker === 'function' && window.openSchoolPicker !== openSchool) {
      try { window.openSchoolPicker(); return true; } catch (_) {}
    }
    openSchoolFallback();
    return true;
  }
  window.openSchoolWhenReady = openSchool;
  window.openSchoolPicker = openSchool;

  function showOfflineRecovery() {
    const view = document.querySelector('#view');
    if (!view) return;
    const danger = view.querySelector('.hero.danger');
    if (!danger || danger.dataset.recoveryPatched === '1') return;
    danger.dataset.recoveryPatched = '1';
    const copy = danger.querySelector('div:first-child');
    if (!copy) return;
    const p = copy.querySelector('p');
    if (p) p.textContent = 'The planner backend is unavailable. Setup can still be opened, and your selection can be kept locally until the backend is available.';
    const actions = document.createElement('div');
    actions.className = 'hero-actions';
    actions.innerHTML = '<button class="btn primary" type="button" id="offline-school">Medical school</button><button class="btn secondary" type="button" id="offline-usmle">USMLE Step 1</button><button class="btn ghost" type="button" id="offline-personal">Personal planner</button><button class="btn ghost" type="button" id="offline-retry">Retry connection</button>';
    copy.appendChild(actions);
    actions.querySelector('#offline-school').onclick = openSchool;
    actions.querySelector('#offline-usmle').onclick = () => window.openStep1BlockPicker?.();
    actions.querySelector('#offline-personal').onclick = () => window.startPersonalPlanner?.();
    actions.querySelector('#offline-retry').onclick = () => window.load?.();
  }

  function bindSchoolButtons() {
    const selectors = '#mf-school, [data-runtime-mode="school"], #first-school, #school-direct-entry, #offline-school';
    qs(selectors).forEach(button => {
      if (button.dataset.startupSchoolBound === '1') return;
      button.dataset.startupSchoolBound = '1';
      button.addEventListener('click', event => {
        event.preventDefault();
        event.stopImmediatePropagation();
        openSchool();
      }, true);
    });
  }

  function startup() {
    showOfflineRecovery();
    bindSchoolButtons();
    const observer = new MutationObserver(() => { showOfflineRecovery(); bindSchoolButtons(); });
    if (document.body) observer.observe(document.body, {childList:true,subtree:true});
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', startup, {once:true});
  else startup();
})();
