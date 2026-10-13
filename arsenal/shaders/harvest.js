// arsenal/shaders/harvest.js -- the browser half of the shader school's harvest verb.
//
// WHY IN THE BROWSER. shadertoy.com sits behind Cloudflare: a script outside a browser gets 403 for pages, shader JSON
// and media alike. The signed-in tab Daniel already has open is allowed, so the harvest runs there (injected by the
// Claude-in-Chrome javascript tool, or pasted into the console) and leaves with ONE download: a bundle that
// `py -m arsenal shader ingest <bundle.json>` saves into the private corpus.
//
// POLITENESS IS A RULE, NOT A SETTING. Every request waits PACE_MS after the previous one, and a reply that is not what
// it should be (Cloudflare's "Just a moment" page instead of JSON) stops the run instead of retrying: a human has to
// tick the check in a tab, and hammering it only makes the next check harder. 2026-10-13: 40 results pages at 400 ms
// tripped the check at page 27; the pace is 1500 ms since.
//
//   __st.playlist('MsKnRK')            -> ids of a playlist, in its order (12 per page)
//   __st.results('love', 10)           -> full shaders from N results pages (the page embeds the full JSON)
//   __st.full(ids)                     -> full shaders by id (POST /shadertoy, 6 per request)
//   __st.media(paths)                  -> {site_path: base64} for textures, cubemap faces, volumes
//   __st.download(name, bundle)        -> one JSON file in Downloads (schema arsenal.shadertoy-harvest/v1)
//   __st.stage(bundle)                 -> the same JSON, selected in a textarea for a Ctrl+C (no download prompt)
//   __st.status()                      -> what the current run has done
(function () {
  const PACE_MS = 1500;
  const BATCH = 6;
  const st = { log: [], stopped: null, busy: false };
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  let last = 0;
  async function paced(url, opts) {
    if (st.stopped) throw new Error('stopped: ' + st.stopped);
    const wait = last + PACE_MS - Date.now();
    if (wait > 0) await sleep(wait);
    last = Date.now();
    const r = await fetch(url, opts);
    if (r.status === 403 || r.status === 429 || r.status === 503) {
      st.stopped = `HTTP ${r.status} on ${url.split('?')[0]} -- tick the check in a shadertoy tab, then __st.resume()`;
      throw new Error(st.stopped);
    }
    return r;
  }
  function extractArray(text, key) {
    const m = new RegExp(key + '\\s*=\\s*\\[').exec(text);
    if (!m) return null;
    const i = m.index + m[0].length - 1;
    let depth = 0, inStr = false, esc = false;
    for (let k = i; k < text.length; k++) {
      const c = text[k];
      if (inStr) { if (esc) esc = false; else if (c === '\\') esc = true; else if (c === '"') inStr = false; continue; }
      if (c === '"') inStr = true;
      else if (c === '[') depth++;
      else if (c === ']') { depth--; if (depth === 0) return JSON.parse(text.slice(i, k + 1)); }
    }
    return null;
  }
  async function pageShaders(url) {
    const html = await (await paced(url)).text();
    const arr = extractArray(html, 'gShaders');
    if (!arr) {
      if (/Just a moment|challenge-platform/i.test(html)) st.stopped = 'Cloudflare check on ' + url.split('?')[0];
      return null;
    }
    return arr;
  }
  async function playlist(id, maxPages = 50) {
    const ids = [];
    for (let p = 0; p < maxPages; p++) {
      const arr = await pageShaders(`/playlist/${id}?from=${p * 12}&num=12`);
      if (!arr || !arr.length) break;
      arr.forEach((s) => { const sid = s.info && s.info.id; if (sid && !ids.includes(sid)) ids.push(sid); });
      st.log.push(`playlist ${id} page ${p + 1}: ${arr.length}`);
      if (arr.length < 12) break;
    }
    return ids;
  }
  async function results(sort, pages, fromPage = 0) {
    const out = [];
    for (let p = fromPage; p < fromPage + pages; p++) {
      const arr = await pageShaders(`/results?query=&sort=${sort}&from=${p * 12}&num=12`);
      if (!arr) break;
      arr.forEach((s, i) => { s.__rank = p * 12 + i + 1; out.push(s); });
      st.log.push(`results ${sort} page ${p + 1}: ${arr.length}`);
    }
    return out;
  }
  async function full(ids) {
    const out = [];
    for (let k = 0; k < ids.length; k += BATCH) {
      const batch = ids.slice(k, k + BATCH);
      const body = 's=' + encodeURIComponent(JSON.stringify({ shaders: batch })) + '&nt=1&nl=1&np=1';
      const r = await paced('/shadertoy', { method: 'POST', headers: { 'Content-Type': 'application/x-www-form-urlencoded' }, body });
      const text = await r.text();
      let arr;
      try { arr = JSON.parse(text); } catch (e) { st.stopped = 'non-JSON reply from /shadertoy (Cloudflare?)'; break; }
      arr.forEach((s) => out.push(s));
      st.log.push(`full ${k + batch.length}/${ids.length}`);
    }
    return out;
  }
  async function toB64(blob) {
    const buf = new Uint8Array(await blob.arrayBuffer());
    let s = '';
    for (let i = 0; i < buf.length; i += 0x8000) s += String.fromCharCode.apply(null, buf.subarray(i, i + 0x8000));
    return btoa(s);
  }
  async function media(paths) {
    const out = {};
    for (const p of paths) {
      if (!p || !p.startsWith('/media/a/')) continue;
      const r = await paced(p);
      if (!r.ok) { st.log.push(`media ${r.status} ${p}`); continue; }
      out[p] = await toB64(await r.blob());
      st.log.push(`media ${Object.keys(out).length}/${paths.length}`);
    }
    return out;
  }
  function download(name, bundle) {
    const text = JSON.stringify(Object.assign({ schema: 'arsenal.shadertoy-harvest/v1', harvested_at: new Date().toISOString() }, bundle));
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([text], { type: 'application/json' }));
    a.download = name;
    document.body.appendChild(a); a.click(); a.remove();
    return text.length;
  }
  // stage(bundle): the download-free exit. Brave asks where to save every download (and holds a second one from the
  // same page behind a permission prompt), so a harvest that runs unattended leaves through the clipboard instead:
  // stage() puts the bundle JSON into a selected textarea, the browser tool presses Ctrl+C (a real key event, which
  // the copy command requires), and `py -m arsenal shader ingest --clipboard` reads it. Returns the byte count.
  function stage(bundle) {
    const text = JSON.stringify(Object.assign({ schema: 'arsenal.shadertoy-harvest/v1', harvested_at: new Date().toISOString() }, bundle));
    let ta = document.getElementById('__st_ta');
    if (!ta) {
      ta = document.createElement('textarea'); ta.id = '__st_ta';
      ta.style.cssText = 'position:fixed;left:0;top:0;width:120px;height:40px;z-index:99999;opacity:0.2;';
      document.body.appendChild(ta);
    }
    ta.value = text; ta.focus(); ta.select();
    return text.length;
  }
  function unstage() { const ta = document.getElementById('__st_ta'); if (ta) ta.remove(); return 'unstaged'; }
  // run(fn): start a long job without holding the caller; poll __st.status()
  function run(label, fn) {
    if (st.busy) return 'busy: ' + st.busy;
    st.busy = label; st.result = null; st.error = null;
    fn().then((r) => { st.result = r; }).catch((e) => { st.error = String(e); }).finally(() => { st.busy = false; });
    return 'started ' + label;
  }
  function status() {
    return { busy: st.busy, stopped: st.stopped, error: st.error, log: st.log.slice(-6),
      result: st.result == null ? null : (Array.isArray(st.result) ? `${st.result.length} items` : typeof st.result) };
  }
  function resume() { st.stopped = null; return 'resumed'; }
  window.__st = { playlist, results, full, media, download, stage, unstage, run, status, resume, state: st, PACE_MS };
  return 'harvest helper ready (pace ' + PACE_MS + ' ms)';
})();
