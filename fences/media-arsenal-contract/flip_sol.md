[DESIGN] Sunshine flip — media-arsenal-contract

I read the other designs through the sealed bodies relayed from their authors (my production worktree does not contain the fence directory). My view changes in one important place.

## What I adopt

**From Vandor, §3: GStreamer 1.28 deserves to move from my “evaluate later” list to the leading candidate for the live media spine.** The concrete current facts Vandor supplied — Windows D3D12 decode/presentation, `d3d12ipcsink/src` for cross-process GPU sharing, WebView2 as a source, a mature clock/caps scheduler, and stable 1.x API/ABI — answer several hard seams I had left for us to build. I would retain my engine-neutral `arsenal.graph` as the public/save format, compile its live subgraphs to GStreamer, and use FFmpeg for long-tail/export plus mpv as the player module. This is adoption, not coronation: first measure D3D11/D3D12 interop, driver removal, seek/flush, colour correctness and 30-minute TDR behavior on Daniel’s AMD host.

**From Navi, §§2–3: distinguish pullable streams from packets and make scheduling demand-driven for media.** My design typed frames/blocks and specified backpressure, but did not promote `stream.audio` / `stream.video`—a pullable source with caps—to a first-class type. That is better. Presentation/audio demand should pull media through bounded queues; control, MIDI and faults remain timestamped push events. This avoids making every edge a firehose and makes seek/offline render much cleaner.

**From Heimdall, V6: one visible control verb.** My `bindings` model had the semantics but not the memorable user law. `map <producer> -> <target>` should be the common gesture for MIDI, FFT/features, automation and Bifrost, with typed units and explicit merge precedence under it.

**From both Heimdall V5 and Navi’s editor-as-ledger section:** make the editor explicitly a projection/mutation surface over the same immutable sequence/EDL ledger, not merely “an EDL input” as I wrote. That connects editing, takes and agent mutations into one provenance model.

## Where I still disagree

1. **Heimdall V1 (“exactly one canonical clock … every other clock … never a peer”) is too strong.** One exact timeline coordinate is useful, but the audio device, display, QPC/MIDI and source clocks are independent oscillators. Calling them derived does not remove drift, jitter, discontinuity or observation error. Keep canonical rational time for documents/events, but runtime clocks remain named peers connected by measured affine maps with uncertainty. Live audio may be elected master; offline virtual time may be elected master. Election is not ontology.

2. **Heimdall V4 (“one GPU context, never multiplied”) should be a host policy and acceptance result, not a protocol law.** A D3D12 decoder, WebView2/WebGL renderer and offline Vulkan worker cannot honestly be represented as one universal context. Start with one live GPU device/context family because this machine’s TDR history warrants it; permit explicit cross-process/device edges and add another only after the stress gate. The type system must describe reality even when policy forbids a topology.

3. **Heimdall V3’s “Resource token stays on device” is the preferred path, not the only valid type.** Preview thumbnails, analysis, browser ingress, software fallback and recovery sometimes require a CPU copy. The invariant should be: every copy/conversion is an explicit planned node with cost and colour semantics. Zero-copy is earned and observed, never inferred from an opaque token.

4. **Navi §1’s fixed canonical microsecond is unnecessary and can invite rounding at frame/sample boundaries.** Her insistence on `(clock-id, position)` is right; represent position as integer ticks plus an exact rational time base. Then 30000/1001 video and 48 kHz audio remain native and exact. A rational number of microseconds is mathematically workable, but the fixed unit buys nothing.

5. **Vandor §3: GStreamer’s own launch syntax must not become Daniel’s durable project contract.** It is an excellent execution backend, but engine-specific element names/properties would bind saved projects to today’s spine. `arsenal.graph` should compile to a pinned GStreamer plan and retain an escape-hatch native node; the stored semantic graph stays portable.

6. **Heimdall V9’s wording that libmpv is an LGPL engine is unsafe as a default.** mpv is GPL-2.0-or-later by default; LGPL mode is a constrained build configuration. Licence profile must derive from the exact binary/configuration, not the library name. Process isolation is not a legal magic wand.

## What I change in my own design

- Make **GStreamer the first live-backend spike**, not a later capture/broadcast option.
- Add first-class `stream.*` capability objects and split scheduling: pull media, push control/fault events.
- Make the sequence ledger the authoritative editable document and takes immutable snapshots/events over it.
- Reduce the first slice: GStreamer hardware decode -> native shader/compositor -> present, audio envelope -> `map` -> shader, with mpv transport/player behavior as a module. Add GIF/MIDI/export immediately after the zero-copy/clock/TDR proof instead of requiring every feature to pass before the contract can be judged.
- Preserve my exact memory-domain descriptors, clock-map uncertainty, explicit conversion-cost plan, epoch-on-seek, lockfile/digests and compiled SPDX report; the other designs reinforce rather than replace those.

## What all four missed or underweighted

**Dynamic latency compensation is not just manifest metadata.** FFT windows, look-ahead limiters, source separation, GPU queues, Bluetooth/audio devices and AI modules can add or change delay while running. The runtime needs a latency-query/update protocol and a compensation transaction: pause or epoch-bound the topology change, recompute path delays, resize queues, preroll, then resume. In live mode it may declare a latency budget impossible and bypass a node; offline it compensates exactly. Without this, typed time stamps can all be “correct” while audio-reactive visuals and MIDI feel visibly late.

Also add one early colour acceptance corpus: limited/full range, SDR/HDR transfer, alpha straight/premultiplied and orientation. All four carried colour metadata, but metadata without known pixel-oracle tests still permits a perfectly typed wrong picture.

**Net:** I now favor an engine-neutral Arsenal contract compiled primarily onto GStreamer 1.28, with mpv as the loved player surface/module and FFmpeg as transform/export. The narrow waist remains exact timed types, explicit memory/copies, one control mapping gesture, and a reproducible sequence/take ledger.
