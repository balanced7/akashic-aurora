// Score lab: arsenal/web/piano-lab-score.js (ES module, page code: DOM, canvas, Web MIDI, WebGL). Slice LS5 of
// research/in-flight/live-sheet-music-2026-09-14/live-sheet-music-plan.md (section 9 LS5, receipts LR11a-g), amended by
// plan-amendments.md section 0 rules 1 and 4 (house engraver; replay first, Web MIDI a bonus) and ls1-rulings.md (a new
// tracker on every seek; the dimmed "hold" header). The page draws the 9:16 score band from the pure modules under
// piano/score/ (ribbon.js, layout.js, paint.js, engrave.js); nothing here is recorded, saved or sent anywhere.
//
// Input: an events.jsonl picked from disk, or a path this page's server serves (a practice log is never committed).
// Live MIDI (bonus) feeds the same ribbon on the page clock. A seek builds a new ribbon, so a new transcriber and a new
// beat tracker (beat.js has a monotonic clock), replays the take up to the target with the taps and presses made before
// it, and repaints; presses after the target are dropped with the abandoned future.
// Tiles: one canvas per bar. An open bar repaints (paint.js) when its layout changes; a settling bar re-engraves in light
// ink (engrave.js); a settled bar is engraved once in full ink and never drawn on again (LR11d counts drawing calls on a
// tile's context after it settled). The G1 bench (LR11a-c, LR11g) times the painters on bench.js fixtures and texture
// uploads in a running three.js scene (raw WebGL2 when three.js cannot load).
//
// window.scoreLab (for the headless check): loadText, loadUrl, seek, run, press, bench, stats, fonts.

import { createLayout, layoutBar, modelBar, overlaps } from "./piano/score/layout.js";
import { createRibbon } from "./piano/score/ribbon.js";
import { createHouseEngraver } from "./piano/score/engrave.js";
import { paintStaves, paintHeader, paintTape, paintOpenBar, paintPedalLine, BRAVURA_URL, PAINT_COLORS } from "./piano/score/paint.js";
import { denseBar, tapeWindow, BENCH_SIZES } from "./piano/score/bench.js";
import { spellMidi } from "./piano/spell.js";

const $ = (id) => document.getElementById(id);
const L = createLayout({ framing: "9:16" });
const VIEW_TOP = Math.floor(L.header.y - 14);
const VIEW_H = Math.ceil(L.band.y1 + 20 - VIEW_TOP);
const canvas = $("score");
canvas.height = VIEW_H;
const ctx = canvas.getContext("2d");
const spell = (midis, key) => midis.map((m) => spellMidi(m, key));
const fonts = { smufl: false, error: null };
const engraver = createHouseEngraver({ now: () => performance.now() });
const ORDER = { off: 0, sound_end: 1, pedal: 2, on: 3 };
const TICK_MS = 250;
const DRAW_METHODS = ["fillText", "fillRect", "stroke", "fill", "clearRect", "drawImage", "strokeText"];

const S = {
  events: [], beats: null, one: null, first: 0, last: 0, t: 0, playing: false, speed: 1, meter0: "4/4", source: null,
  ribbon: null, cursor: 0, nextTick: 0, controls: [], applied: 0,
  tiles: new Map(), settledEver: new Set(), pedalSegs: [], live: false, liveT0: 0, livePedal: false, underPedal: new Set(),
  counters: { ribbons: 0, seeks: 0, livePaints: 0, openPaints: 0, lightEngraves: 0, settledEngraves: 0, drawCallsAfterSettle: 0, settledRepaints: 0, settledReuploads: 0, tileUploads: 0, rangeErrors: 0 },
  frameMs: [], tickMs: [], openMs: [], lightMs: [], fullMs: [], uploadMs: [],
};
const push = (arr, v, cap = 4000) => { arr.push(v); if (arr.length > cap) arr.splice(0, arr.length - cap); };
export const pct = (xs, p) => { if (!xs.length) return null; const s = [...xs].sort((a, b) => a - b); return s[Math.min(s.length - 1, Math.max(0, Math.ceil((p / 100) * s.length) - 1))]; };
const summary = (xs) => ({ n: xs.length, p50: r3(pct(xs, 50)), p95: r3(pct(xs, 95)), max: r3(xs.length ? Math.max(...xs) : null), mean: r3(xs.length ? xs.reduce((a, b) => a + b, 0) / xs.length : null) });
const r3 = (v) => (v == null ? null : Math.round(v * 1000) / 1000);

