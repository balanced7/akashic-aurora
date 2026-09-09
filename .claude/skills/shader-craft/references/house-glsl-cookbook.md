# House GLSL cookbook

Part A is for the operator: what a shader costs here, how its colour is judged, how a change is
looked at, what a true still is, and what to do with an outside shader. Part B is for the author:
the patterns, quoted verbatim from files in this repo and named beside each quote, so
`tests/test_shader_craft_skill_cites_live_surfaces.py` can tell you the day the code moves on
and this page does not. Reimplement in the house idiom; never paste outside code.

---

# Part A — for the operator

## Cost, on this host
- The bed renders at half resolution (`AKASHIC_AURORA_SCALE`, 1 = native). Measured: sizing the
  canvas from its stuck 300x150 to a real 1440x900 took the console from 60fps to 44.6fps; half
  resolution restored the budget, and a soft low-frequency field has no edges to lose.
- Avatar: a ~64px canvas at native device pixels (`AKASHIC_AVATAR_SCALE`, dpr capped at 2; the
  old half-res path was "never correct for the subject"), 48 march steps,
  `powerPreference:'low-power'`, MAX_LIVE animating instances; the rest hold a still.
- Activity line: five sines and two smoothsteps per fragment at 320x28 half-scale, a
  two-hundredth of the aurora behind it.
- Hidden tab: no GPU work (`visibilitychange`).
- Never a second GPU context to look at your own work. The bench renders through the /vfx tab
  that is already open ("no renderer attached" is its honest failure); the harness Browser
  preview opened Shadertoy on 2026-08-12 and Claude Desktop died six seconds later
  (lesson `claude_embedded_preview_crash_trigger_2026_08_12`).

## Palette
Analogous, never a rainbow. The bed's LUT runs cool indigo to periwinkle to soft violet; the
deepseek identity pair from `design/refs/aurora-glass-tokens.css` is where those hues come from,
and coral is the one warm accent, used at lower brightness so it reads as an accent among the
cool rather than as a competing subject. Alarm and warn roles are spent only on alarms
(`design/CONTRACT.md` §1). A wide multi-hue sweep at high saturation is the 2018 gradient-mesh
look; modern dark surfaces read as one light source. Colour transitions ease through HSV the
short way round, never RGB.

## The bench, the eyes, the numbers
```
py scripts/vfx_render.py thumb --chunk <name> --t 1.0 --say "the reference, before I touch gap"
py scripts/vfx_render.py sheet --frames 12 --from 0 --to 8 --say "..."       # contact sheet over time
py scripts/vfx_render.py grid --a <p> --a-from 0 --a-to 1 --b <q> --b-from 0 --b-to 1 --t 2.0
py scripts/vfx_render.py state --state thinking --identity claude
py scripts/vfx_render.py ingest --name <n> --file <f>   # a Shadertoy paste, translated by scripts/vfx_ingest.py, notes + warnings
py scripts/vfx_probe_chroma.py                        # chroma-aware metrics over design/vfx-snaps
py scripts/ui_shot.py --label before --fps            # the cockpit at 1280x860 and 900x820 -> artifacts/ui/
```
`--say` posts beside the image in the bench feed. Metrics sit NEXT to the image, never as a
gate: the luminance-only probe was identical to sixteen digits across three visibly different
renders, which is why `scripts/vfx_probe_chroma.py` exists. A blind seat can measure every
structural cause of jank; only a visible window can measure fps.

## A true still of a feedback effect
`--t` freezes `u_time`, which is enough for a pure function of time and NOT enough for the aurora
with motion blur on, because every frame mixes the previous one in. The protocol: clear both
history textures, render the same t for a fixed K frames, capture the last. Forcing `u_motion`
to 0 gives a pixel-stable image of the core shader only; never present that as verification of
the shipped effect. (The one-frame seek convention was read in iart-ai/webgl-animation-skills,
MIT, on 2026-09-09; ours differs because ours accumulates.)

## Outside shaders
Shadertoy hands you a function; the bench wants a program (`py scripts/vfx_render.py ingest --name <n>
--file <f>`; the translation lives in `scripts/vfx_ingest.py`):
`mainImage(out vec4 fragColor, in vec2 fragCoord)` becomes `main()`, `iTime` becomes `u_time`,
`iResolution` becomes `vec3(u_res, 1.0)`, all by `#define` and never by textual substitution,
because the preprocessor knows what a token boundary is and a string replace does not. iChannel
textures, sound shaders and multi-pass buffers are refused in one sentence instead of failing
forty lines from the real problem. Techniques transfer; code, copy, brand and assets do not. The
geodesic core is adapted from Shadertoy llVXRd (CC-BY-NC-SA): a LICENSE GATE stands before any
public-site use.

---

# Part B — for the author, quoted from our own code

