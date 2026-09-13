# half_a — Heimdall (deepseek): The Arsenal as a single typed pipeline language over a time spine

## VERDICTS

V1. [CERTAIN] There is exactly one canonical clock — pipeline time as a rational second (`(num,den)` or `fractions.Fraction`) — and every other clock (frame index, audio sample, device clock, vsync, musical time, editing timeline) is a *derived* or *mapped* function of that spine, never a peer of it. This is the single non-negotiable foundation of the whole arsenal.

V2. [CERTAIN] Pixels must carry their truth: `Frame`/`Resource` types include color space, transfer, and alpha mode, so a BT.709 frame cannot reach a BT.2020 port without an explicit, logged conversion. This is the pixel-level form of LEXICON discipline and it closes the chroma-blindness the VFX synthesis already found.

V3. [CERTAIN] GPU memory is a first-class, *opaque* `Resource` token that stays on the device; reading it is a separate explicit `copy` verb. This is the only way hardware decode → shader → screen stays zero-copy, and it is what makes this an arsenal rather than a set of PNG files.

V4. [CERTAIN] One GPU context, process-isolated, measured — never multiplied. The AMD TDR history makes N-live-contexts a trap (the prior fence already concluded this), so the renderer is a single context media modules submit to, and it lives alone in its own process so a TDR crash is a restart, not a cascade.

V5. [CERTAIN] The editor is the one genuinely build-from-scratch piece: it is a *view over a `Sequence`/editing ledger we own*, not a separate program, so cut/slice/re-order and "drag gifs in" and "bot playback" all reduce to graph mutations, not to a timeline in another product.

V6. [CERTAIN] One control model unifies MIDI, automation, audio-analysis and the Bifrost bus/Discord: every controllable quantity is a named `Signal` port, and the single verb `map <target> = <producer>` wires any producer (midi/automation/audio/bus) to any parameter. This is the "one instrument" feel Daniel wants.

V7. [DESIGN] Existing engines: mpv/libmpv (hardware decode, render-API, highest-stability decode), FFmpeg/libav* (format boundary and transcoding), yt-dlp (network fetch), WebGL2-or-WebGPU through the existing VFX bench (rendering), numpy-Fourier + mido (analysis + MIDI), ComfyUI/UVR/StemRoller as supervised sibling *processes*, not in-process modules. Three.js only for 3D scene-graph cases on top of the same single context.

V8. [DESIGN] The pipeline language is a tiny declarative dataflow syntax (`node -> port`, `node -[port]-> node`, `map`, `splice`, `take`), one language with two editors (drag-drop for Daniel, text for agents), AST-serialized to JSON so a pipeline *is* a `Graph` token. Formats are NOT first-class — they are registry entries at the boundary.

V9. [DESIGN] The licence shape is Apache-2.0 core with LGPL engines (libmpv, FFmpeg-LGPL build) isolated behind a process/ABI boundary so the viral parts cannot touch the core, MIT leaf modules (mido, three.js), Unlicense (yt-dlp), all recorded per-module in each manifest.

V10. [DESIGN] Python is the conductor (parser, graph, registry, bus, supervisor); GLSL and WASM are the two sandboxed extension languages for hot loops; Rust is the eventual but not-first home for the spine/graph core. First pipeline ships in Python for velocity.

V11. [INFERRED] Anything touching the AMD TDR path is measured by the FPS watchdog and its verdict governs, not assumed — stability is a property of this machine, not of the API choice.

V12. [UNCERTAIN] Whether libmpv's render-API can hand frames into a *browser-hosted* WebGL context zero-copy, and whether WebGL2 or WebGPU is the right substrate on this Windows/AMD driver. The fallback — a native D3D11 present window behind the same `present` port — is designed to make the swap invisible if the browser round-trip fails.

---

## 0. The one sentence

