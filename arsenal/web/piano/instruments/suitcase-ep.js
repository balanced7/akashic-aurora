// Suitcase EP: arsenal/web/piano/instruments/suitcase-ep.js  (ES module, a piano instrument)
//
// A 1970s suitcase-style electric piano built around the host's key row. It has 73 keys (E1-E7, MIDI 28-100), a black
// tolex top unit with rounded corners, chrome corner balls and trim, a blank brushed-silver name rail, and a flat
// smoked-acrylic harp cover. Under the cover: 73 steel tines, brass tonebars, black pickups and felt dampers. The unit
// sits on a tolex speaker base with a silver grille. No brand text anywhere.
//
// Reactive:
//   - a struck tine glows in the note's colour (ctx.noteColor), with a velocity flash on top of a sustain that decays
//     slowly while held, a little faster under the pedal, and quickly on release. It vibrates, and a soft pool of the
//     same colour lights the harp plate under it. A soft vertical haze of that colour stands in the smoked case behind
//     the tine tip, so the glow still reads from the page's low camera.
//   - dampers lift off their tines while a key is held or the pedal is down (the top octave has none, as on the real
//     instrument).
//   - the smoked cover takes a faint wash of the sounding colours, below the bloom threshold.
//   - a red jewel lamp on the left cheek idles dim (below bloom) and flashes with velocity peaks.
// Nothing else is emissive: the body never glows.
//
// Contract: default export {id, name, create(ctx)} -> {group, update(dt, t, state), resize(framing), setActive(on),
// dispose()} plus hints {keyStyle, stageHints, views, info}. No imports: THREE and everything else come through ctx.
// Keys stay host-owned. The body wraps keys 28-100 only when the host says it can hide the rest
// (ctx.supportsKeyRange === true, and keyStyle.range names the keys to show). Otherwise it widens to the host's whole
// row so no key hangs outside the cabinet.
//
// Proportions (spec: scratchpad/instruments/spec.md section 2.3; 1 world unit = one white-key pitch, about 23.5 mm):
// the 73-key span is 43 u (1010 mm), the cheeks 3.8 u, so the cabinet is 51 u (about 1200 mm) wide and 20 u (about
// 480 mm) deep. The top unit is about 6 u tall; the speaker base is 15 u (about 350 mm) with 0.4 u feet.
// Dimensions for the suitcase come from a single forum post [U]; the tine and tonebar layout is stylised.

const TAU = Math.PI * 2;

