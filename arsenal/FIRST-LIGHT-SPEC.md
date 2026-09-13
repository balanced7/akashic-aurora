# First Light — build spec (arsenal v0.1)

Ledger: T399 contract v0, approved by Daniel on 2026-09-13 ("I love it … What do we build first?"). The go for this build, verbatim: "Please build it ^__^! You can do whatever you need in parallel as well".
Contract: `fences/media-arsenal-contract/reconciliation.md`. Page: https://claude.ai/code/artifact/7dd63ddb-3575-4a58-b497-d2df89a4bd92

## What First Light is

Daniel drags a clip from his library onto a page. It plays through a VFX effect, pulses with the clip's own audio, and a knob on his **Arturia KeyLab 88 mk3** turns the hue. Every run is recorded as a take.

The build runs through the contract's narrow waist: exact time with epochs, a typed graph with connect-time checks, `map` bindings, a loud `plan`, and a take ledger.

**Zero downloads.**
- Chrome's own hardware decoder (Radeon RX 9070 XT) plays the video.
- WebGL2 renders.
- Web MIDI reads the KeyLab.
- FFmpeg (bundled in PyAV 17.0.0, libavcodec 62.11.100) analyses the audio offline, producing timestamped features.
- Python 3.11 with the stdlib, numpy and av is already installed.

GStreamer takes over decode only when Lane B earns it by receipt.

## Hard rules for every file

- Never open a page that uses WebGL inside the Claude app's built-in browser pane (it crashed the app on 2026-08-12). Test pages in Chrome.
- The server binds `127.0.0.1` only. Media access is restricted to the configured library roots. No path traversal.
- Exact time never passes through bare floats in Python. Browser media times are doubles by nature, so round them to ticks at an explicit timebase and say so.
- House conventions: Python 3.11, tests at `tests/test_arsenal_*.py`, no new dependencies, and state under `state/arsenal/`.
- Shaders: GLSL ES 3.00, `precision highp float;`, constant loop bounds, compile checked before use.

## Layout

```
arsenal/
  __init__.py          __main__.py (CLI)
  timebase.py          exact time, clocks, epochs, clock maps          [Vandor]
  mediatypes.py        port types, memory domains, caps checks          [Vandor]
  registry.py          module manifests                                [Vandor]
  graph.py             arsenal.graph/v0 load, validate, text form      [Vandor]
  plan.py              loud plan                                       [Vandor]
  take.py              take ledger                                     [Vandor]
  serve.py             local HTTP server (routes below)                [Vandor]
  analysis.py          PyAV probe, hw-decode evidence, audio features  [analysis agent]
  modules/*.json       built-in manifests                              [Vandor]
  graphs/first-light.json                                              [Vandor]
  web/first-light.html, first-light.js, first-light.css                [page agent]
  web/shaders/first-light.frag, first-light.meta.json                  [Navi]
  lanes/hwdecode_soak.py   Lane B.0 receipt                            [analysis agent]
tests/test_arsenal_*.py  unit tests by each author; tests/test_arsenal_pins_heimdall.py = blind pins [Heimdall]
state/arsenal/{takes,cache,receipts}/   runtime state (git-ignored)
```

## Kernel API v0 (Python)

### arsenal.timebase