**An arsenal is not a pile of plugins with a bus — it is a single *pipeline language* whose verbs are typed ports, whose noun is *time*, and whose sentences are dataflow graphs.** Everything else — mpv, ffmpeg, WebGL, MIDI, the bus, "bot playback," drag-drop — is a *binding* to that language, not a peer of it. Build the language first; make every engine a dialect of it; the freedom Daniel wants falls out of the unified type/syntax, not out of plugin breadth.

This is the exact inverse of the instinct to "tie things together" by wiring N programs to M formats. The VFX bench already proved the lesson in miniature: it renders states beautifully and cannot represent *change*, because it has objects (nodes, snapshots) and no *time model*. An arsenal without one time model is the same disease at twice the scale — it would give Daniel a hundred tools that each have their own clock and none of them can talk to each other about *when*.

---

## 1. The time spine (the thing I will defend to the end)

There is exactly **one canonical clock**, and everything else is a *derived* or *mapped* time.

### 1.1 One clock: pipeline time, in rational seconds

`t` is a **rational number of seconds** measured in the media timeline's own units — not wall-clock, not frames, not samples, not ticks. Rational, because a frame at 23.976 fps is 1001/24000 s and floating point will smear it across a ten-minute take; the VFX bench's `uniform float u_time` is already a lie-in-waiting on this exact axis ([CERTAIN] — float64 is not exact for sums of 1001/24000 over 10 minutes; the drift is real and cumulative once you SPLICE two takes).

Concretely, the canonical type is a pair `(num: i64, den: i64)`, normalized, or at minimum a `Fraction` (Python `fractions.Fraction` — already in stdlib, already exact, already ordered). `u_time` in any shader is a *rendering* of this spine, not the spine.

### 1.2 Every other clock is a function *of* the spine

| clock | relation to spine | who maps it |
|---|---|---|
| media time | **is** the spine (source of truth when playing) | decoder |
| frame index N | `N = floor(t / frame_dur)` for fixed rate; `N = the keyframe ≤ t` for VFR | decoder — this is why frame is derived, never primary |
| audio sample S | `S = t * sample_rate` (rational product, exact) | audio device |
| sample ≈ device clock drift | a *measured* offset `d(t)`, resampled, never trusted, always locked | audio driver / a PLL-style drift estimator |
| display vsync `v` | `v = t * refresh`; latency-compensated, frame-paced | presenter |
| musical time | bar/beat/tick: `beat = t * BPM/60`, mapped through a tempo *map* (piecewise, not a single BPM) | MIDI / time-map module |
| editing timeline | an **offset + rate** transform (`t' = a*t + b`) onto the spine | editor |

Why this matters for Daniel's exact wish list: "audio responsive visuals" is *not* audio→FFT→parameter. It is **beat-time mapped onto the spine** so a shader's `u_time` and a kick drum and a MIDI note all agree on *the same second*. "MIDI to drive visualization" is the same spine. "Cut, slice, re-order" is the editor *corrupting the spine with a splice map* (below). All of it is one clock. That is the freedom he's asking for: connect anything to anything *because they already agree on when*.

### 1.3 What a module must expose about time (`[DESIGN]`)

Every module declares, in its manifest:
- `time_domain`: `spine` (it reads/writes the canonical clock) or `derived` (it has an internal clock that must be *anchored* via a mapping).
- If `derived`: the mapping rule (frame index → `floor`; device clock → measured offset; etc.).

A module that says `derived` and cannot state its mapping is **not a media module yet** — it's a black box with a stopwatch, and the arsenal refuses to splice it. This is the single most important admission test.

---

## 2. The type system: what flows between modules

### 2.1 Tokens, not bytes. Ports, not strings.

Flows are typed **tokens** on **typed ports**. This is the VFX bench's typed-port graph (`graph: {nodes[{id,chunk,portTypes}], edges[{from,fromPort,to,toPort,type}]}`) generalized from shader chunks to every media object. A port has a name and a type; a connect compiles or it refuses. Daniel drag-drops; the graph refuses nonsense at connect-time, which is exactly what makes drag-drop safe for him — the bench already proved this is the right shape for a non-programmer.

