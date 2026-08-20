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
  const esc2 = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const api2 = (path, options={}) => fetch(window.plannerApiUrl(path), {headers:{'Content-Type':'application/json', ...(options.headers||{})}, ...options}).then(async r => { let b={}; try{b=await r.json()}catch{}; if(!r.ok) throw Error(b.detail || `HTTP ${r.status}`); return b; });
  function modal(html) { const m=document.querySelector('#modal'); if(!m)return; m.innerHTML=`<div class="modal-card setup-modal">${html}</div>`; m.classList.remove('hidden'); }
  function close(){const m=document.querySelector('#modal');if(m){m.classList.add('hidden');m.innerHTML='';}}
  async function personalPlanner(){ close(); window.__plannerMode='personal'; const original=window.setView; if(original) original('curriculum'); window.toast('Personal Planner opened — add your subjects and topics'); }
  window.startPersonalPlanner=personalPlanner;
  async function applyBlock(blockId, blockName){
    try{
      window.toast(`Preparing Step 1 around ${blockName}…`);
      await api2('/setup/step1',{method:'POST',body:JSON.stringify({start_date:new Date().toISOString().slice(0,10)})});
      const snap=await api2('/snapshot');
      const multipliers=new Map([['cardio',2.2],['resp-renal',2.0],['gi',1.8],['repro-endo',2.0],['neuro',2.0],['immune-blood',1.9],['msk-skin',1.8],['multisystem',1.7],['development',1.5],['biostats',1.5]]);
      const boost=multipliers.get(blockId)||1.0;
      for(const s of (snap.subjects||[])){
        const base=Number(s.exam_weight||1);
        const next=s.id===blockId?base*boost:base;
        await api2('/subjects',{method:'POST',body:JSON.stringify({id:s.id,name:s.name,exam_weight:next,category:s.category})});
      }
      await api2('/replan',{method:'POST',body:JSON.stringify({start_date:new Date().toISOString().slice(0,10),days:7,optimizer:true,locked_session_ids:[]})});
      close(); window.__plannerMode='usmle'; window.__plannerBlock=blockName; await window.load(); window.toast(`Step 1 plan ready — ${blockName} is your current block`);
    }catch(e){window.toast(e.message)}
  }
  function blockPicker(){
    modal(`<div class="setup-kicker">USMLE STEP 1</div><h2>Which block are you studying right now?</h2><p class="setup-copy">The official Step 1 blueprint stays active in the background. Your current block gets extra priority so the planner reflects what you are actually studying this week.</p><div class="block-grid">${blocks.map(([id,name,desc])=>`<button class="block-choice" data-block="${id}" data-name="${esc2(name)}"><strong>${esc2(name)}</strong><span>${esc2(desc)}</span></button>`).join('')}</div><div class="setup-actions"><button class="btn secondary" id="setup-back">Back</button><button class="btn ghost" id="no-block">No block / balanced Step 1</button></div>`);
    document.querySelectorAll('.block-choice').forEach(b=>b.onclick=()=>applyBlock(b.dataset.block,b.dataset.name));
    document.querySelector('#setup-back').onclick=modePicker;
    document.querySelector('#no-block').onclick=()=>applyBlock('','balanced Step 1');
  }
  function modePicker(){
    modal(`<div class="setup-kicker">WELCOME</div><h2>How do you want to use your planner?</h2><p class="setup-copy">Choose the path that matches how you study. You can switch later.</p><div class="mode-grid"><button class="mode-choice" id="mode-usmle"><strong>USMLE Step 1</strong><span>Preloaded official blueprint + current block priority + adaptive scheduling.</span><b>Recommended for board prep →</b></button><button class="mode-choice" id="mode-personal"><strong>Personal Planner</strong><span>Build your own curriculum, exams, deadlines and study blocks without USMLE assumptions.</span><b>Build my own plan →</b></button></div><div class="setup-note">The planner never assumes your school curriculum matches Step 1 exactly.</div>`);
    document.querySelector('#mode-usmle').onclick=blockPicker; document.querySelector('#mode-personal').onclick=personalPlanner;
  }
  window.startStep1=modePicker; window.openPlannerSetup=modePicker;
  const originalSetView=window.setView;
  window.setView=function(view){
    const hasTopics = typeof state !== 'undefined' && Array.isArray(state.snapshot?.topics) && state.snapshot.topics.length>0;
    if(view==='curriculum' && !hasTopics){ personalPlanner(); return; }
    return originalSetView ? originalSetView(view) : undefined;
  };
  const style=document.createElement('style');
  style.textContent=`.setup-modal{max-width:760px!important}.setup-kicker{font-size:10px;letter-spacing:.14em;font-weight:900;color:#0f766e}.setup-modal h2{font-size:28px;letter-spacing:-.04em;margin:8px 0}.setup-copy{color:#71858b;line-height:1.55;margin:0 0 18px}.mode-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}.mode-choice,.block-choice{border:1px solid #dce8e6;background:#fff;text-align:left;border-radius:14px;padding:16px;display:grid;gap:7px;transition:.15s;color:#102a31}.mode-choice:hover,.block-choice:hover{border-color:#71beb6;background:#f5fbfa;transform:translateY(-1px);box-shadow:0 10px 24px rgba(16,42,49,.07)}.mode-choice strong{font-size:17px}.mode-choice span,.block-choice span{font-size:11px;color:#71858b;line-height:1.45}.mode-choice b{font-size:10px;color:#0f766e}.block-grid{display:grid;grid-template-columns:repeat(2,1fr);gap:9px;max-height:55vh;overflow:auto}.block-choice strong{font-size:13px}.block-choice span{font-size:10px}.setup-actions{display:flex;gap:8px;justify-content:flex-end;margin-top:14px}.setup-note{margin-top:15px;padding:10px 12px;border-radius:10px;background:#f6faf9;color:#71858b;font-size:10px}@media(max-width:650px){.mode-grid,.block-grid{grid-template-columns:1fr}.setup-modal h2{font-size:23px}}`;
  document.head.appendChild(style);
})();
