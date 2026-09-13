[DESIGN]

# The Media Arsenal — a contract that lets media modules connect and deploy at will

**half_b — Navi (kimi). Blind reading: this brief, my own prior work on the WebGL2 bench, and durable first-hand knowledge. No other seat's answer was read. Web search was unavailable this session, so version citations are flagged [INFERRED] rather than fabricated.**

---

## 0. The frame

Daniel's three asks, in the order he said them, are **a player, an editor, and a synthesizer** — a Winamp, a Premiere, a Milkdrop. The temptation is to design an app with three tabs. That is the wrong frame, and the way he said it proves it:

> "I want to build up a whole **arsenal** of backend infrastructure and media plugins and modules that we can connect and **deploy at will**."

He did not ask for a player. He asked for a **way to assemble a player out of parts and then rip the parts out and reuse them.** "Arsenal" is the word. "At will" is the word. That is a *modular runtime*, not an application. Milkdrop is a plugin that happened to ship inside Winamp; what he loves is that the visualization could read the audio of whatever was playing — a *pipeline property*, not a feature of one binary.

So the contract is not "here are the modules"; it is "here are the **seams**, and here is the one language that crosses every seam." The modules are almost boring — mpv for decode, FFmpeg for everything, a renderer for presentation. The seams are the whole game.

One thing sharply, up front, load-bearing, carried verbatim if disagreed:

**I do not think this should be one process, and I do not think the hot path should be Python.** The house is Python-first; the contract, orchestrator, bus bridge, MIDI surface, recall glue — Python, fine. But decode, audio, render are not Python's job, and I would rather *orchestrate* a few small native souls over a typed pipe protocol than force them into one GIL and one crash domain (§8). If the reconciler's prior says "single process, Python all the way down," carry that.

---

## 1. One time model

Every real media suite dies on the same reef: **there are several clocks and people pretend there is one.**

Distinct times in his world:

1. **Media time** — position inside content. Files: rational sample/frame indices. Procedural (shader, synth): free-running monotonic `t`. **Can pause, seek, loop, run backward.** Not the wall clock.
2. **Audio-device time** — the DAC's "now." The only clock the ears run on; must be *continuous* (a discontinuity is a click). Monotonic, **cannot seek**.
3. **Display time** — vsync/swap. Here you *drop* frames rather than stretch (a dropped frame is mostly invisible; an audio pop is not).
4. **Musical time** — bars, beats, ticks. A *mapping* from transport position (bar.beat.tick / MIDI clock) to wall time; the mapping changes (tempo, swing, follow-the-flag). Drives MIDI viz and quantized editing.
5. **Editing-timeline time** — the composited "movie" time, a *function of media time*: clip starts, gaps, speed ramps, reverses. A position maps to (media, span, rate).

One law across all: **every clock is a monotonic count mapping to a common canonical timebase; nothing stores time as a bare float.** Canonical timebase = **one microsecond** as a **64-bit rational** (rational micros). Sub-microsecond precision is never needed (one 48 kHz sample ≈ 20.8 µs); the float pathology (precision decay past 2^53, then jitter) is why DAWs abandoned bare doubles long ago.

A **clock**:

```
Clock {
  id:       string            // "media:player0", "audio:default", "display:vfx0"
  domain:   enum {media, audio, display, musical, timeline}
  now:      rational          // canonical micros
  rate:     rational          // 1.0 realtime, 0.5 half, -1 reverse
  origin:   instant           // unix micros at which now == 0 (wall clocks)
  parent:   string | null     // the mapper that links it to canonical time
  can_seek: bool              // media/timeline yes; audio/display no; musical via transport
}
```

The key move: **clocks relate through *mappers*, not through a shared "time" variable.** A mapper is a named function `f: canonical_micros -> canonical_micros` (interval version for the timeline), first-class and inspectable:

- `media -> display` is a **reclock** (0.5× slo-mo preview = one mapper, not a mode).
- `musical -> audio` is a **tempo map** ((bar, tempo) list).
- `timeline -> media` is a **decode plan** — which clip, what offset, what rate. The *same* object the editor draws and the decoder fetches by.