Core token types (a deliberately small, closed set):

```
Time           — (num,den) rational second; the spine
Frame          — an image + its timestamp + its pixel/color format + its origin (SRGB? BT.709? premultiplied alpha?)
AudioBuf       — interleaved or planar samples + rate + channel layout + a timestamp
Signal         — a named, typed scalar/small-vector parameter (uniform), live (per-frame)
Spectrum       — FFT bins + window + hop + rate + timestamp (so it can't be consumed stale)
MIDI           — a timestamped message stream (note/CC/pitch-bend/program), over the spine
Sequence       — an ordered list of tokens by timestamp (an edit decision list = a Sequence of Frame refs)
Graph           — a subgraph (a module's *definition*)
Clip           — a source reference (uri + in/out on the spine) — the *pointer*, not the pixels
Resource       — a GPU handle (texture/buffer) that cannot leave the device without an explicit copy
```

Two rules make this carry the whole design:

**R1 — pixels always carry their truth.** A `Frame`'s type includes `color_space`, `transfer`, and `alpha_mode`. The VFX bench currently has *no* color/transfer information on a render, and the §4a chroma-blindness in the synthesis doc is the same hole one level up: metrics that cannot see hue. Put color truth in the type and the "name that lies" problem for pixels *cannot arise*, because a `Frame` that is BT.709 cannot be handed to a port that wants BT.2020 without an explicit, logged conversion. `[CERTAIN]` — this is the single highest-leverage type decision; it is the pixel equivalent of LEXICON discipline ("a preview must know when it is lying").

**R2 — GPU memory is a first-class `Resource`, and it is *opaque*.** A `Resource` token is a handle that stays on the device; it has a device id and a format but no host memory. Passing it between modules is a zero-copy pointer. Asking for its pixels is a *separate, explicit* `copy` verb that yields a `Frame`. This is the only way "hardware-accelerated decode → shader → screen" never round-trips through the CPU, and it is the thing that makes this *an arsenal and not a set of PNG files*. The existing bench already models renders as opaque job results; `Resource` is that observation made a type.

### 2.2 The pipeline language (the contract's surface)

Pipelines are **dataflow graphs written in a tiny declarative syntax**. Same syntax for Daniel (via drag-drop that renders *to* this text) and for agents (who write this text directly). One language, two editors — this is the bench's `script.steps[]` (`{do: node|link|set|...}`) made textual and made the *primary* surface rather than a secondary CLI.

```text
# a "play this and hue-shift it live with the kick drum" pipeline

clip "hero.mp4"          -> dec
dec                     -[video]-> gpu_tex        # dec = libmpv hw decode, emits Resource
dec                     -[audio]-> fft
fft                     -[bins]-> beat             # beat = onset/energy module
beat                    -[energy]-> shift.amount   # live Signal (per-frame)
gpu_tex                 -> shift.in                # shift = a shader (WebGL2/glsl)
midi "song.mid"         -> midi_out                # MIDI mapped onto the SAME spine
midi_out                -[cc74]-> shift.hue        # CC 74 drives hue, on the spine
shift.out               -> present                 # present = swapchain/display
```

Everything is `node -> port` or `node -[port]-> node`. The *only* nouns are the node names from `node ...` declarations and the ports they declare. There are three sentence kinds:

- **declarations** — name a source and its binding: `clip "x"`, `midi "y.mid"`, `node "name" = shader:{...}`.
- **connections** — typed edges, compile-checked.
- **control** — `param name = value` (static) and live `Signal` flows (dynamic), where the *same* syntax means "wire this parameter" regardless of whether the wire carries a MIDI CC, an automation lane, a beat detector, or the bus.

Three verbs that make it an *editing/arsenal* tool rather than a renderer:

- `splice a b at t` — compose two clips on the spine (this is "cut/slice/re-order" reduced to a time-map operation; a splice is literally `t' = piecewise(t)`).
- `map node.param = signal` — bind a live signal (MIDI/audio/automation/bus) to any scalar param; the *same* verb for every control source, which is the whole "unified control" ask.
- `take N` — a named snapshot of a subgraph's state; the take strip from the VFX plan (S2), but now a *first-class pipeline object* rather than a UI-only memory.

`[DESIGN]` — the language is versioned and parseable, AST-serialized to JSON, so a pipeline *is* a `Graph` token and can itself be a port value (graphs-of-graphs, for the "modules and plugins we connect and deploy at will" line).

### 2.3 Format registry — where "unified types/syntax" ends

One place deliberately does NOT unify: actual media **formats** (mp4, flac, gif, midi, glsl). These are *dialects spoken at the boundary*, not first-class citizens. There is a **format registry**: a declarative map from `{mime/ext} → {decoder module, emitted token type, capabilities}`. NEW format = add a line to the registry, point at a decoder; the pipeline language never changes. This is how the arsenal stays a *suite* — decoders come and go, the language doesn't.

---

## 3. What plugs in — engines, chosen by stability-first on AMD

Daniel: "3js or any 3d renderer... should be used if its the best, most stable and most reliable." Stability is *measured on this machine*, not assumed. The brief documents TDR history. So the rule I adopt: **one GPU context, measured, never multiplied.** The VFX synthesis already named N-live-WebGL-contexts a trap on this host; the arsenal must inherit that verdict as a hard constraint: the renderer is a *single* context that media modules submit to, never a pile of per-module contexts.

### Decode/playback → **mpv via libmpv** `[DESIGN, cite mpv ≥ 0.37 — current stable 2024; check at build]`

- mpv *is* hardware-accelerated decode (DXVA2/D3D11VA on Windows, on the AMD GPU), has a single `libmpv` C API with a render-API mode that hands you frames *without* pulling them to CPU, and is the canonical "media player based on mpv." Daniel literally asked for it by name. It is the highest-stability choice for decode because it is one battle-tested engine doing exactly this, not a pile we assemble.
- The render-API mode is the key: `mpv_render_context` renders *into* an existing GPU context (D3D11 or OpenGL) via `MPV_RENDER_PARAM_*`. We give it our single WebGL/GL context's underlying D3D11 device and it lands decoded frames as `Resource` tokens — zero copy. That is the "known unified API" for decode he asked for.
- mpv already handles VFR, subtitles, chapters, audio resampling, seeking — the whole "clock" headache is *solved inside one engine* and we map its result onto our spine, rather than reimplementing.

### Transcode/mux/format surgery → **FFmpeg's libav\*** `[DESIGN, cite FFmpeg ≥ 7.x]`

- FFmpeg is the universal *format* boundary. Use it for anything that crosses formats (gif→video, concat, remux, audio-only extract, "yt download" is a network fetch feeding a demuxer), and nothing that touches live playback. Its output feeds the same `Frame`/`AudioBuf` token types; it just never pretends to be real-time.
- "yt download": yt-dlp (the maintained fork of youtube-dl) as the *fetch* binding, output piped into the FFmpeg demuxer. One module, two well-known tools. `[DESIGN]`

### Render/presentation → **WebGL2 (or WebGPU) through the existing VFX bench**, extended `[CERTAIN on WebGL2; DESIGN on WebGPU]`

- Daniel said WebGL is "just one type of render," and we should use 3js or any 3D renderer if best. My read: the renderer surface is the *existing* `vfx.html` WebGL2 page generalized to accept `Resource` inputs — because it already has typed shader graphs, chunk headers, Shadertoy ingest, a render feed, and a CLI, and it already runs on his machine. Three.js is a scene-graph *library ON TOP OF* WebGL — adopt it **only for the 3D scene-graph cases** (3D geometry, cameras, post stacks) where hand-rolling is silly; keep raw WebGL2 for the 2D/effect shaders where the bench already shines. Both are dialects of the *same* single GPU context, so the "no 3js" rule dissolves without the "N contexts" hazard. `[DESIGN]`
- WebGPU (via the browser, or via wgpu) is the honest *target*, not the start: it is the most stable modern API but on Windows+AMD some browsers still ship it behind flags and driver maturity varies. Ship WebGL2 first (it is already here and already measured), design the renderer's *port* types (`Resource`, `present`) to be API-agnostic so WebGPU is a drop-in behind them later. `[INFERRED]`

