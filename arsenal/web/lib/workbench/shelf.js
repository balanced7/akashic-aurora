// arsenal/web/lib/workbench/shelf.js -- the SHELF: Daniel's 42 loved shaders as cards, each with its pre-rendered
// filmstrip, its licence, its technique tags linking into the Library, what it teaches in the atlas, and its study note.
//
// WHY PICTURES AND NOT LIVE WINDOWS. Ruling 5 (build-spec-reconciled.md): safe by default for Daniel's GPU. Every
// picture on a card was rendered on SwiftShader (the CPU) by `py -m arsenal shader filmstrip`, under the house lock;
// the card shows those PNGs and nothing else. Hovering a card flips through its frames like a flipbook (one card at a
// time, image swaps only, no WebGL). Running a shader live is the Stage's job, after an explicit click.
//
// WHY THE LICENCE IS ON EVERY CARD. Most of the corpus is CC BY-NC-SA and one carries an all-rights-reserved header;
// the house rebuilds techniques from the maths and never copies code (architecture draft section 9). The badge keeps
// that in view. A study-only shader shows its study note and no images at all.
//
//   const shelf = mountShelf(doc, el, { routes, fetch, onStage(entry), onTag(categoryId), onGroup(name) });
//   shelf.setEntries(normalizeShelf(json, atlas, routes).entries);
//   shelf.setEntries(shelfFromAtlas(atlas, routes).entries, { route, why });   // the index is not served yet
//
// The Shelf index (/shelf/index.json) is written by the Shelf slice tonight; normalizeShelf accepts the field names
// the architecture draft lists (title or name, licence or license, study_only, tags, filmstrip frames and sheet) and
// fills what is missing from the atlas, so the cards degrade field by field rather than all at once.
//
// Apache-2.0, written for the house (Vandor, 2026-10-13). Raw DOM, takes the document as an argument.
import {
  COSTS, fetchText, h, hint, imgFrom, normCost, panel, put, renderStudy, setClass, standInLines, studyBlocks, unavailable,
} from './common.js';

// --------------------------------------------------------------------------------------------- licences --
/** 'permissive' (MIT, CC0, Apache, BSD...), 'restricted' (non-commercial, all rights reserved) or 'unknown'. */
export function licenceClass(text) {
  const s = String(text ?? '').toLowerCase();
  if (!s.trim()) return 'unknown';
  if (/\bnc\b|by-nc|non-?commercial|all rights reserved|proprietary|no licen[cs]e/.test(s)) return 'restricted';
  if (/\bcc0\b|\bmit\b|apache|\bbsd\b|public domain|unlicense|\bzlib\b|\bisc\b/.test(s)) return 'permissive';
  return 'unknown';
}
const LICENCE_WORDS = {
  permissive: 'A permissive licence. The house still rebuilds from the maths and the study note; it never copies the code.',
  restricted: 'Non-commercial or restricted. Studied here, on this machine only; never copied into the house.',
  unknown: 'Licence not recorded in this index; see the study note.',
};

// ------------------------------------------------------------------------------------------- the atlas --
/** The atlas categories a dissector tag maps to: the exact table first, then the tag's family (raymarch.* -> E3). */
export function tagCategories(atlas, tag) {
  const t = (atlas && atlas.tags) || {};
  const exact = (t.exact || {})[tag];
  if (Array.isArray(exact) && exact.length) return exact.slice();
  const fam = (t.groups || {})[String(tag).split('.')[0]];
  return Array.isArray(fam) ? fam.slice() : [];
}

/** What a loved shader teaches in the atlas: the groups it exemplifies, the parts it shows, their categories. */
export function teachesFor(atlas, id) {
  const groups = ((atlas && atlas.groups) || [])
    .filter((g) => (g.exemplars || []).includes(id) || (g.study_only || []).includes(id))
    .map((g) => ({ name: g.name, line: g.line || '', cost: normCost(g.cost), status: g.status || null }));
  const parts = ((atlas && atlas.parts) || []).filter((p) => (p.exemplars || []).includes(id))
    .map((p) => ({ id: p.id, signature: p.signature, category: p.category, module: p.module, status: p.status }));
  const categories = [...new Set(parts.map((p) => p.category))];
  return { groups, parts, categories };
}