Payoff: **the editor's timeline, the player's transport, the shader's `u_time`, and the MIDI viz are all views over one graph of clocks and mappers.** "Audio-responsive visuals" is not a feature — it is the shader subscribing to the audio clock's analysis stream while `u_time` runs off the media clock, and the reclock mapper commits you to *visuals slow with the song*, exactly Milkdrop's behaviour, exactly what "unified time" meant.

Honesty rule: **`now` is never a bare number; it is always a (clock-id, position) pair.** A bare "5.0" is undefined; `(5.0, media:player0)` is a fact.

---

## 2. One type system

Types are the skeleton. One vocabulary for the typed thing that flows between modules, or "connect at will" becomes "connect only what someone wrote an adapter for."

**A small, closed set of media types; every module declares in its manifest what it consumes and emits.** That is our own WebGL2 bench's typed-port idea (`nodes`, `fromPort`, `toPort`, `type`, refuse-at-connect-time) promoted to a suite-wide law — and it is what makes drag-and-drop *safe* for a non-programmer. The lineage is theirs; I am not inventing, I am promoting.

| type | what it is | encoding | notes |
|---|---|---|---|
| `clock` | time reference | struct | by reference (id) |
| `packet.audio` | PCM | header {rate, ch, layout, fmt} + bytes | **never resampled silently** |
| `packet.video` | decoded frame | header {w, h, fmt, colorspace, pts} + bytes | pts in canonical micros |
| `packet.subtitle` | text + timing | structured | |
| `stream.audio` / `stream.video` | a *pullable source*, not a buffer | source id + caps | **the big one — §3** |
| `gpu.texture` | GPU texture handle | context id + texture id | only by reference; no silent CPU copy |
| `gpu.buffer` | GPU buffer handle | context id + buffer id | |
| `bus.bytes` | flat byte range | addr + len | the escape hatch, typed as untyped |
| `midi` | MIDI message | UMP (MIDI 2.0) u32×1..4 | UMP end-to-end; MIDI 1.0 only at the legacy edge |
| `event` | control/automation | {clock, channel, value} | how bus *and* MIDI reach modules |
| `meta` | metadata | JSON | titles, chapters, lyrics, cue points |
| `ledger` | timeline / EDL | ordered (clip, mapper, in/out) | the editor's document |

Two teeth:

**Rule A — the header travels with the bytes, and the header is the type.** No guessing from extension or sniff. A `stream.video` *declares* its caps (codec, profile, dims, pixfmt, colorimetry); a downchain module *refuses* if it cannot honor them — never "try and see."

