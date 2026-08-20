(() => {
  const SCHOOL_PRESETS = {
    batterjee: {
      name: 'Batterjee Medical College',
      note: 'Starter curriculum from publicly available BMC program information. Confirm your current course list with your college before relying on it for exact scheduling.',
      levels: {
        '1': [
          ['Human Biology I', 'Biology'], ['General Chemistry', 'Chemistry'], ['General Physics', 'Physics'],
          ['Mathematics', 'Foundation'], ['English I', 'Foundation'], ['Computer I', 'Foundation'],
          ['Islamic Medical Ethics', 'Professional'], ['Study Skills I', 'Study skills'], ['Medical Terminology I', 'Medicine'],
          ['Medical Terminology II', 'Medicine'], ['Integrated Basic Science Course', 'Integrated basic science'],
          ['English II', 'Foundation'], ['Computer II', 'Foundation'], ['Arabic Language', 'Foundation'], ['Study Skills II', 'Study skills']
        ],
        '2': [['Integrated medical sciences', 'Pre-clinical'], ['Anatomy', 'Pre-clinical'], ['Physiology', 'Pre-clinical'], ['Biochemistry', 'Pre-clinical']],
        '3': [['Pathology', 'Pre-clinical'], ['Pharmacology', 'Pre-clinical'], ['Microbiology', 'Pre-clinical'], ['Immunology', 'Pre-clinical']],
        '5': [['Internal Medicine', 'Clinical'], ['Surgery', 'Clinical'], ['Pediatrics', 'Clinical'], ['Obstetrics & Gynecology', 'Clinical']],
        '6': [['Medicine clerkship', 'Clinical'], ['Surgery clerkship', 'Clinical'], ['Family Medicine', 'Clinical'], ['Psychiatry', 'Clinical']],
        '7': [['Internship / clinical training', 'Internship']]
      }
    }
  };

  const escSchool = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const slugSchool = v => String(v).toLowerCase().trim().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const schoolApi = (path, options={}) => fetch(window.plannerApiUrl(path), {headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options}).then(async r => { let b={}; try{b=await r.json()}catch{} if(!r.ok) throw Error(b.detail || `HTTP ${r.status}`); return b; });
  const schoolModal = html => { const m=document.querySelector('#modal'); if(!m)return; m.innerHTML=`<div class="modal-card setup-modal">${html}</div>`; m.classList.remove('hidden'); };
  const closeSchool = () => { const m=document.querySelector('#modal'); if(m){m.classList.add('hidden');m.innerHTML='';} };
  const schoolToast = m => window.toast && window.toast(m);

  async function setupSchoolPreset(key){
    const preset = SCHOOL_PRESETS[key];
    if(!preset)return;
    const level = document.querySelector('#school-level').value;
    const rows = preset.levels[level] || [];
    if(!rows.length){schoolToast('This level does not have a populated public starter list yet.');return;}
    const daily = Number(document.querySelector('#school-daily').value) || 240;
    try{
      schoolToast(`Loading ${preset.name}…`);
      const subjects = [];
      const topics = [];
      for(const [course, category] of rows){
        const sid = `${key}-level-${level}-${slugSchool(course)}`;
        subjects.push({id:sid,name:course,exam_weight:1,category:`${preset.name} · Level ${level} · ${category}`});
        topics.push({id:`${sid}-core`,subject_id:sid,name:`${course} — core review`,estimated_hours:2,mastery:0,complexity:.5,self_difficulty:3,volume:.5,cognitive_load:.6});
      }
      for(const s of subjects) await schoolApi('/subjects',{method:'POST',body:JSON.stringify(s)});
      for(const t of topics) await schoolApi('/topics',{method:'POST',body:JSON.stringify(t)});
      await schoolApi('/profile',{method:'PUT',body:JSON.stringify({daily_available_minutes:daily,minimum_subject_minutes_week:30,review_fraction:.25,max_session_minutes:60,rest_weekdays:[],energy_pattern:['high','high','medium','medium']})});
      const snap=await schoolApi('/snapshot');
      await schoolApi('/plan',{method:'POST',body:JSON.stringify({
        subjects:(snap.subjects||[]).map(s=>({id:s.id,name:s.name,exam_weight:s.exam_weight,category:s.category})),
        topics:(snap.topics||[]).map(t=>({id:t.id,subject_id:t.subject_id,name:t.name,complexity:t.complexity,estimated_hours:t.estimated_hours,mastery:t.mastery,self_difficulty:t.self_difficulty,volume:t.volume,cognitive_load:t.cognitive_load,last_studied:t.last_studied,next_review_due:t.next_review_due})),
        exams:(snap.exams||[]).map(e=>({id:e.id,date:e.exam_date,subject_ids:JSON.parse(e.subject_ids_json||'[]'),topic_ids:JSON.parse(e.topic_ids_json||'[]'),weight:e.weight})),
        profile:{daily_available_minutes:daily,minimum_subject_minutes_week:30,review_fraction:.25,max_session_minutes:60,rest_weekdays:[],energy_pattern:['high','high','medium','medium']},
        start_date:new Date().toISOString().slice(0,10),days:7,optimizer:true,persist:true,replace_uncompleted:true
      })});
      closeSchool(); window.__plannerMode='school'; window.__plannerSchool=preset.name; window.__plannerLevel=level;
      await window.load(); if(window.setView) window.setView('today'); schoolToast(`${preset.name} Level ${level} plan ready`);
    }catch(e){schoolToast(e.message)}
  }

  function schoolPicker(){
    schoolModal(`<div class="setup-kicker">SCHOOL PLANNER</div><h2>Use your medical school curriculum</h2><p class="setup-copy">Pick your school when we have a starter curriculum. We can add more schools over time; choose Other school for any curriculum you want to enter yourself.</p><div class="school-grid"><button class="school-choice" id="school-batterjee"><strong>Batterjee Medical College</strong><span>Public-data starter · select your level</span><b>Use Batterjee →</b></button><button class="school-choice" id="school-other"><strong>Other school</strong><span>Use the simple personal setup and enter your own courses.</span><b>Enter my curriculum →</b></button></div><div class="school-note">School presets are starter templates, not official exam timetables. Your college can update course structures, so keep your own timetable as the final source of truth.</div>`);
    document.querySelector('#school-batterjee').onclick=()=>{
      schoolModal(`<div class="setup-kicker">BATTERJEE MEDICAL COLLEGE</div><h2>Which level are you in?</h2><p class="setup-copy">Choose your current level and how much time you can study each day.</p><div class="form-grid"><div class="field"><label>Level</label><select id="school-level"><option value="1">Level 1</option><option value="2">Level 2</option><option value="3">Level 3</option><option value="5">Level 5</option><option value="6">Level 6</option><option value="7">Level 7 / Internship</option></select></div><div class="field"><label>Minutes per day</label><input id="school-daily" type="number" min="30" max="720" value="240"></div></div><div class="school-note">BMC describes a pre-clinical phase in years 1–3, clinical years 5–6, and internship year 7. The public starter list is intentionally conservative where exact current course details were not available.</div><div class="setup-actions"><button class="btn secondary" id="school-back">Back</button><button class="btn primary" id="school-build">Build my Batterjee plan →</button></div>`);
      document.querySelector('#school-back').onclick=schoolPicker;
      document.querySelector('#school-build').onclick=()=>setupSchoolPreset('batterjee');
    };
    document.querySelector('#school-other').onclick=()=>window.startPersonalPlanner ? window.startPersonalPlanner() : undefined;
  }

  window.openSchoolPicker = schoolPicker;
  const previousMode = window.openPlannerSetup;
  window.openPlannerSetup = () => schoolModal(`<div class="setup-kicker">CHOOSE A MODE</div><h2>How do you want to plan?</h2><p class="setup-copy">Use a board blueprint, your school's curriculum, or make your own plan.</p><div class="mode-grid"><button class="mode-choice" id="mode-usmle2"><strong>USMLE Step 1</strong><span>Official blueprint + current block priority.</span><b>Board prep →</b></button><button class="mode-choice" id="mode-school2"><strong>My medical school</strong><span>Use a school curriculum when we have a starter preset.</span><b>Choose school →</b></button><button class="mode-choice" id="mode-personal2"><strong>Personal Planner</strong><span>Enter your own subjects and topics.</span><b>Build my own →</b></button></div>`);
  const setupScript = Array.from(document.scripts).find(s => s.src.endsWith('/setup.js'));
  document.querySelector('#mode-usmle2').onclick=()=>window.startStep1 && window.startStep1();
  document.querySelector('#mode-school2').onclick=schoolPicker;
  document.querySelector('#mode-personal2').onclick=()=>window.startPersonalPlanner && window.startPersonalPlanner();
  const style=document.createElement('style'); style.textContent=`.school-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.school-choice{border:1px solid #dce8e6;background:#fff;text-align:left;border-radius:14px;padding:16px;display:grid;gap:7px;color:#102a31}.school-choice:hover{border-color:#71beb6;background:#f5fbfa}.school-choice strong{font-size:17px}.school-choice span{font-size:11px;color:#71858b}.school-choice b{font-size:10px;color:#0f766e}.school-note{margin-top:14px;padding:11px 13px;background:#f4f9f8;border-radius:10px;color:#71858b;font-size:10px;line-height:1.45}@media(max-width:650px){.school-grid{grid-template-columns:1fr}}`;
  document.head.appendChild(style);
})();