// --------------------------------------------------------------------------------------------- fonts ---
const fontReady = (async () => {
  try {
    const face = new FontFace("Bravura", `url(${BRAVURA_URL}) format("woff2")`);
    await Promise.race([face.load(), new Promise((_, rej) => setTimeout(() => rej(new Error("timed out after 9 s")), 9000))]);
    document.fonts.add(face);
    fonts.smufl = true;
  } catch (e) { fonts.error = "Bravura: " + String((e && e.message) || e); }
  engraver.ready(fonts);
  setStatus();
  return { ...fonts };
})();

// ------------------------------------------------------------------------------------------- loading ---
export function parseEvents(text) {
  const t = String(text || "").trim();
  let rows = [];
  if (t.startsWith("[")) rows = JSON.parse(t);
  else rows = t.split(/\r?\n/).filter((l) => l.trim()).map((l) => { try { return JSON.parse(l); } catch { return null; } });
  return rows.filter((e) => e && typeof e.t_ms === "number" && e.kind in ORDER).sort((a, b) => a.t_ms - b.t_ms || ORDER[a.kind] - ORDER[b.kind]);
}
// a take: events.jsonl, a JSON array of events, or { events, beats_ms, one_ms, meter } (fixed beats: the jam rung stand-in)
export function parseTake(text) {
  const t = String(text || "").trim();
  if (t.startsWith("{")) {
    let o = null;
    try { o = JSON.parse(t); } catch { o = null; }   // an events.jsonl also starts with "{": one object per line
    if (o && Array.isArray(o.events)) return { events: parseEvents(JSON.stringify(o.events)), beats: Array.isArray(o.beats_ms) ? o.beats_ms : null, one: o.one_ms ?? null, meter: o.meter || null };
  }
  return { events: parseEvents(t), beats: null, one: null, meter: null };
}
async function loadText(text, label, { meter = "4/4" } = {}) {
  await fontReady;
  const take = parseTake(text);
  const evs = take.events;
  S.beats = take.beats; S.one = take.one;
  if (take.meter) meter = take.meter;
  if (!evs.length) throw new Error("no on/off/pedal/sound_end events with t_ms");
  stopLive();
  S.events = evs; S.first = evs[0].t_ms; S.last = evs[evs.length - 1].t_ms + 2500; S.controls = []; S.source = label; S.meter0 = meter;
  $("meter").value = meter;
  seek(0);
  setStatus();
  return { events: evs.length, seconds: (S.last - S.first) / 1000 };
}
async function loadUrl(url, opts) {
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) throw new Error(`${url}: HTTP ${res.status}`);
  return loadText(await res.text(), url, opts);
}

// ------------------------------------------------------------------------------------------ the ribbon ---
function newRibbon(meter) {
  disposeTiles();
  S.settledEver = new Set();
  S.ribbon = createRibbon({ spell, layout: L, options: { meter, ...(S.beats && !S.live ? { beats: S.beats, one: S.one } : {}) } });
  S.counters.ribbons++;
  S.cursor = 0; S.applied = 0;
  S.nextTick = Math.floor(S.first / TICK_MS) * TICK_MS + TICK_MS;
  S.pedalSegs = [];
}
function seek(ms) {
  if (S.live) return;
  S.t = Math.max(0, Math.min(S.last - S.first, ms));
  const target = S.first + S.t;
  S.controls = S.controls.filter((c) => c.t <= target);
  newRibbon(S.meter0);
  S.counters.seeks++;
  advanceTo(target, false);
  afterTick();
}
function feed(tk) {
  const R = S.ribbon, E = S.events;
  for (;;) {
    const e = S.cursor < E.length && E[S.cursor].t_ms <= tk ? E[S.cursor] : null;
    const c = S.applied < S.controls.length && S.controls[S.applied].t <= tk ? S.controls[S.applied] : null;
    if (!e && !c) break;
    if (c && (!e || c.t <= e.t_ms)) { applyControl(c); S.applied++; continue; }
    if (e.kind === "on") R.noteOn(e.note, e.vel ?? 64, e.t_ms);
    else if (e.kind === "off") R.noteOff(e.note, e.t_ms);
    else if (e.kind === "pedal") R.pedal(!!e.down, e.value ?? (e.down ? 127 : 0), e.t_ms);
    else R.soundEnd(e.note, e.t_ms, e.by ?? null);
    S.cursor++;
  }
}
function applyControl(c) {
  const R = S.ribbon;
  if (c.kind === "tap") R.tap(c.t);
  else if (c.kind === "one") R.thisIsOne(c.t);
  else if (c.kind === "level") R.chooseLevel(c.arg);
  else if (c.kind === "meter") R.setMeter(c.arg);
}
function advanceTo(target, paint) {
  const R = S.ribbon;
  while (S.nextTick <= target) {
    const tk = S.nextTick;
    feed(tk);
    const t0 = performance.now();
    try { R.tick(tk); } catch (e) { if (e instanceof RangeError) S.counters.rangeErrors++; throw e; }
    push(S.tickMs, performance.now() - t0);
    if (paint) afterTick();
    S.nextTick += TICK_MS;
  }
}
function press(kind, arg = null) {
  if (!S.ribbon) return null;
  const t = S.live ? liveNow() : S.first + S.t;
  const c = { t, kind, arg };
  if (!S.live) S.controls = S.controls.filter((x) => x.t <= t);
  S.controls.push(c);
  if (S.live) { applyControl(c); S.applied = S.controls.length; }
  return c;
}

