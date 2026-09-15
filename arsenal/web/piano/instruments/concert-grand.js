// Concert grand — arsenal/web/piano/instruments/concert-grand.js  (ES module, a piano instrument; no imports)
//
// A 9 ft concert grand in black lacquer, built procedurally AROUND the host's 88-key row (the keys stay host-owned).
// Everything comes through ctx: THREE, scene, keyX, isBlack, KEY, noteColor, framing, span.
//
// Proportions (instruments/spec.md §2.1; 1 world unit = one white-key pitch = 23.57 mm, 52 whites = 1225.7 mm):
//   case 2740 x 1560 mm [M, D-274 reference] -> 116 x 66.2 units; key tops 715 mm above the floor [M] -> 30.3 units;
//   rim ~380 mm deep [U]; lid long prop 35 deg [R], short prop 10 deg [R]; three legs [U], lyre with three pedals [M].
//   Plan outline: straight spine, concave bentside, convex tail (Bezier). No brand, no lettering anywhere.
//
// Front of the harp, from the case front (u = distance behind the case front, 1 u = 23.6 mm):
//   u 0.95-3.3  tuning-pin field: 236 thin steel pins with string coils in five staggered rows (~60 mm deep band)
//   u 4.15      capo / bearing bar the strings cross
//   u 4.7-7.6   strike gap in the plate (four openings between struts); felt hammers wait below the strings
//   u 6.25      damper row: one small felt-and-wood head per note 21-88, sitting on the strings behind the strike line
//   u 9.9       music desk: an upright fretwork panel ~900 x 300 mm tilted back 15 deg, ~300 mm behind the fallboard face
//
// Reactive parts (update(dt, t, state)):
//   strings   one LineSegments, the real stringing (1 / 2 / 3 strings per note, 236 in all); a strike lights that note's
//             strings in noteColor (flash ~0.1 s on velocity squared, then a ring that lasts while the key or the pedal
//             holds and damps in ~0.14 s when released).
//   hammers   one InstancedMesh (88): a strike kicks the hammer up to its strings; while the key is held it rests on the
//             back-check, part way up, as a real grand action does.
//   dampers   one InstancedMesh (notes 21-88; the top 20 notes have none) lift while their key is held or the pedal is down.
//   pedal     the right (damper) pedal of the lyre goes down with state.pedal.
//   case glow one SpotLight over the plate takes the ringing notes' mixed colour. Intensity 0 at rest.
//
// Lid and desk: landscape framing gets the long stick (35 deg) and the music desk; portrait framing gets the recording
// setup, lid and desk removed, so the upper frame stays clear for the note bars and the whole harp shows. 'short' (10 deg)
// is available. ctx.options.lid / ctx.options.desk pin a choice; handle.setLid(mode) / handle.setDesk(on) change it.
//
// Lighting: every material reads correctly under the page's own lights. Lacquer and metal take their highlights from a
// private procedural studio map (a 1024x512 canvas: a horizon band the rim walls mirror, softboxes the plate and rim tops
// mirror, a cool rim strip, a warm interior the lid underside mirrors), set per material, never scene.environment. The
// lacquer adds a cool sheen so the silhouette separates from a dark stage. Instrument materials ignore scene fog: a 2.7 m
// case spans more depth than the page fog was tuned for, and fog had turned the hero case to near-black.
// A faint additive stage pool under the case (handle.parts.pool) lets the legs and lyre read against the floor.
//
// Budget (measured in the lab, burst q3, three r186): 32 draw calls / 93,194 triangles in landscape (lid and desk up),
// 28 / 85,950 in portrait (lid and desk off); 432 instances; shared materials; no per-frame allocation.

const DEG = Math.PI / 180;

// ---- canonical dimensions (units; key tops y=0, white key fronts z=+3.1, key backs z=-3.1, span centre x=0) ----
const HALF = 33.09;          // half case width (1560 mm)
const SPAN_HALF = 26;        // half of the 52-white key span
const Z_CASE = -6.6;         // case front (u = 0) just behind the fallboard; u runs backwards: z = Z_CASE - u
const Y_RIM_TOP = 11.0;      // ~265 mm above key tops (closed height ~1000 mm [U])
const Y_RIM_BOT = -4.6;      // rim depth ~15.6 units = 368 mm
const RIM_T = 2.3;           // rim wall thickness (~54 mm)
const Y_FLOOR = -30.33;      // 715 mm below key tops [M]
const Y_SOUNDBOARD = 2.4;
const Y_PLATE = 4.6;         // plate base; with bevel it spans 4.3..5.4
const Y_PLATE_TOP = 5.4;
const Y_STRING = 6.05;       // strings where they cross the capo bar
const Y_BASS = 6.75;         // overstrung bass strings rise over the tenor toward the bridge
const LID_ANGLES = { long: 35 * DEG, short: 10 * DEG };
const U_FLAP = 9.6;          // front flap hinge line (folded back onto the lid)
const U_PROP = 34;           // where the stick stands on the bentside rim
const PLATE_INSET = RIM_T + 0.8;
const BRIDGE_INSET = PLATE_INSET + 2.4;
const U_PIN0 = 0.95, PIN_ROW = 0.58, PIN_ROWS = 5;
const PIN_COIL_Y = 0.25;     // string height on the pin, above the plate top
const U_CAPO = 4.15;
const U_GAP0 = 4.7, U_GAP1 = 7.6;
const U_STRIKE = 5.35;
const U_DAMPER = 6.25;
const U_DESK = 9.9;
const DESK_Y = 10.0, DESK_W = 38.2, DESK_H = 12.7, DESK_T = 0.42, DESK_TILT = 15 * DEG;
const LEG_TOP = Y_RIM_BOT;
const CASTER_H = 1.45;
const Z_LYRE = -1.6;
const Y_PEDAL = -27.9;
const PEDAL_X = [-2.9, 0, 2.9];
const DAMPER_TOP_NOTE = 88;
const DAMPER_LIFT = 0.45;
const HAMMER_REST_TOP = Y_STRING - 0.85, HAMMER_CHECK = 0.4, HAMMER_KICK = 0.82;

// ---- reactive tuning ----
const STRING_GAIN = 1.55;    // string colour = base + noteColor * glow * gain
const TAU_RING = 1.8, TAU_DAMPED = 0.14, TAU_FLASH = 0.1, TAU_HAMMER = 0.05;
const LIGHT_GAIN = 45, LIGHT_MAX_W = 2.6;

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
const damp = (a, b, tau, dt) => b + (a - b) * Math.exp(-dt / Math.max(tau, 1e-4));
const stringsOf = (m) => (m <= 28 ? 1 : m <= 40 ? 2 : 3);

// ------------------------------------------------------------------ plan outline --
// Outer edge of the case in (x, u), sampled evenly along an open path: treble cheek front -> shoulder -> concave
// bentside -> convex tail -> spine -> spine front. Returns [{x, u, nx, nu}] with outward unit normals.
function sampleOutline(THREE, n) {
  const p = new THREE.Path();
  p.moveTo(HALF, 0);
  p.lineTo(HALF, 10);
  p.bezierCurveTo(HALF, 20, 29.5, 25, 26, 30);            // rounded shoulder
  p.bezierCurveTo(16.7, 43, 9, 60.4, 5, 80);             // concave bentside
  p.bezierCurveTo(1, 99.6, -HALF, 118, -HALF, 86);       // convex tail into the spine
  p.lineTo(-HALF, 0);
  const pts = p.getSpacedPoints(n);
  const out = [];
  for (let i = 0; i < pts.length; i++) {
    const a = pts[Math.max(0, i - 1)], b = pts[Math.min(pts.length - 1, i + 1)];
    let tx = b.x - a.x, tu = b.y - a.y;
    const len = Math.hypot(tx, tu) || 1;
    tx /= len; tu /= len;
    out.push({ x: pts[i].x, u: pts[i].y, nx: tu, nu: -tx });   // path runs clockwise in (x,u): outward = (tu, -tx)
  }
  return out;
}
const offsetPath = (path, d) => path.map((p) => ({ x: p.x + p.nx * d, u: p.u + p.nu * d, nx: p.nx, nu: p.nu }));

