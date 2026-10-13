// arsenal/web/lib/workbench/workbench.js -- the Workbench, assembled: LIBRARY | STAGE | INSPECTOR over a STRIP, plus a
// SHELF tab (architecture draft 5.3). The Shader Lab mounts it today (arsenal/web/shaderlab/lab.js); the bench, the
// Studio and First Light can mount the same panels later by passing their own route table.
//
// WHAT HAPPENS ON LOAD, and what does not. On load the page reads data only: the atlas, the module index and the
// module texts, the Shelf index, and the knob generator's JavaScript. No canvas is created, no WebGL context is asked
// for, and the shader runtime (toy-runtime.js) is not even imported (ruling 5). Live runs are OFF until their safety
// review clears: the Stage reads one switch (stage.js liveSwitch: ?live=1 in the address AND the localStorage key, see
// arsenal/web/shaderlab/README.md), and while it is off the lab is view only: SwiftShader stills and filmstrips, no
// Run button, and none of the three ever happens. With it on, the Stage does all three only after "Run live on this
// GPU" is pressed. Every panel says "not available yet" with the route it asked when that route has not answered, so a
// half-built server shows its gaps instead of blank boxes.
//
// HOW THE PANELS TALK. One selection at a time: picking a module (or a group) in the Library shows its datasheet in the
// Inspector, its test card on the Stage and its card renders in the Strip; "Put on stage" on a Shelf card does the same
// for a loved shader; a Shelf tag or a "teaches" link jumps to its category in the Library. The Stage reports what ran
// to the Inspector (the receipt) and its takes to the Strip; the Inspector's knobs go back to the Stage.
//
//   import { mountWorkbench } from '/webl/workbench/workbench.js';
//   const wb = await mountWorkbench(document, document.getElementById('lab'), { routes });   // all options optional
//   await wb.ready;
//
// Apache-2.0, written for the house (Vandor, 2026-10-13). Raw DOM, no framework, no CDN, no build step.
import { ROUTES, fetchJson, fetchText, h, heaviest, normCost, put, setClass, unavailable } from './common.js';
import { buildTree, builtModules, mountLibrary } from './library.js';
import { mountShelf, normalizeShelf, shelfFromAtlas, licenceClass, standInSummary } from './shelf.js';
import { cardShader, mountStage, parseCard, bindParams } from './stage.js';
import { composedFacts, mountInspector } from './inspector.js';
import { mountStrip } from './strip.js';

const MEDIA_SITE_PREFIX = '/media/a/';

/** The card stills a module's card renders to (`py -m arsenal shader card <name> --render`, arsenal/shaders/cards.py):
 *  one t<t>.png per time in its header's t list (default [0], as cards.py's), named the way render.py names frames. */
export function cardImages(routes, name, header, { probe = false } = {}) {
  const ts = header && Array.isArray(header.t) && header.t.length ? header.t : [0];
  return ts.map((t) => routes.card(name, `${probe ? 'nan_' : ''}t${Number(t).toFixed(2)}.png`));
}

/** The Strip's frames for a card: each still beside its NaN probe (NaN and Inf painted magenta, the rest dimmed). */
export function cardFrames(routes, name, header) {
  const ts = header && Array.isArray(header.t) && header.t.length ? header.t : [0];
  return ts.flatMap((t) => [
    { t, url: routes.card(name, `t${Number(t).toFixed(2)}.png`) },
    { t, url: routes.card(name, `nan_t${Number(t).toFixed(2)}.png`), label: `NaN probe, t = ${Number(t).toFixed(2)} s` },
  ]);
}

/** The cost of composing `names`: the heaviest class across every module they pull in (modlib's resolve closure), so a
 *  light card over a heavy helper is gated as the helper. {cls, known, heaviest, unknown, modules}: cls is null when
 *  any module in the closure declares no cost (the whole is then unknown, which the Stage runs as C4) or the closure
 *  cannot be resolved; heaviest names the module that set the class. */
