(() => {
  const SCHOOL_PRESETS={batterjee:{name:'Batterjee Medical College',levels:{'1':[['Human Biology I','Biology'],['General Chemistry','Chemistry'],['General Physics','Physics'],['Mathematics','Foundation'],['English I','Foundation'],['Computer I','Foundation'],['Islamic Medical Ethics','Professional'],['Study Skills I','Study skills'],['Medical Terminology I','Medicine'],['Integrated Basic Science Course','Integrated basic science']], '2':[['Integrated Medical Sciences','Pre-clinical'],['Anatomy','Pre-clinical'],['Physiology','Pre-clinical'],['Biochemistry','Pre-clinical']], '3':[['Pathology','Pre-clinical'],['Pharmacology','Pre-clinical'],['Microbiology','Pre-clinical'],['Immunology','Pre-clinical']], '5':[['Internal Medicine','Clinical'],['Surgery','Clinical'],['Pediatrics','Clinical'],['Obstetrics & Gynecology','Clinical']], '6':[['Medicine Clerkship','Clinical'],['Surgery Clerkship','Clinical'],['Family Medicine','Clinical'],['Psychiatry','Clinical']], '7':[['Internship / Clinical Training','Internship']]}}};
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const slug=v=>String(v).toLowerCase().trim().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const api=(path,opt={})=>fetch(window.plannerApiUrl(path),{headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt}).then(async r=>{let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});
  const modal=html=>{const m=document.querySelector('#modal');if(!m)return;m.innerHTML=`<div class="modal-card setup-modal">${html}</div>`;m.classList.remove('hidden');};
  const close=()=>{const m=document.querySelector('#modal');if(m){m.classList.add('hidden');m.innerHTML='';}};
  const toast=m=>window.toast&&window.toast(m);

  async function buildSchool(){
    const key='batterjee',preset=SCHOOL_PRESETS[key],level=document.querySelector('#school-level')?.value,daily=Number(document.querySelector('#school-daily')?.value)||240,rows=preset.levels[level]||[];
    if(!rows.length)return toast('No starter curriculum is loaded for that level yet.');
    try{
      toast(`Loading ${preset.name}…`);
      const subjects=rows.map(([name,category])=>({id:`${key}-${level}-${slug(name)}`,name,exam_weight:1,category:`${preset.name} · Level ${level} · ${category}`}));
      const topics=subjects.map(s=>({id:`${s.id}-core`,subject_id:s.id,name:'Core review',estimated_hours:2,mastery:0,complexity:.5,self_difficulty:3,volume:.5,cognitive_load:.6}));
      for(const s of subjects)await api('/subjects',{method:'POST',body:JSON.stringify(s)});
      for(const t of topics)await api('/topics',{method:'POST',body:JSON.stringify(t)});
      const profile={daily_available_minutes:daily,minimum_subject_minutes_week:30,review_fraction:.25,max_session_minutes:60,rest_weekdays:[],energy_pattern:['high','high','medium','medium']};
      await api('/profile',{method:'PUT',body:JSON.stringify(profile)});
      const snap=await api('/snapshot');
      await api('/plan',{method:'POST',body:JSON.stringify({subjects:(snap.subjects||[]).map(s=>({id:s.id,name:s.name,exam_weight:s.exam_weight,category:s.category})),topics:(snap.topics||[]).map(t=>({id:t.id,subject_id:t.subject_id,name:t.name,complexity:t.complexity,estimated_hours:t.estimated_hours,mastery:t.mastery,self_difficulty:t.self_difficulty,volume:t.volume,cognitive_load:t.cognitive_load,last_studied:t.last_studied,next_review_due:t.next_review_due})),exams:[],profile,start_date:new Date().toISOString().slice(0,10),days:7,optimizer:true,persist:true,replace_uncompleted:true})});
      close();window.__plannerMode='school';window.__plannerSchool=preset.name;window.__plannerLevel=level;await window.load();if(window.setView)window.setView('today');toast(`${preset.name} Level ${level} plan ready`);
    }catch(e){toast(e.message);}
  }

  function schoolLevel(){modal(`<div class="setup-kicker">BATTERJEE MEDICAL COLLEGE</div><h2>Which level are you in?</h2><p class="setup-copy">Pick your level and the time you can study each day.</p><div class="form-grid"><div class="field"><label>Level</label><select id="school-level"><option value="1">Level 1</option><option value="2">Level 2</option><option value="3">Level 3</option><option value="5">Level 5</option><option value="6">Level 6</option><option value="7">Level 7 / Internship</option></select></div><div class="field"><label>Minutes per day</label><input id="school-daily" type="number" min="30" max="720" value="240"></div></div><div class="school-note">Starter curriculum only. Use your current BMC timetable/course list as the final source of truth.</div><div class="setup-actions"><button class="btn secondary" data-action="school-back">Back</button><button class="btn primary" data-action="school-build">Build my Batterjee plan →</button></div>`);}

  function schoolPicker(){modal(`<div class="setup-kicker">SCHOOL PLANNER</div><h2>Choose your school</h2><p class="setup-copy">Use a starter curriculum when we have one. Otherwise, enter your own subjects.</p><div class="school-grid"><button class="school-choice" data-action="batterjee"><strong>Batterjee Medical College</strong><span>Starter curriculum + level selection</span><b>Use Batterjee →</b></button><button class="school-choice" data-action="other-school"><strong>Other school</strong><span>Use the quick personal setup</span><b>Enter my curriculum →</b></button></div>`);}

  function modePicker(){modal(`<div class="setup-kicker">CHOOSE A MODE</div><h2>How do you want to plan?</h2><p class="setup-copy">Pick what you are studying for. You can switch later.</p><div class="mode-grid"><button class="mode-choice" data-action="usmle"><strong>USMLE Step 1</strong><span>Official blueprint + current block priority.</span><b>Board prep →</b></button><button class="mode-choice" data-action="school"><strong>My medical school</strong><span>Use a school curriculum preset.</span><b>Choose school →</b></button><button class="mode-choice" data-action="personal"><strong>Personal Planner</strong><span>Pick subjects and build your own plan.</span><b>Build my own →</b></button></div>`);}

  window.openPlannerSetup=modePicker;window.openSchoolPicker=schoolPicker;
  document.addEventListener('click',e=>{
    const b=e.target.closest('[data-action]');if(!b)return;
    const action=b.dataset.action;
    if(action==='usmle'){if(window.startStep1)window.startStep1();}
    else if(action==='school')schoolPicker();
    else if(action==='personal'){if(window.startPersonalPlanner)window.startPersonalPlanner();}
    else if(action==='batterjee')schoolLevel();
    else if(action==='other-school'){if(window.startPersonalPlanner)window.startPersonalPlanner();}
    else if(action==='school-back')schoolPicker();
    else if(action==='school-build')buildSchool();
  });
  const style=document.createElement('style');style.textContent=`.school-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.school-choice{border:1px solid #dce8e6;background:#fff;text-align:left;border-radius:14px;padding:16px;display:grid;gap:7px;color:#102a31;cursor:pointer}.school-choice:hover,.mode-choice:hover{border-color:#71beb6;background:#f5fbfa}.school-choice strong{font-size:17px}.school-choice span,.mode-choice span{font-size:11px;color:#71858b}.school-choice b,.mode-choice b{font-size:10px;color:#0f766e}@media(max-width:650px){.school-grid{grid-template-columns:1fr}}`;
  document.head.appendChild(style);
})();