// Horizontal extent of a closed (x,u) polygon at each u (table, step 0.25): lets strings and plate holes stay inside.
function extentTable(poly, uMax) {
  const step = 0.25, n = Math.ceil(uMax / step) + 2;
  const lo = new Float32Array(n).fill(NaN), hi = new Float32Array(n).fill(NaN);
  for (let r = 0; r < n; r++) {
    const u = r * step;
    let mn = Infinity, mx = -Infinity;
    for (let i = 0; i < poly.length; i++) {
      const a = poly[i], b = poly[(i + 1) % poly.length];
      if ((a.u <= u && u < b.u) || (b.u <= u && u < a.u)) {
        const x = a.x + (u - a.u) * (b.x - a.x) / (b.u - a.u);
        if (x < mn) mn = x;
        if (x > mx) mx = x;
      }
    }
    if (mx > mn) { lo[r] = mn; hi[r] = mx; }
  }
  return {
    lo: (u) => lo[clamp(Math.round(u / step), 0, n - 1)],
    hi: (u) => hi[clamp(Math.round(u / step), 0, n - 1)],
  };
}

function chaikin(pts, iters) {
  let p = pts;
  for (let k = 0; k < iters; k++) {
    const q = [];
    for (let i = 0; i < p.length; i++) {
      const a = p[i], b = p[(i + 1) % p.length];
      q.push({ x: 0.75 * a.x + 0.25 * b.x, u: 0.75 * a.u + 0.25 * b.u }, { x: 0.25 * a.x + 0.75 * b.x, u: 0.25 * a.u + 0.75 * b.u });
    }
    p = q;
  }
  return p;
}

// ------------------------------------------------------------------ geometry helpers --
// Flip any triangle whose winding disagrees with its vertex normals, so faces always point where the normals do.
function orient(pos, nor, idx) {
  for (let t = 0; t < idx.length; t += 3) {
    const a = idx[t] * 3, b = idx[t + 1] * 3, c = idx[t + 2] * 3;
    const ux = pos[b] - pos[a], uy = pos[b + 1] - pos[a + 1], uz = pos[b + 2] - pos[a + 2];
    const vx = pos[c] - pos[a], vy = pos[c + 1] - pos[a + 1], vz = pos[c + 2] - pos[a + 2];
    const fx = uy * vz - uz * vy, fy = uz * vx - ux * vz, fz = ux * vy - uy * vx;
    const nx = nor[a] + nor[b] + nor[c], ny = nor[a + 1] + nor[b + 1] + nor[c + 1], nz = nor[a + 2] + nor[b + 2] + nor[c + 2];
    if (fx * nx + fy * ny + fz * nz < 0) { const s = idx[t + 1]; idx[t + 1] = idx[t + 2]; idx[t + 2] = s; }
  }
}

