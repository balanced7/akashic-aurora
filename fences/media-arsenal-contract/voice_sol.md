[DESIGN] **Sunshine extra voice — Media Arsenal contract (T399), 2026-09-13**

## The decision

Build **a small, versioned media protocol and graph compiler, not a new universal media engine**. The arsenal is a federation: mpv is the interactive playback engine, FFmpeg is the deterministic transform/export engine, the existing browser VFX bench is one renderer, and future renderers (libplacebo, wgpu, Three.js, GStreamer) join through adapters. The common layer describes time, typed data, control, cost and provenance; it must not hide engine-specific powers behind a lowest-common-denominator API.

I would call the canonical document `arsenal.graph/v1alpha1`. YAML is the hand-authored spelling; validated JSON is the wire/storage form; Python and Rust builders emit exactly that JSON. Media does **not** flow through Unix pipes or YAML. The document compiles into local in-process edges, shared-memory edges, GPU-handle edges, or supervised IPC.

## 1. One time contract, several honest clocks

Every timed item carries:

```text
TimeSpan { epoch:u64, start:i64, duration:i64, rate:{num:i64, den:i64}, clock:ClockId }
```

`start * num / den` is seconds. No floating-point timestamps. `epoch` changes on seek, loop, source replacement or device reset, so a late pre-seek frame can never masquerade as current. Encoded packets may additionally carry DTS; decoded frames carry presentation time only.

Clocks are not pretended identical. The runtime publishes measured correlations:

```text
ClockMap { from, to, at_from, at_to, slope, uncertainty_ns, observed_at }
```

- live playback defaults to the **audio-device clock**; video schedules against it and may drop/hold according to the edge policy;
- silent/video-only playback uses a monotonic presentation clock;
- offline render uses a virtual clock and never drops;
- source PTS, Windows/QPC MIDI timestamps and display predictions are mapped clocks;
- edit time is an exact rational timeline, independent of current playback;
- musical `{bar, beat, tick}` is a view through a versioned `TempoMap`, not the universal timestamp. Tempo changes therefore do not move media events accidentally.

A module must declare whether it preserves, retimes, generates or destroys timestamps and its latency model. Stateful modules receive explicit `Flush(epoch)` and `EndOfStream`; seek is never inferred from timestamps going backwards.

## 2. One type system, without saying “a GPU frame”

The small envelope is common:

```text
Packet { type_id, schema_version, span, sequence, caps_id,
         payload_handle, provenance[], trace_id }
```

Initial semantic types:

- `media.encoded_packet`
- `media.video_frame`
- `media.audio_block`
- `media.subtitle_cue`
- `control.event` and `control.curve`
- `analysis.features`
- `asset.reference`
- `timeline.edl`

`caps_id` resolves to immutable negotiated descriptors. Video caps include dimensions, pixel format, primaries/transfer/matrix/range, chroma siting, alpha mode, sample aspect, orientation and frame-rate constraint. Audio caps include sample representation, rate, channel count **and channel layout**, interleaving and loudness metadata. Control values carry a real unit/range (`Hz`, `dB`, `seconds`, `colour`, enum), not merely 0–1.

Memory is explicit: `cpu`, `d3d11(texture,adapter_luid)`, `d3d12(resource,adapter_luid)`, `vulkan(image,device_uuid)`, `opengl(texture,share_group)`, `webgpu(texture,adapter)`, or `encoded`. A handle includes ownership, lifetime and synchronization/fence semantics. Two ports both saying `video_frame` do not connect if their memory devices cannot interoperate.

Connection is capability negotiation. The compiler may insert a known converter only when the graph permits it, then prints the price: copies, colour conversions, resamples and estimated latency. `arsenal plan` must make `D3D11 -> CPU -> WebGL` loud. There is no magical zero-copy promise across mpv, a browser and wgpu.

Edges declare pressure policy: `block`, `drop_oldest`, `drop_newest`, `latest`, or `sample(n)`, plus queue duration and latency budget. Offline edges are deterministic/blocking; live preview may drop video but never silently drop control or edit events.

## 3. The pipeline language

Example Daniel can read:

```yaml
api: arsenal.graph/v1alpha1
mode: live
clock: audio/default
assets:
  main: {uri: "E:/Video Output E/song.mp4"}
  spark: {uri: "E:/gifs/sparks.gif"}
nodes:
  player: {use: mpv.playback/v1, with: {source: $main, hwdec: auto-safe}}
  gif:    {use: ffmpeg.image-sequence/v1, with: {source: $spark, loop: true}}
  mix:    {use: vfx.compositor/v1, with: {layout: overlay, x: 0.72, y: 0.08}}
  fft:    {use: audio.spectrum/v1, with: {bands: 64, window: hann}}
  bloom:  {use: vfx.shader/v1, with: {chunk: neon-bloom}}
  midi:   {use: windows-midi.input/v1, with: {port: "auto"}}
  screen: {use: present.window/v1, with: {vsync: true}}
edges:
  - player.video -> mix.base
  - gif.video -> mix.overlay
  - player.audio.monitor -> fft.audio
  - mix.video -> bloom.video -> screen.video
bindings:
  - midi.cc(1) -> bloom.amount {map: [0,127] => [0.0,2.0], smooth: 20ms}
  - fft.band(3) -> bloom.pulse {map: db(-60,0) => [0,1], attack: 12ms, release: 180ms}
```

The canonical graph does not depend on YAML conveniences such as the chained edge; expansion happens before validation. Each run stores the expanded graph, resolved module versions, negotiated caps, inserted adapters, asset hashes, clock maps and events as a **take**. That ties directly to the VFX render ledger/take strip: live improvisation can become reproducible automation, and an agent-created run can appear beside Daniel's runs.

A non-destructive EDL is another graph input: source ranges, exact timeline placement, speed maps, transitions and overlays. “Cut, slice, reorder” edits references first; FFmpeg compiles the EDL for proxies/final export. Destructive file rewriting is never the editor model.

## 4. Module contract and discovery

A module ships a signed/hashed `arsenal.module.json` containing:

- stable namespaced ID, semantic version, protocol range and implementation digest;
- input/output/control ports with schemas and negotiable caps;
- realtime/offline capability, determinism, statefulness and seek/flush behavior;
- clock behavior and declared base/dynamic latency;
- supported operating systems/architectures, GPU APIs and required features;
- isolation modes, permissions (filesystem roots, network, device, GPU), health probe;
- licence/SPDX expression, source URL and redistribution profile.

Discovery searches project, user and system registries in that precedence, but a lockfile resolves every ID to a digest. No ambient PATH surprise becomes a reproducible take. `arsenal inspect`, `plan`, `doctor` and `license-report` are first-class verbs. Unknown manifest fields are preserved; unknown required capabilities fail loudly.

Transport is negotiated separately from semantics. In-process Rust/C ABI is for trusted low-latency nodes. Most engines begin as supervised child processes over length-framed local IPC with shared buffers where earned. JSON is control only, never per-pixel payload. A crash yields `ModuleFailed`, keeps the last reproducible take, and can restart/bypass according to graph policy.

On this AMD host, GPU work belongs in a restartable GPU worker. Start with one device/context family per live graph, add a second only after a ten-minute stress/TDR measurement. The watchdog records adapter/driver, device-removed reason, graph and last node; it degrades to software or bypass rather than retry-looping the driver. Offline jobs run in separate workers with explicit GPU/VRAM budgets.

URL ingestion is sandboxed: yt-dlp gets an allowlisted output root and argument model, not arbitrary postprocessors. Modules declare network and filesystem access. Project files contain references, not copied secrets.

## 5. Engines: reuse versus build

**Plug in:**

- **mpv** for the loved interactive player, transport, seeking, subtitle/audio selection and hardware decoding. Begin with its JSON IPC/process adapter for licence/process isolation; use libmpv's render API only in a separately packaged shell when direct composition earns it. Official manual/client API: https://mpv.io/manual/stable/ and https://github.com/mpv-player/mpv/blob/master/libmpv/client.h . mpv is GPL-2.0-or-later by default; an LGPL build is a constrained feature configuration, not a label we assume: https://github.com/mpv-player/mpv/blob/master/Copyright .
- **FFmpeg libraries/CLI** for probe, demux/decode adapters, GIF/image sequences, filters, proxies and final encoding. Its hardware-device API makes D3D11VA/Vulkan frames describable, but support is discovered at runtime: https://ffmpeg.org/doxygen/trunk/hwcontext_8h.html . FFmpeg is LGPL-2.1-or-later by default and becomes GPL when GPL components are enabled: https://ffmpeg.org/legal.html .
- **yt-dlp** as a source resolver/downloader into the asset cache, never as the graph runtime: https://github.com/yt-dlp/yt-dlp (Unlicense).
- **Windows MIDI Services SDK** as the Windows MIDI 1.0/2.0 timestamped control adapter because the service is already live: https://microsoft.github.io/MIDI/ and https://github.com/microsoft/MIDI . Preserve UMP messages; map to higher-level controls only in a node.
- **Existing WebGL2 VFX bench** as `vfx.browser/v1`, including shader graph, chunks, Shadertoy ingest and render-ledger/take semantics. Do not rewrite it before it can consume a canonical control stream and asset/video input.
- **libplacebo** as the first native high-quality colour/scale/shader candidate and **wgpu** as the native custom compositor candidate; choose by an on-machine spike, not ideology: https://libplacebo.org/ (LGPL-2.1+) and https://docs.rs/wgpu/latest/wgpu/ (MIT/Apache-2.0). **Three.js** is valid for 3D/browser scenes and stays a renderer adapter, not the media contract: https://threejs.org/docs/ (MIT).
- Evaluate **GStreamer** when a live capture/broadcast graph needs its mature scheduling and Windows D3D11 elements; do not put a second universal graph underneath v1 merely because it has one. Docs: https://gstreamer.freedesktop.org/documentation/ ; core is LGPL-2.1, plugins must be inventoried individually.

