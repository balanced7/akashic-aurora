// Vintage Synth — arsenal/web/piano/instruments/vintage-synth.js  (ES module, a piano instrument)
// A generic vintage analog synth body built around the host's keys: walnut end cheeks, a black case, a pitch and a mod
// wheel in a box left of the keys, and a tilted panel with rows of skirted knobs, rocker switches and small jewel lamps.
// No brand, no wordmark: the legend is our own section and function names drawn on a canvas.
//
// Proportions follow the monosynth notes in the instrument spec (section 2.4: sloping cheek top edge, a panel hinged next
// to the keys that tilts back on a kickstand, orange / blue / grey rockers, five sections Controllers -> Output, a
// near-black face with a light-grey legend), widened to a 61-key span (C2..C7). One world unit is one white-key pitch
// (23.57 mm), so the body is about 1.0 m wide.
//
// Options (ctx.options): face "dark" (default, #1b1c1f with a #c9c9c4 legend, per the spec) or "silver" (brushed aluminium).
//
// Keys stay host-owned. keySpan says which 61 keys the body frames; keyStyle gives colour hints for them.
//
// Reactive parts (the only things that emit light):
// - 12 pitch lamps across the top of the panel, one per pitch class, flash in noteColor with the strike's velocity and hold a
//   dimmer glow while a key of that pitch class is down
// - an 8-lamp velocity ladder in the Output section: the hardest recent strike, in its note's colour, with a peak-hold lamp
// - a PEDAL lamp (amber while the sustain pedal is down), a CHORD lamp (lit while a chord is named) and a pilot lamp that
//   warms up while something is being played
// - mechanical: the filter CUTOFF and CONTOUR knobs sweep with a velocity envelope; the mod wheel rolls with the number of
//   held keys; the panel eases to a per-framing tilt
//
// Everything comes through ctx: no imports. No per-frame allocation (preallocated scratch objects, Map.forEach with a
// bound visitor, instanced attributes written in place).

const TAU = Math.PI * 2;
const damp = (current, target, tau, dt) => current + (target - current) * (1 - Math.exp(-dt / Math.max(tau, 1e-4)));
const clamp = (v, lo, hi) => (v < lo ? lo : v > hi ? hi : v);
const FONT = "Jost, Outfit, Raleway, 'Segoe UI', Arial, sans-serif";
const NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];