// ---------------------------------------------------------------------------------------------- tiles ---
function newTile(index) {
  const cv = document.createElement("canvas");
  cv.width = 8; cv.height = L.tileH;
  const c = cv.getContext("2d");
  const tile = { index, canvas: cv, ctx: c, sig: null, settled: false, block: null, calls: 0, callsAfterSettle: 0, texture: null, uploads: 0 };
  for (const m of DRAW_METHODS) {
    const orig = c[m].bind(c);
    c[m] = (...a) => { tile.calls++; if (tile.settled) { tile.callsAfterSettle++; S.counters.drawCallsAfterSettle++; } return orig(...a); };
  }
  S.tiles.set(index, tile);
  return tile;
}
function sizeTile(tile, width) {
  const w = Math.max(8, Math.ceil(width + 2));
  if (tile.canvas.width !== w) tile.canvas.width = w;
  else tile.ctx.clearRect(0, 0, tile.canvas.width, tile.canvas.height);
}
function disposeTile(tile) { if (tile.texture) { GL.disposeTexture(tile.texture); tile.texture = null; } tile.canvas.width = 1; tile.disposed = true; }
function disposeTiles() { for (const t of S.tiles.values()) disposeTile(t); S.tiles.clear(); }

function afterTick() {
  const R = S.ribbon;
  if (!R) return;
  const v = R.view();
  const seen = new Set();
  for (const b of v.live) {
    seen.add(b.index);
    const tile = S.tiles.get(b.index) || newTile(b.index);
    tile.block = b;
    if (tile.settled || tile.sig === b.sig) continue;
    sizeTile(tile, b.layout.width);
    const t0 = performance.now();
    if (b.state === "open") { paintOpenBar(tile.ctx, L, b.layout, { x: 0, fonts }); push(S.openMs, performance.now() - t0); S.counters.openPaints++; }
    else { engraver.engraveBar(tile.ctx, b.model, { L, ink: "light", layout: b.layout }); push(S.lightMs, performance.now() - t0); S.counters.lightEngraves++; }
    tile.sig = b.sig;
    S.counters.livePaints++;
  }
  for (const b of v.blocks) {
    seen.add(b.index);
    let tile = S.tiles.get(b.index);
    if (tile && tile.settled) continue;           // frozen: engraved once, never drawn on again
    if (!tile) tile = newTile(b.index);
    tile.block = b;
    if (S.settledEver.has(b.index)) S.counters.settledRepaints++;   // a settled bar engraved a second time (LR11d)
    S.settledEver.add(b.index);
    sizeTile(tile, b.layout.width);
    const t0 = performance.now();
    engraver.engraveBar(tile.ctx, b.model, { L, ink: "full", layout: b.layout });
    push(S.fullMs, performance.now() - t0);
    tile.settled = true;
    S.counters.settledEngraves++;
    if (GL.ready) GL.uploadTile(tile);
  }
  const left = v.scrollX - (L.playheadX - L.band.x0) - 300;
  for (const [i, tile] of S.tiles) {
    if (!seen.has(i) && !tile.settled) { disposeTile(tile); S.tiles.delete(i); continue; }   // a live bar that collapsed
    if (tile.settled && tile.block && tile.block.x1 < left && !tile.disposed) { disposeTile(tile); }
    if (tile.disposed && !seen.has(i)) S.tiles.delete(i);   // the ribbon no longer holds the block: it never comes back
  }
  S.pedalSegs = R.pedalSegments(v.T - 30000);
}