export function closureCost(lib, names) {
  const none = { cls: null, known: false, heaviest: null, unknown: [], modules: [] };
  if (!lib || typeof lib.resolve !== 'function' || !Array.isArray(names) || !names.length) return none;
  let order;
  try { order = lib.resolve(names); } catch (e) { return { ...none, error: (e && e.message) || String(e) }; }
  const rows = order.map((n) => { const m = lib.get(n); return { name: n, cls: normCost(m && m.header && m.header.cost) }; });
  const unknown = rows.filter((r) => !r.cls).map((r) => r.name);
  const top = heaviest(rows.map((r) => r.cls));
  const by = rows.find((r) => r.cls && r.cls === top);
  return { cls: unknown.length ? null : top, known: !unknown.length, heaviest: unknown.length ? unknown[0] : (by ? by.name : null),
    unknown, modules: rows.map((r) => r.name) };
}

/** A loved shader's saved media path (/media/a/<file>) as a lab-server URL; anything else has none (a stand-in). */
export function mediaFor(routes, src, base) {
  const s = String(src || '');
  if (!s.startsWith(MEDIA_SITE_PREFIX) || s.length <= MEDIA_SITE_PREFIX.length) return null;
  const file = s.slice(MEDIA_SITE_PREFIX.length);
  if (!/^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$/.test(file)) return null;
  const u = routes.corpusMedia + file;
  try { return base ? new URL(u, base).href : u; } catch (e) { return u; }
}

