[DESIGN]
# Vandor's prior — media-arsenal-contract

Committed 2026-09-13 BEFORE the fence brief went to any seat. Formed in conversation with Daniel
(session bee0f118) with no seat's input. Only its sha256 goes into the brief; the text is
revealed at reconciliation, so the halves stay blind to it. The reconciler declares this as its
own prior, and every place a half diverges from it is carried verbatim.

## 1. Principle [DESIGN]
**Own the sockets, not every chip.** The freedom Daniel asked for comes from owning the
interfaces: time, types, syntax, discovery, deployment. Every engine plugs in behind them and
can be swapped out. We borrow where decades of hardware work already exist (codecs, hardware
decode, A/V sync, network transport). We build where nothing good exists (our effects, analysis,
MIDI mapping, orchestration). Writing our own hardware decoders would chain us to driver quirks,
which is less freedom, not more.

## 2. The contract [DESIGN]
- **Time.** One exact rational time value (count + rate; 29.97 fps = 30000/1001). Named clock
  domains, every buffer and event stamped, explicit conversion between them: media time (inside
  a stream), the audio device clock (master for A/V sync), display refresh, musical time (bars,
  beats, ticks, tempo map, MIDI clock, Ableton Link), and editorial timeline time. Copy proven
  models rather than invent: GStreamer clock/segments, OpenTimelineIO RationalTime, Link beat time.
- **Types.** Typed ports.
  - A video frame carries size, pixel format, colour (primaries, transfer, matrix, range) and
    its memory domain: CPU, D3D11, D3D12, Vulkan or WebGPU texture.
  - Other port types: audio blocks, control events (MIDI, OSC, automation curves bound to
    parameters), analysis features (spectra, onsets, beats, per-stem envelopes), text and
    subtitles, timelines (OTIO).
  - Connections negotiate and refuse the impossible at connect time, inserting converters or
    uploaders when a legal path exists. This is the VFX bench's typed-port rule, grown up.
- **Syntax.** A text pipeline language for humans and agents, compiling to a canonical JSON
  graph, for example
  `play song.flac | stems | beats | viz milkdrop "preset" | fx orrery bass=stems.drums | out window spout:obs`.
  Every module is self-describing: `inspect <module>` lists ports, types and parameters, so
  agents compose without reading source. Running pipelines accept live edits (swap a node, set
  a parameter).
- **Registry.** Capability labels map to modules, each with MEASURED receipts on this machine
  (throughput, latency, a stability soak). A request names a capability (`decode.hw`) and gets
  the best receipt. Same shape as the house's model routing (`fleet select --capability`). A
  module without a receipt is presumed broken.
- **Deployment.** A module runs in-process (fast) or out-of-process (a crashing shader cannot
  take down playback). GPU frames cross between modules zero-copy via shared handles. The
  Bifrost bus is the control plane, so agents and Discord can deploy pipelines.

## 3. Engines (verified against current docs 2026-09-13) [CERTAIN unless tagged]
- **GStreamer 1.28** as the media spine (LGPL, API/ABI-stable 1.x; 1.28.7 released 2026-09-07).
  - Windows: D3D12 video decoders and d3d12videosink ranked above D3D11 since 1.26.
  - d3d12ipcsink/src: zero-copy GPU memory sharing between processes.
  - webview2src: web content as a source.
  - 1.28 added Vulkan Video AV1/VP9 decode and H.264 encode, a demucs-based audio source
    separation element (Rust), and ML inference elements.
  - It already has a clock, typed caps and a pipeline syntax.
- **FFmpeg**: the long tail of formats, editing and export; inside GStreamer via gst-libav too.
- **mpv**: a player module, not the spine. The libmpv render API defines only
  MPV_RENDER_API_TYPE_OPENGL and _SW. D3D11 and Vulkan render APIs are open feature requests.
- **Effects: WebGPU everywhere.**
  - wgpu natively can import shared D3D12 resources zero-copy via its hal layer (helper crates:
    wgpu_external_frame, grafting).
  - three.js WebGPURenderer has been production-ready since r171, with automatic WebGL2
    fallback; TSL compiles to WGSL and GLSL.
  - GStreamer's only custom-shader element (glshader) is OpenGL, with no general D3D12
    custom-shader element found. So the FIRST CARD WE BUILD is a GPU effect element (Rust +
    wgpu, WGSL), and the same WGSL runs in web views.
- **3D scenes and UI**: three.js in WebView2, fed into pipelines via webview2src. Electron's
  sharedTexture import (experimental) is the alternative bridge if the UI lives in Electron.
- **MilkDrop**: projectM 4.x (the 9,795-preset Cream of the Crop pack is its default), Butterchurn
  for web.
- **MIDI**: Windows MIDI Services, generally available on Windows 11 24H2/25H2. Built-in loopback,
  every endpoint multi-client, MIDI 2.0. The midisrv service is RUNNING on Daniel's machine
  (25H2 build 26200.9168, checked 2026-09-13).
- **Musical time across apps**: Ableton Link, as an optional module (GPL).
- **Timelines**: OpenTimelineIO. **Outputs**: Spout, NDI, hardware encoders. **Fetch**: yt-dlp.

## 4. Licences, languages [DESIGN]
- Our contract and modules stay permissive (Apache-2.0, like the house). LGPL engines are linked
  dynamically. GPL pieces (mpv default build, Ableton Link) are optional out-of-process modules.
  Every door stays open: free, sold or private.
- Rust for the runtime and fast modules (wgpu, gst-plugins-rs). Python as the control plane and
  agent glue. TypeScript for web modules.

## 5. Build order [DESIGN]
1. This fence: the contract.
2. A walking skeleton, one pipeline under one clock and one command: song → stems → beats → our
   WGSL shader with an FL Studio MIDI knob → window + Spout into OBS. It touches the audio clock,
   musical time, MIDI, zero-copy GPU frames and output. Soak it on Daniel's GPU.
3. Grow the cards one at a time, each with a receipt: yt-dlp, projectM, three.js scenes,
   GIF/image layers, OTIO timeline + export.
4. Products are thin shells over the arsenal: the Winamp-style player, the VJ surface, the editor.

## 6. Risks and open questions [INFERRED/UNCERTAIN]
- A single time model is the hardest part.
- GStreamer's caps negotiation has a real learning curve.
- D3D12 → wgpu import goes through hal, which is advanced and version-sensitive.
- This AMD GPU has a display-driver crash history, hence out-of-process isolation and soak receipts.
- Electron sharedTexture is experimental.
- Open: in live mode, which clock is master (audio device vs Link)? Effects inside GStreamer
  elements, or a separate engine process fed by d3d12ipc? Performing-first vs crafting-first
  (Daniel has not chosen; I leaned live because it exercises every hard part).

## Sources
- https://gstreamer.freedesktop.org/releases/1.26/ · https://gstreamer.freedesktop.org/releases/1.28/
- https://gstreamer.freedesktop.org/documentation/d3d12/index.html · https://gstreamer.freedesktop.org/documentation/gl/gstglshader.html
- https://raw.githubusercontent.com/mpv-player/mpv/master/include/mpv/render.h
- https://docs.rs/wgpu-external-frame/latest/wgpu_external_frame/ · https://docs.rs/grafting/latest/grafting/
- https://www.utsubo.com/blog/threejs-2026-what-changed
- https://www.electronjs.org/docs/latest/api/shared-texture
- https://github.com/projectM-visualizer/projectm · https://github.com/jberg/butterchurn
- https://blogs.windows.com/windowsexperience/2026/02/17/making-music-with-midi-just-got-a-real-boost-in-windows-11/