// --------------------------------------------------------------------------------------------- render ---
function render() {
  const t0 = performance.now();
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.fillStyle = PAINT_COLORS.bg; ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.translate(0, -VIEW_TOP);
  const R = S.ribbon;
  if (R) {
    const v = R.view();
    const off = L.playheadX - L.band.x0 - v.scrollX;
    const xa = -off - 60, xb = -off + L.band.w + 60;
    ctx.save();
    ctx.translate(L.band.x0, L.band.y0);
    ctx.beginPath(); ctx.rect(0, -4 * L.sp, L.band.w, L.tileH + 4 * L.sp); ctx.clip();
    paintStaves(ctx, L, { width: L.band.w, clefs: v.clefs, fifths: v.fifths ?? 0, fonts, clefColumn: false });
    for (const tile of S.tiles.values()) {
      const b = tile.block;
      if (!b || tile.disposed) continue;
      const x = b.x0 + off;
      if (x + tile.canvas.width < 0 || x > L.band.w) continue;
      ctx.drawImage(tile.canvas, x, 0);
    }
    const cols = R.columnsIn(xa, xb);
    paintTape(ctx, L, cols, { dx: off, fonts, endX: R.endX, ticks: R.ticksIn(xa, xb), freely: cols.filter((c) => c.freely).map((c) => c.x) });
    paintPedalLine(ctx, L, S.pedalSegs, { dx: off });
    ctx.strokeStyle = "rgba(159,211,199,0.35)"; ctx.lineWidth = 1;
    ctx.beginPath(); ctx.moveTo(L.playheadX - L.band.x0, 0); ctx.lineTo(L.playheadX - L.band.x0, L.tileH); ctx.stroke();
    paintStaves(ctx, L, { width: 0, clefs: v.clefs, fifths: v.fifths ?? 0, fonts, clefColumn: true });
    ctx.restore();
    paintHeader(ctx, L, v.header, { fonts });
  } else {
    ctx.fillStyle = PAINT_COLORS.faint; ctx.font = "28px sans-serif";
    ctx.fillText("Load an events.jsonl to replay, or connect MIDI.", L.band.x0, L.band.y0 + 120);
  }
  push(S.frameMs, performance.now() - t0);
}

// ------------------------------------------------------------------------------------------- the loop ---
let lastFrame = null, uiAt = 0, dragging = false;
function frame(now) {
  if (lastFrame != null && S.ribbon) {
    if (S.live) advanceLive();
    else if (S.playing) {
      S.t = Math.min(S.last - S.first, S.t + Math.min(250, now - lastFrame) * S.speed);
      advanceTo(S.first + S.t, true);
      if (S.t >= S.last - S.first) setPlaying(false);
    }
  }
  lastFrame = now;
  render();
  if (now - uiAt > 250) { uiAt = now; ui(); }
  requestAnimationFrame(frame);
}
// headless driver: replay [from, to] ms of take time in frames of frameMs, rendering each frame; returns stats
function run({ to = null, seconds = null, frameMs = 1000 / 60, speed = 1, budgetMs = 60000 } = {}) {
  const end = to != null ? to : seconds != null ? S.t + seconds * 1000 : S.last - S.first;
  const wall = performance.now();
  while (S.t < end && performance.now() - wall < budgetMs) {
    S.t = Math.min(end, S.t + frameMs * speed);
    advanceTo(S.first + S.t, true);
    render();
  }
  ui();
  return stats();
}

// ------------------------------------------------------------------------------------------ live MIDI ---
const liveNow = () => performance.now() - S.liveT0;
async function startLive() {
  if (!navigator.requestMIDIAccess) { $("midi-status").textContent = "no Web MIDI in this browser"; return false; }
  let access;
  try { access = await navigator.requestMIDIAccess(); } catch (e) { $("midi-status").textContent = "MIDI refused: " + ((e && e.message) || e); return false; }
  await fontReady;
  S.live = true; setPlaying(false);
  S.events = []; S.controls = []; S.first = 0; S.last = 0; S.source = "live MIDI";
  S.liveT0 = performance.now(); S.livePedal = false; S.underPedal.clear();
  newRibbon($("meter").value);
  const names = [];
  for (const input of access.inputs.values()) { input.onmidimessage = onMidi; names.push(input.name); }
  $("midi-status").textContent = names.length ? `listening: ${names.join(", ")}` : "no MIDI inputs";
  setStatus();
  return true;
}
function stopLive() { S.live = false; }
function onMidi(ev) {
  if (!S.live || !S.ribbon) return;
  const [st, d1, d2] = ev.data, cmd = st & 0xf0, t = liveNow(), R = S.ribbon;
  if (cmd === 0x90 && d2 > 0) R.noteOn(d1, d2, t);
  else if (cmd === 0x80 || (cmd === 0x90 && d2 === 0)) { R.noteOff(d1, t); if (S.livePedal) S.underPedal.add(d1); else R.soundEnd(d1, t, "release"); }
  else if (cmd === 0xb0 && d1 === 64) {
    const down = d2 >= 64;
    if (down !== S.livePedal) {
      S.livePedal = down; R.pedal(down, d2, t);
      if (!down) { for (const n of S.underPedal) R.soundEnd(n, t, "pedal"); S.underPedal.clear(); }
    }
  }
}
function advanceLive() {
  const now = liveNow();
  if (S.nextTick === TICK_MS && now < TICK_MS) return;
  while (S.nextTick <= now) {
    const t0 = performance.now();
    S.ribbon.tick(S.nextTick);
    push(S.tickMs, performance.now() - t0);
    afterTick();
    S.nextTick += TICK_MS;
  }
}

