// arsenal/web/lib/workbench/common.js -- what every Workbench panel shares: the route contract, a tiny element maker,
// fetches that answer with a reason instead of throwing, the honest "not available yet" state, the cost classes, and
// the plain-text reader for study notes.
//
// WHY ONE FILE FOR THESE. The Workbench is the unified UI's first home (build-spec-reconciled.md ruling 4): the Shader
// Lab mounts it today, and the bench, the Studio and First Light are meant to mount the same panels later. A panel that
// hard-codes a URL, or that goes blank when a route is missing, cannot move to another page. So the routes are one
// table a host can override, and every fetch comes back as {ok, data} or {ok: false, reason}, which a panel turns into
// words ("not available yet: /shelf/index.json answered HTTP 404") rather than an empty box.
//
// Like arsenal/web/lib/params-ui.js, every function that builds DOM takes the document as an argument and uses only
// createElement, appendChild, replaceChildren, attributes, properties and listeners, so tests/workbench_lab.test.mjs
// drives the panels with a small fake document. Nothing here sets innerHTML: study notes and receipts are other
// people's words and our own data, shown as text.
//
// Apache-2.0, written for the house (Vandor, 2026-10-13). No framework, no CDN, no build step.

export const WORKBENCH_API = 'arsenal.workbench/v1';

const seg = (s) => encodeURIComponent(String(s));
const segs = (p) => String(p).split('/').filter(Boolean).map(seg).join('/');

// The route contract of `py -m arsenal shader serve` (127.0.0.1:8797). A host page on another server passes its own
// table to mountWorkbench({routes}); every panel reads its URLs from here and nowhere else.
export const ROUTES = Object.freeze({
  atlas: '/atlas.json',                       // arsenal/shaders/atlas.json: families, categories, parts, groups, tags
  glslIndex: '/glsl/index.json',              // arsenal/web/glsl/index.json: the built modules
  modlib: '/glsl/modlib.js',                  // the composer's browser twin
  runtime: '/lab/toy-runtime.js',             // loaded only when someone presses Run
  paramsUi: '/webl/params-ui.js',             // generated controls
  params: '/webl/params.js',                  // the param schema (paramsFromModule)
  shelf: '/shelf/index.json',                 // the 42 loved shaders, joined (the Shelf slice)
  corpusMedia: '/corpus/media/',
  glslFile: (path) => `/glsl/${segs(path)}`,
  render: (id, file) => `/renders/${seg(id)}/${segs(file)}`,
  study: (id) => `/study/${seg(id)}.md`,
  card: (name, file) => `/cards/${seg(name)}/${segs(file)}`,
  cardSource: (name) => `/glsl/cards/${seg(name)}.card`,
  corpusShader: (id) => `/corpus/${seg(id)}/shader.json`,
});

// ------------------------------------------------------------------------------------------------ elements --
/** One element: h(doc, 'button', 'wb-run', 'Run'). props are set as properties, except aria-*, role and data-*. */
export function h(doc, tag, cls, text, props) {
  const e = doc.createElement(tag);
  if (cls) e.className = cls;
  if (text !== undefined && text !== null) e.textContent = String(text);
  if (props) {
    for (const [k, v] of Object.entries(props)) {
      if (v === undefined || v === null) continue;
      if (k.startsWith('data-')) e.dataset[k.slice(5).replace(/-([a-z])/g, (_, c) => c.toUpperCase())] = String(v);
      else if (k === 'role' || k.startsWith('aria-')) e.setAttribute(k, String(v));
      else e[k] = v;
    }
  }
  return e;
}

/** Append children, skipping null and false, so a panel can write conditionals inline. */
export function put(parent, ...kids) {
  for (const k of kids.flat()) if (k) parent.appendChild(k);
  return parent;
}

export function setClass(el, cls, on) {
  const have = String(el.className || '').split(/\s+/).filter(Boolean);
  const next = on ? (have.includes(cls) ? have : [...have, cls]) : have.filter((c) => c !== cls);
  el.className = next.join(' ');
}

/** A text pair for definition lists: <dt>label</dt><dd>value</dd>. value may be an element. */
export function pair(doc, dl, label, value) {
  if (value === undefined || value === null || value === '' || (Array.isArray(value) && !value.length)) return;
  dl.appendChild(h(doc, 'dt', null, label));
  const dd = h(doc, 'dd');
  if (typeof value === 'object' && !Array.isArray(value) && value.tagName) dd.appendChild(value);
  else dd.textContent = Array.isArray(value) ? value.join(', ') : String(value);
  dl.appendChild(dd);
}

