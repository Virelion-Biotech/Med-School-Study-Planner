(() => {
  const QUICK_SUBJECTS=['Anatomy','Physiology','Biochemistry','Pharmacology','Pathology','Microbiology','Immunology','Genetics','Neuroscience','Behavioral Science','Embryology','Histology','Medical Terminology','Community Medicine','Biostatistics','Epidemiology','Ethics','Internal Medicine','Surgery','Pediatrics','Obstetrics & Gynecology','Psychiatry','Family Medicine'];
  const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const slug=v=>String(v).toLowerCase().trim().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'');
  const api=(path,opt={})=>fetch(window.plannerApiUrl(path),{headers:{'Content-Type':'application/json',...(opt.headers||{})},...opt}).then(async r=>{let b={};try{b=await r.json()}catch{}if(!r.ok)throw Error(b.detail||`HTTP ${r.status}`);return b});
  const modal=html=>{const m=document.querySelector('#modal');if(!m)return;m.innerHTML=`<div class="modal-card simple-setup">${html}</div>`;m.classList.remove('hidden');};
  const close=()=>{const m=document.querySelector('#modal');if(m){m.classList.add('hidden');m.innerHTML='';}};
  const toast=m=>window.toast&&window.toast(m);

  function personalSetup(){
    modal(`<div class="setup-kicker">PERSONAL PLANNER</div><h2>Tell me what you need to study.</h2><p class="simple-copy">Pick subjects, add what you have to get through, and I’ll build the week. You can enter topics normally or by lectures/slides.</p>
      <div class="simple-grid">
        <div class="simple-field full"><label>Quick-add subject</label><div class="quick-subject"><select id="sp-quick-subject"><option value="">Choose a subject…</option>${QUICK_SUBJECTS.map(s=>`<option>${esc(s)}</option>`).join('')}</select><button class="btn secondary" id="sp-add-subject">Add</button></div><small>Choose common medical subjects or type your own below.</small></div>
        <div class="simple-field full"><label>Subjects</label><textarea id="sp-subjects" rows="3" placeholder="Anatomy\nPhysiology\nPharmacology"></textarea><small>One subject per line.</small></div>
        <div class="simple-field full"><label>How do you want to enter the workload?</label><select id="sp-workload-mode"><option value="topics">Topics</option><option value="lectures">Lectures</option><option value="slides">Slides</option><option value="both">Lectures + slides</option></select><small>Pick what you actually have. The planner converts the count into a starting time estimate, then learns from your real study time.</small></div>
        <div class="simple-field full"><label>What do you have to study?</label><textarea id="sp-topics" rows="6" placeholder="Topics: Anatomy - Thorax\nLectures: Cardiology - Heart failure | 4 lectures\nSlides: Physiology - Cardiac cycle | 85 slides\nBoth: Pharmacology - Autonomic drugs | 3 lectures | 120 slides"></textarea><small>Examples: <b>Cardiology - Heart failure | 4 lectures</b> · <b>Physiology - Cardiac cycle | 85 slides</b> · <b>Pharmacology - Autonomic drugs | 3 lectures | 120 slides</b></small></div>
        <div class="simple-field"><label>Exam / deadline <span>(optional)</span></label><input id="sp-exam" placeholder="e.g. Block exam"></div>
        <div class="simple-field"><label>Exam date <span>(optional)</span></label><input id="sp-date" type="date"></div>
        <div class="simple-field"><label>Study time per day</label><div class="time-input"><input id="sp-minutes" type="number" min="30" max="720" value="240"><span>minutes</span></div></div>
        <div class="simple-field"><label>Longest session</label><select id="sp-session"><option value="45">45 min</option><option value="60" selected>60 min</option><option value="90">90 min</option><option value="120">120 min</option></select></div>
      </div>
      <div class="simple-note">Starting estimate: about 45 minutes per lecture and about 1.5 minutes per slide. These are only initial estimates; actual study time replaces them as you use the planner.</div>
      <div class="simple-actions"><button class="btn ghost" id="sp-cancel">Cancel</button><button class="btn primary" id="sp-build">Make my plan →</button></div>`);
    document.querySelector('#sp-add-subject').onclick=()=>{const sel=document.querySelector('#sp-quick-subject');const value=sel.value;if(!value)return;const area=document.querySelector('#sp-subjects');const current=area.value.split(/\n|,/).map(x=>x.trim()).filter(Boolean);if(!current.some(x=>x.toLowerCase()===value.toLowerCase())){current.push(value);area.value=current.join('\n');}sel.value='';};
    document.querySelector('#sp-cancel').onclick=close;
    document.querySelector('#sp-build').onclick=buildPersonal;
  }

  function parseWorkloadLine(raw, mode, fallbackSubject){
    const parts=raw.split('|').map(x=>x.trim()).filter(Boolean);
    const first=parts.shift()||raw;
    const nameParts=first.split(/\s+-\s+/,2);
    let subjectName=nameParts.length===2?nameParts[0].trim():fallbackSubject;
    let topicName=nameParts.length===2?nameParts[1].trim():first;
    let lectures=0, slides=0, hours=1;
    for(const p of parts){
      const m=p.match(/([0-9]+(?:\.[0-9]+)?)\s*(lectures?|lects?)/i); if(m) lectures=Number(m[1]);
      const s=p.match(/([0-9]+(?:\.[0-9]+)?)\s*(slides?|pages?)/i); if(s) slides=Number(s[1]);
      const h=p.match(/([0-9]+(?:\.[0-9]+)?)\s*(hours?|hrs?)/i); if(h) hours=Number(h[1]);
    }
    if(mode==='lectures' && !lectures){const m=raw.match(/([0-9]+(?:\.[0-9]+)?)/);lectures=m?Number(m[1]):0;}
    if(mode==='slides' && !slides){const m=raw.match(/([0-9]+(?:\.[0-9]+)?)/);slides=m?Number(m[1]):0;}
    if(mode==='topics'){hours=1;}
    if(lectures>0 || slides>0){hours=Math.max(0.25,(lectures*0.75)+(slides*0.025));}
    return {subjectName,topicName,lectures,slides,estimated_hours:hours};
  }

  async function buildPersonal(){
    const subjectsText=document.querySelector('#sp-subjects').value,topicsText=document.querySelector('#sp-topics').value,mode=document.querySelector('#sp-workload-mode').value,examName=document.querySelector('#sp-exam').value.trim(),examDate=document.querySelector('#sp-date').value;
    const minutes=Math.max(30,Math.min(720,Number(document.querySelector('#sp-minutes').value)||240)),maxSession=Math.max(15,Math.min(240,Number(document.querySelector('#sp-session').value)||60));
    const subjectNames=[...new Set(subjectsText.split(/\n|,/).map(x=>x.trim()).filter(Boolean))];if(!subjectNames.length)return toast('Add at least one subject.');
    const subjectMap=new Map(subjectNames.map(name=>[name.toLowerCase(),{id:slug(name),name}]));
    const topicsRaw=topicsText.split(/\n/).map(x=>x.trim()).filter(Boolean);if(!topicsRaw.length)return toast('Add at least one item to study.');
    if((examName&&!examDate)||(!examName&&examDate))return toast('Enter both the exam name and date, or leave both empty.');
    const topics=[];for(const raw of topicsRaw){const parsed=parseWorkloadLine(raw,mode,subjectNames[0]);let subject=subjectMap.get(parsed.subjectName.toLowerCase())||subjectMap.values().next().value;topics.push({id:`${subject.id}-${slug(parsed.topicName)}`,subject_id:subject.id,name:parsed.topicName,complexity:.5,estimated_hours:parsed.estimated_hours,mastery:0,self_difficulty:3,volume:Math.min(1,Math.max(.1,parsed.estimated_hours/6)),cognitive_load:mode==='topics'?.6:.75});}
    try{toast('Building your plan…');for(const s of subjectMap.values())await api('/subjects',{method:'POST',body:JSON.stringify({id:s.id,name:s.name,exam_weight:1,category:'Personal'})});for(const t of topics)await api('/topics',{method:'POST',body:JSON.stringify(t)});if(examName&&examDate)await api('/exams',{method:'POST',body:JSON.stringify({id:examName,date:examDate,subject_ids:[...subjectMap.values()].map(s=>s.id),topic_ids:[],weight:1})});const profile={daily_available_minutes:minutes,minimum_subject_minutes_week:30,review_fraction:.25,max_session_minutes:maxSession,rest_weekdays:[],energy_pattern:['high','high','medium','medium']};await api('/profile',{method:'PUT',body:JSON.stringify(profile)});const snap=await api('/snapshot');await api('/plan',{method:'POST',body:JSON.stringify({subjects:(snap.subjects||[]).map(s=>({id:s.id,name:s.name,exam_weight:s.exam_weight,category:s.category})),topics:(snap.topics||[]).map(t=>({id:t.id,subject_id:t.subject_id,name:t.name,complexity:t.complexity,estimated_hours:t.estimated_hours,mastery:t.mastery,last_studied:t.last_studied,next_review_due:t.next_review_due,self_difficulty:t.self_difficulty,volume:t.volume,cognitive_load:t.cognitive_load})),exams:(snap.exams||[]).map(e=>({id:e.id,date:e.exam_date,subject_ids:JSON.parse(e.subject_ids_json||'[]'),topic_ids:JSON.parse(e.topic_ids_json||'[]'),weight:e.weight})),profile,start_date:new Date().toISOString().slice(0,10),days:7,optimizer:true,persist:true,replace_uncompleted:true})});close();window.__plannerMode='personal';await window.load();if(window.setView)window.setView('today');toast('Your study plan is ready.');}catch(e){toast(e.message)}}
  window.startPersonalPlanner=personalSetup;window.closeSimpleSetup=close;
  const style=document.createElement('style');style.textContent=`.simple-setup{max-width:780px!important}.simple-setup h2{font-size:30px;letter-spacing:-.045em;margin:7px 0}.simple-copy{color:#71858b;line-height:1.55;margin:0 0 20px}.simple-grid{display:grid;grid-template-columns:1fr 1fr;gap:13px}.simple-field{display:grid;gap:6px}.simple-field.full{grid-column:1/-1}.simple-field label{font-size:10px;font-weight:900;color:#4f656b}.simple-field label span{font-weight:600;color:#9aa8ab}.simple-field textarea,.simple-field input,.simple-field select{border:1px solid #dce8e6;background:#fff;border-radius:10px;padding:10px 11px;color:#102a31;outline:none;resize:vertical}.simple-field textarea:focus,.simple-field input:focus,.simple-field select:focus{border-color:#72bdb5;box-shadow:0 0 0 3px #0f766e12}.simple-field small{font-size:9px;color:#87979b}.quick-subject{display:grid;grid-template-columns:1fr auto;gap:8px}.time-input{display:flex;align-items:center;gap:8px}.time-input input{width:100%}.time-input span{font-size:10px;color:#71858b}.simple-note{margin-top:14px;background:#f4f9f8;border:1px solid #e2ecea;border-radius:10px;padding:11px 13px;color:#71858b;font-size:10px;line-height:1.5}.simple-actions{display:flex;justify-content:flex-end;gap:8px;margin-top:18px}@media(max-width:650px){.simple-grid{grid-template-columns:1fr}.simple-field.full{grid-column:auto}.simple-setup h2{font-size:24px}}
  `;document.head.appendChild(style);
})();