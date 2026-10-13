# shaderlab: the house runtime for the Shadertoy interface

`toy-runtime.js` runs a shader saved in the corpus (`state/arsenal/shaders/corpus/shaders/<id>/shader.json`) the
way it was written to run: Common prepended, the buffers in float ping-pong targets in the order the shader saved
them, Cube A, then Image, with the uniforms and channel inputs that interface defines. `render.html` + `render.js` turn it into deterministic PNG
stills for the headless driver (`py -m arsenal shader render`), on SwiftShader only.

The interface (uniform names, pass types, output ids, sampler words) is public. The code here is ours: nothing is
copied from shadertoy.com's site JavaScript or from any corpus shader, and the tests use synthetic shaders.

## Rules this directory keeps

- **CPU only.** `render.html` reads the renderer string before compiling and refuses to draw unless it names
  SwiftShader and no hardware (`judgeRenderer`, the same rule and `HARDWARE_HINT` as the headless driver; the node
  tests hold the two equal). This host has an AMD display-driver crash history. Do not open these pages in an ordinary browser
  or in the Claude Browser pane; go through the headless driver, which holds the GPU lock (`arsenal/GPU-LOCK.md`).
- **Raw WebGL2.** `#version 300 es` on line 1, `precision highp`, a fullscreen triangle from `gl_VertexID`. No
  three.js, no CDN, no build step.
- **No pretending.** Missing media become deterministic procedural stand-ins, and `stats().substituted` lists each
  one. Things that cannot run are listed in `stats().unsupported`.

## The Shader Lab page (`/lab/`) and the live switch

`py -m arsenal shader serve` serves the lab at http://127.0.0.1:8797/lab/ (`index.html` + `lab.js`, which mount the
Workbench in `arsenal/web/lib/workbench/`).

### Live runs: off until a deliberate local setting

**Live runs are off until their safety review clears.** The lab opens view only, and stays that way unless one switch
is set by hand, in that browser, on purpose. Turning it on is Daniel's call once the review clears.

| | what the page does |
|---|---|
| off (the default) | The Stage shows the subject's SwiftShader still and, for a loved shader, plays its filmstrip on a click (the contact sheet stepped frame by frame: an image, no GPU work). It says "Live runs are off until their safety review clears". There is no Run button, no scale menu, no Stop and no Take. No code path loads the runtime, makes a canvas or asks for a WebGL context. |
| on | "Run live on this GPU" appears on the Stage, behind the guards below. |

The switch is on only when **both** hold:

1. the address asks for it: `/lab/?live=1`, and
2. this browser holds the key: `localStorage['arsenal.shaderlab.live'] === 'on'`.

To turn it on, open http://127.0.0.1:8797/lab/, run this in that tab's browser console, then open
http://127.0.0.1:8797/lab/?live=1:

```js
localStorage.setItem('arsenal.shaderlab.live', 'on')
```

A link alone cannot turn it on, and a key left behind does nothing on a plain `/lab/`. The key belongs to one origin and
one browser profile, so another port, another browser or a private window starts off. A storage that cannot be read
(blocked site data) counts as off. To turn it off again, open `/lab/` without `?live=1`, or remove the key:

```js
localStorage.removeItem('arsenal.shaderlab.live')
```

How it is kept (`stage.js`, pinned in `tests/workbench_lab.test.mjs`): `liveSwitch()` reads the address and the key
once, when the Stage mounts. Two places could start the live path: `build()`, the only place that makes a canvas and
asks the runtime for a toy (its WebGL context), and `loadLive()`, the only place that loads the runtime. Both begin
with `mustBeLive()`, which throws while the switch is off. Every way in (Run, Run again, a scale change, a knob
change, a size change) returns before reaching them. The tests call every Stage method and fire every event with the
switch off, and count runtime loads, canvases, `getContext` calls and animation frames: all must be 0. They also read
`stage.js` and require one canvas, one `createToy` and one runtime load, each behind the check.

