// Virtual Stage v1, the cue sequencer: arsenal/web/stage/phrases.js (pure ES module). Tests: tests/stage_phrases.test.mjs.
//
// Daniel, 2026-10-25: "The parts that are super impressive to me from the light shows are when they have 3 levels of
// light all shooting over the crowd, you have the vertical elements, you can have top, midle then bottom pan up and down
// sequentially. or horizontal flash and pan, then vertical 1, 2, 3 then back to lasers, then a cool pattern of lights from
// the circular halo." And on how he would build it: "give myself the ability to tie groups of lasers together and allow
// them to play various "animations" and triggers". His standing rule: "repeated triggers don't do the exact same thing in
// the exact same space".
//
// A PHRASE is a chaser of cue steps, as a console runs one (the lighting research: each step has its own length in beats
// and advances on follow; the first Go is quantised to the bar; heads move in black). It lives in the set file as data:
//
//   phrases.<name> = { name, bars, go: "bar", sections, base: [lines], steps: [step], vary: {deck, first, no_repeat,
//                      variants, per_repeat} }
//   step  = { id, name, beats, trigger: "follow" | "go", lines: [line], cues: [{at (beats), lines}], camera, ambient? }
//           ambient: the room's veil and fill light for the step, x the theme's (D, the laser hand-off: 0.1, so the
//           lasers cut through true black, as the footage's laser sections do)
//   line  = { group, preset?, values?, effects?: [name | {name, with}], fade? (beats), flash? }   a fixture or cell group
//         | { group, laser: {shape, gate?, schedule?, follow?, colour?, level?, from_beats?, until_beats?, ...} }  lasers
//   camera = { shot, alt?, precut_beats?, then?: {beats, shot} }
//
// The base lines run under every step (the phrase owns those fixtures for its whole run, so they move in black between
// their steps); a step's own lines override them member by member.
//
// NEVER STATIC: each repeat is dealt a VARIANT from a deck without replacement (the first deal is "first"; no two
// neighbouring repeats share one; a variant may be limited to some sections), and PER-REPEAT values change on every repeat
// whatever the variant ("cycle" through a list, "alternate" two values, "add" a step modulo, "seeded" a value in a range).
// A line names them as "$key" anywhere (a group, a value, an effect's override). A variant edits the steps of its repeat:
// replace a step's lines, swap one effect for another, patch an effect's definition, drop effects, negate a per-repeat
// value, split a step into sub-steps, or change the camera.
//
// The RUNNER is driven only by the beat position (grid.js): go() arms the phrase on the next bar line, steps follow on
// their exact beat positions (start + the sum of the lengths before them), next() ends the current step on the next bar
// line, stop() ends the phrase on the next bar line, and a phrase loops for its repeats (or until stopped). update(pos)
// returns the events of the frame: {type: "start"}, {type: "step", step, start, end, ...}, {type: "cue", ...},
// {type: "end"}. Every event carries the EXACT beat position it belongs to (a bar or beat line), not the frame's.

import { aimAt, elementMatrix, eulerToMat3, mat3MulVec, transformPoint } from "./rig.js";
import { hashSeed, rng } from "./effects.js";

export const PHRASES_API = "arsenal.stage-phrases/v1";
export const LINE_EPS = 1e-6;
export const GO_GRACE_BEATS = 0.05;       // a Go pressed this soon after a bar line lands on that line
const DEG = Math.PI / 180;
const isObj = (x) => x && typeof x === "object" && !Array.isArray(x);

// ------------------------------------------------------------------------------------------------- small tools --
export function deepMerge(a, b) {
  if (!isObj(a) || !isObj(b)) return b === undefined ? clone(a) : clone(b);
  const out = clone(a);
  for (const [k, v] of Object.entries(b)) out[k] = isObj(v) && isObj(out[k]) ? deepMerge(out[k], v) : clone(v);
  return out;
}
export function clone(x) { return x === undefined ? undefined : JSON.parse(JSON.stringify(x)); }
// "$key" strings (anywhere in a value) replaced by mods[key]; an unknown key is an error, so a typo never runs silently.
export function subst(x, mods) {
  if (typeof x === "string" && x.startsWith("$")) {
    const k = x.slice(1);
    if (!(k in mods)) throw new Error(`phrase: no per-repeat value ${x}`);
    return mods[k];
  }
  if (Array.isArray(x)) return x.map((v) => subst(v, mods));
  if (isObj(x)) { const o = {}; for (const [k, v] of Object.entries(x)) o[k] = subst(v, mods); return o; }
  return x;
}

