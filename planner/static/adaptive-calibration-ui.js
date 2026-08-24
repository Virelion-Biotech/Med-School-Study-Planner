(() => {
  const api = (path, options = {}) => fetch(window.plannerApiUrl(path), {
    headers: {'Content-Type':'application/json', ...(options.headers || {})},
    ...options,
  }).then(async r => { let b={}; try { b=await r.json(); } catch {} if (!r.ok) throw Error(b.detail || `HTTP ${r.status}`); return b; });

  const original = window.calibrate;
  if (window.__adaptiveCalibrationWrapped) return;
  window.calibrate = async function() {
    try {
      const result = await api('/v2/workload/calibrate-all', {method:'POST'});
      window.toast?.(`${result.count} topic(s) recalibrated with adaptive workload data`);
      if (typeof window.load === 'function') await window.load();
    } catch (e) {
      if (original) return original();
      window.toast?.(e.message || 'Could not recalibrate');
    }
  };
  window.__adaptiveCalibrationWrapped = true;
})();