// ------------------------------------------------------------------------------------------ the entries --
// The contact sheet `py -m arsenal shader filmstrip` draws (render.py contact_sheet): frames in a grid of FILM.cols
// columns under a one-line header, FILM.pad pixels around every cell. The server serves the sheet (one picture) but not
// the frame folder beside it, so the flipbook steps a window across the sheet instead of loading frames one by one.
export const FILM = Object.freeze({ cols: 4, pad: 6, head: 26, cell: Object.freeze([320, 180]) });

/** Where frame i of an n-frame contact sheet sits: {x, y} of its top-left, {cw, ch} its size, {w, h} the sheet's. */
export function sheetFrame(i, n = 8, film = FILM) {
  const cols = Math.max(1, Math.min(film.cols, n || 1));
  const rows = Math.max(1, Math.ceil((n || 1) / cols));
  const [cw, ch] = film.cell;
  return { x: film.pad + (i % cols) * (cw + film.pad), y: film.head + film.pad + Math.floor(i / cols) * (ch + film.pad),
    cw, ch, w: film.pad + cols * (cw + film.pad), h: film.head + film.pad + rows * (ch + film.pad) };
}

// A picture the Shelf index names: a /renders/<id>/<file>.png URL as written, or a bare file name in that folder. Only
// one level is served (serve.py), so anything with a further folder in it is not a picture the page can have.
function renderUrl(routes, id, p) {
  if (!p) return null;
  const s = String(typeof p === 'object' ? p.url || p.file || p.path || '' : p).replace(/\\/g, '/');
  if (!s) return null;
  const prefix = `/renders/${id}/`;
  if (s.startsWith(prefix)) return /\//.test(s.slice(prefix.length)) ? null : s;
  const name = s.split('/').pop();
  return /^[A-Za-z0-9][A-Za-z0-9._-]*\.png$/.test(name) && (s === name || s.includes(prefix)) ? routes.render(id, name) : null;
}

function imagesFor(e, id, routes) {
  const r = e.renders && typeof e.renders === 'object' ? e.renders : {};
  const stills = (Array.isArray(r.stills) ? r.stills : Array.isArray(e.stills) ? e.stills : [])
    .map((f) => ({ t: Number.isFinite(Number(f && f.t)) ? Number(f.t) : null, url: renderUrl(routes, id, f),
      luma: Number.isFinite(Number(f && f.mean_luma)) ? Number(f.mean_luma) : null, flat: !!(f && f.flat) }))
    .filter((f) => f.url)
    .sort((a, b) => (a.t ?? 0) - (b.t ?? 0));
  // The poster is the still that shows the most: a flat or near-black frame (a fade-in at t = 1) goes last. The
  // receipts measure each frame's mean luma, so this is a reading, not a guess; without readings the order stays.
  const shows = (f) => (f.flat ? -1e9 : 0) + (f.luma ?? 0);
  const byShow = stills.some((f) => f.flat || f.luma !== null) ? stills.slice().sort((a, b) => shows(b) - shows(a)) : stills;
  const film = r.filmstrip && typeof r.filmstrip === 'object' ? r.filmstrip : null;
  const sheet = film ? renderUrl(routes, id, film.url || film.path || 'filmstrip.png') : null;
  const n = film ? Math.max(0, Math.floor(Number(film.frames) || 0)) : 0;
  const flip = sheet && n > 1 ? { sheet, frames: n, to: Number(film.to) || null, fps: Number(film.fps) || null } : null;
  const poster = byShow.map((f) => f.url);
  // What `py -m arsenal shader render` writes by default, as a last resort when the index names no still.
  for (const f of ['t1.00.png', 't4.00.png']) poster.push(routes.render(id, f));
  return { poster: [...new Set(poster)], frames: stills.map((f) => ({ t: f.t, url: f.url })), sheet, flip };
}