With the switch on, the Stage keeps the guards described at the top of `stage.js`. It names the cost class before the
click and starts C3 and C4 at half scale at most. It runs a pre-flight on small frames before any full-size frame:
64 x 36, then 128 x 72 (90 x 51 when the tiny frame is too heavy for 128 x 72 at the cube), and larger ones while
those readings leave the growth unproven, none larger than the frame the class may start at. It takes the steepest
growth its readings allow (the cube of the pixels when they cannot bound it). It reads what every frame pays twice and
keeps the smaller, and sets aside a reading larger than the tiny frame (a timing hiccup). It locks the size it
measured. A larger scale is a ladder of one step at a time, each step capped at 150 ms. The house watchdog
holds the last frame (one frame over 500 ms, 2.5 s of slow frames, or 45 slow frames in a row). After any hold, Run
again measures first and draws below the frames that held. A refusal lasts for the page.

**Still owed before the switch may be turned on** (the third live-path re-review, 2026-10-13; the commit that landed
this round is `1a413b29`):

- **A hiccup on a frame reading can still flatten the measured growth.** One slow pre-flight frame (a GC pause, the
  scheduler) makes a steep shader look shallow, so its first live frame can far exceed the prediction. In the
  reviewer's simulation, 84 of 392 runs drew a live frame over 500 ms, the worst about 85 s. It predates this round and
  is identical on the older stage; the per-frame-cost hiccup is fixed, this one is not. A fix reads each pre-flight
  size at least twice and keeps the smaller, or refuses when two readings of one size disagree beyond their error.
- **Symmetric noise on the per-frame reading biases it low** once the smaller of two is kept (worse than before at
  about 30% noise, better at 5 to 10%, which is what SwiftShader showed). A median of three, or keeping the smaller
  only when the two disagree beyond their error, would remove the bias.
- **Cheap subjects can stay at a lower scale than they could run**, because the start-scale bound removed the larger
  reading that proved their growth. A usability cost, not a risk.
- **The 90 x 51 fallback draws frames that cannot change the verdict** for tiny frames already too slow for the
  smallest scale; a pre-check could refuse without them.

The screenshot driver (`arsenal/shaders/lab_shot.mjs`) shoots its view-only views with the switch off. Its receipt
requires no Run button, no canvas and no WebGL context on each of them. Only its `run` view turns the switch on, and
only inside its own private headless Chrome. That Chrome is forced onto SwiftShader, and the renderer is checked
before the page loads. The run view never touches this machine's GPU.

## The runtime API (`toy-runtime.js`, an ES module)

```js
import { createToy } from './toy-runtime.js';
const toy = createToy(canvas, shaderJson, {
  mediaUrl: (src) => url | null,   // src is the saved site path, e.g. /media/a/<sha>.png; null = stand-in
  audio: { fft, wave } | null,     // the starting audio texture (see setAudio)
  pixelRatio: 1,                   // resize(w, h) sizes the canvas to w*pixelRatio x h*pixelRatio
  cubeSize: 1024,                  // Cube A face size (Shadertoy's; lower it for speed only if the shader allows)
  hwPerformance: 1,                // the HW_PERFORMANCE define
  fps: 60,                         // advance()'s default step rate
  dateBase: null,                  // [y, m0, d, s]: iDate = base + iTime (reproducible clocks); null = the real clock
  bufferFormat: null,              // 'RGBA16F' to force one; default the best renderable
  mediaTimeoutMs: 15000,
  parity: true,                    // the GPU-parity shims (below); false compiles every pass exactly as written
});
await toy.ready;                   // media loaded or substituted (toy.load() returns the same promise)
const c = toy.compile();           // {ok, drawable, passes: [{name, type, key, ok, log, mappedLog, firstError, lines, parity}], warnings}
toy.render({ time, frame, timeDelta, frameRate, mouse, date });   // one frame; omitted fields continue
toy.advance(toTime, { fps, maxFrames, mouse });   // fixed-dt frames up to toTime -> {frames, frame, time, reached, behind}
toy.history;                       // true when a frame reads an earlier frame (a feedback buffer or Cube A)
toy.jump(toTime, { fps, mouse });  // history-free shaders only: draw just the frame advance() would end on
toy.reset();                       // clear buffers, Cube A, keyboard, mouse and clock (frame 0, no history)
toy.setAudio({ fft, wave });       // fft 0..1, wave -1..1; 512 values each (other lengths are resampled)
toy.setKeyboard(keyCode, down);
toy.resize(w, h);                  // buffers keep their pixels where old and new sizes overlap (Shadertoy's resize)
toy.stats();                       // {frame, time, passes, order, reads, substituted, unsupported, bufferFormat, ...}
toy.info();                        // renderer, vendor, caps, buffer format
toy.destroy();
```

