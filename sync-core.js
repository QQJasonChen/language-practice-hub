/* Echo Dutch — auto cloud sync engine (Google Apps Script backend).
 *
 * Backend: a user-deployed Apps Script web app that stores one JSON blob
 * in the user's own Google Drive. GET returns {data, updatedAt}; POST
 * (text/plain to avoid CORS preflight) replaces it.
 *
 * Strategy:
 *  - snapshot of last synced state kept in localStorage (LPH_SYNC_SNAP)
 *  - on sync: pull remote, detect local/remote changes since last sync
 *    - only remote changed -> apply remote
 *    - only local changed  -> push local
 *    - both changed        -> per-key smart merge, then push
 *  - dict-of-entries stores merge entry-wise (newer lastDate/lastSeen/due
 *    or higher tries/reps wins); numeric count maps take max; scalars
 *    prefer local.
 */
(function () {
  const URL_KEY = 'lph_sync_url';
  const SNAP_KEY = 'lph_sync_snap';      // JSON of state at last successful sync
  const META_KEY = 'lph_sync_meta';      // {lastSyncAt, lastRemoteUpdatedAt}
  const EXCLUDE = new Set([URL_KEY, SNAP_KEY, META_KEY, 'lph_openai_key']);

  function isOurKey(k) {
    return (k.startsWith('lph_') || k.startsWith('hub_') || k.startsWith('examapp:')) && !EXCLUDE.has(k);
  }
  function collectLocal() {
    const data = {};
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (isOurKey(k)) data[k] = localStorage.getItem(k);
    }
    return data;
  }
  const getMeta = () => { try { return JSON.parse(localStorage.getItem(META_KEY) || '{}'); } catch (e) { return {}; } };
  const getSnap = () => { try { return JSON.parse(localStorage.getItem(SNAP_KEY) || 'null'); } catch (e) { return null; } };

  function changedKeys(a, b) { // keys whose value differs between two {k:str} maps
    const keys = new Set([...Object.keys(a || {}), ...Object.keys(b || {})]);
    return [...keys].filter(k => (a || {})[k] !== (b || {})[k]);
  }

  // ── entry-level merge for one key ──
  const DATE_FIELDS = ['lastDate', 'lastSeen', 'due'];
  const COUNT_FIELDS = ['tries', 'reps', 'attempts'];
  function entryScore(v) {
    if (!v || typeof v !== 'object') return [0, 0];
    let d = '';
    for (const f of DATE_FIELDS) if (typeof v[f] === 'string' && v[f] > d) d = v[f];
    let c = 0;
    for (const f of COUNT_FIELDS) {
      if (typeof v[f] === 'number') c += v[f];
      else if (Array.isArray(v[f])) c += v[f].length;
    }
    return [d, c];
  }
  function pickEntry(a, b) {
    const [da, ca] = entryScore(a), [db, cb] = entryScore(b);
    if (da !== db) return da > db ? a : b;
    if (ca !== cb) return ca > cb ? a : b;
    return a; // tie -> local
  }
  function mergeValue(localStr, remoteStr) {
    if (localStr === undefined) return remoteStr;
    if (remoteStr === undefined) return localStr;
    let L, R;
    try { L = JSON.parse(localStr); R = JSON.parse(remoteStr); } catch (e) { return localStr; }
    const plainObj = v => v && typeof v === 'object' && !Array.isArray(v);
    if (!plainObj(L) || !plainObj(R)) return localStr;
    const out = {};
    const keys = new Set([...Object.keys(L), ...Object.keys(R)]);
    for (const k of keys) {
      const a = L[k], b = R[k];
      if (a === undefined) out[k] = b;
      else if (b === undefined) out[k] = a;
      else if (typeof a === 'number' && typeof b === 'number') out[k] = Math.max(a, b); // count maps (dictee misses)
      else if (a && b && typeof a === 'object' && typeof b === 'object' && !Array.isArray(a)) out[k] = pickEntry(a, b);
      else out[k] = a;
    }
    return JSON.stringify(out);
  }

  function applyData(data) {
    for (const [k, v] of Object.entries(data)) {
      if (isOurKey(k) && v != null) localStorage.setItem(k, v);
    }
  }
  function saveSnap(data, remoteUpdatedAt) {
    localStorage.setItem(SNAP_KEY, JSON.stringify(data));
    localStorage.setItem(META_KEY, JSON.stringify({
      lastSyncAt: Date.now(), lastRemoteUpdatedAt: remoteUpdatedAt || 0 }));
  }

  async function pull(url) {
    const r = await fetch(url, { method: 'GET', redirect: 'follow' });
    if (!r.ok) throw new Error('GET ' + r.status);
    const j = await r.json();
    return { data: (j && j.data) || {}, updatedAt: (j && j.updatedAt) || 0 };
  }
  async function push(url, data) {
    const updatedAt = Date.now();
    const r = await fetch(url, {
      method: 'POST', redirect: 'follow',
      headers: { 'Content-Type': 'text/plain;charset=utf-8' }, // text/plain = no CORS preflight
      body: JSON.stringify({ data, updatedAt }),
    });
    if (!r.ok) throw new Error('POST ' + r.status);
    return updatedAt;
  }

  /** Run one full sync. Returns {status, detail} — status: off|pulled|pushed|merged|uptodate|error */
  async function syncNow() {
    const url = localStorage.getItem(URL_KEY);
    if (!url) return { status: 'off' };
    try {
      const remote = await pull(url);
      const local = collectLocal();
      const snap = getSnap();
      const meta = getMeta();

      if (snap === null) {
        // first sync on this device: merge everything both ways
        const merged = { ...remote.data };
        for (const k of new Set([...Object.keys(local), ...Object.keys(remote.data)]))
          merged[k] = mergeValue(local[k], remote.data[k]);
        applyData(merged);
        const ts = await push(url, merged);
        saveSnap(merged, ts);
        return { status: 'merged', detail: '首次同步，已雙向合併' };
      }

      const localDirty = changedKeys(local, snap);
      const remoteDirty = remote.updatedAt !== meta.lastRemoteUpdatedAt;

      if (!localDirty.length && !remoteDirty) return { status: 'uptodate' };
      if (!localDirty.length && remoteDirty) {
        applyData(remote.data);
        saveSnap(collectLocal(), remote.updatedAt);
        return { status: 'pulled', detail: '已套用其他裝置的進度' };
      }
      if (localDirty.length && !remoteDirty) {
        const ts = await push(url, local);
        saveSnap(local, ts);
        return { status: 'pushed', detail: `已上傳 ${localDirty.length} 項變更` };
      }
      // both changed -> per-key merge
      const merged = {};
      for (const k of new Set([...Object.keys(local), ...Object.keys(remote.data), ...Object.keys(snap)])) {
        const l = local[k], r = remote.data[k], s = snap[k];
        if (l === s) merged[k] = r !== undefined ? r : l;        // only remote changed this key
        else if (r === s || r === undefined) merged[k] = l;       // only local changed this key
        else merged[k] = mergeValue(l, r);                        // both changed -> smart merge
      }
      applyData(merged);
      const ts = await push(url, merged);
      saveSnap(collectLocal(), ts);
      return { status: 'merged', detail: '兩邊都有新進度，已合併' };
    } catch (e) {
      return { status: 'error', detail: String(e && e.message || e) };
    }
  }

  window.LphSync = {
    syncNow,
    isConfigured: () => !!localStorage.getItem(URL_KEY),
    setUrl: u => u ? localStorage.setItem(URL_KEY, u.trim()) : localStorage.removeItem(URL_KEY),
    getUrl: () => localStorage.getItem(URL_KEY) || '',
    lastSyncAt: () => getMeta().lastSyncAt || 0,
    // exposed for tests
    _mergeValue: mergeValue, _pickEntry: pickEntry,
  };
})();
