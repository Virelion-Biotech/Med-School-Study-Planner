const state = { view: 'today', snapshot: {subjects: [], topics: [], exams: [], sessions: []}, profile: null, modal: null, dragSessionId: null };
const $ = s => document.querySelector(s);
const $$ = s => [...document.querySelectorAll(s)];
const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const today = () => new Date().toISOString().slice(0, 10);
const plusDays = (iso, n) => { const d = new Date(`${iso}T00:00:00`); d.setDate(d.getDate() + n); return d.toISOString().slice(0, 10); };
const weekStart = iso => { const d = new Date(`${iso}T00:00:00`); d.setDate(d.getDate() - d.getDay()); return d.toISOString().slice(0, 10); };
const daysUntil = iso => Math.max(0, Math.ceil((new Date(`${iso}T00:00:00`) - new Date(`${today()}T00:00:00`)) / 86400000));
const subjects = () => state.snapshot.subjects || [];
const topics = () => state.snapshot.topics || [];
const exams = () => state.snapshot.exams || [];
const sessions = () => state.snapshot.sessions || [];
const topicById = id => topics().find(t => t.id === id);
const subjectById = id => subjects().find(s => s.id === id);
const topicName = id => topicById(id)?.name || id;
const subjectName = id => subjectById(id)?.name || id;

function toast(message) { const el = $('#toast'); if (!el) return; el.textContent = message; el.classList.add('show'); clearTimeout(window.__toastTimer); window.__toastTimer = setTimeout(() => el.classList.remove('show'), 2600); }
window.toast = toast;

async function api(path, options = {}) {
  const url = window.plannerApiUrl ? window.plannerApiUrl(path) : path;
  const response = await fetch(url, { headers: {'Content-Type': 'application/json', ...(options.headers || {})}, ...options });
  let body = null;
  try { body = await response.json(); } catch (_) {}
  if (!response.ok) throw new Error(body?.detail || `Request failed (${response.status})`);
  return body;
}

async function load() {
  try {
    state.snapshot = await api('/snapshot');
    state.profile = await api('/profile');
    window.__plannerSnapshot = state.snapshot;
    $('#engine-status').textContent = `Backend live · ${state.snapshot.topics?.length || 0} topics`;
    $('#engine-status').previousElementSibling?.classList.add('live');
    render();
  } catch (error) {
    $('#engine-status').textContent = 'Backend unavailable';
    toast(error.message);
    renderOffline(error.message);
  }
}
window.load = load;

function navItem(label, view, icon) { return `<button class="nav-item ${state.view === view ? 'active' : ''}" data-view="${view}"><span class="nav-icon">${icon}</span><span>${label}</span></button>`; }

function render() {
  const titles = {today: 'Today', week: 'Week', curriculum: 'Curriculum', exams: 'Exams', insights: 'Insights'};
  const subtitles = {
    today: 'Your most important work, pulled together for today.',
    week: 'A balanced week built around your exams, memory and available time.',
    curriculum: 'Build the topics the planner will actually schedule.',
    exams: 'Tell the planner what matters and when it matters.',
    insights: 'See what the system has learned from your study history.'
  };
  $('#page-title').textContent = titles[state.view];
  $('#page-subtitle').textContent = subtitles[state.view];
  $$('.nav-item').forEach(b => b.classList.toggle('active', b.dataset.view === state.view));
  const renderers = {today: renderToday, week: renderWeek, curriculum: renderCurriculum, exams: renderExams, insights: renderInsights};
  renderers[state.view]($('#view'));
}

function renderOffline(message) {
  $('#view').innerHTML = `<div class="hero-card danger-hero"><div><div class="eyebrow">Connection problem</div><h2>The planner backend could not be reached.</h2><p>${esc(message)}</p><div class="hero-actions"><button class="btn primary" onclick="load()">Retry connection</button></div></div><div class="hero-orb">!</div></div>`;
}