- `compile().ok` is every pass compiled; `drawable` is every drawn pass compiled (a broken Sound pass does not stop
  the picture). Compiling is all or nothing: the new programs replace the old ones only when every drawn pass
  linked, so a frame never mixes a new pass with an old one. `mappedLog` rewrites `ERROR: 0:<n>:` to
  `ERROR: <pass name>:<line>:`, or `Common:<line>:` when the error is in Common, so the line number is one a reader can
  open in the pass's own `.glsl` file.
- **The mouse.** `mouse` is a state, `{x, y, clickX, clickY, down, clicked}`, or a ready iMouse vec4.
  `mouseUniform(state)` builds the vec4 Shadertoy's page builds: xy the pointer, z = +clickX while the button is held
  and -|clickX| after release, w = +clickY on the one frame of the click and -|clickY| on every other frame, and all
  zeros before any click. A click lasts one frame: the next frame continues with `mouseAfterFrame` (w negated);
  `advance` gives the click to its first frame only, and `jump` to frame 0 only (it stands for the walk's last frame).
- **iFrameRate** is the walk's nominal fps for `advance` and `jump` (the shorter last step to an off-grid t keeps its
  own iTimeDelta but not a doubled rate); a bare `render` without `frameRate` reports 1 / timeDelta.
- **A feedback shader's still is not a function of t.** `advance(t)` from a `reset()` steps frame n at time n/fps,
  then one last frame exactly at t. The same t always gives the same frames. Continuing from an on-grid t equals a
  fresh run; `render.js` resets before a t that follows an off-grid one.
- **Audio.** `setAudio` feeds every music, musicstream and mic input: the 512x2 R8 texture, row 0 the spectrum
  (byte = fft x 255), row 1 the waveform (byte = (wave x 0.5 + 0.5) x 255, so silence is 128). To match an
  AnalyserNode with fftSize 2048, pass its first 512 bins as 0..1. This is how the piano will drive audio-reactive
  shaders. Without audio the texture is silence, listed in `substituted`.
