// The param schema: one descriptor per knob, so the GLSL uniform, the slider, the URL, the preset and the readout all
// come from the same object instead of three hand-kept copies (Gyre used to describe each parameter in HTML attributes,
// in validator ranges and in a URL parser that read the HTML back). It generalises the looks registry's descriptor
// (arsenal/web/piano/looks/registry.js), so a module param and a look setting are the same kind of thing.
//
// Twin: arsenal/params.py implements the same validate, URL codec, formatter, curves, descriptor check and
// paramsFromModule. Both are pinned by tests/fixtures/params/verdicts.json (tests/params_schema.test.mjs and
// tests/test_params_schema.py), so a preset saved by one side means the same thing to the other. Change a rule here and
// the same rule there, or the fixture goes red.
//
// The descriptor:
//   { id, group, label, type: "range" | "choice" | "toggle" | "colour" | "vec",
//     unit, range: {min, max, step}, default, curve: "linear" | "log" | "exp", values: [{value, label}] (choices),
//     help, recBlocked, order, uniform, derived (an expression of other params), cost (true if it changes GPU cost),
//     source: {module, param, instance} }
// Optional fields may be left out of a hand-written descriptor; normalizeDescriptor fills them.
//
// The rules both twins keep (the fixture holds them to it):
//   - Numbers snap to the step grid counted from min, rounding half up; without a step they keep 6 decimals, or as many
//     as min and max need (up to 9), and rounding never takes them out of the range (count and bits imply a step of
//     1). Out of range clamps and is a problem; a snap is not.
//   - A missing value takes the default without a problem; null, a wrong type or an unknown choice takes the default
//     and is a problem (the looks registry refuses null too). Unknown keys are dropped and listed, sorted.
//   - A derived param is computed from the others after they are validated; a value given for it is ignored. Its
//     expression has at most MAX_TOKENS tokens.
//   - Arithmetic is plain IEEE doubles in the same order on both sides, and decimal text is built from integers, never
//     from toFixed (which rounds ties differently from Python's format); integers from 2^53 up are written in full.
//   - The descriptor check refuses choices that are not distinct both as values and as URL text, and a uniform the
//     host binds itself (HOUSE_UNIFORMS).
//   - Colour is linear light in the shader and in every stored value; the UI shows and picks it in OKLCH.

export const PARAMS_API = "arsenal.params/v1";
// The house refusal text for a control locked while recording (the looks registry's REC_BLOCKED; a test keeps them equal).
export const REC_REFUSAL_TEXT = "Stop recording to change this.";

export const TYPES = Object.freeze(["range", "choice", "toggle", "colour", "vec"]);
export const CURVES = Object.freeze(["linear", "log", "exp"]);
// The units vocabulary (unified architecture draft 3.3). The unit decides the control, its formatter and its URL text.
export const NUMERIC_UNITS = Object.freeze(["ratio", "px", "world", "rad", "turns", "deg", "hz", "sec", "per-sec", "stops",
  "kelvin", "nm", "db", "count", "bits"]);
const UNIT_SYMBOL = { ratio: "", px: "px", world: "units", rad: "rad", turns: "turns", deg: "°", hz: "Hz", sec: "s",
  "per-sec": "/s", stops: "stops", kelvin: "K", nm: "nm", db: "dB", count: "", bits: "bits" };
const UNIT_WORDS = { ratio: "a ratio (1 = as authored)", px: "device pixels", world: "scene units", rad: "radians",
  turns: "turns (1 = a full circle)", deg: "degrees", hz: "hertz", sec: "seconds", "per-sec": "per second",
  stops: "stops (each one doubles the light)", kelvin: "kelvin", nm: "nanometres", db: "decibels", count: "a whole number",
  bits: "bits", bool: "on or off", choice: "one of a list", colour: "a colour (linear light, picked in OKLCH)" };
