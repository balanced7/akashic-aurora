// Node tests for the param schema's browser twin (arsenal/web/lib/params.js) and its generated controls
// (arsenal/web/lib/params-ui.js). Zero dependencies:  node tests/params_schema.test.mjs
//
// Why this file exists: one descriptor has to describe a knob everywhere it appears (the GLSL uniform, the slider, the
// URL, the preset, the MIDI range), and the Python twin (arsenal/params.py, tests/test_params_schema.py) must reach the
// same verdict on the same input, or a preset saved by one side is refused or silently changed by the other. Every
// verdict here comes from tests/fixtures/params/verdicts.json, which the Python test reads too.
//
// The controls are checked with a small fake document (no jsdom, no browser), the way tests/piano_looks_registry.test.mjs
// checks the looks registry with a fake page: params-ui takes the document as an argument for exactly this reason.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import {
  REC_REFUSAL_TEXT, checkDescriptors, decode, encode, formatParts, formatValue, fromLooksDescriptor, fromUrl,
  linearToOklch, oklchToLinear, paramsFromModule, positionToValue, validate, validateValue, valueToPosition,
} from "../arsenal/web/lib/params.js";
import { renderParams } from "../arsenal/web/lib/params-ui.js";
import { LOOK_GROUPS, LOOK_SETTINGS, REC_BLOCKED, validateValue as lookValidate } from "../arsenal/web/piano/looks/registry.js";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
let pass = 0, fail = 0;
function check(label, ok, detail = "") {
  if (ok) { pass++; return; }
  fail++;
  console.log(`FAIL ${label}${detail ? ": " + detail : ""}`);
}
// Strict equality: numbers by Object.is after the twins' own -0 rule (both must hand back +0), objects by sorted keys.
function same(a, b) {
  if (typeof a === "number" && typeof b === "number") return Object.is(a, b) || (Number.isNaN(a) && Number.isNaN(b));
  if (Array.isArray(a) || Array.isArray(b)) {
    return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((x, i) => same(x, b[i]));
  }
  if (a && b && typeof a === "object" && typeof b === "object") {
    const ka = Object.keys(a).sort(), kb = Object.keys(b).sort();
    return same(ka, kb) && ka.every((k) => same(a[k], b[k]));
  }
  return a === b;
}
const show = (v) => JSON.stringify(v, (k, x) => (typeof x === "number" && !Number.isFinite(x) ? String(x) : x));
const eq = (label, got, want) => check(label, same(got, want), `got ${show(got)} want ${show(want)}`);

// The fixture spells NaN and the infinities as strings; swap them in.
const SENTINEL = { __NaN__: NaN, __Inf__: Infinity, "__-Inf__": -Infinity };
function revive(v) {
  if (typeof v === "string" && v in SENTINEL) return SENTINEL[v];
  if (Array.isArray(v)) return v.map(revive);
  if (v && typeof v === "object") return Object.fromEntries(Object.entries(v).map(([k, x]) => [k, revive(x)]));
  return v;
}

const D = JSON.parse(readFileSync(here("./fixtures/params/descriptors.json"), "utf8"));
const V = JSON.parse(readFileSync(here("./fixtures/params/verdicts.json"), "utf8"));
const sets = D.sets;
const byId = (set, id) => sets[set].find((d) => d.id === id);
const pairs = (problems) => problems.map((p) => [p.id, p.code]);