// Stand-in inputs: what a render substituted for a medium the corpus lacks (a texture never saved, silent audio). The
// Shelf index carries the receipts' `substituted` lists (shelf.py: one list per receipt, {stills: [...], filmstrip:
// [...]}; a bare list is read too); the same input named twice is listed once.
function standInsOf(r) {
  const lists = (x) => (Array.isArray(x) ? [x] : x && typeof x === 'object' ? Object.values(x).filter(Array.isArray) : []);
  const raw = [...lists(r.substituted), ...lists(r.stand_ins), ...lists(r.standins),
    ...(Array.isArray(r.stills) ? r.stills.map((s) => s && s.substituted) : []),
    r.filmstrip && typeof r.filmstrip === 'object' ? r.filmstrip.substituted : null].filter(Array.isArray).flat();
  const seen = new Set(), out = [];
  for (const s of raw) {
    const o = s && typeof s === 'object' ? { src: String(s.src || s.path || ''), kind: String(s.kind || 'input'),
      reason: String(s.reason || ''), style: s.style ? String(s.style) : null } : { src: String(s || ''), kind: 'input', reason: '', style: null };
    const key = `${o.kind}|${o.src}|${o.reason}`;
    if (!seen.has(key)) { seen.add(key); out.push(o); }
  }
  return out;
}

/** "2 textures, audio silent": a short count of stand-ins by kind, or '' when there are none. */
export function standInSummary(list) {
  const by = new Map();
  for (const s of list || []) by.set(s.kind, (by.get(s.kind) || 0) + 1);
  return [...by].map(([k, n]) => (k === 'audio' ? 'audio silent' : `${n} ${k}${n === 1 ? '' : k.endsWith('s') ? '' : 's'}`)).join(', ');
}

// The SwiftShader render's warm frame time (the receipt's timings.warm_ms), and the size it was drawn at, if the index
// carries them: a second cost signal the Stage shows beside the class.
function swiftOf(r) {
  const t = r.timings && typeof r.timings === 'object' ? r.timings : {};
  const warm = [r.warm_ms, r.warmMs, t.warm_ms, t.warmMs].map(Number).find((x) => Number.isFinite(x) && x >= 0);
  if (warm === undefined) return null;
  const req = r.request && typeof r.request === 'object' ? r.request : {};
  const size = Array.isArray(r.size) && r.size.length === 2 ? r.size.map(Number)
    : Number(r.w) > 0 && Number(r.h) > 0 ? [Number(r.w), Number(r.h)]
      : Number(req.w) > 0 && Number(req.h) > 0 ? [Number(req.w), Number(req.h)] : null;
  return { warmMs: warm, size };
}

const idOf = (c) => (c && typeof c === 'object' ? c.id : c);
const categoryNamesOf = (atlas) => Object.fromEntries(((atlas && atlas.categories) || []).map((c) => [c.id, c.name]));
function licenceText(lic) {
  if (lic && typeof lic === 'object') {
    const name = String(lic.name || '');
    return lic.corrected ? `${name} (corrected from ${lic.meta || 'the meta'})` : name;
  }
  return String(lic ?? '');
}

/** True when ANY source says a shader is study only: the Shelf index (either spelling), the atlas's loved row, or a
 *  group's study_only list. An OR, never a precedence: a stale `false` in one place cannot beat a `true` in another
 *  (the card would offer "Put on stage", and Run would fetch the source the licence keeps to the study note). */
export function isStudyOnly(e, atlas, lovedRow) {
  if ((e && (e.study_only || e.studyOnly)) || (lovedRow && lovedRow.study_only)) return true;
  const id = e && e.id;
  return ((atlas && atlas.groups) || []).some((g) => Array.isArray(g.study_only) && g.study_only.includes(id));
}