function onboardingCard() {
  return `<div class="onboarding hero-card">
    <div class="hero-copy"><div class="eyebrow">Welcome</div><h2>Build your study plan in three moves.</h2><p>This is the control center for your medical curriculum. Start with a demo to see the planner working, or enter your real subjects and exams.</p>
      <div class="hero-actions"><button class="btn primary" onclick="seed()">Load a realistic demo</button><button class="btn ghost" onclick="setView('curriculum')">Add my curriculum</button></div>
    </div>
    <div class="steps"><div><span>01</span><strong>Curriculum</strong><small>Add subjects and topics.</small></div><div><span>02</span><strong>Exams</strong><small>Add dates and coverage.</small></div><div><span>03</span><strong>Plan</strong><small>Generate and study.</small></div></div>
  </div>`;
}

function stat(label, value, sub, tone='') { return `<div class="stat-card ${tone}"><div class="stat-label">${label}</div><div class="stat-value">${value}</div><div class="stat-sub">${sub}</div></div>`; }

function sessionCard(s, mini=false) {
  const t = topicById(s.topic_id); const done = Boolean(s.completed); const type = s.session_type || 'new';
  return `<div class="${mini ? 'mini-session' : 'session-row'} ${done ? 'completed' : ''} session-card" draggable="${Boolean(s.id) && !done}" data-session-id="${s.id || ''}">
    <div class="session-time">${s.planned_minutes}m</div><div class="session-main"><strong>${esc(t?.name || s.topic_id)}</strong><span>${esc(subjectName(t?.subject_id || ''))}${done ? ' · completed' : ''}</span></div><span class="chip ${type}">${type}</span>
  </div>`;
}

function renderToday(v) {
  const d = today();
  const todays = sessions().filter(s => s.session_date === d);
  const future = sessions().filter(s => s.session_date >= d && s.session_date < plusDays(d, 7));
  const done = sessions().filter(s => s.completed).length;
  const upcoming = exams().filter(e => e.exam_date >= d).sort((a,b) => a.exam_date.localeCompare(b.exam_date)).slice(0, 3);
  if (!topics().length) { v.innerHTML = onboardingCard(); return; }
  const planned = todays.reduce((a,s) => a + Number(s.planned_minutes || 0), 0);
  const weekly = future.reduce((a,s) => a + Number(s.planned_minutes || 0), 0);
  const next = upcoming[0];
  v.innerHTML = `<div class="stats-grid">${stat('Today', `${planned}m`, `${todays.length} sessions`, 'teal')}${stat('This week', `${weekly}m`, 'scheduled minutes')}${stat('Completed', done, 'feedback signals')}${stat('Next exam', next ? `${daysUntil(next.exam_date)}d` : '—', next ? esc(next.id) : 'add an exam')}</div>
  <div class="dashboard-grid">
    <section class="panel large"><div class="panel-head"><div><span class="section-kicker">DO THIS NOW</span><h2>Today's sessions</h2></div><button class="btn small ghost" onclick="setView('week')">Open week</button></div>
      ${todays.length ? todays.map(s => sessionCard(s)).join('') : `<div class="empty-state"><div class="empty-icon">✓</div><strong>Nothing scheduled today.</strong><span>Replan the week or add more curriculum.</span><button class="btn primary small" onclick="replanWeek()">Generate today</button></div>`}
    </section>
    <section class="panel"><div class="panel-head"><div><span class="section-kicker">EXAM PRESSURE</span><h2>What is coming?</h2></div><button class="btn small ghost" onclick="setView('exams')">Manage</button></div>
      ${upcoming.length ? upcoming.map(e => `<div class="exam-tile"><div><strong>${esc(e.id)}</strong><span>${e.exam_date}</span></div><b>${daysUntil(e.exam_date)}d</b><div class="pressure"><i style="width:${Math.max(8, Math.min(100, 100 - daysUntil(e.exam_date) * 2))}%"></i></div></div>`).join('') : `<div class="empty-state compact"><strong>No exams yet.</strong><span>Add an exam so urgency can shape the schedule.</span><button class="btn ghost small" onclick="setView('exams')">Add exam</button></div>`}
    </section>
  </div>`;
}

