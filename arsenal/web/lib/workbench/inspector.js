// arsenal/web/lib/workbench/inspector.js -- the INSPECTOR: the datasheet of whatever is selected (a module's header, a
// planned module's parts, a group's wiring, a loved shader's facts), the generated knobs of a recipe, and the receipt
// of what actually ran on the stage.
//
// WHY A RECEIPT BESIDE THE KNOBS. "Tweak one module and have everything update" (Daniel, 2026-10-13) only stays
// trustworthy if every picture can say exactly what made it: which modules at which versions, the sha256 of the
// composed text, the renderer, the scale. The composer already writes those facts into the first lines of every
// composed text (modlib.js emit: `// modules: name@version ...` and `// sha256: ...`); composedFacts() reads them back,
// so the Inspector reports what the composer produced rather than what the page believes it asked for. Think of the
// label a test bench prints on a board: part numbers and revision, not the order form.
//
// The knobs come from arsenal/web/lib/params-ui.js (renderParams) over params.js (paramsFromModule), passed in as
// `paramsLib`, so the house rules for controls (units beside numbers, reset per knob, cost badges, focus returned to
// the keyboard) are kept in one place. If those modules cannot load, the params are listed read-only and the panel says
// why, never a blank and never a dead knob.
//
// Apache-2.0, written for the house (Vandor, 2026-10-13). Raw DOM, takes the document as an argument.
import { COSTS, h, hint, normCost, pair, panel, put, standInLines } from './common.js';

/** {modules: ['name@version', ...], sha} from a composed text's header lines (modlib.js / modules.py emit). */
export function composedFacts(text) {
  const out = { modules: [], sha: null };
  for (const line of String(text || '').split('\n').slice(0, 6)) {
    let m = /^\/\/ modules:\s*(.*)$/.exec(line);
    if (m) out.modules = m[1].trim().split(/\s+/).filter(Boolean);
    m = /^\/\/ sha256:\s*([0-9a-fA-F]+)\s*$/.exec(line);
    if (m) out.sha = m[1];
  }
  return out;
}

const costWords = (c) => { const n = normCost(c); return n ? `${n}: ${COSTS[n].words}` : null; };
function costText(cost) {
  if (!cost) return null;
  if (typeof cost === 'string') return costWords(cost) || cost;
  const bits = [costWords(cost.class) || cost.class];
  if (cost.loop) bits.push(`loop ${cost.loop}`);
  if (cost.tex) bits.push(`${cost.tex} texture fetch${cost.tex === 1 ? '' : 'es'}`);
  if (cost.hooks) bits.push(`${cost.hooks} hook${cost.hooks === 1 ? '' : 's'}`);
  return bits.filter(Boolean).join(' · ');
}
const list = (doc, items, cls) => {
  const ul = h(doc, 'ul', cls || 'wb-list');
  for (const it of items) ul.appendChild(typeof it === 'string' ? h(doc, 'li', null, it) : put(h(doc, 'li'), it));
  return ul;
};
const mono = (doc, text) => h(doc, 'code', 'wb-mono', text);
const fmt = (x) => String(Math.round(Number(x) * 10) / 10);
/** The Stage's pre-flight as one line: what the tiny frame took, the larger frames and the growth taken from them,
 *  what every frame pays whatever its size (when it is something, or a reading set aside), what that predicts, where it
 *  started (or why not). The warm-up before the timed frames shades one pixel (the stage's measure()); a re-measure
 *  (pf.why) says it was measured again and whether it kept its scale, stepped up or continued, never "started". */
