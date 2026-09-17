// Orrery of Light — arsenal/web/piano/instruments/light-deepseek-orrery.js (ES module, no imports)
// "Instruments of light" 2026-09-17. Theme: "the room listens" — an open vertical ring of thin dark rails around the
// keybed with a fan of light-bands rising away like a harp strung for an audience of stars. The bands ARE the strings;
// hammers of light strike them from below. Body stays near-invisible; the light owns the stage. Keys stay host-owned.
//
// Required qualities:
//  - STRIKE physical/velocity-truthful: hammer knocks up and rebounds; band bows in a travelling wavefront; bloom flash
//    only on the strike frame (v^2). Soft = small cool plume, hard = hot wide plume.
//  - SUSTAIN TRUTH via state.sounding (fallback pressed+pedal): held = glowing floor; pedalled = keeps life but cools
//    ~15%; pedal-up release damps ~0.3 s as a visible travelling fade. Pedal alone never lights an unstruck band.
//  - LOW NOTES = ornithopter wing blur: lower notes widen + phase-offset ghost harmonics rise; bass beats slow and wide.
// Surprises: lush chords breathe wind+fog; tense chords crackle; a braided bass-solo filament shows the dance (twists in
// contrary motion, colour follows interval consonance).
// Craft: fixed draw calls, no per-frame allocation, colour stays noteColor saturated, only the strike flash crosses bloom.

const TAU = Math.PI * 2;
const clamp = (v, a, b) => (v < a ? a : v > b ? b : v);
const clamp01 = (v) => (v < 0 ? 0 : v > 1 ? 1 : v);
const lerp = (a, b, t) => a + (b - a) * t;
const damp = (a, b, tau, dt) => b + (a - b) * Math.exp(-dt / Math.max(tau, 1e-4));

const LY0 = 1.1, LY1 = 40, HOT = 1.7, TOPY = 43, DEPTH0 = -1.5, DEPTH1 = -6.5, HAMMY = 0.3;
function stringsOf(m) { return m <= 28 ? 1 : m <= 40 ? 2 : 3; }
function noteBlur(m) { return clamp01((76 - m) / 55); }
function noteWidth(m) { return stringsOf(m) === 1 ? 1.2 : stringsOf(m) === 2 ? 0.7 : 0.19; }

const FOG_COUNT = 240, CRACKLE_COUNT = 96, FSEG = 96;

const bandVert = [
  "attribute vec3 aColor;", "attribute float aGlow;", "attribute float aBlur;", "attribute float aPhase;",
  "attribute float aStrike;", "attribute float aPlumeX;", "attribute float aPlume;", "attribute float aWind;",
  "varying vec3 vColor;", "varying float vGlow;", "varying float vBlur;", "varying float vStrike;",
  "varying float vPlume;", "varying float vPlumeX;", "varying float vPhase;", "varying float vU;",
  "varying float vAcross;", "varying float vWind;",
  "void main(){",
  " vColor=aColor; vGlow=aGlow; vBlur=aBlur; vStrike=aStrike; vPlume=aPlume; vPlumeX=aPlumeX; vPhase=aPhase; vWind=aWind;",
  " vU=uv.x; vAcross=uv.y*2.0-1.0;",
  " float sway=vWind*0.55*sin(vU*4.71239+aPhase*0.4);",
  " vec3 p=position; p.x+=sway;",
  " gl_Position=projectionMatrix*modelViewMatrix*instanceMatrix*vec4(p,1.0);",
  "}",
].join("\n");
const bandFrag = [
  "precision highp float;",
  "varying vec3 vColor;", "varying float vGlow;", "varying float vBlur;", "varying float vStrike;",
  "varying float vPlume;", "varying float vPlumeX;", "varying float vPhase;", "varying float vU;", "varying float vAcross;",
  "void main(){",
  " float edge=smoothstep(0.0,1.0,1.0-abs(vAcross));",
  " float core=pow(edge,1.8);",
  " float wing=0.50*sin(vU*9.42478+vPhase)+0.26*sin(vU*15.70796+vPhase*1.9)+0.16*sin(vU*21.99115+vPhase*2.6);",
  " wing/=0.92;",
  " float wingAmp=1.1*vBlur;",
  " float width=1.0+wingAmp*(0.35+0.65*wing);",
  " float skin=smoothstep(width*0.72,width,edge)-smoothstep(width,width*1.4,edge);",
  " float blurred=core*(1.0-0.55*vBlur)+skin*0.9*vBlur;",
  " float plume=vPlume*exp(-pow((vU-vPlumeX)*7.0,2.0))*(0.4+0.6*(1.0-abs(vAcross)));",
  " vec3 col=vColor*(0.10+0.90*vGlow)+vColor*plume*1.6+vColor*vStrike*2.6;",
  " float luma=dot(col,vec3(0.2126,0.7152,0.0722));",
  " col*=min(1.0,(0.82+vStrike*5.0)/max(luma,1e-4));",
  " float alpha=blurred*(0.35+0.65*vGlow)+plume*0.55+vStrike*0.85;",
  " gl_FragColor=vec4(col,alpha);",
  "}",
].join("\n");