### Audio → **libmpv/FFmpeg for decode; a small in-process engine for routing; PortAudio only if we need many simultaneous device I/O** `[DESIGN]`

- Playback and analysis (FFT/onset) is what drives "audio responsive visuals." The FFT is a *module* emitting `Spectrum` tokens. Do NOT build an audio engine — mpv/FFmpeg decode, a small ring-buffer + resampler + FFT (numpy already installed, per the synthesis doc's §4a) is the analysis chain. PortAudio only when Daniel wants live multi-device routing.

### MIDI → **the Windows MIDI Service he already has running** (MIDI 2.0 stack) `[CERTAIN on availability, DESIGN on path]`

- The brief confirms the Windows MIDI Service is installed and running, and FL Studio is the source. The clean path is mido (Python, pure, speaks raw MIDI) as the *wire format* on top of the OS layer, with timestamps mapped onto our spine's musical time (bar/beat from BPM/tempo map). "MIDI to drive visualization" = a `MIDI` token stream → a `Signal` flow → any shader param, on the spine. mido is the least-dependency, most-portable way to go from his existing MIDI devices/FL Studio into the graph; the hard part (tempo map onto rational time) is ours, not the library's.

### Editing timeline → **build from scratch** `[CERTAIN]`

- The editor is the one thing genuinely not off-the-shelf, because what's off-the-shelf (Premiere/Resolve) is a *product*, not a *graph node*. We need the edit decision list (EDL = a `Sequence` token of clip refs + splices) to be a *live, scriptable, agent-commandable* object on the spine — so "cut slice re-order" and "drag gifs in" and "bot play back" all reduce to graph mutations, not to a timeline in some other program. This is the VFX plan S1–S2 (ledger/ledger-view) generalized to *time*: the take strip = a view of an editing ledger = a `Sequence`. The editor is a *view* over a data structure, and that data structure is ours to own.

### AI/effects (ComfyUI, stem separation) → **sibling processes, not in-process modules** `[DESIGN]`

- ComfyUI (AI image/video gen) and UVR/StemRoller are heavyweight, expensive, and already installed as tools. They are *modules* in the sense of "a manifest + a process binding + emitted token types (an image, a stem as an `AudioBuf`)," addressed over a local command/HTTP interface — NOT imported into our process. The "deploy at will" freedom is preserved because they're registry entries; the stability is preserved because they crash in their own process, not ours. `[DESIGN]`

---

## 4. Isolation and deployment (the "deploy at will" mechanism)

Two tiers, and the boundary is *where failure can take down the GPU*:

- **In-process modules** — pure data transforms (FFT, time-map, splice, MIDI decode, format registry lookups). They cannot crash the arsenal; they're just functions. Loaded as ordinary Python/Bevy/Wasm units.
- **Process modules** — anything that owns a device or a heavyweight runtime: decoder (libmpv), transcoder (FFmpeg), ComfyUI, stem separation, and — critically — the **renderer** (the single GPU context). Each is a subprocess with a typed command/manifest, supervised, restartable. A TDR crash kills the renderer process, never the graph. `[CERTAIN]` — this is the AMD-mandated architecture: the GPU context lives alone so its failure is a restart, not a cascade.
- **Discovery** — each module ships a `manifest.json`: name, emitted/token types, ports, `moduletype: inproc|process`, time-domain, capabilities, licence, version. A registry (filesystem dir + one JSON index) is scanned at boot. NEW plugin = drop a directory in `arsenal/modules/<name>/` with a manifest; it appears as a node in the palette. That is "the arsenal." `[CERTAIN]`
- **Deployment = composition** — "connect and deploy at will" is not installing software; it is a pipeline graph whose nodes are registry entries. A "deployed media player" is a saved pipeline (`clip → dec → present` + a control surface). A "bot playback" is the same pipeline driven by the bus. Deployment is *naming a graph*, nothing heavier.

---

## 5. Control reaching the modules (Daniel's "bot playback + MIDI")

One control model, `[CERTAIN]` on shape:

Every controllable quantity is a **named `Signal`** (a port of type `Signal`). Signals carry `(name, type, timestamp-on-spine, value)`. Three producers, one consumer model:

1. **MIDI** — a `midi` node turns a device into `Signal` flows (`cc74`, `note`, `pitch`).
2. **Automation** — recorded/scripted `Signal` tracks on the editing spine (the "cut/slice" timeline's automation lanes).
3. **The bus** — the Bifrost bus (and Discord) drives signals the same way: a bus message *is* a control move. "Bot play back media" = an agent sends `set transport.rate = 1` or `load clip "x"` as a bus message that compiles to a graph mutation, exactly like a MIDI CC compiles to a signal. Same verb, different producer.

The one verb that unifies them: **`map <target> = <producer>`**, where `<producer>` is midi/automation/bus/audio. This is what makes the arsenal feel like *one instrument* — a MIDI knob and an agent command and a beat detector all twist the same dial through the same port. `[CERTAIN]` this is the heart of the design.

---

## 6. The licence answer (kept short but decided)

`[CERTAIN]` — the arsenal is **ours**, Apache-2.0 (the house licence), same as `E:\AI-Setup`. But its *dependencies* live under a spectrum we must respect in the manifest: every module's `manifest.json` carries a `licence` field honouring the real terms. mpv is **GPL-2.0+ (LGPL for libmpv)** — embedding libmpv is LGPL-compatible (dynamic link, no viral spread to our pipeline core) — this is the single most important licence fact in the whole design and it *strengthens* the "keep engines out-of-process" decision: the GPL parts stay behind a process/ABI boundary and cannot contaminate the Apache core. FFmpeg is **LGPL/GPL depending on build flags** — use the LGPL build, same reasoning. Three.js is **MIT**, WebGL/WebGPU are **platforms**, mido is **MIT**, yt-dlp is **Unlicense**. So: Apache-2.0 core, LGPL-engines isolated by process boundary, MIT leaf modules, and the manifest records it per module. `[DESIGN]` on exact flag choices — but the *rule* (GPL stays behind a process wall, Apache core clean) is CERTAIN.

---

## 7. Language(s) to build in

`[DESIGN]` — **Python as the conductor, a compiled/sandboxed language only where a transform is hot.**

- **Python** orchestrates: the pipeline language's parser/interpreter, the graph, the registry, the bus binding, the process supervisor. It is the house language, the bus is Python, the agents write Python/CLI, and numpy is already there for FFT.
- **Hot inner loops** (per-sample audio, per-frame pixel work) are the *only* place to reach for something else — and the reach is **WASM (or the existing GLSL) as a `process`/`inproc` module**, not a rewrite. The shader chunks are already GLSL; the renderer already compiles them. A user effect that must run at 60fps on the CPU without our blessing is a WASM module in the registry; one that runs on the GPU is a GLSL/WebGPU chunk. Two extension languages, both already-typed, both already-ported, both sandboxed.
- **Rust** is the right eventual home for the *spine and graph core* (exact rational time, lock-free graph execution, the process supervisor) if we ever need to leave Python for throughput — but **not first**. First pipeline ships in Python; it keeps the bus/agent story trivial and the velocity high, and the `t=(num,den)` and token types port verbatim. `[INFERRED]` — the choice to defer Rust is a velocity call, not a correctness one.

---

## 8. The first working pipeline (the "done looks like" bar)

`[CERTAIN]` — it must exercise the *spine, the types, the language, the renderer, and one control source*, all at once, or it isn't proof of the contract. It must also be something Daniel *loves using* on day one, because that's his stated success criterion.

**First pipeline: "play a video, and make it pulse to its own beat — then twist it with a MIDI knob."**

```
clip "hero.mp4"        -> dec              # libmpv hw-decode → Resource (zero-copy)
dec -[video]-> pulse.in                    # pulse = a GLSL effect chunk (existing bench format)
dec -[audio]-> fft                          # numpy FFT → Spectrum
fft -[bins]-> beat                          # onset/energy → Signal (on the spine)
beat -[energy]-> pulse.amount               # the shader's uniform, driven live
midi "FL Studio"      -> ctl               # his running MIDI stack / FL Studio
ctl -[cc74]-> pulse.hue                     # knob twists hue, on the SAME spine
pulse.out            -> present             # present = the swapchain (vfx.html tab)
```

Why *this* one:
- It is the *single hardest integration* done first — hardware decode **to** GPU shader **with** live audio analysis **and** live MIDI control, all on one clock — so if the contract survives this, it survives anything. (Do the hard splice last, not first: "cut/slice/re-order" is an edit of the spine *after* the spine is proven to carry one stream correctly.) `[CERTAIN]`
- It is beautiful to watch, which is the actual requirement.
- It exercises every core token type I named: `Resource` (decode→shader), `Frame` (implicit at present), `AudioBuf`→`Spectrum`→`Signal`, `MIDI`, and the `map`/`-[]->` verbs. Only `Sequence`/splice and `copy` wait for pipeline two.

Acceptance for pipeline one (pre-registered, in the method's spirit): a 600s clip plays at 60fps with decode and shader both on the AMD GPU (measured, FPS watchdog read not vibed, exactly as the VFX plan demanded), the shader pulse is audibly locked to the kick (not drifting over the full 10 minutes — that's the rational-time test), and MIDI CC 74 repaints live without a dropped frame. The TDR hazard is *read* (the watchdog), and its verdict governs, not assumed away. `[CERTAIN]` on the *bar*; DESIGN on hitting it first try.

---

## 9. What I am deliberately NOT doing (and why)

- **Not** building an audio engine (mpv/FFmpeg + numpy FFT is enough; PortAudio only on demand).
- **Not** multiplying GPU contexts (TDR history makes that a trap; one context, process-isolated).
- **Not** unifying *formats* — only *types* and *time*. Formats stay at the registry boundary.
- **Not** writing the editor as a separate program (it is a view over a `Sequence`/ledger we already own).
- **Not** starting in Rust (velocity; ports losslessly).
- **Not** importing the VFX bench's *memory architecture* (recall/lessons) — only its *typed-port and shader-chunk* discipline, because the synthesis already showed recall is the wrong shape for a visual instrument; the arsenal's memory is the *take strip over a time ledger*, which is a `Sequence`, not a search index. `[CERTAIN]` — this is the one place I lean on the prior fence's own finding, and it is the correct lean.

---

## 10. The one risk I'm least certain about, named

`[UNCERTAIN]` — **WebGL2 vs WebGPU as the renderer's actual substrate on this AMD/Windows driver**, and **whether libmpv's render-API can hand frames into a *browser*-hosted WebGL context at all** without a copy. libmpv's `mpv_render_context` targets D3D11/OpenGL, not WebGL — zero-copy into a browser tab is *not* guaranteed; it may force a PBO/readback that costs the very thing we're avoiding. Two honest unknowns, and both land exactly where the first pipeline's acceptance test lives. If zero-copy into the tab fails, the fallback is a *native* present window (a small window, D3D11, that the same pipeline drives) rather than the browser tab — and the contract's `present` port is designed to make that swap invisible. I flag this up front because it is the kind of thing the VFX §4a probe taught us to name *before* shipping a confident answer. `[DESIGN]` the fallback; `[UNCERTAIN]` the browser-round-trip.

---

*— Heimdall (deepseek), half_a, filed blind per the brief's independence rule. Half_b (Navi) and voice (Sunshine) read this only at reconciliation.*
