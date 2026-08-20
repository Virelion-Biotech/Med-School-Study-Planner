(() => {
  const QUICK_SUBJECTS=['Anatomy','Physiology','Biochemistry','Pharmacology','Pathology','Microbiology','Immunology','Genetics','Neuroscience','Behavioral Science','Embryology','Histology','Medical Terminology','Community Medicine','Biostatistics','Epidemiology','Ethics','Internal Medicine','Surgery','Pediatrics','Obstetrics & Gynecology','Psychiatry','Family Medicine'];
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const slug=v=>String(v).toLowerCase().trim().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const api=(path,opt={})=>fetch(window.plannerApiUrl(path),{headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt}).then(async r=>{let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});
  const modal=html=>{const m=document.querySelector('#modal');if(!m)return;m.innerHTML=`<div class="modal-card simple-setup">${html}</div>`;m.classList.remove('hidden');};
  const close=()=>{const m=document.querySelector('#modal');if(m){m.classList.add('hidden');m.innerHTML='';}};
  const toast=m=>window.toast&&window.toast(m);

  function personalSetup(){
    modal(`<div class="setup-kicker">PERSONAL PLANNER</div>
      <h2>Tell me what you need to study.</h2>
      <p class="simple-copy">Add your subjects, then add the lectures or slides you need to get through. Everything else is optional.</p>

      <div class="simple-section">
        <div class="section-title"><b>1. Your subjects</b><span>Add the subjects you are studying.</span></div>
        <div class="quick-subject"><select id="sp-quick-subject"><option value="">Choose a subject…</option>${QUICK_SUBJECTS.map(s=>`<option>${esc(s)}</option>`).join('')}</select><button class="btn secondary" id="sp-add-subject">Add subject</button></div>
        <textarea id="sp-subjects" rows="3" placeholder="Anatomy\nPhysiology\nPharmacology"></textarea>
        <small>One subject per line. You can also type your own.</small>
      </div>

      <div class="simple-section">
        <div class="section-title"><b>2. What do you have to study?</b><span>Add one topic per line. Tell us the lecture and/or slide count.</span></div>
        <div class="workload-head"><span>Topic</span><span>Lectures</span><span>Slides</span><span></span></div>
        <div id="sp-topic-list"></div>
        <button class="btn secondary small" id="sp-add-topic">+ Add topic</button>
        <div class="simple-help">Example: <b>Heart failure</b> → 4 lectures, 85 slides. Leave either count blank when you don't have it.</div>
      </div>

      <div class="simple-section optional-section">
        <div class="section-title"><b>3. Optional</b><span>You can skip these and add them later.</span></div>
        <div class="simple-grid compact">
          <div class="simple-field"><label>Exam / deadline</label><input id="sp-exam" placeholder="e.g. Cardiology block exam"></div>
          <div class="simple-field"><label>Date</label><input id="sp-date" type="date"></div>
          <div class="simple-field"><label>Study time per day</label><div class="time-input"><input id="sp-minutes" type="number" min="30" max="720" value="240"><span>min</span></div></div>
          <div class="simple-field"><label>Longest session</label><select id="sp-session"><option value="45">45 min</option><option value="60" selected>60 min</option><option value="90">90 min</option><option value="120">120 min</option></select></div>
        </div>
      </div>

      <div class="simple-note">Starting estimate: <b>45 min per lecture</b> and <b>1.5 min per slide</b>, combined conservatively. These estimates are only a starting point; your actual study time will teach the planner how long your material really takes.</div>
      <div class="simple-actions"><button class="btn ghost" id="sp-cancel">Cancel</button><button class="btn primary" id="sp-build">Make my plan →</button></div>`);

    document.querySelector('#sp-add-subject').onclick=()=>{const sel=document.querySelector('#sp-quick-subject');const value=sel.value;if(!value)return;const area=document.querySelector('#sp-subjects');const current=area.value.split(/\n|,/).map(x=>x.trim()).filter(Boolean);if(!current.some(x=>x.toLowerCase()===value.toLowerCase())){current.push(value);area.value=current.join('\n');}sel.value='';};
    document.querySelector('#sp-add-topic').onclick=()=>addTopicRow();
    document.querySelector('#sp-cancel').onclick=close;
    document.querySelector('#sp-build').onclick=buildPersonal;
    addTopicRow();
  }

  function addTopicRow(){
    const root=document.querySelector('#sp-topic-list');
    const row=document.createElement('div');row.className='topic-entry';
    row.innerHTML=`<input class="topic-name" placeholder="e.g. Heart failure"><select class="topic-subject"><option value="">Subject</option>${QUICK_SUBJECTS.map(s=>`<option>${esc(s)}</option>`).join('')}</select><input class="topic-lectures" type="number" min="0" step="1" placeholder="0"><input class="topic-slides" type="number" min="0" step="1" placeholder="0"><button class="icon-btn danger topic-remove" type="button">×</button>`;
    root.appendChild(row);
    row.querySelector('.topic-remove').onclick=()=>row.remove();
  }

  function estimateHours(lectures,slides){
    if(!lectures && !slides) return 1;
    return Math.max(0.25,(lectures*0.75)+(slides*0.025));
  }

  function subjectMapFromText(){
    const names=[...new Set(document.querySelector('#sp-subjects').value.split(/\n|,/).map(x=>x.trim()).filter(Boolean))];
    return new Map(names.map(name=>[name.toLowerCase(),{id:slug(name),name}]));
  }

  async function buildPersonal(){
    const subjectMap=subjectMapFromText();
    if(!subjectMap.size)return toast('Add at least one subject.');
    const examName=document.querySelector('#sp-exam').value.trim(),examDate=document.querySelector('#sp-date').value;
    if((examName&&!examDate)||(!examName&&examDate))return toast('Enter both the exam name and date, or leave both empty.');
    const minutes=Math.max(30,Math.min(720,Number(document.querySelector('#sp-minutes').value)||240));
    const maxSession=Math.max(15,Math.min(240,Number(document.querySelector('#sp-session').value)||60));
    const rows=[...document.querySelectorAll('.topic-entry')];
    const topics=[];
    for(const row of rows){
      const name=row.querySelector('.topic-name').value.trim();if(!name)continue;
      const selected=row.querySelector('.topic-subject').value.trim();
      let subject=selected?subjectMap.get(selected.toLowerCase()):null;
      if(!subject)subject=subjectMap.values().next().value;
      const lectures=Math.max(0,Number(row.querySelector('.topic-lectures').value)||0);
      const slides=Math.max(0,Number(row.querySelector('.topic-slides').value)||0);
      topics.push({id:`${subject.id}-${slug(name)}`,subject_id:subject.id,name,complexity:.5,estimated_hours:estimateHours(lectures,slides),mastery:0,self_difficulty:3,volume:Math.min(1,Math.max(.1,estimateHours(lectures,slides)/6)),cognitive_load:(lectures||slides)?0.75:0.6,lecture_count:lectures,slide_count:slides});
    }
    if(!topics.length)return toast('Add at least one topic.');
    try{
      toast('Building your plan…');
      for(const s of subjectMap.values())await api('/subjects',{method:'POST',body:JSON.stringify({id:s.id,name:s.name,exam_weight:1,category:'Personal'})});
      for(const t of topics)await api('/topics',{method:'POST',body:JSON.stringify(t)});
      if(examName&&examDate)await api('/exams',{method:'POST',body:JSON.stringify({id:examName,date:examDate,subject_ids:[...subjectMap.values()].map(s=>s.id),topic_ids:[],weight:1})});
      const profile={daily_available_minutes:minutes,minimum_subject_minutes_week:30,review_fraction:.25,max_session_minutes:maxSession,rest_weekdays:[],energy_pattern:['high','high','medium','medium']};
      await api('/profile',{method:'PUT',body:JSON.stringify(profile)});
      const snap=await api('/snapshot');
      await api('/plan',{method:'POST',body:JSON.stringify({subjects:(snap.subjects||[]).map(s=>({id:s.id,name:s.name,exam_weight:s.exam_weight,category:s.category})),topics:(snap.topics||[]).map(t=>({id:t.id,subject_id:t.subject_id,name:t.name,complexity:t.complexity,estimated_hours:t.estimated_hours,mastery:t.mastery,last_studied:t.last_studied,next_review_due:t.next_review_due,self_difficulty:t.self_difficulty,volume:t.volume,cognitive_load:t.cognitive_load})),exams:(snap.exams||[]).map(e=>({id:e.id,date:e.exam_date,subject_ids:JSON.parse(e.subject_ids_json||'[]'),topic_ids:JSON.parse(e.topic_ids_json||'[]'),weight:e.weight})),profile,start_date:new Date().toISOString().slice(0,10),days:7,optimizer:true,persist:true,replace_uncompleted:true})});
      close();window.__plannerMode='personal';await window.load();if(window.setView)window.setView('today');toast('Your study plan is ready.');
    }catch(e){toast(e.message)}
  }

  window.startPersonalPlanner=personalSetup;window.closeSimpleSetup=close;
  const style=document.createElement('style');
  style.textContent=`
    .simple-setup{max-width:820px!important;max-height:calc(100vh - 40px)!important;overflow-y:auto!important;overflow-x:hidden!important;overscroll-behavior:contain!important}
    .simple-setup::-webkit-scrollbar{width:9px}.simple-setup::-webkit-scrollbar-thumb{background:#b8cfcc;border-radius:10px}.simple-setup::-webkit-scrollbar-track{background:#f2f7f6}
    .simple-setup h2{font-size:30px;letter-spacing:-.045em;margin:7px 0}.simple-copy{color:#71858b;line-height:1.5;margin:0 0 16px}
    .simple-section{padding:15px 0;border-top:1px solid #e7efed}.simple-section:first-of-type{border-top:0;padding-top:0}.section-title{display:grid;gap:3px;margin-bottom:10px}.section-title b{font-size:14px;color:#18343a}.section-title span{font-size:10px;color:#87979b}
    .simple-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.simple-grid.compact{grid-template-columns:repeat(2,1fr)}.simple-field{display:grid;gap:6px}.simple-field label{font-size:10px;font-weight:900;color:#4f656b}
    .simple-field textarea,.simple-field input,.simple-field select,.quick-subject select,.topic-entry input,.topic-entry select{border:1px solid #dce8e6;background:#fff;border-radius:9px;padding:9px 10px;color:#102a31;outline:none}.simple-field textarea{resize:vertical}.simple-field small,.simple-section>small{font-size:9px;color:#87979b}
    .quick-subject{display:grid;grid-template-columns:1fr auto;gap:8px}.time-input{display:flex;align-items:center;gap:8px}.time-input input{width:100%}.time-input span{font-size:10px;color:#71858b}
    .workload-head{display:grid;grid-template-columns:minmax(0,1fr) 90px 90px 32px;gap:8px;color:#8b999c;font-size:9px;font-weight:800;margin:0 0 5px}.topic-entry{display:grid;grid-template-columns:minmax(0,1fr) 150px 90px 90px 32px;gap:8px;align-items:center;margin-bottom:8px}.topic-remove{font-size:16px;line-height:1}
    .simple-help{margin-top:9px;padding:9px 11px;background:#f5faf9;border-radius:9px;color:#71858b;font-size:9px;line-height:1.45}.optional-section{margin-bottom:2px}.simple-note{margin-top:3px;background:#f4f9f8;border:1px solid #e2ecea;border-radius:10px;padding:11px 13px;color:#71858b;font-size:10px;line-height:1.5}.simple-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:15px;position:sticky;bottom:0;background:#fff;padding-top:10px}
    @media(max-width:760px){.topic-entry{grid-template-columns:minmax(0,1fr) 110px 70px 70px 30px}.workload-head{grid-template-columns:minmax(0,1fr) 70px 70px 30px}.simple-grid,.simple-grid.compact{grid-template-columns:1fr}.simple-setup{max-height:calc(100vh - 20px)!important}}
    @media(max-width:520px){.topic-entry{grid-template-columns:1fr 1fr 1fr 1fr 30px}.topic-entry .topic-name{grid-column:1/-1}.workload-head{display:none}.simple-setup h2{font-size:24px}}
  `;
  document.head.appendChild(style);
})();