- **Keyboard.** 256x3 R8: row 0 keys down, row 1 keys pressed this frame (cleared after each frame), row 2 toggles.
- **History-free stills.** `toy.history` is false when no pass reads a buffer holding the previous frame
  (`needsHistory()`). Then every frame is a function of its uniforms alone, and `jump(t)` draws only the walk's last
  frame (same iFrame, iTime, iTimeDelta; `jumpStep()` is tested equal to `advanceSchedule()`'s last entry). `render.js`
  jumps for such shaders, so a slow raymarcher's t=4 costs one frame, not 241.
- **60 fps by default.** `DEFAULT_FPS` (the runtime) and `render.html`'s `fps` both default to 60, Shadertoy's
  rate. A still's iFrame, and a walk's iTimeDelta, are what the shader saw on Shadertoy only at that rate: a shader
  that counts iFrame (a glitch cadence, a particle index) or integrates iTimeDelta shows a different picture at 30.
- **GPU-parity shims.** SwiftShader answers a few built-ins differently from the GPUs the corpus was written on, and
  the header routes those calls to replacements that give the GPU answer (`PARITY_SHIMS`, measured with synthetic
  probes on this host, 2026-10-13):
  - `tanh(x)` returns NaN (black) once |x| passes about 88; GPUs return +-1. The shim clamps x to +-15 first.
  - `min(a, b)` / `max(a, b)` returned NaN when `b` was NaN; GPUs return the operand that is not NaN. Raymarchers
    rely on it: an SDF term that is 0/0 on a ray's first step vanishes inside `min()` on a GPU. One corpus tunnel drew
    solid black without this shim. The probe saw one operand order, and SPIR-V leaves a NaN operand undefined, so the
    shim tests both operands (`mix(mix(min(a, b), a, isnan(b)), b, isnan(a))`) and works whichever one the built-in
    keeps; the node tests evaluate it under both rules.
  The shims are user functions, so a shader that uses `min`/`max`/`tanh` in a const initializer does not compile with
  them. `compile()` then retries per pass at the next level (`PARITY_LEVELS`: full, tanh-only, minmax-only, none),
  reports the level as `passes[].parity`, and warns. In the 335-shader corpus, 8 passes in 4 shaders compile at
  tanh-only (counted before minmax-only existed).

## Semantics, briefly

| thing | what the runtime does |
|---|---|
| pass order | The buffers in the order the shader saved them (not by letter: a save listing A, D, B, C runs D before B), then Cube A, then Image (`EXEC_GROUP`), as Shadertoy's client walks its pass list. A read of an earlier pass sees this frame; of itself or a later pass, the previous frame. `passOrder()` labels every read. |
| buffer targets | RGBA32F with `EXT_color_buffer_float` + `OES_texture_float_linear`, else RGBA16F, else RGBA8 (warned). Sized to the canvas, cleared to 0. A resize copies each half texel for texel over the overlap (the rest 0) and restarts the ping-pong on half 0, Shadertoy's quirk included. Cube A uses RGBA16F when it renders (memory). |
| Cube A | `mainCubemap(fragColor, fragCoord, rayOri, rayDir)` per face, with `fragColor` an `out vec4`, `fragCoord` an `in vec2` and the ray origin and direction `in vec3`; rayDir from the GL cube-map selection table inverted (`CUBE_FACES`), rayOri = 0. |
| Sound | compiles (`mainSound(int, float)` or `mainSound(float)`) against the sound uniform set (no iResolution, iTime, iTimeDelta, iFrameRate, iFrame, iMouse: a sound pass may declare its own); never played (listed in `unsupported`). |
| texture | sampler objects carry filter (nearest, linear, mipmap) and wrap (clamp, repeat, mirror); vflip flips the upload; srgb uploads as SRGB8_ALPHA8. |
| cubemap | six faces `<name>.<ext>`, `<name>_1..5.<ext>` in GL order +X, -X, +Y, -Y, +Z, -Z; with vflip each face uploads flipped and `_2`/`_3` trade places (+Y gets `_3`), as Shadertoy uploads it (`cubemapUploadOrder`). |
| volume | `.bin`: 20-byte little-endian header (signature, width, height, depth, channels, layout, format 0 = u8 / 10 = f32), then texels. One texture per file, always with its mip chain (warned if the format cannot have one). |
| two inputs on a channel | the last one saved: the header's sampler type, the binding and iChannelTime all use it (`channelInput`). |
| video, webcam | procedural stand-in, listed. |
| missing media | a seeded stand-in with mipmaps, in the style the file's kind usually has (`standinStyle`): a `.png` is per-texel RGBA noise whose channels pair as G(x, y) = R(x-37, y-17), the layout noise lookups rely on; a `.jpg` (a photograph or material) is a smooth, tiling, photo-like field (`proceduralPhoto`); a cubemap is a soft sky-and-ground environment (`proceduralEnvironment`, 128^2 faces); a volume is noise (32^3). 2D stand-ins are 256^2 except the four files `KNOWN_MEDIA` pins by how the corpus addresses them (a 1024^2 and two 64^2 noises, one smooth PNG). Each is listed in `substituted` with its `style`. |
| uniforms | iResolution, iTime, iTimeDelta, iFrameRate, iFrame, iChannelTime[4], iChannelResolution[4], iMouse, iDate, iSampleRate (44100), iChannel0..3 as sampler2D / samplerCube / sampler3D. |
| iChannelTime | per channel (`channelTimes`): iTime on a music, musicstream or video channel (its media playing from the start), 0 on every other channel, as Shadertoy gives 0 to buffers, textures, the keyboard, the webcam, a live mic and empty channels. |

## Pure helpers (no WebGL; tested in node)

`buildHeader`, `buildFooter`, `assembleSource`, `sanitizeGlsl`, `mapErrorLog`, `parseErrorLog`, `locateLine`,
`passOrder`, `passKey`, `inputKind`, `bufferKeyForInput`, `samplerFor`, `samplerTypeFor`, `channelInput`,
`channelTimes`, `parseVolumeBin`, `keyboardTextureLayout`, `createKeyboardState`, `packAudioTexture`,
`cubemapFacePaths`, `cubemapUploadOrder`, `cubeFaceBasis`, `advanceSchedule`, `jumpStep`, `needsHistory`,
`onFrameGrid`, `dateUniform`, `mouseUniform`, `mouseAfterFrame`, `bufferFormatCandidates`, `chooseBufferFormat`,
`proceduralTexture`, `proceduralPhoto`, `proceduralEnvironment`, `proceduralVolume`, `standinStyle`, `standinSize`,
`standinPixels`, `normalizeShader`, `shaderFromGlsl`, `judgeRenderer`, `rendererInfo`; the tables `EXEC_GROUP`,
`PARITY_SHIMS`, `PARITY_LEVELS`, `KNOWN_MEDIA`, `HARDWARE_HINT`.

Where Shadertoy's behaviour is not in its public documentation (pass order, resize, iMouse signs, iChannelTime, the
flipped-cubemap faces), it was read from Shadertoy's client code (`effect.js`, `piLibs.js` and the page script,
2026-10-13, in public mirrors of the site's scripts) and written here from that description; no site code is copied.

