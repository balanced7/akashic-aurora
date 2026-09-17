// Crystal Grand — arsenal/web/piano/instruments/glass-piano.js  (ES module, a piano instrument, no imports)
//
// A cast-acrylic grand built around the host's 88-key span. The case (rim, lid, legs, lyre, key blocks, keybed, key slip,
// fallboard, music desk) is clear MeshPhysicalMaterial transmission; the action inside is opaque and visible through it:
// a gold plate with a hammer gap, a spruce soundboard, 229 strings, 88 hammers, 68 dampers, tuning pins, three pedals.
//
// Proportions: Kawai CR-40A class (L 1850 x W 1500 x H 1000 mm, spec.md section 2 GLASS PIANO), key tops 715 mm above the
// floor. Host units: 1 unit = one white-key pitch = 23.57 mm (52 whites = 1225.7 mm), key tops at y = 0, white fronts at
// z = +3.1, key backs at z = -3.1.
//
// Reactive (everything decays; nothing glows at rest):
//  - hammers: a struck key throws its hammer up to the string (faster the harder), it rebounds to check height while the
//    key is held and falls back on release. The felt tip flashes the note colour, v^2 peak over the bloom threshold,
//    exp(-age / 0.28 s), with a faint held floor under the threshold.
//  - strings: the struck note's strings take its colour AND start vibrating, and both last exactly as long as the page
//    says the sound does (state.sounding): a flash, a prompt decay, a pitch-dependent aftersound, then a velocity-scaled
//    floor held for the whole note, finger or pedal, and a 0.30 s damping fade at its end. The vibration is drawn as a
//    translucent long-exposure blur (Dune's ornithopter wings), wide and slow in the bass, a fine shimmer at the top.
//    They are screen-space ribbons in the OPAQUE list under CustomBlending, so they survive the transmission pass.
//    Tuning table below, under "the string light envelope and the vibration blur".
//  - dampers: lift while their key is held or the sustain pedal is down; the right pedal dips with the pedal.
//  - case: clear cast acrylic (white base, a faint cool attenuation over 400 mm, 15 mm walls, 25 mm legs and lyre). A
//    cool-white fresnel edge (no environment map) outlines the silhouettes; strikes tint only the sharpest edges toward
//    the notes' colours, capped under the bloom threshold, so the body never fills with colour.
//  - music desk: the chord name (state.chord.name, our own text) is etched in the chord's colour, flares on a change.
//
// Integration notes for the host: the instrument brings its own keybed, key blocks and key slip, so the host's lacquer
// stage body should hide while it is mounted (hints.hideStageBody). The legs reach a floor 715 mm below the key tops
// (hints.floorY = -30.33); the host floor at y = -2.3 would cut them. Nothing in front of z = -3.55 rises above the key
// tops, so the host's trails (emitted at z = -3.42) are never hidden by the glass.
// Options (ctx.options or setOptions): lid "auto" (off on the page, long prop in the lab's hero view) | "long" |
// "short" | "closed" | "off" (a portrait framing never raises it past "short"); glass "crystal" (transmission) | "fast"
// (plain alpha blend, no transmission pass); desk true | false; edge 0..2 (fresnel edge strength, default 1).

const MM = 1225.7 / 52;
const DEG = Math.PI / 180;
const KEY_STYLE = Object.freeze({ whiteColor: 0xe8e4db, blackColor: 0x0b0c10, capHeight: null, frontLip: 0.28 });
const HINTS = Object.freeze({ hideStageBody: true, floorY: -715 / MM });

const G = Object.freeze({
  halfW: 31.82, rimTh: 1.3, rimBottom: -3.2, rimTop: 11.5, front: -3.6,
  blockInner: 26.12, blockFront: 3.85, bedTop: -0.85, bedBottom: -2.3,
  strY: 2.4, bassStrY: 2.9, agraffeZ: -9.4, strikeZ: -12.3, shank: 5.2, pivotY: -0.99, restTop: 0.4,
  damperZ: -15.6, plateY0: 1.3, plateY1: 1.9, gap0: -9.6, gap1: -16.8, boardY: -1.6,
  lidTh: 0.55, lidFrontZ: -8.8, floorY: -715 / MM,
});
const LID_ANGLE = { long: 38, short: 10, closed: 0, off: 0 };
const GLOW = { peak: 5.0, tau: 0.28, held: 0.3 };
// ---- the string light envelope and the vibration blur ----
// Daniel, 2026-09-17: "the color decay doesn't fully match the sustain of the length of the note ... the decay should be
// slower and have a higher floor", and "notes that are lower could have more of a blur and vibration similar to the wings
// in the helicopters from the movie Dune". The same model as the concert grand's, tuned the same way, so the two
// instruments answer a held pedal identically; only the gains differ, because the crystal's strings sit on gold and are
// NOT its bloom source (the hammer felt is, GLOW.peak above — the strings stay under the 0.9 luminance line at fff).
//
//   name             what it is                                                       value
//   PEAK_EXP         body height at the strike = v^PEAK_EXP  (v = vel/127)            1.35
//   FLASH_EXP        the strike transient's height = v^FLASH_EXP                      2.0
//   TAU_FLASH        the transient's decay                                            0.09 s
//   FLOOR_LO/HI      the floor the body settles on, as a share of the strike body     0.33 at vel 1 -> 0.50 at vel 127
//                    (42 % at vel 64, 46 % at vel 96), held for the WHOLE sound
//   AFTER_SHARE      how much of the above-floor body is in the slow aftersound       0.55
//   TAU_PROMPT       the prompt decay, a real string's first fast loss                1.00 s at A0 -> 0.45 s at C8
//   TAU_AFTER        the aftersound: bass rings for seconds, treble does not          7.0 s at A0 -> 1.2 s at C8
//                    (at C4: prompt 0.70 s, aftersound 3.2 s)                         geometric in pitch
//   TAU_DAMP         the damper landing, when the sound ENDS: the fall's time constant 0.16 s
//   DAMP_FADE        and the window that closes that fall to exactly 0, so the light   0.30 s
//                    never outlives the sound. Level at the release x1, +0.05 s 0.68,
//                    +0.1 s 0.41, +0.15 s 0.21, +0.2 s 0.09, +0.25 s 0.03, +0.3 s 0.
//                    A fade, not a snap: the steepest 60 fps step is 11 % of the level
//                    at the release, and the window lands with zero slope.
//   TAU_VIB_OFF      the blur dies faster than the light: the damper stops the string 0.07 s
//   STR_BODY/FLASH   string colour = base + noteColor * (body * 1.10 + flash * 0.45)  (1.10 is the old STR.peak, so a
//                    strike is as bright as it ever was; at fff the pair reach 0.85 luminance, under the 0.9 bloom line)
//   AMP_BASS/TREBLE  swing half-amplitude at full body, world units, geometric in     0.38 -> 0.038 units
//                    pitch (0.135 at C4). On screen at 16:9 Ultra: about 8.5 framing   (the same numbers the concert
//                    px at A0, 3.4 at C4, 1 at C7. Measured perpendicular px/unit at   grand uses — the two cameras put
//                    the string band: 22.3 / 22.8 / 25.3 / 28.3 (A0/A1/C4/C7).         a unit within 15 % of each other)
//   AMP_EXP          amplitude = AMP(pitch) * body^AMP_EXP: it narrows as the note settles, and never stops while it sounds
//   VIB_HZ           the blur envelope's visual breathing rate, never the real pitch  3.1 Hz (bass) -> 9.5 Hz (top)
//   VIB_WOBBLE       a slow drift of the blur's centre, as a share of its width, so it reads as alive and not as a bar
//   VIB_DETUNE       the unison strings' rates differ by this much, so they beat against each other as real unisons do
//   BLUR_CONSERVE    how much of the string's light is spread rather than added as it widens (1 = conserved exactly,
//                    0 = same peak at any width). 0.45 keeps a wide blur luminous and every pixel of it dimmer than the
//                    string at rest, which is what keeps the bloom out of it.
//   STRING_MIN_PX    the ribbon's half-width floor in drawing-buffer pixels, under the string's own STRING_W/2
// The old string model, kept only as the record of what it was: peak 1.1 now lives in STR_BODY_GAIN, and the two decays
// (0.35 s dry, 1.8 s wet) are what Daniel's "the colour decay doesn't match the sustain" was about.
const PEAK_EXP = 1.35, FLASH_EXP = 2;
const FLOOR_LO = 0.33, FLOOR_HI = 0.50;
const AFTER_SHARE = 0.55;
const TAU_PROMPT_BASS = 1.00, TAU_PROMPT_TREBLE = 0.45;
const TAU_AFTER_BASS = 7.0, TAU_AFTER_TREBLE = 1.2;
const TAU_FLASH = 0.09, TAU_DAMP = 0.16, DAMP_FADE = 0.30, TAU_VIB_OFF = 0.07;
const STR_BODY_GAIN = 1.10, STR_FLASH_GAIN = 0.45;
const AMP_BASS = 0.38, AMP_TREBLE = 0.038, AMP_EXP = 0.8;
const VIB_HZ_BASS = 3.1, VIB_HZ_TREBLE = 9.5, VIB_WOBBLE = 0.22, VIB_DETUNE = 0.06;
const BLUR_DENS_CAP = 3.0, BLUR_DENS_NORM = 0.69, BLUR_CONSERVE = 0.45, STRING_MIN_PX = 0.55;
const pitchOf = (m) => (m - 21) / 87;                    // 0 at A0, 1 at C8
const overPitch = (m, lo, hi) => lo * Math.pow(hi / lo, pitchOf(m));
// Clear cast acrylic. Judge 2026-09-15: the old body read purple, because a broad fresnel term carried the chord's strike
// tint across whole faces. Now the base is white, the attenuation a faint cool grey over 400 mm, and the walls 15 mm
// (25 mm in the legs and lyre).
const GLASS = { color: 0xffffff, roughness: 0.03, ior: 1.49, thickness: 15 / MM, legThickness: 25 / MM,
  attenuationColor: 0xdfe6ef, attenuationDistance: 400 / MM, fastColor: 0xdfe6ef, fastOpacity: 0.16 };
