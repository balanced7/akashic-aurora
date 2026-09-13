# RECONCILIATION — media-arsenal-contract (T399)

[DESIGN] Reconciled by Vandor (claude), 2026-09-13. Daniel gates.

## Inputs (all filed verbatim in this directory)

- `brief.md`: the invitation, carrying Daniel's words verbatim.
- `half_a.md`: Heimdall (deepseek), blind, sealed 12:19.
- `half_b.md`: Navi (kimi), blind, sealed 12:31.
- `voice_sol.md`: Sunshine (sol), blind extra voice. Its sha256 `47450c48481dcc0ba491c66a…` matches its spill ref.
- `prior_vandor.md`: Vandor's prior, sha256 `a5897d1e3636f4bbc9d00547b1b804a3ac1a2d0cd7ab8e1a1475c4d144f34faa`. This is the commitment printed in the brief before any design went out.
- `flip_heimdall.md`, `flip_kimi.md`, `flip_sol.md`: each seat's response after reading the other three.
- `amendments_heimdall_postflip.md`: Heimdall's two post-flip messages to Sunshine (bus 1789320186058-0 and 1789320201631-0), read directly at the source.
- `relays_sol_postflip.md`: Sunshine's relays of those amendments, plus its own final nuance on scheduling (bus 1789320154152-0, 1789320194042-0, 1789320211747-0).

## §1 The decision

**Own the contract; compile to engines.** The canonical artifact is an engine-neutral, versioned typed graph, `arsenal.graph`. It holds typed ports, exact time, explicit memory and copies, bindings and a take ledger. Engines are compile targets and adapters that earn their roles by receipts measured on Daniel's machine, never the contract itself:
- GStreamer 1.28 is the first live backend.
- FFmpeg handles transform and export.
- mpv is the player module.
- The VFX bench is the first renderer.
- wgpu, libplacebo and Three.js come in by spike.

Native code owns clocks, buffers and hot scheduling; Python conducts; TypeScript draws the studio. Every copy, conversion, latency, licence obligation and failure policy is explicit, and `arsenal plan` prints it.

## §2 Where the seats agreed

Convergence on topics the brief itself listed (five clock domains, GPU memory, licences, languages) is compliance with the brief, not independent evidence. The agreements that count are the ones no prompt named:
- exact rational time and never floats (all four, blind)
- colour truth carried in the frame type (Heimdall, Sunshine and Vandor blind; Navi promoted her buried field after reading)
- GPU memory as an explicit handle, with copies explicit (all four)
- the editor as a view over a ledger (Heimdall, Navi, Sunshine)
- mpv as a player rather than a spine (Sunshine and Vandor blind; Heimdall and Navi after reading)
- a native hot path under a Python control plane (Navi, Sunshine and Vandor; Heimdall after reading)
- an owned graph above every engine (all four, in their own words)

`fence pv` reported three MISSING citations, all in half_b: `music/track.flac`, `music/track.mp3` and `music/x.mp3`. They are example filenames inside half_b's illustrative pipeline syntax (§5 and §10), not claims about files in the repository. Nothing rests on them, so no section is retired; this note names them to acknowledge the M1-PV gate.

## §3 The forks, and where they landed

### F1: What is GStreamer's role?

- **Vandor prior §3:** GStreamer 1.28 as "the media spine", wrapped behind our contract.
- **Heimdall flip:** "the correct spine: it already has a clock, typed caps, and a pipeline syntax, which is the very spine I argued we'd have to build. I over-built."
- **Navi flip A:** "adopting it means adopting a *second, competing* version of exactly the three things this contract exists to own", "the one choice that quietly forfeits the brief."
- **Sunshine flip §5:** "GStreamer's own launch syntax must not become Daniel's durable project contract." Its net position: "an engine-neutral Arsenal contract compiled primarily onto GStreamer 1.28."
- **Heimdall post-flip:** "the typed-port graph IS the canonical thing … GStreamer as a backend earns its slot only where its receipts beat ours."

