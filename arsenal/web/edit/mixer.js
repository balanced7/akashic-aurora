// arsenal/web/edit/mixer.js
// The Mixer: one strip per audio lane (A1..An, named after the source tracks): gain -60..+12 dB, mute, solo, and a
// live peak meter read from the lane's AnalyserNode (playback.js). Gain moves are heard while the slider moves and
// become one undo step when it is released; mute and solo are one step each.

import * as T from "./timeline.js";

const METER_FLOOR_DB = -60;
const METER_TOP_DB = 6;
const HOLD_MS = 1200;

export function createMixer(root, { onChange }) {
  root.innerHTML = "";
  root.classList.add("ed-mixer");
  const strips = new Map(); // laneId -> {node, slider, value, mute, solo, meter, peak, hold, holdAt}
  const empty = document.createElement("p");
  empty.className = "ed-muted";
  empty.textContent = "No audio lanes yet: add a clip with sound.";
  root.append(empty);
  let colors = null;

  function strip(lane) {
    const node = document.createElement("div");
    node.className = "ed-strip";
    const head = document.createElement("div");
    head.className = "ed-strip-head";
    const name = document.createElement("span");
    name.className = "ed-strip-name";
    const value = document.createElement("output");
    value.className = "ed-strip-value";
    const mute = button("M", `Mute ${lane.id}`);
    const solo = button("S", `Solo ${lane.id}`);
    head.append(name, value, mute, solo);
    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = String(T.GAIN_MIN_DB);
    slider.max = String(T.GAIN_MAX_DB);
    slider.step = "0.5";
    slider.className = "ed-gain";
    const meter = document.createElement("canvas");
    meter.className = "ed-meter";
    meter.height = 6;
    meter.setAttribute("aria-hidden", "true");
    node.append(head, slider, meter);

    const s = { node, name, slider, value, mute, solo, meter, peak: -Infinity, hold: -Infinity, holdAt: 0, id: lane.id };
    slider.addEventListener("input", () => {
      value.value = fmtDb(Number(slider.value));
      onChange(s.id, { gain_db: Number(slider.value) }, false);
    });
    slider.addEventListener("change", () => onChange(s.id, { gain_db: Number(slider.value) }, true));
    slider.addEventListener("dblclick", () => {
      slider.value = "0";
      value.value = fmtDb(0);
      onChange(s.id, { gain_db: 0 }, true);
    });
    mute.addEventListener("click", () => onChange(s.id, { mute: mute.getAttribute("aria-pressed") !== "true" }, true));
    solo.addEventListener("click", () => onChange(s.id, { solo: solo.getAttribute("aria-pressed") !== "true" }, true));
    return s;
  }

  function button(text, label) {
    const b = document.createElement("button");
    b.type = "button";
    b.className = "btn ed-mini";
    b.textContent = text;
    b.setAttribute("aria-label", label);
    b.setAttribute("aria-pressed", "false");
    return b;
  }

  const fmtDb = (db) => `${db > 0 ? "+" : ""}${db.toFixed(1)} dB`;

  function render(doc) {
    const seen = new Set();
    for (const lane of doc.lanes.audio) {
      let s = strips.get(lane.id);
      if (!s) { s = strip(lane); strips.set(lane.id, s); }
      seen.add(lane.id);
      if (!s.node.isConnected) root.append(s.node);
      s.name.textContent = `${lane.id} ${lane.label || ""}`.trim();
      s.slider.setAttribute("aria-label", `${lane.id} ${lane.label || ""} gain in dB`.trim());
      if (document.activeElement !== s.slider) s.slider.value = String(lane.gain_db || 0);
      s.value.value = fmtDb(Number(s.slider.value));
      s.mute.setAttribute("aria-pressed", String(!!lane.mute));
      s.solo.setAttribute("aria-pressed", String(!!lane.solo));
      s.node.classList.toggle("silent", !T.laneAudible(doc, lane.id));
    }
    for (const [id, s] of strips) {
      if (!seen.has(id)) { s.node.remove(); strips.delete(id); }
    }
    // lane order, moving nodes only when it is wrong: moving a node blurs the slider being dragged or keyed
    const want = doc.lanes.audio.map((l) => strips.get(l.id).node);
    const have = [...root.querySelectorAll(":scope > .ed-strip")];
    if (want.some((n, i) => have[i] !== n)) for (const n of want) root.append(n);
    empty.hidden = strips.size > 0;
  }

  function readColors() {
    const cs = getComputedStyle(document.documentElement);
    return {
      ground: cs.getPropertyValue("--ground").trim(), audio: cs.getPropertyValue("--audio").trim(),
      accent: cs.getPropertyValue("--accent").trim(), control: cs.getPropertyValue("--control").trim(),
      ink3: cs.getPropertyValue("--ink-3").trim(),
    };
  }
  window.matchMedia("(prefers-color-scheme: light)").addEventListener("change", () => { colors = null; });

  const frac = (db) => Math.max(0, Math.min(1, (db - METER_FLOOR_DB) / (METER_TOP_DB - METER_FLOOR_DB)));

  /** levels: {laneId: peak dBFS}. Draws each meter: teal to -12 dB, amber to -3 dB, rose above, with a peak hold. */
  function meter(levels, now = performance.now()) {
    if (!colors) colors = readColors();
    for (const [id, s] of strips) {
      const db = levels && Number.isFinite(levels[id]) ? levels[id] : -Infinity;
      s.peak = Math.max(db, s.peak - 1.2); // ~70 dB/s fall at 60 fps
      if (db >= s.hold || now - s.holdAt > HOLD_MS) { s.hold = db; s.holdAt = now; }
      const c = s.meter;
      const w = c.clientWidth || 200;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      if (c.width !== Math.round(w * dpr)) c.width = Math.round(w * dpr);
      const g = c.getContext("2d");
      g.setTransform(dpr, 0, 0, dpr, 0, 0);
      g.fillStyle = colors.ground;
      g.fillRect(0, 0, w, 6);
      const x = frac(s.peak) * w;
      const x12 = frac(-12) * w, x3 = frac(-3) * w;
      g.fillStyle = colors.audio;
      g.fillRect(0, 0, Math.min(x, x12), 6);
      if (x > x12) { g.fillStyle = colors.accent; g.fillRect(x12, 0, Math.min(x, x3) - x12, 6); }
      if (x > x3) { g.fillStyle = colors.control; g.fillRect(x3, 0, x - x3, 6); }
      if (Number.isFinite(s.hold)) {
        g.fillStyle = s.hold > -3 ? colors.control : colors.ink3;
        g.fillRect(Math.round(frac(s.hold) * w) - 1, 0, 2, 6);
      }
      g.fillStyle = colors.ink3;
      g.fillRect(Math.round(frac(0) * w), 0, 1, 6);
    }
  }

  return { render, meter };
}