export async function mountWorkbench(doc, root, opts = {}) {
  const routes = { ...ROUTES, ...(opts.routes || {}) };
  const g = globalThis;
  const fetchImpl = opts.fetch || ((url, init) => g.fetch(url, init));
  const importModule = opts.importModule || ((url) => import(url));
  const base = opts.base || (g.location ? g.location.href : null);
  const isHidden = opts.isHidden || (() => !!(g.document && g.document.visibilityState === 'hidden'));
  const onVisibilityChange = opts.onVisibilityChange
    || ((fn) => { if (g.document && g.document.addEventListener) g.document.addEventListener('visibilitychange', fn); });
  const reducedMotion = opts.reducedMotion
    || (() => !!(g.matchMedia && g.matchMedia('(prefers-reduced-motion: reduce)').matches));

  // ---- the frame ----
  setClass(root, 'wb-root', true);
  const top = h(doc, 'header', 'wb-top');
  const brand = put(h(doc, 'div', 'wb-brand'), h(doc, 'h1', 'wb-title', 'Shader Lab'),
    h(doc, 'p', 'wb-subtitle', 'The house parts room: modules, the loved shaders, and one stage.'));
  const tabs = h(doc, 'nav', 'wb-tabs', null, { role: 'tablist', 'aria-label': 'Views' });
  const tabBench = h(doc, 'button', 'wb-tab is-active', 'Workbench', { type: 'button', role: 'tab', 'aria-selected': 'true', 'data-tab': 'bench' });
  const tabShelf = h(doc, 'button', 'wb-tab', 'Shelf', { type: 'button', role: 'tab', 'aria-selected': 'false', 'data-tab': 'shelf' });
  put(tabs, tabBench, tabShelf);
  const safety = h(doc, 'p', 'wb-safety');   // its words follow the Stage's switch, below
  put(top, brand, tabs, safety);

  const libEl = h(doc, 'section', null, null, { 'aria-label': 'Library' });
  const stageEl = h(doc, 'section', null, null, { 'aria-label': 'Stage' });
  const inspEl = h(doc, 'section', null, null, { 'aria-label': 'Inspector' });
  const stripEl = h(doc, 'section', null, null, { 'aria-label': 'Strip' });
  const shelfEl = h(doc, 'section', null, null, { 'aria-label': 'Shelf' });
  const benchView = put(h(doc, 'div', 'wb-view wb-view-bench', null, { role: 'tabpanel' }),
    put(h(doc, 'div', 'wb-grid'), libEl, stageEl, inspEl), stripEl);
  const shelfView = put(h(doc, 'div', 'wb-view wb-view-shelf', null, { role: 'tabpanel', hidden: true }), shelfEl);
  root.replaceChildren(top, benchView, shelfView);

  // Leaving the Stage's view STOPS a live run (it is not drawn while the Shelf is in front, and a GPU should not work
  // for a hidden canvas); coming back does not restart it: Run again is an explicit click.
  const AWAY = 'you switched to the Shelf';
  function setTab(which) {
    const shelf = which === 'shelf';
    if (shelf) stage.suspend(AWAY);
    benchView.hidden = shelf;
    shelfView.hidden = !shelf;
    setClass(tabBench, 'is-active', !shelf); tabBench.setAttribute('aria-selected', String(!shelf));
    setClass(tabShelf, 'is-active', shelf); tabShelf.setAttribute('aria-selected', String(shelf));
    if (!shelf) shelf_.stopFlip();
  }
  tabBench.addEventListener('click', () => setTab('bench'));
  tabShelf.addEventListener('click', () => setTab('shelf'));

  // ---- the panels ----
  let atlas = null, lib = null;
  // The Stage reads the one switch (opts.env: the page whose address and storage it reads; by default this page's own),
  // so it is mounted first: the Inspector and the Strip say what they show according to it. The Stage reaches the
  // Inspector and the Strip only when something runs, after both are mounted.
  const stage = mountStage(doc, stageEl, {
    loadRuntime: () => importModule(routes.runtime), env: opts.env,
    raf: opts.raf, caf: opts.caf, now: opts.now, dpr: opts.dpr, isHidden, onVisibilityChange,
    onResize: opts.onResize,   // who says the Stage may have changed size; by default the window, its box and the pixel ratio
    isAway: () => (benchView.hidden ? AWAY : null),
    setTimeout: opts.setTimeout, clearTimeout: opts.clearTimeout,
    onReceipt: (r) => inspector.showReceipt(r),
    onTake: (t) => strip.addTake(t),
  });
  const inspector = mountInspector(doc, inspEl, {
    paramsLib: null, paramsWhy: 'still loading', live: stage.live,
    onParams: (values, descriptors, node) => stage.setParams({ values, descriptors, module: node && node.name }),
    onCategory: (categoryId) => { setTab('bench'); library.reveal(categoryId); },
    onGroup: (name) => { setTab('bench'); library.revealGroup(name); },
  });
  const strip = mountStrip(doc, stripEl, { live: stage.live });
  safety.textContent = stage.live
    ? 'Safe by default: every picture is pre-rendered on SwiftShader. Nothing runs on this GPU until you press Run.'
    : 'View only: every picture is pre-rendered on SwiftShader. Live runs are off until their safety review clears.';
  const library = mountLibrary(doc, libEl, {
    cardImages: (m) => cardImages(routes, m.name, null),
    onSelect: (node) => select(node),
  });
  const shelf_ = mountShelf(doc, shelfEl, {
    routes, fetch: fetchImpl, reducedMotion,
    onStage: (entry) => { setTab('bench'); putShelfOnStage(entry); },
    onTag: (categoryId) => { setTab('bench'); library.reveal(categoryId); },
    onGroup: (name) => { setTab('bench'); library.revealGroup(name); },
  });

  // ---- subjects ----
  // A card's gate is the heaviest class across everything it composes, not its module's own: a C0 helper that calls a
  // march costs a march. What the module pulls in is known at once; the card's own `uses` list is known once its text
  // has been read (data only), and the Stage is raised then, and again at load.
  function costOfUses(names, own) {
    const c = closureCost(lib, names);
    if (!c.modules.length) return { cls: normCost(own), why: null };
    const why = c.unknown.length ? `${c.unknown[0]} declares no cost, so the whole is unknown`
      : c.heaviest && !names.includes(c.heaviest) ? `it pulls in ${c.heaviest} (${c.cls})`
        : c.heaviest && names.length > 1 && c.cls !== normCost(own) ? `its card uses ${c.heaviest} (${c.cls})` : null;
    return { cls: c.cls, why, closure: c };
  }

  function cardSubject(m) {
    const hd = m.header || {};
    const gate = costOfUses([m.name], m.cost);
    return {
      kind: 'card', id: m.name, title: `${m.name}`, byline: `${m.path} · test card`, licence: hd.license || hd.licence || null,
      licenceClass: licenceClass(hd.license || hd.licence), cost: gate.cls, acceptsParams: hd.kind === 'recipe',
      costWhy: gate.why ? `Its class is the heaviest of what it composes: ${gate.why}.` : null,
      poster: cardImages(routes, m.name, null),
      posterHint: `No card rendered yet: py -m arsenal shader card ${m.name} --render`,
      load: async (p) => {
        if (!lib) throw new Error('the module library did not load');
        const src = await fetchText(fetchImpl, routes.cardSource(m.name));
        if (!src.ok) throw new Error(`no test card: ${routes.cardSource(m.name)} answered ${src.reason}`);
        const card = parseCard(src.text);
        const uses = Array.isArray(card.header.uses) && card.header.uses.length ? card.header.uses : [m.name];
        const composed = lib.compose(uses, 'toy');
        const facts = composedFacts(composed);
        const cost = costOfUses(uses, m.cost);
        let common = composed, body = card.body, bound = null;
        if (p && Array.isArray(p.descriptors)) {
          bound = bindParams(common, body, p.descriptors, p.values || {});
          common = bound.common; body = bound.body;
        }
        return { shader: cardShader(m.name, common, body), mediaUrl: null,
          cost: { cls: cost.cls, why: cost.why || 'the heaviest of the modules its card composes' },
          receipt: { modules: facts.modules, sha: facts.sha, card: m.name, uses,
            params: bound ? { ...(p.values || {}) } : null, unread: bound ? bound.unread : null } };
      },
    };
  }

  function plannedSubject(node) {
    const title = node.kind === 'group' ? node.name : node.title;
    return { kind: 'planned', id: title, title, byline: node.kind === 'group' ? node.line : node.path, cost: node.cost,
      poster: [], blocked: { title: 'Planned, not built yet',
        why: `${title} is in the atlas's plan; there is no module text and no card to run yet.` } };
  }

  function shelfSubject(e) {
    return {
      kind: 'shelf', id: e.id, title: e.title, byline: [e.author, e.id].filter(Boolean).join(' · '),
      licence: e.licence || null, licenceClass: e.licenceClass, cost: e.cost,
      swiftshader: e.swiftshader || null, standIns: e.standIns || [],
      poster: e.images.poster, posterHint: `No still yet: py -m arsenal shader filmstrip ${e.id}`,
      film: e.images.flip || null,   // the contact sheet the Stage plays while live runs are off
      blocked: e.studyOnly ? { title: 'Study only', why: 'Its licence keeps it to the study note: no pictures and no live run.' } : null,
      load: async () => {
        const r = await fetchJson(fetchImpl, routes.corpusShader(e.id));
        if (!r.ok) throw new Error(`${routes.corpusShader(e.id)} answered ${r.reason}`);
        return { shader: r.data, mediaUrl: (src) => mediaFor(routes, src, base),
          receipt: { corpus: e.id, licence: e.licence || null } };
      },
    };
  }

  let selectToken = 0;
  // The card's own header says which times it pictures; read it (data only) to label the Strip exactly.
  async function showCardRenders(name, note) {
    const token = ++selectToken;
    strip.showRenders({ title: name, frames: cardFrames(routes, name, null), note });
    const src = await fetchText(fetchImpl, routes.cardSource(name));
    if (token !== selectToken) return;
    if (!src.ok) {
      strip.showRenders({ title: name, note: `No test card yet: ${routes.cardSource(name)} answered ${src.reason}.` });
      return;
    }
    try {
      const card = parseCard(src.text);
      strip.showRenders({ title: name, frames: cardFrames(routes, name, card.header),
        note: card.header.note ? `Look for: ${card.header.note}` : note });
      // The card's own `uses` may pull in more than its module: the gate rises before any click, never falls.
      const uses = Array.isArray(card.header.uses) && card.header.uses.length ? card.header.uses : null;
      if (uses && stage.state().subject === name) {
        const c = costOfUses(uses, null);
        if (c.closure && c.closure.modules.length) stage.raiseCost(c.cls, c.why || `its card composes ${uses.join(', ')}`);
      }
    } catch (e) {
      strip.showRenders({ title: name, note: `The card did not parse: ${(e && e.message) || e}.` });
    }
  }

  function select(node) {
    inspector.showNode(node);
    inspector.clearReceipt();
    if (node.kind === 'group') {
      const b = node.modules.find((m) => m.built);
      if (b) {
        const m = { kind: 'module', path: b.path, name: b.name, title: b.name, header: b.header, version: b.version,
          cost: node.cost, status: 'built', functions: [], parts: [] };
        stage.setSubject(cardSubject(m));
        showCardRenders(b.name, "the group's test card, rendered on SwiftShader");
      } else {
        ++selectToken;
        stage.setSubject(plannedSubject(node));
        strip.showRenders({ title: node.name, note: 'A planned group: nothing to render yet.' });
      }
      return;
    }
    if (node.status === 'built') {
      stage.setSubject(cardSubject(node));
      showCardRenders(node.name, `test card stills, if rendered (py -m arsenal shader card ${node.name} --render)`);
    } else {
      ++selectToken;
      stage.setSubject(plannedSubject(node));
      strip.showRenders({ title: node.title, note: 'A planned module: nothing to render yet.' });
    }
  }

  function putShelfOnStage(e) {
    ++selectToken;
    inspector.showNode({ ...e, kind: 'shelf' });
    inspector.clearReceipt();
    stage.setSubject(shelfSubject(e));
    const subs = standInSummary(e.standIns);
    if (e.studyOnly) strip.showRenders({ title: e.title, note: 'Study only: no pictures.' });
    else strip.showRenders({ title: e.title, frames: e.images.frames, sheet: e.images.sheet,
      note: e.images.frames.length || e.images.sheet
        ? `rendered on SwiftShader${e.renderStatus && e.renderStatus !== 'rendered' ? ` · ${e.renderStatus}` : ''}${subs ? ` · stand-in inputs: ${subs}` : ''}`
        : `Not rendered yet: py -m arsenal shader render ${e.id} --t 1,4, then filmstrip ${e.id}` });
  }

  // ---- loading: data only ----
  // The library is the composer's own: modlib.loadLibrary reads the index and every module file as BYTES and decodes
  // them as the CLI does (a BOM, a byte that is not UTF-8), so the composed sha256 in a receipt is the one
  // `py -m arsenal shader lib compose` prints. It fetches with the page's own fetch, relative to the index route.
  async function loadModuleLibrary() {
    let modlib;
    try { modlib = await importModule(routes.modlib); } catch (e) {
      return { lib: null, missing: { route: routes.modlib, why: `an error (${(e && e.message) || e})` } };
    }
    try {
      return { lib: await modlib.loadLibrary(routes.glslIndex), missing: null };
    } catch (e) {
      const msg = String((e && e.message) || e);
      const why = msg.startsWith(`${routes.glslIndex}: `) ? msg.slice(routes.glslIndex.length + 2) : `an error (${msg})`;
      return { lib: null, missing: { route: routes.glslIndex, why } };
    }
  }

  const ready = (async () => {
    const [atlasR, libR, shelfR] = await Promise.all([
      fetchJson(fetchImpl, routes.atlas), loadModuleLibrary(), fetchJson(fetchImpl, routes.shelf)]);
    atlas = atlasR.ok ? atlasR.data : null;
    lib = libR.lib;
    const indexMissing = libR.missing;
    if (atlas) {
      library.setTree(buildTree(atlas, builtModules(lib), { problems: lib ? lib.problems : [] }), { indexMissing });
    } else {
      library.setUnavailable({ route: routes.atlas, why: atlasR.reason });
    }
    if (shelfR.ok) shelf_.setEntries(normalizeShelf(shelfR.data, atlas || {}, routes).entries);
    else if (atlas) shelf_.setEntries(shelfFromAtlas(atlas, routes).entries, { route: routes.shelf, why: shelfR.reason });
    else shelf_.setUnavailable({ route: routes.shelf, why: shelfR.reason });
    try {
      const [ui, p] = await Promise.all([importModule(routes.paramsUi), importModule(routes.params)]);
      inspector.setParamsLib({ ...p, ...ui });
    } catch (e) {
      inspector.setParamsLib(null, `${routes.paramsUi}: ${(e && e.message) || e}`);
    }
    return { atlas: !!atlas, modules: lib ? lib.modules.size : 0, shelf: shelfR.ok };
  })();

  return { ready, library, shelf: shelf_, stage, inspector, strip, setTab, routes, unavailable: (o) => unavailable(doc, o) };
}