const DEF = {
  id: "vintage-synth",
  name: "Vintage Synth",
  keySpan: { first: 36, last: 96 },  // C2..C7, 61 keys; the host should hide (or dim) keys outside it
  keyStyle: { whiteColor: 0xebe6d8, blackColor: 0x0f0f10, capHeight: 0.8, frontLip: 0.05 },
  options: { face: { values: ["dark", "silver"], default: "dark" } },

  create(ctx) {
    const { THREE, scene, keyX, noteColor } = ctx;
    const KEY = ctx.KEY || {};
    const span = ctx.span || {};
    const first = Math.max(KEY.first ?? 21, span.first ?? DEF.keySpan.first, DEF.keySpan.first);
    const last = Math.min(KEY.last ?? 108, span.last ?? DEF.keySpan.last, DEF.keySpan.last);
    const whiteL = KEY.whiteL ?? 6.2, keyBack = KEY.back ?? -3.1, keyFront = keyBack + whiteL;
    const floorY = span.floorY ?? -2.3;
    const FACE = (ctx.options?.face ?? DEF.options.face.default) === "silver" ? "silver" : "dark";
    const DARK = FACE === "dark";

    // ------------------------------------------------------------ layout --
    const keysLeft = keyX(first) - 0.5, keysRight = keyX(last) + 0.5;
    const WHEEL_BOX = 4.0, GAP = 0.15, CHEEK_T = 1.1;
    const innerL = keysLeft - GAP - WHEEL_BOX, innerR = keysRight + GAP;
    const innerW = innerR - innerL, cx = (innerL + innerR) / 2;
    const BOTTOM = floorY + 0.08;           // feet carry the case 0.08 above the floor
    const FRONT = keyFront + 0.65, REAR = -16.0;
    const HINGE = { y: 0.62, z: -5.2 };
    const PT = 1.45, PD = 10.6;             // panel box thickness and depth

    const group = new THREE.Group();
    group.name = "instrument:vintage-synth";
    const panel = new THREE.Group();
    panel.position.set(cx, HINGE.y, HINGE.z);
    group.add(panel);

    const disposables = [];
    const own = (x) => { disposables.push(x); return x; };
    let disposed = false;

    // --------------------------------------------------------- textures --
    function walnutTexture() {
      const c = document.createElement("canvas");
      c.width = 256; c.height = 1024;
      const g = c.getContext("2d");
      g.fillStyle = "#4a2c19";
      g.fillRect(0, 0, c.width, c.height);
      let seed = 7;
      const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
      for (let i = 0; i < 90; i++) {         // long wavy grain lines along the texture's v axis
        const x0 = rnd() * c.width, amp = 3 + rnd() * 14, freq = 0.004 + rnd() * 0.01, ph = rnd() * TAU;
        const dark = rnd() < 0.6;
        g.strokeStyle = dark ? `rgba(26,13,6,${0.18 + rnd() * 0.35})` : `rgba(140,92,56,${0.08 + rnd() * 0.18})`;
        g.lineWidth = 0.6 + rnd() * (dark ? 3.2 : 1.6);
        g.beginPath();
        for (let y = 0; y <= c.height; y += 8) {
          const x = x0 + Math.sin(y * freq + ph) * amp + Math.sin(y * 0.031 + ph * 2) * 1.5;
          if (y === 0) g.moveTo(x, y); else g.lineTo(x, y);
        }
        g.stroke();
      }
      for (let i = 0; i < 6; i++) {          // a few soft figure bands
        const y = rnd() * c.height;
        const grad = g.createLinearGradient(0, y - 60, 0, y + 60);
        grad.addColorStop(0, "rgba(0,0,0,0)");
        grad.addColorStop(0.5, rnd() < 0.5 ? "rgba(20,10,4,0.22)" : "rgba(150,100,60,0.12)");
        grad.addColorStop(1, "rgba(0,0,0,0)");
        g.fillStyle = grad;
        g.fillRect(0, y - 60, c.width, 120);
      }
      const tex = own(new THREE.CanvasTexture(c));
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.wrapS = tex.wrapT = THREE.RepeatWrapping;
      tex.anisotropy = 4;
      return tex;
    }

    // ------------------------------------------------------ panel layout --
    // Face coordinates: u 0..1 left to right, v 0..1 top (rear edge) to bottom (hinge edge).
    const FACE_INSET = 0.22;
    const FW = innerW - 2 * FACE_INSET, FH = PD - 2 * FACE_INSET;
    const faceX = (u) => -FW / 2 + u * FW;
    const faceZ = (v) => -PD + FACE_INSET + v * FH;
    const ROW = [0.40, 0.64, 0.875];
    const SECTIONS = [
      { name: "CONTROLLERS", u0: 0.0, u1: 0.12 },
      { name: "OSCILLATOR BANK", u0: 0.12, u1: 0.41 },
      { name: "MIXER", u0: 0.41, u1: 0.57 },
      { name: "MODIFIERS", u0: 0.57, u1: 0.86 },
      { name: "OUTPUT", u0: 0.86, u1: 1.0 },
    ];
    // knobs: [u, v, label, scale, value 0..1]
    const KNOBS = [
      [0.04, ROW[0], "TUNE", 0.9, 0.5], [0.04, ROW[1], "GLIDE", 0.9, 0.18], [0.04, ROW[2], "MOD MIX", 0.9, 0.35],
      [0.165, ROW[0], "RANGE", 1, 0.4], [0.255, ROW[0], "FREQUENCY", 1, 0.5], [0.345, ROW[0], "WAVEFORM", 1, 0.62],
      [0.165, ROW[1], "RANGE", 1, 0.4], [0.255, ROW[1], "FREQUENCY", 1, 0.53], [0.345, ROW[1], "WAVEFORM", 1, 0.8],
      [0.165, ROW[2], "RANGE", 1, 0.2], [0.255, ROW[2], "FREQUENCY", 1, 0.44], [0.345, ROW[2], "WAVEFORM", 1, 0.3],
      [0.455, ROW[0], "OSC 1", 0.9, 0.8], [0.455, ROW[1], "OSC 2", 0.9, 0.7], [0.455, ROW[2], "OSC 3", 0.9, 0.55],
      [0.64, ROW[0], "CUTOFF", 1.12, 0.42], [0.725, ROW[0], "EMPHASIS", 1, 0.3], [0.81, ROW[0], "CONTOUR", 1, 0.5],
      [0.64, ROW[1], "ATTACK", 1, 0.1], [0.725, ROW[1], "DECAY", 1, 0.45], [0.81, ROW[1], "SUSTAIN", 1, 0.6],
      [0.64, ROW[2], "ATTACK", 1, 0.05], [0.725, ROW[2], "DECAY", 1, 0.5], [0.81, ROW[2], "SUSTAIN", 1, 0.85],
      [0.905, ROW[0], "VOLUME", 1.25, 0.66], [0.905, ROW[2], "PHONES", 0.85, 0.4],
    ];
    const KNOB_CUTOFF = 15, KNOB_CONTOUR = 17;
    // rockers: [u, v, label, colour, on]
    const ORANGE = 0xd9601c, BLUE = 0x2f6fc4, GREY = 0x9a9ea3;
    const ROCKERS = [
      [0.092, ROW[0], "OSC MOD", ORANGE, 1], [0.092, ROW[1], "GLIDE", GREY, 0],
      [0.52, ROW[0], "ON", BLUE, 1], [0.52, ROW[1], "ON", BLUE, 1], [0.52, ROW[2], "ON", BLUE, 0],
      [0.595, ROW[0], "FILTER MOD", ORANGE, 1], [0.595, ROW[1], "KBD 1", ORANGE, 0], [0.595, ROW[2], "KBD 2", ORANGE, 1],
      [0.905, ROW[1], "POWER", GREY, 1],
    ];
    // lamps: 0..11 pitch classes, 12..19 velocity ladder (bottom to top), 20 pedal, 21 chord, 22 pilot
    const LAMPS = [];
    for (let pc = 0; pc < 12; pc++) LAMPS.push([0.155 + pc * (0.69 / 11), 0.19, NOTE_NAMES[pc], 1.2]);
    const LADDER_N = 8, LADDER0 = 12;
    for (let i = 0; i < LADDER_N; i++) LAMPS.push([0.965, 0.9 - i * (0.62 / (LADDER_N - 1)), "", 0.85]);
    const LAMP_PEDAL = 20, LAMP_CHORD = 21, LAMP_PILOT = 22;
    LAMPS.push([0.092, ROW[2], "PEDAL", 1.05], [0.092, 0.19, "CHORD", 1.05], [0.895, 0.19, "", 0.8]);

    // Draws the face (base finish, section band, legend, scales) into its canvas. Called once, and once more if the
    // legend font was still loading.
    function drawFace(c) {
      const W = c.width, H = c.height;
      const g = c.getContext("2d");
      const px = (u) => u * W, py = (v) => v * H;
      const unit = W / FW;                   // canvas px per world unit
      const spacing = (s) => { if ("letterSpacing" in g) g.letterSpacing = s; };
      spacing("0px");
      g.globalAlpha = 1;
      // the base: near-black anodised (dark) or light aluminium (silver), then thousands of faint horizontal brush streaks
      g.fillStyle = DARK ? "#1b1c1f" : "#b4b7bc";
      g.fillRect(0, 0, W, H);
      let seed = 11;
      const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
      for (let i = 0, n = DARK ? 3600 : 5200; i < n; i++) {
        const y = rnd() * H, x = rnd() * W, len = 80 + rnd() * 900, l = rnd();
        g.strokeStyle = DARK
          ? (l < 0.5 ? `rgba(0,0,0,${0.06 + rnd() * 0.12})` : `rgba(96,100,108,${0.02 + rnd() * 0.05})`)
          : (l < 0.5 ? `rgba(90,94,100,${0.03 + rnd() * 0.07})` : `rgba(245,247,250,${0.03 + rnd() * 0.08})`);
        g.lineWidth = 0.5 + rnd() * 1.4;
        g.beginPath(); g.moveTo(x, y); g.lineTo(x + len, y + (rnd() - 0.5) * 0.8); g.stroke();
      }
      const ink = DARK ? "rgba(201,201,196,0.95)" : "rgba(22,23,26,0.92)";   // #c9c9c4 legend on the dark face
      // title band and section dividers
      const band = 0.12;
      g.fillStyle = DARK ? "rgba(8,8,10,0.9)" : "rgba(24,25,28,0.94)";
      g.fillRect(0, 0, W, py(band));
      g.fillStyle = DARK ? "rgba(214,214,209,0.96)" : "rgba(230,232,236,0.95)";
      g.textAlign = "center"; g.textBaseline = "middle";
      g.font = `600 ${Math.round(0.36 * unit)}px ${FONT}`;
      spacing(`${Math.round(0.08 * unit)}px`);
      for (const s of SECTIONS) g.fillText(s.name, px((s.u0 + s.u1) / 2), py(band / 2));
      g.fillStyle = ink; g.strokeStyle = ink;
      if (DARK) {                            // a thin light rule under the band
        g.globalAlpha = 0.5;
        g.fillRect(0, py(band), W, Math.max(2, 0.03 * unit));
      }
      g.globalAlpha = DARK ? 0.55 : 1;
      g.lineWidth = Math.max(2, 0.035 * unit);
      for (let i = 1; i < SECTIONS.length; i++) {
        const x = px(SECTIONS[i].u0);
        g.beginPath(); g.moveTo(x, py(band)); g.lineTo(x, H); g.stroke();
      }
      g.globalAlpha = 1;
      // labels
      const label = (u, v, text, size = 0.2) => {
        g.font = `500 ${Math.round(size * unit)}px ${FONT}`;
        spacing(`${Math.round(0.03 * unit)}px`);
        g.fillText(text, px(u), py(v));
      };
      for (const [u, v, text, s] of KNOBS) {
        const r = 0.64 * s;
        label(u, v - (r + 0.36) / FH, text);
        // scale: 11 dots on a 300 degree arc, heavier at the ends
        for (let i = 0; i <= 10; i++) {
          const a = (-150 + i * 30) * Math.PI / 180, rr = (r + 0.17) * unit;
          const dot = (i === 0 || i === 10 || i === 5 ? 0.05 : 0.032) * unit;
          g.beginPath(); g.arc(px(u) + rr * Math.sin(a), py(v) - rr * Math.cos(a), dot, 0, TAU); g.fill();
        }
      }
      for (const [u, v, text] of ROCKERS) label(u, v - 0.9 / FH, text, 0.17);
      for (let i = 0; i < 12; i++) label(LAMPS[i][0], LAMPS[i][1] + 0.52 / FH, LAMPS[i][2], 0.16);
      label(LAMPS[LAMP_PEDAL][0], LAMPS[LAMP_PEDAL][1] - 0.62 / FH, "PEDAL", 0.17);
      label(LAMPS[LAMP_CHORD][0], LAMPS[LAMP_CHORD][1] + 0.44 / FH, "CHORD", 0.16);
      label(0.965, 0.24, "PEAK", 0.16);
      // ladder ticks
      for (let i = 0; i < LADDER_N; i++) {
        const [u, v] = LAMPS[LADDER0 + i];
        g.fillRect(px(u) - 0.52 * unit, py(v) - 1.5, 0.16 * unit, 3);
      }
      // a thin frame at the face edge
      g.strokeStyle = DARK ? "rgba(201,201,196,0.3)" : "rgba(20,20,22,0.6)"; g.lineWidth = 3;
      g.strokeRect(1.5, 1.5, W - 3, H - 3);
    }
    function faceTexture() {
      const c = document.createElement("canvas");
      c.width = 2048; c.height = Math.round(2048 * FH / FW);
      drawFace(c);
      const tex = own(new THREE.CanvasTexture(c));
      tex.colorSpace = THREE.SRGBColorSpace;
      tex.anisotropy = 8;
      // If the legend font is declared but still loading, redraw once it lands (a one-off, never per frame).
      try {
        const spec = `600 32px ${FONT}`;
        if (document.fonts && !document.fonts.check(spec)) {
          Promise.all([document.fonts.load(spec), document.fonts.load(`500 32px ${FONT}`)]).then(() => {
            if (disposed) return;
            drawFace(c);
            tex.needsUpdate = true;
          }, () => {});
        }
      } catch { /* no FontFaceSet: keep the first draw */ }
      return tex;
    }

    // -------------------------------------------------------- materials --
    const walnutTex = walnutTexture();
    const walnut = own(new THREE.MeshPhysicalMaterial({ color: 0xffffff, map: walnutTex, roughness: 0.5, metalness: 0,
      clearcoat: 0.4, clearcoatRoughness: 0.42, sheen: 0.3, sheenColor: new THREE.Color(0x6b3a1c), sheenRoughness: 0.6 }));
    // Satin black: a broad, dim lobe, so the host's rim light does not paint the case tops pale blue.
    const body = own(new THREE.MeshPhysicalMaterial({ color: 0x08080a, roughness: 0.72, metalness: 0.0,
      clearcoat: 0.12, clearcoatRoughness: 0.6 }));
    // The face stays under the host's bloom threshold (0.9) under its 1.9 key light. Dark: near-black anodised, a soft
    // anisotropic sheen, the light legend carries the read. Silver: mid-grey albedo, brushed specular.
    const faceMat = own(new THREE.MeshPhysicalMaterial(DARK
      ? { color: 0xffffff, map: faceTexture(), roughness: 0.55, metalness: 0.2, anisotropy: 0.3, anisotropyRotation: 0 }
      : { color: 0xd6d6d6, map: faceTexture(), roughness: 0.48, metalness: 0.45, anisotropy: 0.45, anisotropyRotation: 0 }));
    const metal = own(new THREE.MeshPhysicalMaterial({ color: 0x8f9398, roughness: 0.44, metalness: 0.6,
      anisotropy: 0.4 }));
    const chrome = own(new THREE.MeshPhysicalMaterial({ color: 0xa9adb3, roughness: 0.3, metalness: 0.8 }));
    const knobMat = own(new THREE.MeshPhysicalMaterial({ color: 0x101012, roughness: 0.38, metalness: 0,
      clearcoat: 0.6, clearcoatRoughness: 0.15 }));
    const pointerMat = own(new THREE.MeshPhysicalMaterial({ color: 0xbab6ad, roughness: 0.55, metalness: 0 }));
    const rockerMat = own(new THREE.MeshPhysicalMaterial({ color: 0xffffff, roughness: 0.42, metalness: 0,
      clearcoat: 0.5, clearcoatRoughness: 0.2 }));
    const rubber = own(new THREE.MeshPhysicalMaterial({ color: 0x151517, roughness: 0.8, metalness: 0 }));
    // Wheel-box deck: rough dark plastic (#2a2a2a), no clearcoat, so the host's rim light cannot mirror off it.
    const deck = own(new THREE.MeshPhysicalMaterial({ color: 0x2a2a2a, roughness: 0.78, metalness: 0 }));
    // Lamp lenses: smoky jewel glass (PBR), with each instance's colour used as emitted light instead of albedo. The unlit
    // lens is a dark smoky #151515 so lit and unlit lamps part clearly at player scale.
    const lensMat = own(new THREE.MeshPhysicalMaterial({ color: 0x151515, roughness: 0.12, metalness: 0,
      clearcoat: 1, clearcoatRoughness: 0.05, emissive: 0x000000 }));
    lensMat.onBeforeCompile = (shader) => {
      shader.fragmentShader = shader.fragmentShader
        .replace("#include <color_fragment>", "")
        // r186 defines USE_COLOR (not USE_INSTANCING_COLOR) in the fragment stage when instance colours are present
        .replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\n#if defined( USE_COLOR ) || defined( USE_INSTANCING_COLOR )\ntotalEmissiveRadiance += vColor.rgb;\n#endif");
    };
    lensMat.customProgramCacheKey = () => "vintage-synth-lens";

    // -------------------------------------------------------- geometry --
    // RoundedBoxGeometry comes through ctx (the host imports it); a plain box stands in without it.
    const box = (w, h, d, r = 0.08, seg = 3) =>
      own(ctx.RoundedBoxGeometry ? new ctx.RoundedBoxGeometry(w, h, d, seg, r) : new THREE.BoxGeometry(w, h, d));
    const addMesh = (geo, mat, x, y, z, parent = group) => {
      const m = new THREE.Mesh(geo, mat);
      m.position.set(x, y, z);
      parent.add(m);
      return m;
    };

    // base case: key tray, front rail, back rail, rear case under the panel
    const trayTop = -0.82;
    addMesh(box(innerW, trayTop - BOTTOM, FRONT - 0.1 - (keyBack - 1.1), 0.1), body,
      cx, (trayTop + BOTTOM) / 2, (FRONT - 0.1 + keyBack - 1.1) / 2);
    addMesh(box(innerW, 0.34, 0.3, 0.06), metal, cx, -0.66, keyFront + 0.32);                   // front rail (key slip)
    addMesh(box(innerW, 0.55 - BOTTOM, 1.05, 0.08), body, cx, (0.55 + BOTTOM) / 2, keyBack - 0.58); // back rail
    addMesh(box(innerW, 0.05, 0.12, 0.02), metal, cx, 0.56, keyBack - 0.12);                     // thin trim line on it
    addMesh(box(innerW, HINGE.y - 0.1 - BOTTOM, HINGE.z - REAR + 1.0, 0.12), body,
      cx, (HINGE.y - 0.1 + BOTTOM) / 2, (HINGE.z + 1.0 + REAR + 0.2) / 2);                        // rear case

    // wheel box, left of the keys: a dark deck with two wheels half sunk through rubber-lined slots
    const wheelCx = innerL + WHEEL_BOX / 2, wheelZc = (keyFront + keyBack) / 2;
    addMesh(box(WHEEL_BOX, 0.9, keyFront - keyBack + 0.2, 0.08), body, wheelCx, -0.5, wheelZc);
    addMesh(box(WHEEL_BOX - 0.24, 0.05, keyFront - keyBack - 0.1, 0.02), deck, wheelCx, -0.03, wheelZc);
    const DECK_TOP = -0.005, WHEEL_R = 0.96, WHEEL_W = 0.46;   // 22.6 mm radius over the tread
    const WHEEL_X = [wheelCx - 0.85, wheelCx + 0.85], WHEEL_Z = wheelZc + 0.4, WHEEL_Y = DECK_TOP;
    const slots = new THREE.InstancedMesh(box(WHEEL_W + 0.3, 0.05, 2 * WHEEL_R + 0.36, 0.024, 2), rubber, 2);
    // the wheel: a dished metal hub (lathe, axis along x) inside a knurled rubber tyre (a flattened torus)
    const V2 = (x, y) => new THREE.Vector2(x, y);
    const hubGeo = own(new THREE.LatheGeometry([V2(0, -0.19), V2(0.46, -0.19), V2(0.52, -0.225), V2(0.8, -0.225),
      V2(0.82, -0.2), V2(0.82, 0.2), V2(0.8, 0.225), V2(0.52, 0.225), V2(0.46, 0.19), V2(0, 0.19)], 48));
    hubGeo.rotateZ(Math.PI / 2);
    const tyreGeo = own(new THREE.TorusGeometry(0.86, 0.1, 10, 120));
    {
      const pos = tyreGeo.getAttribute("position");
      for (let i = 0; i < pos.count; i++) {  // 30 shallow ridges on the outer half of the ring
        const x = pos.getX(i), y = pos.getY(i), r = Math.hypot(x, y), a = Math.atan2(y, x);
        const k = 1 + clamp((r - 0.86) / 0.1, 0, 1) * 0.018 * (0.5 + 0.5 * Math.cos(a * 30)) / r;
        pos.setXY(i, x * k, y * k);
      }
      tyreGeo.scale(1, 1, 2.3);             // tread width about 0.46 along the axle
      tyreGeo.computeVertexNormals();
      tyreGeo.rotateY(Math.PI / 2);         // torus axis z -> world x
    }
    // satin grey hub: light enough to read the disc against the tyre, rough enough that the key light does not glint off
    // the dished rim over the bloom threshold
    const hubMat = own(new THREE.MeshPhysicalMaterial({ color: 0x6d7075, roughness: 0.62, metalness: 0.3 }));
    const wheels = new THREE.InstancedMesh(hubGeo, hubMat, 2);
    const tyres = new THREE.InstancedMesh(tyreGeo, rubber, 2);
    const wheelIdx = new THREE.InstancedMesh(own(new THREE.BoxGeometry(0.5, 0.03, 0.07)), pointerMat, 2);
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), e = new THREE.Euler(), p3 = new THREE.Vector3(),
      s3 = new THREE.Vector3(1, 1, 1), up = new THREE.Vector3(0, 1, 0), v3 = new THREE.Vector3();
    for (let i = 0; i < 2; i++) slots.setMatrixAt(i, m4.makeTranslation(WHEEL_X[i], DECK_TOP + 0.02, WHEEL_Z));
    group.add(slots, wheels, tyres, wheelIdx);
    const setWheel = (i, angle) => {
      q.setFromEuler(e.set(angle, 0, 0));
      m4.compose(p3.set(WHEEL_X[i], WHEEL_Y, WHEEL_Z), q, s3.set(1, 1, 1));
      wheels.setMatrixAt(i, m4);
      tyres.setMatrixAt(i, m4);
      v3.set(0, WHEEL_R + 0.025, 0).applyQuaternion(q);
      wheelIdx.setMatrixAt(i, m4.compose(p3.set(WHEEL_X[i] + v3.x, WHEEL_Y + v3.y, WHEEL_Z + v3.z), q, s3));
    };
    setWheel(0, 0); setWheel(1, 0);

    // walnut end cheeks: a side profile with a top edge sloping down toward the player
    const cheekShape = new THREE.Shape();
    {
      const zf = FRONT + 0.15, zr = REAR, yb = BOTTOM, yRear = 1.4, yFront = 0.24, r = 0.28;
      cheekShape.moveTo(zf - r, yb);
      cheekShape.lineTo(zr + r, yb);
      cheekShape.quadraticCurveTo(zr, yb, zr, yb + r);
      cheekShape.lineTo(zr, yRear - r);
      cheekShape.quadraticCurveTo(zr, yRear, zr + r, yRear);
      cheekShape.lineTo(zf - 0.75, yFront);
      cheekShape.quadraticCurveTo(zf, yFront, zf, yFront - 0.75);
      cheekShape.lineTo(zf, yb + r);
      cheekShape.quadraticCurveTo(zf, yb, zf - r, yb);
    }
    const extrudeSide = (shape, thickness) => {
      const geo = own(new THREE.ExtrudeGeometry(shape, { depth: thickness - 0.12, bevelEnabled: true, bevelThickness: 0.06,
        bevelSize: 0.06, bevelSegments: 2, curveSegments: 10 }));
      geo.translate(0, 0, -(thickness - 0.12) / 2);
      geo.rotateY(-Math.PI / 2);             // shape x -> world z, extrusion -> world x
      // planar UVs along the grain: world z and y
      const pos = geo.getAttribute("position"), uv = geo.getAttribute("uv");
      for (let i = 0; i < pos.count; i++) uv.setXY(i, pos.getY(i) * 0.09 + pos.getX(i) * 0.02, pos.getZ(i) * 0.05);
      uv.needsUpdate = true;
      return geo;
    };
    const cheekGeo = extrudeSide(cheekShape, CHEEK_T);
    addMesh(cheekGeo, walnut, innerL - CHEEK_T / 2, 0, 0);
    addMesh(cheekGeo, walnut, innerR + CHEEK_T / 2, 0, 0);

    // rubber feet
    const feet = new THREE.InstancedMesh(own(new THREE.CylinderGeometry(0.32, 0.36, 0.1, 16)), rubber, 4);
    [[innerL + 0.8, FRONT - 1.2], [innerR - 0.8, FRONT - 1.2], [innerL + 0.8, REAR + 1.2], [innerR - 0.8, REAR + 1.2]]
      .forEach(([x, z], i) => feet.setMatrixAt(i, m4.makeTranslation(x, floorY + 0.05, z)));
    group.add(feet);

    // hinge rod
    const hingeGeo = own(new THREE.CylinderGeometry(0.11, 0.11, innerW + 0.2, 16));
    hingeGeo.rotateZ(Math.PI / 2);
    addMesh(hingeGeo, chrome, cx, HINGE.y, HINGE.z);

    // kickstand: a unit rod scaled to the distance between its foot on the case and its seat under the panel
    const standGeo = own(new THREE.CylinderGeometry(0.07, 0.07, 1, 10));
    standGeo.translate(0, 0.5, 0);
    const stands = new THREE.InstancedMesh(standGeo, chrome, 2);
    group.add(stands);
    const STAND_FOOT_Z = HINGE.z - 5.6, STAND_SEAT = 6.4, STAND_X = [cx - innerW * 0.3, cx + innerW * 0.3];

    // --------------------------------------------------------- the panel --
    addMesh(box(innerW, PT, PD, 0.12), body, 0, PT / 2, -PD / 2, panel);
    const faceGeo = own(new THREE.PlaneGeometry(FW, FH));
    faceGeo.rotateX(-Math.PI / 2);
    addMesh(faceGeo, faceMat, 0, PT + 0.004, -PD / 2, panel);
    const panelShape = new THREE.Shape();
    {
      const z0 = 0.35, z1 = -PD - 0.12, y0 = -0.35, y1 = PT + 0.32, r = 0.45;
      panelShape.moveTo(z0 - r, y0);
      panelShape.lineTo(z1 + r, y0);
      panelShape.quadraticCurveTo(z1, y0, z1, y0 + r);
      panelShape.lineTo(z1, y1 - r);
      panelShape.quadraticCurveTo(z1, y1, z1 + r, y1);
      panelShape.lineTo(z0 - r, y1);
      panelShape.quadraticCurveTo(z0, y1, z0, y1 - r);
      panelShape.lineTo(z0, y0 + r);
      panelShape.quadraticCurveTo(z0, y0, z0 - r, y0);
    }
    const panelCheekGeo = extrudeSide(panelShape, CHEEK_T);
    addMesh(panelCheekGeo, walnut, innerL - CHEEK_T / 2 - cx, 0, 0, panel);
    addMesh(panelCheekGeo, walnut, innerR + CHEEK_T / 2 - cx, 0, 0, panel);

    // knobs: skirted black body, a brushed cap, a white pointer line
    const knobGeo = own(new THREE.LatheGeometry([
      new THREE.Vector2(0.64, 0.0), new THREE.Vector2(0.66, 0.04), new THREE.Vector2(0.66, 0.13),
      new THREE.Vector2(0.52, 0.19), new THREE.Vector2(0.43, 0.23), new THREE.Vector2(0.41, 0.56),
      new THREE.Vector2(0.385, 0.62), new THREE.Vector2(0.33, 0.645), new THREE.Vector2(0.0, 0.65),
    ], 32));
    const capGeo = own(new THREE.CylinderGeometry(0.3, 0.3, 0.03, 32));
    capGeo.translate(0, 0.66, 0);
    const pointerGeo = own(new THREE.BoxGeometry(0.06, 0.02, 0.36));
    pointerGeo.translate(0, 0.69, -0.2);
    const N_KNOBS = KNOBS.length;
    const knobs = new THREE.InstancedMesh(knobGeo, knobMat, N_KNOBS);
    const caps = new THREE.InstancedMesh(capGeo, metal, N_KNOBS);
    const pointers = new THREE.InstancedMesh(pointerGeo, pointerMat, N_KNOBS);
    panel.add(knobs, caps, pointers);
    const knobAngle = new Float32Array(N_KNOBS);
    const setKnob = (i, value01) => {
      const [u, v, , s] = KNOBS[i];
      const a = (-150 + 300 * clamp(value01, 0, 1)) * Math.PI / 180;
      knobAngle[i] = value01;
      q.setFromAxisAngle(up, -a);
      m4.compose(p3.set(faceX(u), PT, faceZ(v)), q, s3.set(s, s, s));
      knobs.setMatrixAt(i, m4); caps.setMatrixAt(i, m4); pointers.setMatrixAt(i, m4);
    };
    for (let i = 0; i < N_KNOBS; i++) setKnob(i, KNOBS[i][4]);

    // rocker switches: a black bezel and a coloured rocker tipped on or off
    const bezelGeo = box(0.62, 0.12, 1.02, 0.04, 2);
    bezelGeo.translate(0, 0.06, 0);
    const rockerGeo = box(0.46, 0.22, 0.86, 0.06, 2);
    const N_ROCK = ROCKERS.length;
    const bezels = new THREE.InstancedMesh(bezelGeo, knobMat, N_ROCK);
    const rockers = new THREE.InstancedMesh(rockerGeo, rockerMat, N_ROCK);
    const rc = new THREE.Color();
    ROCKERS.forEach(([u, v, , col, on], i) => {
      bezels.setMatrixAt(i, m4.makeTranslation(faceX(u), PT, faceZ(v)));
      q.setFromEuler(e.set(on ? 0.2 : -0.2, 0, 0));
      rockers.setMatrixAt(i, m4.compose(p3.set(faceX(u), PT + 0.16, faceZ(v)), q, s3.set(1, 1, 1)));
      rockers.setColorAt(i, rc.set(col));
    });
    panel.add(bezels, rockers);

    // lamps: a chrome bezel ring and a jewel lens
    const ringGeo = own(new THREE.TorusGeometry(0.25, 0.06, 8, 24));
    ringGeo.rotateX(Math.PI / 2);
    ringGeo.translate(0, 0.05, 0);
    const lensGeo = own(new THREE.SphereGeometry(0.22, 20, 10, 0, TAU, 0, Math.PI / 2));
    lensGeo.scale(1, 0.75, 1);
    const N_LAMPS = LAMPS.length;
    const rings = new THREE.InstancedMesh(ringGeo, chrome, N_LAMPS);
    const lenses = new THREE.InstancedMesh(lensGeo, lensMat, N_LAMPS);
    const off = new THREE.Color(0, 0, 0);
    LAMPS.forEach(([u, v, , s], i) => {
      m4.compose(p3.set(faceX(u), PT, faceZ(v)), q.identity(), s3.set(s, s, s));
      rings.setMatrixAt(i, m4);
      lenses.setMatrixAt(i, m4);
      lenses.setColorAt(i, off);
    });
    lenses.instanceColor.setUsage(THREE.DynamicDrawUsage);
    panel.add(rings, lenses);

    // Instanced bounding spheres are computed once from the static layout (the kickstand's is refreshed with the tilt).
    for (const im of [slots, wheels, tyres, wheelIdx, feet, knobs, caps, pointers, bezels, rockers, rings, lenses]) im.computeBoundingSphere();
    wheelIdx.boundingSphere.radius += 1.2;   // the index marks roll around the wheel rims

    // ---------------------------------------------------------- reactive --
    const lamp = new Float32Array(12);        // strike peak per pitch class, 0..1
    const lampHeld = new Float32Array(12);    // held level per pitch class this frame
    const lampMidi = new Int16Array(12).fill(60);
    let ladder = 0, ladderHold = 0, ladderHoldT = -1e9, ladderMidi = 60, ladderVel = 0;
    let pedalLvl = 0, chordLvl = 0, pilot = 0.1, lastActivity = -1e9, lastStrikeT = -Infinity;
    let env = 0, heldCount = 0, modWheel = 0, modWheelShown = 0, cutoffShown = -1, contourShown = -1;
    let tilt = 44 * Math.PI / 180, tiltTarget = tilt, tiltShown = -1, active = true;
    const col = new THREE.Color(), col2 = new THREE.Color();

    // Lamp radiance for a note: its hue at full saturation, lifted toward a common luminance so a violet lamp flashes as
    // hard as a yellow one, times the level. Peaks cross the host's bloom threshold (0.9), holds and idles stay below it.
    const LAMP_GAIN = 10;
    const lampColor = (midi, vel, level, target) => {
      noteColor(midi, vel, target);
      const mx = Math.max(target.r, target.g, target.b, 1e-4);
      target.multiplyScalar(1 / mx);
      const lum = 0.2126 * target.r + 0.7152 * target.g + 0.0722 * target.b;
      const lift = clamp(Math.pow(0.4 / Math.max(lum, 0.02), 0.55), 1, 3.2);
      return target.multiplyScalar(level * LAMP_GAIN * lift * 0.5);
    };

    const heldVisit = (p, m) => {
      const pc = ((m % 12) + 12) % 12;
      const lvl = 0.16 + 0.18 * clamp((p?.vel ?? 90) / 127, 0, 1);
      if (lvl > lampHeld[pc]) { lampHeld[pc] = lvl; lampMidi[pc] = m; }
      heldCount++;
    };

    function placeStands() {
      const st = Math.sin(tilt), ct = Math.cos(tilt);
      // seat under the panel, in world space: along the panel's underside from the hinge
      const sy = HINGE.y + STAND_SEAT * st, sz = HINGE.z - STAND_SEAT * ct;
      const fy = HINGE.y - 0.12, fz = STAND_FOOT_Z;
      const dy = sy - fy, dz = sz - fz, len = Math.hypot(dy, dz);
      q.setFromUnitVectors(up, v3.set(0, dy / len, dz / len));
      for (let i = 0; i < 2; i++) stands.setMatrixAt(i, m4.compose(p3.set(STAND_X[i], fy, fz), q, s3.set(1, len, 1)));
      stands.instanceMatrix.needsUpdate = true;
      stands.computeBoundingSphere();
    }

    function update(dt, t, state) {
      if (!active) return;
      dt = clamp(dt || 0, 0, 0.1);
      // panel tilt
      tilt = damp(tilt, tiltTarget, 0.5, dt);
      if (Math.abs(tilt - tiltShown) > 1e-5) {
        panel.rotation.x = tilt;
        tiltShown = tilt;
        placeStands();
      }

      // new strikes
      const notes = state?.notes;
      if (notes && notes.length) {
        let maxT = lastStrikeT;
        for (let i = 0; i < notes.length; i++) {
          const n = notes[i];
          if (n.t > t + 1) continue;
          if (n.t > lastStrikeT) {
            const pc = ((n.midi % 12) + 12) % 12, v = clamp(n.vel / 127, 0, 1);
            if (v >= lamp[pc] * 0.8) { lamp[pc] = Math.max(lamp[pc], v); lampMidi[pc] = n.midi; }
            if (v >= ladder || t - ladderHoldT > 0.25) { ladderMidi = n.midi; ladderVel = n.vel; }
            ladder = Math.max(ladder, v);
            if (v >= ladderHold || t - ladderHoldT > 0.9) { ladderHold = v; ladderHoldT = t; }
            env = Math.max(env, v);
            lastActivity = t;
            if (n.t > maxT) maxT = n.t;
          }
        }
        lastStrikeT = maxT;
      }
      if (notes && notes.length === 0 && lastStrikeT > t + 1) lastStrikeT = -Infinity;  // the clock was reset

      // held keys
      lampHeld.fill(0);
      heldCount = 0;
      if (state?.pressed && state.pressed.size) state.pressed.forEach(heldVisit);
      if (heldCount) lastActivity = t;

      // decays
      const kPeak = Math.exp(-dt / 0.3);
      const attr = lenses.instanceColor;
      for (let pc = 0; pc < 12; pc++) {
        lamp[pc] *= kPeak;
        const lvl = Math.max(lamp[pc], lampHeld[pc]);
        if (lvl < 0.003) attr.setXYZ(pc, 0, 0, 0);
        else { lampColor(lampMidi[pc], 100, lvl, col); attr.setXYZ(pc, col.r, col.g, col.b); }
      }
      ladder = Math.max(0, ladder - dt * 0.55);
      if (t - ladderHoldT > 1.1) ladderHold = Math.max(0, ladderHold - dt * 0.8);
      lampColor(ladderMidi, ladderVel, 1, col2);
      for (let i = 0; i < LADDER_N; i++) {
        const threshold = (i + 0.5) / LADDER_N;
        let lvl = clamp((ladder - threshold) * LADDER_N + 0.5, 0, 1) * (0.45 + 0.55 * (i + 1) / LADDER_N);
        const holdIdx = Math.min(LADDER_N - 1, Math.floor(ladderHold * LADDER_N - 0.001));
        if (ladderHold > 0.05 && i === holdIdx) lvl = Math.max(lvl, 0.9);
        attr.setXYZ(LADDER0 + i, col2.r * lvl, col2.g * lvl, col2.b * lvl);
      }
      pedalLvl = damp(pedalLvl, state?.pedal ? 1 : 0, state?.pedal ? 0.04 : 0.2, dt);
      col.setRGB(1.0, 0.42, 0.08).multiplyScalar(pedalLvl * 1.6);
      attr.setXYZ(LAMP_PEDAL, col.r, col.g, col.b);
      chordLvl = damp(chordLvl, state?.chord ? 1 : 0, state?.chord ? 0.06 : 0.35, dt);
      lampColor(ladderMidi, 100, chordLvl * 0.7, col);
      attr.setXYZ(LAMP_CHORD, col.r, col.g, col.b);
      pilot = damp(pilot, t - lastActivity < 3 ? 0.5 : 0.1, 0.6, dt);
      col.setRGB(1.0, 0.18, 0.06).multiplyScalar(pilot);
      attr.setXYZ(LAMP_PILOT, col.r, col.g, col.b);
      attr.needsUpdate = true;

      // filter envelope on the CUTOFF and CONTOUR knobs, mod wheel with the held keys
      env = heldCount ? damp(env, 0.35, 0.7, dt) : damp(env, 0, 0.45, dt);
      const cutoff = KNOBS[KNOB_CUTOFF][4] + 0.5 * env, contour = KNOBS[KNOB_CONTOUR][4] + 0.35 * env;
      let dirty = false;
      if (Math.abs(cutoff - cutoffShown) > 1e-4) { setKnob(KNOB_CUTOFF, cutoff); cutoffShown = cutoff; dirty = true; }
      if (Math.abs(contour - contourShown) > 1e-4) { setKnob(KNOB_CONTOUR, contour); contourShown = contour; dirty = true; }
      if (dirty) { knobs.instanceMatrix.needsUpdate = caps.instanceMatrix.needsUpdate = pointers.instanceMatrix.needsUpdate = true; }
      modWheel = damp(modWheel, -clamp(heldCount / 8, 0, 1) * 0.9, 0.35, dt);
      if (Math.abs(modWheel - modWheelShown) > 1e-4) {
        setWheel(1, modWheel);
        modWheelShown = modWheel;
        wheels.instanceMatrix.needsUpdate = tyres.instanceMatrix.needsUpdate = wheelIdx.instanceMatrix.needsUpdate = true;
      }
    }

    function resize(framing) {
      // The player view (9:16) looks down from high above the keys, so the panel stands steeper there (50 degrees, 10 up
      // from the first build) to face that camera and keep the legend legible; 16:9 keeps 48.
      const f = typeof framing === "function" ? framing() : framing;
      tiltTarget = (f && f.id === "9:16" ? 50 : 48) * Math.PI / 180;
    }

    function setActive(on) {
      active = !!on;
      group.visible = active;
    }

    function dispose() {
      disposed = true;
      if (group.parent) group.parent.remove(group);
      group.traverse((o) => { if (o.isInstancedMesh) o.dispose(); });
      for (const d of disposables) d.dispose?.();
    }

    // A lab close-up (not per frame): a little in front of the Modifiers and Output sections, looking at the lamps.
    function closeView() {
      group.updateMatrixWorld(true);
      const target = panel.localToWorld(new THREE.Vector3(faceX(0.8), PT, faceZ(0.5)));
      const normal = new THREE.Vector3(0, Math.cos(tilt), Math.sin(tilt)).transformDirection(group.matrixWorld);
      const from = target.clone().addScaledVector(normal, 15).add(new THREE.Vector3(-4.5, 1.5, 6));
      return { target: target.toArray(), from: from.toArray(), fov: 30 };
    }
    // A lab hero: three-quarter from the front left, the whole body in frame. Arguments are for receipts only.
    // Yaw -40, not -34: at -34 the host's rim light (12, 16, -30) mirrors off the low white keys' clearcoat straight into
    // this camera (HDR probe: left-6-key peak 3.81 at -34, 0.39 with the rim light off, 0.68 at -38, 0.51 at -42).
    const HERO_YAW = -40, HERO_ELEV = 24;
    function heroView(yawDeg = HERO_YAW, elevDeg = HERO_ELEV) {
      group.updateMatrixWorld(true);
      const target = group.localToWorld(new THREE.Vector3(cx + 1.0, 0.0, -5.2));
      const yaw = yawDeg * Math.PI / 180, elev = elevDeg * Math.PI / 180, dist = 84;
      const from = target.clone().add(new THREE.Vector3(dist * Math.sin(yaw) * Math.cos(elev), dist * Math.sin(elev),
        dist * Math.cos(yaw) * Math.cos(elev)));
      return { target: target.toArray(), from: from.toArray(), fov: 23 };
    }

    resize(ctx.framing);
    tilt = tiltTarget;
    placeStands();
    panel.rotation.x = tilt; tiltShown = tilt;
    if (scene) scene.add(group);

    return { group, update, resize, setActive, dispose, panel,
      views: { close: closeView, hero: heroView },
      info: { keySpan: { first, last }, face: FACE, width: innerW + 2 * CHEEK_T, depth: FRONT - REAR, knobs: N_KNOBS, rockers: N_ROCK, lamps: N_LAMPS } };
  },
};
export default DEF;
