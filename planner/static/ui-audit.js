(() => {
  const q = (s, r=document) => r.querySelector(s);
  const qs = (s, r=document) => [...r.querySelectorAll(s)];
  const mode = () => window.__plannerMode || (window.location.search.includes('school') ? 'school' : 'personal');
  const modeLabel = () => mode() === 'usmle' ? 'USMLE Step 1' : mode() === 'school' ? (window.__plannerSchool || 'Medical School') : 'Personal Planner';
  const isUSMLE = () => mode() === 'usmle';

  function refreshChrome() {
    const label = modeLabel();
    const reset = q('#reset-btn');
    if (reset) {
      reset.textContent = 'Change plan';
      reset.title = 'Choose a different planning mode';
      reset.onclick = e => { e.preventDefault(); window.openPlannerSetup?.(); };
    }
    const tip = q('.sidebar-tip');
    if (tip) {
      const strong = q('strong', tip), small = q('small', tip);
      if (strong) strong.textContent = label;
      if (small) small.textContent = isUSMLE() ? 'Official blueprint + current block' : mode() === 'school' ? 'Starter curriculum from your school' : 'Your own subjects and deadlines';
      const span = q('span', tip); if (span) span.textContent = 'CURRENT PLAN';
    }
    const titles = {
      curriculum: isUSMLE() ? ['Curriculum', 'What you need to study, ranked by exam importance.'] : mode() === 'school' ? ['My Courses', 'Your school courses and the topics inside them.'] : ['My Subjects', 'Your subjects and topics, with no board-exam assumptions.'],
      exams: ['Exams & Deadlines', 'Dates tell the planner what needs attention first.'],
      insights: ['Progress', 'See what you are learning and how the planner is adapting.'],
      week: ['My Week', 'Your study plan for the next seven days.'],
      today: ['Today', 'The sessions you should focus on today.']
    };
    const v = window.__plannerCurrentView;
    if (v && titles[v]) {
      const h=q('#title'), p=q('#subtitle'); if(h) h.textContent=titles[v][0]; if(p) p.textContent=titles[v][1];
    }
  }

  function rewriteViewLabels() {
    const label = modeLabel();
    const view = q('#view'); if (!view) return;
    // Primary page/panel headings.
    qs('.panel, .hero', view).forEach(panel => {
      const text = panel.textContent || '';
      qs('.kicker', panel).forEach(k => {
        const t = k.textContent.trim();
        if (t === 'WHY THIS MATTERS') k.textContent = isUSMLE() ? 'WHY IT IS PRIORITIZED' : 'WHY IT IS SCHEDULED';
        if (t === 'LEARNING LOOP') k.textContent = 'HOW THE PLANNER LEARNS';
        if (t === 'WEEKLY PLAN') k.textContent = 'YOUR WEEK';
        if (t === 'CURRICULUM') k.textContent = mode() === 'school' ? 'YOUR COURSES' : 'YOUR CURRICULUM';
        if (t === 'EXAM') k.textContent = 'EXAM / DEADLINE';
      });
      qs('h2', panel).forEach(h => {
        if (h.textContent.includes('Blueprint pressure')) h.textContent = isUSMLE() ? 'What is most important?' : 'What is driving your schedule?';
        if (h.textContent.includes('Preloaded from your exam blueprint')) h.textContent = mode() === 'school' ? 'Your school courses' : 'Your subjects and topics';
      });
      qs('.panel-head span', panel).forEach(s => {
        if (s.textContent.includes('Importance is already assigned')) s.textContent = isUSMLE() ? 'Exam importance is already used to rank these.' : 'The planner uses deadlines, workload and performance to rank these.';
      });
    });

    // Exam action must never silently launch a Step 1 reset outside USMLE mode.
    qs('.panel button').forEach(btn => {
      const t = btn.textContent.trim();
      if (t === 'Regenerate Step 1' || t === 'Start Step 1') {
        btn.textContent = isUSMLE() ? (t === 'Regenerate Step 1' ? 'Rebuild Step 1 plan' : 'Set up Step 1') : 'Update this plan';
      }
    });

    // The curriculum button is an action in a personal/school plan, not a USMLE-only editor.
    qs('button').forEach(btn => {
      if (btn.textContent.trim() === '+ Topic') btn.textContent = '+ Add topic';
      if (btn.textContent.trim() === 'Save + replan') btn.textContent = 'Save settings';
      if (btn.textContent.trim() === 'View week') btn.textContent = 'See my week';
      if (btn.textContent.trim() === 'Generate week') btn.textContent = 'Build this week';
      if (btn.textContent.trim() === 'Replan week') btn.title = 'Rebuild the remaining week using your current settings';
      if (btn.textContent.trim() === 'Recalibrate') btn.title = 'Use your logged study time and scores to update workload estimates';
    });
  }

  document.addEventListener('click', e => {
    const btn = e.target.closest('button'); if (!btn) return;
    const text = btn.textContent.trim();
    // Onboarding's old "Build my own plan" route must open the actual setup.
    if (text === 'Build my own plan') {
      e.preventDefault(); e.stopImmediatePropagation(); window.startPersonalPlanner?.(); return;
    }
    // Prevent the exam page from launching the Step 1 preset in school/personal mode.
    if ((text === 'Update this plan' || text === 'Regenerate Step 1' || text === 'Start Step 1') && !isUSMLE()) {
      e.preventDefault(); e.stopImmediatePropagation(); window.openPlannerSetup?.();
    }
  }, true);

  // Track the current navigation view and refresh semantic labels after each render.
  qs('.nav').forEach(btn => btn.addEventListener('click', () => {
    window.__plannerCurrentView = btn.dataset.view;
    setTimeout(() => { refreshChrome(); rewriteViewLabels(); }, 0);
  }));

  const observer = new MutationObserver(() => {
    refreshChrome(); rewriteViewLabels();
  });
  const view = q('#view'); if (view) observer.observe(view, {subtree:true, childList:true});
  setTimeout(() => { refreshChrome(); rewriteViewLabels(); }, 0);
})();