// ------------------------------------------------------------------------------------------ WebGL (G1) ---
const GL = {
  ready: false, kind: null, error: null, renderer: null, three: null, scene: null, camera: null, group: null, gl: null, raw: null,
  async init() {
    if (this.ready || this.kind) return this;
    const cv = $("gl");
    try {
      const THREE = await Promise.race([import("three"), new Promise((_, rej) => setTimeout(() => rej(new Error("three.js import timed out")), 8000))]);
      this.three = THREE;
      this.renderer = new THREE.WebGLRenderer({ canvas: cv, antialias: false, alpha: false, preserveDrawingBuffer: false });
      this.renderer.setPixelRatio(1);
      this.renderer.setSize(cv.width, cv.height, false);
      this.gl = this.renderer.getContext();
      this.scene = new THREE.Scene();
      this.camera = new THREE.OrthographicCamera(0, cv.width * 4, cv.height * 4, 0, -10, 10);
      this.group = new THREE.Group();
      this.scene.add(this.group);
      this.kind = "three r" + THREE.REVISION;
    } catch (e) {
      this.error = String((e && e.message) || e);
      const gl = cv.getContext("webgl2");
      if (!gl) { this.kind = "none"; return this; }
      this.gl = gl; this.kind = "raw WebGL2 (three.js unavailable: " + this.error + ")";
    }
    const dbg = this.gl.getExtension("WEBGL_debug_renderer_info");
    this.info = { version: this.gl.getParameter(this.gl.VERSION), renderer: dbg ? this.gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : this.gl.getParameter(this.gl.RENDERER) };
    this.ready = true;
    const loop = () => { this.renderFrame(); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
    return this;
  },
  renderFrame() {
    if (this.renderer) {
      this.group.position.x = -((performance.now() / 10) % 2000);
      this.renderer.render(this.scene, this.camera);
    } else if (this.gl) { this.gl.clearColor(0.03, 0.03, 0.05, 1); this.gl.clear(this.gl.COLOR_BUFFER_BIT); }
  },
  makeTexture(source) {
    if (this.renderer) {
      const T = this.three, tex = new T.CanvasTexture(source);
      tex.minFilter = T.LinearFilter; tex.generateMipmaps = false;
      const mesh = new T.Mesh(new T.PlaneGeometry(source.width, source.height), new T.MeshBasicMaterial({ map: tex, transparent: true }));
      mesh.position.set(this.group.children.length * 420 + source.width / 2, source.height / 2 + 40, 0);
      this.group.add(mesh);
      if (this.group.children.length > 24) { const old = this.group.children[0]; this.group.remove(old); old.geometry.dispose(); old.material.map && old.material.map.dispose(); old.material.dispose(); }
      return { tex, mesh, source };
    }
    const gl = this.gl, tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    return { tex, source };
  },
  // one upload of the texture's canvas, synchronised with gl.finish(); -> ms
  upload(t, { finish = true } = {}) {
    const gl = this.gl, t0 = performance.now();
    if (this.renderer) { t.tex.needsUpdate = true; this.renderer.initTexture(t.tex); }
    else { gl.bindTexture(gl.TEXTURE_2D, t.tex); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, t.source); }
    if (finish) gl.finish();
    return performance.now() - t0;
  },
  uploadTile(tile) {
    if (tile.texture) { S.counters.settledReuploads++; return; }
    tile.texture = this.makeTexture(tile.canvas);
    push(S.uploadMs, this.upload(tile.texture));
    tile.uploads++; S.counters.tileUploads++;
  },
  disposeTexture(t) {
    if (!t) return;
    if (this.renderer && t.mesh) { this.group.remove(t.mesh); t.mesh.geometry.dispose(); t.mesh.material.dispose(); t.tex.dispose(); }
    else if (this.gl && t.tex && !this.renderer) this.gl.deleteTexture(t.tex);
  },
};