// The per-repeat values of repeat k (0, 1, 2, ...).
export function resolveMods(perRepeat = {}, k = 0, seed = 1) {
  const out = {};
  for (const [key, rule] of Object.entries(perRepeat)) {
    if (rule.cycle) out[key] = rule.cycle[k % rule.cycle.length];
    else if (rule.alternate) out[key] = rule.alternate[k % 2];
    else if (rule.add !== undefined) { const v = rule.add * k; out[key] = rule.mod ? ((v % rule.mod) + rule.mod) % rule.mod : v; }
    else if (rule.seeded) { const r = rng(hashSeed(seed, key, k))(); out[key] = rule.seeded[0] + (rule.seeded[1] - rule.seeded[0]) * r; }
    else if (rule.value !== undefined) out[key] = rule.value;
    else throw new Error(`phrase per_repeat.${key}: one of cycle, alternate, add, seeded, value`);
  }
  return out;
}

// A deck without replacement: shuffled per round (seeded), the first deal can be fixed, and no two neighbouring deals
// are the same variant (across a reshuffle too). eligible(name) filters what can be dealt now (a variant limited to some
// sections); an ineligible card stays in the deck for later.
export class Deck {
  constructor(names, { first = null, noRepeat = true, seed = 1 } = {}) {
    this.names = names.slice();
    this.first = first;
    this.noRepeat = noRepeat;
    this.rand = rng(seed >>> 0);
    this.pile = [];
    this.last = null;
    this.dealt = 0;
  }
  _refill() {
    const p = this.names.slice();
    for (let i = p.length - 1; i > 0; i--) { const j = Math.floor(this.rand() * (i + 1)); [p[i], p[j]] = [p[j], p[i]]; }
    if (this.dealt === 0 && this.first && p.includes(this.first)) { p.splice(p.indexOf(this.first), 1); p.unshift(this.first); }
    this.pile = p;
  }
  next(eligible = () => true) {
    for (let round = 0; round < 3; round++) {
      if (!this.pile.length) this._refill();
      const i = this.pile.findIndex((n) => eligible(n) && !(this.noRepeat && n === this.last && this.names.filter(eligible).length > 1));
      if (i >= 0) { const [n] = this.pile.splice(i, 1); this.last = n; this.dealt++; return n; }
      this.pile = [];                       // nothing left that fits: a fresh round
    }
    const any = this.names.find(eligible) || this.names[0];
    this.last = any; this.dealt++;
    return any;
  }
}

