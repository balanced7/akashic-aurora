// Piano jam: the glass. An unrecorded 2D canvas laid exactly over the WebGL canvas (jam-spec 8.1, 8.5, 8.6; UX 6.2).
//
// While the jam view keeps Claude off the recorded canvas (auto during REC, or glass), the glass draws what the stage
// would: ghost rims (target, incoming, hold, found) and Claude's pressed keys as moonlight quads, plus the cue chip.
// It knows nothing about three.js: the page hands it projectKeyTop(midi), the key's rest-pose top face projected
// through this frame's camera, as 4 corners in CSS pixels of the glass box, in the face's own order:
//   [back-left, back-right, front-right, front-left]
// (piano.js builds the face as (x-hw, back), (x+hw, back), (x+hw, back+len), (x-hw, back+len); a projection into
// framing pixels becomes CSS pixels by multiplying with cssWidth / framing.w).
//
// Every rim is the projection of a rounded rectangle inset on the key top, drawn through the face's homography, so the
// glass outline has the same perspective as the stage's ghost mesh (A9 compares the two). Strokes are in CSS pixels
// times the device pixel ratio: the canvas backing store is cssWidth x dpr.
//
// createGlass({ canvas, projectKeyTop, isBlack?, now? }) -> {
//   resize(cssRect {left, top, width, height}, dpr),
//   draw({ ghosts: {target, incoming, hold, found}, claude: [{midi, level, css}], chip: {image, x, y, w, h, alpha},
//          alpha, t }),
//   clear(), layout() /* the last frame's rects, for receipts */, stats() }
//
// Pure of the page: no imports, no globals besides the canvas it is given.

export const GLASS_API = "arsenal.piano.glass/v0";

// piano.js KEY (world units: one white-key pitch). The glass needs the widths for the stroke unit and the lengths for
// an inset that is the same distance on every side of the key top.
export const KEY_W = Object.freeze({ white: 0.94, black: 0.56 });
export const KEY_L = Object.freeze({ white: 6.2, black: 3.95 });
export const MAX_KEYS = 24;  // projected per frame, at most (8.5)
export const MOON = "200, 220, 255";  // #C8DCFF, Claude's moonlight
export const GHOST_RGB = "199, 214, 242";           // piano.js GHOST (0.78, 0.84, 0.95): ghost rims on black keys
export const GHOST_ON_IVORY_RGB = "62, 82, 119";    // piano.js GHOST_ON_IVORY (#3E5277): ghost rims on white keys

export const RIM = Object.freeze({
  inset: 0.06,         // of the key width, on every side (UX 6.2)
  holdInset: 0.2,      // the hold state's second, inner rim
  radius: 0.12,        // corner radius, of the key width
  strokeU: 0.045,      // stroke: max(2.5 output px, 0.045 u)
  strokeMinPx: 2.5,    // output (device) pixels
  target: 0.55,        // rim alpha on a white key
  targetBlack: 0.7,    // ... and on a black key
  incoming: 0.35,      // dashed, no fill
  dash: 0.12,          // u
  gap: 0.08,           // u
  fill: 0.1,           // the target's inner fill
  breathLo: 0.92,      // the fill breathes 0.92..1.00
  breathHz: 0.5,
  claudeFill: 0.38,    // Claude's pressed key: a moonlight quad at 38% with an 80% rim
  claudeRim: 0.8,
  foundMs: 200,        // found: every rim grows 1.0 -> 1.15 -> 1.0 over 200 ms, size only
  foundScale: 0.15,
});

const BLACK_PCS = new Set([1, 3, 6, 8, 10]);
export const isBlackKey = (m) => BLACK_PCS.has(((m % 12) + 12) % 12);