// ------------------------------------------------------------------------------------------- G1 bench ---
const nextFrame = () => new Promise((res) => requestAnimationFrame(() => res()));
function timeIt(fn, n) { const xs = []; for (let i = 0; i < n; i++) { const t0 = performance.now(); fn(i); xs.push(performance.now() - t0); } return xs; }
async function bench({ n = 200, uploadFrames = 60, uploadsPerFrame = 5, warm = 20 } = {}) {
  await fontReady;
  await GL.init();
  $("bench-state").textContent = "running…";
  const out = { api: "arsenal.piano.score.lab-bench/v0", at: new Date().toISOString(), fonts: { ...fonts }, gl: { kind: GL.kind, ...(GL.info || {}) }, n, lr11a: {}, lr11b: {}, lr11c: {}, lr11g: {} };
  // the page clock's resolution (headless Chrome coarsens performance.now() without cross-origin isolation): per-call
  // p95 values at or near it are bounds, not measurements
  { let r = Infinity, last = performance.now(); for (let i = 0; i < 200000 && r > 0.001; i++) { const t = performance.now(); if (t > last) { r = Math.min(r, t - last); last = t; } } out.timerResolutionMs = r3(r); }
  const cv = document.createElement("canvas");
  cv.width = 1600; cv.height = L.tileH;
  const c2 = cv.getContext("2d");
  const meter = { label: "4/4", beats: 4, beatType: 4, tactus: 4, compound: false, beatTicks: 24, barTicks: 96 };
  const spelledOf = (p) => { const s = spellMidi(p.note, null); return { letter: s.letter, acc: s.acc, octave: s.octave }; };
  for (const onsets of BENCH_SIZES) {
    const bar = denseBar({ onsets });
    const model = modelBar(bar, { meter, spelledOf, clefs: { 1: "treble", 2: "bass" }, octave: { 1: 0, 2: 0 }, fifths: 0 });
    const open = layoutBar(model, L, { widen: false });
    const settled = layoutBar(model, L, { widen: true });
    out.lr11g["bar" + onsets] = { onsets: bar.onsets, collisionsWidened: overlaps(settled.boxes, L).length, collisionsNoWidening: overlaps(layoutBar(model, L, { widen: false, push: false }).boxes, L).length, width: Math.round(settled.width), widenedBeats: settled.beats.filter((b) => b.widened).length };
    if (onsets === 43 || onsets === 67) {
      timeIt(() => { c2.clearRect(0, 0, cv.width, cv.height); paintOpenBar(c2, L, open, { x: 0, fonts }); }, warm);
      out.lr11a["openBar" + onsets] = summary(timeIt(() => { c2.clearRect(0, 0, cv.width, cv.height); paintOpenBar(c2, L, open, { x: 0, fonts }); }, n));
      const tw = tapeWindow({ onsets, spell, L });
      const endX = (h) => h.endX;
      timeIt(() => { c2.clearRect(0, 0, cv.width, cv.height); paintTape(c2, L, tw.columns, { dx: 10, fonts, endX, ticks: tw.ticks }); }, warm);
      out.lr11a["tape" + onsets] = { ...summary(timeIt(() => { c2.clearRect(0, 0, cv.width, cv.height); paintTape(c2, L, tw.columns, { dx: 10, fonts, endX, ticks: tw.ticks }); }, n)), columns: tw.columns.length, clamped: tw.clamped };
    }
    // engraveBar: layout (format) plus draw, as VexFlow's format + draw
    timeIt(() => { c2.clearRect(0, 0, cv.width, cv.height); engraver.engraveBar(c2, model, { L, ink: "full" }); }, warm);
    const drawn = engraver.engraveBar(c2, model, { L, ink: "full" }).drawn;
    out.lr11b["bar" + onsets] = { ...summary(timeIt(() => { c2.clearRect(0, 0, cv.width, cv.height); engraver.engraveBar(c2, model, { L, ink: "full" }); }, n)), drawn };
    await nextFrame();
  }
  // "flushed": the same draw followed by a texture upload of its canvas (forces the 2D raster), reported beside
  if (GL.ready && GL.gl) {
    for (const onsets of [43, 67]) {
      const bar = denseBar({ onsets });
      const model = modelBar(bar, { meter, spelledOf, fifths: 0 });
      const tcv = document.createElement("canvas"); tcv.width = Math.ceil(layoutBar(model, L).width + 2); tcv.height = L.tileH;
      const tc = tcv.getContext("2d"); const tex = GL.makeTexture(tcv);
      const xs = [];
      for (let i = 0; i < 60; i++) { const t0 = performance.now(); tc.clearRect(0, 0, tcv.width, tcv.height); engraver.engraveBar(tc, model, { L, ink: "full" }); GL.upload(tex); xs.push(performance.now() - t0); if (i % 10 === 9) await nextFrame(); }
      out.lr11b["engravePlusUpload" + onsets] = { ...summary(xs), tile: [tcv.width, tcv.height] };
      GL.disposeTexture(tex);
    }
    // LR11c: one tile upload, interleaved with rendered frames of the running scene
    for (const [w, h, label] of [[400, 280, "tile400x280"], [0, L.tileH, "tileBar24"]]) {
      const tcv = document.createElement("canvas");
      const model = modelBar(denseBar({ onsets: 24 }), { meter, spelledOf, fifths: 0 });
      tcv.width = w || Math.ceil(layoutBar(model, L).width + 2); tcv.height = h;
      const tc = tcv.getContext("2d");
      engraver.engraveBar(tc, model, { L, ink: "full" });
      const tex = GL.makeTexture(tcv);
      const fin = [], nofin = [];
      for (let f = 0; f < uploadFrames; f++) {
        await nextFrame();
        for (let k = 0; k < uploadsPerFrame; k++) (k % 2 ? nofin : fin).push(GL.upload(tex, { finish: k % 2 === 0 }));
      }
      out.lr11c[label] = { size: [tcv.width, tcv.height], finish: summary(fin), noFinish: summary(nofin) };
    }
  } else out.lr11c.error = GL.error || "no WebGL";
  out.checks = {
    LR11a: { threshold: "p95 <= 2 ms (43-onset windows, and paintOpenBar at 67) / <= 3 ms (paintTape at 67)", pass: out.lr11a.openBar43.p95 <= 2 && out.lr11a.tape43.p95 <= 2 && out.lr11a.openBar67.p95 <= 2 && out.lr11a.tape67.p95 <= 3 },
    LR11b: { threshold: "p95 <= 8 ms at 43 onsets, <= 12 ms at 67 (drawn: fonts loaded)", pass: out.lr11b.bar43.drawn && out.lr11b.bar43.p95 <= 8 && out.lr11b.bar67.p95 <= 12 },
    LR11c: { threshold: "p95 <= 2 ms (about 400 x 280, gl.finish after the upload)", pass: !!out.lr11c.tile400x280 && out.lr11c.tile400x280.finish.p95 <= 2 },
    LR11g: { threshold: "0 glyph collisions per settled bar with widening", pass: BENCH_SIZES.every((s) => out.lr11g["bar" + s].collisionsWidened === 0) },
  };
  $("bench-out").textContent = JSON.stringify(out, null, 1);
  $("bench-state").textContent = "done";
  scoreLab.lastBench = out;
  return out;
}