// ------------------------------------------------------------------------------------------------ fetching --
/** {ok: true, status, data} or {ok: false, status, reason}. Never throws: a missing route is a state, not a crash. */
export async function fetchJson(fetchImpl, url) {
  let res;
  try { res = await fetchImpl(url); } catch (e) {
    return { ok: false, status: 0, reason: `could not be fetched (${(e && e.message) || e})` };
  }
  if (!res || !res.ok) return { ok: false, status: res ? res.status : 0, reason: `HTTP ${res ? res.status : '?'}` };
  try { return { ok: true, status: res.status, data: await res.json() }; } catch (e) {
    return { ok: false, status: res.status, reason: `the answer is not JSON (${(e && e.message) || e})` };
  }
}

/** The same for text (study notes, module and card sources). */
export async function fetchText(fetchImpl, url) {
  let res;
  try { res = await fetchImpl(url); } catch (e) {
    return { ok: false, status: 0, reason: `could not be fetched (${(e && e.message) || e})` };
  }
  if (!res || !res.ok) return { ok: false, status: res ? res.status : 0, reason: `HTTP ${res ? res.status : '?'}` };
  return { ok: true, status: res.status, text: await res.text() };
}

/** The honest empty state: what is missing, which route was asked, what it answered, and who fills it. */
export function unavailable(doc, { title = 'This panel', route = '', why = '', fills = '' } = {}) {
  const box = h(doc, 'div', 'wb-empty', null, { role: 'status' });
  box.appendChild(h(doc, 'p', 'wb-empty-title', `${title}: not available yet`));
  if (route) box.appendChild(h(doc, 'p', 'wb-empty-why', why ? `${route} answered ${why}.` : `${route} has not answered.`));
  if (fills) box.appendChild(h(doc, 'p', 'wb-empty-fills', fills));
  return box;
}

/** A quiet hint for a panel waiting on a choice ("Pick a module..."). */
export function hint(doc, text) {
  return h(doc, 'p', 'wb-hint', text);
}

// ----------------------------------------------------------------------------------- images with fallbacks --
/** An <img> that walks a list of candidate URLs on error, and calls onNone() when none loads. Lazy by default: a
 *  picture loads when it scrolls into view, so a page of 42 cards does not fetch 42 stills at once. */
export function imgFrom(doc, urls, { alt = '', cls = '', lazy = true, onNone = null } = {}) {
  const list = (urls || []).filter(Boolean);
  const img = h(doc, 'img', cls, null, { alt, decoding: 'async' });
  if (lazy) img.loading = 'lazy';
  let i = 0;
  img.dataset.candidates = String(list.length);
  img.addEventListener('error', () => {
    i += 1;
    if (i < list.length) img.src = list[i];
    else if (typeof onNone === 'function') onNone(img);
  });
  if (list.length) img.src = list[0];
  return img;
}

// ------------------------------------------------------------------------------------------ the cost classes --
// From the atlas (primitive-atlas-draft.md 0.2). The words are what the Run button says before anything runs.
export const COSTS = Object.freeze({
  C0: Object.freeze({ rank: 0, words: 'straight-line arithmetic, no loop' }),
  C1: Object.freeze({ rank: 1, words: 'a small fixed loop' }),
  C2: Object.freeze({ rank: 2, words: 'a march: one ray loop' }),
  C3: Object.freeze({ rank: 3, words: 'nested loops: a march inside a march' }),
  C4: Object.freeze({ rank: 4, words: 'stateful: it keeps render targets between frames' }),
});

/** 'C2', 'C2+T1', {class: 'C2'} -> 'C2'; anything else -> null. */
export function normCost(c) {
  const s = c && typeof c === 'object' ? c.class : c;
  const m = /^\s*(C[0-4])\b/i.exec(String(s ?? ''));
  return m ? m[1].toUpperCase() : null;
}
export const costRank = (c) => { const n = normCost(c); return n ? COSTS[n].rank : -1; };
/** The heavier of a list of classes (nulls ignored); null when none is known. */
export function heaviest(list) {
  let best = null;
  for (const c of list || []) if (costRank(c) > costRank(best)) best = normCost(c);
  return best;
}
/** The stand-ins a render used ({src, kind, reason, style}), one line each for a hover text:
 *  "texture: load failed: procedural stand-in (noise) · /media/a/f735bee5b6...a5756040c2.png". */
export function standInLines(list) {
  return (list || []).map((s) => {
    const src = String((s && s.src) || '');
    const short = src.length > 40 ? `${src.slice(0, 22)}...${src.slice(-14)}` : src;
    return `${(s && s.kind) || 'input'}: ${(s && s.reason) || 'stood in'}${s && s.style ? ` (${s.style})` : ''}${short ? ` · ${short}` : ''}`;
  });
}