**Landed.** `arsenal.graph` is canonical. GStreamer 1.28 is the first live-backend spike and wins each role by receipt.
- Saved projects never contain GStreamer element names or caps strings.
- A pinned GStreamer plan is a compile artifact stored beside the graph, and an escape-hatch native node covers what the graph cannot express.
- **Tripwire** (Navi's objection made operational): if compiling to GStreamer forces its segment, caps or element vocabulary into `arsenal.graph`, stop and repair the contract.
- **Reconciler's note, to verify in the spike rather than assume:** GStreamer's model already sits close to the converged time contract. In playback pipelines the audio sink usually provides the pipeline clock, and a seek produces flush events plus a new segment tied by a seqnum, which is near Sunshine's epoch and `Flush(epoch)`.

Vandor concedes the word "spine".

### F2: One clock or several?

- **Heimdall half_a V1:** "exactly one canonical clock". Withdrawn post-flip: "exact rational timebase YES, single-source-of-truth clock NO."
- **Navi half_b §1:** named clocks related by first-class mappers; "`now` is never a bare number"; canonical rational microseconds.
- **Sunshine voice §1 and flip #4:** a measured `ClockMap` with uncertainty, an `epoch` on every timed item, and "represent position as integer ticks plus an exact rational time base … the fixed unit buys nothing."

**Landed.** One exact representation, several honest clocks.
- A time value is `(clock, epoch, ticks, timebase)`.
- Clocks are named peers related by first-class mappers carrying measured slope and uncertainty.
- The epoch bumps on seek, loop, source replacement and device reset. Stateful modules receive `Flush(epoch)`, and a seek is never inferred from timestamps running backwards.
- Musical time is a versioned `TempoMap` view over the elected master, so tempo edits never move media-timed events.
- Which clock is master depends on the mode (Navi flip, miss #2; Sunshine: "Election is not ontology."):

| mode | master clock | failover |
|---|---|---|
| live, with audio | audio device | virtual continuation clock (§4.6) |
| live, silent or video-only | monotonic presentation clock | none |
| offline render | virtual clock, never drops | none |
| editing | exact rational timeline | none |

### F3: Pull or push?

- **Navi half_b §3:** "I stake the design on pull". Source/Sink, with push only where a producer must.
- **Heimdall flip:** hybrid by port. Post-flip, Heimdall adopts Navi's pull shape.
- **Sunshine post-flip:** "demand-driven where possible, explicit push boundaries and queues where arrival/deadlines require."

**Landed.** `Source<T>`/`Sink<T>`, demand-driven by default (files, offline work, timeline planning).
- **Push boundaries are declared:** audio device demand, capture/MIDI/network arrival, and display deadlines.
- **Queues:** each push boundary gets a bounded queue with a pressure policy (`block | drop_oldest | drop_newest | latest | sample(n)`) and a latency budget.
- **Offline vs live:** offline edges are deterministic. Live preview may drop video but never silently drops control or edit events.
- **Analysis:** a shader samples a timestamped analysis stream aligned to its target time. It never synchronously pulls FFT on its render path.

### F4: One control verb, or two surfaces?

- **Heimdall half_a V6:** one verb, `map <target> = <producer>`. Post-flip, after Navi §5 and Sunshine's disagreement #7, Heimdall withdrew the conflation: "shared types, distinct surfaces."
- **Navi flip:** adopts `map`; "the split I wanted is real but it is a *type* split (`Signal` producer vs graph edge), not a *syntax* split."
- **Sunshine flip:** "`map <producer> -> <target>` should be the common gesture … with typed units and explicit merge precedence under it."

**Landed.** Both.
- **One visible gesture creates a binding:** `map <producer> -> <target> {range, curve, smooth, precedence}`. The arrow runs the same way as dataflow edges; Heimdall's `target = producer` spelling was considered.
- **Two surfaces share the same types:**
  - **Graph mutation** is durable, versioned and undoable: nodes, edges, bindings.
  - **Realtime control** is the timestamped event stream flowing through bindings: MIDI moves, automation values, bus nudges.
- **The bus is a typed producer exactly like MIDI** (Heimdall flip #4), so an agent's moves are remixable events rather than a side channel.

### F5: Which renderer goes first?

- **Vandor prior §3:** the first card built is a wgpu/WGSL effect element.
- **Heimdall flip #2:** "the right *later*, wrong *first*" and "This is Vandor's own receipt principle … turned back on his build order."
- **Sunshine voice §7:** "Correct clocks, colour and recovery beat a fake zero-copy milestone." Sunshine's flip then narrows its first slice to a native GStreamer → shader → present proof.
- **Heimdall post-flip:** "we must NOT gate first delight on zero-copy; make copies loud and soak the native path in parallel."

**Landed.** Two lanes run in parallel, and neither blocks the other.
- **Lane A (delight)** runs through the renderer that already has a receipt: the WebGL2 VFX bench, as `vfx.browser/v1`, with one loud, planned copy.
- **Lane B (native proof)** measures GStreamer D3D12 decode → a native effect → D3D12 present, zero-copy and under soak. Lane B's receipt chooses the native renderer card.

Vandor concedes the build order.

### F6: Python or native on the hot path?

- **Heimdall half_a V10:** the first pipeline ships in Python. Conceded post-flip (#8).
- **Navi, Sunshine and the Vandor prior:** a native realtime host.

**Landed.**
- **Ownership:**
  - Rust owns clocks, buffers, hot scheduling and trusted realtime modules.
  - Python owns orchestration, agents and Bifrost, asset jobs and adapters.
  - TypeScript owns the studio UI and browser VFX.
- **Hot-thread rule:** no Python callbacks on audio or render threads.
- **Navi's allowance:** a Python prototype of the graph plumbing with faked numbers is fine for validating the contract before paying Rust's build cost.
- **Reconciler's suggestion, to verify in Lane A:** with GStreamer as the backend, first-slice audio features can come from its native analysis elements, so no Python touches the audio thread from day one.

### F7: How many GPU contexts?

**Landed** (Sunshine flip #2, conceded by Heimdall): a host policy, not a protocol law. Start with one live device/context family per graph, and add another only after a ten-minute stress and TDR gate. The type system still describes multi-device reality even where policy forbids a topology.

### F8: What protects the licence?

**Landed** (Sunshine; adopted by Heimdall and Navi): licensing is a compiled property.
- Every `plan` emits an SPDX bill of materials and a distribution profile: `arsenal-core`, `arsenal-gpl` or `external`.
- mpv is GPL-2.0-or-later by default. An LGPL build is a constrained configuration, not a label (Sunshine flip #6, correcting half_a V9).
- A process boundary is engineering isolation, "not a legal magic wand."

## §4 Contract v0

### §4.1 Time

```text
TimeRef   { clock: ClockId, epoch: u64, ticks: i64, timebase: {num: i64, den: i64} }
TimeSpan  { start: TimeRef, duration_ticks: i64 }
ClockMap  { from, to, slope, offset, uncertainty_ns, observed_at }
TempoMap  { version, segments: [{at: TimeRef, bpm, meter}] }
```

Every module declares:
- whether it preserves, retimes, generates or destroys timestamps
- its base and dynamic latency

Control events are `Flush(epoch)` and `EndOfStream`.

### §4.2 Types

```text
Packet { type_id, schema_version, span: TimeSpan, sequence, caps_id, payload, provenance[], trace_id }
```

- **Semantic types:** `stream.video`, `stream.audio` (pullable sources with caps), `media.video_frame`, `media.audio_block`, `media.encoded_packet`, `media.subtitle_cue`, `control.event`, `control.curve`, `analysis.features`, `asset.reference`, `timeline.sequence`.
- **Caps:** `caps_id` resolves to an immutable negotiated descriptor.
  - Video: size, pixel format, primaries, transfer, matrix, range, chroma siting, alpha mode, sample aspect, orientation, rate.
  - Audio: sample format, rate, channel count and layout, interleaving, loudness.
  - Control: values carry a real unit and range (Hz, dB, seconds, colour, enum).
- **Colour truth is enforced.** A mismatch refuses at connect time unless a logged conversion is planned.
- **Memory domains** are `cpu | d3d11 | d3d12 | vulkan | opengl | webgpu | encoded`, each with device identity, ownership, lifetime and sync (fence) semantics.
- **Copies and conversions** are planned nodes with printed cost. Zero-copy is observed, never inferred.

### §4.3 Graph, bindings, takes

- **The canonical form is versioned JSON `arsenal.graph`.** Human spellings desugar before validation: edge lines with an `a | b | c` chain shorthand for quick commands, and YAML for saved projects. Bindings use `map` (F4).
- **Every run is a take**, recording:
  - the expanded, locked graph
  - resolved module digests
  - negotiated caps and inserted adapters
  - asset hashes and clock maps
  - events and the licence report

  The take ledger is the recovery state.
- **The editor** is a projection and mutation surface over an immutable `timeline.sequence` ledger. It is non-destructive, and agent takes appear beside Daniel's.
- **Two surfaces for two readers.** The human surface shows change (a filmstrip of takes); the agent surface shows a diffable graph (Navi flip, miss #3: "the human pays in attention and the agent in tokens").

### §4.4 Modules

- **A module** is a directory plus `arsenal.module.json`. The manifest declares:
  - ID, semver, protocol range and digest
  - ports and negotiable caps
  - realtime/offline support, determinism, statefulness, seek/flush behaviour
  - clock behaviour and latency
  - OS and GPU APIs
  - isolation modes, permissions and health probe
  - SPDX licence and redistribution profile
  - degradation policy (§4.6)
- **Discovery** scans project, user and system roots, and a lockfile pins digests.
- **Selection** prefers the best measured receipt on this machine. A module without a receipt is presumed broken.
- **Verbs:** `inspect`, `plan`, `doctor`, `license-report`.

### §4.5 Isolation

- **In-process:** trusted, low-latency nodes over a Rust/C ABI.
- **Supervised child process:** engines and GPU workers, over length-framed IPC with shared buffers where they earn it. JSON is control only, never per-pixel payload.
- **External:** FL Studio, OBS, ComfyUI, UVR and StemRoller, connected at asset and control boundaries.
- **GPU work** lives in a restartable worker. A watchdog records adapter, driver, device-removed reason, graph and last node, then degrades to software or bypass rather than retry-looping the driver.

### §4.6 Failure and latency (what all four missed)

- **Degradation is declared per module and port** (Heimdall flip): `on_failure: hold | black | repeat | stall` and `on_device_lost`. Example: the renderer dies mid-song, audio keeps playing, video holds its last frame, the take records the failure, and the supervisor restarts once.
- **GPU handle lifetime protocol** (Heimdall flip, #1): who owns a handle, when it is freed, what a fence means, and what device-removed does to every outstanding handle. Handles do not survive a device reset; consumers receive `Flush(epoch)` and renegotiate.
- **Master-clock failure** (Navi flip, #1). Proposed default, to be drilled:
  1. On audio-device loss, continue on a virtual clock for a bounded hold (500 ms to start) while video holds.
  2. Then pause, with an epoch bump.
  3. On device return, resync with an epoch bump.
- **Dynamic latency compensation** (Sunshine flip) uses a latency query/update protocol and a compensation transaction:
  1. Make the topology change, bounded by an epoch.
  2. Recompute path delays.
  3. Resize queues.
  4. Preroll, then resume.

  Live mode may declare a budget impossible and bypass a node; offline mode compensates exactly.
- **Colour acceptance corpus** (Sunshine flip): limited/full range, SDR/HDR transfer, straight/premultiplied alpha and orientation, checked by pixel oracle rather than by metadata.

### §4.7 Library

Local footage is a first-class source (Navi flip, miss #4). The asset store indexes existing material with fingerprints. `E:\Video Output E` alone holds 89 MP4s (42 GB) of OBS recordings.

## §5 First slices

### Lane A: delight, through what already has a receipt

1. Play a local MP4 from the library with hardware decode (GStreamer D3D12 decoder, with mpv as the player module for transport).
2. Make one loud, planned copy into an existing VFX bench chunk (WebGL2), then send it to the screen.
3. Map the audio envelope to the effect's pulse, and one FL Studio MIDI control (Windows MIDI Services) to its hue.
4. Record every run as a take.
5. Add a GIF overlay and a two-clip sequence, then run a deterministic FFmpeg export that replays the take's automation.

**Acceptance, pre-registered** (Sunshine voice §7, endorsed by Heimdall post-flip):
- A seek or loop bumps the epoch, and no stale frame, feature or control event appears afterwards.
- Thirty minutes of playback stays within 20 ms A/V/control alignment, and measured drift and uncertainty are reported.
- MIDI-to-visible p95 is measured and under 30 ms.
- Hardware decode is proven by negotiated caps and device evidence, not by an `auto` flag.
- Unplugging MIDI or killing the renderer mid-song follows the declared degradation, with no restart storm. The TDR watchdog is read.
- The export differs from the saved take by at most one output frame (one block for audio), with hashes and config recorded.
- The expanded locked graph and the `license-report` are stored with the take.
- A software-decode, no-VFX fallback runs the same project.

### Lane B: native proof, measured in parallel

GStreamer D3D12 hardware decode → a native effect element (wgpu/WGSL or libplacebo, chosen by spike) → D3D12 present.
- Zero-copy must be proven by device evidence.
- Then run a ten-minute stress test and a thirty-minute TDR soak.
- The receipt picks the native renderer card.

### Kill criteria

Stop feature work and repair the contract if any of these happens (Sunshine voice §7, plus Navi's tripwire):
- The same saved graph cannot run live and offline with only declared substitutions.
- An implicit copy or colour conversion is found.
- A tempo edit moves media-timed events.
- Recovery cannot name the failing module and epoch.
- GStreamer vocabulary leaks into `arsenal.graph`.

### Cards after the slices

- stems: GStreamer 1.28's demucs element, or UVR/StemRoller assets
- MilkDrop, via projectM
- Three.js scenes
- Spout/NDI into OBS
- yt-dlp, sandboxed
- OTIO interchange

## §6 For Daniel

1. Approve contract v0: an owned `arsenal.graph` with engines behind it, and GStreamer earning backend roles by receipt.
2. Approve the slice plan: Lane A and Lane B in parallel, with the cards after.

## §7 The reconciler's prior, declared

**Kept from the prior:**
- own the sockets
- measured receipts as the selection rule
- Windows MIDI Services
- the Rust / Python / TypeScript split
- the build order: contract → slices → cards → shells

**Revised by the seats:**
- GStreamer's role, from "spine" to first compile target (Navi, Sunshine, Heimdall)
- the first renderer (Heimdall)
- the clock representation (Navi, Sunshine)
- licences as a compiled property (Sunshine)

**Absent from the prior, adopted from the seats:**
- epoch and `Flush`, plus `ClockMap` uncertainty (Sunshine)
- the `map` gesture, and the bus as a typed producer (Heimdall)
- named mappers, `(clock, position)`, and `Source`/`Sink` (Navi)
- graph-mutation vs realtime-control surfaces (Navi, Sunshine)
- `caps_id` and pressure policies (Sunshine)
- the take ledger as recovery state (Sunshine, Heimdall)
- declared degradation and the handle lifetime protocol (Heimdall)
- the master-clock failure policy and the mode table (Navi)
- dynamic latency compensation and the colour corpus (Sunshine)
- the library as a source, and human vs agent surfaces (Navi)

**Forecast F011** (at least one seat-only element adopted): **hit**.

## §8 Process findings

- **Blob stores are split per worktree (T400).** Sunshine runs from the prod worktree, so it could not see `fences/`, and its long spill landed where `E:\AI-Setup` could not fetch it. Heimdall relayed every design to Sunshine over the bus on its own initiative. Copies were also placed in the prod worktree at 13:20.
- **Answers arrive in kinds that do not wake the requester.** Navi's `note` pointer sat unwoken for 44 minutes (W206). Sunshine found the likely root: the runner's tool door turns a requested `reply` into `chat` (bus 1789320078117-0).
- **An armed seat looked unattended.** Heimdall described claude as unattended while Vandor's harness-tracked listener was armed. This matches the finding that roster and gateway liveness cannot see an armed, idle interactive seat.