// ------------------------------------------------------------------------------------------------- validation --
export function validatePhrases(rig) {
  const errs = [];
  const err = (m) => errs.push(m);
  const P = rig.phrases || {};
  const shots = (rig.cameras && rig.cameras.shots) || {};
  for (const [name, ph] of Object.entries(P)) {
    const at = `phrases.${name}`;
    if (!Array.isArray(ph.steps) || !ph.steps.length) { err(`${at}.steps: a non-empty list`); continue; }
    const ids = new Set();
    const per = (ph.vary && ph.vary.per_repeat) || {};
    let mods;
    try { mods = resolveMods(per, 0, 1); } catch (e) { err(`${at}: ${e.message}`); mods = {}; }
    const checkLines = (lines, where) => {
      for (const [i, l] of (lines || []).entries()) {
        const lw = `${where}.lines[${i}]`;
        let line;
        try { line = subst(l, mods); } catch (e) { err(`${lw}: ${e.message}`); continue; }
        if (line.laser) {
          if (!rig.laserGroups || !rig.laserGroups[line.group]) err(`${lw}.group: no laser group ${JSON.stringify(line.group)}`);
          continue;
        }
        if (!rig.groups[line.group]) err(`${lw}.group: no group ${JSON.stringify(line.group)}`);
        if (line.preset && !(rig.presets || {})[line.preset]) err(`${lw}.preset: no preset ${JSON.stringify(line.preset)}`);
        for (const e of line.effects || []) {
          const n = typeof e === "string" ? e : e && e.name;
          if (!rig.effects[n]) err(`${lw}.effects: no effect ${JSON.stringify(n)}`);
        }
        if (line.fade !== undefined && !(typeof line.fade === "number" && line.fade >= 0)) err(`${lw}.fade: beats >= 0`);
      }
    };
    checkLines(ph.base, `${at}.base`);
    let beats = 0;
    for (const [i, st] of ph.steps.entries()) {
      const sw = `${at}.steps[${i}]${st && st.id ? ` (${st.id})` : ""}`;
      if (!st.id || ids.has(st.id)) err(`${sw}.id: a unique id`);
      ids.add(st.id);
      if (!(typeof st.beats === "number" && st.beats > 0)) err(`${sw}.beats: a positive number of beats`);
      else beats += st.beats;
      if (st.trigger && !["follow", "go"].includes(st.trigger)) err(`${sw}.trigger: follow or go`);
      if (st.ambient !== undefined && !(typeof st.ambient === "number" && st.ambient >= 0 && st.ambient <= 1)) err(`${sw}.ambient: 0..1`);
      checkLines(st.lines, sw);
      for (const [j, c] of (st.cues || []).entries()) {
        if (!(typeof c.at === "number" && c.at >= 0 && c.at < st.beats)) err(`${sw}.cues[${j}].at: beats inside the step`);
        checkLines(c.lines, `${sw}.cues[${j}]`);
      }
      const cam = st.camera;
      if (cam) {
        for (const s of [cam.shot, cam.alt, cam.then && cam.then.shot]) if (s && !shots[s]) err(`${sw}.camera: no shot ${s}`);
        if (cam.then && !(cam.then.beats >= 2 && cam.then.beats <= st.beats - 2)) err(`${sw}.camera.then.beats: at least 2 beats from either end of the step`);
        if (cam.precut_beats !== undefined && !(cam.precut_beats > 0 && cam.precut_beats <= 2)) err(`${sw}.camera.precut_beats: 0 < beats <= 2`);
      }
    }
    if (ph.bars && Math.abs(beats - ph.bars * 4) > 1e-9) err(`${at}: the steps add up to ${beats} beats, not bars x 4 = ${ph.bars * 4}`);
    const v = ph.vary || {};
    for (const d of v.deck || []) if (!(v.variants || {})[d]) err(`${at}.vary.deck: no variant ${d}`);
    for (const [vn, vd] of Object.entries(v.variants || {})) {
      for (const sid of Object.keys(vd.steps || {})) if (!ids.has(sid)) err(`${at}.vary.variants.${vn}: no step ${sid}`);
      for (const [sid, op] of Object.entries(vd.steps || {})) {
        for (const [from, to] of Object.entries(op.swap || {})) if (!rig.effects[from] || !rig.effects[to]) err(`${at}.vary.variants.${vn}.${sid}.swap: ${from} -> ${to}`);
        if (op.lines) checkLines(op.lines, `${at}.vary.variants.${vn}.${sid}`);
        if (op.split) {
          const sum = op.split.reduce((s, p) => s + p.beats, 0);
          const st = ph.steps.find((s) => s.id === sid);
          if (st && Math.abs(sum - st.beats) > 1e-9) err(`${at}.vary.variants.${vn}.${sid}.split: the parts add up to ${sum}, the step is ${st.beats} beats`);
        }
      }
    }
  }
  return errs;
}

