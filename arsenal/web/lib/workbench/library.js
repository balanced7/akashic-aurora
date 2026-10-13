// arsenal/web/lib/workbench/library.js -- the LIBRARY panel: the house parts room as a tree, families > categories >
// modules, plus the groups (reference designs), each module marked planned or built with its cost class and status.
//
// WHY A TREE OF PLANNED AND BUILT TOGETHER. The atlas (arsenal/shaders/atlas.json) plans 572 parts in 100 module files;
// tonight the library builds the first of them. A catalogue that lists only what exists hides the plan, and one that
// lists only the plan hides progress. So every planned module is shown, and a built one (present in
// /glsl/index.json, parsed by the composer's browser twin) lights up with its own header: think of a parts drawer
// with labels on every bin, some bins still empty. A built module the atlas never planned is listed under its own
// heading rather than dropped, so the tree can never quietly disagree with the files.
//
//   const lib = mountLibrary(doc, sectionEl, { onSelect(node), cardImages(node) -> [urls] });
//   lib.setTree(buildTree(atlas, builtModules(library)));   // or lib.setUnavailable({route, why})
//   lib.reveal('B3');                                        // a Shelf tag lands here
//
// A module's cost class is the heaviest of its parts (or what its header declares, once built); its status is the
// most urgent of its parts' (P0 before P1 before P2). Groups are the atlas's 25 reference designs.
//
// Apache-2.0, written for the house (Vandor, 2026-10-13). Raw DOM, takes the document as an argument.
import { COSTS, h, heaviest, hint, imgFrom, mostUrgent, normCost, panel, put, setClass, unavailable } from './common.js';

// ------------------------------------------------------------------------------------------- the data --
/** The built modules of a composer library (modlib createLibrary / libraryFromSources): path -> facts. */
export function builtModules(lib) {
  const out = new Map();
  if (!lib || !lib.modules) return out;
  for (const m of lib.modules.values()) {
    out.set(m.path, { name: m.name, path: m.path, version: m.version, kind: m.kind, header: m.header,
      provides: m.provides || [], cost: normCost(m.header && m.header.cost) });
  }
  return out;
}

const fileTitle = (path) => String(path).replace(/\.glsl$/, '');