- `class ClockMismatch(ValueError)`, `class StaleEpoch(ValueError)`
- `tb(num, den) -> Fraction` (seconds per tick, so `0 < tb <= 1`; a zero denominator raises `ValueError`); `parse_tb("1001/30000") -> Fraction`; `format_tb(Fraction) -> "num/den"`
- `@dataclass(frozen=True) TimeRef(clock: str, epoch: int, ticks: int, timebase: Fraction)`
  - `ticks` must be an `int`: `bool` or `float` raises `TypeError`. `timebase` accepts an `int` or a `Fraction` > 0; a `float` raises `TypeError`.
  - A timebase above 1 second per tick raises `ValueError`, and the message names the inverse (for example `tb(1, 48000)`). Nothing in media ticks slower than once a second, so such a value is a rate passed by mistake.
  - `.seconds -> Fraction`
  - `.rescale(timebase, *, exact=True) -> TimeRef`. With `exact=True`, raises `ValueError` if the value is not exactly representable; with `exact=False`, rounds half to even.
  - `<, <=, >, >=, ==` against another `TimeRef` only:
    - a different clock raises `ClockMismatch`
    - a different epoch raises `StaleEpoch`
    - a non-`TimeRef` operand raises `TypeError` (`==` returns `False` for a non-`TimeRef`)
    - two refs on the same clock and epoch compare by exact seconds, even when their timebases differ
  - `TimeRef + int` → `TimeRef` with ticks added. `TimeRef + TimeRef` raises `TypeError`.
  - `.to_json() -> {"clock","epoch","ticks","timebase":"num/den"}`; `TimeRef.from_json(d)`
- `@dataclass(frozen=True) TimeSpan(start: TimeRef, duration_ticks: int)`
  - `.end -> TimeRef`
  - `.contains(ref) -> bool`: start-inclusive, end-exclusive; same clock and epoch rules as comparisons
- `class Clock(name: str, domain: str)`
  - `domain` is one of `media, audio, presentation, virtual, timeline, musical`
  - `.epoch` starts at 0
  - `.bump_epoch(reason) -> int` returns the new epoch; `.history -> list[tuple[int, str]]`
  - `.stamp(ticks, timebase) -> TimeRef` at the current epoch
  - `.is_current(ref) -> bool` is true only for this clock's name and current epoch
- `@dataclass(frozen=True) ClockMap(source: str, target: str, slope: Fraction, offset: Fraction, uncertainty_ns: int, observed_at: str)`
  - `.map_seconds(ref) -> Fraction` computes `slope * ref.seconds + offset`; `ref.clock != source` raises `ClockMismatch`
- `MASTER_BY_MODE = {"live_audio": "audio", "live_silent": "presentation", "offline": "virtual", "edit": "timeline"}`

### arsenal.mediatypes

- `PORT_TYPES`: `stream.video, stream.audio, media.video_frame, media.audio_block, media.encoded_packet, media.subtitle_cue, control.event, control.curve, analysis.features, asset.reference, timeline.sequence`
- `MEDIA_PORT_TYPES`: the `stream.*` and `media.*` subset
- `MEMORY_DOMAINS`: `cpu, d3d11, d3d12, vulkan, opengl, webgl, webgpu, browser, encoded`
- `check_caps(out_caps: dict, in_caps: dict) -> list[str]` returns reasons; an empty list means compatible.
  - Only keys present in `in_caps` are checked.
  - An input value of `"any"` accepts anything.
  - An output that lacks a key the input requires counts as a mismatch ("unknown").
  - Keys: `memory, primaries, transfer, matrix, range, alpha_mode, sample_rate, channels, layout`.

### arsenal.registry

- `load_registry(dirs=None) -> Registry`. The default is `arsenal/modules/`. It reads `*.json` manifests.
- `Registry.get(id)` returns the manifest or raises `KeyError`; `Registry.ids()` returns them sorted.
- Manifest v0 fields:
  - `id`, `version`, `protocol: "arsenal.module/v0"`, `engine` (`arsenal|browser|ffmpeg|gstreamer|mpv|external`)
  - `inputs[{port,type,caps?}]`, `outputs[{port,type,caps?}]`, `params[{name,unit,range:[lo,hi]}]`
  - `isolation`, `licence` (an SPDX expression, `NOASSERTION`, or a `LicenseRef-*`), `latency_ms: {base}`
  - `degradation: {on_failure}`, `receipts: []`, optional `notes`

### arsenal.graph

- `class GraphError(ValueError)`, with `.problems: list[str]`
- `load_graph(obj) -> Graph`; `api` must equal `"arsenal.graph/v0"`.
- Graph JSON:
  ```
  {"api","name","mode",
   "assets":{name:{uri}},
   "nodes":{name:{use, with?}},
   "edges":[["a.port","b.port"],...],
   "bindings":[{from,to,range,smooth?:{attack_ms,release_ms},precedence?:int,learn?:bool}]}
  ```