const TIGHT = new Set(["%", "°", "×", "/s"]);   // written against the number: 40%, 45°, 1.50×, 0.25/s
const SIGNED = new Set(["stops", "db"]);         // a plus sign on positive values: +1.5 stops
const INTEGER_UNITS = new Set(["count", "bits"]);
const EPS = 1e-6;                                // the looks registry's tolerance at the ends of a range
const P10 = [1, 10, 100, 1e3, 1e4, 1e5, 1e6, 1e7, 1e8, 1e9];
const FREE_DECIMALS = 6;
const EXP_K = 4;                                 // the exp curve: value = min + span * (e^(k p) - 1) / (e^k - 1)
const ID_RE = /^[A-Za-z][A-Za-z0-9_.]*$/;
const INSTANCE_RE = /^[A-Za-z][A-Za-z0-9]*$/;    // no underscore, so u_<instance>_<name> always parses one way
const UNIFORM_RE = /^[A-Za-z_][A-Za-z0-9_]*$/;
// The uniforms the shader host binds on every surface (unified architecture draft, section 6); a param never takes one.
export const HOUSE_UNIFORMS = Object.freeze(["u_res", "u_time", "u_dt", "u_frame", "u_mouse"]);
const NUM_RE = /^[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?$/;

export const unitWords = (unit) => UNIT_WORDS[unit] || "";

const isNum = (v) => typeof v === "number" && Number.isFinite(v);
const isObj = (v) => v !== null && typeof v === "object" && !Array.isArray(v);
const has = (o, k) => Object.prototype.hasOwnProperty.call(o, k);
const roundHalfUp = (x) => Math.floor(x + 0.5);
const clamp = (x, a, b) => Math.min(Math.max(x, a), b);

// ------------------------------------------------------------------------------------------- decimal text --
// How many decimals a number needs (0.05 -> 2, 100 -> 0, 1e-7 -> 7), up to 9. A scaled value that still rounds to zero
// is never "close enough": without that rule 1e-7 counted as a whole number and a step of 1e-7 snapped 0.5 to 1.
export function decimalsOf(x) {
  const a = Math.abs(x);
  for (let d = 0; d < P10.length; d++) {
    const s = a * P10[d];
    const n = roundHalfUp(s);
    if (n === 0 && a !== 0) continue;
    if (Math.abs(s - n) < 1e-6) return d;
  }
  return P10.length - 1;
}

// An integer-valued double as all its digits: String() writes 1e+21 from 10^21 up and rounds the digits from 2^53 up
// (2^60 -> 1152921504606847000), where Python's str(int) writes them exactly; BigInt writes the same digits as Python.
const intText = (n) => (Number.isFinite(n) && n >= 2 ** 53 ? BigInt(n).toString() : String(n));

// x with exactly `dec` decimals, rounded half away from zero, built from an integer so both twins write the same text.
function fixed(x, dec) {
  let d = dec;
  while (d > 0 && Math.abs(x) * P10[d] >= 1e15) d--;
  const n = roundHalfUp(Math.abs(x) * P10[d]);
  if (n === 0) return d ? "0." + "0".repeat(d) : "0";
  const digits = intText(n).padStart(d + 1, "0");
  const body = d ? digits.slice(0, digits.length - d) + "." + digits.slice(digits.length - d) : digits;
  return (x < 0 ? "-" : "") + body;
}
const strip = (s) => (s.includes(".") ? s.replace(/0+$/, "").replace(/\.$/, "") : s);
function roundTo(x, dec) {
  const n = roundHalfUp(Math.abs(x) * P10[dec]);
  if (n === 0) return 0;
  return (x < 0 ? -n : n) / P10[dec];
}
const numText = (x) => strip(fixed(x, FREE_DECIMALS));

// A value as plain words for a message, the same on both twins.
function show(v) {
  if (typeof v === "string") return v;
  if (typeof v === "boolean") return v ? "true" : "false";
  if (typeof v === "number") return Number.isFinite(v) ? numText(v) : Number.isNaN(v) ? "NaN" : v > 0 ? "Infinity" : "-Infinity";
  if (v === null) return "null";
  if (v === undefined) return "undefined";
  return Array.isArray(v) ? "a list" : "an object";
}

// ------------------------------------------------------------------------------------------- descriptors --
function impliedUnit(type) {
  return type === "toggle" ? "bool" : type === "choice" ? "choice" : type === "colour" ? "colour" : null;
}

// Every field of the shape present, nothing shared with the input.
export function normalizeDescriptor(d) {
  const type = d.type;
  let range = null;
  if (isObj(d.range) && (type === "range" || type === "vec" || type === "colour")) {
    range = { min: d.range.min, max: d.range.max, step: d.range.step ?? null };
  }
  return {
    id: d.id, group: d.group ?? "params", label: d.label ?? d.id, type, unit: d.unit ?? impliedUnit(type), range,
    default: clone(d.default ?? null), curve: d.curve ?? "linear",
    values: type === "choice" && Array.isArray(d.values) ? d.values.map((o) => ({ value: o?.value, label: o?.label })) : null,
    help: d.help ?? "", recBlocked: !!d.recBlocked, order: isNum(d.order) ? d.order : 0, uniform: d.uniform ?? null,
    derived: d.derived ?? null, cost: !!d.cost, source: isObj(d.source) ? { ...d.source } : null,
  };
}
const clone = (v) => (Array.isArray(v) ? v.map(clone) : isObj(v) ? Object.fromEntries(Object.entries(v).map(([k, x]) => [k, clone(x)])) : v);

function bounds(d) {
  const r = isObj(d.range) ? d.range : {};
  if (d.type === "colour") return { min: isNum(r.min) ? r.min : 0, max: isNum(r.max) ? r.max : 1 };
  return { min: r.min, max: r.max };
}

// The grid a value snaps to: the step (count and bits imply 1) and the decimals that keep grid points exact. Without a
// step, FREE_DECIMALS or as many as min and max need (up to 9): a range of [1e-7, 1e-3] at 6 decimals turned its own
// min into 0.
function gridOf(d) {
  const r = isObj(d.range) ? d.range : {};
  let step = isNum(r.step) && r.step > 0 ? r.step : null;
  if (step === null && INTEGER_UNITS.has(d.unit)) step = 1;
  const { min, max } = bounds(d);
  const ends = Math.max(isNum(min) ? decimalsOf(min) : 0, isNum(max) ? decimalsOf(max) : 0);
  if (step === null) return { step: null, dec: Math.max(FREE_DECIMALS, ends) };
  return { step, dec: Math.max(decimalsOf(step), ends) };
}

function quantise(x, min, max, grid) {
  let v = clamp(x, min, max);
  if (grid.step !== null) v = min + roundHalfUp((v - min) / grid.step) * grid.step;
  v = roundTo(v, grid.dec);
  if (v > max && grid.step !== null) v = roundTo(v - grid.step, grid.dec);   // only when max is off the grid
  if (grid.step === null) v = clamp(v, min, max);      // an end past 9 decimals: rounding must not leave the range
  return v + 0;                                        // never -0
}

function defaultOf(d) {
  const v = d.default;
  if (d.type === "range" && isNum(v)) { const { min, max } = bounds(d); return quantise(v, min, max, gridOf(d)); }
  if ((d.type === "vec" || d.type === "colour") && Array.isArray(v)) {
    const { min, max } = bounds(d), g = gridOf(d);
    return v.map((x) => (isNum(x) ? quantise(x, min, max, g) : x));
  }
  return clone(v);
}

function sameChoice(a, b) {
  if (typeof a === "number" && typeof b === "number") return a === b;
  return typeof a === "string" && typeof b === "string" && a === b;
}

function sameValue(a, b) {
  if (Array.isArray(a) || Array.isArray(b)) return Array.isArray(a) && Array.isArray(b) && a.length === b.length && a.every((x, i) => x === b[i]);
  return a === b;
}

const problem = (id, code, message) => ({ id, code, message });

// ------------------------------------------------------------------------------------------- validation --
// validateValue(d, value) -> { value, problem }: one value against one descriptor. undefined means "not given".
export function validateValue(d, value) {
  const label = d.label ?? d.id;
  const fallback = (code, message) => ({ value: defaultOf(d), problem: problem(d.id, code, message) });
  if (value === undefined) return { value: defaultOf(d), problem: null };
  switch (d.type) {
    case "toggle":
      return typeof value === "boolean" ? { value, problem: null } : fallback("type", `${label} must be on or off.`);
    case "choice": {
      const hit = (d.values || []).find((o) => sameChoice(o.value, value));
      return hit ? { value: hit.value, problem: null }
        : fallback("choice", `${label} "${Array.from(show(value)).slice(0, 40).join("")}" is not one of its choices.`);   // 40 code points, as Python slices
    }
    case "vec":
    case "colour": {
      const n = d.type === "colour" ? 3 : Array.isArray(d.default) ? d.default.length : 0;
      if (!Array.isArray(value)) return fallback("type", `${label} must be ${n} numbers.`);
      if (value.length !== n) return fallback("length", `${label} must have ${n} parts.`);
      if (!value.every(isNum)) return fallback("type", `${label} must be ${n} numbers.`);
      const { min, max } = bounds(d), g = gridOf(d);
      const out = value.map((x) => quantise(x, min, max, g));
      if (value.some((x) => x < min - EPS || x > max + EPS)) {
        const message = d.type === "colour"
          ? `${label} channels must be from ${numText(min)} to ${numText(max)}; using ${out.map(numText).join(", ")}.`
          : `${label} must be from ${formatValue({ ...d, type: "range" }, min)} to ${formatValue({ ...d, type: "range" }, max)}; using ${formatValue(d, out)}.`;
        return { value: out, problem: problem(d.id, "range", message) };
      }
      return { value: out, problem: null };
    }
    default: {
      if (!isNum(value)) return fallback("type", `${label} must be a number.`);
      const { min, max } = bounds(d);
      const out = quantise(value, min, max, gridOf(d));
      if (value < min - EPS || value > max + EPS) {
        return { value: out, problem: problem(d.id, "range",
          `${label} must be from ${formatValue(d, min)} to ${formatValue(d, max)}; using ${formatValue(d, out)}.`) };
      }
      return { value: out, problem: null };
    }
  }
}

// validate(descriptors, values) -> { ok, values, problems }: every descriptor gets a legal value (given, snapped,
// clamped or defaulted), derived params are computed, and every departure from what was given is a problem.
export function validate(descriptors, values) {
  const list = Array.isArray(descriptors) ? descriptors : [];
  const lead = [];
  let src = values;
  if (src === null || src === undefined) src = {};
  else if (!isObj(src)) { lead.push(problem("", "values", "Settings must be an object of names and values.")); src = {}; }
  const out = {};
  const perDescriptor = list.map(() => null);
  list.forEach((d, i) => {
    if (d.derived) { out[d.id] = undefined; return; }
    const r = validateValue(d, has(src, d.id) ? src[d.id] : undefined);
    out[d.id] = r.value;
    perDescriptor[i] = r.problem;
  });
  list.forEach((d, i) => {
    if (!d.derived) return;
    const x = evaluate(d.derived, out);
    if (isNum(x)) { const { min, max } = bounds(d); out[d.id] = quantise(x, min, max, gridOf(d)); return; }
    out[d.id] = defaultOf(d);
    perDescriptor[i] = problem(d.id, "derived", `${d.label ?? d.id} could not be worked out from ${d.derived}; using its default.`);
  });
  const known = new Set(list.map((d) => d.id));
  const unknown = Object.keys(src).filter((k) => !known.has(k)).sort()
    .map((k) => problem(k, "unknown", `${k} is not a setting here.`));
  const problems = [...lead, ...perDescriptor.filter(Boolean), ...unknown];
  return { ok: problems.length === 0, values: out, problems };
}

// ------------------------------------------------------------------------------------- derived expressions --
// A tiny arithmetic language: numbers, other params' ids, + - * / ( ), unary minus, and min, max, clamp, abs, floor.
// Any non-finite step fails the whole expression, the same way on both twins. An expression has at most MAX_TOKENS
// tokens: a derived param is a short formula, and the cap bounds how deep the parser and evaluator recurse, so the Python
// twin (whose stack is far smaller) refuses exactly what this one refuses instead of crashing on a deep expression.
const FUNCS = { min: [2, Infinity], max: [2, Infinity], clamp: [3, 3], abs: [1, 1], floor: [1, 1] };
export const MAX_TOKENS = 128;

function tokenize(src) {
  const out = [];
  let i = 0;
  while (i < src.length) {
    const c = src[i];
    if (c === " " || c === "\t") { i++; continue; }
    if (out.length === MAX_TOKENS) throw new Error(`longer than ${MAX_TOKENS} tokens`);   // a token past the cap starts here
    const rest = src.slice(i);
    let m;
    if ((m = /^([0-9]+(\.[0-9]+)?|\.[0-9]+)/.exec(rest))) { out.push({ t: "num", v: Number(m[0]) }); i += m[0].length; continue; }
    if ((m = /^[A-Za-z_][A-Za-z0-9_.]*/.exec(rest))) { out.push({ t: "id", v: m[0] }); i += m[0].length; continue; }
    if ("+-*/(),".includes(c)) { out.push({ t: c }); i++; continue; }
    throw new Error(`unexpected "${c}"`);
  }
  return out;
}

function parseExpr(src) {
  const toks = tokenize(String(src));
  let k = 0;
  const peek = () => toks[k] || { t: "end" };
  const take = (t) => { if (peek().t !== t) throw new Error(`expected ${t}`); return toks[k++]; };
  function expr() {
    let a = term();
    while (peek().t === "+" || peek().t === "-") { const op = toks[k++].t; a = { k: "bin", op, a, b: term() }; }
    return a;
  }
  function term() {
    let a = unary();
    while (peek().t === "*" || peek().t === "/") { const op = toks[k++].t; a = { k: "bin", op, a, b: unary() }; }
    return a;
  }
  function unary() {
    if (peek().t === "-") { k++; return { k: "neg", a: unary() }; }
    return primary();
  }
  function primary() {
    const t = peek();
    if (t.t === "num") { k++; return { k: "num", v: t.v }; }
    if (t.t === "(") { k++; const e = expr(); take(")"); return e; }
    if (t.t === "id") {
      k++;
      if (peek().t !== "(") return { k: "id", v: t.v };
      k++;
      const args = [];
      if (peek().t !== ")") { args.push(expr()); while (peek().t === ",") { k++; args.push(expr()); } }
      take(")");
      const arity = FUNCS[t.v];
      if (!arity) throw new Error(`no function called ${t.v}`);
      if (args.length < arity[0] || args.length > arity[1]) throw new Error(`${t.v} takes ${arity[0]} arguments`);
      return { k: "call", f: t.v, args };
    }
    throw new Error("expected a number, a name or (");
  }
  const tree = expr();
  if (k !== toks.length) throw new Error("unexpected text at the end");
  return tree;
}

function idsIn(node, out = []) {
  if (node.k === "id") out.push(node.v);
  else if (node.k === "neg") idsIn(node.a, out);
  else if (node.k === "bin") { idsIn(node.a, out); idsIn(node.b, out); }
  else if (node.k === "call") for (const a of node.args) idsIn(a, out);
  return out;
}

function run(node, env) {
  let v;
  switch (node.k) {
    case "num": v = node.v; break;
    case "id": v = env[node.v]; break;
    case "neg": v = -run(node.a, env); break;
    case "bin": {
      const a = run(node.a, env), b = run(node.b, env);
      v = node.op === "+" ? a + b : node.op === "-" ? a - b : node.op === "*" ? a * b : a / b;
      break;
    }
    default: {
      const xs = node.args.map((a) => run(a, env));
      v = node.f === "min" ? Math.min(...xs) : node.f === "max" ? Math.max(...xs) : node.f === "clamp" ? clamp(xs[0], xs[1], xs[2])
        : node.f === "abs" ? Math.abs(xs[0]) : Math.floor(xs[0]);
    }
  }
  if (!isNum(v)) throw new Error("not a finite number");
  return v;
}

const parsed = new Map();
function evaluate(src, env) {
  try {
    if (!parsed.has(src)) parsed.set(src, parseExpr(src));
    return run(parsed.get(src), env);
  } catch {
    return NaN;
  }
}

// --------------------------------------------------------------------------------------- descriptor check --
// checkDescriptors(list) -> [{ id, code, message }]: what is wrong with the descriptors themselves (a page or loader
// runs it once; validate trusts its descriptors). Codes per descriptor, in this order: id or duplicate, type, unit,
// range, curve, values, default, derived, uniform.
export function checkDescriptors(descriptors) {
  if (!Array.isArray(descriptors)) return [problem("", "descriptors", "Descriptors must be a list.")];
  const out = [];
  const seen = new Set(), uniforms = new Set();
  const byId = new Map();
  for (const d of descriptors) if (isObj(d) && typeof d.id === "string" && !byId.has(d.id)) byId.set(d.id, d);
  for (const d of descriptors) {
    const id = isObj(d) && typeof d.id === "string" ? d.id : "";
    const add = (code, message) => out.push(problem(id, code, message));
    if (!isObj(d)) { add("descriptor", "A descriptor must be an object."); continue; }
    if (!ID_RE.test(id)) add("id", `"${id}" is not a usable id (a letter, then letters, digits, _ or .).`);
    else if (seen.has(id)) add("duplicate", `${id} is described twice.`);
    seen.add(id);
    if (!TYPES.includes(d.type)) { add("type", `${id} has no known type (${TYPES.join(", ")}).`); continue; }
    const numeric = d.type === "range" || d.type === "vec";
    if (numeric) {
      if (d.unit === undefined || d.unit === null) add("unit", `${id} needs a unit (the number means nothing without one).`);
      else if (!NUMERIC_UNITS.includes(d.unit)) add("unit", `${id} has an unknown unit "${show(d.unit)}".`);
    } else if (d.unit !== undefined && d.unit !== null && d.unit !== impliedUnit(d.type)) {
      add("unit", `a ${d.type} takes the unit "${impliedUnit(d.type)}" or none.`);
    }
    let rangeOk = false;
    const r = d.range;
    const rangeShapeOk = isObj(r) && isNum(r.min) && isNum(r.max) && r.min < r.max
      && (r.step === undefined || r.step === null || (isNum(r.step) && r.step > 0));
    if (numeric) { if (rangeShapeOk) rangeOk = true; else add("range", `${id} needs a range with min below max and a positive step.`); }
    else if (d.type === "colour") {
      if (r === undefined || r === null) rangeOk = true;
      else if (rangeShapeOk) rangeOk = true;
      else add("range", `${id} has a broken range.`);
    }
    const curve = d.curve ?? "linear";
    if (!CURVES.includes(curve)) add("curve", `${id} has an unknown curve "${show(curve)}".`);
    else if (curve === "log" && !(rangeOk && r.min > 0)) add("curve", `${id}: a log curve needs a range above zero.`);
    let valuesOk = true;
    if (d.type === "choice") {
      const vs = d.values;
      // Distinct as values and as URL text: "1" and 1 both write x=1, and the URL could only ever bring back the first.
      valuesOk = Array.isArray(vs) && vs.length > 0 && vs.every((o) => isObj(o) && typeof o.label === "string"
        && (typeof o.value === "string" || isNum(o.value)))
        && vs.every((o, i) => vs.findIndex((p) => sameChoice(p.value, o.value)) === i)
        && new Set(vs.map((o) => codecText(d, o.value))).size === vs.length;
      if (!valuesOk) add("values", `${id} needs a list of distinct choices, each a value and a label.`);
    }
    if (!defaultOk(d, rangeOk, valuesOk)) add("default", `${id} has a default that is not one of its own legal values.`);
    if (d.derived !== undefined && d.derived !== null) {
      let bad = d.type !== "range" || typeof d.derived !== "string";
      if (!bad) {
        try {
          for (const name of idsIn(parseExpr(d.derived))) {
            const t = byId.get(name);
            if (!t || t === d || t.derived || t.type !== "range") bad = true;
          }
        } catch { bad = true; }
      }
      if (bad) add("derived", `${id} is derived from something that is not a plain number param here.`);
    }
    if (d.uniform !== undefined && d.uniform !== null) {
      const u = d.uniform;
      if (typeof u !== "string" || !UNIFORM_RE.test(u) || u.startsWith("gl_") || u.includes("__")) {
        add("uniform", `${id}: "${show(u)}" is not a GLSL name a uniform can have.`);
      } else if (HOUSE_UNIFORMS.includes(u)) add("uniform", `${id}: ${u} is a house uniform the host binds itself.`);
      else if (uniforms.has(u)) add("uniform", `${id}: the uniform ${u} is already bound to another param.`);
      else uniforms.add(u);
    }
  }
  return out;
}

function defaultOk(d, rangeOk, valuesOk) {
  const v = d.default;
  if (d.type === "toggle") return typeof v === "boolean";
  if (d.type === "choice") return valuesOk && d.values.some((o) => sameChoice(o.value, v));
  const { min, max } = bounds(d);
  const inside = (x) => isNum(x) && (!rangeOk || (x >= min - EPS && x <= max + EPS));
  if (d.type === "range") return inside(v);
  if (d.type === "colour") return Array.isArray(v) && v.length === 3 && v.every(inside);
  return Array.isArray(v) && v.length >= 2 && v.length <= 4 && v.every(inside);   // vec
}

// --------------------------------------------------------------------------------------- params from a module --
function typeOfParam(p) {
  if (TYPES.includes(p.type)) return p.type;
  if (Array.isArray(p.choices)) return "choice";
  if (p.unit === "bool") return "toggle";
  if (p.unit === "colour") return "colour";
  if (Array.isArray(p.default)) return "vec";
  return "range";
}

// A header's choices are labels in order and the value is the index (what an int argument receives); an object
// {value, label} keeps its own value.
function choicesOf(p) {
  return p.choices.map((c, i) => (isObj(c) ? { value: c.value, label: String(c.label ?? c.value) }
    : typeof c === "string" ? { value: i, label: c } : { value: c, label: show(c) }));
}

// Rewrite a derived expression's sibling names into the instance's ids ("fold" -> "a.fold"); function names stay.
function namespaceExpr(src, names, inst) {
  return src.replace(/[A-Za-z_][A-Za-z0-9_.]*/g, (m, at) => {
    let j = at + m.length;
    while (src[j] === " " || src[j] === "\t") j++;
    return names.has(m) && src[j] !== "(" ? `${inst}.${m}` : m;
  });
}

// paramsFromModule(header, instanceId) -> descriptors for a recipe's `params`, one per entry argument in header order.
// With an instance id every uniform is namespaced (u_<instance>_<name>) and every id is <instance>.<name>, so two
// instances of one recipe never share a slider (the bench's parameter-bus leak, where one u_sub moved three things).
// With null, a single-instance surface binds short names (u_<name>, or the uniform its header declares).
export function paramsFromModule(header, instanceId = null) {
  if (instanceId !== null && instanceId !== undefined && !(typeof instanceId === "string" && INSTANCE_RE.test(instanceId))) {
    throw new TypeError(`instance id "${show(instanceId)}" must be a letter then letters or digits (no _ or .)`);
  }
  const inst = instanceId ?? null;
  const params = isObj(header) && Array.isArray(header.params) ? header.params : [];
  const names = new Set(params.map((p) => p && p.name).filter((n) => typeof n === "string"));
  return params.map((p, i) => {
    // Without a string name there is no id or uniform to make ("undefined" here and "None" in Python would disagree).
    if (!isObj(p) || typeof p.name !== "string") throw new TypeError(`param ${i} of the header needs a name`);
    const name = p.name;
    const type = typeOfParam(p);
    let range = null;
    if (type === "range" || type === "vec" || (type === "colour" && p.range !== undefined && p.range !== null)) {
      const r = p.range;
      const [min, max] = Array.isArray(r) ? r : [r?.min, r?.max];
      range = { min, max, step: p.step ?? (Array.isArray(r) ? null : r?.step ?? null) };
    }
    const group = p.group ?? "params";
    return {
      id: inst ? `${inst}.${name}` : name,
      group: inst ? `${inst}.${group}` : group,
      label: p.label ?? name,
      type,
      unit: p.unit ?? impliedUnit(type),
      range,
      default: p.default === undefined ? null : clone(p.default),
      curve: p.curve ?? "linear",
      values: type === "choice" ? choicesOf(p) : null,
      help: p.help ?? "",
      recBlocked: !!p.recBlocked,
      order: i,
      uniform: inst ? `u_${inst}_${name}` : (typeof p.uniform === "string" ? p.uniform : `u_${name}`),
      derived: typeof p.derived === "string" && p.derived ? (inst ? namespaceExpr(p.derived, names, inst) : p.derived) : null,
      cost: !!p.cost,
      source: { module: isObj(header) && typeof header.name === "string" ? header.name : null, param: name, instance: inst },
    };
  });
}

// --------------------------------------------------------------------------------------------- the formatter --
const percentMode = (d) => d.unit === "ratio" && bounds(d).max <= 1;
function symbolOf(d) {
  if (d.unit === "ratio") return percentMode(d) ? "%" : "×";
  return UNIT_SYMBOL[d.unit] ?? "";
}
function displayDecimals(d) {
  const step = isObj(d.range) ? d.range.step : null;
  if (isNum(step) && step > 0) return Math.min(decimalsOf(step), 4);
  return INTEGER_UNITS.has(d.unit) ? 0 : 2;
}
function shownNumber(d, x) {
  if (!isNum(x)) return show(x);
  let dec = displayDecimals(d), v = x;
  if (percentMode(d)) { v = x * 100; dec = Math.max(0, dec - 2); }
  let s = fixed(v, dec);
  if (SIGNED.has(d.unit) && !s.startsWith("-") && /[1-9]/.test(s)) s = "+" + s;
  return s;
}
function srgbByte(x) {
  const c = isNum(x) ? clamp(x, 0, 1) : 0;
  const e = c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055;
  return clamp(roundHalfUp(e * 255), 0, 255).toString(16).padStart(2, "0");
}

// formatParts(d, value) -> { text, unit }: the number and its unit apart, for a readout that sets them side by side.
export function formatParts(d, value) {
  switch (d.type) {
    case "toggle": return { text: value === true ? "On" : "Off", unit: "" };
    case "choice": {
      const hit = (d.values || []).find((o) => sameChoice(o.value, value));
      return { text: hit ? String(hit.label) : show(value), unit: "" };
    }
    case "colour":
      return { text: Array.isArray(value) && value.length === 3 ? "#" + value.map(srgbByte).join("") : show(value), unit: "" };
    case "vec":
      return { text: Array.isArray(value) ? value.map((x) => shownNumber(d, x)).join(", ") : show(value), unit: symbolOf(d) };
    default:
      return { text: shownNumber(d, value), unit: symbolOf(d) };
  }
}

// formatValue(d, value) -> "40%", "+1.5 stops", "0.25, -0.50 units", "#ffbc89", "On", "ACES fit".
export function formatValue(d, value) {
  const { text, unit } = formatParts(d, value);
  if (!unit) return text;
  return TIGHT.has(unit) ? text + unit : `${text} ${unit}`;
}

// ------------------------------------------------------------------------------------------- slider curves --
// positionToValue(d, p): a slider position in [0, 1] to a value (not yet snapped; validateValue snaps it).
export function positionToValue(d, p) {
  const { min, max } = bounds(d);
  const t = isNum(p) ? clamp(p, 0, 1) : 0;
  const curve = d.curve ?? "linear";
  if (curve === "log" && min > 0 && max > 0) return min * Math.pow(max / min, t);
  if (curve === "exp") return min + (max - min) * (Math.exp(EXP_K * t) - 1) / (Math.exp(EXP_K) - 1);
  return min + (max - min) * t;
}

// valueToPosition(d, v): the inverse, clamped to [0, 1].
export function valueToPosition(d, v) {
  if (!isNum(v)) return 0;
  const { min, max } = bounds(d);
  if (v <= min) return 0;
  if (v >= max) return 1;
  const curve = d.curve ?? "linear";
  if (curve === "log" && min > 0 && max > 0) return Math.log(v / min) / Math.log(max / min);
  if (curve === "exp") return Math.log(1 + (v - min) / (max - min) * (Math.exp(EXP_K) - 1)) / EXP_K;
  return (v - min) / (max - min);
}

// --------------------------------------------------------------------------------------------- the URL codec --
// Keys are descriptor ids, values are the codec text below, joined with & in descriptor order. Only values that differ
// from the default are written unless { all: true }. Safe characters stay as they are (letters, digits, - . _ ~ , :);
// everything else is %XX of its UTF-8 bytes, upper-case. Decoding also reads + as a space (what URLSearchParams
// writes), keeps the first of repeated keys (what URLSearchParams.get reads), ignores keys it does not know and leaves
// text it cannot read as a string, so validate names the problem.
const SAFE = new Set("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~,:");
const utf8 = new TextEncoder();
const hex2 = (b) => "%" + b.toString(16).toUpperCase().padStart(2, "0");

function esc(s) {
  let out = "";
  for (const ch of String(s)) {
    if (SAFE.has(ch)) out += ch;
    else for (const b of utf8.encode(ch)) out += hex2(b);
  }
  return out;
}

function unesc(s) {
  const bytes = [];
  for (let i = 0; i < s.length;) {
    const c = s[i];
    if (c === "%" && /^[0-9A-Fa-f]{2}$/.test(s.slice(i + 1, i + 3))) { bytes.push(parseInt(s.slice(i + 1, i + 3), 16)); i += 3; continue; }
    if (c === "+") { bytes.push(0x20); i++; continue; }
    const cp = s.codePointAt(i);
    const ch = String.fromCodePoint(cp);
    for (const b of utf8.encode(ch)) bytes.push(b);
    i += ch.length;
  }
  // ignoreBOM keeps a leading U+FEFF, as Python's bytes.decode("utf-8") does; the default would strip it here only.
  return new TextDecoder("utf-8", { ignoreBOM: true }).decode(new Uint8Array(bytes));
}

// The text one value is written as in a URL.
export function codecText(d, v) {
  switch (d.type) {
    case "toggle": return v ? "1" : "0";
    case "choice": return typeof v === "string" ? v : isNum(v) ? numText(v) : show(v);
    case "vec":
    case "colour": { const g = gridOf(d); return (Array.isArray(v) ? v : []).map((x) => strip(fixed(x, g.dec))).join(","); }
    default: return strip(fixed(v, gridOf(d).dec));
  }
}

function readText(d, text) {
  switch (d.type) {
    case "toggle": {
      const t = text.toLowerCase();
      return ["1", "true", "on", "yes"].includes(t) ? true : ["0", "false", "off", "no"].includes(t) ? false : text;
    }
    case "choice": {
      const hit = (d.values || []).find((o) => codecText(d, o.value) === text);
      return hit ? hit.value : text;
    }
    case "vec":
    case "colour": {
      const parts = text.split(",");
      return parts.every((p) => NUM_RE.test(p)) ? parts.map(Number) : text;
    }
    default: return NUM_RE.test(text) ? Number(text) : text;
  }
}

// encode(descriptors, values, { all }) -> "intensity=1.5&layers=30": the validated values as a query string.
export function encode(descriptors, values, { all = false } = {}) {
  const list = Array.isArray(descriptors) ? descriptors : [];
  const r = validate(list, values);
  const parts = [];
  for (const d of list) {
    if (d.derived) continue;
    const v = r.values[d.id];
    if (!all && sameValue(v, defaultOf(d))) continue;
    parts.push(esc(d.id) + "=" + esc(codecText(d, v)));
  }
  return parts.join("&");
}

// decode(descriptors, query) -> the values a query string holds (typed where readable). Takes a string, with or
// without its leading ?, or a URLSearchParams.
export function decode(descriptors, query) {
  const list = Array.isArray(descriptors) ? descriptors : [];
  let q = typeof query === "string" ? query : query && typeof query === "object" ? String(query) : "";
  if (q.startsWith("?")) q = q.slice(1);
  const seen = new Map();
  for (const part of q.split("&")) {
    if (!part) continue;
    const at = part.indexOf("=");
    const key = unesc(at < 0 ? part : part.slice(0, at));
    if (key && !seen.has(key)) seen.set(key, at < 0 ? "" : unesc(part.slice(at + 1)));
  }
  const out = {};
  for (const d of list) if (!d.derived && seen.has(d.id)) out[d.id] = readText(d, seen.get(d.id));
  return out;
}

// fromUrl(descriptors, query) -> validate(descriptors, decode(descriptors, query)).
export function fromUrl(descriptors, query) {
  return validate(descriptors, decode(descriptors, query));
}

// ------------------------------------------------------------------------------------------------ OKLCH --
// Colour is stored as linear-light sRGB; the controls pick it as OKLCH (lightness 0..1, chroma, hue in degrees).
// The forward matrices are Bjorn Ottosson's published OKLab definition (2020, public domain); the inverses are computed
// here rather than copied, so a round trip is exact to rounding.
const M1 = [[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566],
  [0.0883024619, 0.2817188376, 0.6299787005]];
const M2 = [[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099],
  [0.0259040371, 0.7827717662, -0.8086757660]];
function invert3(m) {
  const [[a, b, c], [d, e, f], [g, h, i]] = m;
  const A = e * i - f * h, B = -(d * i - f * g), C = d * h - e * g;
  const det = a * A + b * B + c * C;
  return [[A / det, -(b * i - c * h) / det, (b * f - c * e) / det],
    [B / det, (a * i - c * g) / det, -(a * f - c * d) / det],
    [C / det, -(a * h - b * g) / det, (a * e - b * d) / det]];
}
const M1i = invert3(M1), M2i = invert3(M2);
const mul = (m, v) => m.map((row) => row[0] * v[0] + row[1] * v[1] + row[2] * v[2]);

export function linearToOklch(rgb) {
  const lms = mul(M1, rgb).map(Math.cbrt);
  const [L, a, b] = mul(M2, lms);
  const C = Math.hypot(a, b);
  let h = Math.atan2(b, a) * 180 / Math.PI;
  if (h < 0) h += 360;
  return [L, C, h];
}

export function oklchToLinear([L, C, h]) {
  const r = h * Math.PI / 180;
  const lms = mul(M2i, [L, C * Math.cos(r), C * Math.sin(r)]).map((x) => x * x * x);
  return mul(M1i, lms);
}

// ------------------------------------------------------------------------------------ the looks registry adapter --
// fromLooksDescriptor(d, { default, values }) -> a schema descriptor for one of the looks registry's LOOK_SETTINGS.
// Read-only: the registry and the Studio are unchanged. The registry carries no defaults (a look always supplies its
// own values and the page reports the rest), so pass the page's current value as `default`; without one a choice
// starts on its first value, a toggle off and a range at its minimum. Its live `options(page)` (bake-off schemes the
// page lists at run time) are the registry's business; pass them as `values` to widen the static list.
// The registry's range `step` is its slider's step, not a grid: it accepts 0.87 where the step is 0.05. The schema
// enforces a step, so the adapted range has none (a look's 0.87 must not come back as 0.85).
const LOOKS_COST = new Set(["quality"]);   // render quality changes how hard the GPU works every frame

export function fromLooksDescriptor(d, opts = {}) {
  const type = d.type === "range" || d.type === "toggle" ? d.type : "choice";
  const values = type === "choice"
    ? (Array.isArray(opts.values) ? opts.values : Array.isArray(d.values) ? d.values : []).map((o) => ({ value: o.value, label: String(o.label ?? o.value) }))
    : null;
  const range = type === "range" ? { min: d.range.min, max: d.range.max, step: null } : null;
  let def = opts.default;
  if (def === undefined) def = type === "choice" ? (values[0] ? values[0].value : null) : type === "toggle" ? false : range.min;
  return {
    id: d.id, group: d.group ?? "params", label: d.label ?? d.id, type,
    unit: type === "range" ? "ratio" : impliedUnit(type), range, default: def, curve: "linear", values, help: "",
    recBlocked: !!d.recBlocked, order: isNum(d.order) ? d.order : 0, uniform: null, derived: null,
    cost: LOOKS_COST.has(d.id) || d.cost === true, source: { module: "piano.looks", param: d.id, instance: null },
  };
}