// ------------------------------------------------------------------------------------------------- presets --
// A position preset per member of a head group: Float64Array(n * 2) of [pan, tilt] degrees, or null.
//   values  the same Pan / Tilt for every head;
//   world   world-locked: each head aims at a world point; by level: [x_scale * x, y[level] + shift_y, z];
//   radial  out from the ring centre in the ring's plane, tipped forward_deg toward the ring's face (the audience).
export function resolvePreset(rig, group, preset, mods = {}) {
  if (!preset || group.kind !== "heads") return null;
  // a preset's own "$" parameters are offsets: 0 when the phrase playing it has no such per-repeat value
  const defaults = {};
  JSON.stringify(preset).replace(/"\$([a-z_][a-z0-9_]*)"/g, (_, k) => { defaults[k] = 0; return ""; });
  const p = subst(preset, { ...defaults, ...mods });
  const n = group.n, out = new Float64Array(n * 2);
  for (let m = 0; m < n; m++) {
    const fi = group.memberFixture[m], f = rig.fixtures[fi], el = rig.elements[f.element];
    const em = elementMatrix(el);
    if (p.kind === "values") { out[m * 2] = p.values.Pan ?? 0; out[m * 2 + 1] = p.values.Tilt ?? 0; continue; }
    let target;
    if (p.kind === "world") {
      const lv = group.keys.level[m], t = p.target || {};
      const y = (t.y && (t.y[String(lv)] ?? t.y[lv])) ?? 15;
      target = [(t.x_scale ?? 1) * group.keys.x[m], y + (Number(p.shift_y) || 0), t.z ?? 30];
    } else if (p.kind === "radial") {
      const a = f.angle ?? Math.atan2(f.local[1], f.local[0]);
      const fw = (p.forward_deg ?? 25) * DEG;
      const dirE = [Math.cos(fw) * Math.cos(a), Math.cos(fw) * Math.sin(a), Math.sin(fw)];
      const d = [em[0] * dirE[0] + em[1] * dirE[1] + em[2] * dirE[2], em[3] * dirE[0] + em[4] * dirE[1] + em[5] * dirE[2],
                 em[6] * dirE[0] + em[7] * dirE[1] + em[8] * dirE[2]];
      const base = transformPoint(em, f.local);
      target = [base[0] + 60 * d[0], base[1] + 60 * d[1], base[2] + 60 * d[2]];
    } else throw new Error(`preset kind ${p.kind}: values, world or radial`);
    const r = aimAt(em, f, target, { panHint: 0 });
    out[m * 2] = r.pan; out[m * 2 + 1] = r.tilt;
  }
  return out;
}

// ------------------------------------------------------------------------------------------------- compiling --
function effectRefs(line) { return (line.effects || []).map((e) => (typeof e === "string" ? { name: e } : { ...e })); }

// One line resolved against the rig: its group object, its effects' full definitions, its preset's positions.
function compileLine(rig, raw, mods, patches, stepId) {
  const l = subst(raw, mods);
  if (l.laser) {
    const g = rig.laserGroups && rig.laserGroups[l.group];
    if (!g) throw new Error(`phrase step ${stepId}: no laser group ${l.group}`);
    return { group: l.group, kind: "lasers", heads: g.heads.slice(), laser: { ...l.laser } };
  }
  const g = rig.groups[l.group];
  if (!g) throw new Error(`phrase step ${stepId}: no group ${l.group}`);
  const effects = effectRefs(l).map((ref) => {
    const base = rig.effects[ref.name];
    if (!base) throw new Error(`phrase step ${stepId}: no effect ${ref.name}`);
    const def = deepMerge(deepMerge(base, patches[ref.name] || {}), ref.with || {});
    return { name: ref.name, id: `ph:${l.group}:${ref.name}`, def };
  });
  const presetDef = l.preset ? rig.presets[l.preset] : null;
  if (l.preset && !presetDef) throw new Error(`phrase step ${stepId}: no preset ${l.preset}`);
  return { group: l.group, kind: g.kind, g, values: l.values || {}, preset: l.preset || null, positions: resolvePreset(rig, g, presetDef, mods),
           effects, fade: l.fade ?? 0, flash: l.flash || null };
}