/** The atlas joined with the built modules: {families, groups, unplaced, problems, totals}. */
export function buildTree(atlas, built = new Map(), { problems = [] } = {}) {
  const parts = Array.isArray(atlas && atlas.parts) ? atlas.parts : [];
  const byModule = new Map();
  for (const p of parts) {
    if (!p || !p.module) continue;
    if (!byModule.has(p.module)) byModule.set(p.module, []);
    byModule.get(p.module).push(p);
  }
  // A module's home is the category holding most of its parts (ties: the first in atlas order); it appears once, there,
  // and every other category it serves lists it as "also uses".
  const catOrder = new Map((atlas.categories || []).map((c, i) => [c.id, i]));
  const home = new Map();
  for (const [path, ps] of byModule) {
    const counts = new Map();
    for (const p of ps) counts.set(p.category, (counts.get(p.category) || 0) + 1);
    const best = [...counts.entries()].sort((a, b) => b[1] - a[1] || (catOrder.get(a[0]) ?? 1e9) - (catOrder.get(b[0]) ?? 1e9))[0];
    home.set(path, best[0]);
  }
  const moduleNode = (path, category, family) => {
    const ps = byModule.get(path) || [];
    const b = built.get(path) || null;
    const header = b ? b.header || null : null;
    return {
      kind: 'module', path, category, family,
      name: b ? b.name : fileTitle(path),
      title: fileTitle(path),
      status: b ? 'built' : 'planned',
      priority: mostUrgent(ps.map((p) => p.status)),
      cost: (b && b.cost) || heaviest(ps.map((p) => p.cost)),
      functions: ps.flatMap((p) => p.functions || []),
      parts: ps,
      header, version: b ? b.version : null, moduleKind: b ? b.kind : null,
    };
  };
  const families = (atlas.families || []).map((f) => {
    const categories = (atlas.categories || []).filter((c) => c.family === f.letter).map((c) => {
      const mods = (c.modules || []).filter((m) => byModule.has(m));
      const modules = mods.filter((m) => home.get(m) === c.id).map((m) => moduleNode(m, c.id, f.letter));
      const alsoUses = mods.filter((m) => home.get(m) !== c.id).map((m) => ({ path: m, home: home.get(m) }));
      return { kind: 'category', id: c.id, name: c.name, family: f.letter, modules, alsoUses,
        counts: { modules: modules.length, built: modules.filter((m) => m.status === 'built').length,
          parts: modules.reduce((n, m) => n + m.parts.length, 0) } };
    });
    const all = categories.flatMap((c) => c.modules);
    return { kind: 'family', letter: f.letter, name: f.name, summary: f.summary || [], categories,
      counts: { modules: all.length, built: all.filter((m) => m.status === 'built').length,
        parts: all.reduce((n, m) => n + m.parts.length, 0) } };
  });
  const groupPaths = new Set();
  const groups = (atlas.groups || []).map((g) => {
    const modules = (g.modules || []).map((p) => {
      groupPaths.add(p);
      const b = built.get(p);
      return { path: p, built: !!b, name: b ? b.name : fileTitle(p), header: b ? b.header : null, version: b ? b.version : null };
    });
    return { kind: 'group', name: g.name, line: g.line || '', cost: normCost(g.cost), priority: g.status || null,
      modules, parts: g.parts || [], exemplars: g.exemplars || [], studyOnly: g.study_only || [],
      debug: g.debug || [], landing: g.landing || '', tiers: g.tiers || [], built: modules.some((m) => m.built) };
  });
  const placed = new Set([...byModule.keys(), ...groupPaths]);
  const unplaced = [...built.values()].filter((b) => !placed.has(b.path)).map((b) => ({
    kind: 'module', path: b.path, category: (b.header && b.header.cat) || null, family: (b.header && b.header.family) || null,
    name: b.name, title: fileTitle(b.path), status: 'built', priority: (b.header && b.header.status) || null,
    cost: b.cost, functions: b.provides || [], parts: [], header: b.header, version: b.version, moduleKind: b.kind,
  }));
  const mods = families.flatMap((f) => f.categories).flatMap((c) => c.modules);
  return {
    families, groups, unplaced, problems: problems || [],
    totals: { modules: mods.length, built: mods.filter((m) => m.status === 'built').length + unplaced.length,
      parts: parts.length, groups: groups.length, groupsBuilt: groups.filter((g) => g.built).length },
  };
}

/** The tree narrowed to what matches a query (a module path or name, a function, a category or family name). */
export function filterTree(tree, query) {
  const q = String(query || '').trim().toLowerCase();
  if (!q) return tree;
  const hit = (...xs) => xs.some((x) => String(x || '').toLowerCase().includes(q));
  const modHit = (m) => hit(m.path, m.name, ...(m.functions || []));
  const families = [];
  for (const f of tree.families) {
    const famHit = hit(f.name, f.letter === q.toUpperCase() ? f.letter : '');
    const categories = [];
    for (const c of f.categories) {
      const catHit = famHit || hit(c.name, c.id.toLowerCase() === q ? c.id : '');
      const modules = catHit ? c.modules : c.modules.filter(modHit);
      if (modules.length || (catHit && !c.modules.length)) categories.push({ ...c, modules });
    }
    if (categories.length) families.push({ ...f, categories });
  }
  const groups = tree.groups.filter((g) => hit(g.name, g.line, ...(g.parts || [])));
  return { ...tree, families, groups, unplaced: tree.unplaced.filter(modHit), filtered: q };
}