// The edge is cool white at 0.12 and tight (pow 5.5), so it outlines silhouettes. The strike tint rides pow 10 and is
// capped at luminance 0.09 and at 0.15 per channel. Render 2026-09-15 q2: under a luma-only cap a blue/violet chord
// kept about 1.0 in blue, since blue carries only 0.07 of the luma weight, and at pow 7 that filled the grazing lid
// underside navy.
const EDGE = { color: 0xcfe0ff, gain: 0.12, pow: 5.5, strikePow: 10.0, strikeGain: 0.05, tau: 1.1, maxLuma: 0.09, maxChannel: 0.15 };
const STRING_W = 0.06;  // strings are thin crossed ribbons, not GL lines, so MSAA smooths them
const ETCH = { level: 0.15, flash: 0.9, tau: 0.5 };  // a low resting glow, so the etch never competes with the page's chord header
const CHECK = 0.42;   // share of the blow the hammer is held at while its key stays down

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);
const mix = (a, b, f) => a + (b - a) * f;
const damp = (a, b, tau, dt) => b + (a - b) * Math.exp(-dt / tau);
// The damper's fade, x seconds after the sound ended: the body is already falling at TAU_DAMP, and this window closes
// that fall to exactly 0 at DAMP_FADE. A bare exponential has no end — at TAU_DAMP alone a loud release was still on
// screen a second later, i.e. the light outlived the sound. Smoothstep, so it lands with zero slope and never snaps.
const dampFade = (x) => { if (x >= DAMP_FADE) return 0; const u = x / DAMP_FADE; return 1 - u * u * (3 - 2 * u); };

// ---- the string ribbon shader (the same pair as concert-grand.js; kept per file, an instrument imports nothing) ----
// Vertex: the ribbon is widened perpendicular to the string AS DRAWN, in screen space, so a blur reads the same however
// the string is foreshortened. Half-width = the swing amplitude carried per note in uNote[i].w (world units, projected
// here), never under the string's own resting width. aParam = (u along the speaking length, side -1/+1, light dim, note).
// Fragment: the long-exposure density of a sine swing, 1/sqrt(1-(x/A)^2) — what the eye actually sees of a wing that beats
// faster than the frame rate — normalised and conserved, so a wider blur is fainter per pixel and never stacks to white.
const stringVert = (notes) => `
precision highp float;
uniform vec2 uRes;
uniform float uTime, uMinPx, uRestHalf, uWobble;
uniform vec4 uNote[${notes}];
attribute vec3 aBase;
attribute vec3 aDir;
attribute vec4 aParam;
attribute vec2 aVib;
varying vec3 vCol;
varying float vAcross;
varying float vCore;
void main() {
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vec4 clip = projectionMatrix * mv;
  vec3 dv = mat3(modelViewMatrix) * aDir;                           // aDir is a unit vector in object space,
  float kScale = length(dv);                                        // so its length here is the host's scale on the instrument
  vec4 clipB = projectionMatrix * (mv + vec4(dv, 0.0));
  float w = max(clip.w, 1e-4);
  vec2 s0 = clip.xy / w * uRes * 0.5;
  vec2 s1 = clipB.xy / max(clipB.w, 1e-4) * uRes * 0.5;
  vec2 tang = s1 - s0;
  vec2 nrm = dot(tang, tang) > 1e-8 ? normalize(vec2(-tang.y, tang.x)) : vec2(1.0, 0.0);
  float pxPerUnit = projectionMatrix[1][1] * uRes.y * 0.5 / w;
  vec4 nd = uNote[int(aParam.w + 0.5)];
  float shape = sin(3.14159265 * aParam.x);
  float amp = nd.w * shape;
  float halfW = max(uRestHalf, amp * (0.80 + 0.20 * sin(uTime * aVib.y + aVib.x)));
  float wob = amp * uWobble * sin(uTime * aVib.y * 0.5 + aVib.x * 1.7);
  float restPx = max(uMinPx, uRestHalf * kScale * pxPerUnit);
  float halfPx = max(restPx, halfW * kScale * pxPerUnit);
  clip.xy += nrm * (aParam.y * halfPx + wob * kScale * pxPerUnit) / (uRes * 0.5) * w;
  gl_Position = clip;
  vCol = aBase + nd.rgb * aParam.z;
  vAcross = aParam.y;
  vCore = restPx / halfPx;
}`;
const STRING_FRAG = `
precision highp float;
uniform float uDensCap, uDensNorm, uConserve;
varying vec3 vCol;
varying float vAcross;
varying float vCore;
void main() {
  float d = min(abs(vAcross), 1.0);
  float dens = min(inversesqrt(max(1.0 - d * d, 1e-3)), uDensCap) * uDensNorm;
  float blur = dens * pow(vCore, uConserve) * smoothstep(1.0, 0.86, d);
  float solid = smoothstep(1.0, 0.72, d);                         // the string at rest: the thin ribbon it has always been
  float a = mix(solid, blur, smoothstep(0.0, 0.55, 1.0 - vCore));
  gl_FragColor = vec4(vCol, clamp(a, 0.0, 1.0));
  #include <tonemapping_fragment>
  #include <colorspace_fragment>
}`;
const isPortrait = (f) => !!f && (f.id === "9:16" || (f.h > 0 && f.h > f.w));
const norm2 = (x, z) => { const l = Math.hypot(x, z) || 1; return [x / l, z / l]; };

// ------------------------------------------------------------------ 2D helpers (x, z) --
function signedArea(poly) {
  let a = 0;
  for (let i = 0; i < poly.length; i++) { const p = poly[i], q = poly[(i + 1) % poly.length]; a += p[0] * q[1] - q[0] * p[1]; }
  return a / 2;
}
// Rings along a path in the XZ plane: position, tangent, outward normal n = (t.z, -t.x), miter k. Sharp corners (> 35
// degrees) get two rings, one per edge, so flat faces keep flat normals.
function pathRings(pts, closed) {
  const n = pts.length, out = [], cs = Math.cos(35 * DEG);
  for (let i = 0; i < n; i++) {
    const p = pts[i];
    const dIn = closed || i > 0 ? norm2(p[0] - pts[(i - 1 + n) % n][0], p[1] - pts[(i - 1 + n) % n][1]) : null;
    const dOut = closed || i < n - 1 ? norm2(pts[(i + 1) % n][0] - p[0], pts[(i + 1) % n][1] - p[1]) : null;
    const push = (d, k) => out.push({ x: p[0], z: p[1], tx: d[0], tz: d[1], nx: d[1], nz: -d[0], k });
    if (dIn && dOut) {
      const dot = dIn[0] * dOut[0] + dIn[1] * dOut[1];
      if (dot < cs) { push(dIn, 1); push(dOut, 1); } else {
        const a = norm2(dIn[0] + dOut[0], dIn[1] + dOut[1]);
        push(a, 1 / Math.max(0.4, a[0] * dIn[0] + a[1] * dIn[1]));
      }
    } else push(dIn || dOut, 1);
  }
  if (closed) out.push({ ...out[0] });
  return out;
}
function insetPoly(pts, d) {  // closed; positive d moves inward (against the outward normal)
  const n = pts.length;
  return pts.map((p, i) => {
    const a = pts[(i - 1 + n) % n], b = pts[(i + 1) % n];
    const di = norm2(p[0] - a[0], p[1] - a[1]), dout = norm2(b[0] - p[0], b[1] - p[1]);
    const ni = [di[1], -di[0]], no = [dout[1], -dout[0]];
    const m = norm2(ni[0] + no[0], ni[1] + no[1]);
    const k = 1 / Math.max(0.3, m[0] * ni[0] + m[1] * ni[1]);
    return [p[0] - m[0] * d * k, p[1] - m[1] * d * k];
  });
}
function clipPolyZ(pts, zc) {  // closed polygon, keep z <= zc
  const out = [];
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], q = pts[(i + 1) % pts.length], pin = p[1] <= zc, qin = q[1] <= zc;
    if (pin) out.push(p);
    if (pin !== qin) { const s = (zc - p[1]) / (q[1] - p[1]); out.push([p[0] + (q[0] - p[0]) * s, zc]); }
  }
  return out;
}
function clipLineZ(pts, zc) {  // open polyline, keep z <= zc
  const out = [];
  for (let i = 0; i < pts.length; i++) {
    const p = pts[i], pin = p[1] <= zc;
    if (i > 0) {
      const q = pts[i - 1];
      if ((q[1] <= zc) !== pin) { const s = (zc - q[1]) / (p[1] - q[1]); out.push([q[0] + (p[0] - q[0]) * s, zc]); }
    }
    if (pin) out.push(p);
  }
  return out;
}
function resample(pts, maxLen, closed) {
  const out = [], n = pts.length;
  for (let i = 0; i < (closed ? n : n - 1); i++) {
    const p = pts[i], q = pts[(i + 1) % n], steps = Math.max(1, Math.ceil(Math.hypot(q[0] - p[0], q[1] - p[1]) / maxLen));
    for (let s = 0; s < steps; s++) out.push([p[0] + (q[0] - p[0]) * s / steps, p[1] + (q[1] - p[1]) * s / steps]);
  }
  if (!closed) out.push(pts[n - 1]);
  return out;
}
function inside(poly, x, z) {
  let c = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const a = poly[i], b = poly[j];
    if ((a[1] > z) !== (b[1] > z) && x < (b[0] - a[0]) * (z - a[1]) / (b[1] - a[1]) + a[0]) c = !c;
  }
  return c;
}
// A rounded rectangle in the (u, v) profile plane, counter-clockwise.
function rrect(u0, u1, v0, v1, r, seg = 4) {
  r = Math.min(r, (u1 - u0) / 2 - 1e-4, (v1 - v0) / 2 - 1e-4);
  const out = [];
  const arc = (cu, cv, a0) => { for (let s = 0; s <= seg; s++) { const a = (a0 + 90 * s / seg) * DEG; out.push([cu + r * Math.cos(a), cv + r * Math.sin(a)]); } };
  if (r <= 1e-3) return [[u0, v0], [u1, v0], [u1, v1], [u0, v1]];
  arc(u1 - r, v0 + r, -90); arc(u1 - r, v1 - r, 0); arc(u0 + r, v1 - r, 90); arc(u0 + r, v0 + r, 180);
  return out;
}