// The steps of one repeat: the variant's edits applied, "$key" values filled in, every line compiled. Returns
// {variant, mods, steps: [{id, name, beats, trigger, lines, cues, camera}]}.
export function compileRepeat(rig, name, variant = null, mods = {}) {
  const ph = rig.phrases[name];
  if (!ph) throw new Error(`no phrase ${name}`);
  const vdef = (variant && ph.vary && ph.vary.variants && ph.vary.variants[variant]) || {};
  const steps = [];
  for (const st0 of ph.steps) {
    const op = (vdef.steps && vdef.steps[st0.id]) || {};
    const parts = op.split ? op.split.map((p, k) => ({ ...p, id: `${st0.id}${k + 1}` })) : [{ beats: st0.beats, id: st0.id }];
    for (const part of parts) {
      const ops = [op, part];
      let lines = clone(op.lines || st0.lines || []);
      const patches = {};
      const stepMods = { ...mods };
      let schedule = null;
      for (const o of ops) {
        for (const [from, to] of Object.entries(o.swap || {})) for (const l of lines) {
          if (l.effects) l.effects = l.effects.map((e) => ((typeof e === "string" ? e : e.name) === from ? (typeof e === "string" ? to : { ...e, name: to }) : e));
        }
        for (const [en, p] of Object.entries(o.patch || {})) patches[en] = deepMerge(patches[en] || {}, p);
        for (const d of o.drop_effects || []) for (const l of lines) if (l.effects) l.effects = l.effects.filter((e) => (typeof e === "string" ? e : e.name) !== d);
        for (const k of o.negate || []) if (typeof stepMods[k] === "number") stepMods[k] = -stepMods[k];
        if (o.laser_schedule) schedule = o.laser_schedule;
      }
      const camera = clone(op.camera || st0.camera || null);
      if (camera && camera.alt && mods.camera_alt) camera.shot = camera.alt;
      if (camera && part !== parts[0]) { delete camera.precut_beats; }        // a split step's later parts keep the shot
      if (camera && parts.length > 1 && part !== parts[0]) camera.continue = true;
      const all = [...clone(ph.base || []), ...lines];
      const compiled = all.map((l) => compileLine(rig, l, stepMods, patches, part.id));
      // laser lines: a "levels" shape follows the step's level schedule (the same effect, with the step's patches); a
      // follower follows a named effect of the step (the same definition, with the step's overrides)
      for (const c of compiled) {
        if (c.kind !== "lasers") continue;
        const sname = schedule || c.laser.schedule;
        if (sname) {
          const fromLine = compiled.find((x) => x.kind !== "lasers" && x.effects.some((e) => e.name === sname));
          c.laser.scheduleDef = fromLine ? fromLine.effects.find((e) => e.name === sname).def : deepMerge(rig.effects[sname] || {}, patches[sname] || {});
          c.laser.schedule = sname;
        }
        if (c.laser.follow) {
          const fromLine = compiled.find((x) => x.kind !== "lasers" && x.effects.some((e) => e.name === c.laser.follow));
          c.laser.followDef = fromLine ? fromLine.effects.find((e) => e.name === c.laser.follow).def : rig.effects[c.laser.follow] || null;
        }
        c.laser.layerShift = Number(stepMods.layer_shift) || 0;
        if (rig.presets && rig.presets.layers && rig.presets.layers.target) c.laser.layers = rig.presets.layers.target;
      }
      const cues = (st0.cues || []).filter((c) => !op.split || c.at < part.beats).map((c) => ({ at: c.at, lines: c.lines.map((l) => compileLine(rig, l, stepMods, patches, part.id)) }));
      steps.push({ id: part.id, name: st0.name, beats: part.beats, trigger: st0.trigger || "follow", lines: compiled, cues, camera, mods: stepMods,
                   ambient: typeof (op.ambient ?? st0.ambient) === "number" ? (op.ambient ?? st0.ambient) : 1 });
    }
  }
  return { phrase: name, variant, mods, steps };
}

// The camera plan of a repeat from step i on: entries {shot, p0, p1} in absolute beat positions. bounds[j] is where step
// j starts and bounds[j + 1] where it ends. A step with no camera keeps the shot before it; then: {beats, shot} splits a
// step's shot; precut_beats on a step cuts to its shot that many beats before its ONE (so the cut never lands on the
// flash frame of a step that opens with a flash). Rebuilt at every step, an entry keeps its p0, so the director sees the
// same entry and does not cut again.
export function cameraPlan(steps, bounds, from = 0) {
  const out = [];
  for (let i = from; i < steps.length; i++) {
    const cam = steps[i].camera, s0 = bounds[i], s1 = bounds[i + 1];
    const nx = steps[i + 1] && steps[i + 1].camera;
    const end = s1 - (nx && !nx.continue && nx.precut_beats ? nx.precut_beats : 0);
    if (!cam || cam.continue) { if (out.length) out[out.length - 1].p1 = end; continue; }
    const begin = s0 - (cam.precut_beats || 0);
    const why = cam.precut_beats ? "precut" : "step";
    if (cam.then && s0 + cam.then.beats < end) {
      out.push({ shot: cam.shot, p0: begin, p1: s0 + cam.then.beats, why });
      out.push({ shot: cam.then.shot, p0: s0 + cam.then.beats, p1: end, why: "step" });
    } else out.push({ shot: cam.shot, p0: begin, p1: end, why });
  }
  return out;
}

