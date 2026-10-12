// arsenal/web/edit/timeline-view.js
// The timeline dock's lanes: one canvas for the ruler, lane backgrounds, waveforms, scene-cut and keyframe marks
// (drawn for the visible range only), one DOM element per clip for focus and labels, a DOM playhead, and the pointer
// gestures: scrub on the ruler, trim a clip's edges (snapping to shots, keyframes and the playhead, with the
// cut cost under the pointer), move a clip, drop media from the bin or from Explorer.
//
// The view never edits the document itself: every gesture ends in onCommit(newDoc) with a document made by
// timeline.js, so undo, save and the server all see the same edit.
//
// Measured 2026-10-12 in headless Chromium 148 at 1600x1000 (scratch drive against arsenal serve): a fitted
// 33-minute timeline with three 190,149-bin waveforms redraws in 1.5 ms mean (2.2 ms max), 0.7 ms while scrolling
// zoomed in; 207 clips zoom and scroll at 16.7 ms p50 / 18.0 ms p95 frame intervals (the 60 Hz vsync) with redraws
// of 1.4 ms mean, 3.8 ms max.

import * as T from "./timeline.js";

const ROWS = { ruler: 24, video: 56, audio: 44 };
const EDGE_PX = 7; // grab distance for a clip edge
const SNAP_PX = 8; // snap distance
const MOVE_PX = 4; // a press becomes a move after this much travel
const MEDIA_MIME = "application/x-arsenal-media";

// ----------------------------------------------------------------- colors --

function readTokens() {
  const cs = getComputedStyle(document.documentElement);
  const tok = (name, fallback) => (cs.getPropertyValue(name).trim() || fallback);
  return {
    ground: tok("--ground", "#0F1114"), panel: tok("--panel", "#171A1F"), ink: tok("--ink", "#E6E8EB"),
    ink2: tok("--ink-2", "#A3ACB7"), ink3: tok("--ink-3", "#7F8994"), rule: tok("--rule", "#2C323A"),
    accent: tok("--accent", "#F0A443"), audio: tok("--audio", "#4CC2BA"), control: tok("--control", "#E47FA7"),
    mono: tok("--font-mono", "monospace"),
  };
}

function rgba(hex, a) {
  const h = String(hex).replace("#", "");
  const n = h.length === 3 ? h.split("").map((c) => c + c).join("") : h.slice(0, 6);
  const v = parseInt(n, 16);
  if (!Number.isFinite(v)) return hex;
  return `rgba(${(v >> 16) & 255},${(v >> 8) & 255},${v & 255},${a})`;
}

// ------------------------------------------------------------------- view --

