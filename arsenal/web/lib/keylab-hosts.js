// The KeyLab on pages that already exist, without editing them: arsenal/web/lib/keylab-hosts.js (ES module).
//
// A binder (lib/keylab-client.js) drives a "host": a list of parameters with get and set, and optionally scenes. This
// file builds hosts for the house's shader surfaces from what each page already exposes, so the page itself is not
// touched:
//
//   playHost(win)       Play (/play on the arsenal server): the macro rack's own sliders (input.macro-range, aria-label
//                       k1..k8, hue, intensity), set the way a hand sets them (value + an "input" event, so Play's own
//                       applyContinuous runs and its take ledger records it), and window.__play for the presets.
//   vfxBenchHost(win)   the VFX Bench (/vfx on the Bifrost console): AgentAvatar.PARAMS and DIALS on the bench's `av`,
//                       set the way its own sliders set them (av.target and av.cur, then syncAll and emit once a
//                       frame), its presets (/vfx/presets) as scenes, and a "tint hue" made from the state tint.
//   rangeHost(root)     any page of house controls (lib/params-ui.js rows, e.g. the Shader Lab's Inspector) or plain
//                       range inputs: each slider becomes a parameter.
//   mountKeyLab(opts)   picks the right host for a window, makes the client, the binder and the panel, and returns
//                       them; lib/keylab-mount.js calls it on import.
import { createBinder, createKeyLabClient } from "./keylab-client.js";
import { mountKeyLabHud, wirePadLights, wireScreen } from "./keylab-desk.js";

const clamp = (x, a, b) => Math.min(Math.max(x, a), b);
const num = (v, d = 0) => (typeof v === "number" && Number.isFinite(v) ? v : d);