// ------------------------------------------------------------------------------------------------- the runner --
export class PhraseRunner {
  constructor(rig, { seed = null } = {}) {
    this.rig = rig;
    this.seed = seed ?? rig.seed ?? 1;
    this.phrases = rig.phrases || {};
    this.decks = {};
    this.repeats = {};          // the phrase's repeat counter, kept across runs (the per-repeat values never restart)
    this.state = "idle";        // idle | armed | running
    this.pending = null;
    this.cur = null;            // {name, rep (compiled repeat), index, starts[], start, end, repeatsLeft, ...}
    this.stopAt = null;
    this.events = [];
    this.log = [];              // [{type, phrase, step, variant, repeat, pos}] bounded, for receipts
  }
  get running() { return this.state === "running"; }
  _deck(name) {
    if (!this.decks[name]) {
      const v = this.phrases[name].vary || {};
      const names = v.deck && v.deck.length ? v.deck : Object.keys(v.variants || { default: {} });
      this.decks[name] = new Deck(names, { first: v.first || null, noRepeat: v.no_repeat !== false, seed: hashSeed(this.seed, name, "deck") });
    }
    return this.decks[name];
  }
  _compileNext(name, section, force = null) {
    const ph = this.phrases[name];
    const v = ph.vary || {};
    const deck = this._deck(name);
    const ok = (vn) => { const d = (v.variants || {})[vn] || {}; return !d.sections || d.sections.includes(section); };
    if (force && !(v.variants && v.variants[force])) throw new Error(`phrase ${name}: no variant ${force}`);
    const variant = force || (v.variants ? deck.next(ok) : null);
    if (force) deck.last = force;
    const k = this.repeats[name] = (this.repeats[name] ?? -1) + 1;
    const mods = resolveMods(v.per_repeat || {}, k, hashSeed(this.seed, name));
    const rep = compileRepeat(this.rig, name, variant, mods);
    rep.repeat = k;
    return rep;
  }
  // Arm a phrase to start exactly at beat position `at` (a bar line). opts: repeats (default: until stopped), camera
  // (the phrase drives the camera), section (for the variants limited to some sections), source, variant (the first
  // repeat's, instead of the deck's deal).
  start(name, at, { repeats = Infinity, camera = true, section = "any", source = "show", variant = null } = {}) {
    if (!this.phrases[name]) throw new Error(`no phrase ${name}`);
    this.pending = { name, at, repeats, camera, section, source, variant };
    if (this.state === "idle") this.state = "armed";
    return at;
  }
  // The pad: Go arms the phrase on the next bar line (a press just after a line lands on it). Pressed while a phrase runs,
  // it deals the next repeat from the next bar line.
  go(name, grid, pos, opts = {}) {
    const at = goLine(grid, pos);
    return this.start(name || (this.cur && this.cur.name) || Object.keys(this.phrases)[0], at, { source: "pad", ...opts });
  }
  // Next: the current step ends on the next bar line (if that comes before its own end).
  next(grid, pos) {
    if (!this.cur) return null;
    const at = goLine(grid, pos);
    if (at < this.cur.end - LINE_EPS) { this.cur.end = Math.max(at, this.cur.start); this.cur.cut = true; this.cur.replan = true; }
    this.cur.goPressed = true;
    return this.cur.end;
  }
  stop(grid, pos) {
    if (this.state === "armed") { this.pending = null; this.state = "idle"; return pos; }
    if (!this.cur) return null;
    this.stopAt = goLine(grid, pos);
    return this.stopAt;
  }
  // End now at a known line (a section change that does not carry this phrase).
  stopAtPos(at) { if (this.cur) this.stopAt = at; else if (this.state === "armed") { this.pending = null; this.state = "idle"; } }
  _note(e) { if (this.log.length < 1024) this.log.push(e); }
  _beginRepeat(name, at, opts, keep = null) {
    const rep = this._compileNext(name, opts.section, keep ? null : opts.variant || null);
    const starts = [];
    let p = at;
    for (const st of rep.steps) { starts.push(p); p += st.beats; }
    starts.push(p);
    this.cur = { name, rep, index: -1, starts, start: at, end: at, repeatsLeft: keep ? keep.repeatsLeft : opts.repeats,
                 camera: opts.camera, section: opts.section, source: opts.source, firedCues: new Set(), cut: false };
    this.events.push({ type: "repeat", phrase: name, variant: rep.variant, repeat: rep.repeat, mods: rep.mods, pos: at, steps: rep.steps.map((s) => s.id) });
    this._note({ type: "repeat", phrase: name, variant: rep.variant, repeat: rep.repeat, pos: +at.toFixed(4) });
    this._enterStep(0, at);
  }
  _enterStep(i, at) {
    const c = this.cur, st = c.rep.steps[i];
    c.index = i;
    // the steps after a cut start from the actual line, keeping their own lengths
    let p = at;
    for (let j = i; j < c.rep.steps.length; j++) { c.starts[j] = p; p += c.rep.steps[j].beats; }
    c.starts[c.rep.steps.length] = p;
    c.start = at; c.end = at + st.beats; c.cut = false; c.replan = false; c.goPressed = false; c.firedCues = new Set();
    // the whole repeat's plan (past entries end in the past; an entry keeps its p0, so the director does not cut again)
    const plan = c.camera ? cameraPlan(c.rep.steps, c.starts, 0) : null;
    this.events.push({ type: "step", phrase: c.name, step: st, index: i, id: st.id, start: at, end: c.end, variant: c.rep.variant, repeat: c.rep.repeat,
                       mods: st.mods, camera: plan, last: i === c.rep.steps.length - 1 });
    this._note({ type: "step", phrase: c.name, step: st.id, variant: c.rep.variant, repeat: c.rep.repeat, pos: +at.toFixed(4) });
  }
  update(pos) {
    const ev = this.events;
    ev.length = 0;
    // an armed start (or a Go while running) lands on its line
    if (this.pending && pos >= this.pending.at - LINE_EPS) {
      const p = this.pending;
      this.pending = null;
      if (this.cur) this._note({ type: "end", phrase: this.cur.name, pos: +p.at.toFixed(4), why: "go" });
      const was = this.cur;
      try {
        this.state = "running";
        this.stopAt = null;
        ev.push({ type: "start", phrase: p.name, pos: p.at, source: p.source });
        this._beginRepeat(p.name, p.at, p);
      } catch (e) {
        // a phrase that cannot compile never leaves the runner half-started: the old one ends, the error is an event
        ev.length = 0;
        if (was) ev.push({ type: "end", phrase: was.name, pos: p.at, why: "error" });
        ev.push({ type: "error", phrase: p.name, pos: p.at, message: e.message });
        this._note({ type: "error", phrase: p.name, pos: +p.at.toFixed(4), message: e.message });
        this.cur = null; this.state = "idle";
      }
    }
    for (let guard = 0; guard < 64 && this.cur; guard++) {
      const c = this.cur;
      if (this.stopAt !== null && pos >= this.stopAt - LINE_EPS) {
        ev.push({ type: "end", phrase: c.name, pos: this.stopAt, why: "stop" });
        this._note({ type: "end", phrase: c.name, pos: +this.stopAt.toFixed(4), why: "stop" });
        this.cur = null; this.stopAt = null; this.state = this.pending ? "armed" : "idle";
        break;
      }
      const st = c.rep.steps[c.index];
      if (c.replan) {
        // Next cut the step short: the steps after it move up, and the camera plan with them
        c.replan = false;
        let p = c.end;
        for (let j = c.index + 1; j < c.rep.steps.length; j++) { c.starts[j] = p; p += c.rep.steps[j].beats; }
        c.starts[c.index + 1] = c.end; c.starts[c.rep.steps.length] = p;
        if (c.camera) ev.push({ type: "camera", phrase: c.name, camera: cameraPlan(c.rep.steps, c.starts, 0), pos });
      }
      for (const [j, cue] of (st.cues || []).entries()) {
        const at = c.start + cue.at;
        if (!c.firedCues.has(j) && pos >= at - LINE_EPS && at < c.end - LINE_EPS) {
          c.firedCues.add(j);
          ev.push({ type: "cue", phrase: c.name, step: st.id, cue: j, lines: cue.lines, pos: at });
        }
      }
      // a "go" step holds until Next is pressed (it then ends on the next bar line)
      const held = st.trigger === "go" && !c.goPressed;
      if (held && pos >= c.end - LINE_EPS) c.end += 4;
      if (pos < c.end - LINE_EPS) break;
      const at = c.end;
      if (c.index + 1 < c.rep.steps.length) { this._enterStep(c.index + 1, at); continue; }
      // the repeat is done: loop (the next variant from the deck) or end
      const left = c.repeatsLeft - 1;
      if (left > 0) { c.repeatsLeft = left; this._beginRepeat(c.name, at, c, c); continue; }
      ev.push({ type: "end", phrase: c.name, pos: at, why: "done" });
      this._note({ type: "end", phrase: c.name, pos: +at.toFixed(4), why: "done" });
      this.cur = null; this.state = this.pending ? "armed" : "idle";
      break;
    }
    return ev;
  }
  // The lines the next repeat of a phrase will open with (its base and first step, the deck untouched), for the pre-roll:
  // heads that are dark move to the phrase's positions before it starts (move in black).
  prepareLines(name) {
    const ph = this.phrases[name];
    if (!ph) return [];
    const mods = resolveMods((ph.vary && ph.vary.per_repeat) || {}, (this.repeats[name] ?? -1) + 1, hashSeed(this.seed, name));
    try { return compileRepeat(this.rig, name, null, mods).steps[0].lines; } catch { return []; }
  }
  status() {
    const c = this.cur;
    if (!c) return { state: this.state, pending: this.pending ? { phrase: this.pending.name, at: this.pending.at } : null };
    const st = c.rep.steps[c.index];
    return { state: this.state, phrase: c.name, name: this.phrases[c.name].name || c.name, step: st.id, stepName: st.name, index: c.index,
             steps: c.rep.steps.length, start: c.start, end: c.end, variant: c.rep.variant, repeat: c.rep.repeat, repeatsLeft: c.repeatsLeft };
  }
}

