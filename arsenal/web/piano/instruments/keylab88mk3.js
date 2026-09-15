// KeyLab 88 mk3 — arsenal/web/piano/instruments/keylab88mk3.js  (ES module, a piano instrument)
//
// Daniel's controller, built procedurally around the host's 88-key row. The host owns the keys, camera, bloom and stage;
// this module owns the chassis, end cheeks, top panel and its controls, and the two things that react: the 12 pads and
// the screen. No imports: everything comes through ctx, like the scheme host.
//
// Proportions come from the research spec (scratchpad instruments/spec.md, section 1). Firm [M]: 1295 x 323 x 113 mm, 88 keys,
// 150 mm white keys, 165 mm octave; 12 RGB pads at 29 mm; 3.5 in 480x320 screen; 8 contextual buttons, a clickable main
// encoder and Back; 9 encoders and 9 faders (50 mm); 12 transport/command buttons; Chord/Scale/Arp/Hold; Oct and Trans
// +/-; Prog, Settings, Bank +/-; pitch and mod wheels on the top panel far left; wood end cheeks. Positions along the panel
// are [U] estimates (spec 1.3), so every one of them is a named millimetre constant in LAYOUT below: a tape-measure pass on
// the real unit (spec 1.6) edits numbers, not code. No brand lettering or logo anywhere on the model.
//
// Units: the host's world unit is one white-key pitch. Millimetres convert with MM = pitch / (165 / 7), taken from keyX, so
// the body follows whatever key span the host draws. Lighting is environment-free: every material reads under the host's
// hemisphere, key and rim lights, and only the pads, the button LEDs and the screen emit (the pads only while reacting).
//
// ctx: { THREE, scene, keyX, isBlack, KEY {first,last}, noteColor(midi, vel, target), framing,
//        keySpan? {x0, x1, top, back, front, whiteH}, RoundedBoxGeometry?, fonts? {display}, options? {edition: "black"|"white"} }
// returns { group, update(dt, t, state), resize(framing), setActive(on), dispose(), keyStyle, stage: {floorY}, stats() }
// state: { pressed: Map midi -> {vel, t0}, pedal, chord: {name, nns, key} | null, notes: [{midi, vel, t}] }

const OCTAVE_MM = 165;            // [R] SOS, TP/110
const CHASSIS = { w: 1295, d: 323, cheek: 34.65 };  // [M] 1295 x 323; cheek = (1295 - 52 whites) / 2 [D]
const H = {                        // heights in mm relative to the white key top (0). [U] fitted to the 113 mm envelope
  floor: -78, baseTop: -28, panel: 13, plate: 1.5, button: 4.5, pad: 5, knob: 16, encoder: 17, fader: 11,
  cheekFront: 90, cheekRear: 113,  // cheek top edge above the spec desk (H.floor): sloped, sculpted [U: judge estimate]
};
// x: mm from the chassis' left outer edge; z: mm from the chassis front edge (toward the back).
const LAYOUT = {
  // wheels: rubber cylinders, axis along x, sunk into the well so only the top `show` fraction of the diameter is above the plate
  wheels: { x: [62, 97], z: 245, r: 16, w: 18, show: 0.4, well: { x: 79.5, z: 245, w: 70, d: 48 } },
  global: { x: [140, 166, 192, 218], zBack: 276, zFront: 214, w: 20, d: 11 },   // Prog Settings Bank- Bank+ / Oct- Oct+ Trans- Trans+
  pads: { x0: 306.5, pitch: 33, zFront: 212, zBack: 245, size: 29 },            // 2 x 6 [U]; front row = C..F, back row = F#..B
  fx: { x: [314.75, 364.25, 413.75, 463.25], z: 286, w: 30, d: 9 },              // Chord Scale Arp Hold, behind the pads
  // transport + command: 2 rows of 6 on the pad rows' z; the front row's Stop / Play / Rec are `wide` x wider, and the back
  // row's buttons sit on the front row's centres (x from x0, left to right)
  transport: { x0: 498, gap: 2.9, w: 13, wide: 1.4, zBack: 245, dBack: 11, zFront: 212, dFront: 14 },
  screen: { x: 660, z: 250, w: 74, d: 49.3, bezelW: 86, bezelD: 60 },           // 3.5 in 480x320 active area [D]
  ctxButtons: { x: [631.5, 650.5, 669.5, 688.5], zFront: 212, zBack: 289, w: 15, d: 8 },
  encoder: { x: 728, z: 256, r: 15 }, back: { x: 728, z: 207, w: 18, d: 8 },
  // strips: 50 mm travel in a 62 mm slot; the knob row sits 8 mm (skirt edge to slot end) behind the slot
  strips: { x0: 853.5, pitch: 47, knobZ: 294, knobR: 9, faderZ: 246, travel: 50, slot: 62 },
  separators: { x: [125, 244, 494, 610, 783], z0: 182, z1: 310 },
  faders: [0.72, 0.64, 0.8, 0.55, 0.68, 0.9, 0.6, 0.5, 0.78],   // a static mix, 0 = front (toward the player)
  knobs: [-0.6, 0.2, -1.4, 0.9, 2.1, -2.2, 0.4, 1.3, -0.9],     // pointer angles, radians from straight back
};
// panel: the control plate's surface. seam: a 1 mm lighter bevel line on the zone seams (null = the faint printed line).
const EDITIONS = {
  black: { body: 0x0b0c0f, plate: 0x23262c, trim: 0x3a3d45, wood: 0x3b2619, rubber: 0x131417, button: 0x1d1f24,
           pad: 0x121317, mark: 0.42, markColor: 0xc9ced8, felt: 0x0d0d10, whiteKey: 0xe6e4de, blackKey: 0x0e0e11,
           bodyMat: { roughness: 0.58, clearcoat: 0.12, clearcoatRoughness: 0.55 },
           panel: { roughness: 0.5, metalness: 0.2, clearcoat: 0.35, clearcoatRoughness: 0.32, sheen: 0.35, sheenRoughness: 0.45 },
           seam: "#3a3f47", fill: 2.2, soft: 1 },
  // white: albedo held down and the surface kept matte, so the plate stays under the bloom threshold (0.9) in the key light
  white: { body: 0xc9c9c5, plate: 0xcfcfcb, trim: 0xa9adb5, wood: 0xd2ad82, rubber: 0xdcdde0, button: 0xd4d5d8,
           pad: 0x2a2c31, mark: 0.35, markColor: 0x2a2d33, felt: 0x2b2c30, whiteKey: 0xeceae4, blackKey: 0x101013,
           bodyMat: { roughness: 0.62, clearcoat: 0, specularIntensity: 0.4 },
           panel: { roughness: 0.6, metalness: 0, clearcoat: 0, specularIntensity: 0.35, sheen: 0 },
           seam: null, fill: 0.35, soft: 0.35 },   // already bright: a small fill keeps the plate under the bloom threshold
};
const LED_ROLE = { plain: 0, rec: 1, play: 2, loop: 3, hold: 4, chord: 5, oct: 6, ctx: 7, stop: 8 };
const SCREEN_ON = 0.92, SCREEN_IDLE = 0.46;   // screen brightness: lit, and idle at 50%
// Lettering: Daniel's picks (Google Fonts, OFL). Outfit by default; ctx.options.font or ?font=raleway|jost picks an alternate.
// The host page loads the faces (a Google Fonts link); nothing is drawn in a fallback face while they load.
const FONT_CHOICES = { outfit: "Outfit", raleway: "Raleway", jost: "Jost" };
// Per-view studio profile. The 9:16 player camera sits ~190 units out, inside the host fog (95..280), which halves the
// instrument toward black; the phone profile keeps a share of that fog off this model and adds a soft top reflection
// (a satin panel reads by what it reflects), a key fill, a cool edge rim, and brighter idle LEDs and pad rims.
// fogLit / fogEmit: the share of the host fog applied (1 = all). soft: analytic soft-box reflection. keyFill: an extra
// Lambert key (x ED.fill). rim: Fresnel edge light. The 16:9 views keep the judged look plus a faint rim.
const PROFILE = {
  wide:  { fogLit: 1, fogEmit: 1, soft: 0, keyFill: 0, rim: 0.3, ledIdle: 0.06, padRimIdle: 0.012, phone: false },
  phone: { fogLit: 0.4, fogEmit: 0.25, soft: 1, keyFill: 1, rim: 1, ledIdle: 0.14, padRimIdle: 0.05, phone: true },
};

const decay = (tau, dt) => Math.exp(-dt / Math.max(tau, 1e-4));