function renderWeek(v) {
  if (!topics().length) { v.innerHTML = onboardingCard(); return; }
  const start = weekStart(today()); const days = Array.from({length: 7}, (_,i) => plusDays(start, i)); const grouped = {};
  sessions().forEach(s => (grouped[s.session_date] ||= []).push(s));
  const total = sessions().reduce((a,s) => a + Number(s.planned_minutes || 0), 0);
  v.innerHTML = `<section class="panel"><div class="panel-head week-head"><div><span class="section-kicker">SCHEDULE</span><h2>Weekly allocation <em>${total} min</em></h2><span>Drag an unfinished card to another day. The rest of the week will rebalance around it.</span></div><button class="btn primary" onclick="replanWeek()">Rebalance week</button></div><div class="week-grid">${days.map(d => `<div class="day-column dropzone" data-date="${d}"><div class="day-header"><strong>${new Date(`${d}T00:00:00`).toLocaleDateString(undefined,{weekday:'short'})}</strong><span>${d.slice(5)}</span></div><div class="day-sessions">${(grouped[d] || []).length ? grouped[d].map(s => sessionCard(s,true)).join('') : '<div class="drop-hint">Drop here</div>'}</div></div>`).join('')}</div></section>`;
  bindDragDrop();
}

function renderCurriculum(v) {
  const rows = topics().map(t => `<tr><td><strong>${esc(t.name)}</strong><span class="subrow">${esc(t.id)}</span></td><td>${esc(subjectName(t.subject_id))}</td><td><div class="mastery-cell"><div class="bar"><i style="width:${Math.round(t.mastery*100)}%"></i></div><span>${Math.round(t.mastery*100)}%</span></div></td><td>${Math.round(t.complexity*100)}%</td><td>${t.next_review_due || 'Not scheduled'}</td><td><button class="icon-btn" onclick='editTopic(${JSON.stringify(t)})'>Edit</button></td></tr>`).join('');
  v.innerHTML = `<div class="toolbar-row"><div><span class="section-kicker">CURRICULUM</span><h2>${subjects().length} subjects · ${topics().length} topics</h2></div><div><button class="btn ghost" onclick="addSubject()">+ Subject</button><button class="btn primary" onclick="addTopic()">+ Topic</button></div></div>
    <div class="split-management"><section class="panel"><div class="panel-head"><div><h2>Subjects</h2><span>Fairness is enforced at this level.</span></div></div><div class="subject-list">${subjects().length ? subjects().map(s => `<div class="manage-row"><div><strong>${esc(s.name)}</strong><span>${esc(s.category)} · exam weight ${s.exam_weight}</span></div><div class="row-actions"><button class="icon-btn" onclick='editSubject(${JSON.stringify(s)})'>Edit</button><button class="icon-btn danger" onclick="deleteSubject('${esc(s.id)}')">Delete</button></div></div>`).join('') : '<div class="empty-state compact">No subjects yet.</div>'}</div></section>
    <section class="panel"><div class="panel-head"><div><h2>Topics</h2><span>These are what the engine schedules.</span></div></div>${rows ? `<div class="table-wrap"><table><thead><tr><th>Topic</th><th>Subject</th><th>Mastery</th><th>Complexity</th><th>Review</th><th></th></tr></thead><tbody>${rows}</tbody></table></div>` : '<div class="empty-state compact">No topics yet. Add a topic to start scheduling.</div>'}</section></div>`;
}

