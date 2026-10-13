---
name: reverse-engineering
description: Use when asked to reverse engineer, teardown, decompile, disassemble, datamine, or "figure out how this works" for a binary, app, game, shader, frame, sound, mix, file format, firmware, device, protocol or capture; when reading a look, effect, economy or upgrade curve off a recording; when extracting synth parameters, stems or an impulse response; when planning a clean-room rebuild; or when scoping what is legal and safe to analyse. Use BEFORE opening any tool or downloading any sample.
---

# Reverse engineering

**Iron Law: every conclusion is labelled OBSERVED, INFERRED or UNKNOWN, tied to an evidence ID,
and carries the boundary of the space you searched.** OBSERVED = you read the bytes, watched the
call, measured the pixels. INFERRED = you reasoned from observations (say how confident, and on
what). UNKNOWN = you have not established it, and that is a finding too. Never let static reading
pose as having watched execution. A name, string, filename or preset label is a lead, not a finding:
confirm it by parsing the resource or watching the behaviour. A negative stays bounded ("no license
string in the 412 functions Ghidra named, searching 6 API names, in build sha256 abc…"), never
"there is none."

**Umbrella:** `.claude/skills/deconstruct/SKILL.md` takes anything apart and routes artifact work here;
go there when the target has nothing to open, or you want the whole picture, not only the mechanism.

## Scope and ethics (read before pointing any tool at anything)

**In scope:** understanding, learning from design, interoperability, analysing software we own or are
permitted to analyse, security research on our own systems, and clean-room rebuilding.

**Never in scope, whatever the target or who asks:** cracking DRM or licence checks; piracy;
cheating in online games; bypassing anti-cheat, anti-tamper or bot detection; unpacking commercial
protectors; making or deploying malware; intruding on systems we do not own; ripping or reusing
another work's assets; reading or writing an online game's memory or traffic. Where a technique is
dual-use, this skill describes it at the level of **understanding** and names the legal line; it
gives no step-by-step for the prohibited uses. When the only way forward crosses one of these lines,
**stop and say so** — do not route around it. (The house instinct is already right: `harvest.js`
stops on a Cloudflare challenge and hands it to a human rather than working around it.)

**Not legal advice.** Every playbook carries a jurisdiction-aware legal note (US DMCA §1201 and its
interoperability/security-research exemptions, which excuse the act of circumvention under their
stated conditions and never tools; *Sega v. Accolade*; *Sony v. Connectix*; EU Software Directive
arts. 5–6 and art. 8, which voids contract terms contrary to art. 6 and art. 5(2)–(3); EULAs and terms
of service; trade secrets; copyright in assets versus unprotected game mechanics; and the
trade-dress/look-and-feel caveat, *Tetris Holding v. Xio*). Anything we intend to ship that was
informed by someone else's product goes past a lawyer first. See `references/method-legal-cleanroom.md`.

## Never on the host

This machine runs with Windows Defender off and updates blocked **by the owner's choice** (do not
argue the posture; `machine-security-posture` memory). That removes the two safety nets that would
normally catch a bad sample or a vulnerable parser, so the rule is firm *because* of the posture.
The rule is one sentence, quoted identically in every playbook that handles a sample:

**Never on the host:** "An untrusted sample (any file under study that the house did not build or record itself, unless Daniel has ruled that kind of file trusted) is never run, parsed, decoded or extracted on this machine: it is handled only inside a disposable VM or sandbox that is reverted afterwards, and it is kept outside the repo."

- **What it covers.** Binaries, installers, firmware, documents, archives, captures, and video, image
  or audio files from outside the house. The parser is attack surface, not just the sample (binwalk's
  CVE-2022-4510 ran code on *extraction*; a media decoder is the same risk), so opening an untrusted
  file in ImHex, `arsenal.media probe` or any decoder is VM work. Hashing a file on intake is not
  parsing. Reading plain source text as text is reading; building, installing or running it is
  execution.
- **Host changes are Daniel's decision, never an ordinary step.** Enabling Windows Sandbox or
  Hyper-V, creating or importing a VM, installing any tool, package or driver (Ghidra and a JDK,
  Wireshark, mitmproxy, USBPcap, a Zadig/WinUSB driver swap, any pip or npm package — `npx <package>`
  downloads and runs one), adding a certificate to any trust store, enabling USB debugging on a
  device, or changing any other security setting. Every playbook writes such a step as
  **Daniel's decision:** and the work stops there until he has ruled.