- `Graph.validate(registry) -> list[str]`. Each problem is human-readable and names the offending node or port. It reports:
  - an unknown module
  - an unknown node or port in an edge
  - a wrong edge direction (must be output → input)
  - a type mismatch
  - a caps mismatch (via `check_caps`)
  - an input connected more than once
  - a binding target that is not a declared param
  - a binding source that is not a `control.event`, `control.curve` or `analysis.features` output. A feature suffix is allowed: `node.port.feature`.
  - a binding range outside the param's declared range
  - a malformed binding option: `smooth` not whole milliseconds, `precedence` not an int, or `learn` not a bool
  - The wording names the kind of problem, for example "wrong direction" or "type mismatch".
- `Graph.require_valid(registry)` raises `GraphError`.
- `parse_text(src) -> dict` (graph JSON). One statement per line; `#` starts a comment.
  - `mode <name>`
  - `node <name> = <module.id>`
  - `<a>.<port> -> <b>.<port>`
  - `<a> | <b> | <c>` connects each node's first output to the next node's first input of the same type, and raises `GraphError` if there is none.
  - `map <node>.<port>[.<feature>] -> <node>.<param> {range: lo..hi, smooth: 20ms, precedence: n, learn: true}`
    - `smooth: 20ms` becomes `{"attack_ms": 20, "release_ms": 20}`, and `smooth: 12ms/180ms` sets attack and release separately. The JSON form is typed and never keeps the raw `"20ms"` string.
    - `precedence` is an int and defaults to 0. The text form always writes it; a JSON binding may omit it, which means 0. When bindings share a target, the higher precedence wins, and a tie goes to the latest event.
    - `learn` is `true` or `false`.

### arsenal.plan

- `make_plan(graph, registry) -> dict` plans only a valid graph; otherwise it raises `GraphError`, which the server returns as 400. It returns these keys:
  - `nodes[{name,module,engine,isolation,licence}]`
  - `edges[{from,to,type,copy,note}]`: `copy` is true when a MEDIA port type crosses engines. Otherwise the note says `same engine` or `reference handoff`.
  - `bindings[{from,to,range}]`
  - `latency_ms`: the declared base latency summed along the longest path, labelled declared, not measured
  - `licence_profile`: `arsenal-gpl` if any licence is GPL-family copyleft (GPL or AGPL), otherwise `arsenal-core`. LGPL, when used dynamically, stays in `arsenal-core` (contract F8).
  - `warnings[]`: covers `NOASSERTION` licences (the warning text names `NOASSERTION`), unverified bundles, and every copy
- `render_plan(plan) -> str`

### arsenal.take

- `TakeLedger(root)`
  - `.open(graph_json, plan, meta) -> take_id`. The ID is `YYYYmmdd-HHMMSS-<8 hex of sha256(graph+meta)>`.
  - `.append(take_id, events) -> int`
  - `.close(take_id, summary)`
  - `.load(take_id) -> {"take", "events"}`
  - `.list() -> list[dict]`
- Events: every event needs `kind` and `t` (TimeRef JSON).
  - `t.epoch` is the source of truth for every event.
  - A `kind:"epoch"` event must have `t.epoch = latest + 1`. Its `epoch` field, when present, must agree.
  - Any event whose `t.epoch` is lower than the latest recorded epoch raises `StaleEpoch`. An event from a newer epoch that no epoch event announced raises `ValueError`. In both cases nothing from the batch is written.
- Files: `<root>/<take_id>/take.json` and `<root>/<take_id>/events.jsonl`, append-only. Writing to a closed take raises `ValueError`.

### Reconciled with Heimdall's blind pins (2026-09-13)

Heimdall wrote 70 pins from this spec without reading the kernel. On the first run 59 passed. Of the 11 failures:

- **The kernel changed for 3:**
  - `tb(1, 0)` now raises `ValueError` instead of `ZeroDivisionError`.
  - Problem messages now say "wrong direction" and "type mismatch".