// ------------------------------------------------------------------ geometry builders --
function makeBuilders(THREE) {
  // Sweep a closed (u, v) profile along XZ rings: u runs along the ring's outward normal, v is world y.
  function sweep(rings, poly, caps) {
    if (signedArea(poly) < 0) poly = poly.slice().reverse();
    const n = poly.length, cs = Math.cos(35 * DEG), prof = [];
    for (let i = 0; i < n; i++) {
      const p = poly[i], a = poly[(i - 1 + n) % n], b = poly[(i + 1) % n];
      const di = norm2(p[0] - a[0], p[1] - a[1]), dout = norm2(b[0] - p[0], b[1] - p[1]);
      const ni = [di[1], -di[0]], no = [dout[1], -dout[0]];
      if (di[0] * dout[0] + di[1] * dout[1] < cs) prof.push([p[0], p[1], ni[0], ni[1]], [p[0], p[1], no[0], no[1]]);
      else { const m = norm2(ni[0] + no[0], ni[1] + no[1]); prof.push([p[0], p[1], m[0], m[1]]); }
    }
    prof.push(prof[0].slice());
    const P = prof.length, R = rings.length, pos = [], nor = [], idx = [];
    for (const r of rings) for (const q of prof) {
      const u = q[0] * r.k;
      pos.push(r.x + r.nx * u, q[1], r.z + r.nz * u);
      nor.push(r.nx * q[2], q[3], r.nz * q[2]);
    }
    for (let i = 0; i < R - 1; i++) for (let j = 0; j < P - 1; j++) {
      const a = i * P + j, b = (i + 1) * P + j, c = a + 1, d = b + 1;
      idx.push(a, b, c, c, b, d);
    }
    const faceDot = (a, b, c) => {
      const ax = pos[a * 3], ay = pos[a * 3 + 1], az = pos[a * 3 + 2];
      const ux = pos[b * 3] - ax, uy = pos[b * 3 + 1] - ay, uz = pos[b * 3 + 2] - az;
      const vx = pos[c * 3] - ax, vy = pos[c * 3 + 1] - ay, vz = pos[c * 3 + 2] - az;
      const fx = uy * vz - uz * vy, fy = uz * vx - ux * vz, fz = ux * vy - uy * vx;
      return fx * (nor[a * 3] + nor[b * 3] + nor[c * 3]) + fy * (nor[a * 3 + 1] + nor[b * 3 + 1] + nor[c * 3 + 1]) + fz * (nor[a * 3 + 2] + nor[b * 3 + 2] + nor[c * 3 + 2]);
    };
    let score = 0;
    for (let k = 0; k < idx.length; k += 3) score += faceDot(idx[k], idx[k + 1], idx[k + 2]);
    if (score < 0) for (let k = 0; k < idx.length; k += 3) { const t = idx[k + 1]; idx[k + 1] = idx[k + 2]; idx[k + 2] = t; }
    if (caps) {
      const tris = THREE.ShapeUtils.triangulateShape(poly.map((p) => new THREE.Vector2(p[0], p[1])), []);
      for (const end of [0, 1]) {
        const r = end ? rings[R - 1] : rings[0], sg = end ? 1 : -1, base = pos.length / 3;
        for (const p of poly) { const u = p[0] * r.k; pos.push(r.x + r.nx * u, p[1], r.z + r.nz * u); nor.push(sg * r.tx, 0, sg * r.tz); }
        for (const t of tris) {
          const a = base + t[0], b = base + t[1], c = base + t[2];
          if (faceDot(a, b, c) >= 0) idx.push(a, b, c); else idx.push(a, c, b);
        }
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
    g.setIndex(idx);
    return g;
  }
  const slabX = (x0, x1, zf, zb, y0, y1, r) => sweep(pathRings([[x0, 0], [x1, 0]], false), rrect(-zf, -zb, y0, y1, r), true);
  const slabZ = (zf, zb, xl, xr, y0, y1, r) => sweep(pathRings([[0, zf], [0, zb]], false), rrect(-xr, -xl, y0, y1, r), true);
  const bar = (x0, z0, x1, z1, hw, y0, y1, r) => sweep(pathRings([[x0, z0], [x1, z1]], false), rrect(-hw, hw, y0, y1, r), true);
  function capSlab(poly, y0, y1) {  // flat top and bottom caps of a closed XZ polygon (the lid's inner field)
    const tris = THREE.ShapeUtils.triangulateShape(poly.map((p) => new THREE.Vector2(p[0], -p[1])), []);
    const cw = signedArea(poly.map((p) => [p[0], -p[1]])) < 0;
    const pos = [], nor = [], idx = [];
    for (const [y, up] of [[y1, 1], [y0, -1]]) {
      const base = pos.length / 3;
      for (const p of poly) { pos.push(p[0], y, p[1]); nor.push(0, up, 0); }
      // triangulated in (x, -z): CCW there faces -y after mapping back, so flip for the top
      for (const t of tris) {
        const flip = (up > 0) !== cw;
        idx.push(base + t[0], base + (flip ? t[2] : t[1]), base + (flip ? t[1] : t[2]));
      }
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3));
    g.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
    g.setIndex(idx);
    return g;
  }
  function merge(list) {
    const parts = list.map((g) => (g.index ? g.toNonIndexed() : g));
    let count = 0;
    for (const g of parts) count += g.attributes.position.count;
    const pos = new Float32Array(count * 3), nor = new Float32Array(count * 3), uv = new Float32Array(count * 2);
    let o = 0;
    for (const g of parts) {
      pos.set(g.attributes.position.array, o * 3);
      if (g.attributes.normal) nor.set(g.attributes.normal.array, o * 3);
      if (g.attributes.uv) uv.set(g.attributes.uv.array, o * 2);
      o += g.attributes.position.count;
    }
    for (const g of list) g.dispose();
    for (const g of parts) g.dispose();
    const out = new THREE.BufferGeometry();
    out.setAttribute("position", new THREE.BufferAttribute(pos, 3));
    out.setAttribute("normal", new THREE.BufferAttribute(nor, 3));
    out.setAttribute("uv", new THREE.BufferAttribute(uv, 2));
    out.computeBoundingSphere();
    return out;
  }
  const at = (g, x, y, z, rx = 0, ry = 0, rz = 0) => {
    if (rx || ry || rz) g.applyMatrix4(new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(rx, ry, rz)));
    g.translate(x, y, z);
    return g;
  };
  return { sweep, slabX, slabZ, bar, capSlab, merge, at };
}

// The case plan: spine straight on the left, rounded tail, a gently concave bentside, a short straight treble cheek.
// Returned as world (x, z) points from the front-left corner round to the front-right corner.
function caseOutline(THREE) {
  const W = G.halfW, f = -G.front;
  const p = new THREE.Path();
  p.moveTo(-W, f);
  p.lineTo(-W, 50);
  p.bezierCurveTo(-W, 72, -6, 82, -1, 74);
  p.bezierCurveTo(5, 64.4, 24, 27, W, 17);
  p.lineTo(W, f);
  const out = [];
  for (const v of p.getSpacedPoints(220)) {
    const q = [v.x, -v.y], last = out[out.length - 1];
    if (!last || Math.hypot(q[0] - last[0], q[1] - last[1]) > 1e-3) out.push(q);
  }
  return out;
}

function grainTexture(THREE) {
  const c = document.createElement("canvas");
  c.width = c.height = 512;
  const g = c.getContext("2d");
  g.fillStyle = "#8d6c47";
  g.fillRect(0, 0, 512, 512);
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 260; i++) {
    const x = rnd() * 512, w = 0.6 + rnd() * 2.6, light = rnd() < 0.5;
    g.fillStyle = light ? `rgba(236,205,160,${0.05 + rnd() * 0.12})` : `rgba(60,38,20,${0.05 + rnd() * 0.16})`;
    g.fillRect(x, 0, w, 512);
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(1 / 26, 1 / 26);
  t.rotation = 0.55;
  return t;
}

