// Generated controls: param descriptors (arsenal/web/lib/params.js) rendered into knobs, so every page that shows
// knobs (the bench Inspector, the Studio drawer, First Light's patch panel, Play, Gyre and Wind) gets the same house
// behaviour from one place instead of each page hand-building sliders that drift apart.
//
// What every control keeps (the house rules, unified architecture draft 5.2):
//   - grouped sections, in the order the groups first appear (or the order a page passes in `groups`);
//   - the unit beside every number, with the unit spelled out on hover, and the label's hover carries the help text;
//   - a reset to the default on each control;
//   - a cost badge on a control that changes how hard the GPU works;
//   - a control locked while recording is disabled, looks dead and says why in the house refusal text;
//   - after a pointer interaction the control blurs, so letter keys go back to the note keyboard (the Studio rule:
//     a keyboard change keeps focus, a click or drag gives it back);
//   - a derived param is shown, never set;
//   - colour is picked as OKLCH (lightness, chroma, hue) and stored as linear light.
//
// It takes the document as an argument and uses only createElement, appendChild, attributes, properties and listeners,
// so tests/params_schema.test.mjs drives it with a small fake document instead of a browser or jsdom. Styling is the
// host's: the class names below are stable (params, params-group, params-row, params-label, params-ctl, params-readout,
// params-out, params-unit, params-reset, params-cost, params-refusal, params-swatch).
import {
  REC_REFUSAL_TEXT, codecText, formatParts, formatValue, linearToOklch, normalizeDescriptor, oklchToLinear,
  positionToValue, unitWords, validate, validateValue, valueToPosition,
} from "./params.js";

const POSITIONS = 1000;   // a log or exp slider runs over positions 0..1000 and maps them through the curve
const OKLCH_STEP = 0.001;
// The OKLCH sliders for a colour whose channels run over [min, max]. For 0..1 that is lightness 0..1 and chroma 0..0.4
// (sRGB's most saturated colours sit near 0.32). A wider range (HDR, max 4) reaches further: scaling linear light by k
// scales OKLab by the cube root of k, so lightness tops out at the lightness of [max, max, max] and chroma scales with
// it. Ends are rounded outwards onto the slider's grid, so a legal colour is never clamped by its own slider.
function oklchAxes(min, max) {
  const out = (x, dir) => (dir > 0 ? Math.ceil(x / OKLCH_STEP - 1e-9) : Math.floor(x / OKLCH_STEP + 1e-9)) * OKLCH_STEP;
  const lMax = Math.max(1, linearToOklch([max, max, max])[0]);
  const lMin = Math.min(0, linearToOklch([min, min, min])[0]);
  const reach = Math.max(1, Math.cbrt(Math.max(Math.abs(min), Math.abs(max))));
  return [
    { axis: "L", label: "Lightness", min: +out(lMin, -1).toFixed(3), max: +out(lMax, 1).toFixed(3), step: OKLCH_STEP },
    { axis: "C", label: "Chroma", min: 0, max: +out(0.4 * reach, 1).toFixed(3), step: OKLCH_STEP },
    { axis: "h", label: "Hue", min: 0, max: 360, step: 0.1 },
  ];
}
const VEC_AXES = ["x", "y", "z", "w"];

const humanise = (gid) => String(gid).split(".").map((p) => (p ? p[0].toUpperCase() + p.slice(1) : p)).join(" · ");
const copy = (v) => (Array.isArray(v) ? v.slice() : v);
const same = (a, b) => (Array.isArray(a) && Array.isArray(b) ? a.length === b.length && a.every((x, i) => x === b[i]) : a === b);

