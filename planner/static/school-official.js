(() => {
  const SCHOOLS = {
    bmc: {id:'bmc', name:'Batterjee Medical College', country:'Saudi Arabia', mark:'BMC', years:['prep','2','3','4','5','6','7']},
    harvard: {id:'harvard', name:'Harvard Medical School', country:'United States', mark:'HMS', years:['1','2','3','4']},
    hopkins: {id:'hopkins', name:'Johns Hopkins School of Medicine', country:'United States', mark:'JH', years:['1','2','3','4']},
    mayo: {id:'mayo', name:'Mayo Clinic Alix School of Medicine', country:'United States', mark:'MCA', years:['1','2','3','4']}
  };
  const esc = v => String(v ?? '').replace(/[&<>\"']/g, c => ({'&':'&','<':'<','>':'>','\"':'"',"'":'&#39;'}[c]));
  const modal = () => document.querySelector('#modal');
  const toast = m => window.toast && window.toast(String(m || ''));
  const close = () => { const m = modal(); if (m) { m.classList.add('hidden'); m.replaceChildren(); } };
  const shell = (body) => { const m = modal(); if (!m) return null; m.innerHTML = `<div class=\"modal-card school-official\"><button class=\"modal-close\" id=\"school-close\" type=\"button\" aria-label=\"Close school chooser\">×</button>${body}</div>`; m.classList.remove('hidden'); m.querySelector('#school-close')?.addEventListener('click', close); return m; };
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options}).then(async r => { let b={}; try { b=await r.json(); } catch {} if (!r.ok) { const e=new Error(b.detail || `HTTP ${r.status}`); e.status=r.status; throw e; } return b; });

  function schoolPicker() {
    const m = shell(`<div class=\"setup-kicker\">MEDICAL SCHOOL</div><h2>Choose your medical school</h2><p class=\"school-copy\">Choose your school, then year and current course.</p><div class=\"school-list\">${Object.values(SCHOOLS).map(s => `<button class=\"school-card\" type=\"button\" data-school=\"${s.id}\"><span class=\"school-mark\" aria-hidden=\"true\">${s.mark}</span><span class=\"school-card-copy\"><strong>${esc(s.name)}</strong><span>${esc(s.country)}</span><b>Choose school →</b></span></button>`).join('')}</div><p class=\"school-disclaimer\">These marks are compact identifiers for selection and are not official institutional logos.</p>`);
    m?.querySelectorAll('[data-school]').forEach(b => b.addEventListener('click', () => yearPicker(b.dataset.school)));
  }
  function yearPicker(id) {
    const s=SCHOOLS[id]; if(!s) return schoolPicker();
    const m=shell(`<div class=\"setup-kicker\">${esc(s.name)}</div><h2>Which year are you in?</h2><p class=\"school-copy\">Pick your year.</p><div class=\"level-grid\">${s.years.map(y => `<button class=\"mode-choice\" type=\"button\" data-year=\"${esc(y)}\"><strong>${y==='prep'?'Preparatory Year':`Year ${esc(y)}`}</strong><span>Continue to course selection</span><b>Select →</b></button>`).join('')}</div><button class=\"btn ghost school-back\" id=\"school-back\" type=\"button\">← Back</button>`);
    m?.querySelectorAll('[data-year]').forEach(b=>b.addEventListener('click',()=>coursePicker(id,b.dataset.year)));
    m?.querySelector('#school-back')?.addEventListener('click',schoolPicker);
  }
  function coursePicker(id, year) {
    const s=SCHOOLS[id];
    const courses = id==='bmc' ? ['Respiration & Circulation','Digestion & Defense','Cognition & Action','Regulation & Integration','Growth & Development'] : ['Foundations of Medicine','Integrated Medical Science','Clinical Foundations','Core Clinical Rotations','Advanced Clinical Experiences','Electives & Career Exploration'];
    const m=shell(`<div class=\"setup-kicker\">${esc(s.name)} · ${year==='prep'?'PREPARATORY YEAR':`YEAR ${esc(year)}`}</div><h2>What are you studying now?</h2><p class=\"school-copy\">Choose the course or block to prioritize.</p><div class=\"course-grid\">${courses.map(c=>`<button class=\"course-choice\" type=\"button\" data-course=\"${esc(c)}\"><strong>${esc(c)}</strong><span>Starter curriculum block</span><b>Study this →</b></button>`).join('')}</div><button class=\"btn ghost school-back\" id=\"year-back\" type=\"button\">← Back</button>`);
    m?.querySelectorAll('[data-course]').forEach(b=>b.addEventListener('click',()=>buildSchool(id,year,b.dataset.course)));
    m?.querySelector('#year-back')?.addEventListener('click',()=>yearPicker(id));
  }
  function slug(v){ return String(v).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,40); }
  async function buildSchool(id, year, block) {
    const s=SCHOOLS[id];
    localStorage.setItem('planner-mode','school'); localStorage.setItem('planner-school',s.name); localStorage.setItem('planner-level',year); localStorage.setItem('planner-block',block);
    window.__plannerMode='school'; window.__plannerSchool=s.name; window.__plannerLevel=year; window.__plannerBlock=block;
    const catalog = id==='bmc'
      ? [['Growth & Development',1.0],['Cognition & Action',1.0],['Respiration & Circulation',1.3],['Digestion & Defense',1.1],['Regulation & Integration',1.0]]
      : [['Foundations of Medicine',1.0],['Integrated Medical Science',1.1],['Clinical Foundations',1.2],['Core Clinical Rotations',1.2],['Advanced Clinical Experiences',1.0]];
    const subjects = catalog.map(([name, weight], index) => ({
      id: `${id}-${slug(year)}-${index}-${slug(name)}`,
      name,
      exam_weight: name === block ? 2.2 : weight,
      category: `${s.name} · ${year==='prep'?'Preparatory Year':`Year ${year}`}`,
    }));
    const topics = subjects.map(subject => ({
      id: `${subject.id}-core`,
      subject_id: subject.id,
      name: `${subject.name} — core`,
      complexity: 0.5,
      estimated_hours: nameHours(subject.name, block),
      mastery: 0,
      self_difficulty: 3,
      volume: 0.6,
      cognitive_load: 0.6,
    }));
    try {
      toast(`Setting up ${block}…`);
      const result = await api('/plan', {method:'POST', body:JSON.stringify({
        subjects,
        topics,
        exams:[],
        profile:{daily_available_minutes:240, minimum_subject_minutes_week:30, review_fraction:0.25, max_session_minutes:60, rest_weekdays:[], energy_pattern:['high','medium','medium','low']},
        start_date:new Date().toISOString().slice(0,10),
        days:7,
        optimizer:false,
        persist:true,
        replace_uncompleted:true,
      })});
      localStorage.removeItem('planner-pending-school-selection');
      close();
      if (typeof window.load==='function') await window.load();
      toast(`${block} is now your focus · ${result.sessions?.length||0} sessions created`);
    } catch (e) {
      localStorage.setItem('planner-pending-school-selection', JSON.stringify({school_id:id, school_name:s.name, level:year, block}));
      if (e?.status === 404 || e?.status === 405) {
        close();
        toast(`${block} selected. The current backend does not support school planning yet.`);
      } else if (e?.name === 'TypeError' || /failed to fetch/i.test(String(e?.message||''))) {
        close();
        toast(`${block} saved on this device. Reconnect the planner to generate the schedule.`);
      } else {
        toast(e.message || 'Could not save the school selection');
      }
    }
  }
  function nameHours(subjectName, block){ return subjectName===block ? 3 : 2; }
  window.openSchoolPicker = schoolPicker;
  window.levelPicker = yearPicker;
  window.coursePicker = coursePicker;
  window.buildSchool = buildSchool;

  const style=document.createElement('style');
  style.textContent='.school-official{width:min(920px,100%);max-width:920px!important;max-height:min(90vh,780px);overflow:auto;position:relative}.school-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:16px 0}.school-card{display:flex;align-items:center;gap:14px;width:100%;min-height:112px;border:1px solid #dce8e6;background:#fff;border-radius:14px;padding:14px;text-align:left;cursor:pointer}.school-card:hover,.school-card:focus-visible{border-color:#71beb6;background:#f5fbfa;outline:none}.school-mark{width:58px;height:58px;min-width:58px;border-radius:12px;display:grid;place-items:center;background:#edf5f4;color:#174b50;font-weight:900;font-size:13px;border:1px solid #d5e7e4}.school-card-copy{display:grid;gap:5px;min-width:0}.school-card-copy strong{font-size:14px;color:#18343a}.school-card-copy span{font-size:10px;color:#71858b}.school-card-copy b{font-size:10px;color:#0f766e}.school-disclaimer{font-size:9px;color:#87979b;margin:4px 0}.modal-close{position:absolute;top:12px;right:12px;width:38px;height:38px;border-radius:10px;border:1px solid #dce8e6;background:#fff;color:#486167;font-size:22px;line-height:1;cursor:pointer;z-index:2}.school-back{margin-top:4px}.course-grid,.level-grid{display:grid;gap:10px}.course-choice,.mode-choice{width:100%;text-align:left;cursor:pointer}.course-choice{display:grid;gap:4px;border:1px solid #dce8e6;background:#fff;border-radius:12px;padding:13px}.course-choice:hover,.course-choice:focus-visible,.mode-choice:hover,.mode-choice:focus-visible{border-color:#71beb6;background:#f5fbfa;outline:none}.course-choice strong{font-size:13px;color:#18343a}.course-choice span,.mode-choice span{font-size:10px;color:#71858b}.course-choice b,.mode-choice b{font-size:10px;color:#0f766e}@media(max-width:700px){.school-list{grid-template-columns:1fr}.school-official{max-height:calc(100dvh - 16px);padding:16px}.school-card{min-height:88px}.school-mark{width:50px;height:50px;min-width:50px}}';
  document.head.appendChild(style);
})();