// ------------------------------------------------------------------------------------------------ validate --
for (const c of V.validate) {
  const r = validate(sets[c.set], revive(c.values));
  eq(`validate "${c.name}": ok`, r.ok, c.ok);
  eq(`validate "${c.name}": values`, r.values, revive({ ...V.defaults[c.set], ...c.patch }));
  eq(`validate "${c.name}": problems`, pairs(r.problems), c.problems);
  check(`validate "${c.name}": every problem says why`, r.problems.every((p) => typeof p.message === "string" && p.message.length > 0));
}
for (const c of V.messages) {
  const r = validate(sets[c.set], revive(c.values));
  eq(`message for ${show(c.values)}`, r.problems.map((p) => [p.id, p.code, p.message]), c.problems);
}
check("validate leaves its input alone", (() => {
  const input = { intensity: 5, offset: [3, -3] };
  validate(sets.core, input);
  return same(input, { intensity: 5, offset: [3, -3] });
})());
{
  const one = validateValue(byId("core", "intensity"), 0.333);
  eq("validateValue snaps one value", one.value, 0.33);
  eq("validateValue reports no problem for a snap", one.problem, null);
  const bad = validateValue(byId("core", "rays"), "yes");
  check("validateValue refuses a bad toggle with the default", bad.value === true && bad.problem && bad.problem.code === "type");
}

// --------------------------------------------------------------------------------------------- URL codec --
for (const c of V.encode) {
  eq(`encode ${show(c.values)} all=${c.all}`, encode(sets[c.set], revive(c.values), { all: c.all }), c.query);
}
for (const c of V.decode) {
  eq(`decode "${c.query}"`, decode(sets[c.set], c.query), revive(c.values));
  if (c.verdict) {
    const r = fromUrl(sets[c.set], c.query);
    eq(`fromUrl "${c.query}": ok`, r.ok, c.verdict.ok);
    eq(`fromUrl "${c.query}": problems`, pairs(r.problems), c.verdict.problems);
  }
}
eq("decode reads a URLSearchParams too", decode(sets.core, new URLSearchParams("intensity=1.5&tint=0.18,0.18,0.18")),
  { intensity: 1.5, tint: [0.18, 0.18, 0.18] });
for (const c of V.roundtrip) {
  const want = validate(sets[c.set], revive(c.values)).values;
  const q = encode(sets[c.set], revive(c.values));
  eq(`round trip ${show(c.values)} via "${q}"`, fromUrl(sets[c.set], q).values, want);
  eq(`round trip ${show(c.values)} with every value`, fromUrl(sets[c.set], encode(sets[c.set], revive(c.values), { all: true })).values, want);
}

// ------------------------------------------------------------------------------------------- formatter --
for (const [set, id, value, text, unit, joined] of V.format) {
  const d = byId(set, id);
  eq(`format ${id} ${show(value)} parts`, formatParts(d, revive(value)), { text, unit });
  eq(`format ${id} ${show(value)}`, formatValue(d, revive(value)), joined);
}

// ---------------------------------------------------------------------------------------- slider curves --
{
  const tol = V.curves.tolerance;
  for (const [set, id, p, v] of V.curves.to_value) {
    const got = positionToValue(byId(set, id), p);
    check(`position ${p} -> ${id}`, Math.abs(got - v) <= tol * Math.max(1, Math.abs(v)), `got ${got} want ${v}`);
  }
  for (const [set, id, v, p] of V.curves.to_position) {
    const got = valueToPosition(byId(set, id), v);
    check(`${id} ${v} -> position`, Math.abs(got - p) <= tol, `got ${got} want ${p}`);
  }
  for (const d of sets.units.filter((x) => x.type === "range")) {
    let worst = 0;
    for (let i = 0; i <= 20; i++) worst = Math.max(worst, Math.abs(valueToPosition(d, positionToValue(d, i / 20)) - i / 20));
    check(`curve round trip for ${d.id}`, worst < 1e-9, String(worst));
  }
}

// ------------------------------------------------------------------------------------ descriptor checks --
for (const c of V.check) {
  eq(`checkDescriptors "${c.name}"`, pairs(checkDescriptors(c.set ? sets[c.set] : c.descriptors)), c.problems);
}
// Expressions far past the token cap, built the same way in tests/test_params_schema.py: the Python twin used to recurse
// until it crashed on these, so both twins must refuse them as a problem instead.
for (const [name, expr] of [["1200 minus signs", "-".repeat(1200) + "a"], ["a 2000-term sum", "a" + "+a".repeat(1999)]]) {
  const set = [sets.deep[0], { ...sets.deep[1], derived: expr }];
  eq(`${name}: validate names the derived problem`, pairs(validate(set, {}).problems), [["atCap", "derived"]]);
  eq(`${name}: checkDescriptors refuses it`, pairs(checkDescriptors(set)), [["atCap", "derived"]]);
}