export function createTimelineView(root, opts) {
  const {
    getDoc, getInfo, getPlayhead, onSeek, onCommit, onSelect, onDropMedia, onDropFiles, requestPlan,
    onPreview = () => {}, onPreviewEnd = () => {},
  } = opts;

  root.innerHTML = "";
  const tl = el("div", "ed-tl");
  const heads = el("div", "ed-heads");
  heads.setAttribute("aria-hidden", "true");
  const scroll = el("div", "ed-scroll");
  scroll.tabIndex = 0;
  scroll.setAttribute("role", "group");
  scroll.setAttribute("aria-label", "Timeline lanes. Drop media here. Press ? for keyboard shortcuts.");
  const content = el("div", "ed-content");
  const canvas = el("canvas", "ed-canvas");
  const clipsLayer = el("div", "ed-clips");
  const playhead = el("div", "ed-playhead");
  const hint = el("div", "ed-hint");
  hint.hidden = true;
  hint.setAttribute("aria-hidden", "true"); // rewritten many times a second while dragging: visual only
  const empty = el("div", "ed-empty");
  empty.textContent = "Drop recordings on the Media bin, the monitor or here; double-click a bin item to append it.";
  content.append(canvas, clipsLayer, playhead, hint);
  scroll.append(content, empty);
  tl.append(heads, scroll);
  root.append(tl);

  let colors = readTokens();
  let pps = 40; // pixels per second
  let selected = null;
  let preview = null; // a document drawn instead of the real one while a gesture runs
  let drag = null;
  let indicator = null; // {x, kind}
  let snapLine = null; // timeline seconds
  let layout = T.layoutRows(getDoc(), ROWS);
  let pending = 0;
  let autoFit = true; // keeps the whole edit in view until the person zooms
  const clipEls = new Map();
  const stats = { draws: 0, lastMs: 0, maxMs: 0, totalMs: 0 };

  const doc = () => preview || getDoc();
  const viewW = () => scroll.clientWidth || 1;
  const limits = () => T.zoomLimits(Math.max(T.totalDuration(getDoc()), 10), viewW());

  // ---------------------------------------------------------------- sizing --

  function contentWidth(d) {
    const total = T.totalDuration(d);
    return Math.max(viewW(), Math.ceil((total + Math.max(10, viewW() * 0.25 / pps)) * pps));
  }

  function resize() {
    const d = doc();
    layout = T.layoutRows(d, ROWS);
    content.style.width = `${contentWidth(d)}px`;
    content.style.height = `${layout.height}px`;
    heads.style.height = `${layout.height}px`;
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    const w = viewW(), h = layout.height;
    if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
      canvas.width = Math.round(w * dpr);
      canvas.height = Math.round(h * dpr);
      canvas.style.width = `${w}px`;
      canvas.style.height = `${h}px`;
    }
    renderHeads(d);
  }

  function renderHeads(d) {
    const key = layout.rows.map((r) => r.id + r.label).join("|");
    if (heads.dataset.key === key) return;
    heads.dataset.key = key;
    heads.innerHTML = "";
    for (const r of layout.rows) {
      const h = el("div", `ed-head ed-head-${r.kind}`);
      h.style.top = `${r.y}px`;
      h.style.height = `${r.h}px`;
      if (r.kind === "ruler") h.textContent = "";
      else {
        const id = el("span", "ed-head-id");
        id.textContent = r.id;
        const name = el("span", "ed-head-name");
        name.textContent = r.kind === "video" ? "Picture" : (d.lanes.audio.find((l) => l.id === r.id) || {}).label || "";
        h.append(id, name);
      }
      heads.append(h);
    }
  }

  // ---------------------------------------------------------------- render --

  function invalidate() {
    if (!pending) pending = requestAnimationFrame(draw);
  }

  function draw() {
    pending = 0;
    const t0 = performance.now();
    const d = doc();
    if (autoFit && T.totalDuration(d) > 0 && viewW() > 1) pps = T.fitPps(Math.max(T.totalDuration(d), 10), viewW());
    resize();
    empty.hidden = d.clips.length > 0;
    const ctx = canvas.getContext("2d");
    const dpr = canvas.width / viewW();
    const sx = scroll.scrollLeft;
    const w = viewW();
    const v0 = sx / pps, v1 = (sx + w) / pps;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = colors.ground;
    ctx.fillRect(0, 0, w, layout.height);

    // lane backgrounds
    for (const r of layout.rows) {
      if (r.kind === "ruler") {
        ctx.fillStyle = colors.panel;
        ctx.fillRect(0, r.y, w, r.h);
      }
      ctx.fillStyle = colors.rule;
      ctx.fillRect(0, r.y + r.h - 1, w, 1);
    }

    const order = T.videoClips(d);
    const vRow = layout.rows.find((r) => r.kind === "video");
    for (const c of order) {
      const x0 = c.at * pps - sx, x1 = T.clipEnd(c) * pps - sx;
      if (x1 < -2 || x0 > w + 2) continue;
      const info = getInfo(c.media_id) || {};
      drawVideoClip(ctx, c, info, vRow, x0, x1, w, sx);
      for (const a of c.audio) {
        const row = layout.rows.find((r) => r.id === a.lane);
        if (row) drawAudioClip(ctx, d, c, a, info, row, x0, x1, w, dpr, sx);
      }
    }

    // clip boundaries through every lane
    ctx.fillStyle = rgba(colors.ink, 0.22);
    for (const c of order) {
      const x = Math.round(T.clipEnd(c) * pps - sx);
      if (x >= 0 && x <= w) ctx.fillRect(x, ROWS.ruler, 1, layout.height - ROWS.ruler);
    }

    // selection
    const sel = selected && order.find((c) => c.id === selected);
    if (sel) {
      const x0 = sel.at * pps - sx, x1 = T.clipEnd(sel) * pps - sx;
      ctx.strokeStyle = colors.ink;
      ctx.lineWidth = 1.5;
      ctx.strokeRect(Math.round(x0) + 0.75, ROWS.ruler + 0.75, Math.max(1, Math.round(x1 - x0) - 1.5), layout.height - ROWS.ruler - 1.5);
    }

    drawRuler(ctx, v0, v1, sx, w);

    if (indicator) {
      ctx.fillStyle = colors.accent;
      ctx.fillRect(Math.round(indicator.x - sx) - 1, ROWS.ruler, 2, layout.height - ROWS.ruler);
    }
    if (snapLine !== null) {
      ctx.strokeStyle = colors.control;
      ctx.setLineDash([3, 3]);
      ctx.lineWidth = 1;
      const x = Math.round(snapLine * pps - sx) + 0.5;
      ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, layout.height); ctx.stroke();
      ctx.setLineDash([]);
    }

    syncClips(d, order, sx, w);
    placePlayhead();
    const ms = performance.now() - t0;
    stats.draws++; stats.lastMs = ms; stats.totalMs += ms; stats.maxMs = Math.max(stats.maxMs, ms);
  }

  function drawRuler(ctx, v0, v1, sx, w) {
    const ticks = T.rulerTicks(v0, v1, pps, 84);
    ctx.fillStyle = colors.ink3;
    for (const m of ticks.minor) ctx.fillRect(Math.round(m * pps - sx), ROWS.ruler - 5, 1, 5);
    ctx.font = `10px ${colors.mono}`;
    ctx.textBaseline = "middle";
    for (const m of ticks.major) {
      const x = Math.round(m.t * pps - sx);
      ctx.fillStyle = colors.ink3;
      ctx.fillRect(x, ROWS.ruler - 10, 1, 10);
      ctx.fillStyle = colors.ink2;
      ctx.fillText(m.label, x + 4, ROWS.ruler / 2 - 1);
    }
  }

  function drawVideoClip(ctx, c, info, row, x0, x1, w, sx) {
    const y = row.y + 3, h = row.h - 6;
    const a = Math.max(x0, -2), b = Math.min(x1, w + 2);
    ctx.fillStyle = rgba(colors.accent, c.id === selected ? 0.26 : 0.16);
    ctx.fillRect(a, y, b - a, h);
    ctx.fillStyle = rgba(colors.accent, 0.85);
    ctx.fillRect(a, y, b - a, 2);
    // keyframes (where a trim is lossless), once they are far enough apart to read
    const kf = info.keyframes || [];
    const keyint = info.media && info.media.video && info.media.video.keyint_s;
    if (kf.length && (keyint ? keyint * pps >= 8 : kf.length * 8 < (x1 - x0))) {
      ctx.fillStyle = rgba(colors.ink, 0.35);
      for (const k of kf) {
        if (k < c.src_in || k > c.src_out) continue;
        const x = Math.round((c.at + k - c.src_in) * pps - sx);
        if (x >= a && x <= b) ctx.fillRect(x, y + h - 5, 1, 5);
      }
    }
    // scene cuts
    const cuts = info.shots || [];
    for (const cut of cuts) {
      if (cut.t <= c.src_in || cut.t >= c.src_out) continue;
      const x = Math.round((c.at + cut.t - c.src_in) * pps - sx);
      if (x < a || x > b) continue;
      ctx.fillStyle = cut.source === "clock" ? colors.audio : rgba(colors.ink, 0.85); // the playhead owns rose
      ctx.fillRect(x, y, 1, h);
      ctx.beginPath(); ctx.moveTo(x - 3.5, y); ctx.lineTo(x + 4.5, y); ctx.lineTo(x + 0.5, y + 5); ctx.fill();
    }
  }

  function drawAudioClip(ctx, d, c, entry, info, row, x0, x1, w, dpr, sx) {
    const y = row.y + 3, h = row.h - 6, mid = y + h / 2;
    const a = Math.max(x0, 0), b = Math.min(x1, w);
    if (b <= a) return;
    const gain = T.effectiveGain(d, entry);
    const heard = gain > 0;
    ctx.fillStyle = rgba(heard ? colors.audio : colors.ink3, c.id === selected ? 0.16 : 0.09);
    ctx.fillRect(a, y, b - a, h);
    const peaks = info.peaks && info.peaks.get(entry.src_track);
    if (!peaks) {
      ctx.fillStyle = colors.ink3;
      ctx.font = `10px ${colors.mono}`;
      ctx.textBaseline = "middle";
      const why = info.peaksState || "waiting for peaks";
      if (b - a > 120) ctx.fillText(why, a + 6, mid);
      ctx.fillRect(a, Math.round(mid), b - a, 1);
      return;
    }
    // the visible part of the clip only, one column per device pixel
    const s0 = c.src_in + ((a + sx) / pps - c.at);
    const s1 = c.src_in + ((b + sx) / pps - c.at);
    const cols = Math.max(1, Math.round((b - a) * dpr));
    const colsData = T.peaksColumns(peaks, s0, s1, cols);
    const g = heard ? gain : 1; // a silenced lane keeps its shape, greyed
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = heard ? colors.audio : rgba(colors.ink3, 0.7);
    const ax = a * dpr, ym = mid * dpr, sc = (h / 2 - 1) * dpr;
    for (let i = 0; i < cols; i++) {
      const lo = colsData[2 * i], hi = colsData[2 * i + 1];
      if (Number.isNaN(lo)) continue;
      const top = ym - Math.max(0, T.waveHeight(hi, g)) * sc;
      const bot = ym - Math.min(0, T.waveHeight(lo, g)) * sc;
      ctx.fillRect(ax + i, top, 1, Math.max(1, bot - top));
    }
    ctx.restore();
  }

  function syncClips(d, order, sx, w) {
    const seen = new Set();
    const vRow = layout.rows.find((r) => r.kind === "video");
    for (const c of order) {
      const x0 = c.at * pps, x1 = T.clipEnd(c) * pps;
      let node = clipEls.get(c.id);
      const visible = x1 >= sx - 200 && x0 <= sx + w + 200;
      if (!visible) { if (node) node.style.display = "none"; seen.add(c.id); continue; }
      if (!node) {
        node = el("div", "ed-clip");
        node.setAttribute("role", "button");
        node.dataset.id = c.id;
        node.tabIndex = -1;
        const name = el("span", "ed-clip-name");
        const inEdge = el("span", "ed-edge ed-edge-in");
        const outEdge = el("span", "ed-edge ed-edge-out");
        node.append(name, inEdge, outEdge);
        node.addEventListener("focus", () => select(c.id));
        clipsLayer.append(node);
        clipEls.set(c.id, node);
      }
      seen.add(c.id);
      const info = getInfo(c.media_id) || {};
      const label = info.media ? info.media.name : c.media_id;
      const dur = T.clipDuration(c);
      node.style.display = "";
      node.style.transform = `translate(${x0}px, ${vRow.y + 3}px)`;
      node.style.width = `${Math.max(2, x1 - x0)}px`;
      node.style.height = `${vRow.h - 6}px`;
      node.classList.toggle("selected", c.id === selected);
      node.classList.toggle("narrow", x1 - x0 < 48);
      node.tabIndex = c.id === selected || (!selected && c === order[0]) ? 0 : -1;
      node.setAttribute("aria-pressed", String(c.id === selected));
      const text = `${label} · ${T.formatTime(dur, dur < 10 ? 1 : 0)}`;
      if (node.firstChild.textContent !== text) node.firstChild.textContent = text;
      node.setAttribute("aria-label",
        `${label}, ${T.formatTime(T.clipDuration(c), 2)} long, from ${T.formatTime(c.src_in, 2)} of the source, at ${T.formatTime(c.at, 2)}`);
    }
    for (const [id, node] of clipEls) {
      if (!seen.has(id)) { node.remove(); clipEls.delete(id); }
    }
  }

  function placePlayhead() {
    const t = getPlayhead();
    playhead.style.transform = `translateX(${Math.round(t * pps)}px)`;
    playhead.style.height = `${layout.height}px`;
  }

  // ------------------------------------------------------------- geometry --

  function pointer(e) {
    const r = content.getBoundingClientRect();
    const x = e.clientX - r.left, y = e.clientY - r.top;
    return { x, y, t: Math.max(0, x / pps), row: T.rowAt(layout, y) };
  }

  /** The clip edge within EDGE_PX of x. At a boundary two clips share, the side of the pointer decides: right of it
   * grabs the next clip's in-edge, left of it the previous clip's out-edge. */
  function edgeAt(d, x) {
    let best = null;
    for (const c of T.videoClips(d)) {
      for (const [edge, xe] of [["in", c.at * pps], ["out", T.clipEnd(c) * pps]]) {
        const dx = x - xe;
        if (Math.abs(dx) > EDGE_PX) continue;
        const wrongSide = edge === "in" ? dx < 0 : dx > 0;
        const score = (wrongSide ? 100 : 0) + Math.abs(dx);
        if (!best || score < best.score) best = { clip: c, edge, score };
      }
    }
    return best;
  }

  // -------------------------------------------------------------- gestures --

  function select(id) {
    if (selected === id) return;
    selected = id;
    invalidate();
    onSelect(id);
  }

  function onPointerDown(e) {
    if (e.button !== 0) return;
    const p = pointer(e);
    if (!p.row) return;
    scroll.focus({ preventScroll: true });
    const d = getDoc();
    if (p.row.kind === "ruler") {
      drag = { kind: "scrub" };
      onSeek(p.t);
      content.setPointerCapture(e.pointerId);
      return;
    }
    const edge = edgeAt(d, p.x);
    if (edge) {
      const info = getInfo(edge.clip.media_id) || {};
      select(edge.clip.id);
      drag = {
        kind: "trim", id: edge.clip.id, edge: edge.edge, orig: d, clip: edge.clip, info,
        targets: T.trimSnapTargets(edge.clip, { shots: info.shots || [], keyframes: info.keyframes || [], playhead: getPlayhead() }),
        planKey: "",
      };
      content.setPointerCapture(e.pointerId);
      updateTrim(p, e);
      return;
    }
    const h = T.clipAtTime(d, p.t);
    if (h && p.x <= T.clipEnd(h.clip) * pps) {
      select(h.clip.id);
      drag = { kind: "press", id: h.clip.id, x: p.x, orig: d };
      content.setPointerCapture(e.pointerId);
      return;
    }
    select(null);
    onSeek(Math.min(p.t, T.totalDuration(d)));
  }

  function onPointerMove(e) {
    const p = pointer(e);
    if (!drag) {
      const d = getDoc();
      const edge = p.row && p.row.kind !== "ruler" ? edgeAt(d, p.x) : null;
      content.style.cursor = p.row && p.row.kind === "ruler" ? "col-resize" : edge ? "ew-resize"
        : p.row && T.clipAtTime(d, p.t) ? "grab" : "default";
      return;
    }
    if (drag.kind === "scrub") { onSeek(Math.min(p.t, T.totalDuration(getDoc()))); return; }
    if (drag.kind === "trim") { updateTrim(p, e); return; }
    if (drag.kind === "press" && Math.abs(p.x - drag.x) >= MOVE_PX) drag = { kind: "move", id: drag.id, orig: drag.orig };
    if (drag.kind === "move") {
      content.style.cursor = "grabbing";
      const order = T.videoClips(drag.orig);
      const i = T.insertionIndex(drag.orig, p.t);
      drag.gesture = { kind: "move", id: drag.id, t: p.t };
      const x = i < order.length ? order[i].at * pps : T.totalDuration(drag.orig) * pps;
      indicator = { x, kind: "move" };
      invalidate();
    }
  }

  function updateTrim(p, e) {
    const { clip, edge, info, orig } = drag;
    const { fps, start_s } = T.frameGrid(info.media, info.keyframes, T.docFps(orig));
    const s = e.altKey ? { t: p.t, kind: null } : T.snap(p.t, drag.targets, SNAP_PX / pps);
    const srcT = clip.src_in + (s.t - clip.at);
    const dur = info.media && Number.isFinite(info.media.duration) ? info.media.duration : Infinity;
    // what the person asked for, replayed on the document as it is at release (see T.applyGesture)
    drag.gesture = { kind: "trim", id: clip.id, edge, srcT, mediaDuration: dur, fps, start_s };
    const next = T.applyGesture(orig, drag.gesture);
    const nc = next.clips.find((c) => c.id === clip.id);
    if (edge === "in") {
      // keep the edge under the pointer while dragging; the ripple happens on release
      const pv = JSON.parse(JSON.stringify(orig));
      const pc = pv.clips.find((c) => c.id === clip.id);
      pc.src_in = nc.src_in;
      pc.at = clip.at + (nc.src_in - clip.src_in);
      preview = pv;
    } else {
      preview = next;
    }
    snapLine = s.kind ? s.t : null;
    // the monitor shows the frame under the dragged edge (the out-edge's last frame, not the one after it)
    onPreview(clip.media_id, edge === "in" ? nc.src_in : Math.max(nc.src_in, nc.src_out - 1 / fps));
    const start = nc.src_in;
    const local = T.cutCost(info.keyframes, start, fps);
    const key = `${clip.media_id}|${start.toFixed(4)}|${nc.src_out.toFixed(4)}`;
    const label = `${edge === "in" ? "In" : "Out"} ${T.formatTime(edge === "in" ? nc.src_in : nc.src_out, 2)}`;
    const cost = drag.plan && drag.planKey === key ? T.costHint(drag.plan) : local ? T.costHint(local) : "cost: keyframes unknown";
    showHint(`${label} · ${cost}${s.kind ? ` · snapped to ${s.kind}` : ""}`, (edge === "in" ? pc0(nc, clip) : T.clipEnd(nc)) * pps);
    if (requestPlan && drag.planKey !== key) {
      drag.planKey = key;
      drag.plan = null;
      const mine = drag;
      requestPlan(clip.media_id, start, nc.src_out).then((plan) => {
        if (drag !== mine || mine.planKey !== key || !plan) return;
        mine.plan = plan;
        showHint(`${label} · ${T.costHint(plan)}${s.kind ? ` · snapped to ${s.kind}` : ""}`, hint._x);
      }).catch(() => {});
    }
    invalidate();
  }

  const pc0 = (nc, clip) => clip.at + (nc.src_in - clip.src_in);

  function showHint(text, x) {
    hint.hidden = false;
    hint.textContent = text;
    hint._x = x;
    const max = scroll.scrollLeft + viewW() - hint.offsetWidth - 4;
    hint.style.transform = `translateX(${Math.max(scroll.scrollLeft + 4, Math.min(max, x + 8))}px)`;
  }

  function endGesture(commit) {
    const g = drag;
    drag = null;
    preview = null;
    indicator = null;
    snapLine = null;
    hint.hidden = true;
    content.style.cursor = "";
    if (g && g.kind === "trim") onPreviewEnd();
    if (commit && g && g.gesture && (g.kind === "trim" || g.kind === "move")) {
      // on the document as it is now, never on g.orig: a save or a key may have changed it since the press
      const base = getDoc();
      const next = T.applyGesture(base, g.gesture);
      if (next !== base) onCommit(next, g.kind);
    }
    invalidate();
  }

  content.addEventListener("pointerdown", onPointerDown);
  content.addEventListener("pointermove", onPointerMove);
  content.addEventListener("pointerup", () => endGesture(true));
  content.addEventListener("pointercancel", () => endGesture(false));
  content.addEventListener("lostpointercapture", () => { if (drag) endGesture(true); });

  scroll.addEventListener("scroll", invalidate, { passive: true });
  scroll.addEventListener("wheel", (e) => {
    if (e.ctrlKey || e.metaKey) {
      e.preventDefault();
      const r = scroll.getBoundingClientRect();
      zoom(Math.exp(-e.deltaY * 0.0015), e.clientX - r.left);
    } else if (!e.shiftKey && Math.abs(e.deltaY) > Math.abs(e.deltaX) && tl.scrollHeight <= tl.clientHeight + 1) {
      e.preventDefault();
      scroll.scrollLeft += e.deltaY;
    }
  }, { passive: false });

  // drops: a bin item (by media id) or files from Explorer, placed at the nearest clip boundary
  function dropIndex(e) {
    const p = pointer(e);
    return T.insertionIndex(getDoc(), p.t);
  }
  scroll.addEventListener("dragover", (e) => {
    const types = Array.from(e.dataTransfer ? e.dataTransfer.types : []);
    if (!types.includes(MEDIA_MIME) && !types.includes("Files")) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "copy";
    const d = getDoc();
    const i = dropIndex(e);
    const order = T.videoClips(d);
    indicator = { x: i < order.length ? order[i].at * pps : T.totalDuration(d) * pps, kind: "drop" };
    invalidate();
  });
  scroll.addEventListener("dragleave", () => { indicator = null; invalidate(); });
  scroll.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const i = dropIndex(e);
    indicator = null;
    invalidate();
    const mid = e.dataTransfer.getData(MEDIA_MIME);
    if (mid) onDropMedia(mid, i);
    else if (e.dataTransfer.files && e.dataTransfer.files.length) onDropFiles(Array.from(e.dataTransfer.files), i);
  });

  const ro = new ResizeObserver(() => invalidate());
  ro.observe(scroll);
  const mq = window.matchMedia("(prefers-color-scheme: light)");
  mq.addEventListener("change", () => { colors = readTokens(); invalidate(); });

  // ------------------------------------------------------------ public ---

  function zoom(factor, anchorX = viewW() / 2) {
    autoFit = false;
    const v = T.zoomAround({ pxPerSec: pps, scrollLeft: scroll.scrollLeft }, factor, anchorX, limits());
    pps = v.pxPerSec;
    content.style.width = `${contentWidth(doc())}px`;
    scroll.scrollLeft = v.scrollLeft;
    invalidate();
  }

  function fit() {
    autoFit = true;
    pps = T.fitPps(Math.max(T.totalDuration(getDoc()), 10), viewW());
    scroll.scrollLeft = 0;
    invalidate();
  }

  /** Keeps the playhead visible while playing (page flip) and redraws it. */
  function follow(t) {
    const x = t * pps;
    const sx = scroll.scrollLeft, w = viewW();
    if (x > sx + w - 24 || x < sx) scroll.scrollLeft = Math.max(0, x - 24);
    placePlayhead();
  }

  function cancelGesture() {
    if (drag) endGesture(false);
  }

  return {
    invalidate, zoom, fit, follow, cancelGesture, placePlayhead,
    select: (id) => select(id),
    get selected() { return selected; },
    get pxPerSec() { return pps; },
    set pxPerSec(v) { pps = v; invalidate(); },
    get scroller() { return scroll; },
    focusClip(id) { const n = clipEls.get(id); if (n) n.focus({ preventScroll: false }); },
    stats: () => ({ ...stats, meanMs: stats.draws ? stats.totalMs / stats.draws : 0, clipEls: clipEls.size }),
    resetStats() { stats.draws = 0; stats.lastMs = 0; stats.maxMs = 0; stats.totalMs = 0; },
  };
}

function el(tag, cls) {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  return n;
}
