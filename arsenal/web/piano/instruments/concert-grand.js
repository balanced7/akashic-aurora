// Concert grand — arsenal/web/piano/instruments/concert-grand.js  (ES module, a piano instrument; no imports)
//
// A 9 ft concert grand in black lacquer, lid open on the long stick, built procedurally AROUND the host's 88-key row
// (the keys stay host-owned). Everything comes through ctx: THREE, scene, keyX, isBlack, KEY, noteColor, framing, span.
//
// Proportions (instruments/spec.md §2.1; 1 world unit = one white-key pitch = 23.57 mm, 52 whites = 1225.7 mm):
//   case 2740 x 1560 mm [M, D-274 reference] -> 116 x 66.2 units; key tops 715 mm above the floor [M] -> 30.3 units;
//   rim ~380 mm deep [U]; lid long prop ~35-38 deg [R], stick ~790 mm [R] (ours comes out ~33 units = 780 mm);
//   three legs [U], lyre with three pedals [M]. Plan outline: straight spine, concave bentside, convex tail (Bezier).
//   No brand, no lettering anywhere.
//
// Reactive parts (update(dt, t, state)):
//   strings   one LineSegments, two lines per note; a strike lights that note's strings in noteColor (flash ~0.1 s on
//             velocity squared, then a ring that lasts while the key or the pedal holds and damps in ~0.14 s when
//             released). Strings are unlit lines, so only a hard strike's flash crosses the page's bloom threshold.
//   dampers   one InstancedMesh (notes 21-88; the top 20 notes have none, as on a real grand) lift while their key is
//             held or the damper pedal is down.
//   pedal     the right (damper) pedal of the lyre goes down with state.pedal.
//   case glow one SpotLight under the open lid, pointing down at the plate, takes the ringing notes' mixed colour, so the
//             gold plate, strings and inner rim pick up the chord (the lid, keys and stage are outside its cone).
//             Intensity 0 at rest: nothing glows unless it is reacting.
//
// Lighting: every material is MeshPhysicalMaterial and reads correctly under the page's own lights. Lacquer and metal
// highlights come from a private procedural studio map (a 512x256 canvas of soft strips, the same idea as the host's
// dark studio) set per material, never scene.environment, so nothing else in the scene changes.
//
// Budget (measured in the lab, see the report): ~26 draw calls, ~40k triangles, no per-frame allocation.

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
const Y_STRING = 6.05;       // tenor / treble strings
const Y_BASS = 6.75;         // overstrung bass strings cross above the tenor
const LID_ANGLE = 35 * DEG;
const U_FLAP = 9.6;          // front flap hinge line (folded back onto the lid)
const U_PROP = 34;           // where the long stick stands on the bentside rim
const PLATE_INSET = RIM_T + 0.8;
const BRIDGE_INSET = PLATE_INSET + 2.4;
const STR_U_PIN = [2.8, 4.4, 6.0];
const LEG_TOP = Y_RIM_BOT;
const CASTER_H = 1.45;
const Z_LYRE = -1.6;
const Y_PEDAL = -27.9;
const PEDAL_X = [-2.9, 0, 2.9];
const DAMPER_TOP_NOTE = 88;
const DAMPER_LIFT = 0.55;
const U_DAMPER = 12.6, U_DAMPER_BASS = 17.4;

// ---- reactive tuning ----
const STRING_GAIN = 1.55;    // string colour = base + noteColor * glow * gain
const TAU_RING = 1.8, TAU_DAMPED = 0.14, TAU_FLASH = 0.1;
const LIGHT_GAIN = 45, LIGHT_MAX_W = 2.6;

const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const lerp = (a, b, t) => a + (b - a) * t;
const damp = (a, b, tau, dt) => b + (a - b) * Math.exp(-dt / Math.max(tau, 1e-4));

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