function renderExams(v) {
  const examCards = exams().length ? exams().map(e => { const ss = JSON.parse(e.subject_ids_json || '[]'); const ts = JSON.parse(e.topic_ids_json || '[]'); return `<div class="exam-manage"><div><strong>${esc(e.id)}</strong><span>${e.exam_date} · weight ${e.weight}</span><p>${ss.map(subjectName).map(esc).join(', ') || 'No subject coverage'}${ts.length ? ` · ${ts.length} specific topics` : ''}</p></div><div class="row-actions"><button class="icon-btn" onclick='editExam(${JSON.stringify(e)})'>Edit</button><button class="icon-btn danger" onclick="deleteExam('${esc(e.id)}')">Delete</button></div></div>`; }).join('') : '<div class="empty-state compact">No exams yet. Add one so urgency and coverage can be enforced.</div>';
  const p = state.profile || {daily_available_minutes:240, minimum_subject_minutes_week:60, review_fraction:.25, max_session_minutes:60, rest_weekdays:[]};
  v.innerHTML = `<div class="toolbar-row"><div><span class="section-kicker">EXAM CALENDAR</span><h2>${exams().length} exams configured</h2></div><button class="btn primary" onclick="addExam()">+ Add exam</button></div>
    <div class="dashboard-grid"><section class="panel"><div class="panel-head"><div><h2>Upcoming exams</h2><span>Exam dates drive priority and hard coverage.</span></div></div>${examCards}</section>
    <section class="panel"><div class="panel-head"><div><h2>Study settings</h2><span>These constraints shape every plan.</span></div></div><form id="profile-form" class="settings-form"><div class="field"><label>Daily available minutes</label><input id="p-daily" type="number" min="30" max="1440" value="${p.daily_available_minutes}"></div><div class="field"><label>Weekly minimum per subject</label><input id="p-floor" type="number" min="0" value="${p.minimum_subject_minutes_week}"></div><div class="field"><label>Protected review fraction</label><input id="p-review" type="number" min="0" max="1" step=".05" value="${p.review_fraction}"></div><div class="field"><label>Maximum session</label><input id="p-max" type="number" min="15" max="240" value="${p.max_session_minutes}"></div><div class="field full"><label>Rest days</label><div class="checks">${['Sun','Mon','Tue','Wed','Thu','Fri','Sat'].map((n,i) => `<label><input class="rest-box" type="checkbox" value="${i}" ${(p.rest_weekdays||[]).includes(i)?'checked':''}> ${n}</label>`).join('')}</div></div><button class="btn primary full" type="submit">Save settings + replan</button></form></section></div>`;
  $('#profile-form').onsubmit = saveProfile;
}

async function renderInsights(v) {
  if (!topics().length) { v.innerHTML = onboardingCard(); return; }
  v.innerHTML = `<div class="stats-grid">${stat('Mean mastery', `${Math.round(topics().reduce((a,t)=>a+t.mastery,0)/topics().length*100)}%`, 'across topics', 'teal')}${stat('Reviews due', topics().filter(t=>t.next_review_due && t.next_review_due <= today()).length, 'protected demand')}${stat('Sessions', sessions().length, 'all persisted sessions')}${stat('Subjects', subjects().length, 'active curriculum')}</div><div id="analytics-panel" class="panel"><div class="panel-head"><div><span class="section-kicker">OBSERVED SIGNAL</span><h2>How the planner is learning from you</h2></div><button class="btn ghost" onclick="calibratePlanner()">Recalibrate complexity</button></div><div id="analytics-grid" class="analytics-grid"><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton"></div></div><div class="panel-foot"><a class="btn ghost small" href="${window.plannerApiUrl('/export/sessions.csv')}" target="_blank">Export sessions CSV</a><a class="btn ghost small" href="${window.plannerApiUrl('/export/snapshot.json')}" target="_blank">Export snapshot</a></div></div><section class="panel"><div class="panel-head"><div><span class="section-kicker">MASTERY</span><h2>Subject profile</h2></div></div>${subjects().map(s => { const vals = topics().filter(t=>t.subject_id===s.id).map(t=>t.mastery); const p = vals.length ? Math.round(vals.reduce((a,b)=>a+b,0)/vals.length*100) : 0; return `<div class="mastery-row"><div><strong>${esc(s.name)}</strong><span>${vals.length} topics</span></div><div class="bar"><i style="width:${p}%"></i></div><b>${p}%</b></div>`; }).join('')}</section>`;
  try { const d = await api('/analytics'); $('#analytics-grid').innerHTML = `${stat('Completion', `${Math.round(d.completion_rate*100)}%`, 'planned sessions completed')}${stat('Mean performance', d.mean_performance == null ? '—' : `${Math.round(d.mean_performance*100)}%`, 'session ratings')}${stat('Planning error', `${d.planning_error_minutes >= 0 ? '+' : ''}${d.planning_error_minutes}m`, 'actual − planned')}${stat('Reviews due', d.reviews_due, 'as of today')}`; } catch (e) { toast(e.message); }
}