// ---------------------------------------------------------------------------------- params from a module --
for (const c of V.modules) {
  const header = D.headers[c.header];
  const list = paramsFromModule(header, c.instance);
  const tag = `${c.header}@${c.instance}`;
  if (c.rows) eq(`paramsFromModule ${tag} rows`, list.map((d) => [d.id, d.uniform, d.type, d.unit, d.group, d.order, d.cost]), c.rows);
  if (c.full) eq(`paramsFromModule ${tag} descriptors`, list, c.full);
  if (c.derived) {
    eq(`paramsFromModule ${tag} derived`, Object.fromEntries(list.filter((d) => d.derived).map((d) => [d.id, d.derived])), c.derived);
  }
  eq(`paramsFromModule ${tag} passes the descriptor check`, pairs(checkDescriptors(list)), []);
  eq(`paramsFromModule ${tag} is deterministic`, paramsFromModule(header, c.instance), list);
  if (c.validate) {
    const r = validate(list, c.validate.values);
    eq(`paramsFromModule ${tag} validates`, [r.ok, r.values], [c.validate.ok, c.validate.expect]);
  }
}
for (const [name, inst] of V.module_errors) {
  let threw = false;
  try { paramsFromModule(D.headers[name], inst); } catch { threw = true; }
  check(`paramsFromModule refuses the instance id "${inst}"`, threw);
}
for (const c of V.module_checks) {
  eq(`paramsFromModule then checkDescriptors: ${c.name}`, pairs(checkDescriptors(paramsFromModule(c.header, c.instance))), c.problems);
}
for (const c of V.module_bad_headers) {
  for (const inst of [null, "a"]) {
    let err = null;
    try { paramsFromModule(c.header, inst); } catch (e) { err = e; }
    check(`paramsFromModule refuses ${c.name} (instance ${inst})`, err instanceof TypeError, String(err));
  }
}
{
  const a = paramsFromModule(D.headers["aurora-sheets"], "a").map((d) => d.uniform);
  const b = paramsFromModule(D.headers["aurora-sheets"], "b").map((d) => d.uniform);
  check("two instances never share a uniform (the parameter-bus leak)", a.every((u) => !b.includes(u)));
  const declared = paramsFromModule({ name: "x", params: [{ name: "gain", unit: "ratio", range: [0, 2], default: 1, uniform: "u_gain" }] }, null);
  eq("a single instance keeps a uniform its header declares", declared[0].uniform, "u_gain");
  const ns = paramsFromModule({ name: "x", params: [{ name: "gain", unit: "ratio", range: [0, 2], default: 1, uniform: "u_gain" }] }, "two");
  eq("an instance namespaces it anyway", ns[0].uniform, "u_two_gain");
}