export function preflightText(pf) {
  if (!pf) return null;
  const at = (wh) => (Array.isArray(wh) ? `${wh[0]} × ${wh[1]}` : '?');
  const warm = pf.compileMs !== null && pf.compileMs !== undefined ? `, after a one-pixel draw of ${fmt(pf.compileMs)} ms (its compile)` : '';
  // What every frame pays whatever its size (the one-pixel draw again, timed): only the rest grows with the pixels. Said
  // only when it is something; a reading the stage set aside (more than the tiny frame took: a hiccup in the timing) is
  // said as that, not as what every frame pays.
  const oMs = pf.overhead && Number.isFinite(Number(pf.overhead.ms)) ? Math.round(Number(pf.overhead.ms) * 100) / 100 : null;
  const fixed = oMs === null ? ''
    : pf.overhead.setAside ? `; a per-frame reading of ${oMs} ms, more than the tiny frame took, was set aside as a hiccup`
      : oMs > 0 ? `; every frame pays ${oMs} ms whatever its size` : '';
  // The larger readings, and the growth taken from them: the most they allow, said as such when they could not prove it.
  const larger = [pf.second, ...(Array.isArray(pf.more) ? pf.more : [])].filter(Boolean);
  const g = pf.growth || null;
  const growth = g && g.readings < 2 ? `growth taken as the heaviest, exponent ${pf.exponent ?? 3}: one reading cannot show it`
    : g && !g.proven ? `growth exponent ${pf.exponent ?? 1}, the most its readings allow` : `growth exponent ${pf.exponent ?? 1}`;
  const two = larger.length ? `, then ${larger.map((q) => `${at(q.size)} in ${fmt(q.ms)} ms`).join(', ')} (${growth})`
    : g && g.readings < 2 && !pf.refused ? ` (${growth})` : '';
  const timed = pf.timedWith && pf.timedWith !== 'render' ? ` (timed with ${pf.timedWith})` : '';
  const head = pf.ms === null || pf.ms === undefined ? `${at(pf.size)} frame failed`
    : `${at(pf.size)} px in ${fmt(pf.ms)} ms${timed}${warm}${two}${fixed}`;
  const again = pf.why ? `measured again (${pf.why}): ` : '';
  if (pf.refused) return `${again}${head} · refused: ${pf.refused}`;
  const verb = pf.how === 'kept' ? 'stays at' : pf.how === 'raised' ? 'stepped up to' : pf.why ? 'continues at' : 'started at';
  return `${again}${head} · predicted ${fmt(pf.predictedFullMs)} ms at 1 × (${at(pf.fullSize)}) · ${verb} ${pf.scale} × `
    + `(about ${fmt(pf.predictedMs)} ms; budget ${pf.budgetMs || 30} ms${pf.overBudget ? ', over it' : ''})`;
}