// Sweep a cross-section along a plan path. strips: arrays of {d (outward offset), y, nd, ny}; a new strip = a hard edge.
function sweep(THREE, path, strips, caps) {
  const pos = [], nor = [], uv = [], idx = [];
  let base = 0;
  const n = path.length;
  for (const strip of strips) {
    const m = strip.length;
    for (let i = 0; i < n; i++) {
      const P = path[i];
      for (let j = 0; j < m; j++) {
        const s = strip[j];
        pos.push(P.x + P.nx * s.d, s.y, Z_CASE - (P.u + P.nu * s.d));
        nor.push(P.nx * s.nd, s.ny, -P.nu * s.nd);
        uv.push(i / (n - 1), j / Math.max(1, m - 1));
      }
    }
    for (let i = 0; i < n - 1; i++) {
      for (let j = 0; j < m - 1; j++) {
        const a = base + i * m + j, b = base + (i + 1) * m + j, c = base + (i + 1) * m + j + 1, d = base + i * m + j + 1;
        idx.push(a, b, d, b, c, d);
      }
    }
    base += n * m;
  }
  if (caps) {
    const loop = strips.flat();
    for (const end of [0, n - 1]) {
      const P = path[end], Q = path[end === 0 ? 1 : n - 2];
      let tx = P.x - Q.x, tu = P.u - Q.u;
      const len = Math.hypot(tx, tu) || 1;
      tx /= len; tu /= len;
      let cd = 0, cy = 0;
      for (const s of loop) { cd += s.d; cy += s.y; }
      cd /= loop.length; cy /= loop.length;
      const c0 = base;
      pos.push(P.x + P.nx * cd, cy, Z_CASE - (P.u + P.nu * cd)); nor.push(tx, 0, -tu); uv.push(0.5, 0.5);
      for (const s of loop) { pos.push(P.x + P.nx * s.d, s.y, Z_CASE - (P.u + P.nu * s.d)); nor.push(tx, 0, -tu); uv.push(0, 0); }
      for (let k = 0; k < loop.length; k++) idx.push(c0, c0 + 1 + k, c0 + 1 + ((k + 1) % loop.length));
      base += loop.length + 1;
    }
  }
  orient(pos, nor, idx);
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
  g.setAttribute("uv", new THREE.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  return g;
}

// Rounded-top wall profile (rim): outer face, two quarter rounds and the top, inner face; flat bottom as its own strip.
function wallProfile(h, yb, yt, r, seg) {
  const A = [{ d: h, y: yb, nd: 1, ny: 0 }];
  for (let k = 0; k <= seg; k++) {
    const a = (k / seg) * Math.PI / 2;
    A.push({ d: h - r + r * Math.cos(a), y: yt - r + r * Math.sin(a), nd: Math.cos(a), ny: Math.sin(a) });
  }
  for (let k = 0; k <= seg; k++) {
    const a = Math.PI / 2 + (k / seg) * Math.PI / 2;
    A.push({ d: -h + r + r * Math.cos(a), y: yt - r + r * Math.sin(a), nd: Math.cos(a), ny: Math.sin(a) });
  }
  A.push({ d: -h, y: yb, nd: -1, ny: 0 });
  return [A, [{ d: -h, y: yb, nd: 0, ny: -1 }, { d: h, y: yb, nd: 0, ny: -1 }]];
}

// A box with rounded edges from core primitives (RoundedBoxGeometry is an addon, and instruments import nothing).
function roundedBox(THREE, w, h, d, r, seg = 3) {
  r = Math.min(r, w / 2 - 1e-3, h / 2 - 1e-3, d / 2 - 1e-3);
  const iw = w - 2 * r, ih = h - 2 * r, rc = Math.min(r * 0.5, iw / 2 - 1e-3, ih / 2 - 1e-3);
  const s = new THREE.Shape();
  const x0 = -iw / 2, x1 = iw / 2, y0 = -ih / 2, y1 = ih / 2;
  s.moveTo(x0 + rc, y0);
  s.lineTo(x1 - rc, y0); s.absarc(x1 - rc, y0 + rc, rc, -Math.PI / 2, 0, false);
  s.lineTo(x1, y1 - rc); s.absarc(x1 - rc, y1 - rc, rc, 0, Math.PI / 2, false);
  s.lineTo(x0 + rc, y1); s.absarc(x0 + rc, y1 - rc, rc, Math.PI / 2, Math.PI, false);
  s.lineTo(x0, y0 + rc); s.absarc(x0 + rc, y0 + rc, rc, Math.PI, Math.PI * 1.5, false);
  const g = new THREE.ExtrudeGeometry(s, { depth: d - 2 * r, bevelEnabled: true, bevelThickness: r, bevelSize: r,
    bevelSegments: seg, curveSegments: 3 });
  g.translate(0, 0, -(d - 2 * r) / 2);
  return g;
}

// Merge already-placed geometries into one (BufferGeometryUtils is an addon). parts: [{ geo, color? }]; a color on any
// part adds a per-vertex colour attribute (white where a part gives none). The source geometries are disposed.
function mergeGeos(THREE, parts) {
  let nv = 0, ni = 0;
  const withColor = parts.some((p) => p.color);
  for (const { geo } of parts) {
    nv += geo.attributes.position.count;
    ni += geo.index ? geo.index.count : geo.attributes.position.count;
  }
  const pos = new Float32Array(nv * 3), nor = new Float32Array(nv * 3), uv = new Float32Array(nv * 2);
  const col = withColor ? new Float32Array(nv * 3) : null;
  const idx = new Uint32Array(ni);
  let vo = 0, io = 0;
  for (const { geo, color } of parts) {
    const n = geo.attributes.position.count;
    pos.set(geo.attributes.position.array, vo * 3);
    nor.set(geo.attributes.normal.array, vo * 3);
    if (geo.attributes.uv) uv.set(geo.attributes.uv.array, vo * 2);
    if (col) { const c = color || [1, 1, 1]; for (let k = 0; k < n; k++) col.set(c, (vo + k) * 3); }
    if (geo.index) { const a = geo.index.array; for (let k = 0; k < a.length; k++) idx[io++] = a[k] + vo; }
    else for (let k = 0; k < n; k++) idx[io++] = vo + k;
    vo += n;
    geo.dispose();
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  g.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
  g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
  if (col) g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  g.setIndex(new THREE.BufferAttribute(idx, 1));
  return g;
}

// Private studio reflections as a canvas equirect (three PMREM-converts it per material). Azimuth column: 0.25 = -z
// (behind the piano), 0.5 = +x (audience side), 0.75 = +z (the player). Each band is placed where a surface mirrors it
// from the lab's views (planned offline): rim walls from the hero mirror u 0.16-0.42 at -11..-26 deg; plate, pins and rim
// tops mirror u 0.05-0.45 at +8..+35 deg; the lid underside mirrors u 0.12-0.22 at -30..-48 deg.
function studioEnv(THREE) {
  const W = 1024, H = 512;
  const c = document.createElement("canvas");
  c.width = W; c.height = H;
  const g = c.getContext("2d");
  g.fillStyle = "#000"; g.fillRect(0, 0, W, H);
  g.globalCompositeOperation = "lighter";
  const row = (elev) => (0.5 - elev / 180) * H;
  const col = (az) => az * W;
  const box = (u0, u1, e0, e1, css) => { g.fillStyle = css; g.fillRect(col(u0), row(e1), col(u1) - col(u0), row(e0) - row(e1)); };
  const vgrad = (u0, u1, e0, e1, stops) => {                     // stops run top (e1) -> bottom (e0)
    const gr = g.createLinearGradient(0, row(e1), 0, row(e0));
    for (const [t, css] of stops) gr.addColorStop(t, css);
    g.fillStyle = gr;
    g.fillRect(col(u0), row(e1), col(u1) - col(u0), row(e0) - row(e1));
  };
  g.filter = "blur(12px)";
  vgrad(0, 1, -32, 10, [[0, "rgba(0,0,0,0)"], [0.55, "rgb(30,32,40)"], [1, "rgba(0,0,0,0)"]]);        // hall horizon, all round
  vgrad(0.1, 0.5, -32, -6, [[0, "rgba(0,0,0,0)"], [0.28, "rgb(104,109,127)"], [0.6, "rgb(64,66,79)"], [1, "rgba(0,0,0,0)"]]); // stage band: rim walls
  vgrad(0.5, 1.0, -30, -8, [[0, "rgba(0,0,0,0)"], [0.5, "rgb(46,48,58)"], [1, "rgba(0,0,0,0)"]]);    // front floor bounce: cheeks, fallboard
  box(0.04, 0.15, 7, 24, "rgb(160,142,112)");                   // softbox trio above and behind: plate, pins, rim tops
  box(0.19, 0.30, 7, 24, "rgb(140,140,146)");                   // (kept moderate: the rim top mirrors them at grazing angles)
  box(0.34, 0.45, 7, 24, "rgb(108,124,165)");
  box(0.08, 0.42, 26, 38, "rgb(150,146,138)");                  // long strip higher up (close view on the plate)
  box(0.80, 0.90, 32, 56, "rgb(170,160,145)");                  // key softbox, front left (the lab key light's direction)
  box(0.955, 1.0, -8, 52, "rgb(150,120,95)");                   // warm strip, stage left (-x)
  box(0.0, 0.045, -8, 52, "rgb(150,120,95)");
  box(0.47, 0.53, -8, 48, "rgb(95,115,160)");                   // cool strip, stage right (+x)
  box(0.0, 1.0, 62, 90, "rgb(22,23,28)");                       // faint ceiling so upward faces are not dead black
  // Warm interior, mirrored by the lid underside: brightest toward the rim, dying away downward, with dark string lines.
  vgrad(0, 0.34, -76, -27, [[0, "rgb(112,80,38)"], [0.35, "rgb(58,41,20)"], [1, "rgb(6,4,2)"]]);
  g.filter = "blur(2px)";
  box(0.15, 0.46, -18.6, -16.9, "rgb(120,124,138)");            // crisp horizon lines: a long highlight along the rim wall
  box(0.2, 0.44, -11.5, -10.6, "rgb(80,84,96)");
  box(0.235, 0.255, -8, 8, "rgb(100,118,160)");                 // thin cool rim strip: catches the rim's rounded top edge
  g.filter = "none";
  g.globalCompositeOperation = "source-over";
  g.fillStyle = "rgba(0,0,0,0.42)";
  for (let x = col(0); x < col(0.34); x += 9) g.fillRect(x, row(-27), 3, row(-76) - row(-27));
  const tex = new THREE.CanvasTexture(c);
  tex.mapping = THREE.EquirectangularReflectionMapping;
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

function spruceGrain(THREE) {
  const c = document.createElement("canvas");
  c.width = 256; c.height = 256;
  const g = c.getContext("2d");
  g.fillStyle = "#b99461"; g.fillRect(0, 0, 256, 256);
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let x = 0; x < 256; x += 2 + Math.floor(rnd() * 6)) {
    g.fillStyle = `rgba(92,62,32,${0.12 + rnd() * 0.3})`;
    g.fillRect(x, 0, 1 + Math.floor(rnd() * 2), 256);
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(1 / 16, 1 / 16);
  tex.rotation = 0.55;
  return tex;
}

// Cast-iron hammertone: soft speckle used as the plate's bump and roughness map, so the gold reads as a casting.
function hammertone(THREE) {
  const c = document.createElement("canvas");
  c.width = 256; c.height = 256;
  const g = c.getContext("2d");
  g.fillStyle = "rgb(180,180,180)"; g.fillRect(0, 0, 256, 256);
  let seed = 11;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  g.filter = "blur(1px)";
  for (let i = 0; i < 2600; i++) {
    const v = 140 + Math.floor(rnd() * 90);
    g.fillStyle = `rgb(${v},${v},${v})`;
    g.beginPath();
    g.arc(rnd() * 256, rnd() * 256, 1 + rnd() * 3.2, 0, Math.PI * 2);
    g.fill();
  }
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.NoColorSpace;
  tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
  tex.repeat.set(1 / 4, 1 / 4);
  return tex;
}

function poolTexture(THREE) {
  const c = document.createElement("canvas");
  c.width = 256; c.height = 256;
  const g = c.getContext("2d");
  const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  gr.addColorStop(0, "rgb(255,240,220)");
  gr.addColorStop(0.45, "rgb(150,140,128)");
  gr.addColorStop(1, "rgb(0,0,0)");
  g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
  const tex = new THREE.CanvasTexture(c);
  tex.colorSpace = THREE.SRGBColorSpace;
  return tex;
}

// ------------------------------------------------------------------ the instrument --
function create(ctx) {
  const THREE = ctx.THREE;
  const S = ctx.span || ctx.keySpan || {};
  const K = ctx.KEY || {};
  const keyX = ctx.keyX;
  const left = S.left ?? S.x0 ?? (keyX ? keyX(21) - 0.5 : -SPAN_HALF);
  const right = S.right ?? S.x1 ?? (keyX ? keyX(108) + 0.5 : SPAN_HALF);
  const top = S.keyTop ?? S.top ?? S.yTop ?? 0;
  const front = S.keyFront ?? S.front ?? S.zFront ?? ((K.back ?? -3.1) + (K.whiteL ?? 6.2));
  const k = (right - left) / (2 * SPAN_HALF);                  // host units per canonical unit (1 on the page)

  const group = new THREE.Group();
  group.name = "instrument:concert-grand";
  group.position.set((left + right) / 2, top, front - 3.1 * k);
  group.scale.setScalar(k);

  const geos = [], mats = [], texs = [];
  const G = (g) => (geos.push(g), g);
  const M = (m) => { m.fog = false; mats.push(m); return m; };
  const add = (geo, mat, parent = group) => { const mesh = new THREE.Mesh(G(geo), mat); parent.add(mesh); return mesh; };

  // ---- materials (shared) ----
  const env = studioEnv(THREE); texs.push(env);
  const grain = spruceGrain(THREE); texs.push(grain);
  const tone = hammertone(THREE); texs.push(tone);
  const lacquer = M(new THREE.MeshPhysicalMaterial({ color: 0x050507, roughness: 0.2, metalness: 0, clearcoat: 1,
    clearcoatRoughness: 0.035, envMap: env, envMapIntensity: 2.1, sheen: 0.4, sheenColor: 0x3a4a70, sheenRoughness: 0.5 }));
  // The same lacquer, a little softer, for the parts beside the keys: the page's note lights sit 2 units above them, and a
  // mirror coat there turns each strike into a bloom blob.
  const lacquerNear = M(new THREE.MeshPhysicalMaterial({ color: 0x060608, roughness: 0.34, metalness: 0, clearcoat: 1,
    clearcoatRoughness: 0.24, envMap: env, envMapIntensity: 1.5, sheen: 0.3, sheenColor: 0x3a4a70, sheenRoughness: 0.6 }));
  // The key blocks' curved tops face the host key light's half-vector from the hero seat; a mirror coat there made a bloom
  // blob (burst q1), so the arms (and the rim's inner round) carry a brushed-gloss coat that keeps highlights under bloom.
  const lacquerArm = M(new THREE.MeshPhysicalMaterial({ color: 0x050507, roughness: 0.46, metalness: 0, clearcoat: 1,
    clearcoatRoughness: 0.4, envMap: env, envMapIntensity: 2.0, sheen: 0.4, sheenColor: 0x3a4a70, sheenRoughness: 0.5 }));
  const satin = M(new THREE.MeshPhysicalMaterial({ color: 0x0a0a0c, roughness: 0.55, clearcoat: 0.35, clearcoatRoughness: 0.3,
    envMap: env, envMapIntensity: 0.9 }));
  // Metals are flat and face up, where the host rim light's half-vector points from the close seat: at roughness 0.35 the
  // plate top and pin tops threw bloom blobs (burst q2), so the plate is satin cast gold (0.55) and the pins 0.52.
  const gold = M(new THREE.MeshPhysicalMaterial({ color: 0xb8903a, metalness: 1.0, roughness: 0.55,
    bumpMap: tone, bumpScale: 0.18, clearcoat: 0.12, clearcoatRoughness: 0.5, envMap: env, envMapIntensity: 2.3 }));
  const brass = M(new THREE.MeshPhysicalMaterial({ color: 0xd9ad55, metalness: 0.9, roughness: 0.22, envMap: env, envMapIntensity: 1.5 }));
  const steel = M(new THREE.MeshPhysicalMaterial({ color: 0xb8bcc2, metalness: 1.0, roughness: 0.52, envMap: env, envMapIntensity: 2.8 }));
  const spruce = M(new THREE.MeshPhysicalMaterial({ color: 0xffffff, map: grain, roughness: 0.6, clearcoat: 0.15, clearcoatRoughness: 0.5 }));
  const maple = M(new THREE.MeshPhysicalMaterial({ color: 0x8c6a3c, roughness: 0.5, clearcoat: 0.2, clearcoatRoughness: 0.4 }));
  const felt = M(new THREE.MeshPhysicalMaterial({ color: 0x5c0c1a, roughness: 0.95 }));
  // vertex-coloured parts (damper heads: black wood over grey felt; hammers: cream felt on maple moulding)
  const partsMat = M(new THREE.MeshPhysicalMaterial({ color: 0xffffff, vertexColors: true, roughness: 0.7, clearcoat: 0.2,
    clearcoatRoughness: 0.45, envMap: env, envMapIntensity: 0.7 }));

  // ---- plan ----
  const outer = sampleOutline(THREE, 240);
  let iApex = 0;
  for (let i = 1; i < outer.length; i++) if (outer[i].u > outer[iApex].u) iApex = i;
  const uMax = outer[iApex].u;
  const inner = offsetPath(outer, -RIM_T);
  const plateEdge = offsetPath(outer, -PLATE_INSET);
  const bridgeEdge = offsetPath(outer, -BRIDGE_INSET);
  // Close an open outline with a straight front edge at u0 (points in front of u0 are dropped, so no spikes).
  const closePoly = (path, u0) => {
    const kept = path.filter((q) => q.u > u0 + 1e-6);
    return [{ x: kept[0].x, u: u0 }, ...kept, { x: kept[kept.length - 1].x, u: u0 }];
  };

  // ---- rim ----
  // Outer face, outer round and flat top in mirror lacquer; the inner round, inner face and bottom in the brushed coat.
  // The inner round of the tail faces the player, and under the host key light a mirror coat there drew a blooming line
  // along the tail in the 9:16 view (burst q2).
  {
    const [profile, bottom] = wallProfile(RIM_T / 2, Y_RIM_BOT, Y_RIM_TOP, 0.55, 4);
    const split = 1 + 5;                                        // outer bottom + 5 outer-round points; then the inner round
    const rimPath = offsetPath(outer, -RIM_T / 2);
    add(sweep(THREE, rimPath, [profile.slice(0, split + 1)], false), lacquer);
    add(sweep(THREE, rimPath, [profile.slice(split), bottom], false), lacquerArm);
  }

  // ---- case arms (key blocks rising into the rim), keybed, key slip, fallboard, felt, pinblock face, belly rail ----
  const armShape = new THREE.Shape();
  const P = (z, y) => [-z, y];
  armShape.moveTo(...P(Z_CASE - 1.5, Y_RIM_BOT + 0.25));
  armShape.lineTo(...P(Z_CASE - 1.5, Y_RIM_TOP - 0.25));
  armShape.lineTo(...P(Z_CASE + 0.6, Y_RIM_TOP - 0.25));
  armShape.bezierCurveTo(...P(Z_CASE + 3.4, Y_RIM_TOP - 0.25), ...P(Z_CASE + 3.2, 1.35), ...P(Z_CASE + 6.4, 1.35));
  armShape.lineTo(...P(2.9, 1.35));
  armShape.quadraticCurveTo(...P(3.65, 1.35), ...P(3.65, 0.6));
  armShape.lineTo(...P(3.65, Y_RIM_BOT + 0.25));
  armShape.closePath();
  const armW = HALF - (SPAN_HALF + 0.15);
  const armGeo = G(new THREE.ExtrudeGeometry(armShape, { depth: armW - 0.5, bevelEnabled: true, bevelThickness: 0.25,
    bevelSize: 0.25, bevelSegments: 3, curveSegments: 14 }));
  armGeo.rotateY(Math.PI / 2);
  armGeo.translate(0.25, 0, 0);
  const armR = new THREE.Mesh(armGeo, lacquerArm); armR.position.x = SPAN_HALF + 0.15; group.add(armR);
  const armL = new THREE.Mesh(armGeo, lacquerArm); armL.position.x = -HALF; group.add(armL);

  const place = (mesh, x, y, z) => { mesh.position.set(x, y, z); return mesh; };
  place(add(roundedBox(THREE, 52.3, 3.1, 9.8, 0.15), satin), 0, -2.45, -1.7);                 // keybed / key frame
  place(add(roundedBox(THREE, 52.3, 2.05, 0.6, 0.18), lacquerNear), 0, -1.975, 3.5);         // key slip
  place(add(roundedBox(THREE, 52.2, 2.2, 3.1, 0.4), lacquerNear), 0, 0.2, -5.05);            // fallboard (open)
  place(add(new THREE.BoxGeometry(52.1, 0.18, 0.14), felt), 0, 0.09, -3.43);                 // key-back felt
  place(add(roundedBox(THREE, 61.5, 9.2, 1.4, 0.2), lacquerNear), 0, 0.6, -7.3);             // pinblock face behind the fallboard
  place(add(new THREE.BoxGeometry(60.5, Y_SOUNDBOARD - Y_RIM_BOT, 1.2), satin), 0,
    (Y_SOUNDBOARD + Y_RIM_BOT) / 2, Z_CASE - U_GAP1 - 0.7);                                  // belly rail behind the hammers

  // ---- soundboard (starts behind the belly rail, so the strike gap looks into the dark action) and case bottom ----
  const shapeOf = (poly, flipU = false) => {
    const s = new THREE.Shape();
    poly.forEach((q, i) => (i ? s.lineTo(q.x, flipU ? -q.u : q.u) : s.moveTo(q.x, flipU ? -q.u : q.u)));
    s.closePath();
    return s;
  };
  const sbGeo = new THREE.ShapeGeometry(shapeOf(closePoly(inner, U_GAP1 + 0.2)));
  sbGeo.rotateX(-Math.PI / 2);
  sbGeo.translate(0, Y_SOUNDBOARD, Z_CASE);
  add(sbGeo, spruce);
  const bottomGeo = new THREE.ShapeGeometry(shapeOf(closePoly(inner, 0), true));
  bottomGeo.rotateX(Math.PI / 2);
  bottomGeo.translate(0, Y_RIM_BOT + 0.02, Z_CASE);
  add(bottomGeo, satin);

  // ---- plate (gold casting: pin flange, strike gap between struts, large openings) ----
  const platePoly = closePoly(plateEdge, 0.3);
  const plateX = extentTable(platePoly, uMax);
  const plateShape = shapeOf(platePoly);
  const hole = (u0, u1, f0, f1, smooth = 2) => {
    const n = Math.max(2, Math.ceil(u1 - u0)), pts = [];
    for (let s = 0; s <= n; s++) { const u = lerp(u0, u1, s / n); pts.push({ x: lerp(plateX.lo(u), plateX.hi(u), f0), u }); }
    for (let s = n; s >= 0; s--) { const u = lerp(u0, u1, s / n); pts.push({ x: lerp(plateX.lo(u), plateX.hi(u), f1), u }); }
    const sm = chaikin(pts, smooth);
    const h = new THREE.Path();
    sm.forEach((q, i) => (i ? h.lineTo(q.x, q.u) : h.moveTo(q.x, q.u)));
    h.closePath();
    plateShape.holes.push(h);
  };
  const plateEnd = uMax - PLATE_INSET;
  // strike gap: struts at the bass break (f 0.2, between the bass and tenor strings) and two in the treble
  [[0.025, 0.19], [0.215, 0.455], [0.485, 0.72], [0.75, 0.975]].forEach(([f0, f1]) => hole(U_GAP0, U_GAP1, f0, f1, 1));
  hole(10.8, plateEnd - 12, 0.06, 0.41);
  hole(10.8, 58, 0.49, 0.93);
  hole(63, Math.min(plateEnd - 16, 84), 0.52, 0.88);
  const plateGeo = new THREE.ExtrudeGeometry(plateShape, { depth: 0.5, bevelEnabled: true, bevelThickness: 0.3,
    bevelSize: 0.28, bevelSegments: 2, curveSegments: 4 });
  plateGeo.rotateX(-Math.PI / 2);
  plateGeo.translate(0, Y_PLATE, Z_CASE);
  add(plateGeo, gold);
  const capoW = plateX.hi(U_CAPO) - plateX.lo(U_CAPO) - 1.2;
  place(add(roundedBox(THREE, capoW, 0.66, 0.6, 0.2, 2), gold), (plateX.hi(U_CAPO) + plateX.lo(U_CAPO)) / 2,
    Y_STRING - 0.35, Z_CASE - U_CAPO);                                                        // capo / bearing bar

  // ---- bridge (maple strip over the soundboard, along the bentside and tail) ----
  let b0 = 0, b1 = bridgeEdge.length - 1;
  while (b0 < iApex && bridgeEdge[b0].u < 11) b0++;
  for (let i = iApex; i < bridgeEdge.length; i++) if (bridgeEdge[i].x < -24.5) { b1 = i; break; }
  const bw = 0.45, byb = Y_SOUNDBOARD + 0.1, byt = Y_STRING - 0.08;
  add(sweep(THREE, bridgeEdge.slice(b0, b1 + 1), [
    [{ d: bw, y: byb, nd: 1, ny: 0 }, { d: bw, y: byt, nd: 1, ny: 0 }],
    [{ d: bw, y: byt, nd: 0, ny: 1 }, { d: -bw, y: byt, nd: 0, ny: 1 }],
    [{ d: -bw, y: byt, nd: -1, ny: 0 }, { d: -bw, y: byb, nd: -1, ny: 0 }],
  ], true), maple);

  // ---- strings and tuning pins ----
  const bridgeX = extentTable(closePoly(bridgeEdge, 0), uMax);
  const noteCount = 88;
  let stringTotal = 0;
  for (let m = 21; m <= 108; m++) stringTotal += stringsOf(m);
  const VERTS_PER_STRING = 4;                                  // pin -> capo bar, capo bar -> bridge
  const strPos = new Float32Array(stringTotal * VERTS_PER_STRING * 3);
  const strBase = new Float32Array(strPos.length);
  const strOff = new Uint16Array(noteCount), strNv = new Uint8Array(noteCount);
  const stringX = new Float32Array(noteCount), stringSlope = new Float32Array(noteCount), stringEnd = new Float32Array(noteCount);
  const pinGeo = G(mergeGeos(THREE, [
    { geo: new THREE.CylinderGeometry(0.105, 0.127, 0.55, 8, 1).translate(0, 0.275, 0) },     // pin, ~3 mm radius
    { geo: new THREE.CylinderGeometry(0.19, 0.19, 0.17, 8, 1).translate(0, PIN_COIL_Y, 0) },  // string coil
  ]));
  const pins = new THREE.InstancedMesh(pinGeo, steel, stringTotal);
  const mtx = new THREE.Matrix4();
  const COPPER = [0.24, 0.136, 0.064], STEEL = [0.21, 0.19, 0.16];
  let s = 0;
  for (let i = 0; i < noteCount; i++) {
    const m = 21 + i;
    const bass = m <= 40;
    const f = bass ? (m - 21) / 19 : (m - 41) / 67;
    const xf = bass ? lerp(-27.6, -18.2, f) : lerp(-17.2, 24.2, f);
    const slope = bass ? lerp(0.2, 0.1, f) : lerp(-0.075, -0.012, f);
    let uEnd = U_CAPO + 1;
    for (let u = U_CAPO; u < uMax; u += 0.25) {
      const x = xf + slope * (u - U_CAPO);
      if (!(x > bridgeX.lo(u) && x < bridgeX.hi(u))) break;
      uEnd = u;
    }
    stringX[i] = xf; stringSlope[i] = slope; stringEnd[i] = uEnd;
    const n = stringsOf(m), gap = n === 2 ? 0.24 : 0.19;
    const yEnd = bass ? Y_BASS : Y_STRING;
    const br = bass ? COPPER : STEEL;
    strOff[i] = s * VERTS_PER_STRING; strNv[i] = n * VERTS_PER_STRING;
    for (let l = 0; l < n; l++, s++) {
      const x0 = xf + (l - (n - 1) / 2) * gap;
      const uPin = U_PIN0 + (s % PIN_ROWS) * PIN_ROW;
      const xPin = x0 + slope * (uPin - U_CAPO);
      const o = s * VERTS_PER_STRING * 3;
      strPos.set([xPin, Y_PLATE_TOP + PIN_COIL_Y, Z_CASE - uPin, x0, Y_STRING, Z_CASE - U_CAPO,
        x0, Y_STRING, Z_CASE - U_CAPO, x0 + slope * (uEnd - U_CAPO), yEnd, Z_CASE - uEnd], o);
      for (let v = 0; v < VERTS_PER_STRING; v++) strBase.set(br, o + v * 3);
      mtx.makeTranslation(xPin, Y_PLATE_TOP, Z_CASE - uPin);
      pins.setMatrixAt(s, mtx);
    }
  }
  const strGeo = G(new THREE.BufferGeometry());
  strGeo.setAttribute("position", new THREE.BufferAttribute(strPos, 3));
  const strColAttr = new THREE.BufferAttribute(new Float32Array(strBase), 3);
  strColAttr.setUsage(THREE.DynamicDrawUsage);
  strGeo.setAttribute("color", strColAttr);
  const strMat = M(new THREE.LineBasicMaterial({ vertexColors: true }));
  const strings = new THREE.LineSegments(strGeo, strMat);
  strings.frustumCulled = false;
  group.add(strings, pins);
  // the string height at u for note index i (bass strings climb from the capo bar toward the bridge)
  const stringY = (i, u) => (i + 21 <= 40 ? lerp(Y_STRING, Y_BASS, clamp((u - U_CAPO) / (stringEnd[i] - U_CAPO), 0, 1)) : Y_STRING);
  const stringXAt = (i, u) => stringX[i] + stringSlope[i] * (u - U_CAPO);

  // ---- hammers (felt heads in the strike gap, below the strings) ----
  const CREAM = [0.4, 0.37, 0.31], MOULD = [0.3, 0.2, 0.1];
  const hammerGeo = G(mergeGeos(THREE, [
    { geo: roundedBox(THREE, 0.46, 0.7, 1.0, 0.16, 1).translate(0, -0.35, 0), color: CREAM },
    { geo: new THREE.BoxGeometry(0.4, 0.42, 0.62).translate(0, -0.91, 0.05), color: MOULD },
  ]));
  const hammers = new THREE.InstancedMesh(hammerGeo, partsMat, noteCount);
  hammers.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  hammers.frustumCulled = false;
  for (let i = 0; i < noteCount; i++) {
    mtx.makeScale(i + 21 <= 40 ? 0.9 : 1, 1, 1).setPosition(stringXAt(i, U_STRIKE), HAMMER_REST_TOP, Z_CASE - U_STRIKE);
    hammers.setMatrixAt(i, mtx);
  }
  group.add(hammers);

  // ---- dampers (small heads on the strings, just behind the strike line) ----
  const damperCount = DAMPER_TOP_NOTE - 21 + 1;
  const damperGeo = G(mergeGeos(THREE, [
    { geo: new THREE.BoxGeometry(0.5, 0.24, 0.78).translate(0, 0.12, 0), color: [0.36, 0.35, 0.33] },   // felt
    { geo: roundedBox(THREE, 0.5, 0.62, 0.78, 0.09, 1).translate(0, 0.55, 0), color: [0.02, 0.02, 0.022] }, // wood head
  ]));
  const dampers = new THREE.InstancedMesh(damperGeo, partsMat, damperCount);
  dampers.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  dampers.frustumCulled = false;
  const damperY0 = new Float32Array(damperCount);
  for (let i = 0; i < damperCount; i++) {
    damperY0[i] = stringY(i, U_DAMPER) + 0.01;
    mtx.makeScale(i + 21 <= 40 ? 0.84 : 1, 1, 1).setPosition(stringXAt(i, U_DAMPER), damperY0[i], Z_CASE - U_DAMPER);
    dampers.setMatrixAt(i, mtx);
  }
  group.add(dampers);

  // ---- music desk: upright fretwork panel on a base with a music ledge, props behind, feet on the plate ----
  const zDesk = Z_CASE - U_DESK;
  const deskShape = new THREE.Shape();
  {
    const w = DESK_W / 2, h = DESK_H, r = 0.7;
    deskShape.moveTo(-w + r, 0);
    deskShape.lineTo(w - r, 0); deskShape.absarc(w - r, r, r, -Math.PI / 2, 0, false);
    deskShape.lineTo(w, h - r); deskShape.absarc(w - r, h - r, r, 0, Math.PI / 2, false);
    deskShape.lineTo(-w + r, h); deskShape.absarc(-w + r, h - r, r, Math.PI / 2, Math.PI, false);
    deskShape.lineTo(-w, r); deskShape.absarc(-w + r, r, r, Math.PI, Math.PI * 1.5, false);
    const slot = (cx, y0, y1, hw) => {
      const p = new THREE.Path();
      p.moveTo(cx - hw, y0 + hw);
      p.absarc(cx, y0 + hw, hw, Math.PI, Math.PI * 2, false);
      p.lineTo(cx + hw, y1 - hw);
      p.absarc(cx, y1 - hw, hw, 0, Math.PI, false);
      p.closePath();
      deskShape.holes.push(p);
    };
    for (let j = -12; j <= 12; j++) {
      const lift = 1.3 * Math.cos((j / 12) * Math.PI / 2);     // the slot field arches up toward the middle
      slot(j * 1.05, 2.6, 8.6 + lift, 0.2);
    }
  }
  const deskPanel = new THREE.ExtrudeGeometry(deskShape, { depth: DESK_T, bevelEnabled: true, bevelThickness: 0.06,
    bevelSize: 0.06, bevelSegments: 1, curveSegments: 4 });
  deskPanel.translate(0, 0, -DESK_T / 2);
  deskPanel.rotateX(-DESK_TILT);
  deskPanel.translate(0, DESK_Y, zDesk);
  const propGeo = (x) => {
    const h = 6, back = [DESK_Y + h * Math.cos(DESK_TILT), zDesk - h * Math.sin(DESK_TILT) - DESK_T / 2 - 0.1];
    const foot = [DESK_Y, zDesk - 3.2];
    const len = Math.hypot(back[0] - foot[0], back[1] - foot[1]);
    const g = new THREE.BoxGeometry(0.4, len, 0.4);
    g.rotateX(Math.atan2(back[1] - foot[1], back[0] - foot[0]));
    g.translate(x, (back[0] + foot[0]) / 2, (back[1] + foot[1]) / 2);
    return g;
  };
  const deskGeo = mergeGeos(THREE, [
    { geo: deskPanel },
    { geo: roundedBox(THREE, DESK_W + 0.6, 0.36, 4.2, 0.12, 1).translate(0, DESK_Y - 0.18, zDesk - 1.3) },   // base
    { geo: roundedBox(THREE, DESK_W + 0.6, 0.75, 0.3, 0.1, 1).translate(0, DESK_Y + 0.2, zDesk + 0.72) },    // music ledge lip
    { geo: propGeo(-12) }, { geo: propGeo(12) },
    { geo: new THREE.BoxGeometry(0.8, DESK_Y - 0.36 - Y_PLATE_TOP, 1.4).translate(-16.5, (DESK_Y - 0.36 + Y_PLATE_TOP) / 2, zDesk - 1.3) },
    { geo: new THREE.BoxGeometry(0.8, DESK_Y - 0.36 - Y_PLATE_TOP, 1.4).translate(16.5, (DESK_Y - 0.36 + Y_PLATE_TOP) / 2, zDesk - 1.3) },
  ]);
  const desk = add(deskGeo, satin);

  // ---- lid (hinged on the spine), folded front flap, long and short sticks, hinges ----
  const lidOuter = offsetPath(outer, 0.3);
  const lidPts = [{ x: HALF + 0.3, u: U_FLAP }];
  for (const q of lidOuter) if (q.u > U_FLAP) lidPts.push(q);
  lidPts.push({ x: -HALF - 0.3, u: U_FLAP });
  const LID_T = 0.55, LID_BEV = 0.12;
  const lidOpts = { depth: LID_T, bevelEnabled: true, bevelThickness: LID_BEV, bevelSize: LID_BEV, bevelSegments: 2, curveSegments: 4 };
  const lidGeo = new THREE.ExtrudeGeometry(shapeOf(lidPts), lidOpts);
  lidGeo.rotateX(-Math.PI / 2);
  lidGeo.translate(HALF, LID_BEV, Z_CASE);
  const lidPivot = new THREE.Group();
  lidPivot.position.set(-HALF, Y_RIM_TOP, 0);
  group.add(lidPivot);
  add(lidGeo, lacquer, lidPivot);
  const flapGeo = new THREE.ExtrudeGeometry(shapeOf([{ x: HALF + 0.3, u: U_FLAP + 0.15 }, { x: HALF + 0.3, u: 2 * U_FLAP },
    { x: -HALF - 0.3, u: 2 * U_FLAP }, { x: -HALF - 0.3, u: U_FLAP + 0.15 }]), lidOpts);
  flapGeo.rotateX(-Math.PI / 2);
  flapGeo.translate(HALF, LID_T + 3 * LID_BEV + 0.02, Z_CASE);
  add(flapGeo, lacquer, lidPivot);

  let propI = 1;
  for (let i = 1; i < iApex; i++) if (Math.abs(outer[i].u - U_PROP) < Math.abs(outer[propI].u - U_PROP)) propI = i;
  const rimC = offsetPath([outer[propI]], -RIM_T / 2)[0];
  const propUnit = G(new THREE.CylinderGeometry(0.3, 0.36, 1, 14, 1));
  const makeProp = (angle) => {
    const delta = rimC.x + HALF, cz = Z_CASE - rimC.u;
    const base = new THREE.Vector3(rimC.x, Y_RIM_TOP, cz);
    const tip = new THREE.Vector3(-HALF + delta * Math.cos(angle) ** 2, Y_RIM_TOP + delta * Math.cos(angle) * Math.sin(angle), cz);
    const dir = tip.clone().sub(base);
    const mesh = new THREE.Mesh(propUnit, lacquer);
    mesh.scale.set(1, dir.length(), 1);
    mesh.position.copy(base).addScaledVector(dir, 0.5);
    mesh.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.normalize());
    group.add(mesh);
    return mesh;
  };
  const propLong = makeProp(LID_ANGLES.long), propShort = makeProp(LID_ANGLES.short);

  const hinges = new THREE.InstancedMesh(G(new THREE.BoxGeometry(0.42, 0.5, 2.6)), brass, 3);
  [22, 56, 82].forEach((u, i) => { mtx.makeTranslation(-HALF - 0.12, Y_RIM_TOP - 0.22, Z_CASE - u); hinges.setMatrixAt(i, mtx); });
  group.add(hinges);

  // ---- legs and casters ----
  const legH = LEG_TOP - (Y_FLOOR + CASTER_H);
  const legProfile = [[0, 0], [1.2, 0], [1.2, 0.5], [1.05, 0.8], [1.1, 1.4], [1.28, 1.7], [1.15, 2.1], [1.32, 12],
    [1.55, 18.8], [1.82, 19.2], [1.62, 19.7], [1.72, 21.2], [2.15, 21.6], [2.15, 22.6], [2.45, 22.9], [2.45, legH], [0, legH]]
    .map(([r, y]) => new THREE.Vector2(r, Math.min(y, legH)));
  const legs = new THREE.InstancedMesh(G(new THREE.LatheGeometry(legProfile, 24)), lacquer, 3);
  const casterProfile = [];
  for (let a = 0; a <= 8; a++) { const th = (a / 8) * Math.PI * 0.82; casterProfile.push(new THREE.Vector2(0.62 * Math.sin(th), 0.62 - 0.62 * Math.cos(th))); }
  casterProfile.push(new THREE.Vector2(0.95, 1.0), new THREE.Vector2(1.22, 1.05), new THREE.Vector2(1.22, CASTER_H), new THREE.Vector2(0, CASTER_H));
  const casters = new THREE.InstancedMesh(G(new THREE.LatheGeometry(casterProfile, 16)), brass, 3);
  [[-29.3, Z_CASE + 2.4], [29.3, Z_CASE + 2.4], [-17.5, Z_CASE - 88]].forEach(([x, z], i) => {
    mtx.makeTranslation(x, Y_FLOOR + CASTER_H, z); legs.setMatrixAt(i, mtx);
    mtx.makeTranslation(x, Y_FLOOR, z); casters.setMatrixAt(i, mtx);
  });
  group.add(legs, casters);

  // ---- lyre, pedal box, pedals, rods, braces ----
  const lyreTop = -4.0, lyreBot = Y_PEDAL + 1.4;
  const lyreH = lyreTop - lyreBot;
  const ly = (y) => (y / 22.5) * lyreH;
  const lyre = new THREE.Shape();
  lyre.moveTo(-3.0, 0);
  lyre.bezierCurveTo(-5.2, ly(5), -1.6, ly(13), -3.6, ly(20.5));
  lyre.lineTo(-4.8, lyreH); lyre.lineTo(4.8, lyreH); lyre.lineTo(3.6, ly(20.5));
  lyre.bezierCurveTo(1.6, ly(13), 5.2, ly(5), 3.0, 0);
  lyre.closePath();
  const lyreHole = new THREE.Path();
  lyreHole.moveTo(-1.9, ly(1.2));
  lyreHole.bezierCurveTo(-3.9, ly(5.2), -0.6, ly(13), -2.4, ly(19.6));
  lyreHole.lineTo(2.4, ly(19.6));
  lyreHole.bezierCurveTo(0.6, ly(13), 3.9, ly(5.2), 1.9, ly(1.2));
  lyreHole.closePath();
  lyre.holes.push(lyreHole);
  const lyreGeo = new THREE.ExtrudeGeometry(lyre, { depth: 0.8, bevelEnabled: true, bevelThickness: 0.12, bevelSize: 0.12,
    bevelSegments: 2, curveSegments: 14 });
  lyreGeo.translate(0, lyreBot, Z_LYRE - 0.4);
  add(lyreGeo, lacquer);
  place(add(roundedBox(THREE, 10.5, 2.2, 3.6, 0.35), lacquer), 0, Y_PEDAL + 0.3, Z_LYRE);

  const unitCyl = G(new THREE.CylinderGeometry(1, 1, 1, 10, 1));
  const rodMatrix = (a, b, r) => {
    const dir = new THREE.Vector3().subVectors(b, a);
    const q = new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), dir.clone().normalize());
    return new THREE.Matrix4().compose(a.clone().addScaledVector(dir, 0.5), q, new THREE.Vector3(r, dir.length(), r));
  };
  const rods = new THREE.InstancedMesh(unitCyl, brass, 3);
  [-0.9, 0, 0.9].forEach((x, i) => rods.setMatrixAt(i, rodMatrix(new THREE.Vector3(x, lyreBot, Z_LYRE), new THREE.Vector3(x, lyreTop - 1.2, Z_LYRE), 0.16)));
  const braces = new THREE.InstancedMesh(unitCyl, lacquer, 2);
  [-1, 1].forEach((sx, i) => braces.setMatrixAt(i, rodMatrix(new THREE.Vector3(sx * 2.4, Y_PEDAL + 0.6, Z_LYRE - 1.7),
    new THREE.Vector3(sx * 3.6, Y_RIM_BOT, Z_CASE - 15), 0.28)));
  group.add(rods, braces);

  const pedalShape = new THREE.Shape();
  pedalShape.moveTo(-0.35, 0);
  pedalShape.lineTo(-0.35, -2.2);
  pedalShape.quadraticCurveTo(-0.95, -3.3, -0.95, -5.05);
  pedalShape.absarc(0, -5.05, 0.95, Math.PI, Math.PI * 2, false);
  pedalShape.quadraticCurveTo(0.95, -3.3, 0.35, -2.2);
  pedalShape.lineTo(0.35, 0);
  pedalShape.closePath();
  const pedalGeo = G(new THREE.ExtrudeGeometry(pedalShape, { depth: 0.32, bevelEnabled: true, bevelThickness: 0.06,
    bevelSize: 0.06, bevelSegments: 2, curveSegments: 10 }));
  pedalGeo.rotateX(-Math.PI / 2);
  pedalGeo.translate(0, -0.16, 0);
  const pedals = new THREE.InstancedMesh(pedalGeo, brass, 3);
  pedals.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  pedals.frustumCulled = false;
  const writePedal = (i, angle) => {
    const e = pedals.instanceMatrix.array, o = i * 16, c = Math.cos(angle), sn = Math.sin(angle);
    e[o] = 1; e[o + 1] = 0; e[o + 2] = 0; e[o + 3] = 0;
    e[o + 4] = 0; e[o + 5] = c; e[o + 6] = sn; e[o + 7] = 0;
    e[o + 8] = 0; e[o + 9] = -sn; e[o + 10] = c; e[o + 11] = 0;
    e[o + 12] = PEDAL_X[i]; e[o + 13] = Y_PEDAL; e[o + 14] = Z_LYRE; e[o + 15] = 1;
  };
  for (let i = 0; i < 3; i++) writePedal(i, 0);
  group.add(pedals);

  // ---- stage pool: a faint warm ellipse on the floor so the legs, lyre and pedals read against it ----
  const poolTex = poolTexture(THREE); texs.push(poolTex);
  const poolMat = M(new THREE.MeshBasicMaterial({ map: poolTex, color: new THREE.Color(0.055, 0.052, 0.048), transparent: true,
    blending: THREE.AdditiveBlending, depthWrite: false }));
  const pool = add(new THREE.PlaneGeometry(1, 1), poolMat);
  pool.rotation.x = -Math.PI / 2;
  pool.scale.set(118, 150, 1);
  pool.position.set(-2, Y_FLOOR + 0.03, Z_CASE - 46);
  pool.renderOrder = -1;

  // ---- case light: a soft downward spot over the plate takes the ringing chord's colour ----
  const caseLight = new THREE.SpotLight(0xffffff, 0, 0, 52 * DEG, 1.0, 1.2);
  caseLight.position.set(2, 27, Z_CASE - 50);
  caseLight.target.position.set(-3, Y_PLATE, Z_CASE - 50);
  group.add(caseLight, caseLight.target);

  // ---- all geometry that was created inline ----
  group.traverse((o) => { if (o.geometry && !geos.includes(o.geometry)) geos.push(o.geometry); });

  if (ctx.scene) ctx.scene.add(group);

  // ------------------------------------------------------------------ lid modes --
  let framing = ctx.framing || null;
  const portraitOf = (f) => !!f && (f.id === "9:16" || (f.w && f.h && f.h > f.w));
  const pinnedLid = ctx.options?.lid ?? ctx.lid ?? null;
  const pinnedDesk = ctx.options?.desk ?? null;              // true / false pins the music desk; default: off in portrait
  let lidMode = null;
  // Portrait is the recording setup: lid and desk removed, so the whole harp shows under the note bars.
  const setDesk = (on) => { desk.visible = !!on; };
  setDesk(pinnedDesk ?? !portraitOf(framing));
  function setLid(mode) {
    mode = mode === "short" || mode === "off" ? mode : "long";
    lidMode = mode;
    lidPivot.visible = mode !== "off";
    lidPivot.rotation.z = LID_ANGLES[mode] ?? 0;
    propLong.visible = mode === "long";
    propShort.visible = mode === "short";
    // a short lid would sit in the spot's path: bring the light under it and widen the cone
    if (mode === "short") { caseLight.position.y = Y_RIM_TOP + 3.5; caseLight.angle = 72 * DEG; }
    else { caseLight.position.y = 27; caseLight.angle = 52 * DEG; }
    poolMat.opacity = portraitOf(framing) ? 0.5 : 1;
  }
  setLid(pinnedLid || (portraitOf(framing) ? "off" : "long"));

  // ------------------------------------------------------------------ reactive state (preallocated) --
  const energy = new Float32Array(128), flash = new Float32Array(128), shown = new Float32Array(128);
  const rgb = new Float32Array(128 * 3);
  const held = new Uint8Array(128);
  // One "last seen" clock per source: pressed[m].t0 and notes[].t may not share a clock, so neither blocks the other.
  const lastPress = new Float64Array(128).fill(-Infinity), lastNote = new Float64Array(128).fill(-Infinity);
  const lift = new Float32Array(128), kick = new Float32Array(128), check = new Float32Array(128), hammerShown = new Float32Array(128);
  const tmp = new THREE.Color();
  let active = true, pedalLevel = 0, lightLevel = 0;
  let pedalDown = false;

  const strike = (m, vel, when, seen) => {
    if (m < 21 || m > 108 || !(when > seen[m])) return;
    seen[m] = when;
    const v = clamp(vel / 127, 0, 1);
    energy[m] = Math.max(energy[m], Math.pow(v, 1.5));
    flash[m] = Math.max(flash[m], v * v);
    kick[m] = Math.max(kick[m], 0.55 + 0.45 * v);
    if (ctx.noteColor) ctx.noteColor(m, vel, tmp); else tmp.setHSL(((m * 7) % 12) / 12, 0.9, 0.5);
    rgb[m * 3] = tmp.r; rgb[m * 3 + 1] = tmp.g; rgb[m * 3 + 2] = tmp.b;
  };
  const onPressed = (st, m) => {
    held[m] = 1;
    strike(m, st.vel, st.t0 ?? 0, lastPress);
  };

  function update(dt, t, state) {
    if (!active) return;
    dt = clamp(dt || 0, 0, 0.1);
    held.fill(0);
    pedalDown = !!(state && state.pedal);
    if (state && state.pressed) state.pressed.forEach(onPressed);
    if (state && state.notes) {
      const notes = state.notes;
      for (let i = 0; i < notes.length; i++) strike(notes[i].midi, notes[i].vel, notes[i].t, lastNote);
    }
    const kRing = Math.exp(-dt / TAU_RING), kDamped = Math.exp(-dt / TAU_DAMPED), kFlash = Math.exp(-dt / TAU_FLASH);
    const kKick = Math.exp(-dt / TAU_HAMMER);
    const kUp = 1 - Math.exp(-dt / 0.03), kDown = 1 - Math.exp(-dt / 0.08);
    let colDirty = false, damperDirty = false, hammerDirty = false;
    let ar = 0, ag = 0, ab = 0, aw = 0;
    const colors = strColAttr.array;
    const dArr = dampers.instanceMatrix.array, hArr = hammers.instanceMatrix.array;
    for (let m = 21; m <= 108; m++) {
      const i = m - 21;
      const hasDamper = m <= DAMPER_TOP_NOTE;
      const lifted = held[m] === 1 || (pedalDown && hasDamper);
      energy[m] *= lifted || !hasDamper ? kRing : kDamped;
      flash[m] *= kFlash;
      let g = energy[m] * 0.5 + flash[m] * 0.95;
      if (g < 0.002) g = 0;
      if (g !== shown[m]) {
        shown[m] = g;
        colDirty = true;
        const gain = g * STRING_GAIN;
        const r = rgb[m * 3] * gain, gg = rgb[m * 3 + 1] * gain, b = rgb[m * 3 + 2] * gain;
        for (let v = strOff[i], end = strOff[i] + strNv[i]; v < end; v++) {
          const o = v * 3;
          colors[o] = strBase[o] + r; colors[o + 1] = strBase[o + 1] + gg; colors[o + 2] = strBase[o + 2] + b;
        }
      }
      if (g > 0) { ar += rgb[m * 3] * g; ag += rgb[m * 3 + 1] * g; ab += rgb[m * 3 + 2] * g; aw += g; }
      // hammer: kicked to the string on a strike, resting on the back-check while the key is held
      kick[m] *= kKick;
      if (kick[m] < 1e-3) kick[m] = 0;
      const chk = held[m] ? 1 : 0;
      if (check[m] !== chk) {
        let next = check[m] + (chk - check[m]) * (chk > check[m] ? kUp : kDown);
        if (Math.abs(next - chk) < 1e-3) next = chk;
        check[m] = next;
      }
      const hy = Math.max(check[m] * HAMMER_CHECK, kick[m] * HAMMER_KICK);
      if (hy !== hammerShown[m]) { hammerShown[m] = hy; hArr[i * 16 + 13] = HAMMER_REST_TOP + hy; hammerDirty = true; }
      if (hasDamper) {
        const target = lifted ? 1 : 0, cur = lift[m];
        if (cur !== target) {
          let next = cur + (target - cur) * (target > cur ? kUp : kDown);
          if (Math.abs(next - target) < 1e-3) next = target;
          lift[m] = next;
          dArr[i * 16 + 13] = damperY0[i] + next * DAMPER_LIFT;
          damperDirty = true;
        }
      }
    }
    if (colDirty) strColAttr.needsUpdate = true;
    if (damperDirty) dampers.instanceMatrix.needsUpdate = true;
    if (hammerDirty) hammers.instanceMatrix.needsUpdate = true;

    const pTarget = pedalDown ? 1 : 0;
    if (pedalLevel !== pTarget) {
      pedalLevel += (pTarget - pedalLevel) * (pTarget > pedalLevel ? kUp : kDown);
      if (Math.abs(pedalLevel - pTarget) < 1e-3) pedalLevel = pTarget;
      writePedal(2, pedalLevel * 0.11);
      pedals.instanceMatrix.needsUpdate = true;
    }

    const w = Math.min(aw, LIGHT_MAX_W);
    lightLevel = damp(lightLevel, w, w > lightLevel ? 0.03 : 0.25, dt);
    if (aw > 1e-4) {
      // a mixed chord averages toward pastel; push saturation back so the colour survives on gold and spruce
      const mn = Math.min(ar, ag, ab) * 0.6, peak = Math.max(ar, ag, ab) - mn;
      if (peak > 1e-6) caseLight.color.setRGB((ar - mn) / peak, (ag - mn) / peak, (ab - mn) / peak);
    }
    caseLight.intensity = lightLevel < 1e-3 ? 0 : lightLevel * LIGHT_GAIN;
  }

  function resize(f) {
    framing = f || framing;
    if (!pinnedLid) setLid(portraitOf(framing) ? "off" : "long");
    else poolMat.opacity = portraitOf(framing) ? 0.5 : 1;
    if (pinnedDesk === null) setDesk(!portraitOf(framing));
  }

  function setActive(on) {
    active = !!on;
    group.visible = active;
    if (!active) caseLight.intensity = 0;
  }

  function dispose() {
    if (group.parent) group.parent.remove(group);
    for (const g of new Set(geos)) g.dispose();
    for (const m of new Set(mats)) m.dispose();
    for (const t of texs) t.dispose();
    for (const im of [pins, hammers, dampers, hinges, legs, casters, rods, braces, pedals]) im.dispose();
  }

  // Lab cameras, canonical units mapped through the group's transform. The hero stands on the audience side (+x), where
  // the open lid faces, fitted offline so the whole grand (floor to lid tip) fills the frame height; the close-up looks
  // over the fallboard at the pin field, hammers and dampers with the music desk behind.
  const W = (x, y, z) => [group.position.x + x * k, group.position.y + y * k, group.position.z + z * k];
  const views = {
    hero: { from: W(89.8, 52, 123), target: W(-17.6, -3.1, -36.4), fov: 32 },
    close: { from: W(2, 26, 16), target: W(-6, 5, -9), fov: 40 },
  };

  return {
    group, update, resize, setActive, dispose, views, setLid, setDesk,
    parts: { pool, lid: lidPivot, desk, strings, hammers, dampers, pins },
    keyStyle: KEY_STYLE,
    stageHints: {
      floorY: top + Y_FLOOR * k,                                  // key tops 715 mm above the floor
      hideHostBody: true,                                         // the grand brings its own keybed, cheeks and fallboard
      bounds: { x: [group.position.x - (HALF + 0.3) * k, group.position.x + (HALF + 0.3) * k],
                y: [top + Y_FLOOR * k, top + (Y_RIM_TOP + 66.5 * Math.sin(LID_ANGLES.long)) * k],
                z: [group.position.z + (Z_CASE - uMax - 0.3) * k, group.position.z + 3.9 * k] },
    },
    get info() { return { lid: lidMode, desk: desk.visible, strings: stringTotal, pins: stringTotal, hammers: noteCount, dampers: damperCount }; },
    get framing() { return framing; },
  };
}

// keyStyle rides on the definition too, so a host can style its keys before create() runs (the lab reads it there).
const KEY_STYLE = { whiteColor: 0xeeebe3, blackColor: 0x050506, capHeight: null, frontLip: 0 };
export default { id: "concert-grand", name: "Concert grand", keyStyle: KEY_STYLE, keySpan: { first: 21, last: 108 }, create };
