# Play Night: First Light becomes an instrument

Status: build spec, 2026-09-13 evening. Extends `arsenal/FIRST-LIGHT-SPEC.md`; everything there still holds unless this file says otherwise.

Daniel, verbatim: "Lets keep the momentum going, would be so cool if we had something we can play with tonight!"

Tonight's slice turns First Light into a MilkDrop-style instrument:
- Live audio drives a bank of shader presets. The source is FL Studio through the Focusrite Loopback input, or the clip that is playing.
- The KeyLab 88 mk3 plays it. Encoders move macro knobs; keys and pads flash or switch presets.
- It runs full screen, with or without a video.

## Hard rules

- The First Light hard rules still apply: bind 127.0.0.1 only, and never open GPU pages in the Claude app's browser pane.
- `/first-light` must keep working unchanged. Its receipt (`node arsenal/lanes/chrome_verify.mjs`) is the regression baseline.
- A live input device is analysed only. It is never routed to the speakers: the Loopback input already carries the speaker mix, so routing it back would feed back.
- No library is expected tonight. One is allowed if it is clearly the best option (Daniel's ruling).

## Layout and owners

```
arsenal/
  PLAY-NIGHT-SPEC.md                                   [Vandor]
  presets.py        preset header parsing and checks   [Vandor]
  serve.py          + GET /play, GET /api/presets      [Vandor]
  graphs/play-night.json, modules/webaudio.analyser.json, modules/vfx.preset-bank.json  [Vandor]
  web/play.html, play.js, play.css                     [page agent]
  web/presets/first-light.frag + 3 more                [Navi]
  web/presets/scope-bars.frag, glitch-blocks.frag, mirror-hue.frag, halftone-pop.frag  [preset agent]
  lanes/play_verify.mjs    preset sweep receipt        [Vandor]
tests/test_arsenal_presets.py                          [Vandor]
tests/test_arsenal_pins_playnight_heimdall.py          [Heimdall, blind from this file]
```

## Preset file format

Each preset is one GLSL ES 3.00 fragment shader file: `arsenal/web/presets/<id>.frag`.

- **Line 1** is exactly `#version 300 es`, with nothing before it (GLSL ES and ANGLE require this).
- **Line 2** is `//! ` followed by a one-line JSON object:
  `{"id": "<file stem>", "name": "Human Name", "author": "Navi", "tags": ["video", "generative"], "params": [{"k": 1, "name": "trails", "default": 0.6}]}`
  - `id` equals the file stem and matches `^[a-z0-9][a-z0-9-]{1,40}$`.
  - `name` and `author` are non-empty strings. `tags` is a list of strings (it may be empty or absent).
  - `params` has at most 8 entries. Each entry has:
    - `k`: a whole number from 1 to 8, unique within the file; it drives `u_k<k>`
    - `name`: 1 to 16 characters
    - `default`: a number from 0 to 1
- **The body** must contain:
  - `precision highp float;`
  - `in vec2 v_uv;` (origin at the bottom left)
  - `out vec4 outColor;`
  - uniform declarations only from the list below, with exactly the listed types. Several names may share one declaration: `uniform float u_bass, u_mid;`.
- **Craft floors** (house shader-craft; Daniel's ruling removed only the cockpit's library and single-context rules):
  - `highp` only, never `mediump` or `lowp`
  - no uniform inside a `for` loop condition, so every loop bound is constant
  - no NaN or Inf: guard divisions, `pow` of negatives, and `log` of values at or below zero
  - no per-frame crawl: noise that changes over time must be smooth, never `hash(u_time)`
  - keep it cheap: about 8 texture reads per pixel at most
- **Both modes must look good:**
  - with video (`u_has_video == 1.0`) and without it (`u_has_video == 0.0`, visualizer mode)
  - in silence (all audio uniforms at 0) as well as with loud audio

`arsenal.presets.parse_preset(path) -> dict` returns:

```
{"id", "file", "url": "/web/presets/<file>", "name", "author", "tags": [...],
 "params": [{"k", "name", "default"}], "problems": [str, ...]}
```

- `problems` is empty for a valid file. Every rule broken adds a human-readable problem.
- Fallbacks: `id` is always the file stem; `name` falls back to the stem, `author` to `""`, `tags` and `params` to `[]`.
- `arsenal.presets.list_presets(directory=None) -> list[dict]` parses every `*.frag` in the directory (default `arsenal/web/presets`).
  - The list is sorted by lowercased name, then id.
  - A directory that does not exist gives `[]`.

## Uniforms v1

This is a superset of First Light's list. The page sets every uniform on every frame; uniforms a preset does not use are optimised out.

| uniform | type | meaning |
|---|---|---|
| `u_video` | sampler2D | Current video frame, uploaded with `UNPACK_FLIP_Y_WEBGL`. A 1x1 black texture when there is no video. |
| `u_prev` | sampler2D | This preset's own previous output (feedback), at canvas size. Cleared to black when the preset becomes active, on resize, and on an epoch bump. |
| `u_audio` | sampler2D | 512x2, one channel (R8), linear filtering, uploaded without a Y flip. Row 0 (sample at y = 0.25) holds the spectrum, log-spaced 20 Hz to 16 kHz, 0..1. Row 1 (y = 0.75) holds the waveform, 0..1, where 0.5 is silence. |
| `u_res` | vec2 | Canvas size in device pixels. |
| `u_video_res` | vec2 | Video size, or (1, 1) without video. |
| `u_time` | float | Performance clock in seconds since the page loaded. It never jumps or pauses. (First Light's `u_time` was media time; see `u_media_time`.) |
| `u_media_time` | float | The clip's media time in seconds, 0 without a clip. |
| `u_frame` | float | Frames rendered since this preset became active. |
| `u_has_video` | float | 1.0 when a video frame is bound, otherwise 0.0. |
| `u_pulse` | float | 0..1, the smoothed `0.65*bass + 0.35*flux` (12 ms attack, 180 ms release), as in First Light. |
| `u_beat` | float | 0..1. Set to 1 on a detected beat, a note-on (scaled by velocity) or a key hit, then decays as `exp(-dt/0.18)`. |
| `u_level` | float | 0..1, overall loudness (RMS), auto-gained. |
| `u_bass`, `u_mid`, `u_high`, `u_flux` | float | 0..1, auto-gained bands. |
| `u_hue` | float | 0..360 degrees, global hue offset. |
| `u_intensity` | float | 0..1, global strength (a fader). |
| `u_k1` ... `u_k8` | float | 0..1 macro knobs, named by the preset header. A preset's defaults load when it becomes active. |

### Authoring notes

The vertex shader is First Light's fullscreen triangle (`VERT_SRC` in `web/first-light.js`). Use this letterbox helper:

```glsl
vec2 video_uv(vec2 uv) {  // screen uv -> video uv; outside 0..1 means no video there
  float ca = u_res.x / max(u_res.y, 1.0), va = u_video_res.x / max(u_video_res.y, 1.0);
  vec2 s = va > ca ? vec2(1.0, ca / va) : vec2(va / ca, 1.0);
  return (uv - 0.5) / s + 0.5;
}
```

For feedback trails:
- Fade with a small subtraction as well as a multiplier, for example `max(prev * 0.96 - 1.0/255.0, 0.0)`. The feedback buffer may be 8-bit, and a multiplier alone leaves residue that never clears.
- `outColor.rgb` is clamped to 0..1 when presented, and alpha is ignored.

These notes come from the first preset checks on 2026-09-13:
- The page gives `u_video`, `u_prev` and `u_audio` CLAMP_TO_EDGE wrapping and LINEAR filtering.
- Apply `u_hue` to freshly drawn colour and to the video, never inside the `u_prev` loop. A rotation inside feedback compounds every frame and strobes.
- A knob should set an amount or an angle, never a speed multiplied by `u_time`. Moving such a knob makes the whole picture jump.
- Smooth fast signals before driving geometry with them, for example `0.6*u_pulse + 0.4*u_bass`. Raw bands jitter a zoom.
- Visualizer mode in silence is a real case: FL Studio between takes. It should still show something alive and legible, not a near-black frame.

## Page: `web/play.html`, served at `/play`

### Preset engine

- Load `GET /api/presets`, then fetch and compile each preset's `url`.
- Show broken presets in the list, greyed, with their first problem or compile log. Never pick them for next, previous or random. A preset that fails to compile is broken the same way, and the HUD shows its info log.
- A built-in preset `builtin` ("Passthrough") always exists. It shows the letterboxed video, or a simple spectrum scope without video. It is active when nothing else is.
- Each preset renders into its own ping-pong pair of framebuffers at the canvas backing size:
  - Use RGBA16F when `EXT_color_buffer_half_float` or `EXT_color_buffer_float` is available, otherwise RGBA8.
  - `u_prev` is the other half of the pair.
- Crossfade on a switch: render both presets for `xfade_ms` (default 600, 0 means a cut) and mix them to the screen with a built-in blit shader, using a smoothstep-eased mix.
- Use one WebGL2 context and present to the default framebuffer.
- Keep First Light's context-loss handling and slow-frame watchdog.

### Audio engine

The source is chosen in the UI.
- **`clip`** is the default while a clip plays: a `MediaElementAudioSourceNode` on the `<video>`, also connected to the destination so the clip is still heard.
- **`input`** is `getUserMedia` with the chosen `deviceId` and `echoCancellation`, `noiseSuppression` and `autoGainControl` all false.
  - Request permission once, then list devices by label. Labels are empty until permission is granted.
  - Never connect it to the destination.
  - The Focusrite "Loopback" input carries FL Studio's output.
- **`analysis`** is First Light's precomputed server features. It is a stretch goal: include it if cheap.

Rules:
- Resume the AudioContext on the first user gesture.
- Use one `AnalyserNode` with `fftSize` 2048 and `smoothingTimeConstant` 0. Read frequency and time-domain data once per rendered frame.
- **Bands** by bin frequency: bass 20-150 Hz, mid 150-2000 Hz, high 2000-16000 Hz. Band power is the mean linear power over its bins; `dB = 10*log10(power + 1e-12)`.
- **Auto-gain** per signal:
  - `ceiling = max(dB, ceiling - 6*dt)`
  - `floor = min(dB, floor + 3*dt)`
  - keep `ceiling - floor >= 12`
  - `value = clamp((dB - floor)/(ceiling - floor), 0, 1)`, and 0 when `dB < -80`
- **flux** is the positive spectral flux of linear magnitude over 20 Hz to 16 kHz, auto-gained the same way.
- **level** is the RMS of the time-domain frame in dB, auto-gained.
- **Beat** fires when the bass value exceeds 1.35 times its 1 s moving average and is above 0.3, with a 180 ms refractory period.
- **`u_audio` row 0** holds 512 log-spaced columns interpolated from the dB spectrum, mapped from -90..-20 dB to 0..1. **Row 1** holds 512 samples of the time-domain frame mapped from -1..1 to 0..1.

### MIDI performance layout

- Connect as in First Light, preferring an input named "KeyLab".
- **Learn:** click a target, then move or press a control.
  - Continuous targets are k1-k8, hue, intensity and xfade; a CC drives them as value/127.
  - Trigger targets are next, prev, random, blackout and preset slots 1-12; a note drives them.
- **Defaults before anything is learned:**
  - any note-on flashes `u_beat` at velocity/127
  - CC 1 (mod wheel) drives hue
  - CC 7 drives intensity
- Mappings persist in localStorage under `arsenal.play.midiMap`, with try/catch around both reading and writing.
- Record latency p50/p95 as First Light does, from `event.timeStamp` to the frame that shows it.

### Keyboard

| key | action |
|---|---|
| `1`-`9` | preset by list position |
| left/right arrows | previous/next preset |
| `R` | random preset |
| `X` | toggle crossfade between 600 ms and a cut |
| `H` | hide or show the UI (performance mode) |
| `F` | fullscreen |
| `Space` | play or pause |
| `L` | loop |
| `B` | blackout |

Keys are ignored while typing in an input.

### Modes

- **Performance mode (`H`):**
  - The canvas fills the window and every panel is hidden.
  - On a preset change, the preset name and author show in a corner for 1.5 s, then fade.
  - Moving the mouse shows a one-line hint that hides after 2 s.
- **Visualizer mode:** `/play` opens with no clip, runs the active preset with `u_has_video = 0`, and uses the `input` source when one is chosen. Loading a clip turns the video on and switches the audio to `clip`, unless the user pinned `input`.

### HUD

- fps, the active preset, and compile status
- the audio source, with meters for level, bass, mid, high and beat
- MIDI device and last control
- latency p50/p95
- the take id and event count

### Takes

Reuse the ledger. A take opens on the first play or the first preset switch, and a clip change closes it and opens a new one. Events:
- `preset {id, from, xfade_ms}`
- `param {name, value}`, at most 10 Hz per name
- `audio_source {kind, device_label}`
- `midi` as in First Light

With a clip, `t` is First Light's media clock. Without one, it is `{clock: "presentation", epoch: 0, ticks: round(performance.now()), timebase: "1/1000"}`.

## Server

- `GET /play` serves `web/play.html`. A missing page returns 503.
- `GET /api/presets` returns `{"presets": list_presets(app.presets_dir)}`. `App(roots, takes_root=None, presets_dir=None)` accepts the directory, so tests can use a temporary one.
- Preset files are served by the existing `GET /web/presets/<file>`.
- `GET /api/graph/play-night` returns `graphs/play-night.json` (clip -> decode -> preset bank -> screen, with the audio analyser and MIDI bound to the bank's params).

## Piano detour (the same night)

Daniel, verbatim: "I've always wanted to make a really cool piano visualization! perhaps we can make a detour to set up a 3d rendered animated piano for tiktok where the chords and notes are displayed! We could even make it show sheet music!"

The piano is built in parallel by the piano agent: `web/piano.html`, `piano.js` and `piano.css`.
- It is a three.js scene fed by Web MIDI: keys, note trails, chord names, a grand staff, and 9:16 or 16:9 framing.
- The server additions are Vandor's:
  - **`GET /piano`** serves `web/piano.html`. A missing page returns 503.
  - **`POST /api/recordings?name=<label>`**
    - The body is the recording itself. `Content-Type` must be `video/webm`, `video/mp4` or `video/x-matroska`, with parameters allowed; any other type returns 415.
    - `Content-Length` is required and at most 4 GB (411 when missing, 413 when too large).
    - The file is saved as `<first library root>/arsenal-renders/<YYYY-mm-dd HH-MM-SS> <label>.<ext>`.
    - The label is sanitized to `[A-Za-z0-9_-]` with runs replaced by `-`, at most 40 characters, and defaults to `recording`. A name clash appends ` (2)`, ` (3)` and so on.
    - The upload is written to a `.part` file first, then renamed.
    - The reply is `200 {"path", "clip_id", "bytes"}`, or `400` if the body ends early.
    - The recording shows up in `/api/library` at the next rescan.

## Receipt: `node arsenal/lanes/play_verify.mjs`

1. Load `/play` with the test clip playing in an isolated, muted Chrome with a fake audio device.
2. Activate each preset for 1.5 s, recording its compile status and the dropped-frame count.
3. Run the same sweep once in visualizer mode, without a clip.
4. The receipt passes if every non-broken preset compiles, there are no page exceptions, and dropped frames stay at or below 0.5% of the sweep.

## Later (v2 ideas, not tonight)

- **Speed knobs:** add per-knob phase accumulators (for example `u_phase1`..`u_phase4`), with the page integrating `rate * dt`. A knob can then set a speed without the picture jumping. Today a knob may only set an amount, because `u_time * knob` jumps when the knob moves.
- **Piano render mode:** export MIDI + WAV from FL Studio and render a frame-perfect 1080x1920 60 fps video offline, instead of recording live.
- **Scrolling sheet music** from a MIDI file, beyond tonight's held-chord staff.
- **Vendored libraries:** keep pinned copies of three.js and the notation library under `arsenal/web/vendor/` so the pages work offline. This needs Daniel's OK to download them.
- **Preset hot reload:** recompile a preset when its file changes on disk.

## Acceptance tonight (Daniel playing)

1. FL Studio audio through the Loopback input visibly drives the visuals.
2. KeyLab encoders move macros, and keys or pads flash or switch presets.
3. Full-screen performance mode works with and without a clip.
4. Every preset compiles on his machine, shown by the receipt.