export default {
  id: "keylab88mk3",
  name: "KeyLab 88 mk3",
  // static hint for hosts that style keys before create(): the black edition's keys (create() returns the edition's own)
  keyStyle: { whiteColor: EDITIONS.black.whiteKey, blackColor: EDITIONS.black.blackKey, capHeight: null, frontLip: 0 },

  create(ctx) {
    const { THREE, keyX, isBlack } = ctx;
    const doc = ctx.document || globalThis.document;
    // edition: ctx.options.edition, else a ?edition=white URL parameter (the lab passes no options), else black
    let urlEdition = null, urlFont = null;
    try {
      const q = new URLSearchParams(globalThis.location?.search || "");
      urlEdition = q.get("edition"); urlFont = q.get("font");
    } catch { /* no location */ }
    const opts = ctx.options || {};
    const ED = EDITIONS[(opts.edition || urlEdition) === "white" ? "white" : "black"];
    const FAMILY = FONT_CHOICES[String(opts.font || urlFont || "outfit").toLowerCase()] || FONT_CHOICES.outfit;
    const RB = ctx.RoundedBoxGeometry || null;

    // ------------------------------------------------------------------ span --
    // Always an 88-key chassis, A0..C8, whatever part of the row the host shows.
    const pitch = (keyX(108) - keyX(21)) / 51;
    const MM = pitch / (OCTAVE_MM / 7);
    const ks = ctx.keySpan || ctx.span || {};
    const num = (...v) => v.find((x) => Number.isFinite(x));
    const keyTop = num(ks.top, ks.keyTop, 0);
    const keyBack = num(ks.back, ks.keyBack, -3.1 * pitch);
    const keyFront = num(ks.front, ks.keyFront, 3.1 * pitch);
    const xLeft = keyX(21) - pitch / 2 - CHASSIS.cheek * MM;        // chassis outer left edge
    const zFront = keyFront + 2 * MM;                              // chassis front edge, keys nearly flush
    const X = (mm) => xLeft + mm * MM;
    const Z = (mm) => zFront - mm * MM;
    const Y = (mm) => keyTop + mm * MM;
    const zBack = Z(CHASSIS.d);
    const zPanelFace = keyBack - 3 * MM;
    const zChamfer = zPanelFace - 20 * MM;
    const innerX0 = X(CHASSIS.cheek), innerX1 = X(CHASSIS.w - CHASSIS.cheek), innerW = innerX1 - innerX0;
    const yPlate = Y(H.panel + H.plate);                           // top surface of the control plate
    // The desk: the host's floor when it gives one (piano.js's stage floor is y -2.3, 54 mm under the key tops), so the
    // chassis never sinks through it; the spec estimate (78 mm, stage.floorY below) when it does not.
    const specFloorY = Y(H.floor);
    const floorY = Number.isFinite(ks.floorY) ? Math.min(Y(H.baseTop - 12), ks.floorY) : specFloorY;

    const group = new THREE.Group();
    group.name = "instrument:keylab88mk3";
    const disposables = new Set();
    const keep = (x) => { disposables.add(x); return x; };
    const roundBox = (w, h, d, seg, r) => keep(RB ? new RB(w, h, d, seg, Math.min(r, w / 2, h / 2, d / 2) * 0.999)
                                                  : new THREE.BoxGeometry(w, h, d));
    const add = (geo, mat, x, y, z) => { const m = new THREE.Mesh(geo, mat); m.position.set(x, y, z); group.add(m); return m; };

    // ------------------------------------------------------------- materials --
    const phys = (p) => keep(new THREE.MeshPhysicalMaterial(p));
    const mat = {
      body: phys({ color: ED.body, metalness: 0.0, ...ED.bodyMat }),
      plate: phys({ color: ED.plate, ...ED.panel, sheenColor: new THREE.Color(0x6d7a92) }),
      trim: phys({ color: ED.trim, roughness: 0.3, metalness: 0.7, clearcoat: 0.4, clearcoatRoughness: 0.2 }),
      wood: phys({ color: 0xffffff, roughness: 0.52, metalness: 0.0, clearcoat: 0.45, clearcoatRoughness: 0.38,
                   sheen: 0.25, sheenRoughness: 0.6, sheenColor: new THREE.Color(0xffd7a8) }),
      rubber: phys({ color: ED.rubber, roughness: 0.6, metalness: 0.0, clearcoat: 0.25, clearcoatRoughness: 0.5,
                     sheen: 0.8, sheenRoughness: 0.42, sheenColor: new THREE.Color(0x8d9ab4) }),
      button: phys({ color: ED.button, roughness: 0.42, metalness: 0.0, clearcoat: 0.55, clearcoatRoughness: 0.3,
                     sheen: 0.4, sheenRoughness: 0.5, sheenColor: new THREE.Color(0x7f8aa0) }),
      pad: phys({ color: ED.pad, roughness: 0.55, metalness: 0.0, clearcoat: 0.3, clearcoatRoughness: 0.45,
                  sheen: 0.6, sheenRoughness: 0.5, sheenColor: new THREE.Color(0x9aa6bd) }),
      // wheels: soft matte rubber (the knobs and fader caps keep the satin rubber above)
      wheel: phys({ color: ED.rubber, roughness: 0.8, metalness: 0.0, clearcoat: 0,
                    sheen: 0.45, sheenRoughness: 0.6, sheenColor: new THREE.Color(0x8d9ab4) }),
      // main encoder: neutral bead-blasted aluminium (its glint is also soft-clipped under the bloom threshold, see studio)
      alu: phys({ color: 0xc9ccd1, roughness: 0.36, metalness: 1.0, clearcoat: 0 }),
      bezel: phys({ color: 0x030304, roughness: 0.12, metalness: 0.0, clearcoat: 1.0, clearcoatRoughness: 0.03 }),
      felt: keep(new THREE.MeshStandardMaterial({ color: ED.felt, roughness: 1.0 })),
      slot: keep(new THREE.MeshBasicMaterial({ color: 0x010102 })),
      mark: keep(new THREE.MeshBasicMaterial({ color: new THREE.Color(ED.markColor).multiplyScalar(ED.mark) })),
      glow: keep(new THREE.MeshBasicMaterial({ color: 0xffffff })),   // per-instance HDR colour: LEDs and pad rims
    };
    // Studio: this model's own light, scoped to its materials (no scene lights, so the host's keys and stage are untouched,
    // and no extra draw calls). The shared uniforms are driven by the view profile (resize); the per-material ones say how
    // much of each term a surface takes. Every material gets the same injected code for its shader type, so programs are
    // shared (customProgramCacheKey).
    const STUDIO = {
      uKlFogLit: { value: 1 }, uKlFogEmit: { value: 1 },
      uKlSoft: { value: 0 }, uKlSoftTint: { value: new THREE.Color(0.6, 0.68, 0.84) },
      uKlKeyFill: { value: 0 }, uKlKeyDir: { value: new THREE.Vector3(-0.3, 0.8, 0.52).normalize() },
      uKlRim: { value: 0 }, uKlRimColor: { value: new THREE.Color(0.5, 0.64, 1.0) },
    };
    const STUDIO_PARS = `
uniform float uKlFog; uniform float uKlSoft; uniform vec3 uKlSoftTint; uniform float uKlKeyFill; uniform vec3 uKlKeyDir;
uniform float uKlRim; uniform vec3 uKlRimColor; uniform float uKlRimK; uniform float uKlSoftK; uniform float uKlMaxLum;`;
    const STUDIO_LIGHT = `
{
  vec3 klN = geometryNormal, klV = geometryViewDir;
  float klNV = saturate( dot( klN, klV ) );
  vec3 klKey = normalize( ( viewMatrix * vec4( uKlKeyDir, 0.0 ) ).xyz );
  reflectedLight.directDiffuse += material.diffuseColor * ( RECIPROCAL_PI * uKlKeyFill * saturate( dot( klN, klKey ) ) );
  // soft box: a sky gradient above the desk, seen in the surface's world-space reflection, Schlick-weighted
  vec3 klR = inverseTransformDirection( reflect( -klV, klN ), viewMatrix );
  float klF = 0.04 + 0.96 * pow( 1.0 - klNV, 5.0 );
  reflectedLight.indirectSpecular += uKlSoftTint * ( uKlSoft * uKlSoftK * klF * smoothstep( -0.15, 0.9, klR.y ) );
  // edge rim: Fresnel toward the silhouette (rounded edges, bevels, wheel shoulders)
  reflectedLight.directSpecular += uKlRimColor * ( uKlRim * uKlRimK * pow( 1.0 - klNV, 3.0 ) );
}`;
    // soft knee: luminance above 0.6 x uKlMaxLum is compressed toward uKlMaxLum (the bloom pass keys on luminance)
    const STUDIO_CLIP = `
{
  float klL = dot( gl_FragColor.rgb, vec3( 0.2126, 0.7152, 0.0722 ) ), klK = uKlMaxLum * 0.6;
  if ( klL > klK ) { float klS = uKlMaxLum - klK; gl_FragColor.rgb *= ( klK + klS * ( 1.0 - exp( -( klL - klK ) / klS ) ) ) / klL; }
}`;
    const STUDIO_FOG = `
#ifdef USE_FOG
  #ifdef FOG_EXP2
    float fogFactor = 1.0 - exp( - fogDensity * fogDensity * vFogDepth * vFogDepth );
  #else
    float fogFactor = smoothstep( fogNear, fogFar, vFogDepth );
  #endif
  gl_FragColor.rgb = mix( gl_FragColor.rgb, fogColor, fogFactor * uKlFog );
#endif`;
    const injectStudio = (shader, m) => {
      const k = m.userData.kl;
      Object.assign(shader.uniforms, {
        uKlFog: k.emit ? STUDIO.uKlFogEmit : STUDIO.uKlFogLit, uKlSoft: STUDIO.uKlSoft, uKlSoftTint: STUDIO.uKlSoftTint,
        uKlKeyFill: STUDIO.uKlKeyFill, uKlKeyDir: STUDIO.uKlKeyDir, uKlRim: STUDIO.uKlRim, uKlRimColor: STUDIO.uKlRimColor,
        uKlRimK: k.rimK, uKlSoftK: k.softK, uKlMaxLum: k.maxLum,
      });
      let f = shader.fragmentShader.replace("#include <common>", `#include <common>${STUDIO_PARS}`);
      if (f.includes("#include <lights_fragment_end>")) f = f.replace("#include <lights_fragment_end>", `#include <lights_fragment_end>${STUDIO_LIGHT}`);
      f = f.replace("#include <tonemapping_fragment>", `${STUDIO_CLIP}\n#include <tonemapping_fragment>`)
           .replace("#include <fog_fragment>", STUDIO_FOG);
      shader.fragmentShader = f;
    };
    // per material: rim (x profile rim), soft box (x profile soft x ED.soft), max luminance; emit = takes the emissive fog share
    const studio = (m, { rim = 0, soft = 0, maxLum = 1e4, emit = false } = {}, cacheKey = "keylab88mk3-studio") => {
      m.userData.kl = { rimK: { value: rim }, softK: { value: soft * ED.soft }, maxLum: { value: maxLum }, emit };
      const inner = m.onBeforeCompile && m.onBeforeCompile !== THREE.Material.prototype.onBeforeCompile ? m.onBeforeCompile : null;
      m.onBeforeCompile = (shader, renderer) => { if (inner) inner(shader, renderer); injectStudio(shader, m); };
      m.customProgramCacheKey = () => cacheKey;
    };

    // Pads: dark rubber lit from inside. The per-instance glow is added to the emissive term, so the pad keeps its PBR
    // surface and emits only while a note drives it.
    const PAD_COUNT = 12;
    const padGlowAttr = new THREE.InstancedBufferAttribute(new Float32Array(PAD_COUNT * 3), 3);
    padGlowAttr.setUsage(THREE.DynamicDrawUsage);
    mat.pad.onBeforeCompile = (shader) => {
      shader.vertexShader = shader.vertexShader
        .replace("#include <common>", "#include <common>\nattribute vec3 aGlow;\nvarying vec3 vGlow;")
        .replace("#include <begin_vertex>", "#include <begin_vertex>\nvGlow = aGlow;");
      shader.fragmentShader = shader.fragmentShader
        .replace("#include <common>", "#include <common>\nvarying vec3 vGlow;")
        .replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += vGlow;");
    };
    studio(mat.body, { rim: 0.75, soft: 0.7 });
    studio(mat.plate, { rim: 0.6, soft: 1.2 });
    studio(mat.trim, { rim: 0.3 });
    studio(mat.wood, { rim: 0.6, soft: 0.5 });
    studio(mat.rubber, { rim: 0.3, soft: 0.8 });
    studio(mat.button, { rim: 0.3, soft: 1.3 });
    studio(mat.pad, { rim: 0.25, soft: 1.0 }, "keylab88mk3-pad-glow-studio");
    studio(mat.wheel, { rim: 1.5, soft: 0.7 });   // the shoulders' rim is what makes a sunk wheel read as a wheel
    studio(mat.alu, { maxLum: 0.8 });
    studio(mat.bezel, { rim: 0.2, soft: 0.9 });
    studio(mat.felt);
    studio(mat.slot);
    studio(mat.mark);   // printed paint: the lit fog share
    studio(mat.glow, { emit: true });

    // Wood grain: a seeded canvas, grain running front to back along the cheek.
    const woodTex = (() => {
      const c = doc.createElement("canvas");
      c.width = 1024; c.height = 256;
      const g = c.getContext("2d");
      const base = new THREE.Color(ED.wood);
      const css = (col, k, a) => `rgba(${Math.round(Math.min(1, col.r * k) * 255)},${Math.round(Math.min(1, col.g * k) * 255)},${Math.round(Math.min(1, col.b * k) * 255)},${a})`;
      g.fillStyle = css(base, 1, 1);
      g.fillRect(0, 0, c.width, c.height);
      let seed = 0x6b3a21;
      const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
      for (let i = 0; i < 170; i++) {
        const y0 = rnd() * c.height, amp = 1 + rnd() * 5, freq = 0.002 + rnd() * 0.006, ph = rnd() * 6.28;
        g.strokeStyle = rnd() < 0.55 ? css(base, 0.62 + rnd() * 0.2, 0.18 + rnd() * 0.35) : css(base, 1.18, 0.12 + rnd() * 0.2);
        g.lineWidth = 0.6 + rnd() * 2.2;
        g.beginPath();
        for (let x = 0; x <= c.width; x += 16) {
          const y = y0 + Math.sin(x * freq + ph) * amp + Math.sin(x * freq * 3.1 + ph * 2) * amp * 0.3;
          if (x === 0) g.moveTo(x, y); else g.lineTo(x, y);
        }
        g.stroke();
      }
      const t = keep(new THREE.CanvasTexture(c));
      t.colorSpace = THREE.SRGBColorSpace;
      t.wrapS = t.wrapT = THREE.RepeatWrapping;
      t.repeat.set(1 / (CHASSIS.d * MM), 1 / (120 * MM));
      t.anisotropy = 8;
      return t;
    })();
    mat.wood.map = woodTex;

    // The plate's printed face: zone lines, knob tick arcs, fader scales and generic function labels, drawn in millimetres
    // onto one canvas (no brand text). It carries the plate colour itself, so the face is one opaque lit plane.
    const L = LAYOUT;
    // transport zone: column widths (Stop / Play / Rec wide) and centres, laid left to right from x0
    const TR = L.transport;
    const TRANSPORT = { w: [TR.w, TR.w, TR.w, TR.w * TR.wide, TR.w * TR.wide, TR.w * TR.wide], x: [] };
    for (let i = 0, edge = TR.x0; i < 6; i++) { TRANSPORT.x.push(edge + TRANSPORT.w[i] / 2); edge += TRANSPORT.w[i] + TR.gap; }
    const hostFont = ctx.fonts && ctx.fonts.display;
    const FONT = `"${FAMILY}", ${hostFont ? `${hostFont}, ` : ""}"Outfit", "Jost", "Century Gothic", "Futura", "Avenir Next", "Segoe UI", sans-serif`;
    // Lettering waits for the chosen face (document.fonts), so no fallback face is drawn and then swapped. A face still
    // unavailable after 4 s (offline, no stylesheet on the host page) settles anyway and the fallback stack draws.
    let fontsSettled = !doc.fonts, fontLoaded = false, disposed = false;
    const settleFonts = [];   // redraws to run once the face is ready
    const fontsReady = (fontsSettled ? Promise.resolve(false) : Promise.race([
      (async () => {
        await doc.fonts.ready;
        const sample = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/+-";
        const lists = await Promise.all(["600", "700"].map((w) => doc.fonts.load(`${w} 64px "${FAMILY}"`, sample)));
        return lists.every((l) => l && l.length > 0);
      })(),
      new Promise((res) => globalThis.setTimeout(() => res(false), 4000)),
    ])).catch(() => false).then((ok) => {
      fontsSettled = true; fontLoaded = !!ok;
      if (!disposed) settleFonts.forEach((f) => f());
      return fontLoaded;
    });
    mat.plateFace = phys({ color: 0xffffff, ...ED.panel, sheenColor: new THREE.Color(0x6d7a92) });
    studio(mat.plateFace, { soft: 1.6 });
    // legendCanvas(false): the lit face (plate colour, brushing, ink). legendCanvas(true): ink only on black, used as a faint
    // emissive map on the black edition so printed legends read under environment-free lighting (peak ~0.06 linear, far
    // under the bloom threshold: print, not glow).
    // (reuse: redraw into that canvas and return null, once the font settles)
    const legendCanvas = (inkOnly, reuse) => {
      const px0 = CHASSIS.cheek + 3.5, pw = CHASSIS.w - 2 * CHASSIS.cheek - 7;              // mm, chassis-left based
      const pf = (zFront - (zChamfer - 3 * MM)) / MM + 0.5, pb = CHASSIS.d - 5.5;           // mm from the front
      const c = reuse || doc.createElement("canvas");
      if (!reuse) { c.width = 4096; c.height = 512; }
      const g = c.getContext("2d");
      const sx = c.width / pw, sy = c.height / (pb - pf);
      const cx = (xmm) => (xmm - px0) * sx, cy = (zmm) => (pb - zmm) * sy;
      g.fillStyle = inkOnly ? "#000000" : `#${new THREE.Color(ED.plate).getHexString()}`;
      g.fillRect(0, 0, c.width, c.height);
      let seed = 0x51ab;
      const rnd = () => { seed = (seed * 1664525 + 1013904223) >>> 0; return seed / 4294967296; };
      for (let i = 0; i < 900 && !inkOnly; i++) {  // satin brushing along the width
        g.fillStyle = rnd() < 0.5 ? "rgba(255,255,255,0.022)" : "rgba(0,0,0,0.05)";
        g.fillRect(rnd() * c.width, rnd() * c.height, 80 + rnd() * 900, 1);
      }
      const ink = ED === EDITIONS.white ? "rgba(38,42,50,0.72)" : "rgba(196,203,216,0.62)";
      const faint = ED === EDITIONS.white ? "rgba(38,42,50,0.28)" : "rgba(196,203,216,0.2)";
      g.strokeStyle = ink; g.fillStyle = ink; g.lineCap = "round";
      const label = (text, xmm, zmm, hmm = 2.6) => {
        if (!fontsSettled) return;
        g.save();
        g.translate(cx(xmm), cy(zmm));
        g.scale(1, sy / sx);
        g.font = `600 ${hmm * sx * 1.36}px ${FONT}`;
        if ("letterSpacing" in g) g.letterSpacing = `${0.35 * sx}px`;
        g.textAlign = "center"; g.textBaseline = "middle";
        g.fillText(text, 0, 0);
        g.restore();
      };
      const line = (x0, z0, x1, z1, wmm = 0.35, style = ink) => {
        g.strokeStyle = style; g.lineWidth = wmm * sx;
        g.beginPath(); g.moveTo(cx(x0), cy(z0)); g.lineTo(cx(x1), cy(z1)); g.stroke();
      };
      // zone separators: on the black edition a 1 mm lighter bevel line with a thin shadow beside it (the lit face only)
      for (const x of L.separators.x) {
        if (ED.seam && !inkOnly) {
          line(x + 0.75, L.separators.z0, x + 0.75, L.separators.z1, 0.5, "rgba(0,0,0,0.55)");
          line(x, L.separators.z0, x, L.separators.z1, 1.0, ED.seam);
        } else {
          line(x, L.separators.z0, x, L.separators.z1, 0.5, faint);
        }
      }
      // wheels
      label("PITCH", L.wheels.x[0], L.wheels.well.z - L.wheels.well.d / 2 - 5);
      label("MOD", L.wheels.x[1], L.wheels.well.z - L.wheels.well.d / 2 - 5);
      // global buttons: labels behind each button
      ["PROG", "SETTINGS", "BANK −", "BANK +"].forEach((s, i) => label(s, L.global.x[i], L.global.zBack + L.global.d / 2 + 4.5, 2.2));
      ["OCT −", "OCT +", "TRANS −", "TRANS +"].forEach((s, i) => label(s, L.global.x[i], L.global.zFront + L.global.d / 2 + 4.5, 2.2));
      // MIDI FX row and the pad block frame
      ["CHORD", "SCALE", "ARP", "HOLD"].forEach((s, i) => label(s, L.fx.x[i], L.fx.z + L.fx.d / 2 + 4.5, 2.4));
      {
        const x0 = L.pads.x0 - L.pads.size / 2 - 5, x1 = L.pads.x0 + 5 * L.pads.pitch + L.pads.size / 2 + 5;
        const z0 = L.pads.zFront - L.pads.size / 2 - 5, z1 = L.pads.zBack + L.pads.size / 2 + 5;
        g.strokeStyle = faint; g.lineWidth = 0.45 * sx;
        g.beginPath(); g.roundRect(cx(x0), cy(z1), cx(x1) - cx(x0), cy(z0) - cy(z1), 4 * sx); g.stroke();
        for (let i = 0; i < 12; i++) label(String(i + 1), L.pads.x0 + (i % 6) * L.pads.pitch - L.pads.size / 2 + 2.2,
                                            (i < 6 ? L.pads.zFront : L.pads.zBack) - L.pads.size / 2 - 2.6, 1.8);
      }
      // transport and command: 2 rows of 6
      ["SAVE", "UNDO", "REDO", "METRO", "QUANT", "TAP"].forEach((s, i) => label(s, TRANSPORT.x[i], TR.zBack + TR.dBack / 2 + 4, 2.0));
      ["◀◀", "▶▶", "LOOP", "■", "▶", "●"].forEach((s, i) => label(s, TRANSPORT.x[i], TR.zFront + TR.dFront / 2 + 4.2, i < 3 ? 2.2 : 2.6));
      // screen block: encoder tick ring, BACK
      for (let i = 0; i <= 24; i++) {
        const a = (i / 24) * Math.PI * 2, r0 = L.encoder.r + 2.5, r1 = L.encoder.r + (i % 6 === 0 ? 5 : 4);
        line(L.encoder.x + Math.sin(a) * r0, L.encoder.z + Math.cos(a) * r0, L.encoder.x + Math.sin(a) * r1, L.encoder.z + Math.cos(a) * r1, 0.35, faint);
      }
      label("BACK", L.back.x, L.back.z + L.back.d / 2 + 3.8, 2.0);
      // channel strips: knob tick arcs, channel numbers, fader scales
      for (let i = 0; i < 9; i++) {
        const x = L.strips.x0 + i * L.strips.pitch, kz = L.strips.knobZ;
        for (let k = 0; k <= 10; k++) {
          const a = -2.35 + (k / 10) * 4.7, r0 = L.strips.knobR + 2, r1 = L.strips.knobR + (k === 0 || k === 5 || k === 10 ? 4.2 : 3.2);
          line(x + Math.sin(a) * r0, kz + Math.cos(a) * r0, x + Math.sin(a) * r1, kz + Math.cos(a) * r1, 0.4);
        }
        label(String(i + 1), x, L.strips.faderZ - L.strips.slot / 2 - 4.5, 2.6);   // channel number in front of the slot
        const fz0 = L.strips.faderZ - L.strips.travel / 2, fz1 = L.strips.faderZ + L.strips.travel / 2;
        for (let k = 0; k <= 10; k++) {
          const z = fz0 + (k / 10) * (fz1 - fz0), long = k % 5 === 0 ? 3.4 : 2.0;
          line(x - 4.2, z, x - 4.2 - long, z, 0.35, k % 5 === 0 ? ink : faint);
          line(x + 4.2, z, x + 4.2 + long, z, 0.35, k % 5 === 0 ? ink : faint);
        }
      }
      if (reuse) return null;
      const t = keep(new THREE.CanvasTexture(c));
      t.colorSpace = THREE.SRGBColorSpace;
      t.anisotropy = 16;
      return t;
    };
    mat.plateFace.map = legendCanvas(false);
    if (ED === EDITIONS.black) {
      mat.plateFace.emissiveMap = legendCanvas(true);
      mat.plateFace.emissive = new THREE.Color(1, 1, 1);
      mat.plateFace.emissiveIntensity = 0.3;
    }
    settleFonts.push(() => {
      for (const [tex, inkOnly] of [[mat.plateFace.map, false], [mat.plateFace.emissiveMap, true]]) {
        if (!tex) continue;
        legendCanvas(inkOnly, tex.image);
        tex.needsUpdate = true;
      }
    });

    // --------------------------------------------------------------- chassis --
    // Base tray under the keys, recessed 4 mm behind the key fronts.
    {
      const y0 = floorY + 1 * MM, y1 = Y(H.baseTop), z0 = keyFront - 4 * MM;
      add(roundBox(innerW + 0.5 * MM, y1 - y0, z0 - zBack, 3, 6 * MM), mat.body, (innerX0 + innerX1) / 2, (y0 + y1) / 2, (z0 + zBack) / 2);
    }
    // Panel block behind the keys: a profile (vertical face at the key backs, a chamfer up to the plate, a rounded rear
    // edge) extruded across the width. Shape coordinates are (-z, y); rotateY(pi/2) turns the extrusion axis into +x.
    {
      const s = new THREE.Shape();
      const P = (z, y) => [-z, y];
      const yB = Y(H.baseTop), yT = Y(H.panel), r = 8 * MM;
      s.moveTo(...P(zPanelFace, yB));
      s.lineTo(...P(zPanelFace, Y(2)));
      s.lineTo(...P(zChamfer, yT));
      s.lineTo(...P(zBack + r, yT));
      s.quadraticCurveTo(...P(zBack, yT), ...P(zBack, yT - r));
      s.lineTo(...P(zBack, yB));
      s.lineTo(...P(zPanelFace, yB));
      const geo = keep(new THREE.ExtrudeGeometry(s, { depth: innerW, bevelEnabled: false, curveSegments: 6 }));
      geo.rotateY(Math.PI / 2);
      add(geo, mat.body, innerX0, 0, 0).name = "panel:body";
      // the satin control plate on top (its edges), its printed face (a legend canvas), and a felt strip where the key
      // backs meet the panel face
      const plateD = (zChamfer - 3 * MM) - (zBack + 5 * MM);
      // the box's top stops 0.4 mm under the printed face (0.017 units: clear of depth precision at the page's camera
      // distances), so the face never z-fights it
      const plateH = (H.plate - 0.4) * MM;
      add(roundBox(innerW - 6 * MM, plateH, plateD, 2, 0.6 * MM), mat.plate,
          (innerX0 + innerX1) / 2, Y(H.panel) + plateH / 2, (zChamfer - 3 * MM + zBack + 5 * MM) / 2).name = "panel:plate";
      add(keep(new THREE.PlaneGeometry(innerW - 7 * MM, plateD - 1 * MM).rotateX(-Math.PI / 2)), mat.plateFace,
          (innerX0 + innerX1) / 2, yPlate, (zChamfer - 3 * MM + zBack + 5 * MM) / 2).name = "panel:face";
      add(keep(new THREE.BoxGeometry(innerW, 14 * MM, 1.2 * MM)), mat.felt, (innerX0 + innerX1) / 2, Y(-6), zPanelFace + 0.6 * MM);
    }
    // End cheeks: a sculpted wooden profile with a through slot, bevelled. One geometry, two meshes. The top edge slopes from
    // H.cheekRear above the spec desk at the back to H.cheekFront at the front, with a slight concave sculpt between; the
    // corners are quadratic, their control points on the line itself, so the edge stays tangent-continuous.
    {
      const bs = 2.5 * MM, bt = 2.5 * MM;
      const s = new THREE.Shape();
      const P = (z, y) => [-z, y];
      const zf = zFront + 1 * MM - bs, zb = zBack + bs, yb = floorY + bs;
      const yFrontTop = Y(H.floor + H.cheekFront) - bs, yRearTop = Y(H.floor + H.cheekRear) - bs, r1 = 10 * MM, r2 = 5 * MM;
      const topAt = (z) => yFrontTop + (yRearTop - yFrontTop) * (zf - z) / (zf - zb);   // the straight chord of the top edge
      const sag = 2.5 * MM;
      s.moveTo(...P(zf, yb + r2));
      s.lineTo(...P(zf, yFrontTop - r1));
      s.quadraticCurveTo(...P(zf, yFrontTop), ...P(zf - r1, topAt(zf - r1)));
      {
        const za = zf - r1, zd = zb + r1, zc1 = za + (zd - za) * 0.33, zc2 = za + (zd - za) * 0.67;
        s.bezierCurveTo(...P(zc1, topAt(zc1) - sag), ...P(zc2, topAt(zc2) - sag), ...P(zd, topAt(zd)));
      }
      s.quadraticCurveTo(...P(zb, yRearTop), ...P(zb, yRearTop - r1));
      s.lineTo(...P(zb, yb + r2));
      s.quadraticCurveTo(...P(zb, yb), ...P(zb + r2, yb));
      s.lineTo(...P(zf - r2, yb));
      s.quadraticCurveTo(...P(zf, yb), ...P(zf, yb + r2));
      // the sculpted cutout: a blank stadium slot through the rear half, no lettering [U: shape of the real cutout unmeasured]
      const hA = -(zPanelFace - 24 * MM), hB = -(zBack + 34 * MM), rh = 11 * MM, yc = Y(-4);
      const hole = new THREE.Path();
      hole.moveTo(hA + rh, yc - rh);
      hole.lineTo(hB - rh, yc - rh);
      hole.absarc(hB - rh, yc, rh, -Math.PI / 2, Math.PI / 2, false);
      hole.lineTo(hA + rh, yc + rh);
      hole.absarc(hA + rh, yc, rh, Math.PI / 2, Math.PI * 1.5, false);
      s.holes.push(hole);
      const geo = keep(new THREE.ExtrudeGeometry(s, { depth: CHASSIS.cheek * MM - 2 * bt, bevelEnabled: true, bevelThickness: bt,
                                                      bevelSize: bs, bevelSegments: 3, curveSegments: 20 }));
      geo.rotateY(Math.PI / 2);
      add(geo, mat.wood, xLeft + bt, 0, 0);
      add(geo, mat.wood, innerX1 + bt, 0, 0);
    }

    // -------------------------------------------------------------- controls --
    const M4 = new THREE.Matrix4(), Q = new THREE.Quaternion(), EU = new THREE.Euler(), PV = new THREE.Vector3(), SV = new THREE.Vector3();
    const place = (mesh, i, x, y, z, sx, sy, sz, ry = 0, rx = 0, rz = 0) => {
      PV.set(x, y, z); SV.set(sx, sy, sz); Q.setFromEuler(EU.set(rx, ry, rz)); M4.compose(PV, Q, SV); mesh.setMatrixAt(i, M4);
    };
    const finish = (mesh) => { mesh.instanceMatrix.needsUpdate = true; mesh.computeBoundingBox(); mesh.computeBoundingSphere(); group.add(mesh); return mesh; };

    // Buttons: one instanced body per button, and an LED stripe near its front edge.
    const buttons = [];
    const btn = (xmm, zmm, w, d, role) => buttons.push({ xmm, zmm, w, d, role });
    ["plain", "plain", "plain", "plain"].forEach((r, i) => btn(L.global.x[i], L.global.zBack, L.global.w, L.global.d, r));  // Prog Settings Bank- Bank+
    ["oct", "oct", "plain", "plain"].forEach((r, i) => btn(L.global.x[i], L.global.zFront, L.global.w, L.global.d, r));    // Oct- Oct+ Trans- Trans+
    ["chord", "plain", "plain", "hold"].forEach((r, i) => btn(L.fx.x[i], L.fx.z, L.fx.w, L.fx.d, r));                       // Chord Scale Arp Hold
    TRANSPORT.x.forEach((x) => btn(x, TR.zBack, TR.w, TR.dBack, "plain"));                                                  // Save Undo Redo Metro Quant Tap
    ["plain", "plain", "loop", "stop", "play", "rec"].forEach((r, i) => btn(TRANSPORT.x[i], TR.zFront, TRANSPORT.w[i], TR.dFront, r)); // Rew Fwd Loop Stop Play Rec
    L.ctxButtons.x.forEach((x, i) => btn(x, L.ctxButtons.zBack, L.ctxButtons.w, L.ctxButtons.d, i === 0 ? "ctx" : "plain"));
    L.ctxButtons.x.forEach((x) => btn(x, L.ctxButtons.zFront, L.ctxButtons.w, L.ctxButtons.d, "plain"));
    btn(L.back.x, L.back.z, L.back.w, L.back.d, "plain");
    const unitBox = roundBox(1, 1, 1, 2, 0.16);
    const buttonMesh = new THREE.InstancedMesh(unitBox, mat.button, buttons.length);
    buttons.forEach((b, i) => place(buttonMesh, i, X(b.xmm), yPlate + (H.button / 2) * MM, Z(b.zmm), b.w * MM, H.button * MM, b.d * MM));
    finish(buttonMesh);
    const ledGeo = keep(new THREE.PlaneGeometry(1, 1).rotateX(-Math.PI / 2));
    const ledMesh = new THREE.InstancedMesh(ledGeo, mat.glow, buttons.length);
    const ledRole = new Uint8Array(buttons.length);
    buttons.forEach((b, i) => {
      ledRole[i] = LED_ROLE[b.role];
      place(ledMesh, i, X(b.xmm), yPlate + (H.button + 0.08) * MM, Z(b.zmm) + (b.d / 2 - 2) * MM, b.w * 0.62 * MM, 1, 1.3 * MM);
    });
    ledMesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(buttons.length * 3), 3);
    ledMesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
    finish(ledMesh);
    const ledLevel = new Float32Array(buttons.length);

    // Pads: 2 x 6, pitch class order. Front row (nearest the player) C..F, back row F#..B.
    const padMesh = new THREE.InstancedMesh(roundBox(1, 1, 1, 3, 0.09), mat.pad, PAD_COUNT);
    const rimMesh = new THREE.InstancedMesh(roundBox(1, 1, 1, 2, 0.1), mat.glow, PAD_COUNT);
    for (let pc = 0; pc < PAD_COUNT; pc++) {
      const col = pc % 6, row = pc < 6 ? L.pads.zFront : L.pads.zBack;
      const x = X(L.pads.x0 + col * L.pads.pitch), z = Z(row), s = L.pads.size * MM;
      place(padMesh, pc, x, yPlate + (H.pad / 2 + 0.8) * MM, z, s, H.pad * MM, s);
      place(rimMesh, pc, x, yPlate + 1.6 * MM, z, s + 3 * MM, 3.2 * MM, s + 3 * MM);
    }
    padMesh.geometry.setAttribute("aGlow", padGlowAttr);
    finish(padMesh);
    rimMesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(PAD_COUNT * 3), 3);
    rimMesh.instanceColor.setUsage(THREE.DynamicDrawUsage);
    finish(rimMesh);

    // Wheels: rubber cylinders (axis along x) sunk into a recessed well, far left; only the top 40 % of each rises above the plate.
    {
      const W = L.wheels, r = W.r * MM;
      add(roundBox(W.well.w * MM, 1.2 * MM, W.well.d * MM, 2, 5 * MM), mat.slot, X(W.well.x), yPlate + 0.2 * MM, Z(W.well.z));
      // A moulded tyre: a lathe profile (cap centre, a rounded 2.5 mm shoulder, the tread, the other shoulder, cap centre)
      // so the edges catch the key light and the studio edge rim, and the sunk wheel reads as round rather than as a block.
      const hw = (W.w / 2) * MM, rs = 2.5 * MM, prof = [[0, -hw]];
      for (let s = 0; s <= 4; s++) { const a = (s / 4) * Math.PI / 2; prof.push([r - rs + rs * Math.sin(a), -hw + rs - rs * Math.cos(a)]); }
      for (let s = 0; s <= 4; s++) { const a = (s / 4) * Math.PI / 2; prof.push([r - rs + rs * Math.cos(a), hw - rs + rs * Math.sin(a)]); }
      prof.push([0, hw]);
      const wheelGeo = keep(new THREE.LatheGeometry(prof.map(([a, b]) => new THREE.Vector2(a, b)), 48));
      // Moulded grip ribs across the tread (28 around), so the shallow visible arc still reads as a turning wheel. The ribs
      // sit in the canvas' upper half; the tread's two profile rings map into it and the shoulders and caps into the plain
      // lower half, so this stays one draw call.
      {
        const c = doc.createElement("canvas");
        c.width = 280; c.height = 32;
        const g = c.getContext("2d");
        g.fillStyle = "#ffffff"; g.fillRect(0, 0, c.width, c.height);
        g.fillStyle = "#6a6a6a";
        for (let i = 0; i < 28; i++) g.fillRect(i * 10, 0, 3, 15);
        const t = keep(new THREE.CanvasTexture(c));
        t.colorSpace = THREE.SRGBColorSpace;
        t.wrapS = THREE.RepeatWrapping;
        t.anisotropy = 8;
        mat.wheel.map = t;
        const n = prof.length, V = prof.map((_, j) => (j === 5 ? 0.62 : j === 6 ? 0.94 : 0.2));   // j 5, 6: the tread rings
        const uv = wheelGeo.attributes.uv;
        for (let k = 0; k < uv.count; k++) uv.setY(k, V[k % n]);
      }
      wheelGeo.rotateZ(Math.PI / 2);
      const wheels = new THREE.InstancedMesh(wheelGeo, mat.wheel, 2);
      const marks = new THREE.InstancedMesh(unitBox, mat.mark, 2);
      const yc = yPlate + (2 * W.r * W.show - W.r) * MM;   // axis height: top of the tread at 0.4 x diameter above the plate
      W.x.forEach((xm, i) => {
        // a thin index line across the tread: at the top of the pitch wheel (centred), a little forward on the mod wheel
        const a = i === 0 ? 0 : 0.35;
        place(wheels, i, X(xm), yc, Z(W.z), 1, 1, 1, 0, a);
        place(marks, i, X(xm), yc + Math.cos(a) * (r + 0.1 * MM), Z(W.z) + Math.sin(a) * (r + 0.1 * MM), (W.w - 1.5) * MM, 0.3 * MM, 0.8 * MM, 0, a);
      });
      finish(wheels);
      finish(marks);
    }

    // Screen: glossy bezel and a canvas texture drawn only when the chord changes.
    const SCREEN_W = 960, SCREEN_H = 640;
    const screenCanvas = doc.createElement("canvas");
    screenCanvas.width = SCREEN_W; screenCanvas.height = SCREEN_H;
    const g2 = screenCanvas.getContext("2d");
    const screenTex = keep(new THREE.CanvasTexture(screenCanvas));
    screenTex.colorSpace = THREE.SRGBColorSpace;
    screenTex.anisotropy = 8;
    const screenMat = keep(new THREE.MeshBasicMaterial({ map: screenTex, color: new THREE.Color(SCREEN_IDLE, SCREEN_IDLE, SCREEN_IDLE) }));
    studio(screenMat, { emit: true });
    add(roundBox(L.screen.bezelW * MM, 1.0 * MM, L.screen.bezelD * MM, 2, 3 * MM), mat.bezel, X(L.screen.x), yPlate + 0.5 * MM, Z(L.screen.z));
    add(keep(new THREE.PlaneGeometry(L.screen.w * MM, L.screen.d * MM).rotateX(-Math.PI / 2)), screenMat,
        X(L.screen.x), yPlate + 1.08 * MM, Z(L.screen.z));

    // Knobs: 9 rubber encoders and the aluminium main encoder (lathe profiles), with pointer lines.
    const lathe = (r, h, top) => {
      const pts = [[0, 0], [r, 0], [r, h * 0.62], [r * 0.97, h * 0.7], [r * 0.9, h * 0.74], [r * 0.88, h * 0.94],
                   [r * 0.8, h], [r * top, h], [0, h * 0.97]].map(([a, b]) => new THREE.Vector2(a, b));
      return keep(new THREE.LatheGeometry(pts, 40));
    };
    const knobMesh = new THREE.InstancedMesh(lathe(L.strips.knobR * MM, H.knob * MM, 0.35), mat.rubber, 9);
    const pointerMesh = new THREE.InstancedMesh(unitBox, mat.mark, 10);
    for (let i = 0; i < 9; i++) {
      const x = X(L.strips.x0 + i * L.strips.pitch), z = Z(L.strips.knobZ), a = L.knobs[i];
      place(knobMesh, i, x, yPlate, z, 1, 1, 1);
      const pr = L.strips.knobR * 0.45 * MM;
      place(pointerMesh, i, x - Math.sin(a) * pr, yPlate + (H.knob + 0.1) * MM, z - Math.cos(a) * pr, 1.1 * MM, 0.4 * MM, L.strips.knobR * 0.8 * MM, a);
    }
    finish(knobMesh);
    {
      const e = L.encoder, x = X(e.x), z = Z(e.z);
      add(lathe(e.r * MM, H.encoder * MM, 0.2), mat.alu, x, yPlate, z);
      // a short engraved index line on the flat of the top face (0.3 r .. 0.75 r), standing 0.5 mm proud; no pin
      const a = 0.6, rc = e.r * 0.525 * MM;
      place(pointerMesh, 9, x - Math.sin(a) * rc, yPlate + (H.encoder + 0.25) * MM, z - Math.cos(a) * rc, 1.0 * MM, 0.5 * MM, e.r * 0.45 * MM, a);
    }
    finish(pointerMesh);

    // Faders: slots, caps and cap index lines.
    {
      const S = L.strips, slotLen = S.slot * MM;   // 50 mm travel (cap centres at faderZ +/- 25) plus a cap margin
      const slots = new THREE.InstancedMesh(unitBox, mat.slot, 9);
      const caps = new THREE.InstancedMesh(roundBox(1, 1, 1, 2, 0.14), mat.rubber, 9);
      const lines = new THREE.InstancedMesh(unitBox, mat.mark, 9);
      for (let i = 0; i < 9; i++) {
        const x = X(S.x0 + i * S.pitch);
        place(slots, i, x, yPlate + 0.15 * MM, Z(S.faderZ), 2.6 * MM, 0.5 * MM, slotLen);
        const zc = Z(S.faderZ - S.travel / 2 + L.faders[i] * S.travel);
        place(caps, i, x, yPlate + (3 + (H.fader - 3) / 2) * MM, zc, 14 * MM, (H.fader - 3) * MM, 10 * MM);
        place(lines, i, x, yPlate + (H.fader + 0.05) * MM, zc, 12 * MM, 0.3 * MM, 1.0 * MM);
      }
      finish(slots); finish(caps); finish(lines);
    }

    ctx.scene?.add(group);

    // -------------------------------------------------------------- reaction --
    const padSustain = new Float32Array(PAD_COUNT), padPeak = new Float32Array(PAD_COUNT), padLevel = new Float32Array(PAD_COUNT);
    const padVel = new Float32Array(PAD_COUNT), padSeen = new Float64Array(PAD_COUNT).fill(-Infinity);
    const tmp = new THREE.Color(), rootCol = new THREE.Color();
    let active = true, lastName, lastNns, lastKey, lastMask = -1, lastDim = null, heldMask = 0, anyHeld = false, chordRootPc = -1;
    let pedalLevel = 0, chordLevel = 0, playLevel = 0, frameT = 0;
    const PAD = { holdBase: 0.16, holdVel: 0.22, peakTau: 0.42, attack: 0.018, release: 0.22, surface: 0.35, rim: 2.3, rimIdle: 0.012 };
    // The spec's pads are backlit through translucent edges: the HDR rim (x2.3) carries the glow and the bloom at velocity
    // peaks, and the tops take only a low tint (x0.35) so they still read as rubber.

    const strike = (midi, vel, t) => {
      const pc = ((midi % 12) + 12) % 12;
      if (t <= padSeen[pc]) return;
      padSeen[pc] = t;
      const v = Math.min(1, Math.max(0, vel / 127));
      padPeak[pc] = Math.max(padPeak[pc], Math.pow(v, 1.6));
      padVel[pc] = vel;
    };
    const eachPressed = (st, midi) => {
      const pc = ((midi % 12) + 12) % 12, v = Math.min(1, (st?.vel ?? 100) / 127);
      padSustain[pc] = Math.max(padSustain[pc], PAD.holdBase + PAD.holdVel * v);
      if (padVel[pc] < (st?.vel ?? 100)) padVel[pc] = st?.vel ?? 100;
      heldMask |= 1 << pc;
      anyHeld = true;
      if (st && Number.isFinite(st.t0) && frameT - st.t0 < 0.25) strike(midi, st.vel ?? 100, st.t0);
    };

    const pretty = (s) => String(s || "").replace(/([A-G])bb/g, "$1\u{1D12B}").replace(/([A-G])##/g, "$1\u{1D12A}")
      .replace(/([A-G])b/g, "$1♭").replace(/([A-G])#/g, "$1♯")
      .replace(/([^A-Ga-z])b(\d)/g, "$1♭$2").replace(/([^A-Ga-z])#(\d)/g, "$1♯$2");
    const ROOT_PC = { C: 0, D: 2, E: 4, F: 5, G: 7, A: 9, B: 11 };
    const cssOf = (col, lift) => {
      tmp.copy(col).convertLinearToSRGB();
      const f = (v) => Math.round(255 * Math.min(1, v + (1 - Math.min(1, v)) * lift));
      return `rgb(${f(tmp.r)},${f(tmp.g)},${f(tmp.b)})`;
    };
    let phone = false;                       // the 9:16 profile is active (set by resize)
    const screenArgs = [null, 0, true];      // the last drawScreen arguments, for redraws on font or profile changes
    function drawScreen(chord, mask, dim) {
      screenArgs[0] = chord; screenArgs[1] = mask; screenArgs[2] = dim;
      const g = g2, W = SCREEN_W, Hh = SCREEN_H, text = fontsSettled;
      // On a phone the whole screen is ~60 px wide: a bigger name and number, no header line, bigger dots.
      const LY = phone ? { name: 290, nameY: 330, nnsY: 494, big: 132, sup: 70, ph: 158, dotY: 596, dotOn: 19, dotOff: 11 }
                       : { name: 210, nameY: 318, nnsY: 452, big: 118, sup: 62, ph: 150, dotY: 584, dotOn: 13, dotOff: 9 };
      g.save();
      // Idle is the same layout at half brightness (screenMat's colour, set by the caller), not a near-black panel, so
      // the screen reads as a lit display at phone scale. A deep ground under bright ink: contrast is what survives the
      // downscale.
      const bg = g.createLinearGradient(0, 0, 0, Hh);
      bg.addColorStop(0, "#0e152b"); bg.addColorStop(1, "#03050b");
      g.fillStyle = bg; g.fillRect(0, 0, W, Hh);
      const vg = g.createRadialGradient(W / 2, Hh * 0.46, 40, W / 2, Hh * 0.46, W * 0.62);
      vg.addColorStop(0, "rgba(70,92,160,0.16)"); vg.addColorStop(1, "rgba(0,0,0,0)");
      g.fillStyle = vg; g.fillRect(0, 0, W, Hh);
      // header
      if (text && !phone) {
        g.font = `600 30px ${FONT}`;
        g.textBaseline = "middle";
        if ("letterSpacing" in g) g.letterSpacing = "6px";
        g.fillStyle = "#98a4c2";
        g.textAlign = "left"; g.fillText("CHORD", 44, 54);
        g.textAlign = "right"; g.fillText(chord && chord.key ? `KEY  ${pretty(chord.key).toUpperCase()}` : "KEY  —", W - 44, 54);
        if ("letterSpacing" in g) g.letterSpacing = "0px";
        g.fillStyle = "rgba(255,255,255,0.1)"; g.fillRect(44, 90, W - 88, 2);
      }
      // chord name, filled with a gradient through the chord tones' own colours
      const name = chord ? pretty(chord.name) : "—";
      const m = /^([A-G])(♭|♯)?/.exec(name);
      let rootPc = m ? ROOT_PC[m[1]] + (m[2] === "♭" ? -1 : m[2] === "♯" ? 1 : 0) : -1;
      rootPc = ((rootPc % 12) + 12) % 12;
      if (text) {
        let size = LY.name;
        g.font = `700 ${size}px ${FONT}`;
        while (g.measureText(name).width > W - (phone ? 60 : 120) && size > 80) { size -= 8; g.font = `700 ${size}px ${FONT}`; }
        const tw = g.measureText(name).width;
        const grad = g.createLinearGradient(W / 2 - tw / 2, 0, W / 2 + tw / 2, 0);
        const pcs = [];
        if (m) pcs.push(rootPc);
        for (let i = 1; i < 12; i++) { const pc = (rootPc + i) % 12; if (mask & (1 << pc)) pcs.push(pc); }
        if (pcs.length === 0) grad.addColorStop(0, "#e8ecf4");
        pcs.forEach((pc, i) => grad.addColorStop(pcs.length === 1 ? 0 : i / (pcs.length - 1), cssOf(ctx.noteColor(60 + pc, 112, rootCol), 0.36)));
        g.fillStyle = grad;
        g.textAlign = "center"; g.textBaseline = "alphabetic";
        g.fillText(name, W / 2, LY.nameY);
      }
      // Nashville number in a pill: the page's "1^6/9" -> 1 with a raised 6/9; a string that already carries superscript
      // glyphs ("1⁶ᐟ⁹") is drawn as it is
      const nns = chord && chord.nns ? String(chord.nns) : "";
      if (nns && text) {
        const [num, sup = ""] = nns.includes("^") ? nns.split("^") : [nns];
        const bigF = `600 ${LY.big}px ${FONT}`, supF = `600 ${LY.sup}px ${FONT}`;
        g.font = bigF; const wn = g.measureText(pretty(num)).width;
        g.font = supF; const ws = sup ? g.measureText(pretty(sup)).width + 8 : 0;
        const total = wn + ws, cx = W / 2, cy = LY.nnsY, pw = total + 96, ph = LY.ph;
        g.strokeStyle = phone ? "rgba(210,222,248,0.45)" : "rgba(200,212,240,0.32)"; g.lineWidth = phone ? 6 : 4;
        g.beginPath(); g.roundRect(cx - pw / 2, cy - ph / 2, pw, ph, ph / 2); g.stroke();
        g.fillStyle = "#f4f7fd"; g.textAlign = "left"; g.textBaseline = "alphabetic";
        g.font = bigF; g.fillText(pretty(num), cx - total / 2, cy + LY.big * 0.36);
        if (sup) { g.font = supF; g.fillStyle = "#d6def0"; g.fillText(pretty(sup), cx - total / 2 + wn + 8, cy - 4); }
      }
      // twelve dots: the pads' pitch classes, lit for the chord tones
      for (let pc = 0; pc < 12; pc++) {
        const x = W / 2 + (pc - 5.5) * 50, y = LY.dotY, on = (mask & (1 << pc)) !== 0;
        g.beginPath(); g.arc(x, y, on ? LY.dotOn : LY.dotOff, 0, Math.PI * 2);
        if (on) { g.fillStyle = cssOf(ctx.noteColor(60 + pc, 112, rootCol), 0.1); g.fill(); }
        else { g.strokeStyle = "rgba(255,255,255,0.2)"; g.lineWidth = 3; g.stroke(); }
      }
      g.restore();
      screenTex.needsUpdate = true;
    }
    drawScreen(null, 0, true);
    settleFonts.push(() => { drawScreen(...screenArgs); lastDim = null; });

    const writeRgb = (arr, i, col, k) => { arr[i * 3] = col.r * k; arr[i * 3 + 1] = col.g * k; arr[i * 3 + 2] = col.b * k; };
    const LED_TINT = {
      white: new THREE.Color(1, 1, 1), red: new THREE.Color(1, 0.07, 0.05), green: new THREE.Color(0.25, 1, 0.42),
      amber: new THREE.Color(1, 0.6, 0.18), blue: new THREE.Color(0.4, 0.62, 1),
    };

    function update(dt, t, state) {
      if (!active) return;
      dt = Math.min(Math.max(dt || 0, 0), 0.1);
      frameT = t;
      padSustain.fill(0);
      heldMask = 0; anyHeld = false;
      const pressed = state && state.pressed;
      if (pressed && pressed.forEach) pressed.forEach(eachPressed);
      const notes = state && state.notes;
      if (notes) for (let i = 0; i < notes.length; i++) { const n = notes[i]; if (n && t - n.t < 0.25 && t - n.t >= -0.05) strike(n.midi, n.vel, n.t); }

      // pads
      const kPeak = decay(PAD.peakTau, dt), kAtt = 1 - decay(PAD.attack, dt), kRel = 1 - decay(PAD.release, dt);
      const glow = padGlowAttr.array, rim = rimMesh.instanceColor.array;
      let padsDirty = false;
      for (let pc = 0; pc < PAD_COUNT; pc++) {
        const target = padSustain[pc] + padPeak[pc];
        padPeak[pc] *= kPeak;
        const cur = padLevel[pc], next = cur + (target - cur) * (target > cur ? kAtt : kRel);
        padLevel[pc] = next < 1e-4 ? 0 : next;
        if (Math.abs(next - cur) > 1e-5 || lastDim === null) {
          padsDirty = true;
          if (next > 0) ctx.noteColor(60 + pc, padVel[pc] || 100, tmp); else tmp.setRGB(0, 0, 0);
          writeRgb(glow, pc, tmp, next * PAD.surface);
          const idle = PAD.rimIdle;
          rim[pc * 3] = tmp.r * next * PAD.rim + idle; rim[pc * 3 + 1] = tmp.g * next * PAD.rim + idle; rim[pc * 3 + 2] = tmp.b * next * PAD.rim + idle * 1.3;
        }
      }
      if (padsDirty) { padGlowAttr.needsUpdate = true; rimMesh.instanceColor.needsUpdate = true; }

      // LEDs: subtle. Hold follows the sustain pedal, Chord lights in the root colour while a chord reads, Play while keys are down.
      const kLed = 1 - decay(0.08, dt), chord = state && state.chord;
      pedalLevel += ((state && state.pedal ? 1 : 0) - pedalLevel) * kLed;
      chordLevel += ((chord ? 1 : 0) - chordLevel) * kLed;
      playLevel += ((anyHeld ? 1 : 0) - playLevel) * kLed;

      // screen: redraw only when what it says changes (the root is parsed there too, not per frame)
      const dim = !chord;
      const name = chord ? chord.name : lastName, nns = chord ? chord.nns : lastNns, key = chord ? chord.key : lastKey;
      const mask = chord ? heldMask || lastMask : lastMask;
      if (name !== lastName || nns !== lastNns || key !== lastKey || mask !== lastMask || dim !== lastDim) {
        if (name !== lastName) {
          const m = /^([A-G])(b|#|♭|♯)?/.exec(name || "");
          chordRootPc = m ? (ROOT_PC[m[1]] + (m[2] === "b" || m[2] === "♭" ? 11 : m[2] === "#" || m[2] === "♯" ? 1 : 0)) % 12 : -1;
        }
        lastName = name; lastNns = nns; lastKey = key; lastMask = mask; lastDim = dim;
        drawScreen(name ? { name, nns, key } : null, Math.max(0, mask), dim);
        screenMat.color.setScalar(dim ? SCREEN_IDLE : SCREEN_ON);
      }
      if (chord && chordRootPc >= 0) ctx.noteColor(60 + chordRootPc, 110, rootCol);
      const leds = ledMesh.instanceColor.array;
      let ledsDirty = false;
      for (let i = 0; i < ledLevel.length; i++) {
        let col = LED_TINT.white, k = ledIdle;
        switch (ledRole[i]) {
          case LED_ROLE.rec: col = LED_TINT.red; k = ledIdle + 0.05; break;
          case LED_ROLE.play: col = LED_TINT.green; k = ledIdle + 0.5 * playLevel; break;
          case LED_ROLE.loop: col = LED_TINT.amber; k = ledIdle; break;
          case LED_ROLE.stop: k = ledIdle; break;
          case LED_ROLE.hold: col = LED_TINT.amber; k = ledIdle + 0.92 * pedalLevel; break;
          case LED_ROLE.chord: col = chord ? rootCol : LED_TINT.white; k = ledIdle + 0.77 * chordLevel; break;
          case LED_ROLE.oct: col = LED_TINT.blue; k = ledIdle + 0.01; break;
          case LED_ROLE.ctx: k = ledIdle + 0.14; break;
          default: break;
        }
        const r = col.r * k, gg = col.g * k, b = col.b * k;
        if (Math.abs(leds[i * 3] - r) + Math.abs(leds[i * 3 + 1] - gg) + Math.abs(leds[i * 3 + 2] - b) > 1e-4) {
          leds[i * 3] = r; leds[i * 3 + 1] = gg; leds[i * 3 + 2] = b; ledsDirty = true;
        }
      }
      if (ledsDirty) ledMesh.instanceColor.needsUpdate = true;
    }

    // View profile: the host calls resize(framing) when the frame changes; a portrait frame (9:16) gets the phone profile.
    let ledIdle = PROFILE.wide.ledIdle;
    function applyProfile(fr) {
      const P = fr && (fr.id === "9:16" || (fr.w > 0 && fr.h > fr.w)) ? PROFILE.phone : PROFILE.wide;
      STUDIO.uKlFogLit.value = P.fogLit; STUDIO.uKlFogEmit.value = P.fogEmit; STUDIO.uKlSoft.value = P.soft;
      STUDIO.uKlKeyFill.value = P.keyFill * ED.fill; STUDIO.uKlRim.value = P.rim;
      ledIdle = P.ledIdle; PAD.rimIdle = P.padRimIdle;
      lastDim = null;   // rewrite pad rims and the screen on the next update
      if (phone !== P.phone) { phone = P.phone; drawScreen(...screenArgs); }
    }

    function setActive(on) {
      active = !!on;
      group.visible = active;
      if (!active) { padPeak.fill(0); padLevel.fill(0); padSeen.fill(-Infinity); lastDim = null; }
    }

    function dispose() {
      disposed = true;
      group.removeFromParent();
      padMesh.geometry.deleteAttribute("aGlow");
      for (const d of disposables) d.dispose?.();
      group.traverse((o) => { if (o.isInstancedMesh) o.dispose(); });
      disposables.clear();
    }

    function stats() {
      let meshes = 0, triangles = 0;
      group.traverse((o) => {
        if (!o.isMesh) return;
        meshes++;
        const g = o.geometry, n = g.index ? g.index.count : g.attributes.position.count;
        triangles += (n / 3) * (o.isInstancedMesh ? o.count : 1);
      });
      return { drawCalls: meshes, triangles, pads: Array.from(padLevel, (v) => +v.toFixed(3)),
               font: { family: FAMILY, loaded: fontLoaded, settled: fontsSettled }, profile: phone ? "phone" : "wide" };
    }
    applyProfile(ctx.framing);

    const closeTarget = [(X(L.pads.x0 + 2.5 * L.pads.pitch) + X(L.screen.x)) / 2 + 1.0, yPlate, Z(245)];
    // hero: three-quarter from the front left, high enough (30 deg) that the top panel's controls read
    const heroTarget = [X(CHASSIS.w / 2) + 0.5, Y(-10), (zFront + zBack) / 2 + 0.4];
    const heroYaw = -32 * Math.PI / 180, heroElev = 30 * Math.PI / 180, heroDist = CHASSIS.w * MM * 1.6;
    const heroFrom = [heroTarget[0] + heroDist * Math.sin(heroYaw) * Math.cos(heroElev), heroTarget[1] + heroDist * Math.sin(heroElev),
                      heroTarget[2] + heroDist * Math.cos(heroYaw) * Math.cos(heroElev)];
    return {
      group, update, resize: applyProfile, setActive, dispose, stats,
      fontsReady,   // resolves (true when the chosen face loaded) once the lettering has been drawn in its final face
      font: FAMILY,
      get info() { return stats(); },
      // hints for the host: key colours for this instrument, and where the desk is. specFloorY is the spec's estimate (key
      // tops 78 mm above the desk); floorY is where this body actually ends (the host floor when one was given).
      keyStyle: { whiteColor: ED.whiteKey, blackColor: ED.blackKey, capHeight: null, frontLip: 0 },
      stage: { floorY, specFloorY, width: CHASSIS.w * MM, depth: CHASSIS.d * MM, front: zFront, back: zBack },
      views: { hero: { target: heroTarget, from: heroFrom, fov: 23 },
               close: { target: closeTarget, from: [closeTarget[0] + 6.5, closeTarget[1] + 10.5, closeTarget[2] + 18.5], fov: 30 } },
      layout: { MM, X, Z, Y, yPlate, screen: { x: X(L.screen.x), z: Z(L.screen.z) }, pads: { x: X(L.pads.x0 + 2.5 * L.pads.pitch), z: Z((L.pads.zFront + L.pads.zBack) / 2) } },
    };
  },
};
