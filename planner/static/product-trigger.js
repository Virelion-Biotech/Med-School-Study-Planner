(() => {
  function add(){
    const view=document.querySelector('#view');
    if(!view||document.querySelector('.smart-command')||document.querySelector('#title')?.textContent!=='Today')return;
    fetch(window.plannerApiUrl('/snapshot')).then(r=>r.json()).then(s=>{
      const topics=s.topics||[], sessions=s.sessions||[], exams=s.exams||[], subs=s.subjects||[];
      if(!topics.length)return;
      const d=new Date().toISOString().slice(0,10),tod=sessions.filter(x=>x.session_date===d&&!x.completed),mins=tod.reduce((a,x)=>a+x.planned_minutes,0),due=topics.filter(x=>x.next_review_due&&x.next_review_due<=d).length,avg=topics.reduce((a,x)=>a+(x.mastery||0),0)/topics.length;
      const ready=Math.round(avg*100*Math.max(.65,1-Math.min(.25,due/Math.max(1,topics.length)*.35)));
      const ex=exams.filter(x=>x.exam_date>=d).sort((a,b)=>a.exam_date.localeCompare(b.exam_date))[0];
      const days=ex?Math.max(0,Math.ceil((new Date(`${ex.exam_date}T00:00:00`)-new Date(`${d}T00:00:00`))/86400000)):null;
      const el=document.createElement('section');el.className='smart-command';el.innerHTML=`<div class="smart-main"><div class="kicker">TODAY</div><h2>${mins} min planned</h2><p>${days==null?'No exam deadline set.':`${days} day(s) until ${String(ex.id).replace(/[&<>]/g,'')}.`} ${tod.length} unfinished session(s).</p><div class="smart-actions"><button class="btn primary big" id="smart-start">Start next session</button><button class="btn secondary" id="smart-behind">I'm behind</button><button class="btn ghost" id="smart-min">Minimum day</button></div></div><div class="smart-readiness"><span>Planning readiness</span><strong>${ready}%</strong><small>Coverage signal, not an exam probability</small></div><div class="smart-why"><b>What changed?</b><span>${due} review(s) due today. The planner will rebalance after your completed sessions.</span><button class="text-btn" id="smart-why-btn">Why these tasks?</button></div>`;
      view.prepend(el);
      const next=[...tod].sort((a,b)=>b.planned_minutes-a.planned_minutes)[0];document.querySelector('#smart-start').onclick=()=>next?window.openSession(Number(next.id)):window.toast&&window.toast('Nothing else is scheduled today.');document.querySelector('#smart-behind').onclick=()=>window.rebuild&&window.rebuild('gentle');document.querySelector('#smart-min').onclick=()=>window.rebuild&&window.rebuild('minimum');document.querySelector('#smart-why-btn').onclick=()=>window.openSmartExplainer&&window.openSmartExplainer();
    });
  }
  document.addEventListener('planner:ready',add);window.addEventListener('load',()=>setTimeout(add,300));
})();