// renderParams(doc, descriptors, { values, onChange(id, value, values), recording, groups: [{id, label}], idPrefix })
//   -> { root, rows, values(), setValues(values, { replace }), reset(id), resetAll(), setRecording(on), problems }
// rows: Map id -> { d, row, label, input, inputs, output, unit, reset, badge, refusal, swatch }
export function renderParams(doc, descriptors, opts = {}) {
  const list = (Array.isArray(descriptors) ? descriptors : []).map(normalizeDescriptor);
  const onChange = typeof opts.onChange === "function" ? opts.onChange : () => {};
  const prefix = String(opts.idPrefix || "param");
  let recording = !!opts.recording;
  const first = validate(list, opts.values ?? {});
  let values = first.values;
  const rows = new Map();

  const el = (tag, cls, text) => {
    const e = doc.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  };
  const locked = (rec) => recording && rec.d.recBlocked;

  // A user change: validate this one value, recompute the derived ones, repaint, and tell the page if it moved.
  function commit(rec, raw, skip = []) {
    if (locked(rec)) { paint(rec); return; }
    const id = rec.d.id;
    const before = values[id];
    const one = validateValue(rec.d, raw);
    values = validate(list, { ...values, [id]: one.value }).values;
    for (const r of rows.values()) paint(r, r === rec ? skip : []);
    if (!same(before, values[id])) onChange(id, copy(values[id]), snapshot());
  }
  const snapshot = () => Object.fromEntries(Object.entries(values).map(([k, v]) => [k, copy(v)]));

  // Give focus back after a pointer: a drag or pick ends with "change"; a click carries detail > 0 (0 = keyboard).
  // A click that changes nothing fires no "change", so a keydown once the pointer is released clears the flag: the
  // keyboard change that follows keeps focus. A key that goes down while the pointer is still down (a key pressed
  // mid-drag, or a held note key auto-repeating onto the slider pointerdown just focused) leaves the flag set, so the
  // drag still gives the keyboard back to the notes when it ends.
  function blurAfterPointer(rec, input) {
    const up = () => { rec.down = false; };
    input.addEventListener("pointerdown", () => { rec.pointer = true; rec.down = true; });
    input.addEventListener("pointerup", up);
    input.addEventListener("pointercancel", up);
    input.addEventListener("keydown", () => { if (!rec.down) rec.pointer = false; });
    input.addEventListener("change", () => { if (rec.pointer) input.blur(); rec.pointer = false; rec.down = false; });
  }
  const blurAfterClick = (e, b) => { if (e && e.detail !== 0) b.blur(); };

  function slider(min, max, step) {
    const s = el("input", "params-slider");
    s.type = "range";
    s.min = String(min);
    s.max = String(max);
    s.step = step;
    return s;
  }
  const sliderText = (d, v) => (d.curve === "log" || d.curve === "exp"
    ? String(Math.round(valueToPosition(d, v) * POSITIONS)) : String(v));
  const sliderValue = (d, text) => (d.curve === "log" || d.curve === "exp"
    ? positionToValue(d, Number(text) / POSITIONS) : Number(text));

  function readout(rec, ctl, domId) {
    const box = el("span", "params-readout");
    rec.output = el("output", "params-out");
    rec.output.setAttribute("for", domId);
    rec.unit = el("span", "params-unit");
    rec.unit.dataset.unit = rec.d.unit ?? "";
    rec.unit.title = unitWords(rec.d.unit);
    box.appendChild(rec.output);
    box.appendChild(rec.unit);
    ctl.appendChild(box);
  }

  function buildRow(d) {
    const domId = `${prefix}-${d.id.replace(/[^A-Za-z0-9_-]/g, "-")}`;
    const rec = { d, row: el("div", "params-row"), label: null, input: null, inputs: [], output: null, unit: null,
      reset: null, badge: null, refusal: null, swatch: null, pointer: false, down: false, lch: null, shown: [] };
    const { row } = rec;
    row.dataset.param = d.id;
    row.dataset.type = d.type;
    row.dataset.curve = d.curve;
    row.dataset.locked = "false";
    if (d.derived) row.dataset.derived = "true";
    rec.label = el("label", "params-label", d.label);
    rec.label.id = `${domId}-label`;
    rec.label.setAttribute("for", domId);
    if (d.help) rec.label.title = d.help;
    row.appendChild(rec.label);
    const ctl = el("span", "params-ctl");
    row.appendChild(ctl);

    if (d.derived) {
      readout(rec, ctl, domId);
      rec.output.title = `Worked out from ${d.derived}`;
    } else if (d.type === "toggle") {
      const b = el("button", "params-switch");
      b.type = "button";
      b.setAttribute("role", "switch");
      b.addEventListener("click", (e) => {
        if (locked(rec)) return;
        commit(rec, values[d.id] !== true);
        blurAfterClick(e, b);
      });
      rec.input = b;
      ctl.appendChild(b);
    } else if (d.type === "choice") {
      const s = el("select", "params-select");
      for (const o of d.values || []) {
        const opt = el("option", null, String(o.label));
        opt.value = codecText(d, o.value);
        s.appendChild(opt);
      }
      s.addEventListener("change", () => {
        const hit = (d.values || []).find((o) => codecText(d, o.value) === s.value);
        commit(rec, hit ? hit.value : s.value, [s]);
      });
      blurAfterPointer(rec, s);
      rec.input = s;
      ctl.appendChild(s);
    } else if (d.type === "vec") {
      // One slider per component; a vec has as many components as its default.
      (Array.isArray(d.default) ? d.default : []).forEach((_, i) => {
        const s = slider(d.range.min, d.range.max, d.range.step ? String(d.range.step) : "any");
        s.dataset.axis = VEC_AXES[i];
        s.setAttribute("aria-label", `${d.label} ${VEC_AXES[i]}`);
        const read = () => commit(rec, rec.inputs.map((x) => Number(x.value)), [s]);
        s.addEventListener("input", read);
        s.addEventListener("change", read);
        blurAfterPointer(rec, s);
        rec.inputs.push(s);
        ctl.appendChild(s);
      });
      rec.input = rec.inputs[0] || null;
      readout(rec, ctl, domId);
    } else if (d.type === "colour") {
      const r = d.range || {};
      const min = Number.isFinite(r.min) ? r.min : 0, max = Number.isFinite(r.max) ? r.max : 1;
      for (const ax of oklchAxes(min, max)) {
        const s = slider(ax.min, ax.max, String(ax.step));
        s.dataset.axis = ax.axis;
        s.setAttribute("aria-label", `${d.label} ${ax.label.toLowerCase()}`);
        // A slider holds its axis snapped to its step, so an axis the user has not moved since the last paint is read
        // from the exact OKLCH kept beside it, not from the slider: touching hue must not shift lightness or chroma.
        const read = () => {
          const lch = rec.inputs.map((x, i) => (rec.lch && x.value === rec.shown[i] ? rec.lch[i] : Number(x.value)));
          rec.lch = lch;
          rec.shown = rec.inputs.map((x) => x.value);
          const lin = oklchToLinear(lch);
          commit(rec, lin.map((c) => Math.min(Math.max(c, min), max)), rec.inputs);
        };
        s.addEventListener("input", read);
        s.addEventListener("change", read);
        blurAfterPointer(rec, s);
        rec.inputs.push(s);
        ctl.appendChild(s);
      }
      rec.input = rec.inputs[0];
      rec.swatch = el("span", "params-swatch");
      rec.swatch.setAttribute("aria-hidden", "true");
      ctl.appendChild(rec.swatch);
      rec.output = el("output", "params-out");
      ctl.appendChild(rec.output);
    } else {
      const step = d.curve === "log" || d.curve === "exp" ? "1"
        : d.range.step ? String(d.range.step) : d.unit === "count" || d.unit === "bits" ? "1" : "any";
      const s = d.curve === "log" || d.curve === "exp" ? slider(0, POSITIONS, step) : slider(d.range.min, d.range.max, step);
      const read = () => commit(rec, sliderValue(d, s.value), [s]);
      s.addEventListener("input", read);
      s.addEventListener("change", read);
      blurAfterPointer(rec, s);
      rec.input = s;
      ctl.appendChild(s);
      readout(rec, ctl, domId);
    }
    if (rec.input) {
      rec.input.id = domId;
      rec.input.setAttribute("aria-labelledby", rec.label.id);
    }
    if (d.cost) {
      rec.badge = el("span", "params-cost", "cost");
      rec.badge.title = "Changes how hard the GPU works";
      ctl.appendChild(rec.badge);
    }
    if (!d.derived) {
      const r = el("button", "params-reset", "Reset");
      r.type = "button";
      r.setAttribute("aria-label", `Reset ${d.label} to ${formatValue(d, validateValue(d, d.default).value)}`);
      r.addEventListener("click", (e) => {
        blurAfterClick(e, r);
        if (locked(rec)) return;
        commit(rec, validateValue(d, d.default).value);
      });
      rec.reset = r;
      ctl.appendChild(r);
    }
    if (d.recBlocked) {
      rec.refusal = el("span", "params-refusal", REC_REFUSAL_TEXT);
      rec.refusal.hidden = true;
      row.appendChild(rec.refusal);
    }
    rows.set(d.id, rec);
    paint(rec);
    return row;
  }

  // Show the current value; `skip` holds controls the user is moving right now (their position stays theirs).
  function paint(rec, skip = []) {
    const { d } = rec;
    const v = values[d.id];
    const parts = formatParts(d, v);
    if (rec.output) rec.output.textContent = parts.text;
    if (rec.unit) rec.unit.textContent = parts.unit;
    if (!d.derived) {
      if (d.type === "toggle") {
        rec.input.setAttribute("aria-checked", String(v === true));
        rec.input.textContent = v === true ? "On" : "Off";
      } else if (d.type === "choice") {
        if (!skip.includes(rec.input)) rec.input.value = codecText(d, v);
      } else if (d.type === "vec") {
        rec.inputs.forEach((s, i) => { if (!skip.includes(s)) s.value = String(v[i]); });
      } else if (d.type === "colour") {
        if (!rec.inputs.some((s) => skip.includes(s))) {
          rec.lch = linearToOklch(v);
          rec.inputs.forEach((s, i) => { s.value = String(rec.lch[i]); });
          rec.shown = rec.inputs.map((s) => s.value);   // what each slider holds once it has snapped the value
        }
        rec.swatch.style.background = parts.text;
      } else {
        if (!skip.includes(rec.input)) rec.input.value = sliderText(d, v);
        rec.input.setAttribute("aria-valuetext", formatValue(d, v));
      }
    }
    const dead = locked(rec);
    for (const s of rec.inputs.length ? rec.inputs : rec.input ? [rec.input] : []) s.disabled = dead;
    if (rec.reset) rec.reset.disabled = dead;
    rec.row.dataset.locked = String(dead);
    if (rec.refusal) rec.refusal.hidden = !dead;
  }

  const root = el("div", "params");
  root.setAttribute("data-params", "");
  const given = Array.isArray(opts.groups) ? opts.groups.filter((g) => g && g.id !== undefined) : [];
  const order = given.map((g) => g.id);
  for (const d of list) if (!order.includes(d.group)) order.push(d.group);
  for (const gid of order) {
    const items = list.map((d, i) => [d, i]).filter(([d]) => d.group === gid)
      .sort((a, b) => (a[0].order - b[0].order) || (a[1] - b[1])).map(([d]) => d);
    if (!items.length) continue;
    const sec = el("section", "params-group");
    sec.dataset.group = gid;
    const g = given.find((x) => x.id === gid);
    sec.appendChild(el("h3", "params-grouptitle", g && (g.label || g.title) ? String(g.label || g.title) : humanise(gid)));
    for (const d of items) sec.appendChild(buildRow(d));
    root.appendChild(sec);
  }

  return {
    root,
    rows,
    problems: first.problems,
    descriptors: list,
    values: snapshot,
    // A preset or URL arrives: validate it (merged over what is showing, unless replace) and repaint, without onChange.
    setValues(next, { replace = false } = {}) {
      const r = validate(list, replace ? next : { ...values, ...(next && typeof next === "object" && !Array.isArray(next) ? next : {}) });
      values = r.values;
      for (const rec of rows.values()) paint(rec);
      return r;
    },
    reset(id) { const rec = rows.get(id); if (rec && !rec.d.derived) commit(rec, validateValue(rec.d, rec.d.default).value); },
    resetAll() { for (const rec of rows.values()) if (!rec.d.derived) commit(rec, validateValue(rec.d, rec.d.default).value); },
    setRecording(on) {
      recording = !!on;
      for (const rec of rows.values()) paint(rec);
    },
  };
}