- **The spec was settled for 3 ambiguities he flagged:**
  - `smooth` is typed JSON.
  - `t.epoch` is authoritative.
  - `precedence` is an int with a default of 0.
- **A new guard came from a pattern.** Three pins read a timebase as a rate: `tb(30000, 1001)`, an int timebase of 48000, and 30000 ticks at 1001/30000 taken as 1 s. A careful reader making that mistake three times is a design signal, so a timebase above 1 second per tick is now refused, with the inverse given as a hint.
- **The pins' own arithmetic or helpers were wrong in the rest:**
  - 1/3 s is exactly 16000 ticks at 1/48000.
  - `_graph_obj(nodes=...)` keeps default bindings to nodes the override removed.
  - A browser-memory output feeds a cpu-memory input.
  - An output with no caps feeds an input that requires memory. The spec calls that "unknown", which is a mismatch.

## Built-in modules (arsenal/modules)

| id | in | out | params | engine |
|---|---|---|---|---|
| `file.clip` | none | `media: asset.reference` | none | arsenal |
| `browser.decode` | `media: asset.reference` | `video: stream.video {memory: browser}` | none | browser |
| `ffmpeg.audio-features` | `media: asset.reference` | `features: analysis.features` | none | ffmpeg |
| `vfx.first-light-effect` | `video: stream.video {memory: browser}` | `video: stream.video {memory: webgl}` | `pulse ratio 0..1`, `hue deg 0..360`, `intensity ratio 0..1` | browser |
| `webmidi.input` | none | `cc: control.event` | none | browser |
| `browser.present` | `video: stream.video {memory: webgl}` | none | none | browser |

## Server (arsenal/serve.py): `py -m arsenal serve --port 8793`

- `GET /` redirects (302) to `/first-light`; `GET /first-light` serves the page.
- `GET /web/<path>` serves static files under `arsenal/web/`.
- `GET /api/health` returns `{"ok":true,"api":"arsenal.serve/v0","version"}`.
- `GET /api/library` returns `{"roots":[...],"clips":[{"id","name","path","size","mtime","ext"}]}`.
  - Default root: `E:\Video Output E`.
  - Extensions: mp4, mkv, mov, webm, m4v.
  - Sorted by mtime, newest first; at most 500.
  - `id` is the first 16 hex characters of sha1(abs path).
- `GET /api/media/<id>` streams the file with HTTP Range support (206).
- `GET /api/resolve?name=&size=` returns `{"clip":{...}}`, or 404 when the file is not in the library roots.
- `GET /api/probe/<id>` returns probe JSON.
- `GET /api/analysis/<id>` starts or polls a background job:
  - while running: `202 {"status":"computing","progress"}`
  - when finished: `200 {"status":"ready","features":{...}}`
  - on failure: `500 {"status":"error","error"}`
- `GET /api/graph/first-light` returns `arsenal/graphs/first-light.json`.
- `POST /api/plan` takes the graph JSON, either bare or wrapped as `{"graph"}`, and returns `{"plan","text"}`, or `400 {"problems":[...]}`.
- `POST /api/take/open` takes `{"graph","clip_id","meta"}` and returns `{"take_id"}`.
- `POST /api/take/<id>/events` takes `{"events":[...]}` and returns `{"accepted"}`, or `409 {"error"}` on a stale epoch.
- `POST /api/take/<id>/close` takes `{"summary"}`.
- `GET /api/takes` lists takes; `GET /api/take/<id>` returns one take with its events.

## analysis.py (PyAV)

- `probe(path) -> dict`:
  ```
  {"api":"arsenal.probe/v0","path","size","container",
   "duration":{"ticks","timebase"},
   "video":{index,codec,width,height,pix_fmt,rate:"num/den",timebase:"num/den",primaries,transfer,matrix,range}|null,
   "audio":{index,codec,rate,channels,layout,timebase}|null}
  ```
  Unknown colour fields are `null`, never guessed.
