// agent-avatar.js — the geodesic agent avatar (claude's lane)
//
// A small WebGL2 canvas rendering a subdivided icosahedron of hexagonal tiles, whose MOTION,
// DENSITY and COLOUR are driven by the agent's diagnosed state. The avatar is not decoration:
// it is the signature codebook rendered as an object. What the sensors observe, the codebook
// diagnoses, and this shows.
//
// Model adapted from Matt Zucker's triangle tiling + knighty's icosahedral domain mirroring,
// via "Geodesic tiling" (shadertoy llVXRd, CC-BY-NC-SA). The original cycles three canned
// animations on a timer; that timer is REMOVED here and its parameters are exposed as state
// uniforms instead, which is the whole point — the object animates because the agent is doing
// something, never because six seconds elapsed.
//
// INTERFACE CONTRACT (mirrors AuroraShader deliberately — one house pattern, one seam):
//   if (AgentAvatar.isSupported()) { const a = new AgentAvatar(canvasEl); a.start(); }
//   a.setState('composing'|'tool'|'idle'|'wedged'|'throttled'|'dead'|'unsensed')
//   a.setRate(0..1)     // activity: tokens/sec or tool cadence, normalised
// The status layer owns WHEN to switch; the shader owns the visual. Neither reaches across.
//
// WHY THIS IS SAFE ON THIS MACHINE, and it is not a general truth:
// this host has a documented AMD display-driver TDR history (kernel WATCHDOG dumps correlated
// to the minute with Electron "GPU process gone" crashes, diagnosed 2026-08-02). A 100-step
// full-screen raymarcher is exactly the workload that trips it. So:
//   * AVATARS ARE SMALL. Cost scales with pixel COUNT: ~64px at half-res is ~1k fragments
//     against a full-screen ~700k — roughly 0.15% of the work per frame.
//   * TRACE STEPS ARE CAPPED at 48 (the original used 100) — at this size and distance the
//     surface converges well before that.
//   * powerPreference:'low-power' so we never wake the discrete GPU for a 64px canvas.
//   * A LIVE INSTANCE CAP: past MAX_LIVE avatars, later ones render a static fallback frame
//     instead of animating. Eleven simultaneous raymarchers is not a thing we do.
//   * AN FPS WATCHDOG that permanently disables animation and paints one last frame if the
//     budget is missed — degrade to a still image, never take the console down with us.
//   * visibilitychange stops all GPU work when the tab is hidden.
(function (global) {
  'use strict';

  var MAX_LIVE = 6;            // simultaneously ANIMATING avatars; the rest go static
  var live = 0;

  var VERT = '#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0.0,1.0);}';

  var FRAG = [
'#version 300 es',
'precision highp float;',
'out vec4 outColor;',
'uniform vec2  u_res;',
'uniform float u_time;',
'uniform float u_sub;      // subdivision density: how finely the shell is tiled',
'uniform float u_gap;      // tile separation: openness',
'uniform float u_spin;     // rotation rate',
'uniform float u_pulse;    // breathing amplitude',
'uniform float u_sat;      // colour saturation (0 = greyscale, for dead/unsensed)',
'uniform vec3  u_tint;     // state hue',
'uniform float u_dim;      // overall brightness',
'uniform float u_wire;     // 0 = lit solid shell, 1 = dark wireframe (edges carry the light)',
'',
'#define PI 3.14159265359',
'',
'void pR(inout vec2 p,float a){p=cos(a)*p+sin(a)*vec2(p.y,-p.x);}',
'float pReflect(inout vec3 p,vec3 n,float o){float t=dot(p,n)+o;if(t<0.){p=p-(2.*t)*n;}return sign(t);}',
'float smax(float a,float b,float r){float m=max(a,b);if((-a<r)&&(-b<r)){return max(m,-(r-sqrt((r+a)*(r+a)+(r+b)*(r+b))));}return m;}',
'',
'vec3 facePlane,uPlane,vPlane,nc,pab,pbc,pca;',
'void initIco(){',
'  float cospin=cos(PI/5.),scospin=sqrt(0.75-cospin*cospin);',
'  nc=vec3(-0.5,-cospin,scospin);',
'  pbc=normalize(vec3(scospin,0.,0.5)); pca=normalize(vec3(0.,scospin,cospin)); pab=vec3(0,0,1);',
'  facePlane=pca; uPlane=cross(vec3(1,0,0),facePlane); vPlane=vec3(1,0,0);',
'}',
'void pModIco(inout vec3 p){',
'  p=abs(p); pReflect(p,nc,0.); p.xy=abs(p.xy); pReflect(p,nc,0.); p.xy=abs(p.xy); pReflect(p,nc,0.);',
'}',
'',
'const float sqrt3=1.7320508075688772; const float i3=0.5773502691896258;',
'const mat2 cart2hex=mat2(1,0,i3,2.*i3); const mat2 hex2cart=mat2(1,0,-.5,.5*sqrt3);',
'const float faceRadius=0.3819660112501051;',
'',
'vec3 isect(vec3 n,vec3 pn,float po){return n*((dot(vec3(0),pn)+po)/-dot(pn,n));}',
'vec2 icoFaceCoord(vec3 p){vec3 i=isect(normalize(p),facePlane,-1.);return vec2(dot(i,uPlane),dot(i,vPlane));}',
'vec3 faceToSphere(vec2 f){return normalize(facePlane+(uPlane*f.x)+(vPlane*f.y));}',
'',
'struct TP{vec2 a;vec2 b;vec2 c;vec2 ctr;vec2 ab;vec2 bc;vec2 ca;};',
'TP closestTri(vec2 p){',
'  vec2 pt=cart2hex*p, pi=floor(pt), pf=fract(pt);',
'  float s1=step(pf.y,pf.x), s2=step(pf.x,pf.y);',
'  vec2 a=vec2(s1,1)+pi,b=vec2(1,s2)+pi,c=pi;',
'  a=hex2cart*a; b=hex2cart*b; c=hex2cart*c;',
'  return TP(a,b,c,(a+b+c)/3.,(a+b)/2.,(b+c)/2.,(c+a)/2.);',
'}',
'struct TP3{vec3 a;vec3 b;vec3 c;vec3 ctr;vec3 ab;vec3 bc;vec3 ca;};',
'TP3 geoTri(vec3 p,float sub){',
'  vec2 uv=icoFaceCoord(p); float s=sub/faceRadius/2.; TP t=closestTri(uv*s);',
'  return TP3(faceToSphere(t.a/s),faceToSphere(t.b/s),faceToSphere(t.c/s),faceToSphere(t.ctr/s),',
'             faceToSphere(t.ab/s),faceToSphere(t.bc/s),faceToSphere(t.ca/s));',
'}',
'',
'vec3 pal(float t,vec3 a,vec3 b,vec3 c,vec3 d){return a+b*cos(6.28318*(c*t+d));}',
'vec3 spectrum(float n){return pal(n,vec3(.5),vec3(.5),vec3(1.),vec3(0.,.33,.67));}',
'',
'struct Model{float d;vec3 col;float glow;};',
'Model hexModel(vec3 p,vec3 hc,vec3 eA,vec3 eB,float sub){',
'  float rTop=.05/sub, rCor=.1/sub;',
'  // BREATHING: the shell height oscillates with u_pulse. At pulse 0 it is a still solid.',
'  float phase=dot(hc,pca)*22.+u_time*2.5;',
'  float h=2.-u_pulse*.16*(cos(phase)*.5+.5);',
'  float th=h;',
'  float eAd=dot(p,eA)+u_gap, eBd=dot(p,eB)-u_gap;',
'  float ed=smax(eAd,-eBd,rCor);',
'  float d=smax(ed,length(p)-h,rTop);',
'  d=smax(d,-(length(p)-h+th),rTop);',
'  float fb=clamp((h-length(p))/th,0.,1.);',
// WIREFRAME IS A REASSIGNMENT OF WHERE THE LIGHT LIVES, not a new geometry. The face and the
// edge band already exist; solid mode puts the brightness on the face, wireframe drains the face
// to near-void and lets the edge carry everything. Keeping both under one uniform means the
// state codebook (sub/gap/spin/pulse) is untouched -- an agent looks like itself in either mode.
'  vec3 solidFace=mix(vec3(.9,.9,1.),vec3(.10,.10,.15),step(.5,fb));',
'  vec3 wireFace=vec3(.010,.014,.024);            // not pure black: a faint blue cast keeps the',
'  vec3 col=mix(solidFace,wireFace,u_wire);       // shell readable as a body, not a hole',
'  vec3 ec=spectrum(dot(hc,pca)*5.+length(p)+.8);',
'  ec=mix(vec3(dot(ec,vec3(.33))),ec,u_sat);      // desaturate for dead / unsensed',
'  ec=mix(ec,u_tint,mix(.45,.88,u_wire));         // wireframe leans hard on the state hue: with',
'                                                 // the faces dark, the lines ARE the signal',
// Narrow the band in wireframe so it reads as a drawn LINE rather than a lit bevel. .04 is a
// soft shoulder appropriate to a shaded solid; at two inches it would look like a fat border.
'  float ew=mix(.040,.016,u_wire);',
'  float eb=smoothstep(-ew,-.004,ed);',
'  return Model(d,mix(col,ec,eb),eb);',
'}',
// if/else and NOT a ternary. ESSL refuses `?:` on struct types -- the compiler says
// "ternary operator is not allowed for structures in ESSL 1.0 and webgl". The original
// shadertoy used if/else here; compacting it to a ternary cost a compile error, caught
// only because the shader was compiled before shipping rather than eyeballed.
'Model opU(Model a,Model b){if(a.d<b.d){return a;}return b;}',
'',
'Model map(vec3 p){',
'  pR(p.xz,u_time*u_spin);',
'  pR(p.xy,.35);',
'  pModIco(p);',
'  float sub=u_sub;',
'  TP3 t=geoTri(p,sub);',
'  vec3 eAB=normalize(cross(t.ctr,t.ab)),eBC=normalize(cross(t.ctr,t.bc)),eCA=normalize(cross(t.ctr,t.ca));',
'  Model m=hexModel(p,t.b,eAB,eBC,sub);',
'  m=opU(m,hexModel(p,t.c,eBC,eCA,sub));',
'  m=opU(m,hexModel(p,t.a,eCA,eAB,sub));',
'  return m;',
'}',
'',
// TETRAHEDRAL, not central differences: four map() evaluations for a normal of equivalent
// quality instead of six. map() is by far the expensive call -- it evaluates three hex SDFs --
// so this is a third off the per-pixel normal cost, and it is most of what pays for rendering at
// native resolution rather than half.
'vec3 calcNormal(vec3 p){',
'  const vec2 k=vec2(1,-1); const float e=.0015;',
'  return normalize(k.xyy*map(p+k.xyy*e).d + k.yyx*map(p+k.yyx*e).d +',
'                   k.yxy*map(p+k.yxy*e).d + k.xxx*map(p+k.xxx*e).d);',
'}',
'',
'void main(){',
'  initIco();',
'  vec2 uv=(-u_res.xy+2.*gl_FragCoord.xy)/u_res.y;',
'  vec3 ro=vec3(0,0,-5.5), rd=normalize(vec3(uv,2.));',
'  float t=0.; Model m; bool hit=false;',
'  // 48 steps, not the original 100: at avatar size the surface converges long before that,',
'  // and the step count is the single biggest lever on GPU cost.',
// CONE TRACKING FOR ANALYTIC SILHOUETTE AA, and this is the half of "pixel perfect" that
// resolution alone cannot buy. A raymarch answers hit/miss as a BOOLEAN, so every silhouette
// pixel is fully on or fully off -- that binary IS the staircase, and rendering at native
// resolution only renders it more crisply. Recording the closest ANGULAR approach (d/t) costs
// one min() per step and converts the outer edge into genuine coverage.
'  float cone=1e9;',
'  for(int i=0;i<48;i++){',
'    m=map(ro+rd*t);',
'    if(t>.001) cone=min(cone,m.d/t);',
'    if(m.d<.0015){hit=true;break;}',
'    t+=m.d*.9;',
'    if(t>9.)break;',
'  }',
'  vec3 col=vec3(0.);',
'  float alpha=0.;',
'  if(hit){',
'    vec3 pos=ro+rd*t, n=calcNormal(pos);',
'    vec3 lig=normalize(vec3(.5,.5,-1.)), bl=normalize(vec3(-.5,-.3,1.));',
'    float amb=clamp((dot(n,vec3(0,1,0))+1.)/2.,0.,1.);',
'    float dif=clamp(dot(n,lig),0.,1.);',
'    float bac=pow(clamp(dot(n,bl),0.,1.),1.5);',
'    float fre=pow(clamp(1.+dot(n,rd),0.,1.),2.);',
'    vec3 lin=1.20*dif*vec3(.9)+0.80*amb*vec3(.5,.7,.8)+0.30*bac*vec3(.25)+0.25*fre*u_tint;',
// In wireframe the SURFACE has to stop competing with the lines. Diffuse and ambient drop to a
// fifth and the fresnel rim comes up, so what the eye reads is a silhouette and its edges rather
// than a lit ball with seams drawn on it.
'    vec3 wlin=0.22*lin+1.05*fre*u_tint;',
'    lin=mix(lin,wlin,u_wire);',
'    col=mix(m.col*lin,m.col,m.glow)*u_dim;',
'    alpha=1.;',
'  }else{',
// THE NEAR-MISS BAND. One pixel subtends ~1/u_res.y radians here (rd is built from a uv scaled
// by 1/u_res.y against z=2), so coverage falls off over about a pixel and a half. Tinting it is
// not a fudge: a near-miss is by definition adjacent to the rim it is antialiasing, and the rim
// is exactly what fresnel makes tint-coloured.
'    float px=1./u_res.y;',
'    float cov=1.-smoothstep(0.,px*1.6,cone);',
'    col=u_tint*mix(.42,.75,u_wire)*cov;',
'    alpha=cov*mix(.80,.95,u_wire);',
'  }',
'  col=pow(max(col,0.),vec3(1./2.2));',
'  outColor=vec4(col,alpha);   // transparent background: the avatar sits on the console glass',
'}'
  ].join('\n');

  // STATE TABLE. This is the codebook made visible -- each row is how a diagnosed state LOOKS.
  // Motion means work; stillness means none; grey means we cannot see.
  var STATES = {
    // AMBIENT is the resting face of the fleet, shown when the composer is addressed to
    // everyone: nobody in particular is the subject, so it must look alive without looking
    // busy. Rich subdivision so it reads as an object rather than a blob, a slow turn, and a
    // gentle breath -- the difference between "idle" (one agent waiting) and "ambient"
    // (the system, at rest) is that ambient is not a diagnosis about anyone.
    ambient:   { sub: 3.0, gap: 0.014, spin: 0.09, pulse: 0.55, sat: 1.0, dim: 0.95, tint: [0.29, 0.44, 0.95] },
    // THINKING vs TOOL is the distinction Daniil asked for, and the two must not merely differ in
    // hue -- they differ in KIND of motion, because they are different kinds of work. Thinking is
    // INTERNAL: the shell barely turns and breathes hard, tight and dense, like something holding
    // still to concentrate. Tool use is EXTERNAL: it spins fast and breathes little, because the
    // work is happening out in the world rather than inside. Read across a room you can tell them
    // apart by movement alone, before the colour resolves -- which is the point of a codebook.
    thinking:  { sub: 3.1, gap: 0.009, spin: 0.06, pulse: 1.0,  sat: 1.0, dim: 1.0,  tint: [0.56, 0.42, 1.0] },
    composing: { sub: 2.7, gap: 0.012, spin: 0.22, pulse: 1.0, sat: 1.0, dim: 1.0,  tint: [0.02, 0.51, 1.0] },
    tool:      { sub: 3.4, gap: 0.006, spin: 0.55, pulse: 0.45, sat: 1.0, dim: 1.0,  tint: [0.24, 0.86, 0.60] },
    idle:      { sub: 1.8, gap: 0.010, spin: 0.05, pulse: 0.15, sat: 0.55, dim: 0.62, tint: [0.30, 0.64, 1.0] },
    wedged:    { sub: 2.2, gap: 0.075, spin: 0.0,  pulse: 0.0,  sat: 0.85, dim: 0.85, tint: [1.0, 0.70, 0.16] },
    throttled: { sub: 2.2, gap: 0.030, spin: 0.10, pulse: 0.7,  sat: 0.9,  dim: 0.8,  tint: [0.96, 0.35, 0.55] },
    dead:      { sub: 1.2, gap: 0.004, spin: 0.0,  pulse: 0.0,  sat: 0.0,  dim: 0.30, tint: [0.45, 0.48, 0.52] },
    unsensed:  { sub: 1.6, gap: 0.055, spin: 0.02, pulse: 0.0,  sat: 0.0,  dim: 0.45, tint: [0.55, 0.50, 0.62] }
  };

  function isSupported() {
    try {
      if (global.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches) return false;
      return !!document.createElement('canvas').getContext('webgl2');
    } catch (e) { return false; }
  }

  function AgentAvatar(canvas) {
    this.canvas = canvas;
    this.gl = canvas.getContext('webgl2', {
      alpha: true, antialias: false,
      powerPreference: 'low-power',      // never wake the discrete GPU for a 64px canvas
      preserveDrawingBuffer: false
    });
    if (!this.gl) throw new Error('webgl2 unavailable');
    // Wireframe is a LOOK, not a state, so it lives on the instance rather than in the codebook:
    // every state must survive both treatments unchanged. Exposed as a global so it can be dialled
    // live (window.AKASHIC_AVATAR_WIRE = 0.4) without an edit-restart-reload cycle -- 0 is the
    // original lit solid, 1 is full dark wireframe.
    var wv = parseFloat(global.AKASHIC_AVATAR_WIRE);
    this.wire = (wv >= 0 && wv <= 1) ? wv : 1.0;
    this.cur = Object.assign({}, STATES.idle);
    this.target = Object.assign({}, STATES.idle);
    this.rate = 0;
    this.animating = false;
    this.disabled = false;                // set by the watchdog; never re-enabled
    this._t0 = (global.performance ? performance.now() : Date.now()) / 1000;
    this._frames = 0; this._fpsAt = 0;
    this._compile();
    this._resize();
    this._bind();
  }

  AgentAvatar.prototype.setState = function (name) {
    var s = STATES[name] || STATES.unsensed;
    this.target = Object.assign({}, s);
    this.target.tint = s.tint.slice();
    if (!this.animating && !this.disabled) this.start();
    // A STATIC avatar must SNAP, not ease. `cur` is interpolated toward `target` only inside
    // the animation loop, so an avatar that is disabled (watchdog) or past the live cap has
    // no loop to move it -- it would render its initial state forever while believing it had
    // changed. Snapping is the whole reason a capped avatar is still honest.
    if (!this.animating) {
      this.cur = Object.assign({}, this.target);
      this.cur.tint = this.target.tint.slice();
      this._draw();
    }
  };
  AgentAvatar.prototype.setRate = function (v) {
    this.rate = Math.max(0, Math.min(1, +v || 0));
  };

  AgentAvatar.prototype._compile = function () {
    var gl = this.gl;
    function sh(type, src) {
      var s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
      if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error('avatar compile: ' + gl.getShaderInfoLog(s));
      return s;
    }
    var p = gl.createProgram();
    gl.attachShader(p, sh(gl.VERTEX_SHADER, VERT));
    gl.attachShader(p, sh(gl.FRAGMENT_SHADER, FRAG));
    gl.linkProgram(p);
    if (!gl.getProgramParameter(p, gl.LINK_STATUS)) throw new Error('avatar link: ' + gl.getProgramInfoLog(p));
    gl.useProgram(p);
    this.prog = p;
    var u = {};
    ['u_res','u_time','u_sub','u_gap','u_spin','u_pulse','u_sat','u_tint','u_dim','u_wire']
      .forEach(function (n) { u[n] = gl.getUniformLocation(p, n); });
    this.u = u;
    gl.enable(gl.BLEND);
    gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
  };

  AgentAvatar.prototype._resize = function (cssSize) {
    // ONE BACKING PIXEL PER DEVICE PIXEL, and this is the whole aliasing fix. The avatar used to
    // render at 0.5 and let the browser stretch it 2x, which was fine when it was a 38px chip and
    // is indefensible now that it is a two-inch object the eye is invited to study: no
    // post-process recovers detail a 2x upscale destroyed, and FXAA over a wireframe would only
    // soften the very lines it exists to sharpen. Undersampling is correct for a full-screen
    // ambient background. It was never correct for the subject.
    var dpr = Math.min(global.devicePixelRatio || 1, 2);
    var scale = parseFloat(global.AKASHIC_AVATAR_SCALE);
    if (!(scale > 0 && scale <= 2)) scale = 1.0;
    var eff = Math.max(0.35, dpr * scale);
    // A caller that ALREADY knows the box may hand over its CSS size, and the hero avatar does.
    // Measuring clientWidth is a bet that layout has settled since the box was set; lose that
    // bet and the OLD width is sampled, baking a thumbnail-sized render target into a much
    // larger square -- which is a blur no amount of later redrawing repairs, because the backing
    // store is only re-cut on resize. `cssSize` sticks, so the window-resize handler that calls
    // _resize() bare keeps the right target instead of falling back to a guess.
    if (cssSize > 0) this.cssSize = cssSize;
    var box = this.cssSize || this.canvas.clientWidth || 64;
    var boxH = this.cssSize || this.canvas.clientHeight || 64;
    var w = Math.max(1, Math.round(box * eff));
    var h = Math.max(1, Math.round(boxH * eff));
    // Bound the worst case rather than trusting dpr. Per-fragment cost here is high -- 48 march
    // steps, each evaluating three hex SDFs, plus normals -- so an unbounded 2x-dpr 192px box
    // would be a 384px target and four times the work of native. 320 keeps a hidpi display
    // genuinely sharp without letting the bill scale with someone's monitor.
    var MAX = 320;
    if (w > MAX || h > MAX) {
      var k = MAX / Math.max(w, h);
      w = Math.max(1, Math.round(w * k)); h = Math.max(1, Math.round(h * k));
    }
    this.canvas.width = w; this.canvas.height = h;
    this.gl.viewport(0, 0, w, h);
  };

  AgentAvatar.prototype._bind = function () {
    var self = this;
    this._onVis = function () { document.hidden ? self.stop() : self.start(); };
    document.addEventListener('visibilitychange', this._onVis);
  };

  AgentAvatar.prototype._draw = function () {
    var gl = this.gl, u = this.u, c = this.cur;
    var now = (global.performance ? performance.now() : Date.now()) / 1000;
    gl.useProgram(this.prog);
    gl.uniform2f(u.u_res, this.canvas.width, this.canvas.height);
    gl.uniform1f(u.u_time, now - this._t0);
    gl.uniform1f(u.u_sub, c.sub);
    gl.uniform1f(u.u_gap, c.gap);
    // rate rides ON TOP of the state's base spin: what state you are in sets the character,
    // how hard you are working sets the tempo.
    gl.uniform1f(u.u_spin, c.spin * (0.6 + this.rate * 1.6));
    gl.uniform1f(u.u_pulse, c.pulse);
    gl.uniform1f(u.u_sat, c.sat);
    gl.uniform1f(u.u_dim, c.dim);
    gl.uniform1f(u.u_wire, this.wire);
    gl.uniform3f(u.u_tint, c.tint[0], c.tint[1], c.tint[2]);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  };

  AgentAvatar.prototype._tick = function () {
    if (!this.animating) return;
    var self = this;
    global.requestAnimationFrame(function () { self._tick(); });

    // Ease every parameter toward its target so a state change MORPHS rather than cuts.
    var k = 0.08, c = this.cur, t = this.target;
    ['sub','gap','spin','pulse','sat','dim'].forEach(function (key) { c[key] += (t[key] - c[key]) * k; });
    for (var i = 0; i < 3; i++) c.tint[i] += (t.tint[i] - c.tint[i]) * k;

    this._draw();

    // FPS WATCHDOG. This machine has a display-driver TDR history; a struggling avatar is a
    // warning, not something to push through. Miss the budget and we stop FOREVER, leaving the
    // last frame painted -- a still geodesic is a perfectly good avatar.
    this._frames++;
    var now = (global.performance ? performance.now() : Date.now());
    if (!this._fpsAt) this._fpsAt = now;
    if (now - this._fpsAt > 3000) {
      var fps = this._frames * 1000 / (now - this._fpsAt);
      this._frames = 0; this._fpsAt = now;
      if (fps < 18) {
        this.disabled = true; this.animating = false; live = Math.max(0, live - 1);
        if (global.console) console.warn('[agent-avatar] ' + fps.toFixed(1) + 'fps — animation disabled, holding a static frame');
      }
    }
  };

  AgentAvatar.prototype.start = function () {
    if (this.animating || this.disabled) return;
    if (live >= MAX_LIVE) { this._draw(); return; }   // over the cap: one static frame, no loop
    live++; this.animating = true; this._fpsAt = 0; this._frames = 0;
    this._tick();
  };
  AgentAvatar.prototype.stop = function () {
    if (this.animating) { this.animating = false; live = Math.max(0, live - 1); }
  };
  AgentAvatar.prototype.destroy = function () {
    this.stop();
    document.removeEventListener('visibilitychange', this._onVis);
    var ext = this.gl && this.gl.getExtension('WEBGL_lose_context');
    if (ext) ext.loseContext();
  };

  AgentAvatar.isSupported = isSupported;
  AgentAvatar.STATES = STATES;
  global.AgentAvatar = AgentAvatar;
})(window);