export function mountInspector(doc, root, opts = {}) {
  const onParams = typeof opts.onParams === 'function' ? opts.onParams : () => {};
  const onCategory = typeof opts.onCategory === 'function' ? opts.onCategory : () => {};
  const onGroup = typeof opts.onGroup === 'function' ? opts.onGroup : () => {};
  // Receipts come from a live run; while live runs are off (the Stage's switch, stage.js) the empty receipt says why.
  const live = opts.live !== false;
  let paramsLib = opts.paramsLib || null;
  let paramsWhy = opts.paramsWhy || null;
  const { side, body } = panel(doc, root, 'wb-inspector', 'Inspector', '');
  const nodeBox = h(doc, 'div', 'wb-insp-node');
  const paramsBox = h(doc, 'div', 'wb-insp-params');
  const receiptBox = h(doc, 'div', 'wb-insp-receipt');
  body.replaceChildren(nodeBox, paramsBox, receiptBox);
  let current = null, ui = null;

  function idle() {
    nodeBox.replaceChildren(put(h(doc, 'div', 'wb-insp-idle'), h(doc, 'p', 'wb-kicker', 'Datasheet'),
      hint(doc, 'Pick a module, a group or a loved shader to see its datasheet: what it promises, what it costs, who taught it.')));
    paramsBox.replaceChildren();
    clearReceipt();
  }
  function clearReceipt() {
    const what = 'the modules and their versions, the composed sha256, the renderer and the scale';
    receiptBox.replaceChildren(put(h(doc, 'div', 'wb-receipt is-empty'), h(doc, 'p', 'wb-kicker', 'Receipt'),
      hint(doc, live ? `Nothing has run yet. A live run writes here what ran: ${what}.`
        : `Nothing has run. Live runs are off until their safety review clears; once they are on, a live run writes here what ran: ${what}.`)));
  }

  function titleBlock(kicker, title, sub, chips) {
    return put(h(doc, 'header', 'wb-insp-head'), h(doc, 'p', 'wb-kicker', kicker), h(doc, 'h3', 'wb-insp-title', title),
      sub && h(doc, 'p', 'wb-insp-sub', sub), chips && chips.length ? put(h(doc, 'div', 'wb-chips'), ...chips) : null);
  }
  const chip = (text, cls, title) => h(doc, 'span', `wb-chip ${cls || ''}`.trim(), text, title ? { title } : null);
  const stateChip = (built) => chip(built ? 'built' : 'planned', `wb-state ${built ? 'is-built' : 'is-planned'}`);
  const costChip = (c) => { const n = normCost(c); return chip(n || 'C?', `wb-cost ${n ? 'is-' + n.toLowerCase() : 'is-unknown'}`, costWords(c) || 'cost class not stated'); };

  function headerSheet(hd) {
    const dl = h(doc, 'dl', 'wb-sheet');
    pair(doc, dl, 'Contract', hd.contract);
    pair(doc, dl, 'Craft note', hd.note);
    pair(doc, dl, 'Kind', hd.kind);
    pair(doc, dl, 'Version', hd.version);
    pair(doc, dl, 'Category', [hd.cat, hd.family].filter(Boolean).join(' · '));
    pair(doc, dl, 'Cost', costText(hd.cost));
    pair(doc, dl, 'Entry', hd.entry ? mono(doc, hd.entry) : null);
    pair(doc, dl, 'Hooks', Array.isArray(hd.hooks) && hd.hooks.length ? list(doc, hd.hooks.map((x) => mono(doc, x))) : null);
    if (hd.targets) pair(doc, dl, 'Targets', [hd.targets.glsl, ...(hd.targets.needs || [])].filter(Boolean).join(' · '));
    pair(doc, dl, 'Licence', hd.license || hd.licence);
    pair(doc, dl, 'Credits', Array.isArray(hd.credits) && hd.credits.length ? list(doc, hd.credits.map(String)) : null);
    pair(doc, dl, 'Debug views', hd.debug);
    pair(doc, dl, 'Card', hd.card);
    pair(doc, dl, 'CPU twin', hd.twin ? mono(doc, hd.twin) : null);
    pair(doc, dl, 'Exemplars', hd.exemplars);
    pair(doc, dl, 'Learn', hd.learn);
    pair(doc, dl, 'Needs', hd.needs);
    return dl;
  }

  function partsList(parts) {
    const box = h(doc, 'div', 'wb-parts');
    for (const p of parts) {
      const row = h(doc, 'div', 'wb-part');
      put(row, put(h(doc, 'div', 'wb-part-head'), mono(doc, p.signature || (p.functions || []).join(', ')),
        put(h(doc, 'span', 'wb-chips'), p.status && chip(p.status, `wb-pri is-${String(p.status).toLowerCase()}`), costChip(p.cost))),
      p.contract && h(doc, 'p', 'wb-part-contract', p.contract),
      (p.learn && p.learn.length) || (p.exemplars && p.exemplars.length)
        ? h(doc, 'p', 'wb-part-meta', [p.learn && p.learn.length ? `learn: ${p.learn.join(', ')}` : '',
          p.loved_text ? `loved: ${p.loved_text}` : ''].filter(Boolean).join(' · ')) : null);
      box.appendChild(row);
    }
    return box;
  }

  function paramsSection(node, hd) {
    paramsBox.replaceChildren();
    ui = null;
    const ps = Array.isArray(hd && hd.params) ? hd.params : [];
    if (!ps.length) return;
    const head = put(h(doc, 'div', 'wb-sub-head'), h(doc, 'p', 'wb-kicker', 'Knobs'),
      h(doc, 'p', 'wb-insp-sub', 'Generated from the header. They reach the stage when its card reads them.'));
    paramsBox.appendChild(head);
    if (paramsLib && typeof paramsLib.renderParams === 'function' && typeof paramsLib.paramsFromModule === 'function') {
      let descriptors;
      try { descriptors = paramsLib.paramsFromModule(hd, null); } catch (e) {
        paramsBox.appendChild(h(doc, 'p', 'wb-note', `These params do not form valid descriptors: ${(e && e.message) || e}`));
        return;
      }
      ui = paramsLib.renderParams(doc, descriptors, {
        idPrefix: `wb-${String(node.name || 'p').replace(/[^A-Za-z0-9_-]/g, '-')}`,
        onChange: (id, value, values) => onParams(values, descriptors, node),
      });
      paramsBox.appendChild(ui.root);
      if (ui.problems && ui.problems.length) paramsBox.appendChild(h(doc, 'p', 'wb-note', ui.problems.join('; ')));
      return;
    }
    const dl = h(doc, 'dl', 'wb-sheet');
    for (const p of ps) {
      const range = Array.isArray(p.range) ? `${p.range[0]} to ${p.range[1]}` : '';
      pair(doc, dl, p.label || p.name, [range, p.unit, p.default !== undefined ? `default ${JSON.stringify(p.default)}` : ''].filter(Boolean).join(' · '));
    }
    paramsBox.appendChild(dl);
    paramsBox.appendChild(h(doc, 'p', 'wb-note', `Read-only: the generated controls (params-ui) did not load${paramsWhy ? ` (${paramsWhy})` : ''}.`));
  }

  function showModule(m) {
    const built = m.status === 'built';
    const hd = m.header || null;
    const chips = [stateChip(built), m.priority && chip(m.priority, `wb-pri is-${m.priority.toLowerCase()}`), costChip(m.cost),
      m.version && chip(`v${m.version}`, 'wb-ver')].filter(Boolean);
    const parts = [titleBlock(built ? 'Module' : 'Module · planned', built ? m.name : m.title, m.path, chips)];
    if (hd) parts.push(headerSheet(hd));
    else parts.push(h(doc, 'p', 'wb-note', `Planned in the atlas, not built yet. ${m.parts.length} part${m.parts.length === 1 ? '' : 's'} `
      + 'will live in this file; the signatures and contracts below are the plan it is built to.'));
    if (m.parts && m.parts.length) {
      parts.push(put(h(doc, 'div', 'wb-sub-head'), h(doc, 'p', 'wb-kicker', `Parts · ${m.parts.length}`)));
      parts.push(partsList(m.parts));
    }
    nodeBox.replaceChildren(...parts);
    paramsSection(m, hd);
  }

  function showGroup(g) {
    const chips = [stateChip(g.built), g.priority && chip(g.priority, `wb-pri is-${String(g.priority).toLowerCase()}`), costChip(g.cost)].filter(Boolean);
    const dl = h(doc, 'dl', 'wb-sheet');
    pair(doc, dl, 'The line', g.line);
    pair(doc, dl, 'Lands on', g.landing);
    pair(doc, dl, 'Modules', list(doc, g.modules.map((m) => `${m.name}${m.built ? ` · built${m.version ? ' v' + m.version : ''}` : ' · planned'}`)));
    const tier = (g.tiers || [])[0];
    if (tier) {
      pair(doc, dl, 'Required parts', tier.required);
      pair(doc, dl, 'Optional parts', tier.optional);
    } else pair(doc, dl, 'Parts', g.parts);
    pair(doc, dl, 'Debug views', g.debug);
    pair(doc, dl, 'Exemplars', g.exemplars);
    nodeBox.replaceChildren(titleBlock('Group · reference design', g.name, null, chips), dl);
    const builtMod = g.modules.find((m) => m.built && m.header);
    paramsSection(g, builtMod ? builtMod.header : null);
  }

  function showShelf(e) {
    const chips = [h(doc, 'span', `wb-licence is-${e.licenceClass}`, e.licence || 'licence: see the study note'),
      e.cost && costChip(e.cost), e.studyOnly && chip('study only', 'wb-state is-planned')].filter(Boolean);
    const dl = h(doc, 'dl', 'wb-sheet');
    pair(doc, dl, 'Author', e.author);
    pair(doc, dl, 'Corpus id', e.id);
    pair(doc, dl, 'Passes', Array.isArray(e.passTypes) && e.passTypes.length ? e.passTypes.join(', ') : e.passes);
    if (e.studyOnlyReason) pair(doc, dl, 'Study only', e.studyOnlyReason);
    if (e.tags.length) {
      const box = h(doc, 'div', 'wb-tags');
      for (const t of e.tags) {
        const names = t.categories.map((c) => `${c}${e.categoryNames && e.categoryNames[c] ? ` ${e.categoryNames[c]}` : ''}`);
        const b = h(doc, 'button', 'wb-tag', t.tag, { type: 'button',
          title: names.length ? `In the library: ${names.join(', ')}` : 'No atlas category for this tag' });
        if (!t.categories.length) b.disabled = true;
        b.addEventListener('click', () => { if (t.categories[0]) onCategory(t.categories[0]); });
        box.appendChild(b);
      }
      pair(doc, dl, 'Techniques', box);
    }
    if (e.teaches.groups.length) {
      const box = h(doc, 'div', 'wb-teaches');
      for (const g of e.teaches.groups) {
        const b = h(doc, 'button', 'wb-teach is-group', g.name, { type: 'button', title: g.line || 'a group in the library' });
        b.addEventListener('click', () => onGroup(g.name));
        box.appendChild(b);
      }
      pair(doc, dl, 'Teaches', box);
    }
    pair(doc, dl, 'Renders', e.renderStatus);
    if (Array.isArray(e.standIns) && e.standIns.length) pair(doc, dl, 'Stand-in inputs', list(doc, standInLines(e.standIns)));
    if (e.swiftshader) {
      pair(doc, dl, 'SwiftShader (CPU)', `${fmt(e.swiftshader.warmMs)} ms a frame, warm`
        + `${Array.isArray(e.swiftshader.size) ? ` at ${e.swiftshader.size[0]} × ${e.swiftshader.size[1]}` : ''}`);
    }
    pair(doc, dl, 'Study note', e.studyMissing ? 'none written yet' : e.studyUrl);
    const parts = [titleBlock('Loved shader', e.title, e.author || null, chips), dl];
    if (e.teaches.parts.length) {
      parts.push(put(h(doc, 'div', 'wb-sub-head'), h(doc, 'p', 'wb-kicker', `Parts it shows · ${e.teaches.parts.length}`),
        h(doc, 'p', 'wb-insp-sub', 'Rebuilt in the house from the maths, never copied.')));
      parts.push(partsList(e.teaches.parts.slice(0, 24)));
    }
    nodeBox.replaceChildren(...parts);
    paramsBox.replaceChildren();
  }

  function showNode(node) {
    current = node || null;
    if (!node) { idle(); return; }
    side.textContent = node.kind === 'group' ? 'group' : node.kind === 'module' ? node.status : '';
    if (node.kind === 'group') showGroup(node);
    else if (node.kind === 'shelf') showShelf(node);
    else showModule(node);
  }

  function showReceipt(r) {
    if (!r) { clearReceipt(); return; }
    const dl = h(doc, 'dl', 'wb-sheet wb-receipt-sheet');
    pair(doc, dl, 'Subject', r.subject);
    pair(doc, dl, 'Renderer', r.renderer || 'not reported');
    pair(doc, dl, 'Scale', r.scale !== undefined && r.scale !== null ? `${r.scale} ×` : null);
    pair(doc, dl, 'Drawing buffer', Array.isArray(r.size) ? `${r.size[0]} × ${r.size[1]} px` : null);
    pair(doc, dl, 'Cost class', r.cost ? `${r.cost}${r.raised ? ` (raised from ${r.raised.from || 'unknown'}: ${r.raised.why})` : ''}` : (r.costKnown === false ? 'unknown, run as C4' : null));
    if (r.compile) pair(doc, dl, 'Compile', r.compile.ok ? 'ok' : `failed${r.compile.firstError ? `: ${r.compile.firstError}` : ''}`);
    if (r.preflight) pair(doc, dl, 'Pre-flight', preflightText(r.preflight));
    if (r.swiftshader && Number.isFinite(Number(r.swiftshader.warmMs))) {
      pair(doc, dl, 'SwiftShader (CPU)', `${fmt(r.swiftshader.warmMs)} ms a frame, warm`
        + `${Array.isArray(r.swiftshader.size) ? ` at ${r.swiftshader.size[0]} × ${r.swiftshader.size[1]}` : ''} (the Shelf's render)`);
    }
    if (r.held) {
      const why = r.held.reason === 'gap' ? `one frame took ${fmt(r.held.gapMs)} ms`
        : r.held.reason === 'budget' ? `slow frames added up to ${fmt(r.held.streakMs)} ms` : `${r.held.slowFrames} slow frames in a row`;
      pair(doc, dl, 'Watchdog', `held the last frame: ${why} (at ${r.held.scale} ×, after ${r.held.frames} frames)`);
    }
    pair(doc, dl, 'Modules', Array.isArray(r.modules) && r.modules.length ? list(doc, r.modules.map((m) => mono(doc, m))) : null);
    pair(doc, dl, 'Composed sha256', r.sha ? mono(doc, r.sha) : null);
    if (r.params) pair(doc, dl, 'Knobs', Object.entries(r.params).map(([k, v]) => `${k} = ${JSON.stringify(v)}`));
    if (Array.isArray(r.unread) && r.unread.length) pair(doc, dl, 'Knobs this card ignores', r.unread);
    pair(doc, dl, 'Corpus id', r.corpus);
    pair(doc, dl, 'Licence', r.licence);
    if (Array.isArray(r.substituted) && r.substituted.length) {
      pair(doc, dl, 'Stand-ins', r.substituted.map((s) => `${s.kind || 'medium'}: ${s.reason || ''}`.trim()));
    }
    pair(doc, dl, 'Started', r.startedAt);
    receiptBox.replaceChildren(put(h(doc, 'div', 'wb-receipt'), put(h(doc, 'div', 'wb-sub-head'), h(doc, 'p', 'wb-kicker', 'Receipt · what ran'),
      h(doc, 'p', 'wb-insp-sub', 'Numbers beside the image, never a verdict on taste.')), dl));
  }

  function setParamsLib(lib, why = null) {
    paramsLib = lib || null;
    paramsWhy = why;
    if (current && current.kind === 'module' && current.header) paramsSection(current, current.header);
  }

  idle();
  return { el: root, showNode, showReceipt, clearReceipt, setParamsLib, values: () => (ui ? ui.values() : null) };
}