- `hw_decode_evidence(path, devices=("d3d12va","d3d11va"), frames=30) -> dict` returns:
  ```
  {"tried":[{"device","ok","frames","frame_format","error"}],"ok_device":str|null}
  ```
  The evidence is the hardware frame format reported by PyAV. It is never inferred.
- `audio_features(path, *, progress=None) -> dict`:
  ```
  {"api":"arsenal.features/v0","clock":"media","epoch":0,"timebase":"1/48000",
   "hop_ticks":480,"window_ticks":2048,"start_ticks":<first audio pts rescaled to 1/48000>,
   "names":["rms","bass","mid","high","flux"],
   "frames":[[5 floats rounded to 4 dp], ...],
   "normalization":"per-band p5..p99 of dB mapped to 0..1, clipped",
   "source":{path,size,mtime,audio_stream,sample_rate_in,channels_in},
   "computed_with":{"engine":"ffmpeg","binding":"PyAV <ver>","libavcodec":"<ver>"}}
  ```
  - Mono at 48 kHz via `av.AudioResampler`.
  - Hann window.
  - Bands: bass 20–150 Hz, mid 150–2000 Hz, high 2000–16000 Hz.
  - Flux: positive spectral flux.
  - Row `i` starts at `start_ticks + i*hop_ticks`.
  - Results are cached under `state/arsenal/cache/` keyed by path + size + mtime.
- `lanes/hwdecode_soak.py --path P --minutes N` decodes with the first working hardware device and records fps, errors and the frame format. It writes a receipt JSON to `state/arsenal/receipts/`.

## Page (arsenal/web): Chrome, WebGL2, no libraries

### Look

Keep the patch-bay identity Daniel loved.

**Light tokens:**

| token | value |
|---|---|
| `--ground` | `#EDEFF2` |
| `--panel` | `#F8F9FB` |
| `--ink` | `#15171B` |
| `--ink-2` | `#4B5360` |
| `--ink-3` | `#6B7380` |
| `--rule` | `#CBD1D8` |
| `--accent` | `#A35600` |
| `--audio` | `#0D716E` |
| `--control` | `#962C58` |

**Dark tokens:**

| token | value |
|---|---|
| `--ground` | `#0F1114` |
| `--panel` | `#171A1F` |
| `--ink` | `#E6E8EB` |
| `--ink-2` | `#A3ACB7` |
| `--ink-3` | `#7F8994` |
| `--rule` | `#2C323A` |
| `--accent` | `#F0A443` |
| `--audio` | `#4CC2BA` |
| `--control` | `#E47FA7` |

Dark is the default for a stage. Fonts: Archivo (variable width) and JetBrains Mono from Google Fonts, each with fallbacks.

**Layout:** a large 16:9 stage canvas on the left, and a collapsible rack on the right with these panels:
- Library, searchable
- Patch, showing the live chain with activity lights
- Map, showing live `map` statements, with a Learn button
- HUD:
  - epoch, and media time as ticks/timebase and seconds
  - decoder evidence
  - dropped/total frames
  - MIDI device and last CC
  - knob-to-screen latency, p50 and p95
  - take ID and event count
- Plan, showing `/api/plan` text

### Input

- Drag a video onto the stage, then call `/api/resolve` (name + size).
  - If the clip is found, load it with analysis.
  - If not, play it via an object URL, label it "analysis unavailable: outside library roots", and hold pulse at 0. This is a declared degradation.
- Clicking a library item loads that clip.

### Playback

- A hidden `<video>` whose `src` is `/api/media/<id>`, with its audio playing normally.
- Keys: Space toggles play/pause; L toggles loop; F toggles fullscreen; clicking the seek bar seeks.

### Render

