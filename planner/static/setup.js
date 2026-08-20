(() => {
  const blocks = [
    ['cardio','Cardiovascular','Heart, hemodynamics, ECGs, murmurs, vascular disease'],
    ['resp-renal','Respiratory / Renal','Pulmonary + renal physiology, pathology and pharmacology'],
    ['gi','Gastrointestinal','GI physiology, pathology and pharmacology'],
    ['repro-endo','Reproductive / Endocrine','Reproductive systems, pregnancy and endocrine'],
    ['neuro','Neuro / Psych','Neuroanatomy, neurophysiology and behavioral health'],
    ['immune-blood','Heme / Immune','Hematology, lymphoid disease and immunology'],
    ['msk-skin','MSK / Skin','Musculoskeletal, dermatology and connective tissue'],
    ['multisystem','Multisystem','Integrated multisystem processes and disorders'],
    ['development','Human Development','Embryology, development and well-patient concepts'],
    ['biostats','Biostats / Epidemiology','Biostatistics, epidemiology and population health'],
  ];
  const esc2=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const slug=v=>String(v).toLowerCase().trim().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const api2=(path,options={})=>fetch(window.plannerApiUrl(path),{headers:{'Content-Type':'application/json',...(options.headers||{})},...options}).then(async r=>{let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});
  const close=()=>{const m=document.querySelector('#modal');if(m){m.classList.add('hidden');m.innerHTML=''}};
  const modal=html=>{const m=document.querySelector('#modal');if(!m)return;m.innerHTML=`<div class="modal-card setup-modal">${html}</div>`;m.classList.remove('hidden')};
  const toast=msg=>window.toast?window.toast(msg):undefined;
  const wizard={subjects:[],topics:[],exam:null,daily:240,floor:30,max:60};

  function personalWorkspace(){close();window.__plannerMode='personal';window.__plannerBlock=null;modal(`<div class="setup-kicker">PERSONAL PLANNER</div><h2>Build your plan in four steps.</h2><p class="setup-copy">Add your subjects and topics, optionally add your next exam, tell us how much time you have, and we'll generate the first week.</p><div class="wizard-steps"><span class="active">1 Subjects</span><span>2 Topics</span><span>3 Exam</span><span>4 Time</span></div><div id="personal-wizard"></div>`);wizardStep1();}

  function wizardStep1(){
    const root=document.querySelector('#personal-wizard');
    root.innerHTML=`<div class="wizard-head"><div><strong>What are you studying?</strong><span>Add one or more subjects.</span></div><button class="btn secondary small" id="wiz-add-subject">+ Add subject</button></div><div id="wiz-subject-list" class="wizard-list"></div><div class="wizard-actions"><button class="btn ghost" id="wiz-cancel">Cancel</button><button class="btn primary" id="wiz-next">Next: add topics →</button></div>`;
    renderSubjects();
    document.querySelector('#wiz-add-subject').onclick=()=>{wizard.subjects.push({id:'',name:'',category:'Personal'});renderSubjects()};
    document.querySelector('#wiz-cancel').onclick=()=>close();
    document.querySelector('#wiz-next').onclick=()=>{wizard.subjects=wizard.subjects.map(s=>({...s,id:slug(s.name)})).filter(s=>s.name.trim());const ids=new Set();for(const s of wizard.subjects){if(!s.id||ids.has(s.id))return toast('Every subject needs a unique name');ids.add(s.id)}if(!wizard.subjects.length)return toast('Add at least one subject');wizardStep2()};
  }
  function renderSubjects(){
    const root=document.querySelector('#wiz-subject-list');
    if(!wizard.subjects.length){root.innerHTML='<div class="wizard-empty">No subjects yet. Click “Add subject”.</div>';return}
    root.innerHTML=wizard.subjects.map((s,i)=>`<div class="wizard-row"><input data-si="${i}" class="wiz-subject-name" value="${esc2(s.name)}" placeholder="e.g. Anatomy, Pharmacology, Cardiology"><select data-ci="${i}" class="wiz-subject-cat"><option>Personal</option><option>Preclinical</option><option>Clerkship</option><option>Board prep</option></select><button class="icon-btn danger" data-remove-subject="${i}">Remove</button></div>`).join('');
    document.querySelectorAll('.wiz-subject-name').forEach(e=>e.oninput=()=>wizard.subjects[Number(e.dataset.si)].name=e.value);
    document.querySelectorAll('.wiz-subject-cat').forEach(e=>e.onchange=()=>wizard.subjects[Number(e.dataset.ci)].category=e.value);
    document.querySelectorAll('[data-remove-subject]').forEach(b=>b.onclick=()=>{wizard.subjects.splice(Number(b.dataset.removeSubject),1);renderSubjects()});
  }

  function wizardStep2(){
    const root=document.querySelector('#personal-wizard');root.innerHTML=`<div class="wizard-head"><div><strong>Add your topics</strong><span>Topics are what the engine schedules.</span></div><button class="btn secondary small" id="wiz-add-topic">+ Add topic</button></div><div id="wiz-topic-list" class="wizard-list"></div><div class="wizard-note">Complexity starts neutral and is recalibrated from real study performance.</div><div class="wizard-actions"><button class="btn ghost" id="wiz-back">← Back</button><button class="btn primary" id="wiz-next2">Next: exam / deadline →</button></div>`;
    renderTopics();
    document.querySelector('#wiz-add-topic').onclick=()=>{wizard.topics.push({name:'',subject_id:wizard.subjects[0]?.id||'',estimated_hours:1});renderTopics()};
    document.querySelector('#wiz-back').onclick=wizardStep1;
    document.querySelector('#wiz-next2').onclick=()=>{wizard.topics=wizard.topics.filter(t=>t.name.trim());if(!wizard.topics.length)return toast('Add at least one topic');wizardStep3()};
  }
  function renderTopics(){
    const root=document.querySelector('#wiz-topic-list');
    if(!wizard.topics.length){root.innerHTML='<div class="wizard-empty">No topics yet. Add what you actually need to study.</div>';return}
    root.innerHTML=wizard.topics.map((t,i)=>`<div class="wizard-row topic-row"><input data-ti="${i}" class="wiz-topic-name" value="${esc2(t.name)}" placeholder="e.g. Cardiac cycle, Renal physiology"><select data-ts="${i}" class="wiz-topic-subject">${wizard.subjects.map(s=>`<option value="${esc2(s.id)}" ${t.subject_id===s.id?'selected':''}>${esc2(s.name||s.id)}</option>`).join('')}</select><input data-th="${i}" class="wiz-topic-hours" type="number" min="0.25" step="0.25" value="${t.estimated_hours}"><button class="icon-btn danger" data-remove-topic="${i}">Remove</button></div>`).join('');
    document.querySelectorAll('.wiz-topic-name').forEach(e=>e.oninput=()=>wizard.topics[Number(e.dataset.ti)].name=e.value);
    document.querySelectorAll('.wiz-topic-subject').forEach(e=>e.onchange=()=>wizard.topics[Number(e.dataset.ts)].subject_id=e.value);
    document.querySelectorAll('.wiz-topic-hours').forEach(e=>e.oninput=()=>wizard.topics[Number(e.dataset.th)].estimated_hours=Number(e.value)||1);
    document.querySelectorAll('[data-remove-topic]').forEach(b=>b.onclick=()=>{wizard.topics.splice(Number(b.dataset.removeTopic),1);renderTopics()});
  }

  function wizardStep3(){
    const root=document.querySelector('#personal-wizard');root.innerHTML=`<div class="wizard-head"><div><strong>Do you have an exam or deadline?</strong><span>Optional, but it makes urgency smarter.</span></div></div><div class="choice-grid"><button class="choice-card ${wizard.exam?'':'selected'}" id="no-exam"><strong>No exam yet</strong><span>Balance your curriculum and use spaced review.</span></button><button class="choice-card ${wizard.exam?'selected':''}" id="yes-exam"><strong>Yes, I have one</strong><span>Set a date and what it covers.</span></button></div><div id="exam-fields" class="exam-fields ${wizard.exam?'':'hidden'}"><div class="form-grid"><div class="field"><label>Exam / deadline name</label><input id="wiz-exam-name" value="${esc2(wizard.exam?.id||'Main exam')}"></div><div class="field"><label>Date</label><input id="wiz-exam-date" type="date" value="${esc2(wizard.exam?.date||'')}"></div></div><div class="wizard-note">The first version covers all subjects. You can narrow coverage later.</div></div><div class="wizard-actions"><button class="btn ghost" id="wiz-back3">← Back</button><button class="btn primary" id="wiz-next3">Next: study time →</button></div>`;
    document.querySelector('#no-exam').onclick=()=>{wizard.exam=null;document.querySelector('#exam-fields').classList.add('hidden');document.querySelector('#no-exam').classList.add('selected');document.querySelector('#yes-exam').classList.remove('selected')};
    document.querySelector('#yes-exam').onclick=()=>{wizard.exam=wizard.exam||{id:'Main exam',date:''};document.querySelector('#exam-fields').classList.remove('hidden');document.querySelector('#yes-exam').classList.add('selected');document.querySelector('#no-exam').classList.remove('selected')};
    document.querySelector('#wiz-back3').onclick=wizardStep2;
    document.querySelector('#wiz-next3').onclick=()=>{if(wizard.exam){wizard.exam.id=document.querySelector('#wiz-exam-name').value.trim()||'Main exam';wizard.exam.date=document.querySelector('#wiz-exam-date').value;if(!wizard.exam.date)return toast('Choose an exam date')}wizardStep4()};
  }

  function wizardStep4(){
    const root=document.querySelector('#personal-wizard');root.innerHTML=`<div class="wizard-head"><div><strong>How much time can you study?</strong><span>The planner will never schedule beyond your daily ceiling.</span></div></div><div class="time-hero"><div><b id="wiz-daily-label">${wizard.daily}</b><span>minutes/day</span></div><input id="wiz-daily" type="range" min="30" max="720" step="15" value="${wizard.daily}"><div class="range-labels"><span>30m</span><span>12h</span></div></div><div class="wizard-mini-grid"><div class="field"><label>Weekly minimum per subject</label><input id="wiz-floor" type="number" min="0" value="${wizard.floor}"></div><div class="field"><label>Maximum session length</label><input id="wiz-max" type="number" min="15" max="240" value="${wizard.max}"></div></div><div class="wizard-note">Start conservatively. Actual study time will recalibrate complexity later.</div><div class="wizard-actions"><button class="btn ghost" id="wiz-back4">← Back</button><button class="btn primary" id="wiz-finish">Build my plan →</button></div>`;
    document.querySelector('#wiz-daily').oninput=e=>{wizard.daily=Number(e.target.value);document.querySelector('#wiz-daily-label').textContent=wizard.daily};
    document.querySelector('#wiz-floor').oninput=e=>wizard.floor=Number(e.target.value)||0;
    document.querySelector('#wiz-max').oninput=e=>wizard.max=Math.max(15,Math.min(240,Number(e.target.value)||60));
    document.querySelector('#wiz-back4').onclick=wizardStep3;
    document.querySelector('#wiz-finish').onclick=finishPersonalPlan;
  }

  async function finishPersonalPlan(){
    try{
      wizard.subjects=wizard.subjects.map(s=>({...s,id:slug(s.name)}));
      for(const s of wizard.subjects) await api2('/subjects',{method:'POST',body:JSON.stringify({id:s.id,name:s.name,exam_weight:1,category:s.category})});
      for(const t of wizard.topics){const id=`${t.subject_id}-${slug(t.name)}`;await api2('/topics',{method:'POST',body:JSON.stringify({id,subject_id:t.subject_id,name:t.name,estimated_hours:Number(t.estimated_hours)||1,mastery:0,complexity:.5,self_difficulty:3,volume:.5,cognitive_load:.5})})}
      if(wizard.exam) await api2('/exams',{method:'POST',body:JSON.stringify({id:wizard.exam.id,date:wizard.exam.date,subject_ids:wizard.subjects.map(s=>s.id),topic_ids:[],weight:1})});
      const profile={daily_available_minutes:wizard.daily,minimum_subject_minutes_week:wizard.floor,review_fraction:.25,max_session_minutes:wizard.max,rest_weekdays:[],energy_pattern:['high','high','medium','medium']};
      await api2('/profile',{method:'PUT',body:JSON.stringify(profile)});
      const snap=await api2('/snapshot');
      await api2('/plan',{method:'POST',body:JSON.stringify({subjects:(snap.subjects||[]).map(s=>({id:s.id,name:s.name,exam_weight:s.exam_weight,category:s.category})),topics:(snap.topics||[]).map(t=>({id:t.id,subject_id:t.subject_id,name:t.name,complexity:t.complexity,estimated_hours:t.estimated_hours,mastery:t.mastery,self_difficulty:t.self_difficulty,volume:t.volume,cognitive_load:t.cognitive_load,last_studied:t.last_studied,next_review_due:t.next_review_due})),exams:(snap.exams||[]).map(e=>({id:e.id,date:e.exam_date,subject_ids:JSON.parse(e.subject_ids_json||'[]'),topic_ids:JSON.parse(e.topic_ids_json||'[]'),weight:e.weight})),profile,start_date:new Date().toISOString().slice(0,10),days:7,optimizer:true,persist:true,replace_uncompleted:true})});
      close();window.__plannerMode='personal';await window.load();if(window.setView)window.setView('today');toast('Personal study plan built');
    }catch(e){toast(e.message)}
  }

  function modePicker(){modal(`<div class="setup-kicker">WELCOME</div><h2>How do you want to use your planner?</h2><p class="setup-copy">Choose the path that matches how you study. You can switch later.</p><div class="mode-grid"><button class="mode-choice" id="mode-usmle"><strong>USMLE Step 1</strong><span>Official blueprint + current block priority + adaptive scheduling.</span><b>Board-prep mode →</b></button><button class="mode-choice" id="mode-personal"><strong>Personal Planner</strong><span>Guided setup for your subjects, topics, exams and available time.</span><b>Build my own plan →</b></button></div>`);document.querySelector('#mode-usmle').onclick=blockPicker;document.querySelector('#mode-personal').onclick=personalWorkspace}
  function blockPicker(){modal(`<div class="setup-kicker">USMLE STEP 1</div><h2>Which block are you studying right now?</h2><p class="setup-copy">The official Step 1 blueprint stays active. Your current block gets extra priority this week.</p><div class="block-grid">${blocks.map(([id,name,desc])=>`<button class="block-choice" data-block="${id}" data-name="${esc2(name)}"><strong>${esc2(name)}</strong><span>${esc2(desc)}</span></button>`).join('')}</div><div class="setup-actions"><button class="btn secondary" id="setup-back">Back</button><button class="btn ghost" id="no-block">Balanced Step 1</button></div>`);document.querySelectorAll('.block-choice').forEach(b=>b.onclick=()=>applyBlock(b.dataset.block,b.dataset.name));document.querySelector('#setup-back').onclick=modePicker;document.querySelector('#no-block').onclick=()=>applyBlock('','balanced Step 1')}
  async function applyBlock(blockId,blockName){try{toast(`Preparing Step 1 around ${blockName}…`);await api2('/setup/step1',{method:'POST',body:JSON.stringify({start_date:new Date().toISOString().slice(0,10)})});const snap=await api2('/snapshot');const multipliers=new Map([['cardio',2.2],['resp-renal',2],['gi',1.8],['repro-endo',2],['neuro',2],['immune-blood',1.9],['msk-skin',1.8],['multisystem',1.7],['development',1.5],['biostats',1.5]]);const boost=multipliers.get(blockId)||1;for(const s of snap.subjects||[]){const base=Number(s.exam_weight||1);await api2('/subjects',{method:'POST',body:JSON.stringify({id:s.id,name:s.name,exam_weight:s.id===blockId?base*boost:base,category:s.category})})}await api2('/replan',{method:'POST',body:JSON.stringify({start_date:new Date().toISOString().slice(0,10),days:7,optimizer:true,locked_session_ids:[]})});close();window.__plannerMode='usmle';window.__plannerBlock=blockName;await window.load();toast(`Step 1 ready — ${blockName}`)}catch(e){toast(e.message)}}

  window.startStep1=modePicker;window.openPlannerSetup=modePicker;window.startPersonalPlanner=personalWorkspace;window.personalWorkspace=personalWorkspace;
  const originalSetView=window.setView;
  window.setView=function(view){const hasTopics=typeof state!=='undefined'&&Array.isArray(state.snapshot?.topics)&&state.snapshot.topics.length>0;if(view==='curriculum'&&!hasTopics){personalWorkspace();return}return originalSetView?originalSetView(view):undefined};
  const style=document.createElement('style');style.textContent=`.setup-modal{max-width:820px!important}.setup-kicker{font-size:10px;letter-spacing:.14em;font-weight:900;color:#0f766e}.setup-modal h2{font-size:28px;letter-spacing:-.04em;margin:8px 0}.setup-copy{color:#71858b;line-height:1.55;margin:0 0 18px}.mode-grid,.choice-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.mode-choice,.block-choice,.choice-card{border:1px solid #dce8e6;background:#fff;text-align:left;border-radius:14px;padding:16px;display:grid;gap:7px;transition:.15s;color:#102a31}.mode-choice:hover,.block-choice:hover,.choice-card:hover{border-color:#71beb6;background:#f5fbfa;transform:translateY(-1px);box-shadow:0 10px 24px rgba(16,42,49,.07)}.mode-choice strong{font-size:17px}.mode-choice span,.block-choice span,.choice-card span{font-size:11px;color:#71858b;line-height:1.45}.mode-choice b{font-size:10px;color:#0f766e}.block-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;max-height:55vh;overflow:auto}.block-choice strong{font-size:13px}.block-choice span{font-size:10px}.setup-actions,.wizard-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:16px}.wizard-steps{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin:18px 0}.wizard-steps span{padding:8px 10px;border-radius:9px;background:#f4f8f7;color:#8a999d;font-size:10px;text-align:center;font-weight:800}.wizard-steps span.active{background:#e4f4f1;color:#0f766e}.wizard-head{display:flex;justify-content:space-between;align-items:flex-start;gap:12px;margin-bottom:12px}.wizard-head div{display:grid;gap:4px}.wizard-head strong{font-size:16px}.wizard-head span{font-size:11px;color:#71858b}.wizard-list{display:grid;gap:8px;max-height:48vh;overflow:auto}.wizard-row{display:grid;grid-template-columns:1.5fr .8fr auto;gap:8px;align-items:center;padding:10px;background:#f8fbfa;border:1px solid #dce8e6;border-radius:11px}.topic-row{grid-template-columns:1.3fr 1fr 90px auto}.wizard-row input,.wizard-row select,.exam-fields input,.wizard-mini-grid input{border:1px solid #dce8e6;border-radius:9px;padding:9px;background:#fff}.wizard-empty{padding:35px;text-align:center;border:1px dashed #cddbd9;border-radius:11px;color:#87999d;font-size:11px}.wizard-note{padding:11px 13px;background:#f4f9f8;border-radius:10px;color:#71858b;font-size:10px;margin-top:10px}.choice-card.selected{border-color:#0f766e;background:#e9f7f4;box-shadow:inset 0 0 0 1px #0f766e}.exam-fields{margin-top:13px}.hidden{display:none!important}.time-hero{padding:18px;background:#f6faf9;border:1px solid #dce8e6;border-radius:14px}.time-hero>div{display:flex;align-items:baseline;gap:7px}.time-hero b{font-size:32px;color:#0f766e}.time-hero span{font-size:11px;color:#71858b}.time-hero input{width:100%;margin:14px 0}.range-labels{display:flex!important;justify-content:space-between!important}.wizard-mini-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-top:12px}.wizard-mini-grid .field{display:grid;gap:6px}.wizard-mini-grid label{font-size:10px;font-weight:850}.icon-btn.danger{color:#b7434a;border:1px solid #dce8e6;background:#fff;border-radius:9px;padding:7px 9px;cursor:pointer;font-size:10px}@media(max-width:650px){.mode-grid,.choice-grid,.block-grid,.wizard-mini-grid{grid-template-columns:1fr}.wizard-row,.topic-row{grid-template-columns:1fr}.wizard-steps{grid-template-columns:1fr 1fr}.setup-modal h2{font-size:23px}}`;document.head.appendChild(style);
})();
