(() => {
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {
    headers: {'Content-Type':'application/json', ...(options.headers || {})}, ...options,
  }).then(async r => { let b={}; try { b=await r.json(); } catch {} if (!r.ok) throw Error(b.detail || `HTTP ${r.status}`); return b; });
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

  function installStyle() {
    if (document.querySelector('#adaptive-why-style')) return;
    const style = document.createElement('style');
    style.id = 'adaptive-why-style';
    style.textContent = `.adaptive-why-panel{margin-top:14px;padding:12px 14px;border:1px solid #dce8e6;border-radius:12px;background:#f7fbfa}.adaptive-why-head{display:flex;justify-content:space-between;gap:10px;align-items:center}.adaptive-why-head b{font-size:11px}.adaptive-why-head span{font-size:9px;color:#0f766e;font-weight:800}.adaptive-why-reasons{display:grid;gap:5px;margin-top:8px;color:#71858b;font-size:10px;line-height:1.4}@media(max-width:600px){.adaptive-why-head{align-items:flex-start;flex-direction:column}}`;
    document.head.appendChild(style);
  }

  function explainButton() {
    installStyle();
    const actions = document.querySelector('.modal-card .drawer-actions');
    if (!actions || actions.querySelector('[data-why-session]')) return;
    const title = document.querySelector('.modal-card h2');
    if (!title) return;
    const topic = title.textContent?.trim();
    const snap = window.__plannerSnapshot || {};
    const session = (snap.sessions || []).find(s => {
      const t = (snap.topics || []).find(x => x.id === s.topic_id);
      return t?.name === topic && !s.completed;
    });
    if (!session?.topic_id) return;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'btn secondary';
    button.dataset.whySession = '1';
    button.textContent = 'Why today?';
    button.addEventListener('click', async () => {
      button.disabled = true;
      button.textContent = 'Loading…';
      try {
        const data = await api(`/v2/topic/${encodeURIComponent(session.topic_id)}/why`);
        const existing = document.querySelector('[data-why-panel]');
        existing?.remove();
        const panel = document.createElement('div');
        panel.dataset.whyPanel = '1';
        panel.className = 'adaptive-why-panel';
        const reasons = (data.reasons || []).map(r => `<span>• ${esc(r)}</span>`).join('');
        panel.innerHTML = `<div class="adaptive-why-head"><b>Why this topic?</b><span>${(Number(data.per_minute || 0) * 1000).toFixed(2)} utility / 1k min</span></div><div class="adaptive-why-reasons">${reasons || '<span>High expected learning gain per minute.</span>'}</div>`;
        actions.parentElement?.appendChild(panel);
      } catch (e) {
        window.toast?.(e.message || 'Could not load explanation');
      } finally {
        button.disabled = false;
        button.textContent = 'Why today?';
      }
    });
    actions.insertBefore(button, actions.firstChild);
  }

  const originalOpen = window.openSession;
  if (originalOpen && !window.__adaptiveWhyWrapped) {
    window.openSession = function(...args) {
      const result = originalOpen.apply(this, args);
      setTimeout(explainButton, 0);
      return result;
    };
    window.__adaptiveWhyWrapped = true;
  }
  const originalRender = window.render;
  if (originalRender && !window.__adaptiveWhyRenderWrapped) {
    window.render = function(...args) {
      const result = originalRender.apply(this, args);
      setTimeout(explainButton, 0);
      return result;
    };
    window.__adaptiveWhyRenderWrapped = true;
  }
})();