function entryFrom(e, atlas, routes, loved, names = categoryNamesOf(atlas)) {
  const id = String(e.id || '');
  const l = loved.get(id) || {};
  const studyOnly = isStudyOnly({ ...e, id }, atlas, l);
  // Categories the Shelf placed each tag on (dissect.atlas_map), else the atlas's own tag table.
  const placed = new Map();
  for (const c of Array.isArray(e.categories) ? e.categories : []) {
    if (c && typeof c === 'object' && Array.isArray(c.tags)) for (const t of c.tags) placed.set(t, [...(placed.get(t) || []), c.id]);
  }
  const tags = (Array.isArray(e.tags) ? e.tags : []).map((t) => {
    const tag = typeof t === 'string' ? t : String((t && (t.tag || t.name || t.id)) || '');
    const given = t && typeof t === 'object' && Array.isArray(t.categories) ? t.categories : null;
    return { tag, categories: given || placed.get(tag) || tagCategories(atlas, tag) };
  }).filter((t) => t.tag);
  const fromAtlas = teachesFor(atlas, id);
  const groups = Array.isArray(e.groups) ? e.groups.map((g) => ({ name: g.name, line: g.line || '', cost: normCost(g.cost),
    status: g.status || null })) : fromAtlas.groups;
  const parts = Array.isArray(e.parts) ? e.parts.map((p) => ({ id: p.id, signature: p.signature || (p.functions || []).join(', '),
    category: p.category, module: p.module, status: p.status, cost: p.cost })) : fromAtlas.parts;
  const licence = licenceText(e.licence ?? e.license);
  const passes = Array.isArray(e.passes) ? e.passes : null;
  const stateful = passes && passes.some((t) => /^(buffer|cubemap)$/i.test(String(t))) ? 'C4' : null;
  const study = e.study && typeof e.study === 'object' ? e.study : {};
  const renders = e.renders && typeof e.renders === 'object' ? e.renders : {};
  return {
    id, title: String(e.title || e.name || e.short || l.short || id).trim(), short: e.short || l.short || null,
    author: String(e.author || e.username || ''), licence, licenceClass: licenceClass(licence), studyOnly,
    studyOnlyReason: e.study_only_reason || null,
    tags, categories: Array.isArray(e.categories) && e.categories.length ? e.categories.map(idOf)
      : [...new Set(tags.flatMap((t) => t.categories))],
    teaches: { groups, parts, categories: [...new Set(parts.map((p) => p.category).filter(Boolean))] },
    cost: normCost(e.cost ?? e.cost_class) || stateful, passes: passes ? passes.length : null,
    passTypes: passes ? passes.map(String) : null,
    categoryNames: names,
    images: studyOnly ? { poster: [], frames: [], sheet: null, flip: null } : imagesFor(e, id, routes),
    renderStatus: renders.status ? String(renders.status) : null,
    standIns: studyOnly ? [] : standInsOf(renders),
    swiftshader: studyOnly ? null : swiftOf(renders),
    studyUrl: study.url || routes.study(id), studyMissing: !!study.missing, studyHeadings: study.headings || [],
    url: e.url || null,
  };
}

/** The Shelf index (any of {shaders | entries | loved | items: [...]}, or a bare list) as card entries. */
export function normalizeShelf(json, atlas, routes) {
  const list = Array.isArray(json) ? json
    : (json && (json.shaders || json.entries || json.loved || json.items)) || [];
  const loved = new Map(((atlas && atlas.loved) || []).map((l) => [l.id, l]));
  const names = categoryNamesOf(atlas);
  return { entries: list.filter((e) => e && e.id).map((e) => entryFrom(e, atlas, routes, loved, names)), source: 'shelf' };
}

/** The 42 loved shaders from the atlas alone (the Shelf index is not served yet): names and atlas links only. */
export function shelfFromAtlas(atlas, routes) {
  const loved = (atlas && atlas.loved) || [];
  const map = new Map(loved.map((l) => [l.id, l]));
  const names = categoryNamesOf(atlas);
  return { entries: loved.map((l) => entryFrom({ id: l.id, title: l.short, study_only: l.study_only }, atlas, routes, map, names)),
    source: 'atlas' };
}

