/* Local-first API adapter. It activates only when a planner request cannot reach the remote backend. */
(() => {
  const PREFIXES = ['/health','/profile','/subjects','/topics','/exams','/plan','/replan','/setup','/presets','/sessions','/analytics','/memory','/calibrate','/snapshot','/export','/workspace','/v2'];
  const isPlanner = input => {
    const raw = typeof input === 'string' ? input : (input && input.url) || '';
    return PREFIXES.some(p => raw === p || raw.startsWith(`${p}/`));
  };
  const key = 'med-school-planner-local-state';
  const read = () => {
    try {
      const parsed = JSON.parse(localStorage.getItem(key) || '{}');
      return {
        subjects: Array.isArray(parsed.subjects) ? parsed.subjects : [],
        topics: Array.isArray(parsed.topics) ? parsed.topics : [],
        exams: Array.isArray(parsed.exams) ? parsed.exams : [],
        sessions: Array.isArray(parsed.sessions) ? parsed.sessions : [],
        profile: parsed.profile || {daily_available_minutes:240, minimum_subject_minutes_week:30, review_fraction:.25, max_session_minutes:60, rest_weekdays:[], energy_pattern:['high','medium','medium','low']},
        nextSessionId: Number(parsed.nextSessionId) || 1,
      };
    } catch { return {subjects:[],topics:[],exams:[],sessions:[],profile:{daily_available_minutes:240,minimum_subject_minutes_week:30,review_fraction:.25,max_session_minutes:60,rest_weekdays:[],energy_pattern:['high','medium','medium','low']},nextSessionId:1}; }
  };
  const write = s => { try { localStorage.setItem(key, JSON.stringify(s)); } catch {} };
  const json = (body, status=200) => new Response(JSON.stringify(body), {status, headers:{'Content-Type':'application/json','X-Planner-Local':'1'}});
  const today = () => new Date().toISOString().slice(0,10);
  const plusDays = (iso,n) => { const d=new Date(`${iso}T00:00:00`); d.setDate(d.getDate()+n); return d.toISOString().slice(0,10); };
  const slug = v => String(v||'').toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'').slice(0,50);
  const schedule = (s, start, days=7) => {
    const sessions=[]; const active=s.topics.filter(t=>s.subjects.some(x=>x.id===t.subject_id));
    if (!active.length) return sessions;
    const daily=Math.max(30, Number(s.profile.daily_available_minutes)||240), max=Math.max(15, Math.min(Number(s.profile.max_session_minutes)||60, daily));
    const rest=new Set(Array.isArray(s.profile.rest_weekdays)?s.profile.rest_weekdays:[]);
    for(let d=0; d<days; d++){
      const day=plusDays(start,d); if(rest.has(new Date(`${day}T00:00:00`).getDay())) continue;
      let left=daily, idx=d%s.topics.length, guard=0;
      while(left>=15 && guard++<s.topics.length*3){
        const t=active[idx++%active.length]; const mins=Math.min(max,left);
        sessions.push({session_date:day,topic_id:t.id,planned_minutes:mins,session_type:'new',activity_type:'mixed',completed:false,actual_minutes:null,performance_score:null});
        left-=mins;
        if(mins===0) break;
      }
    }
    return sessions;
  };
  const localHandle = async (input, init={}) => {
    const raw = typeof input === 'string' ? input : (input && input.url) || '';
    const path = raw.replace(/^https?:\/\/[^/]+/,'').split('?')[0] || '/';
    const method=String(init.method||'GET').toUpperCase();
    let body={}; try { body=init.body ? JSON.parse(init.body) : {}; } catch {}
    const s=read();
    if(path==='/health') return json({status:'ok',mode:'local',engine:'local-first-fallback',ui:'available'});
    if(path==='/snapshot' && method==='GET') return json({subjects:s.subjects,topics:s.topics,exams:s.exams,sessions:s.sessions});
    if(path==='/profile' && method==='GET') return json(s.profile);
    if(path==='/profile' && method==='PUT'){s.profile=body;write(s);return json(s.profile);}
    if(path==='/subjects' && method==='POST'){s.subjects=s.subjects.filter(x=>x.id!==body.id);s.subjects.push(body);write(s);return json({status:'saved',subject:body});}
    if(path.startsWith('/subjects/') && method==='DELETE'){const id=decodeURIComponent(path.split('/')[2]);s.subjects=s.subjects.filter(x=>x.id!==id);s.topics=s.topics.filter(x=>x.subject_id!==id);write(s);return json({status:'deleted',id});}
    if(path==='/topics' && method==='POST'){s.topics=s.topics.filter(x=>x.id!==body.id);s.topics.push(body);write(s);return json({status:'saved',topic:body});}
    if(path.startsWith('/topics/') && method==='DELETE'){const id=decodeURIComponent(path.split('/')[2]);s.topics=s.topics.filter(x=>x.id!==id);write(s);return json({status:'deleted',id});}
    if(path==='/exams' && method==='POST'){s.exams=s.exams.filter(x=>x.id!==body.id);s.exams.push(body);write(s);return json({status:'saved',exam:body});}
    if(path.startsWith('/exams/') && method==='DELETE'){const id=decodeURIComponent(path.split('/')[2]);s.exams=s.exams.filter(x=>x.id!==id);write(s);return json({status:'deleted',id});}
    if(path==='/plan' && method==='POST'){
      s.subjects=Array.isArray(body.subjects)?body.subjects:s.subjects; s.topics=Array.isArray(body.topics)?body.topics:s.topics; s.exams=Array.isArray(body.exams)?body.exams:s.exams; s.profile=body.profile||s.profile;
      if(body.replace_uncompleted!==false) s.sessions=s.sessions.filter(x=>x.completed);
      const start=body.start_date||today(), days=Math.min(31,Math.max(1,Number(body.days)||7)); const generated=schedule(s,start,days);
      if(body.persist){generated.forEach(x=>{x.id=s.nextSessionId++;});s.sessions.push(...generated);write(s);}
      return json({sessions:generated,subject_minutes:{},unfulfilled_floor:{},unfulfilled_exam_coverage:{},optimizer:false,persisted:!!body.persist});
    }
    if(path==='/replan' && method==='POST'){
      const start=body.start_date||today(), days=Math.min(31,Math.max(1,Number(body.days)||7)); const locked=new Set((body.locked_session_ids||[]).map(Number));
      const keep=s.sessions.filter(x=>x.completed||locked.has(Number(x.id))); s.sessions=keep; const generated=schedule(s,start,days).filter(x=>!keep.some(k=>k.session_date===x.session_date&&k.topic_id===x.topic_id)); generated.forEach(x=>{x.id=s.nextSessionId++;}); s.sessions.push(...generated);write(s);return json({sessions:generated,subject_minutes:{},unfulfilled_floor:{},unfulfilled_exam_coverage:{},optimizer:false,locked_session_ids:[...locked]});
    }
    const completeMatch=path.match(/^\/sessions\/(\d+)\/complete$/);
    if(completeMatch && method==='POST'){
      const id=Number(completeMatch[1]), row=s.sessions.find(x=>Number(x.id)===id); if(!row) return json({detail:'Session not found'},404); if(row.completed) return json({detail:'Session already completed'},409);
      row.completed=true; row.actual_minutes=Number(body.actual_minutes)||0; row.performance_score=Number(body.performance_score); write(s); return json({status:'completed',session_id:id});
    }
    if(path==='/analytics' && method==='GET'){
      const completed=s.sessions.filter(x=>x.completed).length, planned=s.sessions.length; const perf=s.sessions.filter(x=>x.performance_score!=null);
      return json({completion_rate:planned?completed/planned:0,mean_performance:perf.length?perf.reduce((a,x)=>a+x.performance_score,0)/perf.length:null,planning_error_minutes:0,reviews_due:0,topic_time_history:{}});
    }
    if(path==='/calibrate' && method==='POST') return json({updated:[],count:0});
    const readiness=path==='/v2/readiness' && method==='GET';
    if(readiness){const mastery=s.topics.length?s.topics.reduce((a,t)=>a+Number(t.mastery||0),0)/s.topics.length:0;return json({readiness:'moderate',knowledge:mastery,retention:1,coverage:s.sessions.length?s.sessions.filter(x=>x.completed).length/s.sessions.length:0,practice:0,deadline:1});}
    return json({detail:'Local planner fallback does not implement this endpoint yet'},501);
  };

  const original = window.fetch.bind(window);
  window.fetch = async (input, init={}) => {
    if(!isPlanner(input)) return original(input,init);
    try { return await original(input,init); }
    catch(error) {
      const response = await localHandle(input,init);
      if(response.status !== 501) return response;
      throw error;
    }
  };
})();