function setView(view) { state.view = view; render(); }
window.setView = setView;

function bindSessionClicks() { $$('.session-card').forEach(el => el.addEventListener('click', e => { if (e.target.closest('button')) return; const id = Number(el.dataset.sessionId); if (id) openSession(id); })); }
function bindDragDrop() { $$('.session-card[draggable="true"]').forEach(el => { el.addEventListener('dragstart', () => { state.dragSessionId = Number(el.dataset.sessionId); el.classList.add('dragging'); }); el.addEventListener('dragend', () => el.classList.remove('dragging')); }); $$('.dropzone').forEach(z => { z.addEventListener('dragover', e => { e.preventDefault(); z.classList.add('drag-over'); }); z.addEventListener('dragleave', () => z.classList.remove('drag-over')); z.addEventListener('drop', async e => { e.preventDefault(); z.classList.remove('drag-over'); const id = state.dragSessionId; state.dragSessionId = null; if (id) await reschedule(id, z.dataset.date); }); }); bindSessionClicks(); }

async function reschedule(id, newDate) { try { await api(`/sessions/${id}/reschedule`, {method:'POST', body: JSON.stringify({new_date:newDate})}); await replanWeek([id], true); toast('Session moved and week rebalanced'); } catch (e) { toast(e.message); await load(); } }

async function replanWeek(locked = [], silent = false) { try { await api('/replan', {method:'POST', body: JSON.stringify({start_date:weekStart(today()), days:7, optimizer:true, locked_session_ids:locked})}); await load(); if (!silent) toast('Week rebalanced'); } catch (e) { toast(e.message); } }
window.replanWeek = replanWeek;

async function seed() {
  const subjectsPayload = [{id:'anatomy',name:'Anatomy',exam_weight:1.1,category:'preclinical'},{id:'pharm',name:'Pharmacology',exam_weight:1.2,category:'preclinical'},{id:'path',name:'Pathology',exam_weight:1.0,category:'preclinical'},{id:'physio',name:'Physiology',exam_weight:1.0,category:'preclinical'}];
  const topicsPayload = [['heart-anatomy','anatomy','Heart anatomy',.55,2,.45],['thorax','anatomy','Thorax & mediastinum',.60,2.5,.30],['autonomic','pharm','Autonomic drugs',.72,3,.20],['antibiotics','pharm','Antibiotics',.68,3,.55],['hemo','path','Hemodynamic pathology',.64,2.5,.35],['inflammation','path','Inflammation',.50,2,.65],['cardiac-cycle','physio','Cardiac cycle',.62,2,.50],['renal','physio','Renal physiology',.70,3,.25]].map(([id,s,n,c,h,m])=>({id,subject_id:s,name:n,complexity:c,estimated_hours:h,mastery:m,self_difficulty:Math.round(c*4+1),volume:c,cognitive_load:c}));
  const examPayload = [{id:'Block exam',date:plusDays(today(),9),subject_ids:subjectsPayload.map(s=>s.id),topic_ids:[],weight:1.2}];
  try { await api('/plan',{method:'POST',body:JSON.stringify({subjects:subjectsPayload,topics:topicsPayload,exams:examPayload,profile:{daily_available_minutes:240,minimum_subject_minutes_week:60,review_fraction:.25,max_session_minutes:60,rest_weekdays:[],energy_pattern:['high','high','medium','medium']},start_date:today(),days:7,optimizer:true,persist:true,replace_uncompleted:true})}); await load(); toast('Demo curriculum loaded — your week is ready'); } catch (e) { toast(e.message); }
}
window.seed = seed;