const filVert = [
  "attribute vec3 aColor;", "attribute float aGlow;", "attribute float aTwist;", "attribute float aPhase;",
  "varying vec3 vColor;", "varying float vGlow;", "varying float vU;", "varying float vPhase;", "varying float vTwist;", "varying float vAcrossY;",
  "void main(){ vColor=aColor; vGlow=aGlow; vU=uv.x; vPhase=aPhase; vTwist=aTwist; vAcrossY=uv.y;",
  " gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0); }",
].join("\n");
const filFrag = [
  "precision highp float;",
  "varying vec3 vColor;", "varying float vGlow;", "varying float vU;", "varying float vPhase;", "varying float vTwist;", "varying float vAcrossY;",
  "void main(){",
  " float d=vAcrossY*2.0-1.0;",
  " float strand=exp(-d*d*56.0);",
  " float b2=exp(-pow(d+0.18*vTwist*sin(vU*37.69911+vPhase),2.0)*90.0);",
  " float a=strand+b2*0.7;",
  " gl_FragColor=vec4(vColor*(0.4+0.6*vGlow)*a, a);",
  "}",
].join("\n");

const moteVert = [
  "attribute vec3 aColor;", "attribute float aSize;", "attribute float aAlpha;", "attribute float aGlow;",
  "uniform float uScale;",
  "varying vec3 vColor;", "varying float vAlpha;", "varying float vGlow;",
  "void main(){ vColor=aColor; vAlpha=aAlpha; vGlow=aGlow;",
  " vec4 mv=modelViewMatrix*vec4(position,1.0);",
  " gl_PointSize=clamp(aSize*uScale/max(0.1,-mv.z),1.0,48.0);",
  " gl_Position=projectionMatrix*mv; }",
].join("\n");
const moteFrag = [
  "precision highp float;",
  "uniform sampler2D uSprite;",
  "varying vec3 vColor;", "varying float vAlpha;", "varying float vGlow;",
  "void main(){ vec4 s=texture2D(uSprite,gl_PointCoord);",
  " vec3 col=vColor*(0.4+0.6*vGlow);",
  " float luma=dot(col,vec3(0.2126,0.7152,0.0722));",
  " col*=min(1.0,0.7/max(luma,1e-4));",
  " gl_FragColor=vec4(col*s.rgb, s.a*vAlpha); }",
].join("\n");