// ------------------------------------------------------------------------------------------------ UI ---
function fmt(ms) { const s = Math.max(0, ms) / 1000; return `${Math.floor(s / 60)}:${(s % 60).toFixed(1).padStart(4, "0")}`; }
function setStatus() {
  const f = fonts.smufl ? "Bravura loaded" : fonts.error ? fonts.error : "loading Bravura…";
  $("status").textContent = `${S.source ? (S.live ? "live MIDI" : "replay: " + S.source) : "no take loaded"} · ${f}`;
}
function setPlaying(on) { S.playing = !!on && !S.live && !!S.ribbon; $("play").setAttribute("aria-pressed", String(S.playing)); $("play").textContent = S.playing ? "Pause" : "Play"; }
function stats() {
  const R = S.ribbon;
  const rs = R ? R.stats() : null;
  const sh = (a) => ({ unwidenedMeanSp: a.unwidened.n ? r3(a.unwidened.px / a.unwidened.n / L.sp) : null, unwidenedN: a.unwidened.n, widenedMeanSp: a.widened.n ? r3(a.widened.px / a.widened.n / L.sp) : null, widenedN: a.widened.n, moved: a.moved, blockX0MeanPx: a.x0.n ? r3(a.x0.px / a.x0.n) : null });
  return {
    t: S.t, seconds: (S.last - S.first) / 1000, live: S.live, fonts: { ...fonts },
    counters: { ...S.counters }, tiles: S.tiles.size,
    ribbon: rs && { commits: rs.commits, tapeBars: rs.tapeBars, columns: rs.columns, overlaps: rs.overlaps, clamped: rs.clamped, conflicts: rs.conflicts, tiedFromTape: rs.tiedFromTape, collapses: rs.collapses, pending: rs.pending, idMismatch: rs.idMismatch, tapeMinutes: r3(rs.tapeMinutes), overlapsPerTapeMinute: r3(rs.overlapsPerTapeMinute), waitMaxMs: rs.waitMaxMs, liveChanges: rs.liveChanges, trBars: rs.tr.bars, violations: rs.tr.violations, shiftOpenToEngraved: sh(rs.shiftOpenToEngraved), shiftSettlingToSettled: sh(rs.shiftSettlingToSettled) },
    header: R ? R.view().header : null,
    ms: { frame: summary(S.frameMs), tick: summary(S.tickMs), openPaint: summary(S.openMs), lightEngrave: summary(S.lightMs), settledEngrave: summary(S.fullMs), tileUpload: summary(S.uploadMs) },
    gl: { kind: GL.kind, ready: GL.ready },
  };
}
function ui() {
  const total = S.last - S.first;
  $("time").textContent = S.live ? fmt(liveNow()) + " live" : `${fmt(S.t)} / ${fmt(total)}`;
  if (!dragging && total > 0) $("seek").value = String(Math.round((S.t / total) * 1000));
  const st = stats();
  $("stats").textContent = [
    `header  ${st.header ? `${st.header.bpm ?? "…"} ${st.header.word}${st.header.dim ? " (dim)" : ""} · ${st.header.source} · ${st.header.drawing}` : "-"}`,
    `ribbon  bars ${st.ribbon ? st.ribbon.commits : 0} frozen · tape cols ${st.ribbon ? st.ribbon.columns : 0} · overlaps ${st.ribbon ? st.ribbon.overlaps : 0} · conflicts ${st.ribbon ? st.ribbon.conflicts : 0} · tied in from tape ${st.ribbon ? st.ribbon.tiedFromTape : 0}`,
    `tiles   ${st.tiles} · settled engraves ${st.counters.settledEngraves} · draws after settle ${st.counters.drawCallsAfterSettle} · reuploads ${st.counters.settledReuploads}`,
    `ribbons ${st.counters.ribbons} (seeks ${st.counters.seeks})`,
    `ms p95  frame ${st.ms.frame.p95} · tick ${st.ms.tick.p95} · open ${st.ms.openPaint.p95} · light ${st.ms.lightEngrave.p95} · settled ${st.ms.settledEngrave.p95} · upload ${st.ms.tileUpload.p95}`,
    `gl      ${GL.kind || "not started (Run bench)"}`,
  ].join("\n");
}

