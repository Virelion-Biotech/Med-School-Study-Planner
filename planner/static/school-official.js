(() => {
  const SCHOOLS = {
    bmc: {
      id: 'bmc', name: 'Batterjee Medical College', country: 'Saudi Arabia',
      mark: 'BMC',
      levels: {
        prep:[['BIO 101','Human Biology I',4],['CHM 101','General Chemistry',4],['PHY 101','General Physics',2],['MAT 101','Mathematics',2],['ENGFY 101','English I',2],['COM 101','Computer I',1],['IMEFY 101','Islamic Medical Ethics',2],['SSK 101','Study Skills I',1],['MT 101','Medical Terminology I',1],['IBS 102','Integrated Basic Science Course',12],['ENGFY 102','English II',2],['COM 102','Computer II',1],['ARFY 102','Arabic Language',2],['SSK 102','Study Skills II',1],['MT 102','Medical Terminology II',1]],
        '2':[['MED 211','Growth & Development I',8],['MED 221','Cognition & Action I',7],['MED 231','Respiration & Circulation I',8],['MED 241','Digestion & Defense I',8],['MED 251','Regulation & Integration I',5]],
        '3':[['MED 332','Respiration & Circulation II',8],['MED 342','Digestion & Defense II',8],['MED 322','Cognition & Action II',7],['MED 352','Regulation & Integration II',6],['MED 312','Growth & Development II',7]],
        '4':[['MED 413','Growth & Development III',4],['MED 433','Respiration & Circulation III',8],['MED 443','Digestion & Defense III',8],['MED 423','Cognition & Action III',6],['MED 461','Primary Health Care',4],['MED 462','Forensic Medicine & Toxicology',3],['MED 463','Medical Laboratories',3],['MED 464','Medical Imaging',3],['MED 465','Elective',3]],
        '5':[['MED 571','Surgery',18],['MED 572','Internal Medicine',18]],
        '6':[['MED 673','Pediatrics',14],['MED 674','Obstetrics & Gynecology',14],['MED 675','Ophthalmology',4],['MED 676','ENT',4]],
        '7':[['INTMED 781','General Surgery',4],['INTMED 782','General Medicine',4],['INTMED 783','Pediatrics',4],['INTMED 784','Obstetrics & Gynecology',4],['INTMED 785','Emergency Medicine',4],['INTMED 786','Elective I',2],['INTMED 787','Elective II',2]]
      }
    },
    harvard: { id:'harvard', name:'Harvard Medical School', country:'United States', mark:'HMS', levels:{'1':[['HMS-1','Preclinical Foundations',18],['HMS-2','Integrated Systems',18]],'2':[['HMS-3','Core Clinical Clerkships',24],['HMS-4','Advanced Clinical Practice',18]],'3':[['HMS-5','Advanced Clinical Experiences',18]],'4':[['HMS-6','Electives & Scholarly Work',18]]} },
    hopkins: { id:'hopkins', name:'Johns Hopkins School of Medicine', country:'United States', mark:'JH', levels:{'1':[['JH-1','Genes, Society & Development',18],['JH-2','Mechanisms & Therapeutics',18]],'2':[['JH-3','Clinical Foundations',24],['JH-4','Core Clinical Rotations',24]],'3':[['JH-5','Advanced Clinical Rotations',20]],'4':[['JH-6','Advanced Clinical Electives',18]]} },
    mayo: { id:'mayo', name:'Mayo Clinic Alix School of Medicine', country:'United States', mark:'MCA', levels:{'1':[['MCA-1','Foundations of Medicine',18],['MCA-2','Integrated Medical Science',18]],'2':[['MCA-3','Core Clinical Experiences',24],['MCA-4','Clinical Year',24]],'3':[['MCA-5','Advanced Clinical Experiences',20]],'4':[['MCA-6','Electives & Career Exploration',18]]} }
  };
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const slug=v=>String(v).toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const api=(p,o={})=>fetch(window.plannerApiUrl(p),{headers:{'Content-Type':'application/json',...(o.headers||{})},...o}).then(async r=>{let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});
  const getModal=()=>document.querySelector('#modal');
  const close=()=>{const m=getModal();if(m){m.classList.add('hidden');m.innerHTML='';}};
  const mark=s=><div class="school-mark" aria-hidden="true">${esc(s.mark)}</div>;
  const modal=h=>{const m=getModal();if(!m)return null;m.innerHTML=`<div class="modal-card school-official"><button class="modal-close" id="school-close" type="button" aria-label="Close school chooser">×</button>${h}</div>`;m.classList.remove('hidden');m.querySelector('#school-close')?.addEventListener('click',close);return m};
  function schoolPicker(){
    const rows=Object.values(SCHOOLS);
    const m=modal(`<div class="setup-kicker">MEDICAL SCHOOL</div><h2>Choose your medical school</h2><p class="school-copy">Start from a school curriculum preset. The planner keeps the school structure while adapting your workload and priorities.</p><div class="school-list">${rows.map(s=>`<button class="school-card school-action" type="button" data-school="${s.id}">${mark(s)}<span class="school-card-copy"><strong>${esc(s.name)}</strong><span>${esc(s.country)}</span><b>Choose school →</b></span></button>`).join('')}</div><p class="school-disclaimer">The marks shown here are compact identifiers for selection; they are not official institutional logos.</p>`);
    m.onclick=e=>{const b=e.target.closest('[data-school]');if(!b)return;const s=SCHOOLS[b.dataset.school];if(s.id==='bmc')levelPicker(s.id);else levelPicker(s.id);};
  }
  function levelPicker(schoolId){
    const s=SCHOOLS[schoolId];
    const levels=Object.entries(s.levels);
    const m=modal(`<div class="setup-kicker">${esc(s.name)}</div><h2>Which year are you in?</h2><p class="school-copy">Pick your year. Next you'll choose the course you are studying now.</p><div class="level-grid">${levels.map(([k,v])=>`<button class="mode-choice school-action" type="button" data-school-level="${esc(k)}"><strong>${k==='prep'?'Preparatory Year':`Year ${esc(k)}`}</strong><span>${v.length} courses</span><b>Select →</b></button>`).join('')}</div><button class="btn ghost school-back" type="button" data-school-back="picker">← Back</button>`);
    m.onclick=e=>{const level=e.target.closest('[data-school-level]');if(level){coursePicker(schoolId,level.dataset.schoolLevel);return;}if(e.target.closest('[data-school-back="picker"]'))schoolPicker();};
  }
  function coursePicker(schoolId,level){
    const s=SCHOOLS[schoolId], rows=s.levels[level]||[];
    const m=modal(`<div class="setup-kicker">${esc(s.name)} · ${level==='prep'?'PREPARATORY YEAR':`YEAR ${esc(level)}`}</div><h2>What are you studying now?</h2><p class="school-copy">Choose the course or block you are currently working through. It gets extra priority this week.</p><div class="course-grid">${rows.map(([code,name,credits])=>`<button class="course-choice school-action" type="button" data-school-course="${esc(code)}"><strong>${esc(name)}</strong><span>${esc(code)} · ${credits} credits</span><b>Study this →</b></button>`).join('')}</div><button class="btn ghost school-back" type="button" data-school-back="level">← Back</button>`);
    m.onclick=e=>{const course=e.target.closest('[data-school-course]');if(course){buildSchool(schoolId,level,course.dataset.schoolCourse);return;}if(e.target.closest('[data-school-back="level"]'))levelPicker(schoolId);};
  }
  async function buildSchool(schoolId,level,courseCode){
    const s=SCHOOLS[schoolId], rows=s.levels[level]||[], selected=rows.find(r=>r[0]===courseCode);if(!selected){toast(`That course could not be found. Please choose it again.`);return;}
    try{
      toast(`Setting up ${selected[1]}…`);
      const subjects=[],topics=[];
      for(const [code,name,credits] of rows){const id=`${s.id}-${level}-${slug(code)}`;const weight=code===selected[0]?2.2:Math.max(1,Math.min(1.8,credits/5));subjects.push({id,name,exam_weight:weight,category:`${s.name} ${level==='prep'?'Preparatory':'Year '+level}`});topics.push({id:`${id}-core`,subject_id:id,name:`${name} — core`,estimated_hours:Math.max(2,credits),complexity:.5,mastery:0,self_difficulty:3,volume:.6,cognitive_load:.7});}
      for(const sub of subjects)await api('/subjects',{method:'POST',body:JSON.stringify(sub)});
      for(const t of topics)await api('/topics',{method:'POST',body:JSON.stringify(t)});
      const profile={daily_available_minutes:240,minimum_subject_minutes_week:30,review_fraction:.25,max_session_minutes:60,rest_weekdays:[],energy_pattern:['high','medium','medium','low']};
      await api('/profile',{method:'PUT',body:JSON.stringify(profile)});
      const snap=await api('/snapshot');
      await api('/plan',{method:'POST',body:JSON.stringify({subjects:(snap.subjects||[]).map(x=>({id:x.id,name:x.name,exam_weight:x.exam_weight,category:x.category})),topics:(snap.topics||[]).map(x=>({id:x.id,subject_id:x.subject_id,name:x.name,complexity:x.complexity,estimated_hours:x.estimated_hours,mastery:x.mastery,last_studied:x.last_studied,next_review_due:x.next_review_due,self_difficulty:x.self_difficulty,volume:x.volume,cognitive_load:x.cognitive_load})),exams:(snap.exams||[]).map(x=>({id:x.id,date:x.exam_date,subject_ids:JSON.parse(x.subject_ids_json||'[]'),topic_ids:JSON.parse(x.topic_ids_json||'[]'),weight:x.weight})),profile,start_date:new Date().toISOString().slice(0,10),days:7,optimizer:true,persist:true,replace_uncompleted:true})});
      localStorage.setItem('planner-mode','school');localStorage.setItem('planner-school',s.name);localStorage.setItem('planner-level',level);localStorage.setItem('planner-block',selected[1]);window.__plannerMode='school';window.__plannerSchool=s.name;window.__plannerLevel=level;window.__plannerBlock=selected[1];close();if(typeof window.load==='function')await window.load();toast(`${selected[1]} is now your focus`);
    }catch(e){toast(e.message||'Could not build the school plan. Please try again.');}
  }
  function toast(m){window.toast&&window.toast(m)}
  window.openSchoolPicker=schoolPicker;
  const style=document.createElement('style');style.textContent=`.school-official{width:min(920px,100%);max-width:920px!important;max-height:min(90vh,780px);overflow:auto;position:relative;-webkit-overflow-scrolling:touch}.school-official h2{margin-top:6px}.school-copy{font-size:12px;color:#71858b;line-height:1.5}.school-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin:16px 0}.school-card{display:flex;align-items:center;gap:14px;width:100%;min-height:112px;border:1px solid #dce8e6;background:#fff;border-radius:14px;padding:14px;text-align:left;cursor:pointer}.school-card:hover,.school-card:focus-visible{border-color:#71beb6;background:#f5fbfa;outline:none}.school-mark{width:58px;height:58px;min-width:58px;border-radius:12px;display:grid;place-items:center;background:#edf5f4;color:#174b50;font-weight:900;font-size:13px;letter-spacing:-.03em;border:1px solid #d5e7e4}.school-card-copy{display:grid;gap:5px;min-width:0}.school-card-copy strong{font-size:14px;color:#18343a}.school-card-copy span{font-size:10px;color:#71858b}.school-card-copy b{font-size:10px;color:#0f766e}.school-disclaimer{font-size:9px;color:#87979b;margin:4px 0}.school-back{margin-top:4px}.modal-close{position:absolute;top:12px;right:12px;width:38px;height:38px;border-radius:10px;border:1px solid #dce8e6;background:#fff;color:#486167;font-size:22px;line-height:1;cursor:pointer;z-index:2}.modal-close:hover{background:#f4faf8;color:#18343a}@media(max-width:700px){.modal{padding:8px;align-items:stretch}.school-official{width:100%;max-height:calc(100dvh - 16px);border-radius:16px;padding:16px}.school-list{grid-template-columns:1fr}.school-card{min-height:88px;padding:12px}.school-mark{width:50px;height:50px;min-width:50px}.school-official h2{font-size:22px}.school-copy{font-size:11px}.modal-close{top:10px;right:10px}}`;document.head.appendChild(style);
})();