// -------------------------------------------------------------------------------------- colour (OKLCH) --
{
  let worst = 0;
  for (const c of [[1, 1, 1], [0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [0.18, 0.18, 0.18], [0.5, 0.25, 0.125], [0.02, 0.6, 0.9]]) {
    const [L, C, h] = linearToOklch(c);
    const back = oklchToLinear([L, C, h]);
    worst = Math.max(worst, ...back.map((x, i) => Math.abs(x - c[i])));
  }
  check("OKLCH round trip under 1e-6 in gamut", worst < 1e-6, String(worst));
  const [Lw, Cw] = linearToOklch([1, 1, 1]);
  check("white is L 1, chroma 0", Math.abs(Lw - 1) < 1e-4 && Cw < 1e-4, `${Lw} ${Cw}`);
}

// ------------------------------------------------------------------------------ the looks registry adapter --
{
  const A = { scheme: "classic", instrument: "page", enabled: true, theme: "moon", weather: "world", harmonyMode: "tonnetz",
    intensity: 0.85, motion: 1, journey: 0, harmony: true, waveform: true, autoWorld: false, labels: "harmony",
    colour: "pitch", nns: "chord", framing: "9:16", quality: "studio" };
  const looks = LOOK_SETTINGS.map((d) => fromLooksDescriptor(d, { default: A[d.id] }));
  eq("every look setting adapts", looks.map((d) => d.id), LOOK_SETTINGS.map((d) => d.id));
  eq("the adapted looks pass the descriptor check", pairs(checkDescriptors(looks)), []);
  const r = validate(looks, A);
  check("a whole look validates under the schema", r.ok && same(r.values, A), show(r));
  // The registry's step is its slider's step, never a grid it enforces (it accepts 0.87), so the schema must not snap to it.
  eq("ranges keep their bounds, without the registry's slider step", looks.find((d) => d.id === "intensity").range,
    { min: 0.25, max: 1.4, step: null });
  eq("look ranges are ratios", looks.filter((d) => d.type === "range").map((d) => d.unit), ["ratio", "ratio", "ratio"]);
  eq("render quality is marked as a cost", looks.filter((d) => d.cost).map((d) => d.id), ["quality"]);
  eq("recording locks carry over", looks.filter((d) => d.recBlocked).map((d) => d.id),
    LOOK_SETTINGS.filter((d) => d.recBlocked).map((d) => d.id));
  eq("the refusal text is the house text", REC_REFUSAL_TEXT, REC_BLOCKED);
  const bare = fromLooksDescriptor(LOOK_SETTINGS.find((d) => d.id === "framing"));
  eq("without a page default a choice starts on its first value", bare.default, "9:16");
  // The schema and the registry agree on what is a legal value (scheme and instrument are excluded: the registry also
  // accepts ids the page lists at run time, which a static descriptor cannot know), and a value both accept comes back
  // unchanged: a look the registry takes as it is must not be quietly moved by the schema (off-grid probes such as 0.87
  // sit between the registry's 0.05 slider steps).
  let disagree = [];
  for (const d of LOOK_SETTINGS) {
    if (d.id === "scheme" || d.id === "instrument") continue;
    const probes = [true, false, "nonsense", -1, 0, 0.5, 0.85, 0.87, 0.333, 0.42, 1.12, 1, 1.4, 99, "", null, [1],
      ...(d.values || []).map((o) => o.value), ...(d.range ? [d.range.min, d.range.max, d.range.min - 0.01, d.range.max + 0.01] : [])];
    const adapted = looks.find((x) => x.id === d.id);
    for (const v of probes) {
      const r = validate([adapted], { [d.id]: v });
      const registryOk = lookValidate(d.id, v) === null;
      if (r.ok !== registryOk) disagree.push(`${d.id}=${show(v)} schema ${r.ok} registry ${registryOk}`);
      else if (r.ok && !same(r.values[d.id], v)) disagree.push(`${d.id}=${show(v)} accepted but rewritten to ${show(r.values[d.id])}`);
    }
  }
  eq("schema and registry agree on every probe, values included", disagree, []);
}

// ------------------------------------------------------------------------------------- generated controls --
// A fake document: just enough of the DOM for params-ui (createElement, appendChild, attributes, dataset, listeners,
// focus and blur). Walking the tree replaces querySelector.
class FakeEl {
  constructor(doc, tag) {
    Object.assign(this, { ownerDocument: doc, tagName: tag.toUpperCase(), children: [], parentNode: null, attributes: {},
      dataset: {}, style: {}, className: "", textContent: "", hidden: false, disabled: false, value: "", title: "", type: "",
      listeners: {} });
  }
  appendChild(c) { c.parentNode = this; this.children.push(c); return c; }
  append(...cs) { for (const c of cs) this.appendChild(typeof c === "string" ? Object.assign(new FakeEl(this.ownerDocument, "#text"), { textContent: c }) : c); }
  setAttribute(k, v) { this.attributes[k] = String(v); }
  getAttribute(k) { return k in this.attributes ? this.attributes[k] : null; }
  removeAttribute(k) { delete this.attributes[k]; }
  addEventListener(t, fn) { (this.listeners[t] ||= []).push(fn); }
  removeEventListener(t, fn) { this.listeners[t] = (this.listeners[t] || []).filter((f) => f !== fn); }
  fire(type, props = {}) {
    const e = { type, target: this, currentTarget: this, detail: 0, defaultPrevented: false,
      preventDefault() { this.defaultPrevented = true; }, stopPropagation() {}, ...props };
    for (const fn of [...(this.listeners[type] || [])]) fn(e);
    return e;
  }
  focus() { this.ownerDocument.activeElement = this; }
  blur() { if (this.ownerDocument.activeElement === this) this.ownerDocument.activeElement = this.ownerDocument.body; }
}
function fakeDocument() {
  const doc = { createElement: (t) => new FakeEl(doc, t), activeElement: null };
  doc.body = new FakeEl(doc, "body");
  doc.activeElement = doc.body;
  return doc;
}
function* walk(el) { yield el; for (const c of el.children) yield* walk(c); }
const find = (root, pred) => { for (const el of walk(root)) if (pred(el)) return el; return null; };
const findAll = (root, pred) => [...walk(root)].filter(pred);
const hasClass = (el, c) => (" " + el.className + " ").includes(" " + c + " ");

{
  const doc = fakeDocument();
  const aurora = paramsFromModule(D.headers["aurora-sheets"], null);
  const finish = paramsFromModule(D.headers["display-out"], "fin");
  const demo = paramsFromModule(D.headers["twin-demo"], null);
  const changes = [];
  const ui = renderParams(doc, [...aurora, ...finish, ...demo], {
    onChange: (id, value, values) => changes.push([id, value, values]),
    groups: [{ id: "light", label: "Light" }],
  });
  check("renderParams returns a root element", ui.root && ui.root.tagName === "DIV");
  doc.body.appendChild(ui.root);

  const sections = findAll(ui.root, (el) => el.tagName === "SECTION");
  eq("one section per group, in order of appearance", sections.map((s) => s.dataset.group), ["light", "shape", "quality", "fin.finish", "params"]);
  eq("group headings use given labels, else plain words", sections.map((s) => find(s, (el) => el.tagName === "H3").textContent),
    ["Light", "Shape", "Quality", "Fin · Finish", "Params"]);

  const row = (id) => ui.rows.get(id);
  check("every descriptor has a row", [...aurora, ...finish, ...demo].every((d) => row(d.id) && row(d.id).row.dataset.param === d.id));
  for (const d of [...aurora, ...finish, ...demo].filter((x) => x.type === "range" || x.type === "vec")) {
    const r = row(d.id);
    check(`${d.id}: the unit sits beside the number`, r.unit && r.unit.dataset.unit === d.unit && r.output && r.output.parentNode === r.unit.parentNode,
      r.unit && r.unit.dataset.unit);
  }
  const intensity = row("intensity");
  eq("intensity is a slider with the header's range", [intensity.input.type, intensity.input.min, intensity.input.max, intensity.input.step, intensity.input.value],
    ["range", "0", "2", "0.01", "1"]);
  eq("intensity shows its value and unit", [intensity.output.textContent, intensity.unit.textContent], ["1.00", "×"]);
  eq("hemHeight has no step, so the slider is free", row("hemHeight").input.step, "any");
  eq("hemHeight is in scene units", row("hemHeight").unit.textContent, "units");
  eq("layers steps by one", row("layers").input.step, "1");
  check("layers carries a cost badge", row("layers").badge && !row("layers").badge.hidden && /cost/i.test(row("layers").badge.textContent));
  check("intensity has no cost badge", !row("intensity").badge || row("intensity").badge.hidden);
  eq("exposure: range and unit", [row("fin.ev").input.min, row("fin.ev").input.max, row("fin.ev").output.textContent, row("fin.ev").unit.textContent],
    ["-4", "4", "0.0", "stops"]);
  eq("exposure explains itself on hover", row("fin.ev").label.title, "Brightness before the display curve, in doublings of light.");
  const curve = row("fin.curve");
  eq("display curve is a select of its choices", [curve.input.tagName, curve.input.children.map((o) => o.textContent)],
    ["SELECT", ["Soft (tanh)", "Exponential", "ACES fit", "PBR Neutral"]]);
  const dither = row("fin.ditherLevels");
  eq("a log curve drives the slider by position", [dither.input.min, dither.input.max, dither.input.step, dither.row.dataset.curve],
    ["0", "1000", "1", "log"]);
  eq("... starting at the default's position", dither.input.value, String(Math.round(valueToPosition(dither.d, 255) * 1000)));

  // input: a value change reaches onChange typed and snapped; the readout follows
  intensity.input.value = "1.5";
  intensity.input.fire("input");
  eq("moving intensity reports 1.5", changes.at(-1).slice(0, 2), ["intensity", 1.5]);
  eq("... and the readout follows", intensity.output.textContent, "1.50");
  eq("... and values() holds it", ui.values().intensity, 1.5);
  dither.input.value = "1000";
  dither.input.fire("input");
  eq("the far end of a log slider is the maximum", changes.at(-1).slice(0, 2), ["fin.ditherLevels", 1024]);
  curve.input.value = "2";
  curve.input.fire("change");
  eq("a numeric choice reports its number", changes.at(-1).slice(0, 2), ["fin.curve", 2]);

  // reset to default, per control
  check("every live control has a reset", [...ui.rows.values()].filter((x) => !x.d.derived).every((x) => x.reset && x.reset.tagName === "BUTTON"));
  intensity.reset.fire("click", { detail: 1 });
  eq("reset puts intensity back to its default", [changes.at(-1).slice(0, 2), intensity.input.value, intensity.output.textContent],
    [["intensity", 1], "1", "1.00"]);
  const before = changes.length;
  intensity.reset.fire("click", { detail: 1 });
  check("reset at the default changes nothing", changes.length === before);

  // blur after a pointer, so letter keys go back to the note keyboard; keyboard use keeps focus
  intensity.input.focus();
  intensity.input.fire("pointerdown");
  intensity.input.value = "0.5";
  intensity.input.fire("input");
  intensity.input.fire("change");
  check("a pointer drag ends with the slider blurred", doc.activeElement !== intensity.input);
  intensity.input.focus();
  intensity.input.value = "0.6";
  intensity.input.fire("input");
  intensity.input.fire("change");
  check("a keyboard change keeps focus", doc.activeElement === intensity.input);
  const on = row("on");
  on.input.focus();
  on.input.fire("click", { detail: 1 });
  eq("a pointer click flips the toggle", [changes.at(-1).slice(0, 2), on.input.getAttribute("aria-checked"), on.input.textContent], [["on", false], "false", "Off"]);
  check("... and blurs it", doc.activeElement !== on.input);
  on.input.focus();
  on.input.fire("click", { detail: 0 });
  check("a keyboard press keeps focus on the toggle", doc.activeElement === on.input && ui.values().on === true);
  curve.input.focus();
  curve.input.fire("pointerdown");
  curve.input.value = "1";
  curve.input.fire("change");
  check("a pointer pick blurs the select", doc.activeElement !== curve.input);
  // A click that changes nothing fires no change event, so the pointer flag must not outlive it: the next keyboard
  // change keeps focus. This is the whole sequence a browser sends: the click is released before the key goes down.
  intensity.input.focus();
  intensity.input.fire("pointerdown");
  intensity.input.fire("pointerup");
  intensity.input.fire("click", { detail: 1 });
  intensity.input.fire("keydown", { key: "ArrowRight" });
  intensity.input.value = "0.61";
  intensity.input.fire("input");
  intensity.input.fire("change");
  intensity.input.fire("keyup", { key: "ArrowRight" });
  check("a keyboard change after a still click keeps focus", doc.activeElement === intensity.input);
  // A key that goes down while the pointer is still down (a key pressed mid-drag, or a held note key auto-repeating onto
  // the slider pointerdown just focused) must not cancel the blur: the drag still gives the keyboard back to the notes.
  for (const [name, seq] of [
    ["the review's sequence", ["pointerdown", ["keydown", { key: "a", repeat: true }], "input", "change"]],
    ["a key mid-drag, released before the change", ["pointerdown", "input", ["keydown", { key: "a" }], "input", "pointerup", "change"]],
  ]) {
    intensity.input.focus();
    let v = 0.7;
    for (const step of seq) {
      const [type, props] = Array.isArray(step) ? step : [step, {}];
      if (type === "input") intensity.input.value = (v += 0.01).toFixed(2);
      intensity.input.fire(type, props);
    }
    check(`a key during a drag does not keep focus on the slider (${name})`, doc.activeElement !== intensity.input);
  }
  intensity.input.focus();
  intensity.input.value = "0.62";
  intensity.input.fire("keydown", { key: "ArrowRight" });
  intensity.input.fire("input");
  intensity.input.fire("change");
  check("... and the keyboard change after that drag keeps focus", doc.activeElement === intensity.input);

  // recording: recBlocked controls are dead and say why; the rest stay live
  ui.setRecording(true);
  eq("recording disables a recBlocked control and its reset", [on.input.disabled, on.reset.disabled, on.row.dataset.locked], [true, true, "true"]);
  eq("... with the house refusal text showing", [on.refusal.hidden, on.refusal.textContent], [false, REC_BLOCKED]);
  eq("other controls stay live", [intensity.input.disabled, intensity.row.dataset.locked], [false, "false"]);
  const n = changes.length;
  on.input.fire("click", { detail: 1 });
  check("a locked control ignores a click", changes.length === n && ui.values().on === true);
  on.reset.fire("click", { detail: 1 });
  check("a locked reset ignores a click", changes.length === n);
  ui.setRecording(false);
  eq("stopping the recording brings it back", [on.input.disabled, on.refusal.hidden, on.row.dataset.locked], [false, true, "false"]);

  // derived params are shown, never set
  const dbl = row("doubleFold");
  check("a derived param has a readout and no control", !dbl.input && dbl.row.dataset.derived === "true" && dbl.output);
  const fold = row("fold");
  fold.input.value = "0.3";
  fold.input.fire("input");
  eq("a derived readout follows its sources", dbl.output.textContent, "0.90");
  eq("... and values() carries the derived value", ui.values().doubleFold, 0.9);

  // vectors: one slider per component
  const warp = row("warp");
  eq("a vec gets one slider per component, each with the range", warp.inputs.map((i) => [i.min, i.max, i.step]),
    [["-1", "1", "0.05"], ["-1", "1", "0.05"], ["-1", "1", "0.05"]]);
  warp.inputs[1].value = "0.5";
  warp.inputs[1].fire("input");
  eq("moving one component reports the whole vector", changes.at(-1).slice(0, 2), ["warp", [0, 0.5, 0]]);

  // colour: picked in OKLCH, stored as linear light
  const tint = row("tint");
  eq("a colour is picked with lightness, chroma and hue", tint.inputs.map((i) => i.dataset.axis), ["L", "C", "h"]);
  eq("its swatch shows the colour", tint.swatch.style.background, formatValue(tint.d, [1, 0.9, 0.8]));
  tint.inputs[0].value = String(+tint.inputs[0].value * 0.5);
  tint.inputs[0].fire("input");
  const picked = changes.at(-1);
  check("moving lightness reports a linear colour in range", picked[0] === "tint" && picked[1].length === 3
    && picked[1].every((c) => c >= 0 && c <= 1) && picked[1][0] < 1, show(picked));

  // setValues from outside (a preset) repaints without calling onChange
  const m = changes.length;
  const res = ui.setValues({ intensity: 1.25, "fin.ev": 9 });
  check("setValues does not call onChange", changes.length === m);
  eq("setValues repaints and reports problems", [intensity.input.value, row("fin.ev").output.textContent, res.problems.map((p) => [p.id, p.code])],
    ["1.25", "+4.0", [["fin.ev", "range"]]]);
}
{
  // A range input in a browser clamps what it is given to [min, max] and snaps it to its step grid from min. This fake
  // does the same, so the colour picker is checked against the sliders it will really have.
  class BrowserEl extends FakeEl {
    get value() { return this._value ?? ""; }
    set value(x) {
      if (this.tagName !== "INPUT" || this.type !== "range" || this.min === undefined || this.max === undefined) { this._value = String(x); return; }
      const lo = Number(this.min), hi = Number(this.max), step = this.step === "any" ? null : Number(this.step);
      let n = Math.min(Math.max(Number(x), lo), hi);
      if (step) {
        const dec = Math.max(...[this.step, this.min].map((t) => (String(t).split(".")[1] || "").length));
        n = Number((lo + Math.round((n - lo) / step) * step).toFixed(dec));
        if (n > hi) n = Number((lo + Math.floor((hi - lo) / step) * step).toFixed(dec));
      }
      this._value = String(n);
    }
  }
  const doc = { createElement: (t) => new BrowserEl(doc, t), activeElement: null };
  doc.body = new BrowserEl(doc, "body");
  const changes = [];
  const descs = [
    { id: "hot", label: "Hot", type: "colour", range: { min: 0, max: 4 }, default: [3, 2, 1] },
    { id: "tint", label: "Tint", type: "colour", default: [1, 0.5, 0.25] },
  ];
  eq("an HDR colour range passes the descriptor check", pairs(checkDescriptors(descs)), []);
  const ui = renderParams(doc, descs, { onChange: (id, v) => changes.push([id, v]) });
  for (const id of ["hot", "tint"]) {
    const rec = ui.rows.get(id);
    for (const s of rec.inputs) {
      s.value = s.value;   // touch an axis without moving it
      s.fire("input");
      s.fire("change");
      eq(`${id}: touching ${s.dataset.axis} without moving it changes nothing`, [changes.length, ui.values()[id]],
        [0, descs.find((d) => d.id === id).default]);
    }
  }
  const hot = ui.rows.get("hot");
  check("the lightness slider reaches the brightest legal colour", Number(hot.inputs[0].max) >= linearToOklch([4, 4, 4])[0],
    hot.inputs[0].max);
  hot.inputs[0].value = hot.inputs[0].max;
  hot.inputs[0].fire("input");
  check("... and moving it there gives a colour brighter than 1", changes.length === 1 && Math.max(...changes[0][1]) > 1,
    show(changes));
  eq("a colour in 0..1 keeps the 0..1 lightness slider", [ui.rows.get("tint").inputs[0].min, ui.rows.get("tint").inputs[0].max], ["0", "1"]);
}
{
  // The looks registry's settings render through the same controls (the Studio is not changed).
  const doc = fakeDocument();
  const looks = LOOK_SETTINGS.map((d) => fromLooksDescriptor(d));
  const ui = renderParams(doc, looks, { groups: LOOK_GROUPS });
  eq("looks render in the registry's groups", findAll(ui.root, (el) => el.tagName === "SECTION").map((s) => s.dataset.group),
    LOOK_GROUPS.map((g) => g.id));
  eq("... under the registry's labels", findAll(ui.root, (el) => el.tagName === "H3").map((h) => h.textContent), LOOK_GROUPS.map((g) => g.label));
  check("the switches are switches", ui.rows.get("harmony").input.getAttribute("role") === "switch");
}

console.log(`${pass} passed, ${fail} failed`);
process.exit(fail ? 1 : 0);
