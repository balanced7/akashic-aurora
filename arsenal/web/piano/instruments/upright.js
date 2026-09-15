// Walnut Upright: arsenal/web/piano/instruments/upright.js (ES module, a piano instrument; no imports)
//
// A warm walnut upright built around the host's 88-key row. The keys stay the host's. This module draws the case
// around them: fallboard, cheek arms with a scrolled top, key slip, a music shelf holding an open book, turned
// front legs on toe blocks, three brass pedals, a pair of swing-arm candle sconces and a little metronome on the lid.
// Everything is procedural: rounded boxes, extrusions, lathes, tubes and canvas textures (walnut grain; a veneer
// atlas holding a straight vertical-stripe kneeboard and a horizontal-grain upper panel, planar-mapped so each panel
// shows its whole region; the book's paper). No brand name or logo anywhere; the only lettering is our own chord name
// on the book.
//
// Proportions (spec.md section 2.2): about 1500 W x 1250 H x 610 D mm, key tops about 750 mm above the floor. One
// host world unit is one white-key pitch; the 52 white keys are 1225.7 mm, so 1 mm = 52 / 1225.7 units. The whole
// case is built at the host's scale and scaled by (key span / 52), so a host with other key sizes still fits.
//
// What reacts (everything that can glow sits under the bloom threshold until a note pushes it over):
//   felt strip   the burgundy felt under the fallboard lights up behind each key, in its note colour. A strike
//                peaks and falls back within about 0.2 s to a held glow; pedal-held notes fade slowly; the peak is
//                the only part that blooms. The same light washes up the fallboard's lower face.
//   candles      the two flames are lit at rest (warm, no bloom). Strikes feed them: they stretch, brighten past
//                the bloom threshold and lean toward the colours just played, and their light throws that colour
//                onto the panel, the book, the brass and the host's keys (see Lifetime). In portrait framing (the
//                9:16 player, where note bars rise over the upper panel) the flame colour is halved and the lights cap
//                at 60.
//   book         shows the chord name, Nashville number and key on its right page, inked in the root's colour. The
//                letters glow a little on a strike (emissive at most 0.8, and luminance-capped so they stay under
//                bloom) and fade over about half a second.
//   pedal        the right (sustain) pedal goes down with the sustain pedal.
//   metronome    the pendulum starts swinging while you play and slows to rest a few seconds after you stop.
//
// Lifetime: after dispose() the renderer's geometries, textures and programs are back where they were before create(),
// except for one bounded cost kept on purpose. The candles are scene PointLights by default so they warm the host's ivory
// keys (without them the keys read visibly grey; ruled 2026-09-15). A scene light makes every host material that draws
// with it (the keys, the floor) compile a light-count variant three keeps for the page's life: 2 programs, once, not per
// switch. ctx.options.hostLight === false removes that cost: the candles then light only this case's own materials in its
// shaders, with three's point-light maths, and dispose() returns exactly to baseline.
//
// Contract: default export {id, name, create(ctx)}; create returns {group, update(dt, t, state), resize(framing),
// setActive(on), dispose()} plus hints: keyStyle, stage and views (see the bottom of create).

const TAU = Math.PI * 2;
const HOST_SPAN = 52;                     // white keys, in host units
const MM = HOST_SPAN / 1225.7;            // host units per millimetre
const FLOOR_Y = -750 * MM;                // key tops (y 0) sit 750 mm above the floor
const FALL_TILT = 22.5 * Math.PI / 180;   // the open fallboard leans back this far from vertical
const LEAN = 3 * Math.PI / 180;           // the book leans back against the panel
const FELT_W = 208;                       // felt light texels across the 52 white keys (4 per key)

// Aged ivory and ebony; a thin ivory cap and front lip. Also on the handle create() returns.
const KEY_STYLE = Object.freeze({ whiteColor: 0xe9dcc2, blackColor: 0x17110d, capHeight: 0.12, frontLip: 0.05 });

export default { id: "upright", name: "Walnut Upright", keyStyle: KEY_STYLE, create };

