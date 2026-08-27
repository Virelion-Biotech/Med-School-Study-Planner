/* Local-first API adapter. It activates only when a planner request cannot reach the remote backend. */
(() => {
  const PREFIXES=['/health','/profile','/subjects','/topics','/exams','/plan','/replan','/setup','/presets','/sessions','/analytics','/memory','/calibrate','/snapshot','/export','/workspace','/v2'];
  const apiBase=()=>String(window.PLANNER_API_BASE||'').replace(/\/$/,'');
  const isPlanner=input=>{const raw=typeof input==='string'?input:(input&&input.url)||'';return PREFIXES.some(p=>raw===p||raw.startsWith(`${p}/`))||(apiBase()&&raw.startsWith(`${apiBase()}/`));};
  const key='med-school-planner-local-state';
  const defaults=()=>({subjects:[],topics:[],exams:[],sessions:[],profile:{daily_available_minutes:240,minimum_subject_minutes_week:30,review_fraction:.25,max_session_minutes:60,rest_weekdays:[],energy_pattern:['high','medium','medium','low']},nextSessionId:1});
  const read=()=>{try{const p=JSON.parse(localStorage.getItem(key)||'{}');return {subjects:Array.isArray(p.subjects)?p.subjects:[],topics:Array.isArray(p.topics)?p.topics:[],exams:Array.isArray(p.exams)?p.exams:[],sessions:Array.isArray(p.sessions)?p.sessions:[],profile:p.profile||defaults().profile,nextSessionId:Number(p.nextSessionId)||1};}catch{return defaults();}};
  const write=s=>{try{localStorage.setItem(key,JSON.stringify(s));}catch{}};
  const json=(body,status=200)=>new Response(JSON.stringify(body),{status,headers:{'Content-Type':'application/json','X-Planner-Local':'1'}});
  const today=()=>new Date().toISOString().slice(0,10);
  const plus=(iso,n)=>{const d=new Date(`${iso}T00:00:00`);d.setDate(d.getDate()+n);return d.toISOString().slice(0,10);};
  const schedule=(s,start,days)=>{const out=[],tops=s.topics.filter(t=>s.subjects.some(x=>x.id===t.subject_id)),daily=Math.max(30,Number(s.profile.daily_available_minutes)||240),max=Math.max(15,Math.min(Number(s.profile.max_session_minutes)||60,daily)),rest=new Set(s.profile.rest_weekdays||[]);if(!tops.length)return out;for(let i=0;i<days;i++){const day=plus(start,i);if(rest.has(new Date(`${day}T00:00:00`).getDay()))continue;let left=daily,idx=i%tops.length;while(left>=15){const t=tops[idx++%tops.length],m=Math.min(max,left);out.push({session_date:day,topic_id:t.id,planned_minutes:m,session_type:'new',activity_type:'mixed',completed:false,actual_minutes:null,performance_score:null});left-=m;}}return out;};
  const handle=async(input,init={})=>{const raw=typeof input==='string'?input:(input&&input.url)||'',path=raw.replace(/^https?:\/\/[^/]+/,'').split('?')[0]||'/',method=String(init.method||'GET').toUpperCase();let body={};try{body=init.body?JSON.parse(init.body):{};}catch{}const s=read();
    if(path==='/health')return json({status:'ok',mode:'local'});
    if(path==='/snapshot'&&method==='GET')return json({subjects:s.subjects,topics:s.topics,exams:s.exams,sessions:s.sessions});
    if(path==='/profile'&&method==='GET')return json(s.profile);
    if(path==='/profile'&&method==='PUT'){s.profile=body;write(s);return json(s.profile);}
    if(path==='/subjects'&&method==='POST'){s.subjects=s.subjects.filter(x=>x.id!==body.id);s.subjects.push(body);write(s);return json({status:'saved',subject:body});}
    if(path.startsWith('/subjects/')&&method==='DELETE'){const id=decodeURIComponent(path.split('/')[2]);s.subjects=s.subjects.filter(x=>x.id!==id);s.topics=s.topics.filter(x=>x.subject_id!==id);write(s);return json({status:'deleted',id});}
    if(path==='/topics'&&method==='POST'){s.topics=s.topics.filter(x=>x.id!==body.id);s.topics.push(body);write(s);return json({status:'saved',topic:body});}
    if(path.startsWith('/topics/')&&method==='DELETE'){const id=decodeURIComponent(path.split('/')[2]);s.topics=s.topics.filter(x=>x.id!==id);write(s);return json({status:'deleted',id});}
    if(path==='/exams'&&method==='POST'){s.exams=s.exams.filter(x=>x.id!==body.id);s.exams.push(body);write(s);return json({status:'saved',exam:body});}
    if(path.startsWith('/exams/')&&method==='DELETE'){const id=decodeURIComponent(path.split('/')[2]);s.exams=s.exams.filter(x=>x.id!==id);write(s);return json({status:'deleted',id});}
    if(path==='/plan'&&method==='POST'){s.subjects=Array.isArray(body.subjects)?body.subjects:s.subjects;s.topics=Array.isArray(body.topics)?body.topics:s.topics;s.exams=Array.isArray(body.exams)?body.exams:s.exams;s.profile=body.profile||s.profile;if(body.replace_uncompleted!==false)s.sessions=s.sessions.filter(x=>x.completed);const generated=schedule(s,body.start_date||today(),Math.min(31,Math.max(1,Number(body.days)||7)));if(body.persist){generated.forEach(x=>x.id=s.nextSessionId++);s.sessions.push(...generated);write(s);}return json({sessions:generated,subject_minutes:{},unfulfilled_floor:{},unfulfilled_exam_coverage:{},optimizer:false,persisted:!!body.persist});}
    if(path==='/replan'&&method==='POST'){const start=body.start_date||today(),days=Math.min(31,Math.max(1,Number(body.days)||7)),locked=new Set((body.locked_session_ids||[]).map(Number));s.sessions=s.sessions.filter(x=>x.completed||locked.has(Number(x.id)));const generated=schedule(s,start,days);generated.forEach(x=>x.id=s.nextSessionId++);s.sessions.push(...generated);write(s);return json({sessions:generated,subject_minutes:{},unfulfilled_floor:{},unfulfilled_exam_coverage:{},optimizer:false});}
    const cm=path.match(/^\/sessions\/(\d+)\/complete$/);if(cm&&method==='POST'){const row=s.sessions.find(x=>Number(x.id)===Number(cm[1]));if(!row)return json({detail:'Session not found'},404);if(row.completed)return json({detail:'Session already completed'},409);row.completed=true;row.actual_minutes=Number(body.actual_minutes)||0;row.performance_score=Number(body.performance_score);write(s);return json({status:'completed',session_id:row.id});}
    if(path==='/analytics'&&method==='GET'){const done=s.sessions.filter(x=>x.completed),perf=done.filter(x=>x.performance_score!=null);return json({completion_rate:s.sessions.length?done.length/s.sessions.length:0,mean_performance:perf.length?perf.reduce((a,x)=>a+x.performance_score,0)/perf.length:null,planning_error_minutes:0,reviews_due:0,topic_time_history:{}});}
    if(path==='/calibrate'&&method==='POST')return json({updated:[],count:0});
    if(path==='/v2/readiness'&&method==='GET'){const mastery=s.topics.length?s.topics.reduce((a,t)=>a+Number(t.mastery||0),0)/s.topics.length:0;return json({readiness:'moderate',knowledge:mastery,retention:1,coverage:s.sessions.length?s.sessions.filter(x=>x.completed).length/s.sessions.length:0,practice:0,deadline:1});}
    return json({detail:'Local planner fallback does not implement this endpoint yet'},501);
  };
  const original=window.fetch.bind(window);
  window.fetch=async(input,init={})=>{if(!isPlanner(input))return original(input,init);try{return await original(input,init);}catch(error){const response=await handle(input,init);if(response.status!==501)return response;throw error;}};
})();