- WebGL2, with a fullscreen triangle from `gl_VertexID`.
- Upload the video with `UNPACK_FLIP_Y_WEBGL = true`, so `v_uv (0,0)` is the video's bottom-left.
- Load `/web/shaders/first-light.frag`. If the fetch or compile fails, use a built-in effect (hue rotation plus pulse glow) and show the compile log in the HUD.
- Use `requestVideoFrameCallback`: upload and draw with `metadata.mediaTime`. Fall back to `requestAnimationFrame` with `currentTime`.
- Cap the device pixel ratio at 2.
- Watchdog: if 20 consecutive draws exceed twice the frame interval, halve the backing scale (minimum 0.5) and show it.
- On `webglcontextlost`: show the `<video>` directly as a bypass and emit `degraded`. On restore, rebuild, bump the epoch, and resume.

### Uniforms (the contract with the shader)

```
uniform sampler2D u_video;
uniform vec2  u_res;
uniform vec2  u_video_res;
uniform float u_time;       // media time, seconds
uniform float u_pulse;      // 0..1 (map from features)
uniform float u_hue;        // degrees 0..360 (map from MIDI)
uniform float u_intensity;  // 0..1 (default 0.8; second learnable knob)
uniform float u_bass, u_mid, u_high, u_flux;  // 0..1 at this frame
in vec2 v_uv; out vec4 outColor;
```

The shader letterboxes itself ("contain", black bars) using `u_res` and `u_video_res`.

### Analysis sampling

- `ticks = Math.round(mediaTime*48000)`
- `idx = floor((ticks - start_ticks)/hop_ticks)`, clamped
- Pulse is `0.65*bass + 0.35*flux`, smoothed with a 12 ms attack and 180 ms release.
- The smoothing state resets on every epoch bump.

### Epochs

Epochs are per clip, starting at 0. Bump on:
- `seeking`
- a loop restart (media time jumps backwards more than 0.5 s)
- WebGL restore

On each bump:
- Clear the smoothing state.
- Drop queued events from the old epoch.
- Send `{kind:"epoch", epoch, reason}` first.

A clip change opens a new take.

### MIDI

- Call `navigator.requestMIDIAccess()` from a "Connect MIDI" button.
- Prefer an input whose name contains "KeyLab"; otherwise use the first input.
- Learn: the next CC received binds to hue (0..360). A second Learn binds intensity (0..1).
- Show the mapping as `map midi.cc(<n>) -> fx.hue {range: 0..360}`.
- Persist mappings in `localStorage`, inside try/catch.

### Knob-to-screen latency

- When a CC arrives, record `event.timeStamp`.
- On the first video-frame callback after the uniform changes, record `metadata.expectedDisplayTime - timeStamp`.
- Keep the last 200 samples, and show p50 and p95.

### Hardware decode evidence

- `navigator.mediaCapabilities.decodingInfo` (`powerEfficient`)
- `video.getVideoPlaybackQuality()`

### Take

- On the first play of a clip, `POST /api/take/open` with the graph (clip asset filled in), `clip_id`, and meta (`userAgent`, `decodingInfo`, MIDI device).
- Every 500 ms, batch events: `epoch`, `play`, `pause`, `seek`, `midi {cc,value,param,mapped}`, `param {name,value}` (at most 10 Hz each), `degraded {reason}`.
- Every event's `t` is `{clock:"media", epoch, ticks: Math.round(mediaTime*90000), timebase:"1/90000"}`.
- On `pagehide` or a clip change, close the take with a summary: latency p50/p95, dropped/total frames, decoding evidence.
- Stretch: "Replay take" drives hue and intensity from a take's recorded MIDI events at their media times.

## First Light acceptance (from contract §5, Lane A steps 1–4)

1. A seek or loop bumps the epoch, and no smoothing state or event from an older epoch appears afterwards. The server refuses stale events with 409.
2. MIDI-to-visible p95 is measured and shown, with a target of under 30 ms.
3. A 30-minute run reports measured drift and alignment.
4. Hardware decode evidence is recorded in the take, from Chrome's `powerEfficient` plus `getVideoPlaybackQuality`, alongside the PyAV hardware frame format for the same clip.
5. The plan prints every engine crossing and every licence, and `NOASSERTION` shows up as a warning.
6. Every run leaves `take.json` and `events.jsonl` that can be loaded back.
7. With the shader missing or broken, the page still plays using its built-in effect and says so.