function create(ctx) {
  const T_BUILD = performance.now();
  const THREE = ctx.THREE;
  const KEY = ctx.KEY || { first: 21, last: 108 };
  const FIRST = KEY.first, COUNT = KEY.last - KEY.first + 1;
  const keyX = ctx.keyX;
  const isBlack = ctx.isBlack;

  // ------------------------------------------------------------ key span --
  const span = ctx.span || {};
  const x0 = span.left !== undefined ? span.left : span.x0 !== undefined ? span.x0 : keyX(FIRST) - 0.5;
  const x1 = span.right !== undefined ? span.right : span.x1 !== undefined ? span.x1 : keyX(KEY.last) + 0.5;
  const cx = (x0 + x1) / 2;
  const S = (x1 - x0) / HOST_SPAN;        // 1 on the host

  const group = new THREE.Group();
  group.name = "instrument:upright";
  group.position.set(cx, 0, 0);
  group.scale.setScalar(S);
  const disposables = [];
  const keep = (x) => { disposables.push(x); return x; };

  // ------------------------------------------------------------ helpers --
  // A rounded box with smooth normals: a segmented box whose edge rows are spread by tan() so the rounding is circular,
  // then pushed onto a radius-r shell around the inner box (the same idea as three's RoundedBoxGeometry, no import).
  function roundBox(w, h, d, r, k = 2) {
    r = Math.max(0.002, Math.min(r, w * 0.49, h * 0.49, d * 0.49));
    const n = 2 * k + 1;
    const g = new THREE.BoxGeometry(1, 1, 1, n, n, n);
    const pa = g.attributes.position.array, na = g.attributes.normal.array;
    const half = [w / 2, h / 2, d / 2];
    const p = [0, 0, 0], q = [0, 0, 0];
    for (let i = 0; i < pa.length; i += 3) {
      for (let a = 0; a < 3; a++) {
        const idx = Math.round((pa[i + a] + 0.5) * n);
        const inner = half[a] - r;
        if (idx <= k) p[a] = -inner - r * Math.tan((k - idx) / k * Math.PI / 4);
        else p[a] = inner + r * Math.tan((idx - (n - k)) / k * Math.PI / 4);
        q[a] = Math.max(-inner, Math.min(inner, p[a]));
      }
      let dx = p[0] - q[0], dy = p[1] - q[1], dz = p[2] - q[2];
      const len = Math.hypot(dx, dy, dz) || 1;
      dx /= len; dy /= len; dz /= len;
      pa[i] = q[0] + dx * r; pa[i + 1] = q[1] + dy * r; pa[i + 2] = q[2] + dz * r;
      na[i] = dx; na[i + 1] = dy; na[i + 2] = dz;
    }
    return g;
  }
  // Area-weighted normals across faces that meet at under creaseDeg (for extrusions: smooth curves, crisp caps).
  function smoothNormals(geo, creaseDeg) {
    const pa = geo.attributes.position.array, tris = pa.length / 9;
    const fn = new Float32Array(tris * 3);
    const buckets = new Map();
    const keyOf = (i) => `${Math.round(pa[i] * 1e3)},${Math.round(pa[i + 1] * 1e3)},${Math.round(pa[i + 2] * 1e3)}`;
    for (let t = 0; t < tris; t++) {
      const o = t * 9;
      const ax = pa[o + 3] - pa[o], ay = pa[o + 4] - pa[o + 1], az = pa[o + 5] - pa[o + 2];
      const bx = pa[o + 6] - pa[o], by = pa[o + 7] - pa[o + 1], bz = pa[o + 8] - pa[o + 2];
      fn[t * 3] = ay * bz - az * by; fn[t * 3 + 1] = az * bx - ax * bz; fn[t * 3 + 2] = ax * by - ay * bx;
      for (let c = 0; c < 3; c++) {
        const k = keyOf(o + c * 3);
        let list = buckets.get(k);
        if (!list) buckets.set(k, (list = []));
        list.push(t);
      }
    }
    const cosC = Math.cos(creaseDeg * Math.PI / 180);
    const nrm = new Float32Array(pa.length);
    for (let t = 0; t < tris; t++) {
      const fx = fn[t * 3], fy = fn[t * 3 + 1], fz = fn[t * 3 + 2];
      const fl = Math.hypot(fx, fy, fz) || 1;
      for (let c = 0; c < 3; c++) {
        const list = buckets.get(keyOf(t * 9 + c * 3));
        let sx = 0, sy = 0, sz = 0;
        for (const j of list) {
          const gx = fn[j * 3], gy = fn[j * 3 + 1], gz = fn[j * 3 + 2];
          const gl = Math.hypot(gx, gy, gz) || 1;
          if ((fx * gx + fy * gy + fz * gz) / (fl * gl) >= cosC) { sx += gx; sy += gy; sz += gz; }
        }
        const sl = Math.hypot(sx, sy, sz) || 1;
        nrm[t * 9 + c * 3] = sx / sl; nrm[t * 9 + c * 3 + 1] = sy / sl; nrm[t * 9 + c * 3 + 2] = sz / sl;
      }
    }
    geo.setAttribute("normal", new THREE.BufferAttribute(nrm, 3));
    return geo;
  }
  // Merge parts into one draw call. part: {geo, pos, rot, grain}. grain 'x'|'y'|'z' box-maps UVs in case space with
  // the wood's long grain along that axis (every board gets its own offset into the texture); no grain keeps the
  // part's own UVs (the veneer panels, the book).
  const GRAIN_U = 24, GRAIN_V = 12;  // host units covered by one repeat of the grain texture (along, across)
  function merge(parts) {
    const m4 = new THREE.Matrix4(), qt = new THREE.Quaternion(), eu = new THREE.Euler(), one = new THREE.Vector3(1, 1, 1);
    const tv = new THREE.Vector3();
    let count = 0;
    const ready = [];
    parts.forEach((part, pi) => {
      let g = part.geo.index ? part.geo.toNonIndexed() : part.geo;
      if (g !== part.geo) part.geo.dispose();
      if (part.planar) {
        // planar UVs over the part's own x/y extent, into an atlas rect [u0, v0, u1, v1]. A rounded box's own UVs put
        // the whole flat face into 0.4..0.6, which magnified the veneer five times into a swirl with stepped lines.
        g.computeBoundingBox();
        const bb = g.boundingBox, [u0, v0, u1, v1] = part.planar;
        const pa = g.attributes.position.array, uv = new Float32Array(pa.length / 3 * 2);
        const sx = (u1 - u0) / Math.max(1e-6, bb.max.x - bb.min.x), sy = (v1 - v0) / Math.max(1e-6, bb.max.y - bb.min.y);
        for (let i = 0, j = 0; i < pa.length; i += 3, j += 2) {
          uv[j] = u0 + (pa[i] - bb.min.x) * sx;
          uv[j + 1] = v0 + (pa[i + 1] - bb.min.y) * sy;
        }
        g.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
      }
      const r = part.rot || [0, 0, 0], p = part.pos || [0, 0, 0];
      eu.set(r[0], r[1], r[2], r[3] || "XYZ");
      m4.compose(tv.set(p[0], p[1], p[2]), qt.setFromEuler(eu), one);
      g.applyMatrix4(m4);
      ready.push({ g, part, seed: pi });
      count += g.attributes.position.count;
    });
    const P = new Float32Array(count * 3), N = new Float32Array(count * 3), UV = new Float32Array(count * 2);
    const AX = { x: 0, y: 1, z: 2 };
    let o = 0;
    for (const { g, part, seed } of ready) {
      const n = g.attributes.position.count;
      const pa = g.attributes.position.array, na = g.attributes.normal.array, ua = g.attributes.uv ? g.attributes.uv.array : null;
      P.set(pa, o * 3);
      N.set(na, o * 3);
      const ga = part.grain ? AX[part.grain] : -1;
      const su = seed * 0.37 % 1, sv = seed * 0.61 % 1;
      for (let i = 0; i < n; i++) {
        let u, v;
        if (ga < 0) { u = ua ? ua[i * 2] : 0; v = ua ? ua[i * 2 + 1] : 0; }
        else {
          const ax = Math.abs(na[i * 3]), ay = Math.abs(na[i * 3 + 1]), az = Math.abs(na[i * 3 + 2]);
          const dom = ax >= ay && ax >= az ? 0 : ay >= az ? 1 : 2;
          if (dom !== ga) {
            const other = 3 - dom - ga;
            u = pa[i * 3 + ga] / GRAIN_U + su; v = pa[i * 3 + other] / GRAIN_V + sv;
          } else {  // end grain: a squeezed patch of the texture
            u = pa[i * 3 + (dom + 1) % 3] / GRAIN_V * 0.25 + su; v = pa[i * 3 + (dom + 2) % 3] / GRAIN_V + sv;
          }
        }
        UV[(o + i) * 2] = u; UV[(o + i) * 2 + 1] = v;
      }
      o += n;
      g.dispose();
    }
    const out = new THREE.BufferGeometry();
    out.setAttribute("position", new THREE.BufferAttribute(P, 3));
    out.setAttribute("normal", new THREE.BufferAttribute(N, 3));
    out.setAttribute("uv", new THREE.BufferAttribute(UV, 2));
    out.computeBoundingSphere();
    return keep(out);
  }
  const lathe = (pts, segs = 20) => new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), segs);

  // ------------------------------------------------------------ textures --
  function hash2(ix, iy, seed) {
    let h = (Math.imul(ix, 374761393) + Math.imul(iy, 668265263) + Math.imul(seed, 1442695041)) | 0;
    h = Math.imul(h ^ (h >>> 13), 1274126177);
    return ((h ^ (h >>> 16)) >>> 0) / 4294967296;
  }
  function vnoise(x, y, px, py, seed) {  // value noise, periodic over px by py lattice cells
    const ix = Math.floor(x), iy = Math.floor(y), fx = x - ix, fy = y - iy;
    const xa = ((ix % px) + px) % px, xb = (xa + 1) % px, ya = ((iy % py) + py) % py, yb = (ya + 1) % py;
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    const a = hash2(xa, ya, seed), b = hash2(xb, ya, seed), c = hash2(xa, yb, seed), d = hash2(xb, yb, seed);
    return a + (b - a) * sx + (c - a) * sy + (a - b - c + d) * sx * sy;
  }
  // Walnut toward spec #6b3f22 but less saturated than it: the candles and key light are warm, and the earlier
  // [150, 94, 58] / [46, 26, 16] read orange-red once lit.
  const WALNUT_LIGHT = [138, 97, 68], WALNUT_DARK = [40, 27, 19];
  function paintWood(W, H, valueAt) {
    const cv = document.createElement("canvas");
    cv.width = W; cv.height = H;
    const g2 = cv.getContext("2d");
    const img = g2.createImageData(W, H), px = img.data;
    for (let y = 0; y < H; y++) {
      for (let x = 0; x < W; x++) {
        const t = Math.max(0, Math.min(1, valueAt(x, y)));
        const o = (y * W + x) * 4;
        px[o] = WALNUT_DARK[0] + (WALNUT_LIGHT[0] - WALNUT_DARK[0]) * t;
        px[o + 1] = WALNUT_DARK[1] + (WALNUT_LIGHT[1] - WALNUT_DARK[1]) * t;
        px[o + 2] = WALNUT_DARK[2] + (WALNUT_LIGHT[2] - WALNUT_DARK[2]) * t;
        px[o + 3] = 255;
      }
    }
    g2.putImageData(img, 0, 0);
    return cv;
  }
  // Straight walnut, tileable both ways: growth rings (y) warped along the grain (x), dark latewood lines, long pores.
  const RINGS = 40;
  const grainCanvas = paintWood(1024, 512, (x, y) => {
    const u = x / 1024, v = y / 512;
    const warp = 0.35 * Math.sin(TAU * (2 * u + v)) + 0.12 * Math.sin(TAU * (5 * u - 2 * v) + 1.7) + 0.6 * vnoise(u * 6, v * 3, 6, 3, 11);
    const r = v * RINGS + warp * 1.2;
    const late = Math.pow(0.5 + 0.5 * Math.cos(TAU * r), 10);  // a smooth latewood line: no stair-steps when magnified
    const pores = vnoise(u * 64, v * 256, 64, 256, 5);
    const streak = vnoise(u * 8, v * 120, 8, 120, 17);
    const figure = vnoise(u * 3, v * 8, 3, 8, 3);
    return 0.36 + 0.34 * figure + 0.12 * pores + 0.12 * streak - 0.32 * late;
  });
  // Veneer atlas, 1024 x 2048 (flipY: canvas top = v 1). Both halves are mirrored about the centre line (a quiet
  // bookmatch) with the old cathedral sway cut to 40%.
  //   top half (v 0.5..1)     kneeboard: straight vertical stripes, low-contrast figure, latewood lines at 0.15
  //   bottom half (v 0..0.5)  upper panel: horizontal grain, long soft streaks, latewood lines at 0.2 (was ~0.5)
  const veneerCanvas = paintWood(1024, 2048, (x, y) => {
    const xm = x < 512 ? 511 - x : x - 512, xn = xm / 512;
    if (y < 1024) {
      const yu = y / 1024;
      const sway = 0.4 * (0.05 * Math.sin(TAU * (yu * 1.2 + xn * 1.5)) + 0.05 * vnoise(xn * 4, yu * 3, 64, 64, 9));
      const late = Math.pow(0.5 + 0.5 * Math.cos(TAU * (xn + sway) * 26), 6);
      const figure = vnoise(xn * 12, yu * 1.5, 64, 64, 13);
      const pores = vnoise(xn * 300, yu * 16, 4096, 4096, 21);
      return 0.5 + 0.1 * figure + 0.08 * pores - 0.15 * late - 0.04 * xn;
    }
    // straighter and thinner lines than the kneeboard's: the close-up puts this panel at 4x magnification
    const yu = (y - 1024) / 1024;
    const warp = 0.2 * (0.05 * Math.sin(TAU * (xn * 1.1 + yu * 0.4)) + 0.05 * vnoise(xn * 2, yu * 4, 64, 64, 7));
    const late = Math.pow(0.5 + 0.5 * Math.cos(TAU * (yu + warp) * 18), 12);
    const streak = vnoise(xn * 2.5, yu * 40, 64, 64, 17);
    const pores = vnoise(xn * 60, yu * 320, 4096, 4096, 23);
    return 0.48 + 0.08 * streak + 0.07 * pores - 0.2 * late - 0.03 * xn;
  });
  const ATLAS_PAD_U = 4 / 1024, ATLAS_PAD_V = 6 / 2048;
  const KNEE_RECT = [ATLAS_PAD_U, 0.5 + ATLAS_PAD_V, 1 - ATLAS_PAD_U, 1 - ATLAS_PAD_V];
  const UPPER_RECT = [ATLAS_PAD_U, ATLAS_PAD_V, 1 - ATLAS_PAD_U, 0.5 - ATLAS_PAD_V];
  function canvasTex(cv, repeat) {
    const t = keep(new THREE.CanvasTexture(cv));
    t.colorSpace = THREE.SRGBColorSpace;
    t.anisotropy = 8;
    if (repeat) { t.wrapS = THREE.RepeatWrapping; t.wrapT = THREE.RepeatWrapping; }
    return t;
  }
  const grainTex = canvasTex(grainCanvas, true);
  const veneerTex = canvasTex(veneerCanvas, false);

  // The felt's light: one row of texels across the key span, rewritten only while something is lit.
  const feltData = new Uint8Array(FELT_W * 4);
  const feltTex = keep(new THREE.DataTexture(feltData, FELT_W, 1, THREE.RGBAFormat));
  feltTex.magFilter = THREE.LinearFilter;
  feltTex.minFilter = THREE.LinearFilter;
  feltTex.needsUpdate = true;

  // ------------------------------------------------------------ materials --
  const M = {
    case: new THREE.MeshPhysicalMaterial({ map: grainTex, roughness: 0.35, clearcoat: 0.6, clearcoatRoughness: 0.2 }),
    veneer: new THREE.MeshPhysicalMaterial({ map: veneerTex, roughness: 0.35, clearcoat: 0.6, clearcoatRoughness: 0.14 }),
    dark: new THREE.MeshPhysicalMaterial({ color: 0x1e120b, roughness: 0.78 }),
    leather: new THREE.MeshPhysicalMaterial({ color: 0x4a1a12, roughness: 0.5, clearcoat: 0.3, clearcoatRoughness: 0.4 }),
    felt: new THREE.MeshPhysicalMaterial({ color: 0x6e1622, roughness: 1, sheen: 1, sheenColor: new THREE.Color(0xd07080),
      sheenRoughness: 0.55, emissive: 0xffffff, emissiveMap: feltTex, emissiveIntensity: 3.0 }),
    brass: new THREE.MeshPhysicalMaterial({ color: 0xd2a04e, metalness: 0.45, roughness: 0.3, clearcoat: 0.4, clearcoatRoughness: 0.2 }),
    wax: new THREE.MeshPhysicalMaterial({ color: 0xf3e8d2, roughness: 0.55, sheen: 0.5, sheenColor: new THREE.Color(0xffe0b0),
      emissive: 0xff9a40, emissiveIntensity: 0.03 }),
    flame: new THREE.MeshBasicMaterial({ vertexColors: true, blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }),
    wash: new THREE.MeshBasicMaterial({ map: feltTex, vertexColors: true, color: new THREE.Color(0.85, 0.85, 0.85),
      blending: THREE.AdditiveBlending, transparent: true, depthWrite: false }),
    paper: null,  // made with the book below
  };
  for (const k in M) if (M[k]) keep(M[k]);

  // ------------------------------------------------------------ the case --
  const wood = [], veneer = [], dark = [], brass = [];
  const add = (list, geo, pos, grain, rot, planar) => list.push({ geo, pos, grain, rot, planar });

  // sides, lid and its moulding
  for (const s of [-1, 1]) add(wood, roundBox(2.0, 52.0, 17.9, 0.24), [s * 30.8, FLOOR_Y + 26.0, -13.35], "y");
  add(wood, roundBox(64.6, 0.8, 19.0, 0.32, 3), [0, 20.6, -13.5], "x");
  add(wood, roundBox(61.6, 0.55, 0.9, 0.26), [0, 19.95, -4.75], "x");
  add(dark, roundBox(59.6, 51.0, 0.6, 0.1), [0, FLOOR_Y + 25.5, -21.9]);
  // upper panel with a moulded frame around a bookmatched veneer
  add(wood, roundBox(59.6, 17.2, 0.6, 0.12), [0, 11.6, -5.5], "x");
  add(veneer, roundBox(54.6, 12.6, 0.2, 0.06), [0, 12.6, -5.12], null, null, UPPER_RECT);
  add(wood, roundBox(55.6, 0.5, 0.36, 0.16), [0, 19.15, -5.05], "x");
  add(wood, roundBox(55.6, 0.5, 0.36, 0.16), [0, 6.05, -5.05], "x");
  for (const s of [-1, 1]) add(wood, roundBox(0.5, 13.6, 0.36, 0.16), [s * 27.55, 12.6, -5.05], "y");
  // music shelf and its lip
  add(wood, roundBox(55.0, 0.7, 1.9, 0.26), [0, 4.75, -4.5], "x");
  add(wood, roundBox(55.0, 0.5, 0.2, 0.08), [0, 5.25, -3.62], "x");
  // the open fallboard, leaning back over the felt; end blocks either side
  add(wood, roundBox(52.1, 4.45, 0.42, 0.19, 3), [0, 2.35, -4.15], "x", [-FALL_TILT, 0, 0]);
  for (const s of [-1, 1]) add(wood, roundBox(3.7, 5.4, 1.2, 0.16), [s * 27.95, 1.8, -5.0], "y");
  add(dark, roundBox(52.1, 1.7, 2.3, 0.05), [0, -0.02, -4.55]);  // the cavity under the fallboard
  // cheek arms: a side profile with a scrolled front and a rise at the back, extruded across the arm
  const cheekShape = new THREE.Shape();
  cheekShape.moveTo(-5.4, -2.6);
  cheekShape.lineTo(3.75, -2.6);
  cheekShape.lineTo(3.75, -0.25);
  cheekShape.quadraticCurveTo(3.75, 1.05, 2.55, 1.05);
  cheekShape.lineTo(-1.6, 1.25);
  cheekShape.quadraticCurveTo(-4.4, 1.35, -4.4, 3.4);
  cheekShape.lineTo(-5.4, 3.4);
  cheekShape.closePath();
  const cheekGeo = () => {
    const g = new THREE.ExtrudeGeometry(cheekShape, { depth: 5.54, bevelEnabled: true, bevelThickness: 0.08, bevelSize: 0.08,
      bevelSegments: 2, curveSegments: 14 });
    g.rotateY(-Math.PI / 2);
    return smoothNormals(g, 32);
  };
  add(wood, cheekGeo(), [31.72, 0, 0], "z");
  add(wood, cheekGeo(), [-26.02, 0, 0], "z");
  // key slip in front of the keys, keybed board under them
  add(wood, roundBox(52.2, 2.2, 0.7, 0.2), [0, -1.6, 3.5], "x");
  add(wood, roundBox(59.6, 0.5, 9.8, 0.16), [0, -2.85, -1.0], "x");
  add(dark, roundBox(52.2, 1.75, 8.9, 0.05), [0, -1.73, -1.3]);
  // lower case: kneeboard, frame, veneer, plinth, toe blocks, turned legs
  add(wood, roundBox(59.6, 27.5, 0.6, 0.1), [0, -16.85, -5.5], "x");
  add(veneer, roundBox(52.6, 22.6, 0.2, 0.06), [0, -16.7, -5.12], null, null, KNEE_RECT);
  add(wood, roundBox(54.1, 0.5, 0.36, 0.16), [0, -5.0, -5.05], "x");
  add(wood, roundBox(54.1, 0.5, 0.36, 0.16), [0, -28.4, -5.05], "x");
  for (const s of [-1, 1]) add(wood, roundBox(0.5, 23.9, 0.36, 0.16), [s * 26.8, -16.7, -5.05], "y");
  add(wood, roundBox(59.6, 1.2, 1.5, 0.22), [0, FLOOR_Y + 0.6, -5.05], "x");
  const LEG_H = -3.1 - (FLOOR_Y + 0.9);
  const legPts = [[0, 0], [1.05, 0], [1.05, 0.5], [0.8, 0.8], [0.62, 1.4], [0.62, 3.2], [0.9, 4.6], [1.12, 6.6], [1.05, 8.4],
    [0.72, 9.8], [0.5, 11.2], [0.48, 17.5], [0.62, 19.2], [0.95, 21.4], [1.05, 23], [0.8, 24.6], [0.62, 25.6], [0.95, 26.4],
    [1.1, 27.2], [1.1, 28.2], [0, 28.2]].map(([r, y]) => [r, y * LEG_H / 28.2]);
  for (const s of [-1, 1]) {
    add(wood, roundBox(3.4, 0.9, 9.0, 0.26), [s * 28.95, FLOOR_Y + 0.45, -0.8], "z");
    add(wood, lathe(legPts, 20), [s * 28.95, FLOOR_Y + 0.9, 1.7], "y");
  }

  // pedals: brass paddles out of the plinth; the right one is the sustain and moves
  const paddle = new THREE.Shape();
  paddle.moveTo(-0.32, 0); paddle.lineTo(0.32, 0); paddle.lineTo(0.42, -3.3);
  paddle.quadraticCurveTo(0.62, -4.6, 0, -4.7); paddle.quadraticCurveTo(-0.62, -4.6, -0.42, -3.3); paddle.closePath();
  const paddleGeo = () => {
    const g = new THREE.ExtrudeGeometry(paddle, { depth: 0.22, bevelEnabled: true, bevelThickness: 0.06, bevelSize: 0.06,
      bevelSegments: 2, curveSegments: 8 });
    g.rotateX(-Math.PI / 2);
    return smoothNormals(g, 32);
  };
  const PEDAL_Y = FLOOR_Y + 0.75, PEDAL_Z = -5.6;
  add(brass, paddleGeo(), [-3.4, PEDAL_Y, PEDAL_Z]);
  add(brass, paddleGeo(), [0, PEDAL_Y, PEDAL_Z]);

  // candle sconces: rosette on the veneer, an S-curved arm, a drip pan with a finial, a wax candle and a wick
  const flames = [];
  const candleLights = [];
  // A candle's light: a scene PointLight by default, so it warms the host's keys (see Lifetime at the top); with
  // ctx.options.hostLight === false an Object3D carrying a point light's place, colour, intensity, distance and decay,
  // which candleShading draws on the case alone.
  const hostLight = ctx.options?.hostLight !== false;
  const candleLight = (color, intensity, distance, decay) => Object.assign(new THREE.Object3D(),
    { isCandleLight: true, color: new THREE.Color(color), intensity, distance, decay });
  const flameGeo = (() => {
    const g = lathe([[0, 0], [0.1, 0.04], [0.19, 0.22], [0.2, 0.46], [0.14, 0.78], [0.06, 1.08], [0, 1.3]], 16);
    const pa = g.attributes.position.array, col = new Float32Array(pa.length);
    for (let i = 0; i < pa.length; i += 3) {
      const y = Math.max(0, Math.min(1, pa[i + 1] / 1.3));
      const core = Math.exp(-((y - 0.32) / 0.22) * ((y - 0.32) / 0.22));
      col[i] = 0.25 + 0.75 * Math.min(1, y * 4) * (1 - 0.35 * y);
      col[i + 1] = 0.3 + 0.55 * core + 0.1 * (1 - y);
      col[i + 2] = 0.55 * (1 - Math.min(1, y * 3.5)) + 0.18 * core;
      const fade = Math.max(0, Math.min(1, (1 - y) * 3.2));
      col[i] *= fade; col[i + 1] *= fade; col[i + 2] *= fade;
    }
    g.setAttribute("color", new THREE.BufferAttribute(col, 3));
    return keep(g);
  })();
  const waxParts = [];
  for (const s of [-1, 1]) {
    const sx = s * 23.6, cupX = s * 24.6, cupY = 9.35, cupZ = -4.1;
    add(brass, lathe([[0, 0], [0.85, 0], [0.9, 0.08], [0.78, 0.18], [0.5, 0.22], [0.3, 0.35], [0.18, 0.42], [0, 0.44]], 24),
      [sx, 12.6, -5.02], null, [Math.PI / 2, 0, 0]);
    const curve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(sx, 12.6, -4.7), new THREE.Vector3(sx + s * 0.35, 12.0, -4.15),
      new THREE.Vector3(sx + s * 0.85, 10.5, -3.98), new THREE.Vector3(cupX, 9.4, cupZ)]);
    add(brass, new THREE.TubeGeometry(curve, 28, 0.11, 8, false), [0, 0, 0]);
    add(brass, lathe([[0, -0.75], [0.12, -0.66], [0.22, -0.42], [0.12, -0.16], [0.64, 0], [0.68, 0.08], [0.6, 0.14],
      [0.34, 0.16], [0.34, 0.55], [0.4, 0.6], [0.36, 0.66], [0, 0.64]], 24), [cupX, cupY, cupZ]);
    waxParts.push({ geo: new THREE.CylinderGeometry(0.3, 0.33, 4.0, 20, 1), pos: [cupX, cupY + 2.6, cupZ] });
    add(dark, new THREE.CylinderGeometry(0.03, 0.035, 0.32, 6), [cupX, cupY + 4.72, cupZ]);
    const flame = new THREE.Mesh(flameGeo, M.flame);
    flame.position.set(cupX, cupY + 4.66, cupZ);
    flame.renderOrder = 2;
    group.add(flame);
    flames.push({ mesh: flame, phase: s > 0 ? 1.3 : 4.1 });
    const light = hostLight ? new THREE.PointLight(0xffb070, 0, 42, 1.6) : candleLight(0xffb070, 0, 42, 1.6);
    light.position.set(cupX - s * 0.6, cupY + 5.4, cupZ + 1.0);
    group.add(light);
    candleLights.push(light);
  }

  // metronome on the lid: a four-sided walnut pyramid, a dark slot, a brass pendulum that swings while you play
  const MET = { x: -21, z: -12, base: 21.0, h: 6.2, rb: 1.9, rt: 0.42 };
  const apo = (h) => (MET.rb + (MET.rt - MET.rb) * h / MET.h) * Math.SQRT1_2;
  const faceTilt = Math.atan((apo(0) - apo(MET.h)) / MET.h);
  add(wood, new THREE.CylinderGeometry(MET.rt, MET.rb, MET.h, 4, 1), [MET.x, MET.base + MET.h / 2, MET.z], "y", [0, Math.PI / 4, 0]);
  add(dark, roundBox(0.55, 4.2, 0.08, 0.03), [MET.x, MET.base + 3.3, MET.z + apo(3.3) + 0.03], null, [-faceTilt, 0, 0]);
  const pendulumGeo = merge([
    { geo: new THREE.BoxGeometry(0.07, 4.6, 0.07), pos: [0, 2.3, 0] },
    { geo: roundBox(0.5, 0.34, 0.2, 0.06), pos: [0, 3.2, 0] },
  ]);
  const pendulum = new THREE.Group();
  pendulum.position.set(MET.x, MET.base + 0.9, MET.z + apo(0.9) + 0.14);
  pendulum.rotation.set(-faceTilt, 0, 0);
  pendulum.add(new THREE.Mesh(pendulumGeo, M.brass));
  group.add(pendulum);

  // felt strip behind the key backs, and the wash of its light on the fallboard's lower face
  const felt = new THREE.Mesh(keep(new THREE.BoxGeometry(HOST_SPAN, 0.42, 0.22)), M.felt);
  felt.position.set(0, 0.2, -3.22);
  group.add(felt);
  const fallFrame = new THREE.Object3D();
  fallFrame.position.set(0, 2.35, -4.15);
  fallFrame.rotation.x = -FALL_TILT;
  fallFrame.updateMatrix();
  // The wash covers only the lower third of the fallboard (was 2.4 of its 4.45) and fades faster, so the coloured
  // wisps stay well under the fallboard's top edge and out of the 9:16 frame's note-bar zone.
  const WASH_H = 1.5;
  const washGeo = keep(new THREE.PlaneGeometry(HOST_SPAN, WASH_H, 1, 6));
  {
    const pa = washGeo.attributes.position.array, col = new Float32Array(pa.length);
    for (let i = 0; i < pa.length; i += 3) {
      // clamped: float32 positions put the top row a hair past 1, and pow(negative, x) is NaN (bloom spreads it over the frame)
      const f = Math.pow(Math.max(0, Math.min(1, 1 - (pa[i + 1] + WASH_H / 2) / WASH_H)), 2.2);
      col[i] = f; col[i + 1] = f; col[i + 2] = f;
    }
    washGeo.setAttribute("color", new THREE.BufferAttribute(col, 3));
  }
  const wash = new THREE.Mesh(washGeo, M.wash);
  wash.position.set(0, -2.2 + WASH_H / 2, 0.235).applyMatrix4(fallFrame.matrix);
  wash.rotation.x = -FALL_TILT;
  wash.renderOrder = 1;
  group.add(wash);

  // the book on the music shelf: leather cover, two bowed pages, our chord name on the right page
  const BOOK = { w: 18.2, h: 12.8, cvW: 1536, cvH: 1080, glowW: 768, glowH: 540 };
  const paperCanvas = document.createElement("canvas");
  paperCanvas.width = BOOK.cvW; paperCanvas.height = BOOK.cvH;
  const glowCanvas = document.createElement("canvas");
  glowCanvas.width = BOOK.glowW; glowCanvas.height = BOOK.glowH;
  const paperTex = canvasTex(paperCanvas, false);
  const glowTex = canvasTex(glowCanvas, false);
  M.paper = keep(new THREE.MeshPhysicalMaterial({ map: paperTex, roughness: 0.92, emissive: 0xffffff, emissiveMap: glowTex,
    emissiveIntensity: 0, side: THREE.DoubleSide }));
  const bookGroup = new THREE.Group();
  bookGroup.position.set(0, 5.12, -4.0);
  bookGroup.rotation.x = -LEAN;
  const pageGeo = keep(new THREE.PlaneGeometry(BOOK.w, BOOK.h, 36, 1));
  {
    const pa = pageGeo.attributes.position.array, hw = BOOK.w / 2;
    for (let i = 0; i < pa.length; i += 3) {
      const a = Math.min(1, Math.abs(pa[i]) / hw);
      pa[i + 2] = 0.26 * (1 - Math.pow(1 - a, 3));
    }
    pageGeo.computeVertexNormals();
  }
  const pages = new THREE.Mesh(pageGeo, M.paper);
  pages.position.set(0, BOOK.h / 2 + 0.2, 0.02);
  bookGroup.add(pages);
  const coverGeo = merge([{ geo: roundBox(BOOK.w + 0.6, BOOK.h + 0.4, 0.22, 0.08), pos: [0, BOOK.h / 2 + 0.2, -0.14] }]);
  bookGroup.add(new THREE.Mesh(coverGeo, M.leather));
  group.add(bookGroup);

  const FONT = '"Outfit", "Jost", "Raleway", "Segoe UI", system-ui, sans-serif';
  const PC_OF = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
  const inkColor = new THREE.Color();
  function rootPc(name) {
    const m = /^([A-G])([#♯b♭]?)/.exec(name || "");
    if (!m) return -1;
    return (PC_OF[m[1]] + (m[2] === "#" || m[2] === "♯" ? 1 : m[2] === "b" || m[2] === "♭" ? -1 : 0) + 12) % 12;
  }
  const toSrgb8 = (c) => Math.round(255 * Math.max(0, Math.min(1, c <= 0.0031308 ? 12.92 * c : 1.055 * Math.pow(c, 1 / 2.4) - 0.055)));
  const cssOf = (c, scale) => `rgb(${toSrgb8(c.r * scale)}, ${toSrgb8(c.g * scale)}, ${toSrgb8(c.b * scale)})`;
  function staves(g2, x, y, w, count, gap, step) {
    g2.strokeStyle = "rgba(70, 48, 30, 0.5)";
    g2.lineWidth = 2;
    for (let s = 0; s < count; s++) {
      const top = y + s * step;
      for (let l = 0; l < 5; l++) { g2.beginPath(); g2.moveTo(x, top + l * gap); g2.lineTo(x + w, top + l * gap); g2.stroke(); }
      g2.beginPath(); g2.moveTo(x, top); g2.lineTo(x, top + 4 * gap); g2.moveTo(x + w, top); g2.lineTo(x + w, top + 4 * gap); g2.stroke();
      for (let b = 1; b < 4; b++) { g2.beginPath(); g2.moveTo(x + w * b / 4, top); g2.lineTo(x + w * b / 4, top + 4 * gap); g2.stroke(); }
    }
  }
  function fitFont(g2, text, weight, size, maxW) {
    g2.font = `${weight} ${size}px ${FONT}`;
    const w = g2.measureText(text).width;
    if (w > maxW) { size = Math.floor(size * maxW / w); g2.font = `${weight} ${size}px ${FONT}`; }
    return size;
  }
  const shown = { name: null, nns: null, key: null };
  const BOOK_GLOW_MAX = 0.8, BOOK_GLOW_LUMA = 0.45;
  let glowCap = BOOK_GLOW_MAX;
  function drawBook(chord) {
    const W = BOOK.cvW, H = BOOK.cvH, g2 = paperCanvas.getContext("2d");
    const paper = g2.createLinearGradient(0, 0, W, 0);
    paper.addColorStop(0, "#dccaa6"); paper.addColorStop(0.08, "#efe3c8"); paper.addColorStop(0.46, "#ece0c4");
    paper.addColorStop(0.5, "#c9b58e"); paper.addColorStop(0.54, "#ece0c4"); paper.addColorStop(0.92, "#efe3c8");
    paper.addColorStop(1, "#dccaa6");
    g2.fillStyle = paper; g2.fillRect(0, 0, W, H);
    // left page: a quiet score
    staves(g2, 90, 150, W / 2 - 180, 6, 17, 145);
    // right page: staves under the chord
    staves(g2, W / 2 + 90, 610, W / 2 - 180, 3, 17, 145);
    const gc = glowCanvas.getContext("2d");
    gc.fillStyle = "#000"; gc.fillRect(0, 0, BOOK.glowW, BOOK.glowH);
    if (chord && chord.name) {
      const pc = rootPc(chord.name);
      if (pc >= 0) ctx.noteColor(60 + pc, 110, inkColor); else inkColor.setRGB(0.3, 0.2, 0.12);
      const peak = Math.max(inkColor.r, inkColor.g, inkColor.b, 1e-3);
      // glow cap: emissive at most 0.8 per channel, and its luminance at most 0.45 so ink + lit paper stays under bloom
      const inkLuma = (0.2126 * inkColor.r + 0.7152 * inkColor.g + 0.0722 * inkColor.b) / peak;
      glowCap = Math.min(BOOK_GLOW_MAX, BOOK_GLOW_LUMA / Math.max(inkLuma, 1e-3));
      const cxp = W * 0.75, maxW = W / 2 - 200;
      g2.textAlign = "center"; g2.textBaseline = "alphabetic";
      const size = fitFont(g2, chord.name, 600, 250, maxW);
      g2.fillStyle = cssOf(inkColor, 0.62 / peak);
      g2.fillText(chord.name, cxp, 360);
      const sub = [chord.nns, chord.key ? `in ${chord.key}` : ""].filter(Boolean).join("   ·   ");
      if (sub) {
        fitFont(g2, sub, 400, 64, maxW);
        g2.fillStyle = "rgba(70, 48, 30, 0.85)";
        g2.fillText(sub, cxp, 480);
      }
      g2.strokeStyle = "rgba(70, 48, 30, 0.35)"; g2.lineWidth = 2;
      g2.beginPath(); g2.moveTo(cxp - 180, 525); g2.lineTo(cxp + 180, 525); g2.stroke();
      // the glow map: the same letters, full colour on black, at half resolution
      const k = BOOK.glowW / W;
      gc.textAlign = "center"; gc.textBaseline = "alphabetic";
      gc.font = `600 ${Math.round(size * k)}px ${FONT}`;
      gc.fillStyle = cssOf(inkColor, 1 / peak);
      gc.fillText(chord.name, cxp * k, 360 * k);
    }
    paperTex.needsUpdate = true;
    glowTex.needsUpdate = true;
  }
  drawBook(null);
  if (document.fonts && document.fonts.ready) {
    document.fonts.ready.then(() => { if (!disposed) drawBook(shown.name ? { ...shown } : null); });
  }

  // ------------------------------------------------------------ candle shading --
  // Without hostLight the candles light the case's own lit materials: three's point light (r186 getPointLightInfo), added
  // right after the scene's point lights, where the two PointLights were. A degenerate triangle drawn first each frame
  // moves the candles into the camera's view space (as three does for a PointLight's uniforms) before any lit part draws.
  if (!hostLight) {
    const candleU = { uCandlePos: { value: [new THREE.Vector3(), new THREE.Vector3()] },
      uCandleColor: { value: [new THREE.Color(0, 0, 0), new THREE.Color(0, 0, 0)] }, uCandleFall: { value: new THREE.Vector2(42, 1.6) } };
    const CANDLE_GLSL = `#if defined( RE_Direct )
for ( int i = 0; i < 2; i ++ ) {
	IncidentLight candleDirect;
	vec3 candleVector = uCandlePos[ i ] - geometryPosition;
	candleDirect.direction = normalize( candleVector );
	float candleDistance = length( candleVector );
	candleDirect.color = uCandleColor[ i ];
	candleDirect.color *= getDistanceAttenuation( candleDistance, uCandleFall.x, uCandleFall.y );
	candleDirect.visible = ( candleDirect.color != vec3( 0.0 ) );
	RE_Direct( candleDirect, geometryPosition, geometryNormal, geometryViewDir, geometryClearcoatNormal, material, reflectedLight );
}
#endif
`;
    const beginChunk = THREE.ShaderChunk.lights_fragment_begin;
    const spotAt = beginChunk.indexOf("#if ( NUM_SPOT_LIGHTS > 0 )");
    const CANDLE_BEGIN = spotAt >= 0 ? beginChunk.slice(0, spotAt) + CANDLE_GLSL + beginChunk.slice(spotAt) : beginChunk + CANDLE_GLSL;
    const candleShading = (sh) => {
      Object.assign(sh.uniforms, candleU);
      sh.fragmentShader = "uniform vec3 uCandlePos[ 2 ];\nuniform vec3 uCandleColor[ 2 ];\nuniform vec2 uCandleFall;\n" +
        sh.fragmentShader.replace("#include <lights_fragment_begin>", CANDLE_BEGIN);
    };
    for (const k in M) {
      if (!M[k] || !M[k].isMeshStandardMaterial) continue;
      M[k].onBeforeCompile = candleShading;
      M[k].customProgramCacheKey = () => "upright-candles";
    }
    const hookGeo = keep(new THREE.BufferGeometry());
    hookGeo.setAttribute("position", new THREE.BufferAttribute(new Float32Array(9), 3));
    const frameHook = new THREE.Mesh(hookGeo, M.dark);
    frameHook.name = "frame hook";
    frameHook.frustumCulled = false;
    frameHook.renderOrder = -1e6;
    frameHook.onBeforeRender = (renderer, scene, camera) => {
      const view = camera.matrixWorldInverse;
      for (let i = 0; i < 2; i++) {
        const l = candleLights[i];
        candleU.uCandlePos.value[i].setFromMatrixPosition(l.matrixWorld).applyMatrix4(view);
        candleU.uCandleColor.value[i].copy(l.color).multiplyScalar(l.intensity);
      }
      candleU.uCandleFall.value.set(candleLights[0].distance, candleLights[0].decay);
    };
    group.add(frameHook);
  }

  // ------------------------------------------------------------ merged meshes --
  const woodMesh = new THREE.Mesh(merge(wood), M.case);
  const veneerMesh = new THREE.Mesh(merge(veneer), M.veneer);
  const darkMesh = new THREE.Mesh(merge(dark), M.dark);
  const brassMesh = new THREE.Mesh(merge(brass), M.brass);
  const waxMesh = new THREE.Mesh(merge(waxParts), M.wax);
  group.add(woodMesh, veneerMesh, darkMesh, brassMesh, waxMesh);
  const sustainPivot = new THREE.Group();
  sustainPivot.position.set(3.4, PEDAL_Y, PEDAL_Z);
  sustainPivot.add(new THREE.Mesh(merge([{ geo: paddleGeo() }]), M.brass));
  group.add(sustainPivot);

  if (ctx.scene) ctx.scene.add(group);

  // ------------------------------------------------------------ reactive state --
  const level = new Float32Array(COUNT), strikeT = new Float64Array(COUNT).fill(-Infinity);
  const heldVel = new Float32Array(COUNT), heldT0 = new Float64Array(COUNT);
  const keyRGB = new Float32Array(COUNT * 3), texel = new Float32Array(COUNT), sigma = new Float32Array(COUNT);
  for (let k = 0; k < COUNT; k++) {
    const m = FIRST + k;
    texel[k] = ((keyX(m) - cx) / S + HOST_SPAN / 2) / HOST_SPAN * FELT_W - 0.5;
    sigma[k] = (isBlack(m) ? 0.32 : 0.46) / HOST_SPAN * FELT_W;
  }
  const acc = new Float32Array(FELT_W * 3);
  const tmp = new THREE.Color(), warm = new THREE.Color(1.0, 0.6, 0.26), flameCol = new THREE.Color(), tint = new THREE.Color();
  // the candles' light is warm but less saturated than the flame, so the walnut doesn't go orange-red under it
  const lightWarm = new THREE.Color(1.0, 0.74, 0.46);
  const isPortrait = (f) => !!f && (f.id === "9:16" || (f.w > 0 && f.h > f.w));
  let portrait = isPortrait(ctx.framing);
  let flameE = 0, playE = 0, sheetPulse = 0, tintR = 0, tintG = 0, tintB = 0, tintW = 0;
  let pedalDepth = 0, swingPhase = 0, swingAmp = 0, feltLit = false, active = true, disposed = false, now = 0;

  const velOf = (v) => Math.max(0, Math.min(1, v > 1.001 ? v / 127 : v || 0));
  function strike(k, v) {
    ctx.noteColor(FIRST + k, v * 127, tmp);
    keyRGB[k * 3] = tmp.r; keyRGB[k * 3 + 1] = tmp.g; keyRGB[k * 3 + 2] = tmp.b;
    level[k] = Math.max(level[k], v * 1.25);
    flameE = Math.min(2.2, flameE + v * v * 0.5);
    playE = Math.min(1.6, playE + v * 0.3);
    tintR += tmp.r * v; tintG += tmp.g * v; tintB += tmp.b * v; tintW += v;
    sheetPulse = Math.max(sheetPulse, v);
  }
  function markHeld(st, m) {
    const k = m - FIRST;
    if (k < 0 || k >= COUNT || !st) return;
    const v = velOf(st.vel);
    heldVel[k] = Math.max(v, 1e-3);
    const t0 = st.t0 !== undefined ? st.t0 : now;
    heldT0[k] = t0;
    if (t0 > strikeT[k] + 1e-6) { strikeT[k] = t0; strike(k, v); }
  }

  function update(dt, t, state) {
    if (!active || disposed) return;
    dt = Math.max(0, Math.min(dt || 0, 0.1));
    now = t;
    const pressed = state && state.pressed, notes = state && state.notes, pedal = !!(state && state.pedal);
    const chord = state && state.chord;

    // strikes: recent notes and fresh presses (each key remembers the last strike it has seen)
    if (notes) {
      for (let i = 0; i < notes.length; i++) {
        const n = notes[i], k = n.midi - FIRST;
        if (k < 0 || k >= COUNT || !(n.t > strikeT[k] + 1e-6) || n.t > t + 1e-3) continue;
        strikeT[k] = n.t;
        strike(k, velOf(n.vel));
      }
    }
    heldVel.fill(0);
    if (pressed) pressed.forEach(markHeld);

    // felt light per key: the strike peak falls to a held glow; released keys fade (slowly under the pedal)
    let any = false;
    const fadeUp = Math.exp(-dt / 0.2), fadePedal = Math.exp(-dt / 1.3);
    for (let k = 0; k < COUNT; k++) {
      const v = heldVel[k];
      const target = v > 0 ? v * (0.3 + 0.95 * Math.exp(-(t - heldT0[k]) / 0.2)) : 0;
      const L = level[k] * (v <= 0 && pedal ? fadePedal : fadeUp);  // strike() sets the flash of a tap already released
      level[k] = Math.max(target, L);
      if (level[k] > 0.004) any = true; else level[k] = 0;
    }
    if (any || feltLit) {
      acc.fill(0);
      if (any) {
        for (let k = 0; k < COUNT; k++) {
          const L = level[k];
          if (L <= 0) continue;
          const c = texel[k], sg = sigma[k], r0 = Math.max(0, Math.ceil(c - sg * 3)), r1 = Math.min(FELT_W - 1, Math.floor(c + sg * 3));
          const pr = keyRGB[k * 3] * L, pg = keyRGB[k * 3 + 1] * L, pb = keyRGB[k * 3 + 2] * L;
          for (let i = r0; i <= r1; i++) {
            const d = (i - c) / sg, w = Math.exp(-0.5 * d * d);
            acc[i * 3] += pr * w; acc[i * 3 + 1] += pg * w; acc[i * 3 + 2] += pb * w;
          }
        }
      }
      for (let i = 0; i < FELT_W; i++) {
        feltData[i * 4] = Math.min(255, acc[i * 3] * 255);
        feltData[i * 4 + 1] = Math.min(255, acc[i * 3 + 1] * 255);
        feltData[i * 4 + 2] = Math.min(255, acc[i * 3 + 2] * 255);
        feltData[i * 4 + 3] = 255;
      }
      feltTex.needsUpdate = true;
      feltLit = any;
    }

    // candles: energy from strikes, colour from what was just played
    flameE *= Math.exp(-dt / 0.55);
    playE *= Math.exp(-dt / 3.0);
    const tintFade = Math.exp(-dt / 0.9);
    tintR *= tintFade; tintG *= tintFade; tintB *= tintFade; tintW *= tintFade;
    const E = Math.min(1.6, flameE);
    let mixAmt = 0;
    if (tintW > 1e-3) {
      tint.setRGB(tintR / tintW, tintG / tintW, tintB / tintW);
      const pk = Math.max(tint.r, tint.g, tint.b, 1e-3);
      tint.multiplyScalar(1 / pk);
      mixAmt = Math.min(0.7, E * 0.55);
    } else tint.copy(warm);
    // portrait (9:16 player): the note bars rise over the upper panel, so the flames bloom half as hard there
    const flameGain = portrait ? 0.5 : 1, lightCap = portrait ? 60 : Infinity;
    for (let i = 0; i < flames.length; i++) {
      const f = flames[i], ph = f.phase;
      const flick = 1 + 0.06 * Math.sin(t * 13.1 + ph) + 0.04 * Math.sin(t * 23.7 + ph * 2) + 0.03 * Math.sin(t * 7.3 + ph * 3);
      f.mesh.scale.set(1 + 0.12 * E, (1 + 0.5 * E) * (0.96 + 0.08 * flick), 1 + 0.12 * E);
      f.mesh.rotation.z = 0.05 * Math.sin(t * 3.1 + ph) + 0.05 * E * Math.sin(t * 17.0 + ph);
      if (i === 0) {
        flameCol.copy(warm).lerp(tint, mixAmt).multiplyScalar((0.5 + 2.0 * E) * flick * flameGain);
        M.flame.color.copy(flameCol);
      }
      const light = candleLights[i];
      light.color.copy(lightWarm).lerp(tint, mixAmt * 0.8);
      light.intensity = Math.min(lightCap, (16 + 70 * E) * flick);
    }
    M.wax.emissiveIntensity = 0.03 + 0.05 * E;

    // the book: redraw on a new chord; its letters glow on strikes
    if (chord && chord.name) {
      if (chord.name !== shown.name || chord.nns !== shown.nns || chord.key !== shown.key) {
        shown.name = chord.name; shown.nns = chord.nns; shown.key = chord.key;
        drawBook(chord);
      }
    } else if (shown.name !== null) {
      shown.name = null; shown.nns = null; shown.key = null;
      drawBook(null);
    }
    sheetPulse *= Math.exp(-dt / 0.5);
    M.paper.emissiveIntensity = shown.name ? glowCap * sheetPulse * sheetPulse : 0;

    // sustain pedal
    pedalDepth += ((pedal ? 1 : 0) - pedalDepth) * (1 - Math.exp(-dt / 0.045));
    sustainPivot.rotation.x = pedalDepth * 0.1;

    // metronome: swings while you play, settles a few seconds after
    swingAmp += (Math.min(1, playE) - swingAmp) * (1 - Math.exp(-dt / (playE > swingAmp ? 0.6 : 1.8)));
    swingPhase = (swingPhase + dt * TAU * 0.7) % TAU;   // 84 beats a minute: one tick at each end of the swing
    pendulum.rotation.z = 0.42 * swingAmp * Math.sin(swingPhase);
  }

  function setActive(on) {
    active = !!on;
    group.visible = active;
    if (!active) {
      level.fill(0); flameE = 0; playE = 0; sheetPulse = 0; tintW = 0; swingAmp = 0;
      feltData.fill(0); feltTex.needsUpdate = true; feltLit = false;
      for (const l of candleLights) l.intensity = 0;
    }
  }
  // world-space instrument: only the candles' bloom depends on the framing (halved in portrait)
  function resize(framing) { if (framing) portrait = isPortrait(framing); }
  function dispose() {
    if (disposed) return;
    disposed = true;
    if (group.parent) group.parent.remove(group);
    for (const d of disposables) if (d && d.dispose) d.dispose();
    group.traverse((o) => { if (o.isPointLight && o.dispose) o.dispose(); });
  }

  // world position of a point in case space (for the view hints)
  const W = (x, y, z) => [cx + x * S, y * S, z * S];
  return {
    group, update, resize, setActive, dispose,
    // Hints for the host (all optional):
    //   keyStyle  aged ivory and ebony, a thin ivory cap and front lip
    //   stage     the floor sits below the host's -2.3; the host's own lacquer keybed, cheeks, back rail and felt should
    //             hide while this is active (they poke through the fallboard and cheek arms); nothing of this case sits
    //             in front of z -3.5 above y 1.12, so the host's trail plane (TRAIL_Z -3.42) stays clear
    //   views     a hero three-quarter and a close-up (candle, book, felt), world coordinates
    keyStyle: KEY_STYLE,
    stage: { floorY: FLOOR_Y * S, hideHostBody: true, clearInFrontOfZ: -3.5 * S },
    views: {
      hero: { from: W(68, 15, 101), target: W(-2, -4.5, -8), fov: 34 },
      close: { from: W(23, 9, 21), target: W(11.5, 6.5, -4), fov: 38 },
    },
    info: { parts: { wood: wood.length, veneer: veneer.length, dark: dark.length, brass: brass.length },
      buildMs: Math.round(performance.now() - T_BUILD) },
  };
}