function modalShell(title, body, saveLabel='Save') { let m = $('#editor-modal'); if (!m) { m = document.createElement('div'); m.id='editor-modal'; m.className='modal hidden'; document.body.appendChild(m); } m.innerHTML = `<div class="modal-card"><div class="modal-head"><div><div class="eyebrow">Planner setup</div><h3>${title}</h3></div><button class="close" onclick="closeEditor()">×</button></div>${body}<div class="drawer-actions"><button id="editor-save" class="btn primary">${saveLabel}</button><button class="btn ghost" onclick="closeEditor()">Cancel</button></div></div>`; m.classList.remove('hidden'); }
function closeEditor() { const m=$('#editor-modal'); if (m) m.classList.add('hidden'); }
window.closeEditor = closeEditor;
function multiOptions(items, selected=[]) { return items.map(x => `<option value="${esc(x.id)}" ${selected.includes(x.id) ? 'selected' : ''}>${esc(x.name || x.id)}</option>`).join(''); }

function addSubject() { modalShell('Add subject', `<div class="form-grid"><div class="field"><label>ID</label><input id="e-id" pattern="[A-Za-z0-9_-]+" placeholder="cardiology"></div><div class="field"><label>Name</label><input id="e-name" placeholder="Cardiology"></div><div class="field"><label>Exam weight</label><input id="e-weight" type="number" min="0" step=".1" value="1"></div><div class="field"><label>Category</label><input id="e-cat" value="general"></div></div>`); $('#editor-save').onclick = async () => { try { await api('/subjects',{method:'POST',body:JSON.stringify({id:$('#e-id').value.trim(),name:$('#e-name').value.trim(),exam_weight:Number($('#e-weight').value),category:$('#e-cat').value.trim()})}); closeEditor(); await load(); toast('Subject added'); } catch(e) { toast(e.message); } }; }
function editSubject(x) { modalShell('Edit subject', `<div class="form-grid"><div class="field"><label>ID</label><input id="e-id" value="${esc(x.id)}" readonly></div><div class="field"><label>Name</label><input id="e-name" value="${esc(x.name)}"></div><div class="field"><label>Exam weight</label><input id="e-weight" type="number" min="0" step=".1" value="${x.exam_weight}"></div><div class="field"><label>Category</label><input id="e-cat" value="${esc(x.category)}"></div></div>`); $('#editor-save').onclick = async () => { try { await api('/subjects',{method:'POST',body:JSON.stringify({id:x.id,name:$('#e-name').value.trim(),exam_weight:Number($('#e-weight').value),category:$('#e-cat').value.trim()})}); closeEditor(); await load(); toast('Subject updated'); } catch(e) { toast(e.message); } }; }
window.addSubject=addSubject; window.editSubject=editSubject;