// --------------------------------------------------------------------------------------------- the panel --
const MAX_TAGS = 6;     // a card shows six technique tags; the rest fold into "+N" (hover lists them)
const MAX_TEACH = 5;    // and five of the categories it teaches

export function mountShelf(doc, root, opts = {}) {
  const routes = opts.routes;
  const fetchImpl = opts.fetch;
  const onStage = typeof opts.onStage === 'function' ? opts.onStage : () => {};
  const onTag = typeof opts.onTag === 'function' ? opts.onTag : () => {};
  const onGroup = typeof opts.onGroup === 'function' ? opts.onGroup : () => {};
  const reducedMotion = typeof opts.reducedMotion === 'function' ? opts.reducedMotion : () => false;
  const setTimer = opts.setTimeout || ((fn, ms) => setTimeout(fn, ms));
  const clearTimer = opts.clearTimeout || ((t) => clearTimeout(t));
  const { side, body } = panel(doc, root, 'wb-shelf', 'Shelf',
    'The loved shaders, pre-rendered on SwiftShader. Pictures only: nothing runs until you ask.');
  const banner = h(doc, 'div', 'wb-shelf-banner');
  const grid = h(doc, 'div', 'wb-shelf-grid', null, { role: 'list' });
  // The study column opens beside the cards when a note is asked for, and the cards have the whole width otherwise.
  const study = h(doc, 'aside', 'wb-study', null, { 'aria-live': 'polite', hidden: true });
  const layout = put(h(doc, 'div', 'wb-shelf-layout'), grid, study);
  body.replaceChildren(hint(doc, 'Reading the Shelf index...'));
  let flip = null;   // {sprite, timer, i}: the one card flipping
  let studyToken = 0;

  function stopFlip() {
    if (!flip) return;
    clearTimer(flip.timer);
    setClass(flip.sprite, 'is-playing', false);
    flip = null;
  }
  // Step a window across the contact sheet, frame by frame: the sheet is one picture already loaded once, so the
  // flipbook costs one image request per card and a background-position change per step, and nothing on the GPU.
  function startFlip(media, sprite, entry) {
    const f = entry.images.flip;
    if (!f || reducedMotion()) return;
    stopFlip();
    const r = typeof media.getBoundingClientRect === 'function' ? media.getBoundingClientRect() : null;
    const width = r && r.width > 0 ? r.width : FILM.cell[0];
    const first = sheetFrame(0, f.frames);
    const k = width / first.cw;
    if (!sprite.style.backgroundImage) sprite.style.backgroundImage = `url("${f.sheet}")`;   // fetched on first hover only
    sprite.style.backgroundSize = `${Math.round(first.w * k)}px ${Math.round(first.h * k)}px`;
    // The sheet's own spacing (to / (frames - 1) seconds) is real time; sparse frames are held long enough to read.
    const spacing = f.to && f.frames > 1 ? (f.to / (f.frames - 1)) * 1000 : 250;
    const dt = Math.max(60, Math.min(300, spacing));
    flip = { sprite, timer: null, i: 0 };
    setClass(sprite, 'is-playing', true);
    const step = () => {
      if (!flip || flip.sprite !== sprite) return;
      const g = sheetFrame(flip.i, f.frames);
      sprite.style.backgroundPosition = `${-Math.round(g.x * k)}px ${-Math.round(g.y * k)}px`;
      flip.i = (flip.i + 1) % f.frames;
      flip.timer = setTimer(step, dt);
    };
    step();
  }

  function closeStudy() {
    studyToken++;
    study.hidden = true;
    study.replaceChildren();
    setClass(layout, 'has-study', false);
  }

  async function openStudy(entry) {
    const token = ++studyToken;
    const head = h(doc, 'header', 'wb-study-head');
    const close = h(doc, 'button', 'wb-btn wb-quiet wb-study-close', 'Close', { type: 'button', 'aria-label': 'Close the study note' });
    close.addEventListener('click', closeStudy);
    put(head, put(h(doc, 'div', 'wb-study-bar'), h(doc, 'p', 'wb-kicker', 'Study note'), close),
      h(doc, 'h3', 'wb-study-title', entry.title),
      h(doc, 'p', 'wb-study-sub', `${entry.studyUrl} · private, served on loopback only`));
    study.replaceChildren(head, hint(doc, 'Reading the note...'));
    study.hidden = false;
    setClass(layout, 'has-study', true);
    const r = fetchImpl ? await fetchText(fetchImpl, entry.studyUrl) : { ok: false, reason: 'no fetch' };
    if (token !== studyToken) return;
    if (!r.ok) {
      study.replaceChildren(head, unavailable(doc, { title: 'This study note', route: entry.studyUrl, why: r.reason,
        fills: 'Study notes live in state/arsenal/shaders/study/ and are served at /study/<id>.md by the lab server.' }));
      return;
    }
    study.replaceChildren(head, renderStudy(doc, studyBlocks(r.text)));
    if (typeof study.scrollTo === 'function') study.scrollTo(0, 0);
  }

  function card(entry) {
    const art = h(doc, 'article', `wb-shelf-card${entry.studyOnly ? ' is-study-only' : ''}`, null,
      { role: 'listitem', 'data-id': entry.id });
    const media = h(doc, 'div', 'wb-shelf-media');
    if (entry.studyOnly) {
      media.appendChild(put(h(doc, 'div', 'wb-media-note'), h(doc, 'p', null, 'Study only'),
        h(doc, 'p', 'wb-media-sub', 'Its licence keeps it to the study note: no pictures, no live run.')));
    } else {
      const img = imgFrom(doc, entry.images.poster, { alt: `${entry.title}: a still rendered on SwiftShader`, cls: 'wb-flip',
        onNone: (el) => { el.remove(); media.appendChild(put(h(doc, 'div', 'wb-media-note'), h(doc, 'p', null, 'No render yet'),
          h(doc, 'p', 'wb-media-sub', `py -m arsenal shader filmstrip ${entry.id}`))); } });
      media.appendChild(img);
      const f = entry.images.flip;
      if (f) {
        const sprite = h(doc, 'div', 'wb-sprite', null, { 'aria-hidden': 'true' });
        media.appendChild(sprite);
        media.appendChild(h(doc, 'span', 'wb-flip-hint', `${f.frames} frames · hover to play`));
        media.addEventListener('pointerenter', () => startFlip(media, sprite, entry));
        media.addEventListener('pointerleave', stopFlip);
        art.addEventListener('focusin', () => startFlip(media, sprite, entry));
        art.addEventListener('focusout', stopFlip);
      }
    }
    const meta = h(doc, 'div', 'wb-shelf-meta');
    const titleRow = put(h(doc, 'div', 'wb-shelf-titlerow'), h(doc, 'h3', 'wb-shelf-title', entry.title),
      entry.cost && h(doc, 'span', `wb-chip wb-cost is-${entry.cost.toLowerCase()}`, entry.cost, { title: `Cost ${entry.cost}: ${COSTS[entry.cost].words}` }));
    const by = h(doc, 'p', 'wb-byline', [entry.author || 'author not in this index', entry.id].join(' · '));
    const lic = h(doc, 'span', `wb-licence is-${entry.licenceClass}`, entry.licence || 'licence: see the study note',
      { title: LICENCE_WORDS[entry.licenceClass] });
    // A render drawn with stand-ins (a texture the corpus never saved, silent audio) is not the shader as its author saw
    // it: the badge says so, and hovering it lists each stand-in.
    const subs = entry.standIns || [];
    const standin = subs.length ? h(doc, 'span', 'wb-standin', 'stand-in inputs', { tabIndex: 0,
      title: `These pictures were rendered with stand-ins (${standInSummary(subs)}):\n${standInLines(subs).join('\n')}` }) : null;
    put(meta, titleRow, by, put(h(doc, 'div', 'wb-licence-row'), lic, standin));
    if (entry.tags.length) {
      const tags = h(doc, 'div', 'wb-tags', null, { 'aria-label': 'Techniques, linked to the library' });
      for (const t of entry.tags.slice(0, MAX_TAGS)) {
        const b = h(doc, 'button', 'wb-tag', t.tag, { type: 'button',
          title: t.categories.length ? `In the library: ${t.categories.map((c) => `${c} ${entry.categoryNames[c] || ''}`.trim()).join(', ')}`
            : 'No atlas category for this tag' });
        if (!t.categories.length) b.disabled = true;
        b.addEventListener('click', () => { if (t.categories[0]) onTag(t.categories[0], t); });
        tags.appendChild(b);
      }
      if (entry.tags.length > MAX_TAGS) {
        tags.appendChild(h(doc, 'span', 'wb-more', `+${entry.tags.length - MAX_TAGS}`,
          { title: entry.tags.slice(MAX_TAGS).map((t) => t.tag).join(', ') }));
      }
      meta.appendChild(tags);
    }
    const teach = entry.teaches;
    if (teach.groups.length || teach.categories.length) {
      const row = h(doc, 'div', 'wb-teaches');
      row.appendChild(h(doc, 'span', 'wb-teaches-label', 'Teaches'));
      for (const g of teach.groups) {
        const b = h(doc, 'button', 'wb-teach is-group', g.name, { type: 'button', title: g.line });
        b.addEventListener('click', () => onGroup(g.name));
        row.appendChild(b);
      }
      for (const c of teach.categories.slice(0, MAX_TEACH)) {
        const n = teach.parts.filter((p) => p.category === c).length;
        const name = entry.categoryNames[c] ? ` ${entry.categoryNames[c]}` : '';
        const b = h(doc, 'button', 'wb-teach', c, { type: 'button', title: `${c}${name}: ${n} part${n === 1 ? '' : 's'} it shows` });
        b.addEventListener('click', () => onTag(c));
        row.appendChild(b);
      }
      if (teach.categories.length > MAX_TEACH) row.appendChild(h(doc, 'span', 'wb-more', `+${teach.categories.length - MAX_TEACH}`));
      meta.appendChild(row);
    }
    const actions = h(doc, 'div', 'wb-actions');
    if (!entry.studyOnly) {
      const stageBtn = h(doc, 'button', 'wb-btn wb-stage-btn', 'Put on stage', { type: 'button',
        title: 'Show it on the Stage. It stays a still until you press Run there.' });
      stageBtn.addEventListener('click', () => onStage(entry));
      actions.appendChild(stageBtn);
    }
    const studyBtn = h(doc, 'button', 'wb-btn wb-quiet wb-study-btn', 'Open study note', { type: 'button' });
    studyBtn.addEventListener('click', () => openStudy(entry));
    actions.appendChild(studyBtn);
    meta.appendChild(actions);
    put(art, media, meta);
    return art;
  }

  function setEntries(entries, missing = null) {
    stopFlip();
    const list = entries || [];
    side.textContent = `${list.length} shader${list.length === 1 ? '' : 's'} · pre-rendered on SwiftShader`;
    banner.replaceChildren(...(missing ? [unavailable(doc, { title: 'The Shelf index', route: missing.route, why: missing.why,
      fills: `Showing the ${list.length} loved shaders the atlas names, with whatever renders already exist. The Shelf slice adds `
        + '/shelf/index.json (authors, licences, technique tags, filmstrips).' })] : []));
    grid.replaceChildren(...list.map(card));
    body.replaceChildren(...(missing ? [banner] : []), layout);
  }

  function setUnavailable({ route, why, fills } = {}) {
    stopFlip();
    side.textContent = '';
    body.replaceChildren(unavailable(doc, { title: 'The Shelf', route, why,
      fills: fills || 'The Shelf needs /shelf/index.json, or at least /atlas.json for the names of the 42 loved shaders.' }));
  }

  return { el: root, setEntries, setUnavailable, openStudy: (entry) => openStudy(entry), closeStudy, stopFlip };
}