export default {
  id: "glass-piano",
  name: "Crystal Grand",
  keyStyle: KEY_STYLE,
  hints: HINTS,

  create(ctx) {
    const { THREE, scene } = ctx;
    const B = makeBuilders(THREE);
    const KEY = ctx.KEY || { first: 21, last: 108 };
    const first = KEY.first, N = KEY.last - KEY.first + 1;
    const keyX = ctx.keyX || ((m) => (m - 21 - 43.5) * 52 / 88);
    const span = ctx.span || {};
    const left = span.left ?? keyX(first) - 0.5, right = span.right ?? keyX(KEY.last) + 0.5;
    const options = { lid: "auto", glass: "crystal", desk: true, edge: 1, ...(ctx.options || {}) };
    let heroPose = false;  // the lab's hero view poses the lid on its long prop; the page takes it off so action and sky stay clear
    const fallbackColor = (m, vel, target) => target.setHSL(((m % 12) * 7 % 12) / 12, 0.9, 0.5);
    const noteColor = ctx.noteColor || fallbackColor;
    const floorY = ctx.floorY ?? G.floorY;

    const group = new THREE.Group();
    group.name = "instrument:glass-piano";
    group.position.x = (left + right) / 2;
    group.scale.setScalar((right - left) / 52);
    scene.add(group);
    const geos = [], mats = [], texs = [];
    const add = (mesh) => { group.add(mesh); return mesh; };

    // ---------------------------------------------------------------- materials --
    const edgeBase = new THREE.Color(EDGE.color).multiplyScalar(EDGE.gain);
    const edgeU = { value: edgeBase.clone() }, edgePow = { value: EDGE.pow };
    const strikeU = { value: new THREE.Color(0, 0, 0) }, strikePow = { value: EDGE.strikePow };
    let edgeScale = 1;
    // each glass program's uniforms: the renderer puts its transmission render target's texture in them (see dispose)
    const glassUniforms = new Set();
    const glassHook = (sh) => {
      glassUniforms.add(sh.uniforms);
      sh.uniforms.uEdge = edgeU;
      sh.uniforms.uEdgePow = edgePow;
      sh.uniforms.uStrike = strikeU;
      sh.uniforms.uStrikePow = strikePow;
      sh.fragmentShader = "uniform vec3 uEdge;\nuniform float uEdgePow;\nuniform vec3 uStrike;\nuniform float uStrikePow;\n" + sh.fragmentShader.replace("#include <emissivemap_fragment>",
        "#include <emissivemap_fragment>\n{ float fr = 1.0 - clamp(abs(dot(normal, normalize(vViewPosition))), 0.0, 1.0);\n  totalEmissiveRadiance += uEdge * pow(fr, uEdgePow) + uStrike * pow(fr, uStrikePow); }");
    };
    // one program, two materials: the case walls and the thicker legs/lyre share the uniforms above
    const makeGlass = (thickness) => {
      const m = new THREE.MeshPhysicalMaterial({
        color: GLASS.color, roughness: GLASS.roughness, metalness: 0, transmission: 1, thickness, ior: GLASS.ior,
        attenuationColor: new THREE.Color(GLASS.attenuationColor), attenuationDistance: GLASS.attenuationDistance,
        specularIntensity: 1, clearcoat: 0.6, clearcoatRoughness: 0.04,
      });
      m.onBeforeCompile = glassHook;
      m.customProgramCacheKey = () => "glass-piano-crystal";
      return m;
    };
    const glass = makeGlass(GLASS.thickness), glassLeg = makeGlass(GLASS.legThickness);
    const gold = new THREE.MeshPhysicalMaterial({ color: 0xc8a052, metalness: 0.55, roughness: 0.36, clearcoat: 0.5, clearcoatRoughness: 0.25 });
    const brass = new THREE.MeshPhysicalMaterial({ color: 0xd9b46c, metalness: 0.7, roughness: 0.28 });
    const grain = grainTexture(THREE);
    texs.push(grain);
    const spruce = new THREE.MeshPhysicalMaterial({ color: 0x957250, map: grain, roughness: 0.66 });
    const maple = new THREE.MeshPhysicalMaterial({ color: 0xc49a66, roughness: 0.55 });
    const dark = new THREE.MeshPhysicalMaterial({ color: 0x2b2019, roughness: 0.5, clearcoat: 0.4 });
    const steel = new THREE.MeshPhysicalMaterial({ color: 0xaeb4bd, metalness: 0.6, roughness: 0.3 });
    const felt = new THREE.MeshPhysicalMaterial({ color: 0xe6e0d2, roughness: 0.9, sheen: 0.8, sheenRoughness: 0.6, sheenColor: new THREE.Color(0xffffff) });
    felt.onBeforeCompile = (sh) => {
      sh.vertexShader = "attribute vec3 aGlow;\nattribute float aTip;\nvarying vec3 vGlow;\n" + sh.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\nvGlow = aGlow * aTip;");
      sh.fragmentShader = "varying vec3 vGlow;\n" + sh.fragmentShader.replace("#include <emissivemap_fragment>", "#include <emissivemap_fragment>\ntotalEmissiveRadiance += vGlow;");
    };
    felt.customProgramCacheKey = () => "glass-piano-felt";
    // The strings must stay in the OPAQUE list: a transparent material drops out of three's transmission pass, and the
    // whole case is transmission 1 — the lit strings would vanish behind the desk and the rim. CustomBlending gives plain
    // "over" compositing without the transparent flag (three applies the blend either way), so a string at rest, alpha 1,
    // composites exactly as the opaque ribbon it replaces, and only a vibrating one goes translucent.
    const strU = {
      uRes: { value: new THREE.Vector2(1920, 1080) },
      uTime: { value: 0 },
      uNote: { value: new Float32Array(N * 4) },        // rgb = the note's light, w = its swing amplitude in units
      uMinPx: { value: STRING_MIN_PX }, uRestHalf: { value: STRING_W / 2 }, uWobble: { value: VIB_WOBBLE },
      uDensCap: { value: BLUR_DENS_CAP }, uDensNorm: { value: BLUR_DENS_NORM }, uConserve: { value: BLUR_CONSERVE },
    };
    const stringMat = new THREE.ShaderMaterial({
      uniforms: strU, vertexShader: stringVert(N), fragmentShader: STRING_FRAG,
      transparent: false, blending: THREE.CustomBlending, blendSrc: THREE.SrcAlphaFactor, blendDst: THREE.OneMinusSrcAlphaFactor,
      depthWrite: false, side: THREE.DoubleSide,
    });
    stringMat.customProgramCacheKey = () => "glass-piano-strings";
    mats.push(glass, glassLeg, gold, brass, spruce, maple, dark, steel, felt, stringMat);

    function applyGlass(mode) {
      const fast = mode === "fast";
      for (const m of [glass, glassLeg]) {
        m.transmission = fast ? 0 : 1;
        m.transparent = fast;
        m.opacity = fast ? GLASS.fastOpacity : 1;
        m.depthWrite = !fast;
        m.color.set(fast ? GLASS.fastColor : GLASS.color);
        m.needsUpdate = true;
      }
    }
    function applyEdge() {
      edgeScale = Math.max(0, Math.min(2, Number(options.edge ?? 1) || 0));
      edgeU.value.copy(edgeBase).multiplyScalar(edgeScale);
    }

    // ---------------------------------------------------------------- the plan --
    const outline = caseOutline(THREE);                 // U path, front-left round to front-right
    const innerRim = insetPoly(outline, G.rimTh);        // same indices
    const hitchPoly = insetPoly(outline, G.rimTh + 1.6);
    const strutPoly = insetPoly(outline, G.rimTh + 1.3);

    // ---------------------------------------------------------------- crystal body (one draw) --
    const W = G.halfW, bi = G.blockInner;
    const bodyParts = [
      B.sweep(pathRings(outline, false), rrect(-G.rimTh, 0, G.rimBottom, G.rimTop, 0.45), true),               // rim
      B.slabZ(G.blockFront, G.front, -W, -bi, G.bedBottom, 1.45, 0.45),                                         // key blocks
      B.slabZ(G.blockFront, G.front, bi, W, G.bedBottom, 1.45, 0.45),
      B.slabX(-bi, bi, 3.2, G.front, G.bedBottom, G.bedTop, 0.1),                                               // keybed
      B.slabX(-bi, bi, G.blockFront, 3.2, G.bedBottom, -0.28, 0.18),                                            // key slip
      B.slabX(-W, W, G.front, G.gap0, G.rimBottom, G.bedBottom, 0.1),                                           // belly
      B.slabX(-bi, bi, -3.72, -4.95, -0.55, 2.75, 0.35),                                                        // fallboard
      B.slabX(-15.5, 15.5, -5.0, -6.3, G.plateY1, 2.9, 0.2),                                                    // desk rest
    ];
    const leg = (x, z, top) => {
      const h = top - floorY - 0.9, pts = [[2.2, 0], [2.2, -0.5], [1.6, -1.2], [1.85, -4], [1.25, -h + 2.6], [1.55, -h + 0.5], [1.4, -h]];
      return B.at(new THREE.LatheGeometry(pts.map((p) => new THREE.Vector2(p[0], p[1])), 28), x, top, z);
    };
    // legs, lyre and pedal box: one draw in the thicker-walled acrylic, so they read as crystal columns
    const legParts = [leg(-28.9, -0.4, G.bedBottom), leg(28.9, -0.4, G.bedBottom), leg(-8, -64, G.rimBottom)];
    const lyreTop = G.rimBottom, boxTop = floorY + 3.0;
    for (const x of [-2.9, 2.9]) legParts.push(B.at(new THREE.CylinderGeometry(0.42, 0.52, lyreTop - boxTop, 16), x, (lyreTop + boxTop) / 2, -5.8));
    legParts.push(B.slabX(-5.8, 5.8, -4.1, -7.6, floorY + 1.1, boxTop, 0.4));                                    // pedal box
    for (const x of [-4.2, 4.2]) {                                                                               // lyre braces
      const g = new THREE.CylinderGeometry(0.22, 0.22, 1, 10);
      const a = [x, boxTop, -7.2], b = [x * 0.6, lyreTop, -12.5];
      const len = Math.hypot(b[1] - a[1], b[2] - a[2]);
      g.scale(1, len, 1);
      g.applyMatrix4(new THREE.Matrix4().makeRotationX(Math.atan2(b[2] - a[2], b[1] - a[1])));
      g.applyMatrix4(new THREE.Matrix4().makeRotationZ(-Math.atan2(b[0] - a[0], b[1] - a[1])));
      g.translate((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (a[2] + b[2]) / 2);
      legParts.push(g);
    }
    const bodyGeo = B.merge(bodyParts), legGeo = B.merge(legParts);
    const body = add(new THREE.Mesh(bodyGeo, glass));
    add(new THREE.Mesh(legGeo, glassLeg));
    geos.push(bodyGeo, legGeo);

    // music desk (glass) and its etched chord name
    const deskGroup = new THREE.Group();
    deskGroup.position.set(0, 2.9, -5.6);
    deskGroup.rotation.x = -14 * DEG;
    add(deskGroup);
    const deskGeo = B.merge([B.slabX(-15, 15, 0.22, -0.22, 0, 9.5, 0.12), B.slabX(-15, 15, 0.95, -0.22, -0.2, 0.45, 0.15)]);
    deskGroup.add(new THREE.Mesh(deskGeo, glass));
    geos.push(deskGeo);
    const etchCanvas = document.createElement("canvas");
    etchCanvas.width = 1024;
    etchCanvas.height = 256;
    const etchTex = new THREE.CanvasTexture(etchCanvas);
    etchTex.colorSpace = THREE.SRGBColorSpace;
    texs.push(etchTex);
    const etchMat = new THREE.MeshBasicMaterial({ map: etchTex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, color: 0x000000, toneMapped: true });
    mats.push(etchMat);
    const etchGeo = new THREE.PlaneGeometry(22, 5.5);
    geos.push(etchGeo);
    const etch = new THREE.Mesh(etchGeo, etchMat);
    etch.position.set(0, 5.4, 0.3);
    etch.renderOrder = 2;
    deskGroup.add(etch);

    // lid and prop (glass), hinged on the spine
    const lidPoly = resample(clipPolyZ(outline, G.lidFrontZ), 1.0, true).map((p) => [p[0] + W, p[1]]);
    const lidGeo = B.merge([
      B.sweep(pathRings(lidPoly, true), [[-0.7, 0], [-0.05, 0], [0.09, 0.06], [0.15, 0.2], [0.15, 0.35], [0.09, 0.49], [-0.05, 0.55], [-0.7, 0.55]], false),
      B.capSlab(insetPoly(lidPoly, 0.7), 0, G.lidTh),
    ]);
    geos.push(lidGeo);
    const lid = add(new THREE.Mesh(lidGeo, glass));
    lid.position.set(-W, G.rimTop, 0);
    const propGeo = new THREE.CylinderGeometry(0.3, 0.3, 1, 14);
    geos.push(propGeo);
    const prop = add(new THREE.Mesh(propGeo, glass));
    let propBase = [24, -36];
    { let best = Infinity;
      for (const p of insetPoly(outline, G.rimTh / 2)) if (p[0] > 0 && Math.abs(p[1] + 36) < best) { best = Math.abs(p[1] + 36); propBase = p; } }
    function applyLid(want) {
      // auto: lid off on the page (render 2026-09-15: even the short prop veiled the action in 9:16), long prop for the hero
      let mode = want === "auto" ? (heroPose ? "long" : "off") : want;
      if (portrait && mode === "long") mode = "short";  // judge 2026-09-15: a raised lid sat in the air the 9:16 note bars need
      const th = (LID_ANGLE[mode] ?? 10) * DEG;
      lid.visible = mode !== "off";
      lid.rotation.z = th;
      prop.visible = mode === "long" || mode === "short";
      const len = (propBase[0] + W) * Math.sin(th);
      prop.scale.set(1, Math.max(len, 0.01), 1);
      prop.rotation.z = th;
      prop.position.set(propBase[0] - Math.sin(th) * len / 2, G.rimTop + Math.cos(th) * len / 2, propBase[1]);
    }

    // ---------------------------------------------------------------- plate, soundboard, rails --
    const plateParts = [
      B.slabX(-30.3, 30.3, -5.0, G.gap0, G.plateY0, G.plateY1, 0.25),
      B.slabX(-30.4, 30.4, G.gap1, G.gap1 - 1.6, G.plateY0, G.plateY1, 0.25),
      B.sweep(pathRings(clipLineZ(innerRim, G.gap0), false), rrect(-2.6, 0, G.plateY0, G.plateY1, 0.2), true),
    ];
    for (const [x0, dx] of [[-11.3, 0.45], [6.5, 0.15], [19, 0]]) {
      const d = norm2(dx, -1);
      let L = 2;
      while (L < 90 && inside(strutPoly, x0 + d[0] * L, G.gap1 - 1.6 + d[1] * L)) L += 0.5;
      plateParts.push(B.bar(x0, G.gap1 - 1.2, x0 + d[0] * L, G.gap1 - 1.6 + d[1] * L, 0.6, G.plateY0, G.plateY1, 0.2));
    }
    const plateGeo = B.merge(plateParts);
    geos.push(plateGeo);
    add(new THREE.Mesh(plateGeo, gold));

    const boardPoly = clipPolyZ(innerRim, G.gap0);
    const boardShape = new THREE.Shape(boardPoly.map((p) => new THREE.Vector2(p[0], -p[1])));
    const boardGeo = new THREE.ShapeGeometry(boardShape, 1);
    boardGeo.rotateX(-Math.PI / 2);
    boardGeo.translate(0, G.boardY, 0);
    geos.push(boardGeo);
    add(new THREE.Mesh(boardGeo, spruce));

    // wood: hammer flange rail, rest rail, damper guide rail
    const hx0 = -26, pitch = 52 / N;
    const hammerX = (i) => hx0 + (i + 0.5) * pitch;
    const pivotZ = G.strikeZ + G.shank;
    const damperCount = Math.max(0, Math.min(N, 88 - first + 1));
    const woodGeo = B.merge([
      B.slabX(-26.6, 26.6, pivotZ + 0.5, pivotZ - 0.5, -1.6, -1.1, 0.12),
      B.slabX(-26.6, 26.6, -10.4, -11.2, -1.4, -1.08, 0.1),
      B.slabX(-26.4, hammerX(damperCount - 1) + 0.5, G.damperZ + 0.5, G.damperZ - 0.5, 0.35, 0.75, 0.1),
    ]);
    geos.push(woodGeo);
    add(new THREE.Mesh(woodGeo, dark));

    const brassParts = [];
    for (const x of [-26.9, -13.3, 13.3, 26.9]) brassParts.push(B.slabZ(-6.2, -8.8, x - 0.15, x + 0.15, G.bedBottom, -1.12, 0.05));
    for (const z of [-20, -42]) brassParts.push(B.slabZ(z + 1.2, z - 1.2, -W - 0.12, -W + 0.5, G.rimTop - 0.4, G.rimTop + 0.08, 0.08));
    const caster = (x, z) => B.at(new THREE.LatheGeometry([[0, 0], [1.2, 0], [1.5, 0.35], [1.45, 0.8], [1.1, 0.95], [0, 0.95]].map((p) => new THREE.Vector2(p[0], p[1])), 20), x, floorY, z);
    brassParts.push(caster(-28.9, -0.4), caster(28.9, -0.4), caster(-8, -64));
    const brassGeo = B.merge(brassParts);
    geos.push(brassGeo);
    add(new THREE.Mesh(brassGeo, brass));

    // ---------------------------------------------------------------- strings and pins --
    const strings = [];     // [key index, x front, y, z pin, x back, z back]
    const keyStr0 = new Uint16Array(N), keyStrN = new Uint8Array(N);
    for (let i = 0; i < N; i++) {
      const m = first + i, n = m <= 28 ? 1 : m <= 47 ? 2 : 3, bass = m < 48;
      const raw = 2.2 * Math.pow(1.94, (108 - m) / 12);
      let L = 62 * (1 - Math.exp(-raw / 62));
      const d = norm2(bass ? 0.45 : 0, -1), y = bass ? G.bassStrY : G.strY;
      keyStr0[i] = strings.length;
      keyStrN[i] = n;
      for (let s = 0; s < n; s++) {
        const xf = hammerX(i) + (n === 1 ? 0 : (s - (n - 1) / 2) * (n === 2 ? 0.16 : 0.14));
        let l = L;
        while (l > 1 && !inside(hitchPoly, xf + d[0] * l, G.agraffeZ + d[1] * l)) l -= 0.4;
        strings.push([i, xf, y, -5.7 - (strings.length % 3) * 1.1, xf + d[0] * l, G.agraffeZ + d[1] * l]);
      }
    }
    // A string is a screen-space ribbon: its width is set in the vertex shader, so it can widen into a vibration blur
    // without ever becoming a hairline that aliases. The speaking length is subdivided so sin(pi u) has somewhere to go;
    // the pin-to-agraffe stretch never moves and stays dimmed to 0.6 as it always was.
    const NS = strings.length;
    const SPEAK_SPANS = 8;
    const NODES = 2 + SPEAK_SPANS + 1;                 // pin, agraffe | agraffe ... hitch
    const SV = NODES * 2, TRIS = (1 + SPEAK_SPANS) * 2;
    const sPos = new Float32Array(NS * SV * 3), sBase = new Float32Array(NS * SV * 3), sDir = new Float32Array(NS * SV * 3);
    const sParam = new Float32Array(NS * SV * 4), sVib = new Float32Array(NS * SV * 2);
    const sIdx = new Uint16Array(NS * TRIS * 3);
    strings.forEach(([i, xf, y, zp, xb, zb], k) => {
      const m = first + i;
      const base = m < 41 ? [0.13, 0.065, 0.028] : [0.15, 0.155, 0.17];
      const nodes = [[xf, G.plateY1 + 0.55, zp, 0, 0.6], [xf, y, G.agraffeZ, 0, 0.6]];
      for (let q = 0; q <= SPEAK_SPANS; q++) {
        const f = q / SPEAK_SPANS;
        nodes.push([mix(xf, xb, f), y, mix(G.agraffeZ, zb, f), f, 1]);
      }
      const dir = (a, b) => { const d = [b[0] - a[0], b[1] - a[1], b[2] - a[2]], l = Math.hypot(d[0], d[1], d[2]) || 1; return [d[0] / l, d[1] / l, d[2] / l]; };
      const d0 = dir(nodes[0], nodes[1]), d1 = dir(nodes[2], nodes[NODES - 1]);
      const l = k - keyStr0[i], n = keyStrN[i];                              // this string's place in its unison group
      const phase = (k * 2.39996323) % (2 * Math.PI);
      const om = 2 * Math.PI * overPitch(m, VIB_HZ_BASS, VIB_HZ_TREBLE) * (1 + VIB_DETUNE * (l - (n - 1) / 2));
      const v0 = k * SV;
      for (let q = 0; q < NODES; q++) {
        const nd = nodes[q], d = q < 2 ? d0 : d1;
        for (let side = 0; side < 2; side++) {
          const v = v0 + q * 2 + side, o3 = v * 3;
          sPos[o3] = nd[0]; sPos[o3 + 1] = nd[1]; sPos[o3 + 2] = nd[2];
          sBase[o3] = base[0] * nd[4]; sBase[o3 + 1] = base[1] * nd[4]; sBase[o3 + 2] = base[2] * nd[4];
          sDir[o3] = d[0]; sDir[o3 + 1] = d[1]; sDir[o3 + 2] = d[2];
          const o4 = v * 4;
          sParam[o4] = nd[3]; sParam[o4 + 1] = side ? 1 : -1; sParam[o4 + 2] = nd[4]; sParam[o4 + 3] = i;
          sVib[v * 2] = phase; sVib[v * 2 + 1] = om;
        }
      }
      let ti = k * TRIS * 3;
      const quad = (a) => { sIdx[ti++] = a; sIdx[ti++] = a + 2; sIdx[ti++] = a + 1; sIdx[ti++] = a + 1; sIdx[ti++] = a + 2; sIdx[ti++] = a + 3; };
      quad(v0);
      for (let q = 0; q < SPEAK_SPANS; q++) quad(v0 + (2 + q) * 2);
    });
    const stringGeo = new THREE.BufferGeometry();
    stringGeo.setAttribute("position", new THREE.BufferAttribute(sPos, 3));
    stringGeo.setAttribute("aBase", new THREE.BufferAttribute(sBase, 3));
    stringGeo.setAttribute("aDir", new THREE.BufferAttribute(sDir, 3));
    stringGeo.setAttribute("aParam", new THREE.BufferAttribute(sParam, 4));
    stringGeo.setAttribute("aVib", new THREE.BufferAttribute(sVib, 2));
    stringGeo.setIndex(new THREE.BufferAttribute(sIdx, 1));
    stringGeo.computeBoundingSphere();
    geos.push(stringGeo);
    const stringMesh = add(new THREE.Mesh(stringGeo, stringMat));
    stringMesh.renderOrder = 1;                        // after the plate and soundboard, so it blends over them
    stringMesh.frustumCulled = false;
    const strViewport = new THREE.Vector4();
    stringMesh.onBeforeRender = (renderer) => {        // the pass actually drawing: the transmission target is its own size
      renderer.getCurrentViewport(strViewport);
      strU.uRes.value.set(strViewport.z, strViewport.w);
    };

    const pinGeo = new THREE.CylinderGeometry(0.075, 0.075, 0.55, 6);
    pinGeo.translate(0, 0.275, 0);
    geos.push(pinGeo);
    const pins = add(new THREE.InstancedMesh(pinGeo, steel, NS));
    const m4 = new THREE.Matrix4();
    strings.forEach(([, xf, , zp], k) => pins.setMatrixAt(k, m4.makeTranslation(xf, G.plateY1, zp)));
    pins.frustumCulled = false;

    // ---------------------------------------------------------------- hammers --
    const shankGeo = B.merge([
      B.at(new THREE.CylinderGeometry(0.075, 0.075, G.shank + 0.3, 6), 0, 0, -(G.shank + 0.3) / 2 + 0.15, Math.PI / 2),
      new THREE.BoxGeometry(0.3, 0.42, 0.6).translate(0, -0.1, 0.05),
    ]);
    const headGeo = B.sweep(pathRings([[-0.22, 0], [0.22, 0]], false), [[-0.2, 0.05], [0.2, 0.05], [0.2, 0.38], [0.3, 0.5], [0.355, 0.68], [0.35, 0.86], [0.31, 1.02], [0.24, 1.16], [0.14, 1.26], [0, 1.3], [-0.14, 1.26], [-0.24, 1.16], [-0.31, 1.02], [-0.35, 0.86], [-0.355, 0.68], [-0.3, 0.5], [-0.2, 0.38]], true);
    headGeo.translate(0, 0.09, -G.shank);
    { const p = headGeo.attributes.position, tip = new Float32Array(p.count);
      for (let v = 0; v < p.count; v++) { const s = clamp01((p.getY(v) - 0.09 - 0.5) / 0.8); tip[v] = 0.15 + 0.85 * s * s * (3 - 2 * s); }
      headGeo.setAttribute("aTip", new THREE.BufferAttribute(tip, 1)); }
    const glowArr = new Float32Array(N * 3);
    const glowAttr = new THREE.InstancedBufferAttribute(glowArr, 3).setUsage(THREE.DynamicDrawUsage);
    headGeo.setAttribute("aGlow", glowAttr);
    geos.push(shankGeo, headGeo);
    const shanks = add(new THREE.InstancedMesh(shankGeo, maple, N));
    const heads = add(new THREE.InstancedMesh(headGeo, felt, N));
    shanks.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    heads.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    shanks.frustumCulled = heads.frustumCulled = false;
    const aTop = new Float32Array(N);
    for (let i = 0; i < N; i++) aTop[i] = Math.asin(Math.min(0.9, ((first + i < 48 ? G.bassStrY : G.strY) - 0.03 - G.restTop) / G.shank));

    // ---------------------------------------------------------------- dampers and pedals --
    const damperGeo = B.merge([
      B.slabX(-0.21, 0.21, 0.55, -0.55, 0, 0.85, 0.08),
      new THREE.CylinderGeometry(0.035, 0.035, 4.2, 5).translate(0, -2.1, 0),
    ]);
    geos.push(damperGeo);
    const dampers = damperCount > 0 ? add(new THREE.InstancedMesh(damperGeo, dark, damperCount)) : null;
    if (dampers) { dampers.instanceMatrix.setUsage(THREE.DynamicDrawUsage); dampers.frustumCulled = false; }
    const pedalGeo = B.sweep(pathRings([[0, 0], [0, 3.3]], false), rrect(-0.36, 0.36, -0.14, 0.14, 0.1), true);
    geos.push(pedalGeo);
    const pedals = add(new THREE.InstancedMesh(pedalGeo, brass, 3));
    pedals.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    const pedalY = floorY + 2.0;

    // ---------------------------------------------------------------- reactive state --
    const strikeT = new Float64Array(N).fill(-1e9), strikeV = new Float32Array(N), strikeCol = new Float32Array(N * 3);
    const held = new Uint8Array(N), topHit = new Uint8Array(N), ang = new Float32Array(N), shownAng = new Float32Array(N).fill(NaN);
    const lift = new Float32Array(damperCount), shownLift = new Float32Array(damperCount).fill(NaN), strLevel = new Float32Array(N);
    // The light envelope (the tuning table at the top): body = floor + prompt + aftersound, plus the strike flash. It is
    // integrated, not recomputed from the strike clock, so a re-strike carries the level it finds, a sound's end fades
    // instead of snapping, and a pedal PRESS never resurrects a note the page has already ended.
    const bFloor = new Float32Array(N), bPrompt = new Float32Array(N), bAfter = new Float32Array(N);
    const bodyLvl = new Float32Array(N), flash = new Float32Array(N), vibGate = new Float32Array(N), shownAmp = new Float32Array(N);
    const dampT = new Float32Array(N);                               // seconds into the damper's fade, 0 while it sounds
    const alive = new Uint8Array(N), seenStrike = new Uint32Array(N);
    const lastNote = new Float64Array(N).fill(-Infinity);            // the strike ring's high-water mark per key
    const riseT = new Float64Array(N).fill(-1e9);                    // the hammer is still in flight until then
    const tauPrompt = new Float32Array(N), tauAfter = new Float32Array(N), ampMax = new Float32Array(N);
    for (let i = 0; i < N; i++) {
      tauPrompt[i] = overPitch(first + i, TAU_PROMPT_BASS, TAU_PROMPT_TREBLE);
      tauAfter[i] = overPitch(first + i, TAU_AFTER_BASS, TAU_AFTER_TREBLE);
      ampMax[i] = overPitch(first + i, AMP_BASS, AMP_TREBLE);
    }
    let seeded = false;
    const tmp = new THREE.Color(), edgeAcc = new THREE.Color(0, 0, 0), chordCol = new THREE.Color(0.6, 0.7, 1);
    const chordAcc = new THREE.Color();
    let chordN = 0, frameT = 0, active = true, pedalAng = 0, shownPedal = NaN, etchName = null, etchLevel = 0, etchFlash = 0;
    let framing = ctx.framing || null;
    let portrait = isPortrait(framing);

    // age > 0 seeds a sound that was already ringing when the crystal was mounted, or a strike the ring reports late: the
    // envelope is analytic, so it can simply be advanced. A strike never dips the light to dark first — whatever is still
    // showing above the new peak is folded into the prompt term and decays from there.
    function strike(m, vel, t0, age = 0) {
      const i = m - first;
      if (i < 0 || i >= N) return;
      const v = clamp01(vel > 1 ? vel / 127 : vel);
      const lit = bodyLvl[i] > 0;                     // this string is still showing light from a sound that has not ended
      strikeT[i] = t0;
      strikeV[i] = v;
      topHit[i] = 0;
      // The hammer's flight, 18-33 ms: a DARK string waits for it. A lit one must not — re-arming the gate on a re-strike
      // blanked the note to full dark for the frames before the new flash, throwing away the level the carry just kept.
      // The hammer arm still flies either way: it is animated off strikeT/strikeV, not off this gate.
      riseT[i] = lit ? -1e9 : t0 + (0.055 - 0.037 * v);
      noteColor(m, vel > 1 ? vel : vel * 127, tmp);
      strikeCol[i * 3] = tmp.r; strikeCol[i * 3 + 1] = tmp.g; strikeCol[i * 3 + 2] = tmp.b;
      const peak = Math.pow(v, PEAK_EXP), fl = peak * mix(FLOOR_LO, FLOOR_HI, v), above = peak - fl;
      const carry = Math.max(0, bodyLvl[i] - peak);
      bFloor[i] = fl;
      bPrompt[i] = (above * (1 - AFTER_SHARE) + carry) * Math.exp(-age / tauPrompt[i]);
      bAfter[i] = above * AFTER_SHARE * Math.exp(-age / tauAfter[i]);
      bodyLvl[i] = bFloor[i] + bPrompt[i] + bAfter[i];
      flash[i] = Math.max(flash[i], Math.pow(v, FLASH_EXP) * Math.exp(-age / TAU_FLASH));
      vibGate[i] = 1;
      dampT[i] = 0;                                   // a strike during the damper's fade reopens the window
      strLevel[i] = -1;                                 // the colour changed with the note: write it even at the same level
      const fade = age > 0 ? Math.exp(-age / EDGE.tau) : 1;
      edgeAcc.r += tmp.r * v * EDGE.strikeGain * fade; edgeAcc.g += tmp.g * v * EDGE.strikeGain * fade; edgeAcc.b += tmp.b * v * EDGE.strikeGain * fade;
    }
    function visitPressed(st, m) {                     // the etched chord name is what the FINGERS hold, as it always was
      const i = m - first;
      if (i < 0 || i >= N) return;
      noteColor(m, st.vel, tmp);
      chordAcc.r += tmp.r; chordAcc.g += tmp.g; chordAcc.b += tmp.b;
      chordN++;
    }
    // Daniel's lettering picks (Outfit, Raleway, Jost; OFL). The host's display face leads when it passes one. The etch
    // redraws when a web font finishes loading, so a first chord drawn in the fallback face gets replaced.
    const displayFace = ctx.fonts && ctx.fonts.display ? `${ctx.fonts.display}, ` : "";
    const NAME_FONT = `500 128px ${displayFace}Outfit, Jost, Raleway, "Segoe UI", sans-serif`;
    const NNS_FONT = '400 52px Raleway, Jost, Outfit, "Segoe UI", sans-serif';
    const fontSet = typeof document !== "undefined" && document.fonts ? document.fonts : null;
    let etchNns = "";
    const onFontsLoaded = () => { if (etchName) drawEtch(etchName, etchNns); };
    if (fontSet && fontSet.addEventListener) fontSet.addEventListener("loadingdone", onFontsLoaded);
    function drawEtch(name, nns) {
      etchNns = nns || "";
      const g = etchCanvas.getContext("2d");
      g.clearRect(0, 0, 1024, 256);
      if (!name) { etchTex.needsUpdate = true; return; }
      g.fillStyle = "#ffffff";
      g.textAlign = "center";
      g.textBaseline = "middle";
      g.font = NAME_FONT;
      g.fillText(name, 512, nns ? 104 : 128, 1000);
      if (nns) {
        g.globalAlpha = 0.6;
        g.font = NNS_FONT;
        g.fillText(nns, 512, 208, 1000);
        g.globalAlpha = 1;
      }
      etchTex.needsUpdate = true;
    }

    function reset() {
      strikeT.fill(-1e9); riseT.fill(-1e9); held.fill(0); ang.fill(0); lift.fill(0); strLevel.fill(-1);
      bFloor.fill(0); bPrompt.fill(0); bAfter.fill(0); bodyLvl.fill(0); flash.fill(0); vibGate.fill(0); dampT.fill(0);
      alive.fill(0); shownAmp.fill(0); strU.uNote.value.fill(0);
      seeded = false;
      edgeAcc.setRGB(0, 0, 0); etchLevel = 0; etchFlash = 0; pedalAng = 0;
      glowArr.fill(0); glowAttr.needsUpdate = true;
      strikeU.value.setRGB(0, 0, 0);
      etchMat.color.setRGB(0, 0, 0);
      pose(0);
    }

    function pose(dt) {
      let moved = false;
      for (let i = 0; i < N; i++) {
        if (shownAng[i] === ang[i]) continue;
        shownAng[i] = ang[i];
        m4.makeRotationX(ang[i]);
        m4.setPosition(hammerX(i), G.pivotY, pivotZ);
        shanks.setMatrixAt(i, m4);
        heads.setMatrixAt(i, m4);
        moved = true;
      }
      if (moved) { shanks.instanceMatrix.needsUpdate = true; heads.instanceMatrix.needsUpdate = true; }
      if (dampers) {
        let lifted = false;
        for (let i = 0; i < damperCount; i++) {
          if (shownLift[i] === lift[i]) continue;
          shownLift[i] = lift[i];
          m4.makeTranslation(hammerX(i), (first + i < 48 ? G.bassStrY : G.strY) + 0.03 + lift[i] * 0.5, G.damperZ);
          dampers.setMatrixAt(i, m4);
          lifted = true;
        }
        if (lifted) dampers.instanceMatrix.needsUpdate = true;
      }
      if (shownPedal !== pedalAng) {
        shownPedal = pedalAng;
        for (let k = 0; k < 3; k++) {
          m4.makeRotationX(k === 2 ? pedalAng : 0);
          m4.setPosition(-2.4 + 2.4 * k, pedalY, -4.1);
          pedals.setMatrixAt(k, m4);
        }
        pedals.instanceMatrix.needsUpdate = true;
      }
    }

    applyGlass(options.glass);
    applyEdge();
    applyLid(options.lid);
    deskGroup.visible = options.desk !== false;
    reset();

    return {
      group,
      keyStyle: KEY_STYLE,
      hints: HINTS,
      stage: { floorY },
      // lab cameras: a three-quarter from the front right (the open lid faces that way) and a close-up of the action
      views: {
        // fitted offline (judge 2026-09-15: the lid tip and tail were cropped): the case, the long-prop lid and the tail
        // sit inside +-0.9 NDC, centred; only the feet of the front legs leave the bottom edge
        hero: () => { heroPose = true; applyLid(options.lid); return { from: [106.4, 72.8, 78.7], target: [-7.3, 10.5, -23.4], fov: 30 }; },
        close: { from: [17, 12.5, -1.5], target: [-1.8, 1.2, -13], fov: 34 },
      },
      info: { hammers: N, strings: NS, dampers: damperCount, pins: NS, pedals: 3 },
      update(dt, t, state) {
        if (!active) return;
        dt = Math.min(Math.max(dt || 0, 0), 0.1);
        frameT = t;
        held.fill(0);
        alive.fill(0);
        chordAcc.setRGB(0, 0, 0);
        chordN = 0;
        if (state && state.pressed) state.pressed.forEach(visitPressed);
        const first0 = !seeded;
        seeded = true;
        // The sustain record (piano.js, the instrument-host header): an entry lives exactly while the page holds that
        // sound, finger or pedal. This is the whole of "the light lasts as long as the note does".
        const sounding = state && state.sounding;
        if (sounding) {
          for (const [m, e] of sounding) {
            const i = m - first;
            if (i < 0 || i >= N) continue;
            alive[i] = 1;
            held[i] = e.held ? 1 : 0;
            if (e.strike !== seenStrike[i]) {
              seenStrike[i] = e.strike;
              strike(m, e.vel, e.t0, first0 ? Math.max(0, t - e.t0) : 0);
              if (e.t0 > lastNote[i]) lastNote[i] = e.t0;     // the ring reports the same strike: do not count it twice
            }
          }
        } else if (state && state.pressed) {
          // A host with no sustain record (an older page, an embedder): fingers and the pedal, as this instrument read them before.
          state.pressed.forEach((st, m) => { const i = m - first; if (i >= 0 && i < N) { held[i] = 1; alive[i] = 1; } });
          const ped = !!(state && state.pedal);
          for (let i = 0; i < N; i++) if (!alive[i] && bodyLvl[i] > 0 && (ped ? i < damperCount : false)) alive[i] = 1;
        }
        // The strike ring: the only place a note struck and released inside one frame shows at all.
        const notes = state && state.notes;
        if (notes) {
          for (let k = 0; k < notes.length; k++) {
            const n = notes[k], i = n.midi - first;
            if (i < 0 || i >= N || !(n.t > lastNote[i]) || n.t > t + 0.05) continue;
            lastNote[i] = n.t;
            if (!first0) strike(n.midi, n.vel, n.t, Math.max(0, t - n.t));   // on the first frame the ring is history
          }
        }
        const pedal = !!(state && state.pedal);

        const eK = Math.exp(-dt / EDGE.tau);
        edgeAcc.r *= eK; edgeAcc.g *= eK; edgeAcc.b *= eK;
        const luma = 0.2126 * edgeAcc.r + 0.7152 * edgeAcc.g + 0.0722 * edgeAcc.b;
        if (luma > EDGE.maxLuma) { const s = EDGE.maxLuma / luma; edgeAcc.r *= s; edgeAcc.g *= s; edgeAcc.b *= s; }
        const peak = Math.max(edgeAcc.r, edgeAcc.g, edgeAcc.b);
        if (peak > EDGE.maxChannel) { const s = EDGE.maxChannel / peak; edgeAcc.r *= s; edgeAcc.g *= s; edgeAcc.b *= s; }
        strikeU.value.setRGB(edgeAcc.r * edgeScale, edgeAcc.g * edgeScale, edgeAcc.b * edgeScale);

        const kFlash = Math.exp(-dt / TAU_FLASH), kDamp = Math.exp(-dt / TAU_DAMP), kVibOff = Math.exp(-dt / TAU_VIB_OFF);
        const un = strU.uNote.value;
        let glowDirty = false;
        for (let i = 0; i < N; i++) {
          const age = t - strikeT[i], v = strikeV[i], rise = 0.055 - 0.037 * v;
          if (age >= 0 && age < rise) { const s = age / rise; ang[i] = aTop[i] * s * s; } else {
            let rem = dt;
            if (!topHit[i] && age >= rise && age < 2) { ang[i] = aTop[i]; topHit[i] = 1; rem = Math.min(dt, age - rise); }
            const goal = held[i] ? aTop[i] * CHECK : 0;
            ang[i] = Math.abs(ang[i] - goal) < 1e-4 ? goal : damp(ang[i], goal, held[i] ? 0.05 : 0.07, rem);
          }
          if (i < damperCount) {
            const goal = held[i] || pedal ? 1 : 0;
            lift[i] = Math.abs(lift[i] - goal) < 1e-3 ? goal : damp(lift[i], goal, goal ? 0.035 : 0.08, dt);
          }
          // the felt glow, still read straight off the strike clock (it is the crystal's bloom flash)
          const struck = age >= rise && age < 12;
          const g = struck ? GLOW.peak * v * v * Math.exp(-(age - rise) / GLOW.tau) + (held[i] ? GLOW.held * v : 0) : 0;
          const o = i * 3, gr = strikeCol[o] * g, gg = strikeCol[o + 1] * g, gb = strikeCol[o + 2] * g;
          if (glowArr[o] !== gr || glowArr[o + 1] !== gg || glowArr[o + 2] !== gb) { glowArr[o] = gr; glowArr[o + 1] = gg; glowArr[o + 2] = gb; glowDirty = true; }
          // the string light and its vibration blur, both alive exactly as long as the SOUND is
          flash[i] *= kFlash;
          if (flash[i] < 1e-4) flash[i] = 0;
          if (alive[i]) {                                 // sounding: the two-stage decay onto a velocity-scaled floor
            bPrompt[i] *= Math.exp(-dt / tauPrompt[i]);
            bAfter[i] *= Math.exp(-dt / tauAfter[i]);
            vibGate[i] = 1;
            if (dampT[i]) dampT[i] = 0;                   // it is sounding again: the damper's window reopens
          } else if (bodyLvl[i] > 0) {                    // the sound ended: the damper lands, a fade and not a snap
            dampT[i] += dt;
            bFloor[i] *= kDamp; bPrompt[i] *= kDamp; bAfter[i] *= kDamp;
            vibGate[i] *= kVibOff;                        // the string stops moving before its glow is gone
          }
          // the stored terms keep falling at TAU_DAMP; the window is applied on read, so it cannot compound frame to frame
          let b = bFloor[i] + bPrompt[i] + bAfter[i];
          if (dampT[i] > 0) b *= dampFade(dampT[i]);      // ... and it is over, all the way to rest, by DAMP_FADE
          if (b < 1.5e-3) { b = 0; bFloor[i] = 0; bPrompt[i] = 0; bAfter[i] = 0; vibGate[i] = 0; }
          bodyLvl[i] = b;
          const on = t >= riseT[i] ? 1 : 0;               // nothing lights while the hammer is still on its way
          let lvl = (b * STR_BODY_GAIN + flash[i] * STR_FLASH_GAIN) * on;
          if (lvl < 0.003) lvl = 0;
          const amp = b > 0 ? ampMax[i] * Math.pow(b, AMP_EXP) * vibGate[i] * on : 0;
          if (lvl !== strLevel[i] || amp !== shownAmp[i]) {
            strLevel[i] = lvl; shownAmp[i] = amp;
            const o4 = i * 4;
            un[o4] = strikeCol[o] * lvl; un[o4 + 1] = strikeCol[o + 1] * lvl; un[o4 + 2] = strikeCol[o + 2] * lvl;
            un[o4 + 3] = amp;
          }
        }
        if (glowDirty) glowAttr.needsUpdate = true;
        strU.uTime.value = t;
        pedalAng = Math.abs(pedalAng - (pedal ? -0.11 : 0)) < 1e-4 ? (pedal ? -0.11 : 0) : damp(pedalAng, pedal ? -0.11 : 0, 0.05, dt);
        pose(dt);

        // the etched chord name
        if (deskGroup.visible) {
          const chord = state && state.chord, name = chord && chord.name ? chord.name : null;
          if (name !== etchName) {
            // no flare in portrait: there the etch sits behind the note bars and would echo the page's chord header
            if (name) { drawEtch(name, chord.nns || ""); etchFlash = portrait ? 0 : ETCH.flash; }
            etchName = name;
          }
          if (chordN > 0) chordCol.setRGB(chordAcc.r / chordN, chordAcc.g / chordN, chordAcc.b / chordN);
          etchFlash *= Math.exp(-dt / ETCH.tau);
          etchLevel = damp(etchLevel, name ? ETCH.level : 0, name ? 0.08 : 0.4, dt);
          const e = etchLevel + etchFlash * (name ? 1 : 0);
          etchMat.color.setRGB(chordCol.r * e, chordCol.g * e, chordCol.b * e);
          etch.visible = e > 0.002;
        }
      },
      resize(f) { framing = f || framing; portrait = isPortrait(framing); heroPose = false; applyLid(options.lid); },
      setActive(on) {
        active = !!on;
        group.visible = active;
        if (!active) reset();
      },
      setOptions(o) {
        Object.assign(options, o || {});
        applyGlass(options.glass);
        applyEdge();
        applyLid(options.lid);
        deskGroup.visible = options.desk !== false;
      },
      get framing() { return framing; },
      dispose() {
        scene.remove(group);
        if (fontSet && fontSet.removeEventListener) fontSet.removeEventListener("loadingdone", onFontsLoaded);
        for (const g of geos) g.dispose();
        for (const m of mats) m.dispose();
        for (const t of texs) t.dispose();
        shanks.dispose(); heads.dispose(); pins.dispose(); pedals.dispose();
        if (dampers) dampers.dispose();
        // The renderer draws what is behind transmissive glass into a render target it makes on first use and keeps for
        // the page's life (full size, 4x multisampled, mipmapped). It is freed with the glass; a later transmissive
        // material (spectacle's, or the glass again) gets a new one on its next frame.
        const targets = new Set();
        for (const u of glassUniforms) {
          const t = u.transmissionSamplerMap && u.transmissionSamplerMap.value;
          if (t && t.renderTarget && t.renderTarget.isRenderTarget) targets.add(t.renderTarget);
        }
        for (const rt of targets) rt.dispose();
        glassUniforms.clear();
      },
    };
  },
};