function addTopic() { if (!subjects().length) { toast('Add a subject first'); setView('curriculum'); return; } modalShell('Add topic', `<div class="form-grid"><div class="field"><label>ID</label><input id="e-id" placeholder="heart-failure"></div><div class="field"><label>Name</label><input id="e-name" placeholder="Heart failure"></div><div class="field"><label>Subject</label><select id="e-sub">${multiOptions(subjects())}</select></div><div class="field"><label>Estimated hours</label><input id="e-hours" type="number" min=".25" step=".25" value="1"></div><div class="field"><label>Mastery 0–1</label><input id="e-mastery" type="number" min="0" max="1" step=".01" value="0"></div><div class="field"><label>Complexity 0–1</label><input id="e-complexity" type="number" min="0" max="1" step=".01" value=".5"></div><div class="field"><label>Difficulty 1–5</label><input id="e-diff" type="number" min="1" max="5" step=".5" value="3"></div><div class="field"><label>Volume 0–1</label><input id="e-volume" type="number" min="0" max="1" step=".01" value=".5"></div><div class="field"><label>Cognitive load 0–1</label><input id="e-load" type="number" min="0" max="1" step=".01" value=".5"></div></div>`); $('#editor-save').onclick = saveTopic; }
function editTopic(x) { modalShell('Edit topic', `<div class="form-grid"><div class="field"><label>ID</label><input id="e-id" value="${esc(x.id)}" readonly></div><div class="field"><label>Name</label><input id="e-name" value="${esc(x.name)}"></div><div class="field"><label>Subject</label><select id="e-sub">${multiOptions(subjects(),[x.subject_id])}</select></div><div class="field"><label>Estimated hours</label><input id="e-hours" type="number" min=".25" step=".25" value="${x.estimated_hours}"></div><div class="field"><label>Mastery 0–1</label><input id="e-mastery" type="number" min="0" max="1" step=".01" value="${x.mastery}"></div><div class="field"><label>Complexity 0–1</label><input id="e-complexity" type="number" min="0" max="1" step=".01" value="${x.complexity}"></div><div class="field"><label>Difficulty 1–5</label><input id="e-diff" type="number" min="1" max="5" step=".5" value="${x.self_difficulty}"></div><div class="field"><label>Volume 0–1</label><input id="e-volume" type="number" min="0" max="1" step=".01" value="${x.volume}"></div><div class="field"><label>Cognitive load 0–1</label><input id="e-load" type="number" min="0" max="1" step=".01" value="${x.cognitive_load}"></div></div>`); $('#editor-save').onclick = saveTopic; }
async function saveTopic() { try { await api('/topics',{method:'POST',body:JSON.stringify({id:$('#e-id').value.trim(),subject_id:$('#e-sub').value,name:$('#e-name').value.trim(),estimated_hours:Number($('#e-hours').value),mastery:Number($('#e-mastery').value),complexity:Number($('#e-complexity').value),self_difficulty:Number($('#e-diff').value),volume:Number($('#e-volume').value),cognitive_load:Number($('#e-load').value)})}); closeEditor(); await load(); toast('Topic saved'); } catch(e) { toast(e.message); } }
window.addTopic=addTopic; window.editTopic=editTopic;

function addExam() { if (!subjects().length) { toast('Add subjects before creating an exam'); setView('curriculum'); return; } modalShell('Add exam', `<div class="form-grid"><div class="field"><label>Exam name</label><input id="e-id" placeholder="Block exam"></div><div class="field"><label>Date</label><input id="e-date" type="date" value="${plusDays(today(),14)}"></div><div class="field"><label>Weight</label><input id="e-weight" type="number" min="0" step=".1" value="1"></div><div class="field"><label>Subjects</label><select id="e-sub" multiple size="5">${multiOptions(subjects())}</select></div></div><div class="field full"><label>Specific topics (optional)</label><select id="e-topics" multiple size="7">${multiOptions(topics())}</select></div>`); $('#editor-save').onclick = saveExam; }
function editExam(x) { const ss=JSON.parse(x.subject_ids_json||'[]'), tt=JSON.parse(x.topic_ids_json||'[]'); modalShell('Edit exam', `<div class="form-grid"><div class="field"><label>Exam name</label><input id="e-id" value="${esc(x.id)}" readonly></div><div class="field"><label>Date</label><input id="e-date" type="date" value="${x.exam_date}"></div><div class="field"><label>Weight</label><input id="e-weight" type="number" min="0" step=".1" value="${x.weight}"></div><div class="field"><label>Subjects</label><select id="e-sub" multiple size="5">${multiOptions(subjects(),ss)}</select></div></div><div class="field full"><label>Specific topics (optional)</label><select id="e-topics" multiple size="7">${multiOptions(topics(),tt)}</select></div>`); $('#editor-save').onclick = saveExam; }
async function saveExam() { try { await api('/exams',{method:'POST',body:JSON.stringify({id:$('#e-id').value.trim(),date:$('#e-date').value,weight:Number($('#e-weight').value),subject_ids:[...$('#e-sub').selectedOptions].map(o=>o.value),topic_ids:[...$('#e-topics').selectedOptions].map(o=>o.value)})}); closeEditor(); await load(); toast('Exam saved'); } catch(e) { toast(e.message); } }
window.addExam=addExam; window.editExam=editExam;

