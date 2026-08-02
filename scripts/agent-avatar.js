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
'uniform vec3  u_id0;      // agent identity gradient, start (the BODY -- who this is)',
'uniform vec3  u_id1;      // agent identity gradient, end',
'uniform float u_round;    // tile shape: 0 = hexagon, 1 = disc',
'uniform float u_star;     // tile shape: >0 scallops the border, <0 pulls it into points',
'uniform float u_see;      // see-through: how strongly the FAR side shows through the near',
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
// TILE SHAPE. rCor is the corner-blend radius: at 0 the tile keeps the sharp hexagon the
// geodesic triangle gives it, and as it grows the corners round off until the tile is a disc.
// That single number is a real shape axis and costs nothing -- it was already in the smax.
'  float rTop=.05/sub, rCor=(.10+.62*u_round)/sub;',
'  // BREATHING: the shell height oscillates with u_pulse. At pulse 0 it is a still solid.',
'  float phase=dot(hc,pca)*22.+u_time*2.5;',
'  float h=2.-u_pulse*.16*(cos(phase)*.5+.5);',
'  float th=h;',
'  float eAd=dot(p,eA)+u_gap, eBd=dot(p,eB)-u_gap;',
'  float ed=smax(eAd,-eBd,rCor);',
// STAR / FLOWER. The two edge planes already form a 2D frame around the tile, so the atan of
// their signed distances is an angle -- no tangent basis to build, no extra normalisation. A
// six-fold modulation of the border pulls it into points (negative) or scallops it (positive),
// which is a genuinely different SHAPE rather than the same hexagon at another size.
'  float ang=atan(dot(p,eB),dot(p,eA));',
'  ed+=u_star*(.040/sub)*cos(6.*ang);',
'  float d=smax(ed,length(p)-h,rTop);',
'  d=smax(d,-(length(p)-h+th),rTop);',
'  float fb=clamp((h-length(p))/th,0.,1.);',
// WIREFRAME IS A REASSIGNMENT OF WHERE THE LIGHT LIVES, not a new geometry. The face and the
// edge band already exist; solid mode puts the brightness on the face, wireframe drains the face
// to near-void and lets the edge carry everything. Keeping both under one uniform means the
// state codebook (sub/gap/spin/pulse) is untouched -- an agent looks like itself in either mode.
'  vec3 solidFace=mix(vec3(.9,.9,1.),vec3(.10,.10,.15),step(.5,fb));',
// IDENTITY LIVES IN THE BODY, STATE LIVES IN THE LINES. Wireframe drained the faces to near-void
// and left them doing nothing, which is exactly the surface an agent's identity can occupy
// without fighting the state codebook for the same channel. The edges keep carrying the state
// hue, so the two never collide: you read WHO from the body and WHAT from the lines, and either
// can change without disturbing the other.
//
// The ramp runs diagonally across the shell to echo the 135deg the CSS identity gradients use --
// same colours, same direction, so the hero avatar and the little .av chips are recognisably the
// same object at two sizes rather than two different visual systems.
'  float gt=clamp(.5+.62*dot(normalize(hc),normalize(vec3(.7,.7,0.))),0.,1.);',
'  vec3 ident=mix(u_id0,u_id1,gt);',
'  ident=mix(vec3(dot(ident,vec3(.33))),ident,u_sat);   // a dead seat shows no vivid identity',
'  vec3 wireFace=ident*.062;                      // dim: a body to be read, not a lamp',
'  vec3 col=mix(solidFace,wireFace,u_wire);       // shell readable as a body, not a hole',
'  vec3 ec=spectrum(dot(hc,pca)*5.+length(p)+.8);',
'  ec=mix(vec3(dot(ec,vec3(.33))),ec,u_sat);      // desaturate for dead / unsensed',
'  ec=mix(ec,u_tint,mix(.45,.88,u_wire));         // wireframe leans hard on the state hue: with',
'                                                 // the faces dark, the lines ARE the signal',
// Narrow the band in wireframe so it reads as a drawn LINE rather than a lit bevel. .04 is a
// soft shoulder appropriate to a shaded solid; at two inches it would look like a fat border.
'  float ew=mix(.040,.016,u_wire);',
'  float eb=smoothstep(-ew,-.004,ed);',
// THE SWEEP, and this is the part meant to reward a long look rather than a glance. A band of
// brightness travels across the shell; its DIRECTION drifts on three incommensurate rates, so
// the sweep never repeats on any cycle an eye can latch onto. A loop that repeats teaches you
// its period in about thirty seconds and then there is nothing left to see -- that is the
// difference between a decoration and something you keep watching. Cost: one normalize, one
// dot, one cos, and it rides the tile centre so it moves ACROSS the tiling rather than with it.
'  vec3 wd=normalize(vec3(sin(u_time*.083),cos(u_time*.061),sin(u_time*.047+1.7)));',
'  float wv=smoothstep(.72,1.,cos(dot(hc,wd)*3.4-u_time*.85));',
'  ec*=1.+1.5*wv;',
'  eb=min(1.,eb*(1.+.55*wv));',
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
// SEE-THROUGH BACK LAYER -- this is what makes it a WIREFRAME rather than a dark solid with
// bright seams. You see the far side of the shell through the near one, and the moire between
// two tilings sliding across each other is the thing worth staring at: it is generated, not
// looped, so it never shows you the same interference twice.
//
// Marching the shell a second time would double the most expensive part of the shader. The shell
// is a sphere, so instead SOLVE the ray-sphere crossing in closed form and evaluate the tile
// pattern exactly once at the far point. Two map() calls against a 48-step march is noise, and
// it is exact rather than approximate.
'  if(u_see>.001){',
'    float bb=dot(ro,rd), cc=dot(ro,ro)-4.0;',      // shell radius ~2
'    float dd=bb*bb-cc;',
'    if(dd>0.){',
'      Model mb=map(ro+rd*(-bb+sqrt(dd)));',
// Only the EDGES come through. Letting the far FACES through would just flood the silhouette
// with a flat wash and destroy the very depth the second layer exists to create.
'      col+=mb.col*mb.glow*u_see*.55*u_dim;',
'      alpha=max(alpha,mb.glow*u_see*.9);',
'    }',
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
    ambient:   { sub: 3.0, gap: 0.014, spin: 0.09, pulse: 0.55, sat: 1.0, dim: 0.95, round: 0.35, star: 0.00, tint: [0.29, 0.44, 0.95] },
    // THINKING vs TOOL is the distinction Daniil asked for, and the two must not merely differ in
    // hue -- they differ in KIND of motion, because they are different kinds of work. Thinking is
    // INTERNAL: the shell barely turns and breathes hard, tight and dense, like something holding
    // still to concentrate. Tool use is EXTERNAL: it spins fast and breathes little, because the
    // work is happening out in the world rather than inside. Read across a room you can tell them
    // apart by movement alone, before the colour resolves -- which is the point of a codebook.
    thinking:  { sub: 3.1, gap: 0.009, spin: 0.06, pulse: 1.0,  sat: 1.0, dim: 1.0, round: 0.85, star: 0.30,  tint: [0.56, 0.42, 1.0] },
    composing: { sub: 2.7, gap: 0.012, spin: 0.22, pulse: 1.0, sat: 1.0, dim: 1.0, round: 0.55, star: 0.10,  tint: [0.02, 0.51, 1.0] },
    tool:      { sub: 3.4, gap: 0.006, spin: 0.55, pulse: 0.45, sat: 1.0, dim: 1.0, round: 0.00, star: -0.35,  tint: [0.24, 0.86, 0.60] },
    idle:      { sub: 1.8, gap: 0.010, spin: 0.05, pulse: 0.15, sat: 0.55, dim: 0.62, round: 0.60, star: 0.00, tint: [0.30, 0.64, 1.0] },
    wedged:    { sub: 2.2, gap: 0.075, spin: 0.0,  pulse: 0.0,  sat: 0.85, dim: 0.85, round: 0.00, star: -0.85, tint: [1.0, 0.70, 0.16] },
    throttled: { sub: 2.2, gap: 0.030, spin: 0.10, pulse: 0.7,  sat: 0.9,  dim: 0.8, round: 0.20, star: 0.55,  tint: [0.96, 0.35, 0.55] },
    dead:      { sub: 1.2, gap: 0.004, spin: 0.0,  pulse: 0.0,  sat: 0.0,  dim: 0.30, round: 0.90, star: 0.00, tint: [0.45, 0.48, 0.52] },
    unsensed:  { sub: 1.6, gap: 0.055, spin: 0.02, pulse: 0.0,  sat: 0.0,  dim: 0.45, round: 0.50, star: 0.00, tint: [0.55, 0.50, 0.62] }
  };

  // IDENTITY PRESETS. These are NOT new colours -- claude, deepseek and user are lifted verbatim
  // from the .av chip gradients already in bifrost_ui.py (linear-gradient(135deg, ...)), so the
  // hero avatar and the little roster chips are the same visual object at two sizes. Inventing a
  // second scheme here would have been the easy path and would have quietly split the design
  // system in two, which is exactly the sort of drift nobody notices until it is everywhere.
  //
  // The additions (kimi, sol, gemini) are new only because no chip existed for them; they are
  // picked in the same saturation and luminance register so no one agent reads as louder than
  // another purely by accident of palette.
  var IDENT = {
    claude:   [[0.878, 0.569, 0.361], [0.851, 0.482, 0.353]],   // #e0915c -> #d97b5a  coral
    deepseek: [[0.478, 0.635, 0.969], [0.616, 0.486, 0.969]],   // #7aa2f7 -> #9d7cf7  peri->violet
    user:     [[0.373, 0.827, 0.608], [0.247, 0.749, 0.525]],   // #5fd39b -> #3fbf86  green
    kimi:     [[0.941, 0.698, 0.275], [0.878, 0.541, 0.235]],   // amber
    sol:      [[0.373, 0.816, 0.851], [0.247, 0.690, 0.788]],   // cyan
    gemini:   [[0.847, 0.478, 0.729], [0.706, 0.400, 0.784]],   // rose -> orchid
    system:   [[0.478, 0.522, 0.612], [0.376, 0.412, 0.502]]    // neutral slate: the unnamed
  };

  function identFor(agent) {
    if (IDENT[agent]) return IDENT[agent];
    // Prefix match so incarnations and variants inherit their parent's identity rather than
    // falling to slate -- deepseek-ui and deepseek-plumbing ARE deepseek to the eye.
    for (var k in IDENT) { if (k !== 'system' && agent && agent.indexOf(k) === 0) return IDENT[k]; }
    return IDENT.system;
  }

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
    // Identity eases too, so a broadcast avatar handing over from one agent to another MORPHS
    // between their gradients instead of snapping -- the same courtesy the state gets.
    // See-through amount. Dial it live with _heroAv.shader.see = 0..1, or pin it before the
    // avatar mounts with window.AKASHIC_AVATAR_SEE -- the comment used to claim that global was
    // read and it was not, which is the kind of small lie that costs somebody an afternoon.
    var sv = parseFloat(global.AKASHIC_AVATAR_SEE);
    this.see = (sv >= 0 && sv <= 1) ? sv : 0.85;
    this.id0 = IDENT.system[0].slice(); this.id1 = IDENT.system[1].slice();
    this.idT0 = this.id0.slice();       this.idT1 = this.id1.slice();
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

  // WHO this avatar is currently speaking for. Separate call from setState on purpose: identity
  // and state change for different reasons and at different rates, and folding them into one
  // setter would force every caller that knows one to also assert the other.
  AgentAvatar.prototype.setIdentity = function (agent) {
    var p = identFor(agent);
    this.idT0 = p[0].slice(); this.idT1 = p[1].slice();
    if (!this.animating) {                    // static avatar: snap, same rule as setState
      this.id0 = this.idT0.slice(); this.id1 = this.idT1.slice();
    }
  };

  // --- colour easing helpers ---------------------------------------------------------------
  // A straight RGB lerp between two distant hues passes through their average, and the average of
  // violet and green is mud. Easing in HSV keeps every intermediate frame a real colour.
  function rgb2hsv(c) {
    var r = c[0], g = c[1], b = c[2];
    var mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn, h = 0;
    if (d > 1e-6) {
      if (mx === r)      h = ((g - b) / d) % 6;
      else if (mx === g) h = (b - r) / d + 2;
      else               h = (r - g) / d + 4;
      h /= 6; if (h < 0) h += 1;
    }
    return [h, mx > 1e-6 ? d / mx : 0, mx];
  }
  function hsv2rgb(h, s, v) {
    var i = Math.floor(h * 6), f = h * 6 - i;
    var p = v * (1 - s), q = v * (1 - f * s), t = v * (1 - (1 - f) * s);
    switch (i % 6) {
      case 0: return [v, t, p];
      case 1: return [q, v, p];
      case 2: return [p, v, t];
      case 3: return [p, q, v];
      case 4: return [t, p, v];
      default: return [v, p, q];
    }
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
    ['u_res','u_time','u_sub','u_gap','u_spin','u_pulse','u_sat','u_tint','u_dim','u_wire',
     'u_id0','u_id1','u_round','u_star','u_see']
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
    gl.uniform3f(u.u_id0, this.id0[0], this.id0[1], this.id0[2]);
    gl.uniform3f(u.u_id1, this.id1[0], this.id1[1], this.id1[2]);
    gl.uniform1f(u.u_round, c.round);
    gl.uniform1f(u.u_star, c.star);
    // see-through rides the wireframe amount: a LIT SOLID shell must not show its own back face
    // (that reads as a rendering fault, not as depth), while a wireframe is defined by doing so.
    gl.uniform1f(u.u_see, this.wire * this.see);
    gl.uniform3f(u.u_tint, c.tint[0], c.tint[1], c.tint[2]);
    gl.clearColor(0, 0, 0, 0);
    gl.clear(gl.COLOR_BUFFER_BIT);
    gl.drawArrays(gl.TRIANGLES, 0, 3);
  };

  AgentAvatar.prototype._tick = function () {
    if (!this.animating) return;
    var self = this;
    global.requestAnimationFrame(function () { self._tick(); });

    // FRAME-RATE INDEPENDENT, and this is a correctness fix rather than a matter of taste. k was a
    // fixed 0.08 PER FRAME, so the identical transition settled in ~0.47s at 60Hz and in half that
    // on a 144Hz panel: the animation ran at whatever speed the monitor happened to be. An
    // exponential on ELAPSED TIME settles in the same wall-clock everywhere, and TAU can then be
    // stated as something meaningful -- 0.45s here, so a change reads as a deliberate morph over
    // roughly a second and a third rather than as a cut.
    var TAU = 0.45;
    var nowS = (global.performance ? performance.now() : Date.now()) / 1000;
    var dt = this._lastT ? Math.min(0.1, nowS - this._lastT) : 0.016;
    this._lastT = nowS;
    var k = 1 - Math.exp(-dt / TAU);

    var c = this.cur, t = this.target, i;
    ['sub','gap','spin','pulse','sat','dim','round','star'].forEach(function (key) { c[key] += (t[key] - c[key]) * k; });

    // TINT EASES THROUGH HSV, NOT RGB. thinking is violet and tool is green -- close to opposite
    // on the wheel -- so a straight RGB lerp between them passes through their average, which is
    // a desaturated grey-brown. Every intermediate frame looked like a fault. Interpolating hue
    // the SHORT way round sweeps violet -> blue -> teal -> green instead: each frame is a real
    // colour, and the transition reads as one light changing rather than two fighting.
    var ch = rgb2hsv(c.tint), th = rgb2hsv(t.tint);
    var dh = th[0] - ch[0];
    if (dh > 0.5) dh -= 1; else if (dh < -0.5) dh += 1;      // shortest path around the wheel
    var h = ch[0] + dh * k; if (h < 0) h += 1; else if (h > 1) h -= 1;
    // Saturation and value stay linear: only HUE is angular, and treating the other two as
    // angles too would make a fade to grey take the long way through white.
    c.tint = hsv2rgb(h, ch[1] + (th[1] - ch[1]) * k, ch[2] + (th[2] - ch[2]) * k);

    for (i = 0; i < 3; i++) {
      this.id0[i] += (this.idT0[i] - this.id0[i]) * k;
      this.id1[i] += (this.idT1[i] - this.id1[i]) * k;
    }

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