const DEF = {
  id: "suitcase-ep",
  name: "Suitcase Electric Piano",
  keySpan: { first: 28, last: 100 },  // E1..E7, 73 keys; the host hides (or dims) keys outside it
  keyStyle: { whiteColor: 0xeeeadf, blackColor: 0x0c0c0e, capHeight: 0.8, frontLip: 0.05 },

  create(ctx) {
    const { THREE, keyX, isBlack, noteColor } = ctx;
    const scene = ctx.scene;
    const hostFirst = ctx.KEY?.first ?? 21, hostLast = ctx.KEY?.last ?? 108;
    const S = { keyFront: 3.1, keyBack: -3.1, whiteTop: 0, whiteBottom: -0.8, blackTop: 0.52, railY: 1.12, trailZ: -3.42,
                floorY: -2.3, ...(ctx.span || {}) };
    if (!Number.isFinite(S.railY)) S.railY = ctx.RAIL_Y ?? 1.12;
    const want = ctx.options?.range || DEF.keySpan;
    const ranged = ctx.supportsKeyRange !== false && !ctx.options?.fullSpan;  // false: widen the body to the host's row
    const first = Math.max(hostFirst, ranged ? want.first : hostFirst);
    const last = Math.min(hostLast, ranged ? want.last : hostLast);
    const N = last - first + 1;
    const ND = Math.max(0, N - 12);  // notes with dampers: all but the top octave
    const edgeL = keyX(isBlack(first) ? first - 1 : first) - 0.5;
    const edgeR = keyX(isBlack(last) ? last + 1 : last) + 0.5;

    // ------------------------------------------------------------ dimensions --
    const GAP = 0.14, CHEEK = 3.8;
    const inL = edgeL - GAP, inR = edgeR + GAP;           // inner faces of the cheeks
    const X0 = inL - CHEEK, X1 = inR + CHEEK;             // outer faces
    const CX = (X0 + X1) / 2;
    const Z_FRONT = S.keyFront - 0.3;                     // the keys overhang the front rail
    const Z_BACK = -17.4;
    const Y_TOP = 1.48;                                   // one flat top: cheeks, back wall and harp cover
    // The real top unit runs about 4.6 u below the key tops and stands on a 15 u speaker base. The host floor
    // (span.floorY, -2.3 on /piano) is higher than that, so by default the unit rests on the floor on short feet and the
    // base is left out. A host whose floor sits at or below the base's feet (or options.withBase) gets the full suitcase.
    const FEET = 0.14, BASE_H = 15.0;
    const withBase = ctx.options?.withBase === true || S.floorY <= -4.6 - 0.18 - BASE_H - 0.42;
    const Y_BOT = withBase ? -4.6 : Math.max(-4.6, S.floorY + FEET);
    // The name rail stays low (0.82, just over the black keys' 0.52) and the harp sits high under the cover, so a camera
    // at the page's 17-22 degrees sees the tine tips and the pools on the plate over the rail (receipt r1: with the rail
    // at 1.05 and the plate at -0.6 the page and player views hid almost all of the glow).
    const RAIL = { z0: S.keyBack - 0.1, z1: -4.45, top: Math.min(S.railY - 0.3, 0.82), bottom: -1.0 };
    const HARP = { z0: RAIL.z1, z1: -16.5, plate: -0.3 };
    const TINE_Y = 0.6, TIP_Z = -6.45, PICKUP_Z = -6.0, TONEBAR_Y = 1.02;
    const BASE = { x0: X0 + 0.3, x1: X1 - 0.3, z0: Z_BACK + 0.3, z1: Z_FRONT - 0.3, y1: Y_BOT - 0.18 };
    BASE.y0 = BASE.y1 - BASE_H;
    const FLOOR_Y = withBase ? BASE.y0 - 0.42 : Y_BOT - FEET;

    // ------------------------------------------------------------- utilities --
    const disposables = [];
    const keep = (x) => (disposables.push(x), x);
    let seed = 0x5eed;
    const rand = () => {  // mulberry32: the procedural textures are the same on every load
      seed |= 0; seed = (seed + 0x6d2b79f5) | 0;
      let r = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      r = (r + Math.imul(r ^ (r >>> 7), 61 | r)) ^ r;
      return ((r ^ (r >>> 14)) >>> 0) / 4294967296;
    };
    function canvas(w, h) {
      if (typeof document !== "undefined") { const c = document.createElement("canvas"); c.width = w; c.height = h; return c; }
      return new OffscreenCanvas(w, h);
    }
    function texture(c, { srgb = true, repeat = null } = {}) {
      const t = keep(new THREE.CanvasTexture(c));
      if (srgb) t.colorSpace = THREE.SRGBColorSpace;
      if (repeat) { t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(repeat[0], repeat[1]); }
      t.anisotropy = 4;
      return t;
    }
    function roundRect(w, h, r, path = new THREE.Shape()) {
      const hw = w / 2, hh = h / 2;
      r = Math.max(0.001, Math.min(r, hw - 0.001, hh - 0.001));
      path.moveTo(-hw + r, -hh);
      path.lineTo(hw - r, -hh);
      path.absarc(hw - r, -hh + r, r, -Math.PI / 2, 0, false);
      path.lineTo(hw, hh - r);
      path.absarc(hw - r, hh - r, r, 0, Math.PI / 2, false);
      path.lineTo(-hw + r, hh);
      path.absarc(-hw + r, hh - r, r, Math.PI / 2, Math.PI, false);
      path.lineTo(-hw, -hh + r);
      path.absarc(-hw + r, -hh + r, r, Math.PI, Math.PI * 1.5, false);
      return path;
    }
    // ExtrudeGeometry gives flat per-face normals; average them across edges softer than the crease angle, so rounded
    // corners and bevels shade smoothly while box edges stay crisp.
    function creased(g, deg = 40) {
      const pos = g.attributes.position.array, tris = (pos.length / 9) | 0;
      const fn = new Float32Array(tris * 3);
      for (let f = 0; f < tris; f++) {
        const a = f * 9;
        const ux = pos[a + 3] - pos[a], uy = pos[a + 4] - pos[a + 1], uz = pos[a + 5] - pos[a + 2];
        const vx = pos[a + 6] - pos[a], vy = pos[a + 7] - pos[a + 1], vz = pos[a + 8] - pos[a + 2];
        let nx = uy * vz - uz * vy, ny = uz * vx - ux * vz, nz = ux * vy - uy * vx;
        const l = Math.hypot(nx, ny, nz) || 1;
        fn[f * 3] = nx / l; fn[f * 3 + 1] = ny / l; fn[f * 3 + 2] = nz / l;
      }
      const buckets = new Map();
      const keyOf = (i) => `${Math.round(pos[i] * 1000)},${Math.round(pos[i + 1] * 1000)},${Math.round(pos[i + 2] * 1000)}`;
      for (let v = 0; v < tris * 3; v++) {
        const k = keyOf(v * 3);
        let b = buckets.get(k);
        if (!b) buckets.set(k, (b = []));
        b.push((v / 3) | 0);
      }
      const out = new Float32Array(tris * 9), cos = Math.cos(deg * Math.PI / 180);
      for (let v = 0; v < tris * 3; v++) {
        const f = (v / 3) | 0, b = buckets.get(keyOf(v * 3));
        let nx = 0, ny = 0, nz = 0;
        for (const o of b) {
          const d = fn[f * 3] * fn[o * 3] + fn[f * 3 + 1] * fn[o * 3 + 1] + fn[f * 3 + 2] * fn[o * 3 + 2];
          if (d > cos) { nx += fn[o * 3]; ny += fn[o * 3 + 1]; nz += fn[o * 3 + 2]; }
        }
        const l = Math.hypot(nx, ny, nz) || 1;
        out[v * 3] = nx / l; out[v * 3 + 1] = ny / l; out[v * 3 + 2] = nz / l;
      }
      g.setAttribute("normal", new THREE.BufferAttribute(out, 3));
      return g;
    }
    const EXTRUDE = (depth, b) => ({ depth: Math.max(0.001, depth), bevelEnabled: b > 0, bevelThickness: b, bevelSize: b,
                                     bevelSegments: 3, curveSegments: 6 });
    // A slab rounded in plan (corners r) with bevelled edges (b), extruded up the Y axis.
    function slabY(x0, x1, z0, z1, y0, y1, r, b) {
      const g = new THREE.ExtrudeGeometry(roundRect(x1 - x0 - 2 * b, z1 - z0 - 2 * b, r - b), EXTRUDE(y1 - y0 - 2 * b, b));
      g.rotateX(-Math.PI / 2);
      g.translate((x0 + x1) / 2, y0 + b, (z0 + z1) / 2);
      return creased(g);
    }
    // A slab whose side profile (Z-Y) is rounded (r), extruded along the X axis.
    function slabX(x0, x1, z0, z1, y0, y1, r, b) {
      const g = new THREE.ExtrudeGeometry(roundRect(z1 - z0 - 2 * b, y1 - y0 - 2 * b, r - b), EXTRUDE(x1 - x0 - 2 * b, b));
      g.rotateY(Math.PI / 2);
      g.translate(x0 + b, (y0 + y1) / 2, (z0 + z1) / 2);
      return creased(g);
    }
    const at = (g, x, y, z) => (g.translate(x, y, z), g);
    // Concatenate geometries into one (position, normal, uv), so each material is one draw call.
    function merge(list) {
      const parts = list.map((g) => { const n = g.index ? g.toNonIndexed() : g; if (n !== g) g.dispose(); return n; });
      let count = 0;
      for (const g of parts) count += g.attributes.position.count;
      const pos = new Float32Array(count * 3), nor = new Float32Array(count * 3), uv = new Float32Array(count * 2);
      let o = 0;
      for (const g of parts) {
        const c = g.attributes.position.count;
        pos.set(g.attributes.position.array, o * 3);
        nor.set(g.attributes.normal.array, o * 3);
        if (g.attributes.uv) uv.set(g.attributes.uv.array, o * 2);
        o += c;
        g.dispose();
      }
      const out = new THREE.BufferGeometry();
      out.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      out.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
      out.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
      out.computeBoundingSphere();
      return keep(out);
    }

    // -------------------------------------------------------------- textures --
    const tolexBump = (() => {  // pebbled vinyl
      const c = canvas(256, 256), g = c.getContext("2d");
      g.fillStyle = "#808080"; g.fillRect(0, 0, 256, 256);
      for (let i = 0; i < 2600; i++) {
        const x = rand() * 256, y = rand() * 256, r = 1.2 + rand() * 2.6, l = 110 + rand() * 90;
        const grad = g.createRadialGradient(x, y, 0, x, y, r);
        grad.addColorStop(0, `rgba(${l},${l},${l},0.9)`); grad.addColorStop(1, "rgba(128,128,128,0)");
        g.fillStyle = grad;
        for (const dx of [0, -256, 256]) for (const dy of [0, -256, 256]) { g.beginPath(); g.arc(x + dx, y + dy, r, 0, TAU); g.fill(); }
      }
      return texture(c, { srgb: false, repeat: [0.9, 0.9] });
    })();
    const brushed = (() => {  // brushed aluminium: fine streaks along the rail's length
      const c = canvas(512, 8), g = c.getContext("2d");
      for (let x = 0; x < 512; x++) {
        const l = 176 + rand() * 46 + (rand() < 0.04 ? 30 : 0);
        g.fillStyle = `rgb(${l},${l + 2},${l + 5})`; g.fillRect(x, 0, 1, 8);
      }
      return texture(c, { repeat: [0.35, 1] });
    })();
    const grilleTex = (() => {  // silver grille cloth: a basket weave with a little lurex sparkle
      const c = canvas(256, 256), g = c.getContext("2d");
      g.fillStyle = "#2c2e32"; g.fillRect(0, 0, 256, 256);
      for (let y = 0; y < 256; y += 4) for (let x = 0; x < 256; x += 4) {
        const over = ((x >> 2) + (y >> 2)) % 2 === 0, l = 150 + rand() * 50;
        g.fillStyle = `rgb(${l},${l + 3},${l + 8})`;
        if (over) g.fillRect(x, y + 0.6, 4, 2.8); else g.fillRect(x + 0.6, y, 2.8, 4);
      }
      for (let i = 0; i < 380; i++) { g.fillStyle = "rgba(255,255,255,0.85)"; g.fillRect((rand() * 256) | 0, (rand() * 256) | 0, 1, 1); }
      return texture(c, { repeat: [1, 1] });
    })();
    const coverTex = (() => {  // smoked acrylic: a clear centre, darker edges and one bright polished inset line
      const c = canvas(1024, 512), g = c.getContext("2d");
      g.fillStyle = "rgba(20,26,36,0.30)"; g.fillRect(0, 0, 1024, 512);
      const edge = (x0, y0, x1, y1) => {
        const grad = g.createLinearGradient(x0, y0, x1, y1);
        grad.addColorStop(0, "rgba(6,8,12,0.55)"); grad.addColorStop(1, "rgba(6,8,12,0)");
        g.fillStyle = grad;
        g.fillRect(Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0) || 1024, Math.abs(y1 - y0) || 512);
      };
      edge(0, 0, 0, 48); edge(0, 512, 0, 464); edge(0, 0, 36, 0); edge(1024, 0, 988, 0);
      g.strokeStyle = "rgba(210,220,235,0.42)"; g.lineWidth = 3; g.strokeRect(20, 22, 984, 468);
      g.strokeStyle = "rgba(210,220,235,0.12)"; g.lineWidth = 1; g.strokeRect(27, 30, 970, 452);
      return texture(c);
    })();
    const poolTex = (() => {
      const c = canvas(128, 128), g = c.getContext("2d");
      const grad = g.createRadialGradient(64, 64, 0, 64, 64, 64);
      grad.addColorStop(0, "rgba(255,255,255,1)"); grad.addColorStop(0.35, "rgba(255,255,255,0.45)"); grad.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = grad; g.fillRect(0, 0, 128, 128);
      return texture(c);
    })();

    // ------------------------------------------------------------- materials --
    // Environment-free PBR: the host lights (hemisphere, key, rim, note lights) are all these see. Clearcoat and sheen
    // carry the highlights, since there is no environment for metals to reflect.
    const M = {
      tolex: new THREE.MeshPhysicalMaterial({ color: 0x0e0e10, roughness: 0.74, bumpMap: tolexBump, bumpScale: 1.4,
        sheen: 0.7, sheenRoughness: 0.5, sheenColor: new THREE.Color(0x4c4f58), clearcoat: 0.12, clearcoatRoughness: 0.55 }),
      chrome: new THREE.MeshPhysicalMaterial({ color: 0xdfe3e8, metalness: 0.5, roughness: 0.22, clearcoat: 1, clearcoatRoughness: 0.12 }),
      rail: new THREE.MeshPhysicalMaterial({ color: 0xffffff, map: brushed, metalness: 0.45, roughness: 0.32, clearcoat: 0.3, clearcoatRoughness: 0.5 }),
      plate: new THREE.MeshPhysicalMaterial({ color: 0x15161a, metalness: 0.3, roughness: 0.62 }),  // no clearcoat: a key-light peak there blooms
      brass: new THREE.MeshPhysicalMaterial({ color: 0xe0b45e, metalness: 0.25, roughness: 0.38 }),
      pickup: new THREE.MeshPhysicalMaterial({ color: 0x121214, roughness: 0.4, clearcoat: 0.6, clearcoatRoughness: 0.2 }),
      felt: new THREE.MeshStandardMaterial({ color: 0x4a0a16, roughness: 1 }),
      black: new THREE.MeshPhysicalMaterial({ color: 0x0a0a0b, roughness: 0.32, clearcoat: 0.8, clearcoatRoughness: 0.15 }),
      lamp: new THREE.MeshStandardMaterial({ color: 0x2a0503, emissive: new THREE.Color(1, 0.16, 0.05), emissiveIntensity: 0.35, roughness: 0.2 }),
      grille: new THREE.MeshPhysicalMaterial({ color: 0xffffff, map: grilleTex, roughness: 0.85, sheen: 0.8,
        sheenRoughness: 0.4, sheenColor: new THREE.Color(0x9aa0a8) }),
      cover: new THREE.MeshPhysicalMaterial({ color: 0xffffff, map: coverTex, transparent: true, depthWrite: false,
        // not a mirror: a near-mirror clearcoat turns the key light into a bloom blob across the cover (receipt r1 hero)
        // (r2: still a blob at 0.24; a satin coat keeps the key light's peak under the bloom threshold)
        roughness: 0.45, clearcoat: 0.35, clearcoatRoughness: 0.45, emissive: new THREE.Color(0, 0, 0) }),
      glow: new THREE.MeshBasicMaterial({ color: 0xffffff, vertexColors: true, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending }),
      pool: new THREE.MeshBasicMaterial({ color: 0xffffff, map: poolTex, transparent: true, depthWrite: false,
        blending: THREE.AdditiveBlending }),
    };
    for (const m of Object.values(M)) keep(m);

    const group = new THREE.Group();
    group.name = "instrument:suitcase-ep";
    group.visible = false;
    const addMesh = (geo, mat, name) => { const m = new THREE.Mesh(geo, mat); m.name = name; group.add(m); return m; };

    // ------------------------------------------------------------------ body --
    const BR = 0.5, BB = 0.26;  // body edge radius and bevel
    const tolexParts = [
      slabY(X0 + 0.2, X1 - 0.2, Z_BACK, Z_FRONT - 0.2, Y_BOT, -1.25, 1.1, 0.3),        // top unit tub, under the keys
      slabX(X0, inL, Z_BACK, Z_FRONT, Y_BOT, Y_TOP, BR + 0.3, BB),                       // left cheek
      slabX(inR, X1, Z_BACK, Z_FRONT, Y_BOT, Y_TOP, BR + 0.3, BB),                       // right cheek
      slabX(inL - 0.05, inR + 0.05, Z_BACK, HARP.z1, Y_BOT, Y_TOP, 0.3, 0.14),           // back wall
      slabX(inL - 0.05, inR + 0.05, S.keyFront - 2.4, Z_FRONT, Y_BOT, -1.22, 0.45, 0.16),// front rail under the keys
    ];
    if (withBase) { // the speaker base, and its front frame with the grille opening cut out
      tolexParts.push(slabY(BASE.x0, BASE.x1, BASE.z0, BASE.z1 - 0.3, BASE.y0, BASE.y1, 0.45, 0.3));
      const w = BASE.x1 - BASE.x0, h = BASE.y1 - BASE.y0, b = 0.1;
      const shape = roundRect(w - 2 * b, h - 2 * b, 0.35);
      const gw = w - 3.4, gh = h - 3.8, gy = -0.55;  // opening size and vertical offset (a deeper band on top)
      const hole = new THREE.Path();
      roundRect(gw, gh, 0.5, hole);
      const holePts = hole.getPoints(6).map((p) => new THREE.Vector2(p.x, p.y + gy));
      shape.holes.push(new THREE.Path(holePts));
      const g = new THREE.ExtrudeGeometry(shape, EXTRUDE(0.3 - 2 * b, b));
      g.translate((BASE.x0 + BASE.x1) / 2, (BASE.y0 + BASE.y1) / 2, BASE.z1 - 0.3 + b);
      tolexParts.push(creased(g));
      const grille = new THREE.PlaneGeometry(gw + 0.3, gh + 0.3);
      grilleTex.repeat.set((gw + 0.3) * 0.45, (gh + 0.3) * 0.45);
      at(grille, (BASE.x0 + BASE.x1) / 2, (BASE.y0 + BASE.y1) / 2 + gy, BASE.z1 - 0.2);
      addMesh(keep(grille), M.grille, "grille");
    }
    const footH = withBase ? 0.42 : FEET, footY = withBase ? BASE.y0 : Y_BOT;
    for (const x of [BASE.x0 + 1.4, BASE.x1 - 1.4]) for (const z of [BASE.z0 + 1.4, BASE.z1 - 1.6]) {  // rubber feet
      tolexParts.push(at(new THREE.CylinderGeometry(0.55, 0.62, footH + 0.02, 16), x, footY - footH / 2 + 0.01, z));
    }
    addMesh(merge(tolexParts), M.tolex, "tolex");

    // ------------------------------------------------------------ chrome trim --
    const chromeParts = [];
    const ball = (x, y, z, r = 0.5) => chromeParts.push(at(new THREE.SphereGeometry(r, 14, 10), x, y, z));
    for (const x of [X0 + 0.34, X1 - 0.34]) for (const y of [Y_BOT + 0.34, Y_TOP - 0.34]) for (const z of [Z_BACK + 0.34, Z_FRONT - 0.34]) ball(x, y, z, 0.5);
    if (withBase) for (const x of [BASE.x0 + 0.3, BASE.x1 - 0.3]) for (const y of [BASE.y0 + 0.3, BASE.y1 - 0.3]) for (const z of [BASE.z0 + 0.3, BASE.z1 - 0.3]) ball(x, y, z, 0.46);
    // seam bands: where the top unit meets the base, and the base's top edge
    chromeParts.push(slabY(X0 - 0.03, X1 + 0.03, Z_BACK - 0.03, Z_FRONT + 0.03, Y_BOT - 0.02, Y_BOT + 0.2, BB + 0.05, 0.05));
    if (withBase) {
      chromeParts.push(slabY(BASE.x0 - 0.03, BASE.x1 + 0.03, BASE.z0 - 0.03, BASE.z1 + 0.03, BASE.y1 - 0.3, BASE.y1 + 0.02, 0.48, 0.05));
      chromeParts.push(slabY(BASE.x0 - 0.03, BASE.x1 + 0.03, BASE.z0 - 0.03, BASE.z1 + 0.03, BASE.y0 - 0.02, BASE.y0 + 0.24, 0.48, 0.05));
    }
    // a polished frame around the harp cover, and the cover's front edge over the name rail
    const trimW = 0.2, trimH = 0.05;
    chromeParts.push(slabX(inL - 0.1, inR + 0.1, HARP.z0 - trimW, HARP.z0 + 0.02, RAIL.top - 0.05, Y_TOP + trimH, 0.06, 0.03));
    chromeParts.push(slabX(inL - 0.1, inR + 0.1, HARP.z1 - 0.02, HARP.z1 + trimW, Y_TOP - 0.02, Y_TOP + trimH, 0.03, 0.02));
    chromeParts.push(slabY(inL - trimW, inL + 0.02, HARP.z1 - 0.02, HARP.z0 + 0.02, Y_TOP - 0.02, Y_TOP + trimH, 0.03, 0.02));
    chromeParts.push(slabY(inR - 0.02, inR + trimW, HARP.z1 - 0.02, HARP.z0 + 0.02, Y_TOP - 0.02, Y_TOP + trimH, 0.03, 0.02));
    // pickup rail
    chromeParts.push(slabX(inL + 0.3, inR - 0.3, PICKUP_Z + 0.25, PICKUP_Z + 0.7, HARP.plate - 0.05, TINE_Y - 0.12, 0.08, 0.04));

    // --------------------------------------------------------- the name rail --
    addMesh(merge([slabX(inL - 0.02, inR + 0.02, RAIL.z1, RAIL.z0, RAIL.bottom, RAIL.top, 0.3, 0.1)]), M.rail, "name-rail");

    // ------------------------------------------------------------------ harp --
    addMesh(merge([
      slabY(inL + 0.02, inR - 0.02, HARP.z1, HARP.z0 - 0.05, -1.6, HARP.plate, 0.15, 0.06),
      slabX(inL + 0.2, inR - 0.2, HARP.z1 + 0.1, HARP.z1 + 1.4, HARP.plate - 0.1, HARP.plate + 0.55, 0.2, 0.06),  // rear support rail
    ]), M.plate, "harp-plate");

    const X = new Float32Array(N), LEN = new Float32Array(N), BZ = new Float32Array(N), FREQ = new Float32Array(N), PHASE = new Float32Array(N);
    const brassParts = [], pickupParts = [];
    for (let i = 0; i < N; i++) {
      const m = first + i, u = N > 1 ? i / (N - 1) : 0;
      X[i] = keyX(m);
      LEN[i] = 1.5 + 5.6 * Math.pow(1 - u, 1.35);                // long bass tines, short treble tines
      BZ[i] = TIP_Z - LEN[i];
      FREQ[i] = TAU * (5.5 + 7 * u);                             // visible wobble rate, faster up the keyboard
      PHASE[i] = rand() * TAU;
      const tb = 0.55 * LEN[i] + 0.45;                           // tonebar: from behind the block to about half the tine
      brassParts.push(at(new THREE.BoxGeometry(0.15, 0.09 + 0.07 * u, tb), X[i], TONEBAR_Y, BZ[i] - 0.45 + tb / 2));
      chromeParts.push(at(new THREE.BoxGeometry(0.34, 0.42, 0.42), X[i], (TINE_Y + TONEBAR_Y) / 2, BZ[i] - 0.05));  // tine block
      const p = new THREE.CylinderGeometry(0.2, 0.2, 0.55, 12);
      p.rotateX(Math.PI / 2);
      pickupParts.push(at(p, X[i], TINE_Y, PICKUP_Z));
    }
    addMesh(merge(brassParts), M.brass, "tonebars");
    addMesh(merge(pickupParts), M.pickup, "pickups");

    // ---------------------------------------------------------- controls, handles --
    const cheekCX = (X0 + inL) / 2;
    const blackParts = [];
    const knobProfile = [[0, 0], [0.56, 0], [0.6, 0.07], [0.55, 0.16], [0.44, 0.22], [0.4, 0.58], [0.36, 0.66], [0, 0.66]]
      .map(([x, y]) => new THREE.Vector2(x, y));
    for (const z of [0.7, -1.5]) {
      blackParts.push(at(new THREE.LatheGeometry(knobProfile, 28), cheekCX, Y_TOP, z));
      chromeParts.push(at(new THREE.CylinderGeometry(0.3, 0.3, 0.04, 24), cheekCX, Y_TOP + 0.67, z));
      chromeParts.push(at(new THREE.BoxGeometry(0.05, 0.02, 0.26), cheekCX, Y_TOP + 0.7, z - 0.12));  // pointer
    }
    { const bezel = new THREE.TorusGeometry(0.3, 0.06, 8, 20); bezel.rotateX(Math.PI / 2); chromeParts.push(at(bezel, cheekCX, Y_TOP + 0.02, -3.3)); }
    { const jack = new THREE.CylinderGeometry(0.2, 0.2, 0.08, 18); chromeParts.push(at(jack, cheekCX, Y_TOP + 0.02, -4.9)); }
    { const hole = new THREE.CylinderGeometry(0.11, 0.11, 0.1, 12); blackParts.push(at(hole, cheekCX, Y_TOP + 0.03, -4.9)); }
    for (const side of withBase ? [-1, 1] : []) {  // strap handles on the base ends
      const h = new THREE.TorusGeometry(1.5, 0.17, 8, 22, Math.PI);
      h.rotateX(Math.PI / 2); h.rotateY(Math.PI / 2); h.scale(0.55, 1, 1);
      if (side < 0) h.rotateY(Math.PI);  // bulge outward on the left end too (a negative scale would flip the winding)
      const xFace = side < 0 ? BASE.x0 : BASE.x1, yH = BASE.y1 - 3.2, zH = (BASE.z0 + BASE.z1) / 2;
      blackParts.push(at(h, xFace + side * 0.02, yH, zH));
      for (const dz of [-1.5, 1.5]) chromeParts.push(at(new THREE.BoxGeometry(0.2, 0.62, 0.6), xFace + side * 0.08, yH, zH + dz));
    }
    addMesh(merge(blackParts), M.black, "knobs-handles");
    addMesh(merge(chromeParts), M.chrome, "chrome");
    const lamp = addMesh(keep(at(new THREE.SphereGeometry(0.26, 18, 8, 0, TAU, 0, Math.PI / 2), cheekCX, Y_TOP + 0.02, -3.3)), M.lamp, "jewel-lamp");

    // ----------------------------------------------------------- harp cover --
    const coverGeo = merge([slabY(inL, inR, HARP.z1, HARP.z0, Y_TOP - 0.12, Y_TOP, 0.04, 0.03)]);
    const cover = addMesh(coverGeo, M.cover, "harp-cover");
    coverTex.repeat.set(1 / (inR - inL), 1 / (HARP.z0 - HARP.z1));
    coverTex.offset.set(0.5, 0.5);
    coverTex.wrapS = coverTex.wrapT = THREE.ClampToEdgeWrapping;
    // Glows draw before the cover (so the smoke dims them a little), and the cover draws before the host's other
    // transparents: it writes no depth, and a later draw order would darken the trails that rise in front of it.
    cover.renderOrder = -1;

    // ------------------------------------------------------ instanced, reactive --
    const tineGeo = keep(new THREE.CylinderGeometry(0.036, 0.03, 1, 8, 1, true));
    tineGeo.rotateX(Math.PI / 2); tineGeo.translate(0, 0, 0.5);   // base at z=0, tip at z=1 (toward the player)
    const glowGeo = keep(new THREE.CylinderGeometry(0.036, 0.03, 1, 8, 6, true));
    glowGeo.rotateX(Math.PI / 2); glowGeo.translate(0, 0, 0.5);
    {
      const p = glowGeo.attributes.position, c = new Float32Array(p.count * 3);
      for (let v = 0; v < p.count; v++) { const k = 0.18 + 0.82 * Math.pow(p.getZ(v), 1.6); c[v * 3] = c[v * 3 + 1] = c[v * 3 + 2] = k; }
      glowGeo.setAttribute("color", new THREE.BufferAttribute(c, 3));
    }
    const poolGeo = keep(new THREE.PlaneGeometry(1, 1)); poolGeo.rotateX(-Math.PI / 2);
    const damperGeo = keep(new THREE.BoxGeometry(0.3, 0.16, 0.3));
    // Tine light: a soft vertical haze standing in the smoked case just behind each tine tip, facing the player. The
    // plate pools are flat and a 17-22 degree camera sees them edge-on (receipt r2), but this faces that camera.
    const CARD_H = (Y_TOP - 0.14) - HARP.plate;
    const cardGeo = keep(new THREE.PlaneGeometry(1, 1));
    const cardTex = (() => {
      const c = canvas(64, 128), g = c.getContext("2d");
      const tineAt = (TINE_Y - HARP.plate) / CARD_H;  // brightest at tine height
      const v = g.createLinearGradient(0, 128, 0, 0);
      v.addColorStop(0, "rgba(255,255,255,0)");
      v.addColorStop(Math.max(0.05, tineAt - 0.14), "rgba(255,255,255,0.5)");
      v.addColorStop(tineAt, "rgba(255,255,255,1)");
      v.addColorStop(Math.min(0.95, tineAt + 0.2), "rgba(255,255,255,0.35)");
      v.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = v; g.fillRect(0, 0, 64, 128);
      g.globalCompositeOperation = "destination-in";
      const h = g.createLinearGradient(0, 0, 64, 0);
      h.addColorStop(0, "rgba(255,255,255,0)"); h.addColorStop(0.5, "rgba(255,255,255,1)"); h.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = h; g.fillRect(0, 0, 64, 128);
      return texture(c);
    })();
    const cardMat = keep(new THREE.MeshBasicMaterial({ color: 0xffffff, map: cardTex, transparent: true, depthWrite: false,
      blending: THREE.AdditiveBlending, side: THREE.DoubleSide }));

    const instanced = (geo, mat, count, name, dynamic) => {
      const m = new THREE.InstancedMesh(geo, mat, Math.max(1, count));
      m.count = count;
      m.name = name;
      m.frustumCulled = false;  // instances move; the stored bounds would go stale
      if (dynamic) m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      group.add(m);
      return m;
    };
    const tines = instanced(tineGeo, M.chrome, N, "tines", true);
    const glowTines = instanced(glowGeo, M.glow, N, "tine-glow", true);
    const pools = instanced(poolGeo, M.pool, N, "tine-pools", false);
    const dampers = instanced(damperGeo, M.felt, ND, "dampers", true);
    const cards = instanced(cardGeo, cardMat, N, "tine-light", false);
    for (const m of [glowTines, pools, cards]) {
      m.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(Math.max(1, N) * 3), 3);
      m.instanceColor.setUsage(THREE.DynamicDrawUsage);
      m.renderOrder = -2;
      m.visible = false;
    }

    const mtx = new THREE.Matrix4(), P = new THREE.Vector3(), Q = new THREE.Quaternion(), E = new THREE.Euler(), SC = new THREE.Vector3();
    const tmpC = new THREE.Color();
    const IDQ = new THREE.Quaternion();
    function placeTine(i, ang) {
      E.set(ang, 0, 0); Q.setFromEuler(E);
      P.set(X[i], TINE_Y, BZ[i]);
      SC.set(1, 1, LEN[i]); mtx.compose(P, Q, SC); tines.setMatrixAt(i, mtx);
      SC.set(4.6, 4.6, LEN[i]); mtx.compose(P, Q, SC); glowTines.setMatrixAt(i, mtx);
    }
    const damperZ = (i) => TIP_Z - 0.22 * LEN[i] - 0.1;
    function placeDamper(i, lift) {
      P.set(X[i], TINE_Y + 0.036 + 0.08 + lift * 0.3, damperZ(i));
      SC.set(1, 1, 1); mtx.compose(P, IDQ, SC); dampers.setMatrixAt(i, mtx);
    }
    for (let i = 0; i < N; i++) {
      placeTine(i, 0);
      P.set(X[i], HARP.plate + 0.015, BZ[i] + LEN[i] * 0.55); SC.set(1.7, 1, LEN[i] + 2.6);
      mtx.compose(P, IDQ, SC); pools.setMatrixAt(i, mtx);
      P.set(X[i], HARP.plate + CARD_H / 2, TIP_Z - 0.25); SC.set(1.0, CARD_H, 1);
      mtx.compose(P, IDQ, SC); cards.setMatrixAt(i, mtx);
      if (i < ND) placeDamper(i, 0);
    }

    scene.add(group);

    // --------------------------------------------------------------- reaction --
    const held = new Uint8Array(N), lit = new Uint8Array(N);
    const glow = new Float32Array(N), flash = new Float32Array(N), lift = new Float32Array(N);
    const struck = new Float64Array(N).fill(-Infinity);
    const col = new Float32Array(N * 3);
    let now = 0, lampLevel = 0, active = false, primed = false;

    function strike(i, vel, time) {
      struck[i] = time;
      const v = Math.min(1, Math.max(0, (vel ?? 100) / 127));
      noteColor(first + i, vel ?? 100, tmpC);
      col[i * 3] = tmpC.r; col[i * 3 + 1] = tmpC.g; col[i * 3 + 2] = tmpC.b;
      if (!primed) { glow[i] = Math.max(glow[i], 0.25 + 0.5 * v); return; }  // already sounding when mounted: no flash
      let age = now - time;
      if (!(age >= 0 && age < 5)) age = 0;  // a clock we cannot compare: treat the strike as this frame's
      glow[i] = Math.max(glow[i], (0.35 + 1.25 * Math.pow(v, 1.4)) * Math.exp(-age / 2.6));
      flash[i] = Math.max(flash[i], 2.6 * Math.pow(v, 2.2) * Math.exp(-age / 0.12));
      lampLevel = Math.max(lampLevel, v * v * Math.exp(-age / 0.2));
    }
    const onPressed = (info, midi) => {
      const i = midi - first;
      if (i < 0 || i >= N) return;
      held[i] = 1;
      const t0 = info?.t0 ?? now;
      if (t0 > struck[i]) strike(i, info?.vel, t0);
    };

    function update(dt, t, state) {
      if (!active) return;
      now = t;
      dt = Math.min(Math.max(dt || 0, 0), 0.1);
      held.fill(0);
      const pedal = !!state?.pedal;
      if (state?.pressed) state.pressed.forEach(onPressed);
      const notes = state?.notes;
      if (notes) for (let k = 0; k < notes.length; k++) {
        const n = notes[k], i = n.midi - first;
        if (i >= 0 && i < N && n.t > struck[i]) {
          if (primed) strike(i, n.vel, n.t); else struck[i] = n.t;
        }
      }
      primed = true;

      const kFlash = Math.exp(-dt / 0.12), kHeld = Math.exp(-dt / 2.6), kPedal = Math.exp(-dt / 1.8), kFree = Math.exp(-dt / 0.16);
      const kLift = 1 - Math.exp(-dt / 0.045);
      let any = false, sr = 0, sg = 0, sb = 0, moved = false, colours = false, damped = false;
      for (let i = 0; i < N; i++) {
        glow[i] *= held[i] ? kHeld : pedal ? kPedal : kFree;
        flash[i] *= kFlash;
        const e = glow[i] + flash[i];
        if (e > 0.004) {
          any = true; lit[i] = 1;
          const r = col[i * 3] * e, g = col[i * 3 + 1] * e, b = col[i * 3 + 2] * e;
          // gains put a hard strike's tine well over the bloom threshold (0.9) and its pool near it (receipt r1: 1x / 0.42x
          // read as faint dots from the page camera)
          glowTines.setColorAt(i, tmpC.setRGB(r * 2.0, g * 2.0, b * 2.0));
          pools.setColorAt(i, tmpC.setRGB(r * 0.95, g * 0.95, b * 0.95));
          cards.setColorAt(i, tmpC.setRGB(r * 0.5, g * 0.5, b * 0.5));
          sr += r; sg += g; sb += b;
          placeTine(i, (Math.min(e, 1.2) * 0.055 / LEN[i]) * Math.sin(t * FREQ[i] + PHASE[i]));
          moved = colours = true;
        } else if (lit[i]) {
          lit[i] = 0; glow[i] = flash[i] = 0;
          glowTines.setColorAt(i, tmpC.setRGB(0, 0, 0));
          pools.setColorAt(i, tmpC);
          cards.setColorAt(i, tmpC);
          placeTine(i, 0);
          moved = colours = true;
        }
        if (i < ND) {
          const target = held[i] || pedal ? 1 : 0;
          if (lift[i] !== target) {
            lift[i] += (target - lift[i]) * kLift;
            if (Math.abs(target - lift[i]) < 1e-3) lift[i] = target;
            placeDamper(i, lift[i]);
            damped = true;
          }
        }
      }
      if (moved) { tines.instanceMatrix.needsUpdate = true; glowTines.instanceMatrix.needsUpdate = true; }
      if (colours) { glowTines.instanceColor.needsUpdate = pools.instanceColor.needsUpdate = cards.instanceColor.needsUpdate = true; }
      if (damped) dampers.instanceMatrix.needsUpdate = true;
      glowTines.visible = pools.visible = cards.visible = any;
      M.cover.emissive.setRGB(Math.min(0.2, sr * 0.012), Math.min(0.2, sg * 0.012), Math.min(0.2, sb * 0.012));
      lampLevel *= Math.exp(-dt / 0.2);
      M.lamp.emissiveIntensity = 0.35 + 3.2 * lampLevel;
    }

    function setActive(on) {
      active = !!on;
      group.visible = active;
      if (!active) {
        glow.fill(0); flash.fill(0); lampLevel = 0; primed = false;
        for (let i = 0; i < N; i++) if (lit[i]) { lit[i] = 0; glowTines.setColorAt(i, tmpC.setRGB(0, 0, 0)); pools.setColorAt(i, tmpC); cards.setColorAt(i, tmpC); placeTine(i, 0); }
        glowTines.instanceColor.needsUpdate = pools.instanceColor.needsUpdate = cards.instanceColor.needsUpdate = true;
        tines.instanceMatrix.needsUpdate = glowTines.instanceMatrix.needsUpdate = true;
        glowTines.visible = pools.visible = cards.visible = false;
        M.cover.emissive.setRGB(0, 0, 0);
        M.lamp.emissiveIntensity = 0.35;
      }
    }

    function resize(/* framing */) { /* the body has no framing-dependent parts */ }

    function dispose() {
      scene.remove(group);
      for (const m of [tines, glowTines, pools, dampers, cards]) m.dispose();
      for (const d of disposables) d.dispose?.();
      group.clear();
    }

    return {
      group, update, resize, setActive, dispose,
      keyStyle: { ...DEF.keyStyle, range: { first, last } },
      keySpan: { first, last },
      // floorY is where this body ends; hideHostBody: the host's own keybed, cheeks and back rail would show through
      stage: { floorY: FLOOR_Y, withBase, hideHostBody: true, width: X1 - X0, depth: Z_FRONT - Z_BACK, front: Z_FRONT, back: Z_BACK },
      // close-up: the harp behind the lab's D flat 6/9 voicing (MIDI 49-75, x about -9 to 6)
      views: { close: { target: [-2.2, 0.25, -9.2], from: [5.8, 9.2, 6.5], fov: 34 } },
      info: { first, last, keys: N, ranged, withBase, width: X1 - X0, depth: Z_FRONT - Z_BACK, floorY: FLOOR_Y, centerX: CX },
    };
  },
};

export default DEF;