OBS, ComfyUI, UVR/StemRoller and FL Studio initially integrate at **asset/control boundaries**: OBS virtual camera/recording or WebSocket, ComfyUI job/result assets, separated stems as immutable assets, MIDI/tempo interchange with FL Studio. Do not couple their internal graphs into the realtime ABI in v1.

**Build:** the schemas/validator, graph compiler/planner, clock mapper, buffer/handle contract, module registry/lockfile, supervisor, take/provenance ledger, EDL, control/automation merger, licence report, Python SDK/CLI and thin Rust realtime host. Build basic FFT/envelope features in Rust (MIT/Apache crates) before accepting a copyleft analysis dependency into the base profile.

Language split: Rust owns clocks, buffers, scheduling and trusted realtime modules; Python owns orchestration, agents/Bifrost, asset jobs and rapid adapters; TypeScript owns the studio UI/browser VFX. C ABI/IPC is the boundary, never Python callbacks on the audio/render thread.

## 6. Licensing is a compiled property

Keep the protocol, schemas, Python control plane and Rust host Apache-2.0/MIT compatible. Publish profiles:

1. `arsenal-core` — permissive/LGPL dynamically used components with source/notice obligations tracked;
2. `arsenal-gpl` — opt-in player/codec bundle where combined-work obligations are accepted;
3. `external` — user-installed executable adapters.

Every `plan` emits an SPDX bill of materials and the resulting distribution profile. A process boundary is useful engineering isolation, **not a legal magic wand**; final packaging gets counsel/review. Never ship a conveniently downloaded codec build without preserving its configuration and licence provenance.

## 7. First working pipeline

Build the smallest slice that proves the contract and feels like the future:

**Drop a local MP4 and a GIF -> mpv plays/seeks with hardware decode -> the GIF overlays -> one existing VFX chunk affects the composition -> audio envelope drives one shader parameter -> one physical MIDI control drives another -> record the run as a take -> deterministic FFmpeg export replays the recorded automation.**

For the first spike, allow one explicit CPU copy at a browser/native boundary if zero-copy is not already available; print it in `arsenal plan`. Correct clocks, colour and recovery beat a fake zero-copy milestone.

Pre-register acceptance:

- seek/loop increments epoch; no old GIF/video/control packet appears afterward;
- 30 minutes of playback remains within 20 ms A/V/control alignment and reports measured drift/uncertainty;
- MIDI-to-visible response p95 is measured and under 30 ms locally;
- hardware decode is runtime-proven by negotiated caps/device evidence, not inferred from an `auto` flag;
- unplug MIDI and crash the renderer: playback survives or performs the declared bypass; no restart storm/TDR;
- exported duration and automation event positions differ from the saved take by at most one output frame (audio by one block), with hashes/config recorded;
- `license-report` and the fully expanded locked graph are stored with the take;
- a software-decode/no-VFX fallback works on the same project.

Kill criteria for the architecture: if the same saved graph cannot run live and offline with only declared module substitutions; if an implicit copy/colour conversion is found; if musical tempo edits move media-timed events; or if recovery cannot identify the failing module/epoch, stop feature work and repair the contract.

## Bottom line

The freedom comes from a narrow, honest waist: exact time plus clock mappings, semantic packet types plus explicit memory/caps, and a versioned graph that compiles to different engines. mpv, FFmpeg, WebGL, wgpu, Three.js and future tools remain themselves. Daniel gets one readable way to connect them, agents get one inspectable JSON contract, and neither is trapped by whichever renderer we happen to choose first.