$("file").addEventListener("change", async (e) => {
  const f = e.target.files && e.target.files[0];
  if (!f) return;
  try { await loadText(await f.text(), f.name, { meter: $("meter").value }); } catch (err) { $("status").textContent = String(err.message || err); }
});
$("load").addEventListener("click", async () => { const p = $("path").value.trim(); if (!p) return; try { await loadUrl(p, { meter: $("meter").value }); } catch (err) { $("status").textContent = String(err.message || err); } });
$("play").addEventListener("click", () => setPlaying(!S.playing));
$("speed").addEventListener("change", () => { S.speed = Number($("speed").value) || 1; });
$("seek").addEventListener("input", () => { dragging = true; });
$("seek").addEventListener("change", () => { dragging = false; seek((Number($("seek").value) / 1000) * (S.last - S.first)); });
$("tap").addEventListener("click", () => press("tap"));
$("half").addEventListener("click", () => press("level", 0.5));
$("double").addEventListener("click", () => press("level", 2));
$("one").addEventListener("click", () => press("one"));
$("meter").addEventListener("change", () => { if (S.ribbon) press("meter", $("meter").value); });
$("midi").addEventListener("click", () => startLive());
$("bench").addEventListener("click", () => bench());
window.addEventListener("keydown", (e) => {
  if (e.target && (e.target.tagName === "INPUT" || e.target.tagName === "SELECT")) return;
  if (e.key === " ") { e.preventDefault(); setPlaying(!S.playing); }
  else if (e.key === "t" || e.key === "T") press("tap");
  else if (e.key === "1") press("one");
});

const scoreLab = {
  loadText, loadUrl, seek: (ms) => { seek(ms); render(); return stats(); }, run, press, bench, stats, fonts: () => fontReady,
  play: (on = true) => setPlaying(on), layout: L, lastBench: null,
};
window.scoreLab = scoreLab;
const q = new URLSearchParams(location.search);
if (q.get("events")) loadUrl(q.get("events"), { meter: q.get("meter") || "4/4" }).catch((err) => { $("status").textContent = String(err.message || err); });
setStatus();
requestAnimationFrame(frame);