// The bar line a Go lands on: the next one, or the one just passed if the press came within the grace.
export function goLine(grid, pos) {
  const prev = grid.nextBarPos(pos) - 4;
  return pos - prev < GO_GRACE_BEATS ? prev : grid.nextBarPos(pos);
}

// Unused here but exported for the renderer-free checks: the world direction a position preset gives a head (its beam
// axis from the pivot), so a receipt can see where the layers cross the crowd.
export function presetDirection(rig, group, positions, m) {
  const fi = group.memberFixture[m], f = rig.fixtures[fi], el = rig.elements[f.element];
  const em = elementMatrix(el);
  const body = eulerToMat3(f.rot);
  const pa = positions[m * 2] * DEG, ti = positions[m * 2 + 1] * DEG;
  const dirB = [Math.sin(ti) * Math.sin(pa), Math.cos(ti), Math.sin(ti) * Math.cos(pa)];
  const e = mat3MulVec(body, dirB);
  return [em[0] * e[0] + em[1] * e[1] + em[2] * e[2], em[3] * e[0] + em[4] * e[1] + em[5] * e[2], em[6] * e[0] + em[7] * e[1] + em[8] * e[2]];
}

// Play one frame's phrase events onto the rig: a step replaces the phrase layer (programmer.setOverlay), the laser group
// lines (the section's laser look is muted while a phrase owns the lasers) and the camera plan; a cue merges into them;
// the end hands everything back (the look over `releaseBeats`, the section's laser look, the section's camera through
// onEnd). Returns the steps entered, for the HUD and the receipts.
export function playPhraseEvents(events, { programmer, lasers = null, director = null, releaseBeats = 1, onEnd = null, manualCamera = () => false } = {}) {
  const entered = [];
  for (const e of events) {
    if (e.type === "step") {
      programmer.setOverlay(e.step.lines, e.start);
      if (lasers) { lasers.setGroupLines(e.step.lines.filter((l) => l.kind === "lasers"), e.start); lasers.setLookMute(true); }
      if (director && e.camera && e.camera.length && !manualCamera()) director.plan(e.camera);
      entered.push(e);
    } else if (e.type === "cue") {
      programmer.setOverlay(e.lines, e.pos, { replace: false });
      if (lasers) lasers.setGroupLines(e.lines.filter((l) => l.kind === "lasers"), e.pos, { replace: false });
    } else if (e.type === "camera") {
      if (director && e.camera && e.camera.length && !manualCamera()) director.plan(e.camera);
    } else if (e.type === "end") {
      programmer.clearOverlay(e.pos, releaseBeats);
      if (lasers) { lasers.clearGroups(); lasers.setLookMute(false); }
      if (director) director.plan(null);
      if (onEnd) onEnd(e);
    }
  }
  return entered;
}