## The sketch skeleton (`design/vfx-sketches/*.frag`)
```glsl
#version 300 es
precision highp float;
out vec4 outColor;
uniform vec2  u_res;
uniform float u_time;
void main(){
  vec2 uv=(-u_res.xy+2.*gl_FragCoord.xy)/u_res.y;   // centred, aspect-true, y up: the bench's frame
  // ...
  outColor = vec4(col, 1.0);
}
```
The bench (`scripts/vfx.html`) adds the avatar's tunables when a sketch wants them: `u_sub`
`u_gap` `u_spin` `u_pulse` `u_sat` `u_tint` `u_dim` `u_wire` `u_id0` `u_id1` `u_round` `u_star`
`u_see` `u_thick`. Declare only what you use: `gl.uniform1f(null, x)` is a legal no-op, so one
driver can set everything and each style takes what it wants (`scripts/agent-avatar.js`, RENDER STYLES).

## The module skeleton — one seam, one house pattern
Fullscreen triangle, no vertex buffer (`scripts/activity-line.js`):
```js
var VERT = '#version 300 es\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.0-1.0,0.0,1.0);}';
```
The gate (`scripts/aurora-shader.js`):
```js
  function isSupported() {
    if (typeof document === 'undefined') return false;
    try {
      if (global.matchMedia && global.matchMedia('(prefers-reduced-motion: reduce)').matches) {
        return false;
      }
      return !!document.createElement('canvas').getContext('webgl2');
    } catch (e) {
      return false;
    }
  }
```
The contract, the same shape on every module:
```js
if (X.isSupported()) { const x = new X(canvasEl); x.start(); }
x.setState(...);   // the status layer owns WHEN; the shader owns the visual
x.setRate(0.5);    // activity, normalised 0..1
x.destroy();       // the mount restores the CSS fallback
```
The mount lives in `scripts/bifrost_ui.py` (DeepSeek's file). It constructs, starts, and only
THEN hides the CSS fallback (`aurora-fallback-hide`); `destroy()` puts the fallback back. When a
module is missing or refuses, the canvas says why in a data attribute: `cv.dataset.vlOff =
'no-webgl2' | 'pending-script' | 'ctor: ...'`. Pollers call `setState` only when the fingerprint
of the polled data changed (lesson `hud_fingerprint_diff_pattern`). The activity line's
`setTint([r,g,b])` is a display colour (it defaults to the console's OS blue); only the avatar's
`u_tint` is a diagnosis.

## The subject renders at native device pixels (`scripts/agent-avatar.js`)
```js
    var dpr = Math.min(global.devicePixelRatio || 1, 2);
```
One backing pixel per device pixel is the whole aliasing fix: the avatar used to render at 0.5
and let the browser stretch it, which was fine for a 38px chip and indefensible for a two-inch
object the eye is invited to study. No post-process recovers detail a 2x upscale destroyed.
Undersampling is correct for a full-screen ambient background; it was never correct for the
subject. `AKASHIC_AVATAR_SCALE` dials it.

## Counts are injected, never duplicated (`scripts/aurora-shader.js`)
```js
  .replace(/NPT/g,      String(NPT))
  .replace(/NTR/g,      String(NPT * TRAILP))
  .replace(/TRAILP/g,   String(TRAILP))
  .replace(/SEGN/g,     String(TRAILP - 1))
  .replace(/STEPS/g,    String(STEPS))
```
GLSL array sizes must be compile-time literals. Raise a count in JS and forget the shader, and
the loop reads past the uploaded data into whatever the driver left in those uniform slots,
which renders as stray geometry rather than as an error. STEPS × NPT is the inner product of
the whole aurora: it is the single number that sets the cost of everything. And STEPS × MARCH_DT
must span the depth the swarms actually occupy, or the volume clips them (CAMZ 3.6, a 0.30
start and 26 × 0.20 of march cover z from −3.3 to +1.9; the swarms live inside ±2.6).

## Jitter: static per pixel, never per frame (`scripts/aurora-shader.js`)
```glsl
    float jit = fract(sin(dot(gl_FragCoord.xy, vec2(12.9898, 78.233))) * 43758.5453);
```
A jitter fixed per pixel breaks march banding exactly as well as `hash(fragCoord + time)` and
does not shimmer. Per-frame jitter IS crawling film grain, the thing Daniel asked to remove, so
there is no separate grain term at all. The sin-fract hash is safe here because the program
declares `precision highp float;`; under mediump it bands into blocks.

## Feedback needs ping-pong (`scripts/aurora-shader.js`)
```glsl
      outColor.rgb = mix(texture(u_history, uv).rgb, outColor.rgb, u_motion);
```
When `u_motion` is 0 this is exactly the old crisp path, and the driver skips the whole offscreen
round trip (`const mb = this.motion > 0.001;`), so the feature is zero-cost when off. A shader
cannot read and write the same texture: the frame renders into a HISTORY framebuffer with the
PREVIOUS frame's texture bound as `u_history`, a passthrough blit puts it on the canvas, and the
two textures swap. They must match the canvas backing store exactly; a resize rebuilds them and
invalidates history, and `_firstFrame` gates the first read so a black history is never mixed in.

## Derivatives only on continuous values (`design/vfx-sketches/fibshell.frag`)
```glsl
    // AA width from the CONTINUOUS surface coord — fwidth(edge) explodes at cell
    // borders (cell-id discontinuity) and shreds whole quad rows; m does not.
    float aa = clamp(length(fwidth(m)) * sqrt(N) * 0.75, 0.02, 0.10);
```
The search window is sized for QUERIES, and brute force comes first:
```glsl
    // candidate window: a QUERY point needs azimuth-matched candidates, which are
    // NOT only Fibonacci gaps (that heuristic is for lattice-point neighbors).
    for (int j = -26; j <= 26; j++) {
      check(k0 + float(j), m, d1, d2, bk);
    }
```
Fifty-three tiny candidates is nothing at avatar sizes, and it cannot lie. The exhaustive sweep
is the ground truth a clever window must match (lesson `fibshell_shader_two_defect_classes`).

## A silhouette is antialiased by cone tracking (`scripts/agent-avatar.js`)
```glsl
    if(t>.001) cone=min(cone,m.d/t);
```
A raymarch answers hit/miss as a boolean, so every silhouette pixel is fully on or fully off;
that binary IS the staircase, and native resolution only renders it more crisply. Recording the
closest angular approach costs one `min()` per step and turns the outer edge into genuine
coverage. Tiling edges use the continuous-coordinate rule above; silhouettes use this one.

## The watchdog counts consecutive slow frames (`scripts/agent-avatar.js`)
```js
      if (sinceTick > 55) this._slowStreak = (this._slowStreak || 0) + 1;
      else this._slowStreak = 0;
      if ((this._slowStreak || 0) >= 45) {   // ~2.5s of consecutive slow frames, rAF firing
```
`requestAnimationFrame` is THROTTLED when the tab is hidden while `performance.now()` keeps
advancing, so frames-over-wall-clock reads a throttle as a dying GPU and latched the animation
off forever (the freeze bug, lesson `rAF_throttle_reads_as_fps_freeze`). Count back-to-back slow
frames instead, reset on `start()` and `visibilitychange`, and when it trips hold the last frame:
a still geodesic is a perfectly good avatar. A capped or disabled avatar SNAPS to its target
state: `cur` eases toward `target` only inside the loop, and a still that believes it changed
would render its initial state forever.

## The codebook: a state is a row, an identity is a gradient (`scripts/agent-avatar.js`)
```js
    thinking:  { sub: 3.1, gap: 0.009, spin: 0.06, pulse: 1.0,  ...
    tool:      { sub: 3.4, gap: 0.006, spin: 0.55, pulse: 0.45, ...
```
Thinking is INTERNAL (barely turns, breathes hard); tool use is EXTERNAL (spins fast, breathes
little): tell them apart by movement before the colour resolves. Grey means we cannot see.
Identity presets are the `.av` chip gradients from `scripts/bifrost_ui.py` lifted verbatim; a
second scheme would split the design system in two. Rill wears the deepseek gradient because
Rill IS DeepSeek; prefix matching lets incarnations inherit their parent's identity. Tint eases
through HSV the short way round: thinking violet to tool green through RGB passes through a
desaturated grey-brown, and every intermediate frame looked like a fault.

## More laws the avatar's comments teach (`scripts/agent-avatar.js`)
- The body is a superquadric by a radius-in-direction swap under an unchanged tiling; `u_cube = 0`
  is bit-identical to the sphere and the morph is continuous, never a branch.
- Tetrahedral normals: four `map()` evaluations instead of six, a third off the per-pixel cost.
- The see-through back layer is a closed-form ray-sphere solve evaluated once at the far point,
  never a second march; only the far EDGES come through, or the silhouette floods flat.
- A scratch compile builds and links the new program BEFORE deleting the old, so a failed
  experiment leaves the working renderer untouched and returns the driver's error text.
  Sketches never enter STYLES: a style is mountable, a sketch is being tried.
- Wireframe is a reassignment of where the light lives, not a new geometry; identity lives in
  the body, state in the lines, and neither channel disturbs the other.

## Traps (each one compiled, rendered, or crashed before it became a rule)
- `precision mediump float;` — our hashes band into blocks; `highp` always.
- A count written in JS and again in GLSL — inject it (see "Counts are injected").
- `fwidth` of a cell id, a branch index, or anything discontinuous — rows shred (see "Derivatives").
- `?:` on a struct type — ESSL refuses; `if/else`. Caught only because the shader was compiled
  before shipping rather than eyeballed.
- Sampling the texture you are rendering into — undefined feedback; ping-pong (see "Feedback").
- A watchdog that divides frames by wall-clock — reads a hidden tab as a dying GPU (see "Watchdog").
- A header comment as the source of truth — the avatar's header said "half-res, ~1k fragments"
  after `_resize` had gone native. Read the function, then fix the bullet.