// ------------------------------------------------------------------------------------------ the panel --
function chip(doc, text, cls, title) {
  return h(doc, 'span', `wb-chip ${cls || ''}`.trim(), text, title ? { title } : null);
}
function costChip(doc, cls) {
  const c = normCost(cls);
  return chip(doc, c || 'C?', `wb-cost ${c ? 'is-' + c.toLowerCase() : 'is-unknown'}`,
    c ? `Cost ${c}: ${COSTS[c].words}` : 'Cost class not stated');
}
function statusChip(doc, status) {
  return status === 'built'
    ? chip(doc, 'built', 'wb-state is-built', 'In the library: composed from /glsl/')
    : chip(doc, 'planned', 'wb-state is-planned', 'Planned in the atlas, not built yet');
}

export function mountLibrary(doc, root, opts = {}) {
  const onSelect = typeof opts.onSelect === 'function' ? opts.onSelect : () => {};
  const cardImages = typeof opts.cardImages === 'function' ? opts.cardImages : () => [];
  const { side, body } = panel(doc, root, 'wb-library', 'Library', '');
  const filterBox = h(doc, 'div', 'wb-filter');
  const filter = h(doc, 'input', 'wb-filter-input', null, {
    type: 'search', placeholder: 'Filter: module, function, category', 'aria-label': 'Filter the library' });
  filterBox.appendChild(filter);
  const tree = h(doc, 'div', 'wb-tree', null, { role: 'tree' });
  body.replaceChildren(hint(doc, 'Reading the atlas and the module index...'));
  let full = null, selected = null;
  const rows = new Map();     // path or group:name -> row element
  const families = new Map(); // letter -> details
  const categories = new Map(); // id -> details

  function select(key, node) {
    if (selected) setClass(selected, 'is-selected', false);
    selected = rows.get(key) || null;
    if (selected) { setClass(selected, 'is-selected', true); selected.setAttribute('aria-current', 'true'); }
    if (node) onSelect(node);
  }

  function moduleRow(m) {
    const btn = h(doc, 'button', `wb-module is-${m.status}`, null, { type: 'button', 'data-path': m.path });
    const thumb = h(doc, 'span', 'wb-thumb', null, { 'aria-hidden': 'true' });
    const urls = m.status === 'built' ? cardImages(m) : [];
    if (urls.length) {
      thumb.appendChild(imgFrom(doc, urls, { alt: '', cls: 'wb-thumb-img',
        onNone: (img) => { img.remove(); setClass(thumb, 'is-none', true); thumb.title = 'No card rendered yet'; } }));
    } else setClass(thumb, m.status === 'built' ? 'is-none' : 'is-planned', true);
    const text = h(doc, 'span', 'wb-mod-text');
    text.appendChild(h(doc, 'span', 'wb-mod-name', m.status === 'built' && m.name !== m.title ? m.name : m.title));
    const sub = m.status === 'built' && m.name !== m.title ? m.path : `${m.functions.length} ${m.functions.length === 1 ? 'part' : 'parts'}`;
    text.appendChild(h(doc, 'span', 'wb-mod-sub', sub + (m.version ? ` · v${m.version}` : '')));
    const chips = put(h(doc, 'span', 'wb-chips'), statusChip(doc, m.status),
      m.priority && chip(doc, m.priority, `wb-pri is-${m.priority.toLowerCase()}`, `Atlas status ${m.priority}`),
      costChip(doc, m.cost));
    put(btn, thumb, text, chips);
    btn.title = m.functions.length ? m.functions.slice(0, 12).join(', ') + (m.functions.length > 12 ? ', ...' : '') : m.path;
    btn.addEventListener('click', () => select(m.path, m));
    rows.set(m.path, btn);
    return btn;
  }

  function groupRow(g) {
    const btn = h(doc, 'button', `wb-group ${g.built ? 'is-built' : 'is-planned'}`, null, { type: 'button', 'data-group': g.name });
    const text = h(doc, 'span', 'wb-mod-text');
    text.appendChild(h(doc, 'span', 'wb-mod-name', g.name));
    text.appendChild(h(doc, 'span', 'wb-mod-sub', g.line));
    put(btn, h(doc, 'span', `wb-thumb ${g.built ? 'is-none' : 'is-planned'}`, null, { 'aria-hidden': 'true' }), text,
      put(h(doc, 'span', 'wb-chips'), statusChip(doc, g.built ? 'built' : 'planned'),
        g.priority && chip(doc, g.priority, `wb-pri is-${String(g.priority).toLowerCase()}`), costChip(doc, g.cost)));
    btn.addEventListener('click', () => select(`group:${g.name}`, g));
    rows.set(`group:${g.name}`, btn);
    return btn;
  }

  function render(t) {
    rows.clear(); families.clear(); categories.clear(); selected = null;
    const open = !!t.filtered;
    const nodes = [];
    for (const f of t.families) {
      const fam = h(doc, 'details', 'wb-branch wb-family', null, { 'data-family': f.letter });
      fam.open = open;
      const sum = h(doc, 'summary', 'wb-fam-sum');
      put(sum, h(doc, 'span', 'wb-fam-letter', f.letter), h(doc, 'span', 'wb-fam-name', f.name),
        h(doc, 'span', 'wb-fam-count', `${f.counts.built}/${f.counts.modules}`, { title: `${f.counts.built} of ${f.counts.modules} modules built; ${f.counts.parts} parts planned` }));
      fam.appendChild(sum);
      for (const c of f.categories) {
        const cat = h(doc, 'details', 'wb-category', null, { 'data-category': c.id, 'data-family': f.letter });
        cat.open = open;
        const cs = h(doc, 'summary', 'wb-cat-sum');
        put(cs, h(doc, 'span', 'wb-cat-id', c.id), h(doc, 'span', 'wb-cat-name', c.name),
          h(doc, 'span', 'wb-fam-count', `${c.counts.built}/${c.counts.modules}`));
        cat.appendChild(cs);
        const ul = h(doc, 'ul', 'wb-modules', null, { role: 'group' });
        for (const m of c.modules) ul.appendChild(put(h(doc, 'li'), moduleRow(m)));
        for (const a of c.alsoUses || []) {
          const li = h(doc, 'li', 'wb-also');
          const link = h(doc, 'button', 'wb-link', `${fileTitle(a.path)} (in ${a.home})`, { type: 'button' });
          link.addEventListener('click', () => reveal(a.home, a.path));
          put(li, h(doc, 'span', 'wb-also-label', 'also uses'), link);
          ul.appendChild(li);
        }
        cat.appendChild(ul);
        fam.appendChild(cat);
        categories.set(c.id, cat);
      }
      families.set(f.letter, fam);
      nodes.push(fam);
    }
    if (t.groups.length) {
      const g = h(doc, 'details', 'wb-branch wb-groups', null, { 'data-family': 'groups' });
      g.open = open;
      put(g, put(h(doc, 'summary', 'wb-fam-sum'), h(doc, 'span', 'wb-fam-letter', '∑'), h(doc, 'span', 'wb-fam-name', 'Groups: reference designs'),
        h(doc, 'span', 'wb-fam-count', `${t.groups.filter((x) => x.built).length}/${t.groups.length}`)));
      const ul = h(doc, 'ul', 'wb-modules');
      for (const grp of t.groups) ul.appendChild(put(h(doc, 'li'), groupRow(grp)));
      g.appendChild(ul);
      families.set('groups', g);
      nodes.push(g);
    }
    if (t.unplaced.length) {
      const u = h(doc, 'details', 'wb-branch wb-unplaced', null, { 'data-family': 'unplaced' });
      u.open = true;
      put(u, put(h(doc, 'summary', 'wb-fam-sum'), h(doc, 'span', 'wb-fam-letter', '?'),
        h(doc, 'span', 'wb-fam-name', 'Built, not in the atlas'), h(doc, 'span', 'wb-fam-count', String(t.unplaced.length))));
      const ul = h(doc, 'ul', 'wb-modules');
      for (const m of t.unplaced) ul.appendChild(put(h(doc, 'li'), moduleRow(m)));
      u.appendChild(ul);
      nodes.push(u);
    }
    if (!nodes.length) nodes.push(hint(doc, `Nothing matches "${t.filtered}".`));
    tree.replaceChildren(...nodes);
  }

  function problemsBox(problems) {
    if (!problems || !problems.length) return null;
    const box = h(doc, 'div', 'wb-note wb-problems', null, { role: 'status' });
    box.appendChild(h(doc, 'p', 'wb-note-title', `${problems.length} module${problems.length === 1 ? '' : 's'} set aside (quarantined by the composer)`));
    const ul = h(doc, 'ul');
    for (const p of problems.slice(0, 8)) ul.appendChild(h(doc, 'li', null, p.problem || String(p)));
    box.appendChild(ul);
    return box;
  }

  function setTree(t, meta = {}) {
    full = t;
    side.textContent = `${t.totals.built} of ${t.totals.modules} built · ${t.totals.parts} parts`;
    side.title = `${t.totals.built} modules built of ${t.totals.modules} planned; ${t.totals.groupsBuilt} of ${t.totals.groups} groups built`;
    const notes = [];
    if (meta.indexMissing) {
      notes.push(unavailable(doc, { title: 'Module index', route: meta.indexMissing.route, why: meta.indexMissing.why,
        fills: 'Every module shows as planned until `py -m arsenal shader lib index --write` has run and the route answers.' }));
    }
    notes.push(problemsBox(t.problems));
    if (!meta.indexMissing && t.totals.built === 0) {
      notes.push(h(doc, 'p', 'wb-hint wb-lib-hint', 'Every bin below is planned: its parts, contracts and costs come from the atlas. '
        + 'A module lights up here the moment it lands in the library index.'));
    }
    render(t);
    body.replaceChildren(...notes.filter(Boolean), filterBox, tree);
  }

  function setUnavailable({ route = '/atlas.json', why = '', fills } = {}) {
    full = null;
    side.textContent = '';
    body.replaceChildren(unavailable(doc, { title: 'The atlas', route, why,
      fills: fills || 'The tree is drawn from arsenal/shaders/atlas.json; the lab server serves it at /atlas.json.' }));
  }

  function reveal(categoryId, path) {
    if (!full) return false;
    if (filter.value) { filter.value = ''; render(full); }
    const cat = categories.get(categoryId);
    if (!cat) return false;
    const fam = families.get(cat.dataset.family);
    if (fam) fam.open = true;
    cat.open = true;
    setClass(cat, 'is-revealed', true);
    const row = path ? rows.get(path) : null;
    const target = row || cat;
    if (typeof target.scrollIntoView === 'function') target.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    if (row && typeof row.focus === 'function') row.focus();
    return true;
  }

  function revealGroup(name) {
    const fam = families.get('groups');
    if (fam) fam.open = true;
    const row = rows.get(`group:${name}`);
    if (row && typeof row.scrollIntoView === 'function') row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
    return !!row;
  }

  filter.addEventListener('input', () => { if (full) render(filterTree(full, filter.value)); });

  // Select a module by path without a click (a host restoring its last pick).
  function selectPath(path) {
    if (!full) return null;
    const all = [...full.families.flatMap((f) => f.categories).flatMap((c) => c.modules), ...full.unplaced];
    const node = all.find((m) => m.path === path) || null;
    if (node) select(path, node);
    return node;
  }

  return { el: root, setTree, setUnavailable, reveal, revealGroup, select: selectPath, tree: () => full };
}