/** 'P0' < 'P1' < 'P2': the most urgent of a list. */
export function mostUrgent(list) {
  const known = (list || []).filter((s) => /^P[0-2]$/.test(String(s))).sort();
  return known[0] || null;
}

// ----------------------------------------------------------------------------------------- study notes --
// A study note is Markdown written by the house. The Shelf shows it as plain text: headings, paragraphs, lists and
// tables become text blocks; emphasis marks and link brackets are dropped; nothing is ever parsed as HTML.
const clean = (s) => String(s)
  .replace(/\*\*([^*]+)\*\*/g, '$1').replace(/__([^_]+)__/g, '$1')
  .replace(/`([^`]*)`/g, '$1')
  .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, '$1 ($2)')
  .replace(/\s+/g, ' ').trim();
const cells = (line) => line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => clean(c));

/** Markdown -> [{kind: 'heading', level, text} | {kind: 'para', text} | {kind: 'list', items} |
 *  {kind: 'table', rows} | {kind: 'code', text}]. */
export function studyBlocks(md) {
  const lines = String(md || '').replace(/\r\n?/g, '\n').split('\n');
  const out = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i++; continue; }
    if (/^\s*```/.test(line)) {
      const body = [];
      i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])) body.push(lines[i++]);
      i++;
      out.push({ kind: 'code', text: body.join('\n') });
      continue;
    }
    const hm = /^(#{1,6})\s+(.*)$/.exec(line);
    if (hm) { out.push({ kind: 'heading', level: hm[1].length, text: clean(hm[2]) }); i++; continue; }
    if (/^\s*\|/.test(line)) {
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) {
        if (!/^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i])) rows.push(cells(lines[i]));
        i++;
      }
      out.push({ kind: 'table', rows });
      continue;
    }
    if (/^\s*(?:[-*+]|\d+[.)])\s+/.test(line)) {
      const items = [];
      while (i < lines.length && lines[i].trim()) {
        const lm = /^\s*(?:[-*+]|\d+[.)])\s+(.*)$/.exec(lines[i]);
        if (lm) items.push(lm[1]);
        else if (items.length) items[items.length - 1] += ' ' + lines[i].trim();
        else break;
        i++;
      }
      out.push({ kind: 'list', items: items.map(clean) });
      continue;
    }
    const para = [];
    while (i < lines.length && lines[i].trim() && !/^(#{1,6})\s/.test(lines[i]) && !/^\s*\|/.test(lines[i])
      && !/^\s*```/.test(lines[i]) && !/^\s*(?:[-*+]|\d+[.)])\s+/.test(lines[i])) para.push(lines[i++]);
    out.push({ kind: 'para', text: clean(para.join(' ')) });
  }
  return out;
}

/** The blocks as elements, text only. */
export function renderStudy(doc, blocks) {
  const box = h(doc, 'div', 'wb-study-text');
  for (const b of blocks) {
    if (b.kind === 'heading') box.appendChild(h(doc, b.level <= 1 ? 'h3' : 'h4', 'wb-study-h', b.text));
    else if (b.kind === 'para') box.appendChild(h(doc, 'p', null, b.text));
    else if (b.kind === 'code') box.appendChild(h(doc, 'pre', 'wb-study-code', b.text));
    else if (b.kind === 'list') {
      const ul = h(doc, 'ul');
      for (const it of b.items) ul.appendChild(h(doc, 'li', null, it));
      box.appendChild(ul);
    } else if (b.kind === 'table') {
      const wrap = h(doc, 'div', 'wb-study-table');
      const table = h(doc, 'table');
      b.rows.forEach((row, r) => {
        const tr = h(doc, 'tr');
        for (const c of row) tr.appendChild(h(doc, r === 0 ? 'th' : 'td', null, c));
        table.appendChild(tr);
      });
      wrap.appendChild(table);
      box.appendChild(wrap);
    }
  }
  return box;
}

/** A panel's frame: <section class="wb-panel {cls}"> with a quiet uppercase heading and a body. */
export function panel(doc, root, cls, title, aside) {
  setClass(root, 'wb-panel', true);
  setClass(root, cls, true);
  const head = h(doc, 'header', 'wb-panel-head');
  head.appendChild(h(doc, 'h2', 'wb-panel-title', title));
  const side = h(doc, 'span', 'wb-panel-aside', aside || '');
  head.appendChild(side);
  const body = h(doc, 'div', 'wb-panel-body');
  root.replaceChildren(head, body);
  return { head, side, body };
}