export default {
  id: "light-deepseek-orrery",
  name: "Orrery of Light",
  hints: { hideStageBody: true, hideHostBody: true, floorY: -2.3 },

  create(ctx) {
    const { THREE, scene, keyX, noteColor, renderer } = ctx;
    const KEY = ctx.KEY || { first: 21, last: 108 };
    const span = ctx.span || { left: -26, right: 26 };
    const FIRST = KEY.first, LAST = KEY.last, COUNT = LAST - FIRST + 1;

    const group = new THREE.Group();
    group.name = "instrument:light-deepseek-orrery";
    const disposables = [];
    const own = (x) => { disposables.push(x); return x; };
    let disposed = false, active = false;

    const tmpColor = new THREE.Color();

    // cage
    const railMat = own(new THREE.LineBasicMaterial({ color: 0x2a2f3a, transparent: true, opacity: 0.55 }));
    const mkline = (pts) => own(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), railMat));
    const cage = new THREE.Group();
    cage.add(mkline([new THREE.Vector3(span.left - 0.6, -1.0, DEPTH0), new THREE.Vector3(span.left - 0.6, TOPY, DEPTH1)]));
    cage.add(mkline([new THREE.Vector3(span.right + 0.6, -1.0, DEPTH0), new THREE.Vector3(span.right + 0.6, TOPY, DEPTH1)]));
    cage.add(mkline([new THREE.Vector3(span.left - 0.6, TOPY, DEPTH1), new THREE.Vector3(0, TOPY + 0.6, DEPTH1 - 0.5), new THREE.Vector3(span.right + 0.6, TOPY, DEPTH1)]));
    group.add(cage);

    // bands
    const bandGeo = own(new THREE.PlaneGeometry(LY1 - LY0 + HOT, 1.0, 24, 1));
    bandGeo.rotateZ(-Math.PI / 2);
    const iGlow = new Float32Array(COUNT);
    const iBlur = new Float32Array(COUNT);
    const iPhase = new Float32Array(COUNT);
    const iStrike = new Float32Array(COUNT);
    const iPlumeX = new Float32Array(COUNT);
    const iPlume = new Float32Array(COUNT);
    const iWind = new Float32Array(COUNT);
    const iColor = new Float32Array(COUNT * 3);
    const bandMat = own(new THREE.ShaderMaterial({ vertexShader: bandVert, fragmentShader: bandFrag, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    const bands = new THREE.InstancedMesh(bandGeo, bandMat, COUNT);
    bands.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    bands.frustumCulled = false;
    const bandX = new Float32Array(COUNT);
    const bandZ = new Float32Array(COUNT);
    const bandW = new Float32Array(COUNT);
    const bandVel = new Float32Array(COUNT);
    const dummy = new THREE.Object3D();
    for (let i = 0; i < COUNT; i++) {
      const m = FIRST + i;
      const x = keyX(m), t = (m - FIRST) / (COUNT - 1);
      bandX[i] = x; bandZ[i] = lerp(DEPTH0, DEPTH1, t); bandW[i] = noteWidth(m);
      iBlur[i] = noteBlur(m);
      iPhase[i] = (i * 0.37) % TAU;
      noteColor(m, 100, tmpColor);
      iColor[i * 3] = tmpColor.r; iColor[i * 3 + 1] = tmpColor.g; iColor[i * 3 + 2] = tmpColor.b;
      iGlow[i] = 0; iStrike[i] = 0; iPlumeX[i] = 0; iPlume[i] = 0; iWind[i] = 0;
      dummy.position.set(x, LY0, bandZ[i]);
      dummy.scale.set(bandW[i], 1, 1);
      dummy.updateMatrix();
      bands.setMatrixAt(i, dummy.matrix);
    }
    bands.instanceMatrix.needsUpdate = true;
    // bind the per-note instanced attributes the band shader reads
    bandGeo.setAttribute("aColor", new THREE.InstancedBufferAttribute(iColor, 3));
    bandGeo.setAttribute("aGlow", new THREE.InstancedBufferAttribute(iGlow, 1));
    bandGeo.setAttribute("aBlur", new THREE.InstancedBufferAttribute(iBlur, 1));
    bandGeo.setAttribute("aPhase", new THREE.InstancedBufferAttribute(iPhase, 1));
    bandGeo.setAttribute("aStrike", new THREE.InstancedBufferAttribute(iStrike, 1));
    bandGeo.setAttribute("aPlumeX", new THREE.InstancedBufferAttribute(iPlumeX, 1));
    bandGeo.setAttribute("aPlume", new THREE.InstancedBufferAttribute(iPlume, 1));
    bandGeo.setAttribute("aWind", new THREE.InstancedBufferAttribute(iWind, 1));
    group.add(bands);

    // hammers
    const hammerGeo = own(new THREE.BoxGeometry(0.14, 1.0, 0.14));
    hammerGeo.translate(0, 0.5, 0);
    const hammerMat = own(new THREE.MeshBasicMaterial({ color: 0xffffff }));
    const hammers = new THREE.InstancedMesh(hammerGeo, hammerMat, COUNT);
    hammers.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
    hammers.frustumCulled = false;
    const hRise = new Float32Array(COUNT);
    const hT0 = new Float64Array(COUNT).fill(-1e9);
    const hd = new THREE.Object3D();
    for (let i = 0; i < COUNT; i++) {
      hd.position.set(bandX[i], HAMMY, bandZ[i]);
      hd.updateMatrix();
      hammers.setMatrixAt(i, hd.matrix);
      hammers.setColorAt(i, tmpColor.setHex(0x808080));
    }
    hammers.instanceMatrix.needsUpdate = true;
    group.add(hammers);

    // bass-solo filament
    const FV = (FSEG + 1) * 2;
    const filVerts = new Float32Array(FV * 3);
    const filColors = new Float32Array(FV * 3);
    const filUv = new Float32Array(FV * 2);
    const filIdx = new Uint16Array(FSEG * 6);
    const filGlowArr = new Float32Array(FV);
    const filTwistArr = new Float32Array(FV);
    const filPhaseArr = new Float32Array(FV);
    for (let s = 0; s <= FSEG; s++) { filUv[s * 4] = s / FSEG; filUv[s * 4 + 1] = 0; filUv[s * 4 + 2] = s / FSEG; filUv[s * 4 + 3] = 1; }
    for (let s = 0; s < FSEG; s++) { const a = s * 2, b = s * 2 + 1, c = s * 2 + 2, d = s * 2 + 3; filIdx.set([a, b, d, a, d, c], s * 6); }
    const filGeo = new THREE.BufferGeometry();
    filGeo.setAttribute("position", new THREE.BufferAttribute(filVerts, 3));
    filGeo.setAttribute("aColor", new THREE.BufferAttribute(filColors, 3));
    filGeo.setAttribute("aGlow", new THREE.BufferAttribute(filGlowArr, 1));
    filGeo.setAttribute("aTwist", new THREE.BufferAttribute(filTwistArr, 1));
    filGeo.setAttribute("aPhase", new THREE.BufferAttribute(filPhaseArr, 1));
    filGeo.setAttribute("uv", new THREE.BufferAttribute(filUv, 2));
    filGeo.setIndex(new THREE.BufferAttribute(filIdx, 1));
    own(filGeo);
    const filMat = own(new THREE.ShaderMaterial({ vertexShader: filVert, fragmentShader: filFrag, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
    const filament = new THREE.Mesh(filGeo, filMat);
    filament.frustumCulled = false;
    filament.visible = false;
    group.add(filament);
    let filTwist = 0, filPrevBassY = 0, filPrevSoloY = 0;

    // sprite
    const spriteTex = own((() => {
      const c = document.createElement("canvas"); c.width = c.height = 128;
      const g = c.getContext("2d");
      const grd = g.createRadialGradient(64, 64, 1, 64, 64, 64);
      grd.addColorStop(0, "rgba(255,255,255,1)"); grd.addColorStop(0.22, "rgba(255,255,255,0.72)");
      grd.addColorStop(0.55, "rgba(255,255,255,0.22)"); grd.addColorStop(1, "rgba(255,255,255,0)");
      g.fillStyle = grd; g.fillRect(0, 0, 128, 128);
      const tx = new THREE.CanvasTexture(c); tx.colorSpace = THREE.SRGBColorSpace; return tx;
    })());

    const makePoints = (count, uScaleRef) => {
      const geo = own(new THREE.BufferGeometry());
      const pos = new Float32Array(count * 3), col = new Float32Array(count * 3), sz = new Float32Array(count), al = new Float32Array(count), gl = new Float32Array(count);
      geo.setAttribute("position", new THREE.BufferAttribute(pos, 3));
      geo.setAttribute("aColor", new THREE.BufferAttribute(col, 3));
      geo.setAttribute("aSize", new THREE.BufferAttribute(sz, 1));
      geo.setAttribute("aAlpha", new THREE.BufferAttribute(al, 1));
      geo.setAttribute("aGlow", new THREE.BufferAttribute(gl, 1));
      const mat = own(new THREE.ShaderMaterial({ vertexShader: moteVert, fragmentShader: moteFrag, uniforms: { uSprite: { value: spriteTex }, uScale: uScaleRef }, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending }));
      const pts = new THREE.Points(geo, mat); pts.frustumCulled = false; group.add(pts);
      return pts;
    };
    const uScale = { value: 540 }; // drawingBufferHeight * 0.5, set on resize
    if (renderer) {
      const gl = renderer.getContext ? renderer.getContext() : null;
      uScale.value = (gl ? gl.drawingBufferHeight : renderer.domElement.height) * 0.5;
    }
    const fog = makePoints(FOG_COUNT, uScale);
    const crackle = makePoints(CRACKLE_COUNT, uScale);

    const strikeT = new Float64Array(COUNT).fill(-1e9);
    const glow = new Float32Array(COUNT);
    const plumeX = new Float32Array(COUNT);
    const plumeA = new Float32Array(COUNT);
    const strikeA = new Float32Array(COUNT);
    const heldNow = new Uint8Array(COUNT);
    let feelLush = 0, feelTense = 0;

    const fogPh = new Float32Array(FOG_COUNT);
    const fogSeed = new Float32Array(FOG_COUNT);
    let seed = 12345;
    const rnd = () => ((seed = (seed * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
    for (let i = 0; i < FOG_COUNT; i++) { fogPh[i] = rnd() * TAU; fogSeed[i] = rnd(); }
    const crackleT0 = new Float64Array(CRACKLE_COUNT).fill(-1e9);

    function strike(m, vel, t) {
      const i = m - FIRST;
      if (i < 0 || i >= COUNT) return;
      const v = clamp01(vel / 127);
      strikeT[i] = t;
      glow[i] = Math.max(glow[i], 1.0);
      hT0[i] = t;
      hRise[i] = 0;
      plumeX[i] = 0;
      plumeA[i] = 0.5 + 0.6 * v;
      strikeA[i] = clamp(v * v * 1.5, 0, 1);
      bandVel[i] = v;
      noteColor(m, vel, tmpColor);
      hammers.setColorAt(i, tmpColor);
    }

    function update(dt, t, state) {
      if (!active || disposed) return;
      dt = Math.max(0, Math.min(dt || 0, 0.1));
      state = state || {};

      const notes = state.notes;
      if (notes) for (let k = 0; k < notes.length; k++) {
        const n = notes[k], i = n.midi - FIRST;
        if (i >= 0 && i < COUNT && n.t > strikeT[i] + 1e-6 && n.t <= t + 1e-3) strike(n.midi, n.vel, n.t);
      }

      const snd = state.sounding;
      heldNow.fill(0);
      let bassM = -1, topM = -1, nv = 0;
      if (snd) {
        // state.sounding is a Map keyed by midi; the entry may or may not carry .midi, so take the key.
        snd.forEach((rec, key) => {
          const m = (rec && rec.midi !== undefined) ? rec.midi : key;
          const i = (m - FIRST) | 0;
          if (i < 0 || i >= COUNT) return;
          heldNow[i] = 1;
          // sustain answers velocity: damp glow toward a velocity-scaled target rather than
          // Math.max-ing to the strike, so a soft note holds a soft floor and a hard one a bright one.
          const lev = (rec && rec.held) ? 1.0 : 0.85;
          const vel = (rec && typeof rec.vel === "number") ? rec.vel : 100;
          const target = lev * (0.45 + 0.55 * vel / 127);
          glow[i] = damp(glow[i], target, 0.25, dt);
          if (bassM < 0 || m < bassM) bassM = m;
          if (topM < 0 || m > topM) topM = m;
          nv++;
        });
      } else {
        const pressed = state.pressed;
        if (pressed) pressed.forEach((ent, m) => {
          const i = m - FIRST;
          if (i < 0 || i >= COUNT) return;
          heldNow[i] = 1;
          const v = (ent && typeof ent === "object" && ent.vel !== undefined) ? ent.vel / 127 : 0.7;
          glow[i] = Math.max(glow[i], 0.4 + 0.6 * v);
          bandVel[i] = Math.max(bandVel[i], v);
          if (bassM < 0 || m < bassM) bassM = m;
          if (topM < 0 || m > topM) topM = m;
          nv++;
        });
      }
      const pedal = !!state.pedal;

      const spread = nv >= 2 ? topM - bassM : 0;
      const cluster = nv >= 3 && spread <= 4;
      feelLush = damp(feelLush, clamp01(nv / 6) * clamp01(spread / 24) * (cluster ? 0.4 : 1), 0.15, dt);
      feelTense = damp(feelTense, cluster ? 0.7 : 0, 0.1, dt);

      for (let i = 0; i < COUNT; i++) {
        strikeA[i] *= Math.exp(-dt / 0.09);
        plumeX[i] += dt * (0.5 + 2.5 * bandVel[i]);
        plumeA[i] *= Math.exp(-dt / 0.5);
        if (plumeX[i] > 1.0) plumeA[i] = 0;
        iPhase[i] = (iPhase[i] + dt * (3.5 + 3.0 * (1.0 - iBlur[i]))) % TAU;
        if (!heldNow[i]) {
          glow[i] *= Math.exp(-dt / ((pedal || !snd) ? 1.3 : 0.3));
          if (glow[i] < 0.004) {
            glow[i] = 0;
            if (hammers.instanceColor) hammers.setColorAt(i, tmpColor.setHex(0x808080));
          }
        }
        iGlow[i] = glow[i];
        iStrike[i] = strikeA[i];
        iPlumeX[i] = plumeX[i];
        iPlume[i] = plumeA[i] * glow[i];
        iWind[i] = feelLush * (0.3 + 0.7 * Math.sin(t * 2.2 + (FIRST + i) * 0.11));
      }
      bandGeo.attributes.aGlow.needsUpdate = true;
      bandGeo.attributes.aStrike.needsUpdate = true;
      bandGeo.attributes.aPlumeX.needsUpdate = true;
      bandGeo.attributes.aPlume.needsUpdate = true;
      bandGeo.attributes.aWind.needsUpdate = true;
      bandGeo.attributes.aPhase.needsUpdate = true;

      for (let i = 0; i < COUNT; i++) {
        const dh = t - hT0[i];
        hRise[i] = dh < 0.12 ? Math.sin(Math.min(1, dh / 0.05) * Math.PI) * 1.6 : (dh < 0.3 ? hRise[i] * Math.exp(-dt / 8) : 0);
        hd.position.set(bandX[i], HAMMY + hRise[i], bandZ[i]);
        hd.updateMatrix();
        hammers.setMatrixAt(i, hd.matrix);
      }
      hammers.instanceMatrix.needsUpdate = true;
      if (hammers.instanceColor) hammers.instanceColor.needsUpdate = true;

      if (nv >= 2 && bassM >= 0 && topM >= 0) {
        filament.visible = true;
        const bx = keyX(bassM), tx = keyX(topM);
        const bi = bassM - FIRST, ti = topM - FIRST;
        const by = LY0 + 0.5 + clamp01(bi / (COUNT - 1)) * 2.0;
        const ty = LY0 + 0.5 + clamp01(ti / (COUNT - 1)) * 2.0;
        const bz = bandZ[bi], tz = bandZ[ti];
        const db = by - filPrevBassY, ds = ty - filPrevSoloY;
        filPrevBassY = by; filPrevSoloY = ty;
        filTwist = damp(filTwist, (db * ds < 0) ? clamp01(-db * ds * 40) : 0, 0.2, dt);
        const ivs = (topM - bassM) % 12;
        const dissonant = [1, 2, 6, 10, 11].indexOf(ivs) >= 0;
        noteColor(topM, 100, tmpColor);
        if (dissonant) tmpColor.setRGB(tmpColor.r * 0.6 + 0.5, tmpColor.g * 0.4, tmpColor.b * 0.6 + 0.5);
        const fg = 0.5 + 0.5 * clamp01(1 - ((topM - bassM) - 5) / 30);
        // perpendicular (screen-space width) direction: perpendicular to (bass->solo) in the X-Z plane
        const dx = tx - bx, dz = tz - bz;
        const dl = Math.hypot(dx, dz) || 1;
        const px = -dz / dl, pz = dx / dl;
        const halfW = 0.22;
        for (let s = 0; s <= FSEG; s++) {
          const u = s / FSEG;
          const mx = lerp(bx, tx, u), my = lerp(by, ty, u), mz = lerp(bz, tz, u);
          // two vertices flared by the perpendicular (taper: wider mid-filament, thinner at the ends)
          const taper = Math.sin(u * Math.PI) * 0.6 + 0.4;
          filVerts[(s * 2) * 3] = mx - px * halfW * taper; filVerts[(s * 2) * 3 + 1] = my; filVerts[(s * 2) * 3 + 2] = mz - pz * halfW * taper;
          filVerts[(s * 2 + 1) * 3] = mx + px * halfW * taper; filVerts[(s * 2 + 1) * 3 + 1] = my; filVerts[(s * 2 + 1) * 3 + 2] = mz + pz * halfW * taper;
          for (let j = 0; j < 2; j++) {
            const vi = s * 2 + j;
            filColors[vi * 3] = tmpColor.r; filColors[vi * 3 + 1] = tmpColor.g; filColors[vi * 3 + 2] = tmpColor.b;
            filGlowArr[vi] = fg; filTwistArr[vi] = filTwist; filPhaseArr[vi] = t * 3.0;
          }
        }
        filament.geometry.attributes.position.needsUpdate = true;
        filament.geometry.attributes.aColor.needsUpdate = true;
        filament.geometry.attributes.aGlow.needsUpdate = true;
        filament.geometry.attributes.aTwist.needsUpdate = true;
        filament.geometry.attributes.aPhase.needsUpdate = true;
      } else filament.visible = false;

      let accR = 0, accG = 0, accB = 0, accN = 0;
      for (let i = 0; i < COUNT; i++) if (heldNow[i] && glow[i] > 0.05) { accR += iColor[i * 3]; accG += iColor[i * 3 + 1]; accB += iColor[i * 3 + 2]; accN++; }
      for (let i = 0; i < FOG_COUNT; i++) {
        const ph = fogPh[i], s = fogSeed[i];
        fog.geometry.attributes.position.array[i * 3] = Math.sin(t * 0.7 + ph) * 26.0;
        fog.geometry.attributes.position.array[i * 3 + 1] = ((t * 2.0 + s * 40.0) % 40.0) + 1.0;
        fog.geometry.attributes.position.array[i * 3 + 2] = lerp(DEPTH0, DEPTH1, s);
        fog.geometry.attributes.aSize.array[i] = 0.4 + s * 2.0;
        fog.geometry.attributes.aAlpha.array[i] = feelLush * (0.25 + 0.75 * clamp01(Math.sin(t * 1.3 + ph) * 0.5 + 0.5));
        fog.geometry.attributes.aGlow.array[i] = 0.8;
        if (accN > 0) { fog.geometry.attributes.aColor.array[i * 3] = accR / accN; fog.geometry.attributes.aColor.array[i * 3 + 1] = accG / accN; fog.geometry.attributes.aColor.array[i * 3 + 2] = accB / accN; }
      }
      fog.geometry.attributes.position.needsUpdate = true;
      fog.geometry.attributes.aColor.needsUpdate = true;
      fog.geometry.attributes.aSize.needsUpdate = true;
      fog.geometry.attributes.aAlpha.needsUpdate = true;
      fog.geometry.attributes.aGlow.needsUpdate = true;

      for (let i = 0; i < CRACKLE_COUNT; i++) {
        const ct = crackleT0[i];
        if (feelTense > 0.1 && (ct < 0 || t - ct > 0.4 + (i % 7) * 0.13)) {
          crackleT0[i] = t;
          crackle.geometry.attributes.position.array[i * 3] = lerp(span.left, span.right, rnd());
          crackle.geometry.attributes.position.array[i * 3 + 1] = lerp(LY0, LY1, rnd());
          crackle.geometry.attributes.position.array[i * 3 + 2] = lerp(DEPTH0, DEPTH1, rnd());
          crackle.geometry.attributes.aColor.array[i * 3] = iColor[(i % COUNT) * 3];
          crackle.geometry.attributes.aColor.array[i * 3 + 1] = iColor[(i % COUNT) * 3 + 1];
          crackle.geometry.attributes.aColor.array[i * 3 + 2] = iColor[(i % COUNT) * 3 + 2];
        }
        crackle.geometry.attributes.aAlpha.array[i] = ct < 0 ? 0 : feelTense * clamp01(1 - (t - ct) / 0.35);
        crackle.geometry.attributes.aSize.array[i] = 0.6 + (i % 5) * 0.3;
        crackle.geometry.attributes.aGlow.array[i] = 1.0;
      }
      crackle.geometry.attributes.position.needsUpdate = true;
      crackle.geometry.attributes.aColor.needsUpdate = true;
      crackle.geometry.attributes.aSize.needsUpdate = true;
      crackle.geometry.attributes.aAlpha.needsUpdate = true;
      crackle.geometry.attributes.aGlow.needsUpdate = true;
    }

    function resize(framing) {
      const portrait = !!framing && (framing.id === "9:16" || (framing.h > 0 && framing.h > framing.w));
      const dz = portrait ? 1.5 : 0;
      if (renderer) {
        const gl = renderer.getContext ? renderer.getContext() : null;
        uScale.value = (gl ? gl.drawingBufferHeight : renderer.domElement.height) * 0.5;
      }
      for (let i = 0; i < COUNT; i++) {
        dummy.position.set(bandX[i], LY0, bandZ[i] + dz);
        dummy.scale.set(bandW[i], 1, 1);
        dummy.updateMatrix();
        bands.setMatrixAt(i, dummy.matrix);
      }
      bands.instanceMatrix.needsUpdate = true;
    }

    function setActive(on) { active = on; group.visible = on; }

    function dispose() {
      if (disposed) return;
      disposed = true;
      active = false;
      for (let i = 0; i < disposables.length; i++) {
        const d = disposables[i];
        if (!d) continue;
        try { if (d.dispose) d.dispose(); } catch (e) {}
        try { if (d.geometry) d.geometry.dispose(); } catch (e) {}
        try { if (d.material) d.material.dispose(); } catch (e) {}
        try { if (d.texture) d.texture.dispose(); } catch (e) {}
      }
      disposables.length = 0;
      group.removeFromParent();
    }

    return { group, update, resize, setActive, dispose };
  },
};