async function deleteSubject(id) { if (!confirm('Delete this subject and its topics?')) return; try { await api(`/subjects/${encodeURIComponent(id)}`,{method:'DELETE'}); await load(); toast('Subject deleted'); } catch(e) { toast(e.message); } }
async function deleteTopic(id) { if (!confirm('Delete this topic?')) return; try { await api(`/topics/${encodeURIComponent(id)}`,{method:'DELETE'}); await load(); toast('Topic deleted'); } catch(e) { toast(e.message); } }
async function deleteExam(id) { if (!confirm('Delete this exam?')) return; try { await api(`/exams/${encodeURIComponent(id)}`,{method:'DELETE'}); await load(); toast('Exam deleted'); } catch(e) { toast(e.message); } }
window.deleteSubject=deleteSubject; window.deleteTopic=deleteTopic; window.deleteExam=deleteExam;

async function saveProfile(e) { e.preventDefault(); try { const rest=$$('.rest-box:checked').map(x=>Number(x.value)); state.profile = await api('/profile',{method:'PUT',body:JSON.stringify({daily_available_minutes:Number($('#p-daily').value),minimum_subject_minutes_week:Number($('#p-floor').value),review_fraction:Number($('#p-review').value),max_session_minutes:Number($('#p-max').value),rest_weekdays:rest,energy_pattern:['high','high','medium','medium']})}); await replanWeek([],true); toast('Settings saved and week regenerated'); } catch(e) { toast(e.message); } }

async function calibratePlanner() { try { const out=await api('/calibrate',{method:'POST'}); toast(out.count ? `Recalibrated ${out.count} topic(s)` : 'Not enough history to recalibrate yet'); await load(); } catch(e) { toast(e.message); } }
window.calibratePlanner=calibratePlanner;

function openSession(id) { const s=sessions().find(x=>Number(x.id)===Number(id)); if (!s || s.completed) return; state.modal=s; $('#modal-title').textContent=topicName(s.topic_id); $('#modal-meta').textContent=s.session_date; $('#modal-planned').textContent=`${s.planned_minutes} min`; $('#modal-type').textContent=s.session_type; $('#modal-subject').textContent=subjectName(topicById(s.topic_id)?.subject_id || ''); $('#actual-minutes').value=s.planned_minutes; $('#score').value=''; const m=$('#session-modal'); m.classList.remove('hidden'); m.setAttribute('aria-hidden','false'); }
window.openSession=openSession;
function closeModal() { const m=$('#session-modal'); m.classList.add('hidden'); m.setAttribute('aria-hidden','true'); state.modal=null; }
async function completeCurrent(replan=false) { const s=state.modal; if(!s) return; const actual=Number($('#actual-minutes').value), score=Number($('#score').value); if(!Number.isFinite(actual)||actual<0||!Number.isFinite(score)||score<0||score>1){toast('Enter actual minutes and a score from 0 to 1');return;} try { await api(`/sessions/${s.id}/complete`,{method:'POST',body:JSON.stringify({actual_minutes:actual,performance_score:score})}); closeModal(); await load(); toast('Session completed — mastery and memory updated'); if(replan) await replanWeek(); } catch(e){toast(e.message);} }

$('#nav').addEventListener('click', e => { const b=e.target.closest('.nav-item'); if(!b) return; setView(b.dataset.view); });
$('#replan').onclick=()=>replanWeek();
$('#seed').onclick=seed;
$('#modal-close').onclick=closeModal;
$('#modal-complete').onclick=()=>completeCurrent(false);
$('#modal-replan').onclick=()=>completeCurrent(true);
$('#session-modal').addEventListener('click',e=>{if(e.target.id==='session-modal')closeModal();});
load();