// ------------------------------------------------------------------------------------------------- Play --
export function playHost(win) {
  const doc = win.document;
  const range = (target) => doc.querySelector(`input.macro-range[aria-label="${target}"]`);
  const nameOf = (target) => {
    const r = range(target);
    const row = r && r.closest(".macro");
    if (!row || row.classList.contains("unnamed")) return null;
    const n = row.querySelector(".macro-name");
    return n ? n.textContent.trim() : null;
  };
  const listeners = new Set();
  const onInput = (ev) => {
    const t = ev.target;
    if (!t || !t.classList || !t.classList.contains("macro-range") || ev.__keylab) return;
    for (const fn of listeners) fn(t.getAttribute("aria-label"));
  };
  doc.addEventListener("input", onInput, true);
  const play = () => win.__play || null;
  return {
    kind: "play",
    params() {
      const out = [];
      for (let k = 1; k <= 8; k++) {
        const n = nameOf(`k${k}`);
        if (n && n !== "—") out.push({ id: `k${k}`, label: n, min: 0, max: 1, step: 0.01, unit: "ratio" });
      }
      if (range("intensity")) out.push({ id: "intensity", label: "intensity", min: 0, max: 1, step: 0.01, unit: "ratio", role: "master" });
      if (range("hue")) out.push({ id: "hue", label: "hue", min: 0, max: 360, step: 1, unit: "deg", role: "hue" });
      return out;
    },
    get(id) {
      const r = range(id);
      if (!r) return 0;
      const norm = Number(r.value) / 1000;
      return id === "hue" ? norm * 360 : norm;
    },
    set(id, v) {
      const r = range(id);
      if (!r) return;
      const norm = id === "hue" ? v / 360 : v;
      r.value = String(Math.round(clamp(norm, 0, 1) * 1000));
      const Ev = win.Event;
      const ev = new Ev("input", { bubbles: true });
      ev.__keylab = true;
      r.dispatchEvent(ev);
    },
    scenes() {
      const p = play();
      return p ? p.presets().filter((x) => !x.broken).map((x) => ({ id: x.id, label: x.name })) : [];
    },
    scene() { const p = play(); const a = p && p.active(); return a ? a.id : null; },
    selectScene(id) { const p = play(); return p ? p.select(id) !== false : false; },
    onExternal(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    destroy() { doc.removeEventListener("input", onInput, true); },
  };
}

// --------------------------------------------------------------------------------------------- VFX Bench --
function rgbToHsv([r, g, b]) {
  const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
  let h = 0;
  if (d > 1e-9) h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return [((h * 60) + 360) % 360, mx > 0 ? d / mx : 0, mx];
}
function hsvToRgb([h, s, v]) {
  const f = (n) => { const k = (n + h / 60) % 6; return v - v * s * Math.max(0, Math.min(k, 4 - k, 1)); };
  return [f(5), f(3), f(1)];
}
export function vfxBenchHost(win) {
  const AA = win.AgentAvatar;
  if (!AA || !win.av) throw new Error("this is not the VFX Bench (no AgentAvatar and av)");
  const av = () => win.av;
  const params = (AA.PARAMS || []).map((p) => ({ id: `p.${p.k}`, k: p.k, label: p.label || p.k, min: p.min, max: p.max, step: p.step, unit: "ratio",
    role: p.k === "dim" ? "master" : undefined }));
  const dials = (AA.DIALS || []).map((d) => ({ id: `d.${d.k}`, k: d.k, label: d.label || d.k, min: d.min, max: d.max, step: d.step, unit: "ratio" }));
  const hue = { id: "tint.hue", label: "tint hue", min: 0, max: 360, step: 1, unit: "deg", role: "hue" };
  let frame = 0, presetNames = [], current = null;
  const flush = () => {
    frame = 0;
    try { if (typeof win.syncAll === "function") win.syncAll(); if (typeof win.emit === "function") win.emit(); } catch { /* the bench repaints itself next time */ }
  };
  const later = () => { if (!frame) frame = win.requestAnimationFrame(flush); };
  const refresh = async () => {
    try { presetNames = Object.keys(await (await win.fetch("/vfx/presets")).json() || {}).sort(); } catch { presetNames = []; }
  };
  refresh();
  const listeners = new Set();
  // A hand on one of the bench's own sliders: the slider's label names the parameter (the bench builds both from the
  // same PARAMS / DIALS entry), so only that parameter's faders let go.
  const onInput = (ev) => {
    const box = ev.target && ev.target.closest && ev.target.closest("#params, #dials");
    if (!box) return;
    const text = ev.target.closest("label")?.querySelector(".lab span")?.textContent?.trim();
    const hit = [...params, ...dials].filter((p) => p.label === text);
    for (const fn of listeners) for (const p of hit.length ? hit : [...params, ...dials]) fn(p.id);
  };
  win.document.addEventListener("input", onInput, true);
  return {
    kind: "vfx-bench",
    params: () => [...params, ...dials, hue],
    get(id) {
      const a = av();
      if (id === "tint.hue") return rgbToHsv((a.target && a.target.tint) || [1, 1, 1])[0];
      if (id.startsWith("p.")) return num(a.target && a.target[id.slice(2)]);
      if (id.startsWith("d.")) return num(a[id.slice(2)]);
      return 0;
    },
    set(id, v) {
      const a = av();
      if (id === "tint.hue") {
        const hsv = rgbToHsv(a.target.tint || [1, 1, 1]);
        const rgb = hsvToRgb([v, Math.max(hsv[1], 0.35), Math.max(hsv[2], 0.5)]);
        a.target.tint = rgb.slice(); if (a.cur) a.cur.tint = rgb.slice();
      } else if (id.startsWith("p.")) {
        const k = id.slice(2);
        a.target[k] = v; if (a.cur) a.cur[k] = v;
        if (win.dirty && typeof win.dirty === "object") win.dirty[k] = true;   // the bench keeps unsaved tuning across a subject switch
      } else if (id.startsWith("d.")) {
        const k = id.slice(2);
        if (k === "rate" && typeof a.setRate === "function") a.setRate(v); else a[k] = v;
      }
      later();
    },
    scenes: () => presetNames.map((n) => ({ id: n, label: n })),
    scene: () => current,
    selectScene(id) {
      const sel = win.document.getElementById("presets");
      if (!sel || typeof win.loadPreset !== "function") return false;
      if (![...sel.options].some((o) => o.value === id)) return false;
      sel.value = id;
      current = id;
      Promise.resolve(win.loadPreset()).catch(() => {});
      return true;
    },
    onExternal(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    refresh,
    destroy() { win.document.removeEventListener("input", onInput, true); },
  };
}

// --------------------------------------------------------------------------------------- any range inputs --
export function rangeHost(root) {
  const doc = root.ownerDocument || root;
  const win = doc.defaultView;
  const inputs = () => [...root.querySelectorAll('input[type="range"]')].filter((i) => !i.disabled && i.offsetParent !== null);
  const idOf = (i, n) => i.id || (i.getAttribute("aria-label") ? "aria:" + i.getAttribute("aria-label") : `range${n}`);
  const labelOf = (i) => {
    const row = i.closest(".params-row");
    const l = (row && row.querySelector(".params-label")) || (i.id && doc.querySelector(`label[for="${i.id}"]`)) || i.closest("label");
    return ((l && l.textContent) || i.getAttribute("aria-label") || i.id || "slider").trim().split("\n")[0].slice(0, 40);
  };
  const find = (id) => inputs().find((i, n) => idOf(i, n) === id) || null;
  const listeners = new Set();
  const onInput = (ev) => {
    if (ev.__keylab || !ev.target || ev.target.type !== "range") return;
    const n = inputs().indexOf(ev.target);
    if (n >= 0) for (const fn of listeners) fn(idOf(ev.target, n));
  };
  doc.addEventListener("input", onInput, true);
  return {
    kind: "ranges",
    params: () => inputs().map((i, n) => {
      const min = Number(i.min || 0), max = Number(i.max || 100), step = i.step && i.step !== "any" ? Number(i.step) : undefined;
      return { id: idOf(i, n), label: labelOf(i), min, max: max > min ? max : min + 1, step, unit: "ratio" };
    }),
    get(id) { const i = find(id); return i ? Number(i.value) : 0; },
    set(id, v) {
      const i = find(id);
      if (!i) return;
      i.value = String(v);
      const ev = new win.Event("input", { bubbles: true });
      ev.__keylab = true;
      i.dispatchEvent(ev);
    },
    onExternal(fn) { listeners.add(fn); return () => listeners.delete(fn); },
    destroy() { doc.removeEventListener("input", onInput, true); },
  };
}

// ------------------------------------------------------------------------------------------------- mount --
// opts: win (the page to drive; default this window), doc (where the panel goes; default this document), host (a
// ready host), namespace, title, parent, url (the engine's events address), overlay.
export function mountKeyLab(opts = {}) {
  const win = opts.win || window;
  let host = opts.host || null, kind = "custom";
  if (!host) {
    if (win.__play && win.document.querySelector("input.macro-range")) { host = playHost(win); kind = "play"; }
    else if (win.AgentAvatar && win.av) { host = vfxBenchHost(win); kind = "vfx-bench"; }
    else { host = rangeHost(win.document.body); kind = "ranges"; }
  } else kind = host.kind || kind;
  const client = createKeyLabClient(opts.url ? { url: opts.url } : {});
  const binder = createBinder(client, host, { namespace: opts.namespace || `mount-${kind}` });
  const offExternal = host.onExternal ? host.onExternal((id) => binder.notifyExternal(id)) : null;
  const hud = mountKeyLabHud({ doc: opts.doc || document, client, binder, parent: opts.parent, overlay: opts.overlay,
    title: opts.title || `KeyLab · ${kind}`, scenes: () => (host.scenes ? host.scenes() : []), scene: () => (host.scene ? host.scene() : null),
    collapsed: opts.collapsed });
  const offLights = wirePadLights(client, binder);
  const offScreen = wireScreen(client, binder);
  client.start();
  return {
    kind, host, client, binder, hud,
    destroy() { offLights(); offScreen(); offExternal && offExternal(); hud.destroy(); binder.destroy(); client.stop(); host.destroy && host.destroy(); },
  };
}