// The projective map from the unit square to a quad: (0,0) p0, (1,0) p1, (1,1) p2, (0,1) p3 (Heckbert's square-to-quad).
// A degenerate quad (three corners in a line) falls back to the bilinear map, which never divides by zero.
export function squareToQuad(q) {
  const [x0, y0] = q[0], [x1, y1] = q[1], [x2, y2] = q[2], [x3, y3] = q[3];
  const dx1 = x1 - x2, dx2 = x3 - x2, dx3 = x0 - x1 + x2 - x3;
  const dy1 = y1 - y2, dy2 = y3 - y2, dy3 = y0 - y1 + y2 - y3;
  let g = 0, h = 0;
  if (Math.abs(dx3) > 1e-9 || Math.abs(dy3) > 1e-9) {
    const den = dx1 * dy2 - dx2 * dy1;
    if (Math.abs(den) < 1e-12) {
      return (u, v) => [x0 + (x1 - x0) * u + (x3 - x0) * v + (x0 - x1 + x2 - x3) * u * v,
                        y0 + (y1 - y0) * u + (y3 - y0) * v + (y0 - y1 + y2 - y3) * u * v];
    }
    g = (dx3 * dy2 - dx2 * dy3) / den;
    h = (dx1 * dy3 - dx3 * dy1) / den;
  }
  const a = x1 - x0 + g * x1, b = x3 - x0 + h * x3, c = x0;
  const d = y1 - y0 + g * y1, e = y3 - y0 + h * y3, f = y0;
  return (u, v) => {
    const w = g * u + h * v + 1;
    return [(a * u + b * v + c) / w, (d * u + e * v + f) / w];
  };
}

// A rounded rectangle in the key top's (u across, v along) square, inset by `inset` key widths on every side and scaled
// by `scale` about the face centre, as a closed polyline through the face's projection.
export function rimPath(quad, black, inset, scale = 1) {
  const W = black ? KEY_W.black : KEY_W.white, L = black ? KEY_L.black : KEY_L.white;
  const map = squareToQuad(quad);
  const iu = inset, iv = inset * W / L;
  const ru = Math.min(RIM.radius, 0.45 - iu), rv = ru * W / L;
  const u0 = iu, u1 = 1 - iu, v0 = iv, v1 = 1 - iv;
  const pts = [];
  const arc = (cu, cv, from) => {
    for (let k = 0; k <= 4; k++) {
      const a = from + (k / 4) * (Math.PI / 2);
      pts.push([cu + Math.cos(a) * ru, cv + Math.sin(a) * rv]);
    }
  };
  arc(u1 - ru, v0 + rv, -Math.PI / 2);  // back-right
  arc(u1 - ru, v1 - rv, 0);             // front-right
  arc(u0 + ru, v1 - rv, Math.PI / 2);   // front-left
  arc(u0 + ru, v0 + rv, Math.PI);       // back-left
  return pts.map(([u, v]) => map(0.5 + (u - 0.5) * scale, 0.5 + (v - 0.5) * scale));
}

// The length-weighted centroid of a closed polyline (where the rim's ink sits), in the polyline's own units.
export function outlineCentroid(pts) {
  let sx = 0, sy = 0, sl = 0;
  for (let i = 0; i < pts.length; i++) {
    const [ax, ay] = pts[i], [bx, by] = pts[(i + 1) % pts.length];
    const l = Math.hypot(bx - ax, by - ay);
    sx += (ax + bx) / 2 * l;
    sy += (ay + by) / 2 * l;
    sl += l;
  }
  return sl > 0 ? [sx / sl, sy / sl] : [pts[0][0], pts[0][1]];
}

const finite = (q) => Array.isArray(q) && q.length === 4 &&
  q.every((p) => Array.isArray(p) && Number.isFinite(p[0]) && Number.isFinite(p[1]));
const uniqMidi = (list) => {
  const out = [];
  for (const m of list || []) if (Number.isInteger(m) && m >= 21 && m <= 108 && !out.includes(m)) out.push(m);
  return out;
};