// Private studio reflections: black with soft strips, as a canvas equirect (three PMREM-converts it per material).
function studioEnv(THREE) {
  const c = document.createElement("canvas");
  c.width = 512; c.height = 256;
  const g = c.getContext("2d");
  g.fillStyle = "#000"; g.fillRect(0, 0, 512, 256);
  g.filter = "blur(5px)";
  const row = (elev) => (0.5 - elev / 180) * 256;              // equirect row for an elevation in degrees
  const col = (az) => az * 512;                                 // 0.25 = -z (behind the piano), 0.75 = +z (the player)
  const band = (u0, u1, e0, e1, css) => { g.fillStyle = css; g.fillRect(col(u0), row(e1), col(u1) - col(u0), row(e0) - row(e1)); };
  band(0.08, 0.42, 22, 36, "rgb(235,228,215)");                 // long strip behind and above: lid and rim tops from the front
  band(0.58, 0.92, 38, 56, "rgb(205,210,222)");                 // strip above the player: the lid underside
  band(0.955, 1.0, -8, 52, "rgb(240,200,160)");                 // warm strip, stage left (-x)
  band(0.0, 0.045, -8, 52, "rgb(240,200,160)");
  band(0.47, 0.53, -8, 48, "rgb(165,190,240)");                 // cool strip, stage right (+x)
  band(0.0, 1.0, 70, 90, "rgb(26,28,34)");                      // faint ceiling so upward faces are not dead black
  band(0.1, 0.4, 2, 20, "rgb(78,80,92)");                       // low back band: the lid's top reads from the player's seat
  band(0.45, 1.0, -28, -10, "rgb(44,47,56)");                   // front floor bounce: long neutral sheen on the rim walls
  // Warm interior, seen only by downward faces (the lid underside mirrors the gold plate): a gradient that dies away from
  // the hinge, with thin dark lines so it reads as a reflection of strings, not a painted panel (burst 2 was flat mustard).
  const warm = g.createLinearGradient(0, row(-12), 0, row(-70));
  warm.addColorStop(0, "rgb(112,82,40)");
  warm.addColorStop(0.45, "rgb(52,38,18)");
  warm.addColorStop(1, "rgb(8,6,3)");
  g.fillStyle = warm;
  g.fillRect(col(0), row(-12), col(0.32) - col(0), row(-70) - row(-12));
  g.filter = "none";
  g.fillStyle = "rgba(0,0,0,0.45)";
  for (let x = col(0); x < col(0.32); x += 5) g.fillRect(x, row(-12), 2, row(-70) - row(-12));
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

// ------------------------------------------------------------------ the instrument --
function create(ctx) {
  const THREE = ctx.THREE;
  const K = ctx.KEY || {};
  const first = K.first ?? 21, last = K.last ?? 108;
  const S = ctx.span || ctx.keySpan || {};
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
  const M = (m) => (mats.push(m), m);
  const add = (geo, mat, parent = group) => { const mesh = new THREE.Mesh(G(geo), mat); parent.add(mesh); return mesh; };

  // ---- materials (shared) ----
  const env = studioEnv(THREE); texs.push(env);
  const grain = spruceGrain(THREE); texs.push(grain);
  const lacquer = M(new THREE.MeshPhysicalMaterial({ color: 0x030304, roughness: 0.2, metalness: 0, clearcoat: 1,
    clearcoatRoughness: 0.03, envMap: env, envMapIntensity: 1.7 }));
  // The same lacquer, a little softer, for the parts beside the keys: the page's note lights sit 2 units above them, and a
  // mirror coat there turns each strike into a bloom blob (burst 1).
  const lacquerNear = M(new THREE.MeshPhysicalMaterial({ color: 0x040405, roughness: 0.34, metalness: 0, clearcoat: 1,
    clearcoatRoughness: 0.24, envMap: env, envMapIntensity: 1.4 }));
  const satin = M(new THREE.MeshPhysicalMaterial({ color: 0x09090b, roughness: 0.55, clearcoat: 0.3, clearcoatRoughness: 0.35,
    envMap: env, envMapIntensity: 0.6 }));
  const gold = M(new THREE.MeshPhysicalMaterial({ color: 0xb48a3a, metalness: 0.72, roughness: 0.36, clearcoat: 0.3,
    clearcoatRoughness: 0.38, envMap: env, envMapIntensity: 1.35 }));
  const brass = M(new THREE.MeshPhysicalMaterial({ color: 0xd9ad55, metalness: 0.9, roughness: 0.22, envMap: env, envMapIntensity: 1.5 }));
  const steel = M(new THREE.MeshPhysicalMaterial({ color: 0xc8ccd2, metalness: 0.9, roughness: 0.26, envMap: env, envMapIntensity: 1.2 }));
  const spruce = M(new THREE.MeshPhysicalMaterial({ color: 0xffffff, map: grain, roughness: 0.6, clearcoat: 0.15, clearcoatRoughness: 0.5 }));
  const maple = M(new THREE.MeshPhysicalMaterial({ color: 0x8c6a3c, roughness: 0.5, clearcoat: 0.2, clearcoatRoughness: 0.4 }));
  const felt = M(new THREE.MeshPhysicalMaterial({ color: 0x5c0c1a, roughness: 0.95 }));

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
  add(sweep(THREE, offsetPath(outer, -RIM_T / 2), wallProfile(RIM_T / 2, Y_RIM_BOT, Y_RIM_TOP, 0.55, 4), false), lacquer);

  // ---- case arms (key blocks rising into the rim), keybed, key slip, fallboard, felt, belly rail ----
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
  const armR = new THREE.Mesh(armGeo, lacquer); armR.position.x = SPAN_HALF + 0.15; group.add(armR);
  const armL = new THREE.Mesh(armGeo, lacquer); armL.position.x = -HALF; group.add(armL);

  const place = (mesh, x, y, z) => { mesh.position.set(x, y, z); return mesh; };
  place(add(roundedBox(THREE, 52.3, 3.1, 9.8, 0.15), satin), 0, -2.45, -1.7);                 // keybed / key frame
  place(add(roundedBox(THREE, 52.3, 2.05, 0.6, 0.18), lacquerNear), 0, -1.975, 3.5);         // key slip
  place(add(roundedBox(THREE, 52.2, 2.2, 3.1, 0.4), lacquerNear), 0, 0.2, -5.05);            // fallboard (open)
  place(add(new THREE.BoxGeometry(52.1, 0.18, 0.14), felt), 0, 0.09, -3.43);                 // key-back felt
  place(add(roundedBox(THREE, 61.5, 9.2, 1.4, 0.2), lacquerNear), 0, 0.6, -7.3);             // belly rail

  // ---- soundboard and case bottom ----
  const shapeOf = (poly, flipU = false) => {
    const s = new THREE.Shape();
    poly.forEach((q, i) => (i ? s.lineTo(q.x, flipU ? -q.u : q.u) : s.moveTo(q.x, flipU ? -q.u : q.u)));
    s.closePath();
    return s;
  };
  const innerPoly = closePoly(inner, 1.2);
  const sbGeo = new THREE.ShapeGeometry(shapeOf(innerPoly));
  sbGeo.rotateX(-Math.PI / 2);
  sbGeo.translate(0, Y_SOUNDBOARD, Z_CASE);
  add(sbGeo, spruce);
  const bottomGeo = new THREE.ShapeGeometry(shapeOf(closePoly(inner, 0), true));
  bottomGeo.rotateX(Math.PI / 2);
  bottomGeo.translate(0, Y_RIM_BOT + 0.02, Z_CASE);
  add(bottomGeo, satin);

  // ---- plate (gold frame with openings) ----
  const platePoly = closePoly(plateEdge, 0.3);
  const plateX = extentTable(platePoly, uMax);
  const plateShape = shapeOf(platePoly);
  const hole = (u0, u1, f0, f1) => {
    const pts = [];
    for (let u = u0; u <= u1 + 1e-6; u += 1) pts.push({ x: lerp(plateX.lo(u), plateX.hi(u), f0), u });
    for (let u = u1; u >= u0 - 1e-6; u -= 1) pts.push({ x: lerp(plateX.lo(u), plateX.hi(u), f1), u });
    const sm = chaikin(pts, 2);
    const h = new THREE.Path();
    sm.forEach((q, i) => (i ? h.lineTo(q.x, q.u) : h.moveTo(q.x, q.u)));
    h.closePath();
    plateShape.holes.push(h);
  };
  const plateEnd = uMax - PLATE_INSET;
  [[0.03, 0.235], [0.265, 0.47], [0.5, 0.705], [0.735, 0.94]].forEach(([f0, f1]) => hole(10.4, 14.8, f0, f1));
  hole(16.8, plateEnd - 12, 0.05, 0.43);
  hole(16.8, 60, 0.5, 0.93);
  hole(64, Math.min(plateEnd - 16, 84), 0.52, 0.86);
  const plateGeo = new THREE.ExtrudeGeometry(plateShape, { depth: 0.5, bevelEnabled: true, bevelThickness: 0.3,
    bevelSize: 0.28, bevelSegments: 2, curveSegments: 4 });
  plateGeo.rotateX(-Math.PI / 2);
  plateGeo.translate(0, Y_PLATE, Z_CASE);
  add(plateGeo, gold);

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

  // ---- strings, tuning pins, dampers ----
  const bridgeX = extentTable(closePoly(bridgeEdge, 0), uMax);
  const noteCount = 88;
  const LINES_PER_NOTE = 2;
  const strPos = new Float32Array(noteCount * LINES_PER_NOTE * 2 * 3);
  const strCol = new Float32Array(strPos.length);
  const strBase = new Float32Array(strPos.length);
  const stringX = new Float32Array(noteCount), stringSlope = new Float32Array(noteCount);
  const pinGeo = G(new THREE.CylinderGeometry(0.12, 0.12, 0.9, 8, 1));
  const pins = new THREE.InstancedMesh(pinGeo, steel, noteCount * LINES_PER_NOTE);
  const mtx = new THREE.Matrix4();
  let pinI = 0;
  for (let i = 0; i < noteCount; i++) {
    const m = 21 + i;
    const bass = m <= 40;
    const s = bass ? (m - 21) / 19 : (m - 41) / 67;
    const xf = bass ? lerp(-26.8, -18.4, s) : lerp(-17.2, 24.2, s);
    const slope = bass ? lerp(0.2, 0.1, s) : lerp(-0.075, -0.012, s);
    const y = bass ? Y_BASS : Y_STRING;
    const u0 = STR_U_PIN[i % 3];
    let uEnd = u0 + 1;
    for (let u = u0; u < uMax; u += 0.25) {
      const x = xf + slope * (u - u0);
      const lo = bridgeX.lo(u), hi = bridgeX.hi(u);
      if (!(x > lo && x < hi)) break;
      uEnd = u;
    }
    stringX[i] = xf; stringSlope[i] = slope;
    const copper = bass ? 1 : 0;
    for (let l = 0; l < LINES_PER_NOTE; l++) {
      const dx = (l - (LINES_PER_NOTE - 1) / 2) * (bass ? 0.2 : 0.16);
      const o = (i * LINES_PER_NOTE + l) * 6;
      strPos.set([xf + dx, y, Z_CASE - u0, xf + dx + slope * (uEnd - u0), y, Z_CASE - uEnd], o);
      const br = copper ? [0.15, 0.085, 0.04] : [0.13, 0.12, 0.1];
      strBase.set([...br, ...br], o);
      mtx.makeTranslation(xf + dx, Y_PLATE + 1.15, Z_CASE - u0);
      pins.setMatrixAt(pinI++, mtx);
    }
  }
  strCol.set(strBase);
  const strGeo = G(new THREE.BufferGeometry());
  strGeo.setAttribute("position", new THREE.BufferAttribute(strPos, 3));
  const strColAttr = new THREE.BufferAttribute(strCol, 3);
  strColAttr.setUsage(THREE.DynamicDrawUsage);
  strGeo.setAttribute("color", strColAttr);
  const strMat = M(new THREE.LineBasicMaterial({ vertexColors: true }));
  const strings = new THREE.LineSegments(strGeo, strMat);
  strings.frustumCulled = false;
  group.add(strings);
  group.add(pins);

  const damperCount = DAMPER_TOP_NOTE - 21 + 1;
  const damperGeo = G(roundedBox(THREE, 1, 1.15, 1.7, 0.12, 2));
  const dampers = new THREE.InstancedMesh(damperGeo, satin, damperCount);
  dampers.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
  dampers.frustumCulled = false;
  const damperY0 = new Float32Array(damperCount);
  for (let i = 0; i < damperCount; i++) {
    const m = 21 + i, bass = m <= 40;
    const u = bass ? U_DAMPER_BASS : U_DAMPER;
    const x = stringX[i] + stringSlope[i] * (u - STR_U_PIN[i % 3]);
    damperY0[i] = (bass ? Y_BASS : Y_STRING) + 0.1 + 0.575;
    mtx.makeScale(bass ? 0.48 : 0.52, 1, 1).setPosition(x, damperY0[i], Z_CASE - u);
    dampers.setMatrixAt(i, mtx);
  }
  group.add(dampers);

  // ---- lid (hinged on the spine, 35 deg), folded front flap, long stick, hinges ----
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
  lidPivot.rotation.z = LID_ANGLE;
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
  const delta = rimC.x + HALF;
  const cz = Z_CASE - rimC.u;
  const propBase = new THREE.Vector3(rimC.x, Y_RIM_TOP, cz);
  const propTop = new THREE.Vector3(-HALF + delta * Math.cos(LID_ANGLE) ** 2, Y_RIM_TOP + delta * Math.cos(LID_ANGLE) * Math.sin(LID_ANGLE), cz);
  const propDir = propTop.clone().sub(propBase);
  const propLen = propDir.length();
  const prop = add(new THREE.CylinderGeometry(0.3, 0.36, propLen, 14, 1), lacquer);
  prop.position.copy(propBase).addScaledVector(propDir, 0.5);
  prop.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), propDir.normalize());

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
    const e = pedals.instanceMatrix.array, o = i * 16, c = Math.cos(angle), s = Math.sin(angle);
    e[o] = 1; e[o + 1] = 0; e[o + 2] = 0; e[o + 3] = 0;
    e[o + 4] = 0; e[o + 5] = c; e[o + 6] = s; e[o + 7] = 0;
    e[o + 8] = 0; e[o + 9] = -s; e[o + 10] = c; e[o + 11] = 0;
    e[o + 12] = PEDAL_X[i]; e[o + 13] = Y_PEDAL; e[o + 14] = Z_LYRE; e[o + 15] = 1;
  };
  for (let i = 0; i < 3; i++) writePedal(i, 0);
  group.add(pedals);

  // ---- case light: a soft downward spot over the plate takes the ringing chord's colour ----
  // A point light here mirrored in the lid as a bloom "moon" (burst 1). The spot sits below the open lid and points down,
  // so the lid, the keys and the stage stay outside its cone; the plate, strings and inner rim take the colour.
  const caseLight = new THREE.SpotLight(0xffffff, 0, 0, 52 * DEG, 1.0, 1.2);
  caseLight.position.set(2, 27, Z_CASE - 50);
  caseLight.target.position.set(-3, Y_PLATE, Z_CASE - 50);
  group.add(caseLight, caseLight.target);

  // ---- all geometry that was created inline ----
  group.traverse((o) => { if (o.geometry && !geos.includes(o.geometry)) geos.push(o.geometry); });

  if (ctx.scene) ctx.scene.add(group);

  // ------------------------------------------------------------------ reactive state (preallocated) --
  const energy = new Float32Array(128), flash = new Float32Array(128), shown = new Float32Array(128);
  const rgb = new Float32Array(128 * 3);
  const held = new Uint8Array(128);
  // One "last seen" clock per source: pressed[m].t0 and notes[].t may not share a clock, so neither blocks the other.
  const lastPress = new Float64Array(128).fill(-Infinity), lastNote = new Float64Array(128).fill(-Infinity);
  const lift = new Float32Array(128);
  const tmp = new THREE.Color();
  let active = true, pedalLevel = 0, lightLevel = 0, framing = ctx.framing || null;
  let pedalDown = false;

  const strike = (m, vel, when, seen) => {
    if (m < 21 || m > 108 || !(when > seen[m])) return;
    seen[m] = when;
    const v = clamp(vel / 127, 0, 1);
    energy[m] = Math.max(energy[m], Math.pow(v, 1.5));
    flash[m] = Math.max(flash[m], v * v);
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
    const kUp = 1 - Math.exp(-dt / 0.03), kDown = 1 - Math.exp(-dt / 0.08);
    let colDirty = false, damperDirty = false;
    let ar = 0, ag = 0, ab = 0, aw = 0;
    const colors = strColAttr.array;
    const dArr = dampers.instanceMatrix.array;
    for (let m = 21; m <= 108; m++) {
      const hasDamper = m <= DAMPER_TOP_NOTE;
      const lifted = held[m] === 1 || (pedalDown && hasDamper);
      energy[m] *= lifted || !hasDamper ? kRing : kDamped;
      flash[m] *= kFlash;
      let g = energy[m] * 0.5 + flash[m] * 0.95;
      if (g < 0.002) g = 0;
      if (g !== shown[m]) {
        shown[m] = g;
        colDirty = true;
        const gain = g * STRING_GAIN, i = m - 21;
        const r = rgb[m * 3] * gain, gg = rgb[m * 3 + 1] * gain, b = rgb[m * 3 + 2] * gain;
        for (let l = 0; l < LINES_PER_NOTE * 2; l++) {
          const o = (i * LINES_PER_NOTE * 2 + l) * 3;
          colors[o] = strBase[o] + r; colors[o + 1] = strBase[o + 1] + gg; colors[o + 2] = strBase[o + 2] + b;
        }
      }
      if (g > 0) { ar += rgb[m * 3] * g; ag += rgb[m * 3 + 1] * g; ab += rgb[m * 3 + 2] * g; aw += g; }
      if (hasDamper) {
        const target = lifted ? 1 : 0, cur = lift[m];
        if (cur !== target) {
          let next = cur + (target - cur) * (target > cur ? kUp : kDown);
          if (Math.abs(next - target) < 1e-3) next = target;
          lift[m] = next;
          dArr[(m - 21) * 16 + 13] = damperY0[m - 21] + next * DAMPER_LIFT;
          damperDirty = true;
        }
      }
    }
    if (colDirty) strColAttr.needsUpdate = true;
    if (damperDirty) dampers.instanceMatrix.needsUpdate = true;

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

  function resize(f) { framing = f || framing; }

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
    pins.dispose(); dampers.dispose(); hinges.dispose(); legs.dispose(); casters.dispose(); rods.dispose(); braces.dispose(); pedals.dispose();
  }

  // Lab cameras, canonical units mapped through the group's transform. The hero stands on the audience side (+x), where
  // the open lid faces; the close-up looks over the fallboard at the dampers and strings a chord in the middle lights.
  const W = (x, y, z) => [group.position.x + x * k, group.position.y + y * k, group.position.z + z * k];
  const views = {
    hero: { from: W(148, 42, 94), target: W(-9, 3, -46), fov: 30 },
    close: { from: W(10, 23, 17), target: W(-8, 4, -17), fov: 36 },
  };

  return {
    group, update, resize, setActive, dispose, views,
    // Hints for the host. Keys stay host-owned; these only suggest a look and where the stage floor belongs.
    keyStyle: KEY_STYLE,
    stageHints: {
      floorY: top + Y_FLOOR * k,                                  // key tops 715 mm above the floor
      hideHostBody: true,                                         // the grand brings its own keybed, cheeks and fallboard
      bounds: { x: [group.position.x - (HALF + 0.3) * k, group.position.x + (HALF + 0.3) * k],
                y: [top + Y_FLOOR * k, top + (Y_RIM_TOP + 66.5 * Math.sin(LID_ANGLE)) * k],
                z: [group.position.z + (Z_CASE - uMax - 0.3) * k, group.position.z + 3.9 * k] },
    },
    get framing() { return framing; },
  };
}

// keyStyle rides on the definition too, so a host can style its keys before create() runs (the lab reads it there).
const KEY_STYLE = { whiteColor: 0xeeebe3, blackColor: 0x050506, capHeight: null, frontLip: 0 };
export default { id: "concert-grand", name: "Concert grand", keyStyle: KEY_STYLE, keySpan: { first: 21, last: 108 }, create };