- **No disposable VM or sandbox is enabled today** (Windows Sandbox present but off; Hyper-V off; WSL
  and Docker are *not* sandboxes — WSL mounts C:/E: and launches Windows programs, Docker hosts
  `akashic-redis`). **Daniel's decision:** enabling one. Until then, this work is limited to **static
  reading of files we built or trust** and **browser-hosted practice grounds**.
- **Do not run or wrap Universal Extractor 2.** It sits in `%USERPROFILE%\Desktop\unorg desktop\`
  (`research/reviewed/reverse-engineering-2026-10-13/house-inventory.md`, "Third-party tools found by
  name"): provenance unverified, a bundle of third-party binaries, and parts of it exist to unpack
  protected executables and decrypt game archives. Never route work to it.
- **Keep samples out of the repo, and remember the repo is public.** Untrusted binaries, extracted
  assets, captures, other people's frames, downloaded datasets and models live outside `E:\AI-Setup`
  (not on the X:\ ramdisk — that is logs/temp only), hashed on intake, deleted when the study ends.
  Decompiler output, disassembly, third-party code and target excerpts never go into a tracked file
  (`fences/` is tracked and public, as are `research/`, `docs/`, `.claude/` and `tests/`); cite
  private evidence by path and hash instead.
- **`state/` is not uniformly private.** `.gitignore` re-includes `state/coord/**`, `state/drills/**`,
  `state/rewrites/`, `state/authorship/` and named files under `state/ci/`. In particular
  `state/coord/web_fetch_receipts.jsonl` records every URL the house web door fetches and is one
  `git add -A` away from publishing target URLs (house-inventory finding F2). After case work, stage
  files by name, never `git add -A` or `git add .`. Case files, ledgers and recordings (Daniel's own
  included) go in **`state/re/<case>/`**, which `state/*` ignores; confirm a new path with
  `git check-ignore -v <path>` before writing to it.
- **Static-first is a safety feature, not just a method.** Reading bytes never executes the target,
  but the reader can still be exploited, so static reading of an untrusted sample is VM work too.
  Prefer static; escalate to dynamic only when a question truly needs runtime evidence, and only in
  the VM.

## Clean-room rebuild, in brief (how we build on what we learn, lawfully)

Copyright protects **expression** (code, art, audio, text — including the written text of a game's
rules — and the specific look-and-feel), never the **idea, method or function** (in the US, 17 U.S.C.
102(b); a game's method of play is free). The wall keeps the two apart so a rebuild is provably
independent:

1. **Dirty side** studies the original (lawfully; static/dynamic) and writes a **functional
   specification** in plain language — numbers, timings, structure, with every line tagged OBSERVED —
   and no code, assets or distinctive expression.
2. **A third party reviews it for expression before it crosses** — a different seat from the one
   that wrote it, or Daniel — and strips anything that is expression rather than behaviour; every
   crossing is logged (hash, from, to, reviewer).
3. **Clean side** — a seat that never saw the original — builds from the spec alone.

**On this host a fresh session is not a separate room.** Boot, the session-start whisper and the
recall hooks inject shared lessons, notes, handoffs and Bifrost mail into every session, and the
auto-memory loads into every Claude session, so a dirty finding on any of those planes reaches the
"fresh" implementer by itself. The house rules, in full in `references/method-legal-cleanroom.md`:

- **Dirty-side findings live only in the private case folder `state/re/<case>/`** — never in `learn`,
  `note`, `handoff`, `log`, the Bifrost bus, the auto-memory, a commit message, a message to another
  session or any tracked file. Dirty seats also switch off the hooks that report to shared planes by
  themselves (`AKASHIC_SESSION_SIGNALS`, `AKASHIC_TRACE`, `AKASHIC_TOUCH` and
  `AKASHIC_RECALL_AT_ACTION` set to `0`) and the harness's own auto-memory
  (`CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` in the launching shell), which can otherwise write to the one
  memory folder every session shares.
- **The implementer is a separate agent id, in a CLI session set up for it (never the desktop
  app):** launched from its own folder outside the repo and the home folder, whose settings give it
  its own id, the auto-memory off (`"autoMemoryEnabled": false` plus
  `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1`; otherwise the shared memory index loads into its first turn),
  the trial database (`REDIS_DB=15`) **and** a throwaway data root (`AI_SETUP=<an empty folder outside
  the repo>` plus the house's isolation flags; `REDIS_DB` alone isolates Redis, while the store also
  writes to a file tier that is otherwise the house's own), and the hooks off. It runs **no house verb
  at all** (not even `boot` or `recall`) and gets **no akashic MCP door** (a door on the trial
  database still serves the eye, the transcript archive and the web), no web, no tools that list or
  message other sessions, and deny rules on whole roots: the repo and its clones, the transcript
  archive, `%USERPROFILE%\.claude` and the Temp folder.
- **The isolation is verified, not assumed, and the settings are not a wall:** before the
  specification crosses, the monitor checks the first turn for any case term or auto-memory block,
  checks the tool list, and confirms a read of each denied root is refused; at the end it audits the
  whole transcript for any access outside the build folder, any house root or verb, any web use and
  any message from another session. A shell can still read any file, and no setting was found that
  stops another session sending the clean seat a message, so the audit, not the settings, shows what
  it saw.
- **Only the functional specification crosses**, after the third-party review above.
- **Daniel has seen the original and directs the build**, so his direction to the implementer is
  given as mechanics, numbers and feel in words — never as reference images, footage or assets of the
  original — and is logged as a crossing.
- **A taint register records who saw what**, and the clean seat is never given read access to it.

Prefer a spec written **as conformance tests** (Wine's method): they say exactly when the rebuild is
done. Caveat with teeth: a model's training data may already contain a well-known project's source,
so even an isolated session is not automatically clean — **claim "clean room" only with the logs to
prove it, and never rebuild a known open-source project to relicense it.** For a game, mechanics are
free to reimplement; art, audio, text, UI and distinctive presentation are not. Full protocol:
`references/method-legal-cleanroom.md`.

## When someone says… (route it, in ten seconds)

| Someone says | First move | Playbook |
|---|---|---|
| "reverse engineer this .exe / .dll / binary" | Identify the tier first (managed→near-source decompile; native+metadata→pseudocode; stripped→infer): one `diec`/PE-header/magic check decides the whole workflow. A binary we did not build is an untrusted sample: VM for parsing it, and for anything that runs. | software-binaries |
| "it's an Electron / desktop JS app" | It is almost never compiled: `asar extract`, look for `.map` source maps (that *is* the source). Our own app on the host; an outside app is an untrusted sample (VM). Defeating integrity fuses is circumvention — stop. | software-binaries, web-apps-protocols-ux |
| "what's inside this save / game file / unknown format?" | Entropy scan to find text/code vs opaque regions, then walk the chunks; the declared length landing on the next record is the falsifiable test. Capture it as a Kaitai `.ksy`. | software-binaries |
| "how does this game's loop / economy / upgrade path work?" | No code: play and record on our own account (record only, measure offline afterwards), read store pages, patch notes, wikis (dated), talks; model the faucets, sinks and curves. Terms like Habby's forbid opening the client. | games-design-teardown, archero-design-seed |
| "how did they make this look / effect?" | Author's talk first, then measure our own recording: decode the display transform to light before any falloff/bloom/motion number, calibrate the ruler on a look we built. Frame-debug only our own pages. | graphics-vfx |
| "what synth / sound / room is this?" / "extract the stems" | Route by shape — sound, space, mix, passage. Closed loop: analyse, re-make, compare with a stated distance; run it first on a known target. Stems are estimates, not the multitrack. | audio-music |
| "capture / read this web app's traffic or bundle" | Our own pages and open-source apps only; CDP/HAR for behaviour, source maps or webcrack/wakaru for structure (not original names). No credentialed sessions of others' services. | web-apps-protocols-ux |
| "read this device / MIDI / USB / firmware / radio" | Read what the device already publishes (USB descriptors, MIDI Identity Request, vendor files) first; sniff second; open firmware last, VM only. Receive-only on radio; never transmit. | hardware-firmware-signals |
| "help us get good at this" / "set up practice" | Pick a ground built to be reversed (our own compiled code, crackmes.one, Flare-On archives, OST2, Compiler Explorer); predict-before-look; one question per session. | practice-and-learning-path |
| "my app" with no name | **Ask which.** Paths in saved reports and test fixtures do not select the target, and choosing the target is the asker's job, not ours. | all |
| "build us the archero-style game" | A future project. Study mechanics freely; investment on the player not the item, weapons as sidegrades on one power budget, randomness in the run not the meta, effects as data. | archero-design-seed |

## The universal method

1. **Permission and scope first.** Is the target ours, open source, built for practice, or something
   we are licensed to examine? Read the EULA/terms. Unclear → stop and ask Daniel. The person asking
   picks the target; we do not pick one for them.
2. **Write the question checklist**, each question beside the evidence that would answer it. "How does
   the upgrade path work?" is not a task; "which function reads the save's `level` field, and what
   writes it?" is. Revisit it at the end; mark each answered / partial / unresolved; never call a
   broad investigation complete while a required question is open.
3. **Fingerprint the target.** SHA-256, size, version, where it came from, tool versions. Without this
   nothing is reproducible.
4. **Route the target, then start summary-first.** Pick the first tool from *what the artifact is*
   (the routing table below), not from habit. Overview or inventory before drilling — the export
   table often answers the question before you decompile 30,000 functions.
5. **Static before dynamic.** Reading bytes/pixels/samples answers "what can it do" and never executes
   the target; dynamic answers "what it actually did" and triggers the VM rule and the legal rule.
   Escalate only when static genuinely cannot answer.
6. **Inspect resources and configuration alongside code.** Behaviour lives in data (cost tables,
   shader params, presets, manifests). Parse the real resource with a format-aware tool; never infer
   behaviour from a name. A finding earns OBSERVED only from a falsifiable check (the chunk length
   lands on the next record; the byte-rate equals rate×channels×bits/8).
7. **Corroborate with the evidence type the claim needs** — a static read of a branch is not proof it
   runs; a measurement of runtime behaviour is not a source dump. Pair static and dynamic; they check
   each other.
8. **Cache by content hash; rerun an analysis only when one of its inputs has changed.** If a probe,
   search or decompile returned nothing useful, change the input, resolve the blocker, or record it as
   a bounded negative — rerunning it unchanged is wasted tokens.
9. **Keep a finding ledger** — each claim linked to its evidence ID, kind (O/I/U), likelihood (one
   fixed scale) and confidence, search boundary and what is still open. This is the skill; the disassembler is
   the easy part.
10. **Revisit the checklist** and mark each question's state honestly.
11. **When rebuilding, separate observed behaviour from design choice.** "The original *does* X"
    (observed) stays in a different column from "we *choose* Y" (our design). The clean-room wall sits
    exactly on that line.

## Master routing table

Artifact or question → first house verb or tool → evidence it yields → what it cannot tell you.
House verbs are named where they exist; external tools otherwise (none are installed on this host
today — see the inventory and each playbook's gap list; **Daniel's decision:** installing any of
them). Every row obeys the never-on-host rule. A row marked **(VM)** is VM-only whatever the file. A
row marked **(trusted on host; untrusted → VM)** runs on the host only for files we built or recorded, or that
Daniel has ruled trusted; any other file goes to the VM. Unmarked rows touch no outside sample (our
own pages and devices, public documents read as text).

| Artifact or question | First tool | Evidence it yields | What it cannot tell you |
|---|---|---|---|
| Any unknown file, first contact (trusted on host; untrusted → VM) | `diec` (Detect It Easy) + a sliding-window entropy scan; `py agent_cli.py find` to locate by name | File type, compiler, packer, tier; where opaque regions sit | Behaviour; names if stripped/packed |
| "Is this .NET or native?" (trusted on host; untrusted → VM) | PE parse: CLI header (data-dir index 14) / `BSJB` vs none | Managed→Tier 1 (ILSpy); native→Tier 2/3 (Ghidra) | How good the decompile is until you run it |
| Windows `.exe`/`.dll`, native (VM) | Ghidra (headless `-readOnly` or GUI) | Disassembly, pseudocode, imports/exports, strings | Runtime values; which branch real input takes |
| .NET assembly / Unity Mono (trusted on host; untrusted → VM) | ILSpy / `ilspycmd`; dnSpyEx to debug (VM) | Near-original C#, type/method names | Values behind runtime config; a third party's IL2CPP or protected build is out of scope (our own builds have source) |
| Android `.apk` / `.dex` (VM) | JADX | Java source, manifest, resources, strings | Native `.so` logic (→ Ghidra); server behaviour |
| PyInstaller `.exe` (VM) | pyinstxtractor → pycdc/uncompyle6 | `.pyc` then Python source | 3.11+ complex control flow (treat as INFERRED) |
| Electron desktop app (trusted on host; untrusted → VM) | `@electron/asar` list/extract; `@electron/fuses read` | App JS/TS, package.json, source maps, fuse state | Minified names a minifier destroyed; native modules |
| Minified/bundled JS, has `.map` | read the source map (`sourcesContent`) | The original source, directly | Nothing — you have the source |
| Minified/bundled JS, no map (trusted on host; untrusted → VM) | webcrack / wakaru | Un-minified, un-bundled modules; readable structure | Original identifier names (gone at minify) |
| `.wasm` module (VM) | `wasm-objdump -h` → `wasm2wat` → `wasm-decompile` | Sections, imports/exports, WAT, C-like pseudocode | Original source (optimised away); stripped names |
| Unknown binary / save format (trusted on host; untrusted → VM) | ImHex (entropy + Pattern Language); binwalk for blobs, always (VM) | Structure, chunk boundaries, opaque payload locations | Meaning of a field without diffing/behaviour |
| "Document a format for the house" | Kaitai Struct `.ksy` | A parser in 12 languages + the spec, one artifact | Semantics you have not yet reverse engineered |
| "What can this binary do?" (capabilities) | capa (VM) | Capabilities mapped to MITRE ATT&CK | Whether it did them at runtime |
| "What changed between v1 and v2?" | BinDiff / Diaphora (VM) | Per-function matched/changed/new | Why it changed; intent |
| "Where does this app store data?" (ours) | Process Monitor | Exact file/registry paths, access patterns | Why; the on-disk format (→ ImHex/Kaitai) |
| "What APIs does our app call, with what args?" | API Monitor / Frida Interceptor (ours, VM) | Live API/COM calls, parameters, returns | Paths you did not exercise (no negative proof) |
| "Walk this bug backward to its cause" (ours) | WinDbg + Time Travel Debugging (VM) | Reversible, queryable execution trace | Kernel mode; PPL; altering history |
| Firmware image (VM) | binwalk `-E` then `-e`; unblob | Embedded filesystems/kernels/blobs, entropy map | Logic inside extracted binaries (→ Ghidra); encrypted parts |
| Our own WebGL page: "what does this frame do?" | Spector.js (dev browser; later a headless SwiftShader lane) | Every GL call with state, shaders as compiled, textures, targets, draw/instance counts | GPU timing; how Daniel's real GPU rounds/orders |
| Our own WebGPU page | WebGPU Inspector | Objects, frame capture, frame times | Native-driver behaviour |
| Our own native/engine build (Daniel's GPU call) | RenderDoc; PIX / Radeon GPU Profiler for timing | Event list, pipeline state, every target, overdraw, pixel history, shader debug | Real timing from replay; CPU-side logic |
| Shader source we own or may study (GLSL, Shadertoy JSON) | `py -m arsenal shader dissect --atlas` | Techniques with file:line evidence + confidence, cost, dead code, atlas parts | How it looks in motion (use `render`/`filmstrip`); runtime-only bugs |
| A video of an effect or game (trusted on host; untrusted → VM) | `py -m arsenal.media probe`, then `grab --sheet` / `shots`, `py -m arsenal storyboard`/`motion` | Frame rate, range, cuts, contact sheets, pacing | Anything above the clip; hidden passes; exact internal params |
| A still: "what palette / grade?" (trusted on host; untrusted → VM) | OKLab k-means + tone statistics (future `look` verb) | Palette shares, black/white points, tint by lightness band, saturation curve | The grade operator; HDR values above clip |
| A grade from a pipeline we can run | Identity Hald CLUT through it (FFmpeg `haldclutsrc`) | The exact per-pixel transform as a LUT | Spatial effects (position + neighbour tests flag them) |
| Bloom in a frame (trusted on host; untrusted → VM) | Radial profile in decoded light; for our build, the float bloom target | Presence, whether unclipped emitters bloom, tail shape, radii | Threshold value / strength from an 8-bit frame (biased) |
| Particle counts | Connected components (low) + local maxima (high), from our frames | A bracket on the count and its trend | An exact count under heavy additive overlap |
| Hit-stop / screen shake (trusted on host; untrusted → VM) | Blurred structural frame difference; phase correlation after removing moving foreground | Held frames; per-frame camera offset, amplitude, decay | Intent; shake with no static world in view |
| A game's design loop / economy / upgrade curve | Our own recording + `arsenal.media grab/shots`; store pages, patch notes, wikis (dated), GDC talks | Observed actions, rhythm, offers, prices, reported numbers | Server tables, true drop rates, designer intent |
| Drop rate / gacha odds | Published odds disclosure; our own tally with a Wilson interval | Published odds, or an honest interval | Undisclosed pity rules; silent server changes |
| Which engine / SDKs (a game we own or a Steam title) | Licences/credits screen; SteamDB tech (file names only); PCGamingWiki | Named signals with strength and date | Certainty; per-version changes; an ads SDK is not the engine |
| An unknown audio file: what is it, what happened to it? (trusted on host; untrusted → VM) | `py -m arsenal.media probe` then `audio` (loudness) | Container, codec, rate, tracks, LUFS/LRA/TP | Provenance; encoding history (next row) |
| "Is this really lossless?" (trusted on host; untrusted → VM) | Long-term spectrum / spectrogram | Brick-wall cutoff, empty bands, bit-depth use | Which encoder exactly (a fingerprint, not proof) |
| A single synth/instrument note (trusted on host; untrusted → VM) | pYIN + harmonic table + RMS envelope (librosa) | f0, harmonic pattern, filter shape, ADSR, noise share | The product/preset; whether a matching patch is the original |
| A room / speaker / static effect we own | Exponential sweep + deconvolution (REW) | IR, RT60/EDT, frequency response, reflection times | Time-variant or level-dependent behaviour |
| A finished mix: what are the parts? (trusted on host; untrusted → VM) | Demucs / BS-RoFormer on CPU | Estimated stems for listening | The real multitracks; parts' true EQ/levels |
| A melody / passage (have MIDI?) (trusted on host; untrusted → VM) | MIDI → `py -m arsenal.practice`, `pianocue voicing`; else Basic Pitch / Kong / Transkun | Notes, timing, chords, key, voicings | Spelling, hands, pedal (most models), meter under rubato |
| A game's adaptive music / feedback SFX | Own play recorded music-only and SFX-only via the game's sliders + beat/onset analysis | Which states change the music, variation, priority, ducking | Authored rules/values; branches never triggered |
| A plugged-in device: what is it, which driver? | `Get-PnpDevice` / `Get-PnpDeviceProperty` | VID, PID, revision, compatible IDs, driver | Message formats; interfaces a vendor driver hides |
| "What does this USB device say it is?" | USBView `/q /f /saveall:` (installed) or UsbTreeView | Device/config/interface/endpoint descriptors, strings | Runtime behaviour; viewer labels are inferences — re-decode raw bytes |
| "What messages does this instrument send?" | MIDI monitor (Windows MIDI Services, MIDI-OX, ReceiveMIDI) | Timestamped messages, SysEx bytes | What another app sends *to* it; USB control traffic |
| "Who is this MIDI device / which firmware?" | Universal Identity Request `F0 7E 7F 06 01 F7` (Daniel's go, nothing running) | Manufacturer ID, family, member, revision | Vendor-specific behaviour; silent devices |
| Our own app's network traffic | `pktmon` (built in) on our own client; Wireshark/mitmproxy are installs (**Daniel's decision**); TLS interception only in the VM, or by trusting the proxy's certificate for our own client process alone (`NODE_EXTRA_CA_CERTS` / `SSL_CERT_FILE`), never in a host certificate store | Message vocabulary and sequences | Others' traffic (out of scope); rare paths not exercised |
| A wire / header / test pad on a board we own | Multimeter, then logic analyser + sigrok (`uart`,`i2c`,`spi`,`midi`…) | Edges, timing, decoded bytes | Analogue faults; anything faster than ~1/4 the sample rate |
| A radio device we own | Label/FCC ID, then SDR++ waterfall, `rtl_433`, inspectrum/URH (receive only) | Frequency, modulation, symbol timing, decoded fields | Encrypted payloads; others' traffic is off-limits; never transmit |
| "Is this region compressed or encrypted?" (trusted on host; untrusted → VM) | Signature scan **and** entropy together | Header present → unpackable; no header + ~8 bits/byte → unknown | Entropy alone never answers it |
| "Is our rebuild equivalent?" | Conformance / differential tests (Wine/Samba method) | Every mismatch inside the tested domain | Equivalence outside the sampled domain |
| "Can I legally do this?" | `references/method-legal-cleanroom.md`, then a lawyer for anything commercial | Orientation by jurisdiction | Legal advice |

## Red-flag phrases (each one means STOP)

- "Just decompile it and we're done" (decompiler output is an INFERENCE from one tool; corroborate)
- "The function is called `validateLicense`, so…" (a name is a lead, never a finding)
- "I'll run the sample to see what it does" (VM only; never on this host)
- "It's fine, it's just a small binary / firmware / mod" (into the VM, out of the repo)
- "The curve is ×1.15, so level 40 costs…" (ten points prove nothing outside their range; a soft cap hid in Drill B — 2.7× wrong)
- "There's no telemetry / no network call" (bound it: searched what, how, in which build)
- "Let's just use their art as a placeholder" (assets are the one thing copyright protects; the licence line catches it)
- "We only need to get past the licence check / DRM / anti-cheat" (out of scope — stop, do not route around)
- "We can rebuild this open-source lib and relicense it" (a model that has seen the source is not a clean room)
- "I'll save this finding with `learn` / leave it in the handoff" during a case (dirty findings stay in `state/re/<case>/`; shared memory reaches the clean seat)
- "Here's a screenshot of the original so the implementer gets the feel" (direction crosses as words, numbers and feel only, logged)
- "Just trust the mitmproxy certificate on the machine" (**Daniel's decision**; trust it per process or work in the VM)
- "The spectral distance is low, so the patch is right" (a 56% decay error barely moved it; check envelopes separately)
- "Same picture / same number twice" (cache by content hash; a rerun with no changed input teaches nothing)

## Why this feeds the loop

The house already practises most of this discipline per subsystem — fence verdict tags
(CERTAIN/DESIGN/INFERRED/UNCERTAIN), `ask --preset findings`, every `arsenal.media` result's `blind`
field, `eye trace` edges labelled recorded/derived/inferred, `forecast`'s mandatory "dies when",
`tests/test_find_bounded_is_not_absent.py`. What it lacked was one evidence discipline that spans
domains and routes any target. That is this skill. The gaps each playbook names (a disposable VM, a
read-only triage router, a target-shaped case ledger, the clean-room wall generalised) are build
proposals for Daniel's or Vandor's ruling, not things done here.

## Credit

The evidence discipline this skill is built on, restated here in our own words, we learned from
the **REA skill by morluto** (`morluto/rea`, https://github.com/morluto/rea, MIT): keep what was
seen apart from what was reasoned and from what is still open, each tied to an evidence ID; decide
what the target is before choosing a tool; take the overview before the detail; rerun an analysis
only when an input changed; read the data and settings beside the code instead of trusting names;
keep a finding ledger with confidence and the edge of the search; close the question list at the
end; in a rebuild, keep what the original does apart from what we choose; keep every negative
bounded; and let the person asking pick the target. We adopted its habits of mind, in our
own words, not its server machinery. Where REA's MCP tooling (its Ghidra/IDA/JADX/firmware/capture
routes) would help later, it is a clean fit and credited there. Tool and technique authors are
credited by name in each playbook.

## The playbooks

- `references/method-legal-cleanroom.md` — the discipline, the legal map, the clean-room protocol, host safety
- `references/software-binaries.md` — native, managed, Electron/JS, WASM, file formats
- `references/games-design-teardown.md` — design teardown from play and public sources, no code
- `references/graphics-vfx.md` — frames, looks, effects, the shader-school bench
- `references/audio-music.md` — sounds, spaces, mixes, passages, game audio
- `references/web-apps-protocols-ux.md` — web apps, bundles, CDP/HAR, protocols, interaction
- `references/hardware-firmware-signals.md` — MIDI, USB, logic analysers, firmware, radio
- `references/practice-and-learning-path.md` — practice grounds, note formats, a twelve-week path
- `references/archero-design-seed.md` — a seed for Daniel's future game (not a plan)