export function createGlass({ canvas, projectKeyTop, isBlack = isBlackKey, now = () => performance.now() } = {}) {
  if (!canvas || typeof canvas.getContext !== "function") throw new Error("createGlass needs a canvas");
  if (typeof projectKeyTop !== "function") throw new Error("createGlass needs projectKeyTop(midi) -> 4 corners");
  const ctx = canvas.getContext("2d");
  const box = { left: 0, top: 0, width: 0, height: 0, dpr: 1 };
  let dirty = false;
  let last = { keys: [], chip: null, alpha: 0 };
  const counts = { draws: 0, clears: 0, keys: 0, capped: 0, skipped: 0, lastMs: 0, maxMs: 0 };

  function resize(cssRect, dpr = 1) {
    const r = cssRect || {};
    const width = Math.max(0, Number(r.width) || 0), height = Math.max(0, Number(r.height) || 0);
    box.left = Number(r.left) || 0;
    box.top = Number(r.top) || 0;
    box.width = width;
    box.height = height;
    box.dpr = Math.max(0.25, Math.min(4, Number(dpr) || 1));
    canvas.style.left = `${box.left}px`;
    canvas.style.top = `${box.top}px`;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    const w = Math.round(width * box.dpr), h = Math.round(height * box.dpr);
    if (canvas.width !== w || canvas.height !== h) {
      canvas.width = w;
      canvas.height = h;
      dirty = false;  // a resize clears the backing store
    }
    return { width: w, height: h, dpr: box.dpr };
  }

  function clear() {
    if (canvas.width && canvas.height) {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.clearRect(0, 0, canvas.width, canvas.height);
    }
    dirty = false;
    last = { keys: [], chip: null, alpha: 0 };
    counts.clears++;
  }

  // One projected face: its quad, the px size of a world unit (for strokes and dashes), and the stroke width in CSS px.
  function face(midi) {
    let q = null;
    try { q = projectKeyTop(midi); } catch { q = null; }
    if (!finite(q)) return null;
    const black = !!isBlack(midi);
    const W = black ? KEY_W.black : KEY_W.white;
    const edge = (Math.hypot(q[1][0] - q[0][0], q[1][1] - q[0][1]) + Math.hypot(q[2][0] - q[3][0], q[2][1] - q[3][1])) / 2;
    const uPx = edge / W;
    const lineWidth = Math.max(RIM.strokeMinPx / box.dpr, RIM.strokeU * uPx);
    return { midi, black, quad: q.map((p) => [p[0], p[1]]), uPx, lineWidth };
  }

  function tracePath(pts) {
    ctx.beginPath();
    ctx.moveTo(pts[0][0], pts[0][1]);
    for (let i = 1; i < pts.length; i++) ctx.lineTo(pts[i][0], pts[i][1]);
    ctx.closePath();
  }

  function draw(state = {}) {
    const t0 = now();
    const alpha = Math.max(0, Math.min(1, state.alpha == null ? 1 : Number(state.alpha)));
    const t = state.t == null ? t0 : Number(state.t);
    const g = state.ghosts || {};
    const target = uniqMidi(g.target), incoming = uniqMidi(g.incoming), hold = uniqMidi(g.hold);
    const claude = (state.claude || []).filter((c) => c && Number.isInteger(c.midi) && c.midi >= 21 && c.midi <= 108 &&
      (c.level == null || c.level > 0.004));
    const chip = state.chip && state.chip.image ? state.chip : null;
    if (!canvas.width || !canvas.height || alpha < 0.004 ||
        (!target.length && !incoming.length && !hold.length && !claude.length && !chip)) {
      if (dirty) clear();
      counts.skipped++;
      return { keys: 0, capped: false };
    }
    // Which keys, and in which states; at most MAX_KEYS projected (Claude's keys first: they are sounding).
    const byMidi = new Map();
    const add = (m, k, v = true) => {
      if (!byMidi.has(m)) {
        if (byMidi.size >= MAX_KEYS) { counts.capped++; return; }
        byMidi.set(m, { target: false, incoming: false, hold: false, claude: null });
      }
      byMidi.get(m)[k] = v;
    };
    for (const c of claude) add(c.midi, "claude", { level: c.level == null ? 1 : Math.min(1, c.level), css: c.css || null });
    for (const m of target) add(m, "target");
    for (const m of hold) add(m, "hold");
    for (const m of incoming) add(m, "incoming");

    const found = Number.isFinite(g.found) ? (t - g.found) / RIM.foundMs : Infinity;
    const scale = found >= 0 && found <= 1 ? 1 + RIM.foundScale * Math.sin(Math.PI * found) : 1;
    const breath = RIM.breathLo + (1 - RIM.breathLo) * (0.5 + 0.5 * Math.cos(2 * Math.PI * RIM.breathHz * t / 1000));

    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.setTransform(box.dpr, 0, 0, box.dpr, 0, 0);  // draw in CSS pixels
    ctx.lineJoin = "round";
    ctx.lineCap = "butt";
    const keysOut = [];
    const order = [...byMidi.entries()].map(([m, s]) => ({ m, s, black: !!isBlack(m) }))
      .sort((a, b) => (a.black - b.black) || (a.m - b.m));  // white keys first: the black keys lie over them
    for (const { m, s } of order) {
      const f = face(m);
      if (!f) continue;
      const rec = { midi: m, black: f.black, states: [], quad: f.quad, lineWidth: +f.lineWidth.toFixed(3), rims: [] };
      if (s.claude) {
        const lv = s.claude.level;
        ctx.setLineDash([]);
        tracePath(f.quad);
        ctx.fillStyle = s.claude.css || `rgb(${MOON})`;
        ctx.globalAlpha = RIM.claudeFill * lv * alpha;
        ctx.fill();
        ctx.strokeStyle = s.claude.css || `rgb(${MOON})`;
        ctx.lineWidth = f.lineWidth;
        ctx.globalAlpha = RIM.claudeRim * lv * alpha;
        ctx.stroke();
        rec.states.push(s.claude.css ? "replay" : "claude");
      }
      const rimAlpha = f.black ? RIM.targetBlack : RIM.target;
      // piano.js's ghost frame colours: moonlight on a black key, a dark moonlight blue on ivory (moonlight on ivory
      // barely shows)
      const rimCss = f.black ? `rgb(${GHOST_RGB})` : `rgb(${GHOST_ON_IVORY_RGB})`;
      if (s.target) {
        const pts = rimPath(f.quad, f.black, RIM.inset, scale);
        tracePath(pts);
        ctx.setLineDash([]);
        ctx.fillStyle = rimCss;
        ctx.globalAlpha = RIM.fill * breath * alpha;
        ctx.fill();
        ctx.strokeStyle = rimCss;
        ctx.lineWidth = f.lineWidth;
        ctx.globalAlpha = rimAlpha * alpha;
        ctx.stroke();
        rec.states.push("target");
        rec.rims.push({ state: "target", centroid: outlineCentroid(pts).map((v) => +v.toFixed(3)) });
      }
      if (s.incoming && !s.target) {
        const pts = rimPath(f.quad, f.black, RIM.inset, scale);
        tracePath(pts);
        ctx.setLineDash([Math.max(2, RIM.dash * f.uPx), Math.max(1.5, RIM.gap * f.uPx)]);
        ctx.strokeStyle = rimCss;
        ctx.lineWidth = f.lineWidth;
        ctx.globalAlpha = RIM.incoming * alpha;
        ctx.stroke();
        ctx.setLineDash([]);
        rec.states.push("incoming");
        rec.rims.push({ state: "incoming", centroid: outlineCentroid(pts).map((v) => +v.toFixed(3)) });
      }
      if (s.hold) {
        const pts = rimPath(f.quad, f.black, RIM.holdInset, scale);
        tracePath(pts);
        ctx.setLineDash([]);
        ctx.strokeStyle = rimCss;
        ctx.lineWidth = f.lineWidth;
        ctx.globalAlpha = (s.target ? rimAlpha : RIM.incoming) * alpha;
        ctx.stroke();
        rec.states.push("hold");
        rec.rims.push({ state: "hold", centroid: outlineCentroid(pts).map((v) => +v.toFixed(3)) });
      }
      keysOut.push(rec);
    }
    let chipOut = null;
    if (chip) {
      const ca = Math.max(0, Math.min(1, chip.alpha == null ? 1 : Number(chip.alpha)));
      if (ca > 0.004) {
        ctx.globalAlpha = ca * alpha;
        try {
          ctx.drawImage(chip.image, chip.x, chip.y, chip.w, chip.h);
          chipOut = { x: chip.x, y: chip.y, w: chip.w, h: chip.h };
        } catch { chipOut = null; }
      }
    }
    ctx.globalAlpha = 1;
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    dirty = true;
    last = { keys: keysOut, chip: chipOut, alpha, scale: +scale.toFixed(4) };
    const ms = now() - t0;
    counts.draws++;
    counts.keys = keysOut.length;
    counts.lastMs = +ms.toFixed(3);
    counts.maxMs = Math.max(counts.maxMs, counts.lastMs);
    return { keys: keysOut.length, capped: byMidi.size >= MAX_KEYS };
  }

  function layout() {
    return { api: GLASS_API, css: { left: box.left, top: box.top, width: box.width, height: box.height }, dpr: box.dpr,
             backing: { width: canvas.width, height: canvas.height }, alpha: last.alpha, scale: last.scale || 1,
             keys: last.keys.map((k) => ({ ...k, quad: k.quad.map((p) => [+p[0].toFixed(3), +p[1].toFixed(3)]) })),
             chip: last.chip };
  }

  const stats = () => ({ ...counts, dirty, width: canvas.width, height: canvas.height, dpr: box.dpr });

  return { resize, draw, clear, layout, stats };
}