Tests: `node tests/shaderlab_runtime.test.mjs`. The GL path is tested against a recording fake WebGL2 context that
enforces the rules a real one would refuse a draw for (feedback loops, sampler units, uniforms set on the bound
program, `#version` on line 1). Pixels themselves are proved only by the headless SwiftShader harness.

## render.html

```
render.html?src=<shader.json or .frag url>&t=0,1.5,4&w=480&h=270&fps=60&media=<prefix for /media/a/ files>
            [&fps=N (60)] [&budget=ms (120000)] [&cube=N (1024)] [&hw=0|1] [&parity=0|1 (1)]
```

Sets `window.__render = {done, ok, renderer, compile, frames: [{t, png, ms, frames, frame, reset, jumped}], warmMs,
history, substituted, unsupported, errors, stage, params, stats}`. `warmMs` is one more frame drawn after the stills
are saved and timed to completion (a 1x1 readPixels): SwiftShader compiles a program at its first draw, so a still's
`ms` overstates the per-frame cost, and `warmMs` is the number to compare across shaders. `parity=0` (the harness's
`--no-parity`) compiles without the shims, to see SwiftShader's own answers. A watchdog ends the page with an error when the budget is spent, and
the frame walk yields every 50 ms so it can fire. `media` defaults to `/corpus/media/` when the page is served from
`/lab/` by `py -m arsenal shader serve`. The iDate of every still is 2026-01-01 12:00 plus iTime.
