(() => {
  const BMC={
    name:'Batterjee Medical College',
    levels:{
      prep:[['BIO 101','Human Biology I',4],['CHM 101','General Chemistry',4],['PHY 101','General Physics',2],['MAT 101','Mathematics',2],['ENGFY 101','English I',2],['COM 101','Computer I',1],['IMEFY 101','Islamic Medical Ethics',2],['SSK 101','Study Skills I',1],['MT 101','Medical Terminology I',1],['IBS 102','Integrated Basic Science Course',12],['ENGFY 102','English II',2],['COM 102','Computer II',1],['ARFY 102','Arabic Language',2],['SSK 102','Study Skills II',1],['MT 102','Medical Terminology II',1]],
      '2':[['MED 211','Growth & Development I',8],['MED 221','Cognition & Action I',7],['MED 231','Respiration & Circulation I',8],['MED 241','Digestion & Defense I',8],['MED 251','Regulation & Integration I',5]],
      '3':[['MED 332','Respiration & Circulation II',8],['MED 342','Digestion & Defense II',8],['MED 322','Cognition & Action II',7],['MED 352','Regulation & Integration II',6],['MED 312','Growth & Development II',7]],
      '4':[['MED 413','Growth & Development III',4],['MED 433','Respiration & Circulation III',8],['MED 443','Digestion & Defense III',8],['MED 423','Cognition & Action III',6],['MED 461','Primary Health Care',4],['MED 462','Forensic Medicine & Toxicology',3],['MED 463','Medical Laboratories',3],['MED 464','Medical Imaging',3],['MED 465','Elective',3]],
      '5':[['MED 571','Surgery',18],['MED 572','Internal Medicine',18]],
      '6':[['MED 673','Pediatrics',14],['MED 674','Obstetrics & Gynecology',14],['MED 675','Ophthalmology',4],['MED 676','ENT',4]],
      '7':[['INTMED 781','General Surgery',4],['INTMED 782','General Medicine',4],['INTMED 783','Pediatrics',4],['INTMED 784','Obstetrics & Gynecology',4],['INTMED 785','Emergency Medicine',4],['INTMED 786','Elective I',2],['INTMED 787','Elective II',2]]
    }
  };
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const slug=v=>String(v).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const api=(p,o={})=>fetch(window.plannerApiUrl(p),{headers:{'Content-Type':'application/json',...(o.headers||{})},...o}).then(async r=>{let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});
  const getModal=()=>document.querySelector('#modal');
  const modal=h=>{const m=getModal();if(!m)return null;m.innerHTML=`<div class="modal-card school-official">${h}</div>`;m.classList.remove('hidden');return m};
  const close=()=>{const m=getModal();if(m)m.classList.add('hidden')};
  function picker(){
    const m=modal(`<div class="setup-kicker">MY MEDICAL SCHOOL</div><h2>Choose your school</h2><p class="school-copy">A school preset gives you a useful starting curriculum. You can change it later.</p><div class="mode-grid school-mode-grid"><button class="mode-choice school-action" type="button" data-school-action="bmc"><strong>Batterjee Medical College</strong><span>Choose your year and current course.</span><b>Use Batterjee →</b></button><button class="mode-choice school-action" type="button" data-school-action="other"><strong>Other school</strong><span>Use the simple personal planner for your own courses.</span><b>Enter my courses →</b></button></div>`);
    if(m)m.onclick=e=>{const b=e.target.closest('[data-school-action]');if(!b)return;if(b.dataset.schoolAction==='bmc')levelPicker();else{close();if(typeof window.startPersonalPlanner==='function')window.startPersonalPlanner();}};
  }
  function levelPicker(){
    const levels=Object.entries(BMC.levels);
    const m=modal(`<div class="setup-kicker">BATTERJEE MEDICAL COLLEGE</div><h2>Which year are you in?</h2><p class="school-copy">Pick your year. Next you'll choose the course you are studying now.</p><div class="level-grid">${levels.map(([k,v])=>`<button class="mode-choice school-action" type="button" data-school-level="${esc(k)}"><strong>${k==='prep'?'Preparatory Year':`Year ${esc(k)}`}</strong><span>${v.length} courses</span><b>Select →</b></button>`).join('')}</div><button class="btn ghost school-back" type="button" data-school-back="picker">← Back</button>`);
    if(m)m.onclick=e=>{const level=e.target.closest('[data-school-level]');if(level){coursePicker(level.dataset.schoolLevel);return;}if(e.target.closest('[data-school-back="picker"]'))picker();};
  }
  function coursePicker(level){
    const rows=BMC.levels[level]||[];
    const m=modal(`<div class="setup-kicker">BATTERJEE · ${level==='prep'?'PREPARATORY YEAR':`YEAR ${esc(level)}`}</div><h2>What are you studying now?</h2><p class="school-copy">Choose the course or block you are currently working through. It gets extra priority this week.</p><div class="course-grid">${rows.map(([code,name,credits])=>`<button class="course-choice school-action" type="button" data-school-course="${esc(code)}"><strong>${esc(name)}</strong><span>${esc(code)} · ${credits} credits</span><b>Study this →</b></button>`).join('')}</div><button class="btn ghost school-back" type="button" data-school-back="level">← Back</button>`);
    if(m)m.onclick=e=>{const course=e.target.closest('[data-school-course]');if(course){buildBMC(level,course.dataset.schoolCourse);return;}if(e.target.closest('[data-school-back="level"]'))levelPicker();};
  }
  async function buildBMC(level,courseCode){
    const rows=BMC.levels[level]||[], selected=rows.find(r=>r[0]===courseCode);if(!selected){window.toast&&window.toast('That course could not be found. Please choose it again.');return;}
    const daily=240;
    try{
      window.toast&&window.toast(`Setting up ${selected[1]}…`);
      const subjects=[],topics=[];
      for(const [code,name,credits] of rows){const id=`bmc-${level}-${slug(code)}`;const weight=code===selected[0]?2.2:Math.max(1,Math.min(1.8,credits/5));subjects.push({id,name,exam_weight:weight,category:`BMC ${level==='prep'?'Preparatory':'Year '+level}`});topics.push({id:`${id}-core`,subject_id:id,name:`${name} — core`,estimated_hours:Math.max(2,credits),complexity:.5,mastery:0,self_difficulty:3,volume:.6,cognitive_load:.7});}
      for(const s of subjects)await api('/subjects',{method:'POST',body:JSON.stringify(s)});
      for(const t of topics)await api('/topics',{method:'POST',body:JSON.stringify(t)});
      const profile={daily_available_minutes:daily,minimum_subject_minutes_week:30,review_fraction:.25,max_session_minutes:60,rest_weekdays:[],energy_pattern:['high','medium','medium','low']};
      await api('/profile',{method:'PUT',body:JSON.stringify(profile)});
      const snap=await api('/snapshot');
      await api('/plan',{method:'POST',body:JSON.stringify({subjects:(snap.subjects||[]).map(s=>({id:s.id,name:s.name,exam_weight:s.exam_weight,category:s.category})),topics:(snap.topics||[]).map(t=>({id:t.id,subject_id:t.subject_id,name:t.name,complexity:t.complexity,estimated_hours:t.estimated_hours,mastery:t.mastery,last_studied:t.last_studied,next_review_due:t.next_review_due,self_difficulty:t.self_difficulty,volume:t.volume,cognitive_load:t.cognitive_load})),exams:(snap.exams||[]).map(e=>({id:e.id,date:e.exam_date,subject_ids:JSON.parse(e.subject_ids_json||'[]'),topic_ids:JSON.parse(e.topic_ids_json||'[]'),weight:e.weight})),profile,start_date:new Date().toISOString().slice(0,10),days:7,optimizer:true,persist:true,replace_uncompleted:true})});
      localStorage.setItem('planner-mode','school');localStorage.setItem('planner-school','Batterjee Medical College');localStorage.setItem('planner-level',level);localStorage.setItem('planner-block',selected[1]);window.__plannerMode='school';window.__plannerSchool=BMC.name;window.__plannerLevel=level;window.__plannerBlock=selected[1];close();if(typeof window.load==='function')await window.load();window.toast&&window.toast(`${selected[1]} is now your focus`);
    }catch(e){window.toast&&window.toast(e.message||'Could not build the school plan. Please try again.');}
  }
  window.openSchoolPicker=picker;
  const style=document.createElement('style');style.textContent=`.school-official{width:min(900px,100%);max-width:900px!important;max-height:min(88vh,760px);overflow:auto;-webkit-overflow-scrolling:touch}.school-official h2{margin-top:6px}.school-copy{font-size:12px;color:#71858b;line-height:1.5}.school-mode-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.level-grid,.course-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:10px;max-height:58vh;overflow:auto;margin:14px 0;padding:2px;-webkit-overflow-scrolling:touch}.school-action{width:100%;min-height:92px;touch-action:manipulation;-webkit-tap-highlight-color:transparent}.school-action:active{transform:scale(.99)}.course-choice{border:1px solid #dce8e6;background:#fff;text-align:left;border-radius:12px;padding:13px;display:grid;gap:5px}.course-choice:hover,.course-choice:focus-visible{border-color:#71beb6;background:#f4faf8;outline:none}.course-choice strong{font-size:13px}.course-choice span{font-size:10px;color:#71858b}.course-choice b{font-size:10px;color:#0f766e}.school-back{margin-top:4px}@media(max-width:650px){.modal{padding:8px;align-items:stretch}.school-official{width:100%;max-height:calc(100dvh - 16px);border-radius:16px;padding:16px}.school-mode-grid,.level-grid,.course-grid{grid-template-columns:1fr;max-height:none}.school-action{min-height:76px;padding:12px}.school-official h2{font-size:22px}.school-copy{font-size:11px}}`;document.head.appendChild(style);
})();