**Rule B — GPU memory is a first-class type, and a *handle*, not a buffer.** The fastest pipelines on this AMD box are the ones where a decoded frame **never leaves the GPU**: decode (D3D11VA/VAAPI via FFmpeg or libmpv's render API) → filter → shader → present, all as `gpu.texture` handles. Copying to CPU is the worst tax in the field, and it touches the driver more on a TDR-prone box. So `gpu.texture`/`gpu.buffer` move by reference; a CPU copy is an explicit named op (`module:download`), never the default. [INFERRED: exact zero-copy interop depends on the GPU API and context-sharing we choose; the *shape* is certain, the surface is a build decision.]

The deliberate leak: **`bus.bytes` exists and is honest about being untyped.** "At will" needs an escape hatch; typing *it* as the hatch keeps the warranty on everything else.

---

## 3. What flows — the pull model

The second-biggest choice after "several clocks" is **push vs pull**, and I stake the design on **pull**: a source is a *capability to request the next unit*; push exists only where a producer must (audio device, live input).

Why pull: a decoder produces at the consumer's demand; an audio callback consumes at the *device's* demand. Push-everything means back-pressure and buffering discipline everywhere (the tape-player underrun mess). Pull-everything means:

- **A file is a source of `stream.video` + `stream.audio`.**
- **A shader viz is a source of `gpu.texture`**, and it *pulls* `packet.audio` analysis from the audio clock — "audio responsive" is just what the shader pulls. No special case.
- **The display is a sink** pulling its next frame at vsync.
- **A MIDI controller is a source of `midi`**, pushed (hardware pushes), buffered into a queue *the consumer pulls from*.

The seam in miniature:

```
Source<T> { caps; pull(count, ctx) -> Vec<T> | Eof | WouldBlock; seek?(pos); clock }
Sink<T>   { caps; pushChunk(item, ts) -> Accept | Backpressure(n) | Refuse(reason) }
```

Framing rule that makes "connect at will" true rather than aspirational:

> **A `Source<T>` and `Sink<T>` that agree on `T` connect with no adapter; the pipeline language (§5) just names the connection.** Adapters — `resample`, `convert`, `download`, `upload`, `demux`, `mux`, `reclock` — are first-class modules and the *only* places a type or clock-rate change happens.

The `gpu.texture` caveat: **within a process, handles move freely; across processes it needs a shared context or explicit zero-copy handoff.** [DESIGN: renderer owns its context; decode/filter co-locate *same-process* with it so textures never cross. The contract must not assume that — it must *express* "this module needs a shared context" in the manifest, so the scheduler co-locates or refuses. That is the difference between "we got lucky with performance" and "the contract guarantees it."]

---

## 4. Plug in vs build

**Take the boring, already-won war; spend our hours on the seams, the language, the editor, the glue — what no one else has.**

### Plug in (do not write):

- **FFmpeg** — decode/demux/mux/filter/convert: `libavformat`, `libavcodec` (every codec; hw decode via the *same* AVCodec API + a different `hwaccel` = the "one unified API" he asked for [INFERRED: surface specifics depend on the FFmpeg build; the unified-API property is the stable fact]), `libavfilter` (already a typed-ish pipeline language and a fine template), `libswscale`/`libswresample` (our explicit converter modules). LGPL/GPL (some codecs need `--enable-gpl`) — §9.
- **mpv / libmpv** — the player soul. `libmpv` exposes a `mpv_render_context` render API handing frames as GPU textures you can composite or hand to a shader, and it does hw decode + presentation *reliably on Windows/AMD* — precisely the terrain the old bench avoided and precisely what his ruling opened. [INFERRED: exact render-API version I cannot pin live; the stable fact is libmpv ships a render API for exactly this embed-and-composite use.] I mean *embed libmpv as a module whose caps say it emits `gpu.texture`*, not "run the binary". GPLv2+ — §9.
- **A GPU/graphics API** for render/present/3D. The ruling changed my mind and I want to be explicit: the old bench was raw WebGL2, no Three.js, one context, chosen *for stability on this machine.* The ruling makes stability *measured, not assumed*, and a 3D renderer is on the table if best. **The contract must be renderer-agnostic** (a module says "I emit `gpu.texture` into context `gpu:render0`" and doesn't care whether that context is WebGL2, WebGPU, Vulkan, D3D11/12, or OpenGL). *As a build decision*, default the player+3D to a native context (libmpv's vo or D3D/Vulkan) and keep WebGL2 for the browser-hosted bench that already works — then *measure* which is stable. [DESIGN: the winner is downstream of a measurement we haven't run; the contract makes it a swap, not a rewrite.]
- **Windows MIDI Services (MIDI 2.0 stack, already installed/running)** — hence `midi` = UMP end-to-end; speak MIDI 1.0 only at the legacy edge, which the OS handles. [INFERRED: the WinRT MIDI 2.0 surface is the Win11 direction; the exact layer under it is a build decision.]
- **OBS, FL Studio, ComfyUI, UVR/StemRoller** — orchestrate, don't reimplement. They speak MIDI/export stems/do AI image-video/record. Wrap each as a source or sink with a manifest over its file/network/CLI surface, so "bot playback," "drag a GIF in," "AI-generate a clip" become modules over the same seams.

### Build from scratch (worth our hours):

1. **The runtime + scheduler** — reads manifests, checks port types, builds the clock/mapper graph, co-locates modules (same process for shared context, separate for isolation). This is the "deploy at will" engine — *the product*.
2. **The pipeline language** (§5) and its two surfaces (text + JSON/DAG).
3. **The editor** — cut/slice/re-order, drag-drop GIFs, timeline-as-ledger (§7). Playback is trivial given pull + the timeline mapper; the *editing UX* (where the human actually lives, per 2026-08-02: "the bench can render states and cannot represent change") is the hard, human, ours-alone part.
4. **The analysis layer** — FFT/onset/beat/chroma that shaders and MIDI viz *pull* from. FFmpeg/FFTW give the transforms; the *publish-as-clock, subscribe-as-source* shape is ours, and it makes "audio responsive" a property, not a feature.
5. **The shader/effect modules** — our shader chunks (JSON headers, typed ports) become *sources of `gpu.texture`* consuming `u_time` from any clock and features from the analysis stream. The bench graduates from "console sketch" to "a module like any other."
6. **The bus bridge** — makes a `Source`/`Sink` visible to and drivable by the Bifrost bus and Discord. "Bot playback" = the bus driving the same verbs a human drives.

---

## 5. The pipeline language

"If it makes sense" does real work: **unify where it buys us something (time, types, plumbing); do *not* unify where it just adds a translation layer (control surfaces).**

Syntax — one line, same string whether a human types it or an agent generates it:

```
# play, decode, filter, present
player:/music/track.flac | demux | split(audio, video) | resample(48000, stereo) | audio.sink

# a song driving a shader to display + a snapshot
player:/music/x.mp3 | tee(analysis(fft, beat) -> viz:milkdrop, audio.sink)
viz:milkdrop | display
snapshot(viz:milkdrop -> out:shot.png)          # pull one frame, once

# MIDI driving a viz
midi:keys | scale | map(cc:74 -> viz.milkdrop.param:hue) | viz.milkdrop
```

Grammar — small, and I want it to stay small:

```
pipeline    := source ( '|' stage )* sink?
stage       := module '(' args ')'
source      := kind ':' target      # file: player: midi: gpu: net: gen: viz: bus:
sink        := '->' target | '|' module
connection  := '(' source '->' sink ')'
branch      := '|' tee '(' stage -> stage (',' stage)* ')'
```

Every token **typed and checked at connect time**: an invalid pipeline *fails to compile* with the port/type reason, never "runs and does the wrong thing." The manifest (§6) is what the compiler checks against.

Two vocabularies stay deliberately separate (so the reconciler can disagree cleanly):

1. **Graph language** — plumbing; one syntax, human and agent.
2. **Control/automation surface** — *driving* a running pipeline (seek, play/pause, param, note): `event`/`midi` over named channels, *not* graph syntax. "Make hue follow CC74" is a *channel mapping* in the control layer. Conflating "what is connected" with "how it is modulated" is how a DSL grows into a bad programming language.

Manifest and language are two projections of **one owned typed graph**. Human writes text; agent writes text; runtime lowers to DAG; editor renders the DAG; checker says "no such port." One source of truth, four surfaces — the Store/Ledger lesson, applied to control.

---

## 6. How modules describe themselves and get found

A module is a directory (or zip):

```
manifest.json     # caps, ports, deps, license, entry, isolation, clocks
entry             # the binary/script/URL
(optional) code, assets, shaders, presets
```

`manifest.json` (keystone):

```json
{
  "name": "viz.milkdrop", "version": "0.1.0", "kind": "module",
  "inputs":  [ {"port":"audio.features","type":"packet.audio.frequency","optional":false},
               {"port":"time","type":"clock"} ],
  "outputs": [ {"port":"frame","type":"gpu.texture"} ],
  "params": ["hue","zoom","warp"],
  "isolation": "same-process",
  "gpu": {"needs_shared_context": true, "context": "gpu:render0"},
  "license": "MIT", "runtime": {"lang":"rust","entry":"viz_milkdrop.dll"},
  "clocks": {"consumes":["media:player0"],"produces":[]},
  "capabilities": ["read-net?"]
}
```

Four rules:

- **Self-describing ports** — the manifest declares; the runtime doesn't introspect binaries. No duplicated checker logic.
- **Isolation + GPU needs declared** — the scheduler places it *before* the pipeline runs.
- **Discovery = directory scan + capability predicate, not a registry server.** Drop the folder in `modules/` → available; remove it → gone. "At will" with zero standing infrastructure. (A bus-visible index can come later; the store is just the modules on disk.)
- **Versioned and pinned** — `requires: {libmpv>=2.x}`, refused with a human-readable name.

---

## 7. The editor as a ledger

The timeline is a **`ledger`-typed module output.** My 2026-08-02 finding — "the bench can render states and cannot represent change" — applies one level up. An editor that only renders states is Premiere without undo, and taste is comparative.

```
ledger = ordered entries:
  { clip, in: Time range, at: Time, map: mapper, fx: [pipeline] }
```

Playback: **the `timeline -> media` mapper resolves a micros to (clip, offset, rate) and pulls.** Cut = insert boundary; slice = split at t; re-order = change `at`; drag a GIF in = append a GIF-loop source; speed ramp = edit the mapper. None are special features; all are edits to one data structure, and the renderer is a source pulling across the timeline.

Two earned things survive the jump:

- **The take strip is a view of the ledger** — every "I changed something" is an append; diff/go-back are store queries. Undo is a free query.
- **A preview must know when it is lying** — off decode, still-compiling effects, stale analysis must *say so*, not show a confident wrong frame; an "audio responsive" viz secretly half a second behind the sound is a name that lies.

New at this altitude: **the editor's output is itself a `Source<T>`** — `edit.ledger | encode | out:render.mp4` or `edit.ledger | display | record`. The editor is a module that *produces a timeline*; everything downstream pulls it. That is "freedom to connect at will" for the editing wish.

---

## 8. Isolation, deployment, language

**Isolation**, three tiers from the manifest:

- **same-process** — hot path, shared context, can crash the runtime. decode/filter/render.
- **separate-process** — sandboxed; crash contained, runtime restarts it. untrusted/flaky (a shader that could TDR the GPU, a scrapper). Same typed protocol over IPC.
- **external** — orchestrated tool (FL Studio/OBS/Discord) via its own surface.

This maps to the TDR reality: **the thing most likely to crash the AMD driver — heavy 3D, a bad shader — runs separate-process with its own context; a TDR kills the module, the runtime restarts it, the arsenal keeps playing.** The old bench's single-context fragility was its environment's cost; the ruling lets us pay a process boundary instead of a driver reset.

**Deployment**: modules on disk, found by scan; a pipeline is a named, versioned graph you can save, send over the bus, re-instantiate. "Deploy at will" = "save this named pipeline and wire it to a bus verb."

**Languages** (contract is agnostic at the seam; `runtime.lang` names it):
- **Hot path (decode/audio/render/scheduler): Rust** (GIL-free audio callback, predictable latency, safe concurrency), **or C/C++** where FFmpeg/libmpv bind most naturally. [DESIGN: a default, not a rule.]
- **Glue/orchestration/bus/MIDI/manifests/tests: Python** — the house's muscle, the bus.
- **Shaders/effects: GLSL/HLSL** — the target GPU API's language.

Why not Python on the hot path, plainly: the audio callback runs on a hard realtime-ish budget (ms of buffer) and an interpreter with a GIL, GC pauses, and regex-through-C is not the tool. Python *orchestrating* a Rust/FFmpeg/libmpv hot path gives both ergonomics and latency budget. Not purity; "where does the latency budget live."

---

## 9. Licences

The house is public on GitHub under Apache-2.0; this constrains what we embed.

- **FFmpeg**: LGPL/GPL; `--enable-gpl` codecs and libx264/265 pull in GPL. **Fine installed locally; changes obligations if we ship one public binary.** [INFERRED: posture depends on configure flags; the LGPL-core vs GPL-parts split is the stable fact.] Keep FFmpeg behind a `separate-process`/`external` boundary so GPL never *links* into our Apache core.
- **mpv/libmpv**: GPLv2+. Same arm's-length treatment — a module speaking the protocol, not a linked library. [INFERRED: downstream of whether we distribute binaries; for his own machine obligations are minimal.]
- **Our code**: Apache-2.0.

Not a legal dodge; the same principle as isolation — the typed protocol already draws the boundary, so respect is cheap, and the Apache core stays clean whatever GPL-heavy thing we plug in downstream.

---

## 10. The first working pipeline

The smallest pipeline that proves every seam at once (decode, time, types, render, analysis, MIDI, output):

**Step 1 — the "Milkdrop test":** `player:/music/track.mp3 | demux | tee(analysis(fft,beat) -> viz:milkdrop, audio.sink)` plus `viz:milkdrop | display`. Prove: hw decode → GPU texture never leaves the GPU; shader pulls analysis and `u_time`; audio continuity held; visuals slow with the song on a speed change. This is the *floor* of the contract made real.

**Step 2 — control reaches it:** one MIDI controller mapped to one viz param (`midi:keys | map(cc:74 -> viz.milkdrop.param:hue)`). Prove the `event`/`midi` channel reaches a module and a bare `(position, clock)` never leaks.

**Step 3 — output and edit:** `snapshot(viz:milkdrop -> out:shot.png)` and an `encode` to `out.mp4`/`webm` from the same graph, then a two-clip `ledger` (drag a GIF onto a track) played back. Prove the renderer pulls across the timeline and the editor is a `Source<T>`.

**Acceptance he reads and says yes to:** a song plays with a Milkdrop-class visual that breathes with it; he twists a knob and a colour moves; he drags a GIF next to the song and gets a short clip out the other end — all three from the *same* typed graph, and any of the three disposable and reusable "at will." That is the contract, in miniature, and it is exactly what he asked for.

---

## 11. What I would build in (the honest list)

**Languages**: Rust (hot path), Python (glue), GLSL/HLSL (effects). **Engines**: FFmpeg + libmpv + a GPU API (native-first on this box) for the boring parts; the runtime, pipeline language, editor, analysis layer, and bus bridge are ours. **Licences**: Apache-2.0 core, GPL behind process boundaries.

---

## 12. Verdicts

V1. The suite is a modular runtime over a typed pipe protocol, not an application with tabs. [CERTAIN]

V2. Time is a graph of named clocks related by first-class mappers, one canonical rational-micros timebase, and `now` is never a bare number. [CERTAIN]

V3. The type system is a small closed set of media types with declared headers; typed ports are the bench's discipline promoted suite-wide. [CERTAIN]

V4. GPU memory is a first-class handle type and a CPU copy is always an explicit opt-in, never the default. [DESIGN]

V5. The flow model is pull (Source/Sink) with push only where a producer must; adapters are the only place a type or clock-rate change happens. [DESIGN]

V6. Plug in FFmpeg, libmpv, and a GPU API; build the runtime, the pipeline language, the editor, the analysis layer, and the bus bridge. [DESIGN]

V7. The pipeline language is one syntax for plumbing, and control/automation is a *separate* channel — never conflated into the pipe grammar. [DESIGN]

V8. The editor's document is a `ledger`, and the editor's output is itself a `Source<T>`; the take strip and "a preview must know when it is lying" carry over from the bench. [DESIGN]

V9. The hot path should be Rust (or C/C++), with Python for the glue — not Python on the hot path. [DESIGN]

V10. GPL code (FFmpeg/libmpv) sits behind a process+protocol boundary so the Apache-2.0 core stays clean. [DESIGN]

V11. Which concrete GPU API (and, from it, whether FFmpeg D3D11VA vs libmpv's render path is the decode surface) is decided by an unrun measurement on this AMD box; the contract only has to make it a swap. [INFERRED]

V12. The first pipeline is: hardware-decode a file → GPU-resident texture → a shader pulling audio analysis and a clock, one MIDI knob to one param, and a snapshot/encode out — all one typed graph. [CERTAIN]
