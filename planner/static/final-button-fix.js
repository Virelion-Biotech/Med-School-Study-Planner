(() => {
  // Final authoritative button wiring. Loaded last so it wins over layered patches.
  const toast = (m) => {
    if (typeof window.toast === 'function') return window.toast(m);
    const el = document.querySelector('#toast');
    if (!el) return;
    el.textContent = String(m || '');
    el.classList.add('show');
    clearTimeout(window.__finalToast);
    window.__finalToast = setTimeout(() => el.classList.remove('show'), 2600);
  };

  function wireHeader() {
    const reset = document.querySelector('#reset-btn');
    if (reset) {
      reset.type = 'button'; reset.textContent = 'Change plan';
      reset.onclick = (e) => { e?.preventDefault?.(); e?.stopPropagation?.(); if (typeof window.openPlannerSetup === 'function') window.openPlannerSetup(); else toast('Plan chooser is unavailable'); };
    }
    const mode = document.querySelector('#mode-btn');
    if (mode) {
      mode.type = 'button'; mode.textContent = 'Change mode';
      mode.onclick = (e) => { e?.preventDefault?.(); e?.stopPropagation?.(); if (typeof window.openPlannerSetup === 'function') window.openPlannerSetup(); else toast('Mode chooser is unavailable'); };
    }
    const replan = document.querySelector('#replan-btn');
    if (replan) {
      replan.type = 'button'; replan.removeAttribute('onclick');
      replan.onclick = (e) => { e?.preventDefault?.(); e?.stopPropagation?.(); if (typeof window.replanWeek === 'function') window.replanWeek(); else toast('Rebuild is unavailable'); };
    }
  }

  function wireNav() {
    document.querySelectorAll('#nav .nav').forEach((btn) => {
      if (!btn.dataset.view) return;
      btn.onclick = (e) => { e?.preventDefault?.(); if (typeof window.setView === 'function') window.setView(btn.dataset.view); };
    });
    const tools = document.querySelector('#smart-tools');
    if (tools) {
      tools.removeAttribute('data-view');
      tools.onclick = (e) => { e?.preventDefault?.(); e?.stopPropagation?.(); if (typeof window.openTools === 'function') window.openTools(); else toast('Tools are unavailable'); };
    }
  }

  function wireFirstRun() {
    const bind = (sel, fn) => document.querySelectorAll(sel).forEach((b) => {
      if (b.dataset.finalBound === '1') return;
      b.dataset.finalBound = '1';
      b.addEventListener('click', (e) => { e.preventDefault(); e.stopPropagation(); fn(); }, true);
    });
    bind('#first-usmle, #rf-usmle, #mf-usmle, #offline-usmle', () => {
      if (typeof window.openStep1BlockPicker === 'function') window.openStep1BlockPicker();
      else if (typeof window.startStep1 === 'function') window.startStep1();
      else toast('USMLE setup is unavailable');
    });
    bind('#first-school, #rf-school, #mf-school, #offline-school, #school-direct-entry', () => {
      if (typeof window.openSchoolWhenReady === 'function') window.openSchoolWhenReady();
      else if (typeof window.openSchoolPicker === 'function') window.openSchoolPicker();
      else toast('School setup is unavailable');
    });
    bind('#first-personal, #rf-personal, #mf-personal, #offline-personal', () => {
      if (typeof window.startPersonalPlanner === 'function') window.startPersonalPlanner();
      else toast('Personal planner is unavailable');
    });
    document.querySelectorAll('#view button').forEach((b) => {
      if (b.textContent.trim() !== 'Build my own plan' || b.dataset.finalBound === '1') return;
      b.dataset.finalBound = '1'; b.removeAttribute('onclick');
      b.addEventListener('click', (e) => { e.preventDefault(); if (typeof window.startPersonalPlanner === 'function') window.startPersonalPlanner(); }, true);
    });
  }

  // The personal-v2 timetable importer previously called personalSetup(), which
  // cleared the parsed state immediately after parsing it. Replace that path at
  // the DOM boundary so imported rows are persisted and actually scheduled.
  function wirePersonalImport() {
    const button = document.querySelector('#pv-import-use');
    if (!button || button.dataset.finalImportBound === '1') return;
    button.dataset.finalImportBound = '1';
    button.addEventListener('click', async (event) => {
      event.preventDefault(); event.stopImmediatePropagation();
      const text = document.querySelector('#pv-paste')?.value?.trim() || '';
      if (!text) return toast('Paste at least one timetable line first.');
      try {
        const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {headers:{'Content-Type':'application/json', ...(options.headers || {})}, ...options}).then(async r => { let b={}; try { b=await r.json(); } catch (_) {} if (!r.ok) throw new Error(b.detail || `HTTP ${r.status}`); return b; });
        const initial = await api('/snapshot');
        const subjects = new Map((initial.subjects || []).map(s => [String(s.name).toLowerCase(), s]));
        const rows = text.split(/\n/).map(x => x.trim()).filter(Boolean);
        let imported = 0;
        for (const line of rows) {
          const p = line.split('|').map(x => x.trim());
          if (p.length < 3 || !p[1] || !p[2]) continue;
          const subjectName = p[1], topicName = p[2];
          let subject = subjects.get(subjectName.toLowerCase());
          if (!subject) {
            const id = subjectName.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80) || `imported-${Date.now()}`;
            await api('/subjects', {method:'POST', body:JSON.stringify({id, name:subjectName, exam_weight:1, category:'Imported'})});
            subject = {id, name:subjectName, exam_weight:1, category:'Imported'};
            subjects.set(subjectName.toLowerCase(), subject);
          }
          let lectures=0, slides=0, questions=0;
          p.slice(3).forEach(x => { let m=x.match(/(\d+(?:\.\d+)?)\s*lect/i); if(m) lectures=Number(m[1]); m=x.match(/(\d+(?:\.\d+)?)\s*slide/i); if(m) slides=Number(m[1]); m=x.match(/(\d+)\s*(question|qbank|uworld)/i); if(m) questions=Number(m[1]); });
          const minutes=Math.max(15, lectures*45 + slides*1.5 + questions*1.5);
          await api('/topics', {method:'POST', body:JSON.stringify({id:`import-${Date.now()}-${imported}-${Math.random().toString(36).slice(2,8)}`, subject_id:subject.id, name:topicName, estimated_hours:minutes/60, complexity:.5, mastery:0, self_difficulty:3, volume:Math.min(1,minutes/360), cognitive_load:.75})});
          imported++;
        }
        if (!imported) return toast('No valid timetable rows were found.');
        const profile = await api('/profile');
        const latest = await api('/snapshot');
        await api('/plan', {method:'POST', body:JSON.stringify({
          subjects:(latest.subjects||[]).map(s=>({id:s.id,name:s.name,exam_weight:s.exam_weight,category:s.category})),
          topics:(latest.topics||[]).map(t=>({id:t.id,subject_id:t.subject_id,name:t.name,complexity:t.complexity,estimated_hours:t.estimated_hours,mastery:t.mastery,last_studied:t.last_studied,next_review_due:t.next_review_due,self_difficulty:t.self_difficulty,volume:t.volume,cognitive_load:t.cognitive_load})),
          exams:(latest.exams||[]).map(e=>({id:e.id,date:e.exam_date,subject_ids:JSON.parse(e.subject_ids_json||'[]'),topic_ids:JSON.parse(e.topic_ids_json||'[]'),weight:e.weight})),
          profile, start_date:new Date().toISOString().slice(0,10), days:7, optimizer:true, persist:true, replace_uncompleted:true
        })});
        const modal=document.querySelector('#modal'); if(modal){modal.classList.add('hidden');modal.innerHTML='';}
        await window.load?.(); window.setView?.('today'); toast(`${imported} timetable item(s) imported and scheduled.`);
      } catch (error) { toast(error.message || 'Could not import the timetable.'); }
    }, true);
  }

  function repairSessionSubjectLabel() {
    const original=window.openSession;
    if(typeof original!=='function' || original.__subjectLabelFixed) return;
    const wrapped=function(id){
      original(id);
      const snapshot=window.__plannerSnapshot||{}, session=(snapshot.sessions||[]).find(s=>Number(s.id)===Number(id));
      const topic=(snapshot.topics||[]).find(t=>t.id===session?.topic_id), subject=(snapshot.subjects||[]).find(s=>s.id===topic?.subject_id);
      const p=document.querySelector('#modal .modal-card > p');
      if(p && subject) p.textContent=`${subject.name} · ${session?.planned_minutes ?? ''} minutes · ${String(session?.activity_type || session?.activity || 'mixed').replace(/_/g,' ')}`;
    };
    wrapped.__subjectLabelFixed=true; window.openSession=wrapped;
  }

  function applyAll() { wireHeader(); wireNav(); wireFirstRun(); wirePersonalImport(); repairSessionSubjectLabel(); }
  const start=()=>{ applyAll(); const obs=new MutationObserver(()=>applyAll()); if(document.body) obs.observe(document.body,{childList:true,subtree:true}); };
  if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',start,{once:true}); else start();
  setTimeout(applyAll,0); setTimeout(applyAll,250); setTimeout(applyAll,1000);
})();
