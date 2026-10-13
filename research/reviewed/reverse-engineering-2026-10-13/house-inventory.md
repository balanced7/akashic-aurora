# Reverse engineering, 2026-10-13: what the house already has, and what a full arsenal still lacks

Daniel, 2026-10-13, asked that the house learn to reverse engineer anything ("I want us to have the whole reverse
engineering arsenal"), with an Archero-style game in mind for later: a fair upgrade path, and new weapons and effects
released for free. The trigger was the REA skill by **morluto** (https://github.com/morluto/rea, file
`.agents/skills/reverse-engineer-anything/SKILL.md`). Vandor's reading of it: adopt REA's *discipline*, not its server
machinery. This file is the first step: an inventory, read-only, of every tool, verb and module the house already has
that serves reverse engineering, followed by the gap list.

**How this was made.** Everything below was read or run on this machine on 2026-10-13, read-only. Commands that were
run: `py -m arsenal.media` (verb list), `py -m arsenal.media doctor` (no `--save`), the shader CLI's help, `py agent_cli.py
discover` and `-h` on sixteen verbs, `py -m arsenal.practice -h`, `py -m arsenal.pianocue -h`, `py agent_cli.py find` for
about forty tool names, a Python `find_spec` sweep over sixty packages plus a `shutil.which` sweep over forty executables
(located, never executed), `Test-Path` on a few Windows components, read-only git (`check-ignore`, `ls-files`,
`status --porcelain`), and `py agent_cli.py web fetch` on the source URLs in section 9. Nothing was installed, started,
rendered, or committed. No browser was driven, no GPU was used, port 8793 was not touched, and no file outside this one
was written in the repo.

**Evidence tags used in this file** (the REA habit of separating observation from inference, in the house's own words):

- **[ran]** I executed it today and saw the output.
- **[read]** stated in the module's own docstring or code, read today. Numbers in a [read] row are that module's own
  measurements, not re-measured here.
- **[found]** located on disk today (Everything index or `Test-Path`), not executed.
- **[inferred]** my reading of the evidence, not directly observed.
- **[unknown]** not resolved by anything I looked at.

---

## 1. The boundaries this file keeps

**Scope.** The arsenal is for understanding, learning from design, interoperability, analysing software we own or are
permitted to analyse, security research on our own systems, and clean-room rebuilding. It is not for cracking DRM or
licence checks, piracy, cheating in online games, bypassing anti-cheat or anti-tamper, making or deploying malware, or
getting into systems we do not own. Where a gap below names a dual-use tool, it is named at the level of what it is for,
with the boundary beside it.

**Host safety.** This machine runs with Windows Defender off and updates blocked, by the owner's choice (the posture is
not argued here). So: any work that touches an untrusted binary, firmware image, document or capture happens inside a
disposable VM or sandbox. Untrusted code never runs on the host. Samples never enter the repository. Section 5 records
that the machine has no such disposable environment enabled today; that is gap G1.

**Legal note (not legal advice).** Reverse engineering law depends on where you are and what you agreed to.

- *United States.* 17 U.S.C. 1201 forbids circumventing access controls, with narrow carve-outs: 1201(f) for
  interoperability of an independently created program, 1201(j) for security testing, and the Copyright Office's
  triennial exemptions (37 C.F.R. 201.40, which include good-faith security research). Courts have held disassembly for
  interoperability can be fair use: *Sega v. Accolade*, 977 F.2d 1510 (9th Cir. 1992), and *Sony v. Connectix*, 203 F.3d
  596 (9th Cir. 2000). Contracts can still forbid it: a EULA or terms of service that bans reverse engineering has been
  enforced (*Bowers v. Baystate*, 320 F.3d 1317 (Fed. Cir. 2003); *Davidson & Associates v. Jung*, 422 F.3d 630 (8th Cir.
  2005)). Trade-secret law treats reverse engineering of a lawfully obtained product as a proper means (18 U.S.C.
  1839(6)(B)), unless a contract says otherwise.
- *European Union.* The Software Directive 2009/24/EC lets a lawful user observe, study and test a program (art. 5(3))
  and decompile it only for interoperability, under conditions (art. 6). The Trade Secrets Directive (EU) 2016/943 art.
  3(1)(b) allows reverse engineering of a lawfully acquired product unless lawfully restricted by contract.
- *Games specifically.* Game mechanics and rules are ideas and are not protected by copyright (17 U.S.C. 102(b)); code,
  art, audio, text and other assets are. The look and feel can still be protected expression: *Tetris Holding v. Xio
  Interactive*, 863 F. Supp. 2d 394 (D.N.J. 2012), found infringement in a clone that copied Tetris's visual expression
  even though the rules were free to use. An "Archero-style" game is safe ground at the level of mechanics and economy;
  copying a specific game's assets, screens or distinctive presentation is not.

---

## 2. The discipline, and where the house already practises it

REA's working method, restated in our words, beside the house organ that already does the same thing. Short quotes from
the skill are marked as quotes; the rest is paraphrase.

| REA's habit (our words) | Where the house already does it | What is missing |
|---|---|---|
| Every conclusion is an observation, an inference or an unknown, and cites its evidence | Fence verdict tags CERTAIN / DESIGN / INFERRED / UNCERTAIN, checked at seal time (`core/coord/fence_workspace.py`, method M1-CF) [read]; `ask --preset findings` forces FINDINGS / REASONING / CHECK / BLIND (`core/comm/presets.py:130-144`) [read]; every `arsenal.media` result carries a `blind` field saying what it cannot see (`arsenal/media/receipt.py`) [read]; `eye trace` labels each edge recorded / derived / inferred [ran help] | One evidence-ID namespace that points at bytes of a *target* (hash, offset or address), not at repo files |
| Route the target first: pick the tool from what the target is | Per-format doors exist (`arsenal.media probe` for media, `shader dissect` for GLSL, `riot.py` for match JSON) [read] | No generic "what is this file" router (gap G3) |
| Summary first; never repeat an identical analysis without a changed input | Probe sidecars and the media catalog (a 2.4 GB file is probed once) [read]; the web door's ETag cache [read]; `sift --dry-run` builds the evidence pack before any spend [ran help]; `scout` asks "has this been done" [ran help] | Not wired across lanes for a reverse-engineering case |
| Read resources and configuration with the code; never infer behaviour from names | `dissect` matches the shape of the maths, names only add confidence [read] [Correction, Vandor 2026-10-13: a name alone can earn a weak tag (0.5-0.65), which `explain` reports as inferred]; the Shelf re-reads every licence comment because the meta's reading was wrong for 32 of 33 restrictive shaders [read]; `riot.py` records the "bootless Draven" error, where the boots had moved to `roleBoundItem` [read]; `midiports.py` reads WinMM because the browser's port list went stale [read] | Nothing generic; the habit lives in individual modules |
| Keep a finding ledger: confidence, search boundary, unknowns; revisit the checklist at the end | `college` keeps source, sealed lecture, typed claim audit and errata in a hash chain (`core/library/college.py`) [read]; `forecast` pre-registers falsifiable bets with a "dies when" [ran help]; fence reconciliation verifies every citation before reading conclusions (M1-PV) [read] | No ledger shaped for one target: identity, permission basis, question checklist, findings, close-out (gap G2) |
| Bounded negative searches stay bounded (the skill: "keep bounded negative searches bounded") | `tests/test_find_bounded_is_not_absent.py`: an unsearched space is not an empty one, pinned after a real false "absent" [read]; `sift` reports its sampling cap in the pack's blind list [read]; `manual search` names its denominator on a zero [read] | Already strong; reuse as is |
| Separate observed behaviour from design choices when rebuilding | The craft studies' line, techniques transfer while code, copy, brand and assets do not (`research/in-flight/craft-study-saffron-shader-excavation-avatar-plan-2026-09-02.md`) [read]; the Shelf's "datasheet, never the schematic" [read]; the licence line measures it (section 3.1) [read] | The measured wall covers the shader corpus only (gap G4) |
| Never pick the target on the user's behalf (the skill: "Never choose an example app on the user's behalf") | Conductor's doctrine: briefs carry Daniel's words verbatim and one calibrated question [memory index] | Nothing to build; a rule for every playbook |

---

## 3. The inventory

### 3.1 Static readers of code and data

The house's deepest static analysis today is for GLSL, built for the shader school. It is the closest thing the house
has to a disassembler: a reader that turns code into a call graph, finds dead code, and tags techniques with line
evidence.

**`py -m arsenal shader <verb>`** (`arsenal/shaders/`). The other workflow tonight is building `arsenal/web/glsl/*`,
`arsenal/shaders/twins/*`, `modules.py` lint and the Shader Lab files; those are listed here for completeness and read
only.

| Verb | Reads | Evidence it yields | Receipt lands | Limits |
|---|---|---|---|---|
| `ingest` | a harvest bundle (`arsenal.shadertoy-harvest/v1`) from `harvest.js` in a signed-in shadertoy.com tab, or the clipboard | the shader exactly as served (provenance), one `.glsl` per pass, a meta file (author, licence reading, passes, inputs), media by content hash | `state/arsenal/shaders/corpus/` (gitignored); each bundle kept byte for byte as `harvests/<sha256>.json` [read] | Shadertoy-shaped JSON only. The site sits behind Cloudflare, so the harvest runs in Daniel's own tab, waits 1.5 s between requests, and stops on a challenge instead of retrying [read] |
| `list`, `show`, `missing` | the corpus | facts per shader; ids a set names but the corpus lacks; media sampled but not saved | stdout or `--json` | views only |
| `harvest-js` | nothing | the helper's path, or a paste-ready snippet that fetches missing media | stdout | needs a human step in a browser tab |
| `dissect` | a corpus id, a Shadertoy JSON, **or any `.frag`/`.glsl` file** [ran help] | technique tags, each with file:line evidence and a confidence (0.5 floor); three per-pixel cost views; dead code by reachability from the entry points; `--atlas` places tags on house categories | stdout or `--json`; anything describing third-party code stays under `state/` [read] | Regex detectors over a token-flattened text from `glsl.py`. Not a compiler: no types, no overload resolution, macros are not expanded, an `#if` it cannot evaluate keeps its first branch and says so. Its `work` estimate ranks with measured ms at Spearman +0.78, but that timing is mostly compile time [read] |
| `census` | the corpus or one set | technique frequencies, pairs that travel together, families (weighted Jaccard, average linkage, cut at 0.75) | `state/arsenal/shaders/census/<set>.{md,json}` plus a dated twin under `runs/` [read] | deterministic; the family cut was swept on one corpus of 335 [read] |
| `render`, `check`, `filmstrip` | one shader, or the corpus | PNG stills at chosen times; a compile-and-one-frame census; a contact sheet over time. Every receipt names the shader, author and licence | `state/arsenal/shaders/renders/<id>/`, `state/arsenal/shaders/check/<timestamp>.json` [read] | CPU only: SwiftShader in a private headless Chrome that refuses to draw if the renderer names hardware; under the GPU lock; bursts under three minutes; corpus pictures never leave `state/` [read] |
| `card` | a house module's `.card` file | a test-pattern render with three verdicts (compiles, not flat, no NaN) | `state/arsenal/shaders/cards/<name>/` [read] | house modules only; owned by the other workflow tonight |
| `shelf` | corpus, dissector, atlas, study notes, renders | one card per Loved shader, including a *corrected* licence: every comment is re-read for phrases that withhold permission (33 of 335 do; the meta caught 1) [read] | `state/arsenal/shaders/shelf/index.json` [read] | private by design; study-only entries carry no pictures |
| `atlas` | `arsenal/shaders/atlas.json` | the parts catalogue, planned against built | stdout | — |
| `lib` | `arsenal/web/glsl/` | list, show, compose, lint, manifests, index | stdout, or `--write` | other workflow's surface tonight |
| `licence-line` | every file git would commit (read-only git), against 12-token shingles of every corpus pass | each shared run with its verdict; exempt runs (bare signatures, declared textbook idioms) are shown, never hidden; the baseline may only shrink | stdout or `--json`, exit 1 on a breach; `arsenal/shaders/licence_line_baseline.json`, `licence_line_allow.json` [read] | scoped to the shader corpus; "copied" is defined as a shared 12-token run [read] |
| `serve` | — | the lab's own read-only server, loopback only, default port 8797, port 8793 refused, non-loopback Host headers refused [read] | — | for the headless driver, not a person's browser |

Also in this lane:

- **`arsenal/shaders/glsl.py`**, the GLSL ES reader: tokens with line numbers, functions, structs, uniforms, loops with
  literal bounds, a call graph and a reachability walk from the entry points [read]. Its limits are the `dissect` limits
  above. It is the one house module that behaves like a decompiler's front end, for a source language.
- **`py -m arsenal coupling`**: a static census of the preset bank, which audio channels each preset reads and how
  deeply (`arsenal/presets.py`) [read]. Our own code only; stdout.
- **`py -m arsenal inspect`** and **`plan`**: module manifests (`arsenal.module/v0`, `arsenal/registry.py`) and graph
  plans [read]. The registry already allows an `external` engine, so a future reverse-engineering primitive can register
  in the same place as the media and shader modules [read].

### 3.2 Runtime observation of pages we own

Every lane here drives a private headless Chrome with a throwaway profile over the Chrome DevTools Protocol, never
Daniel's own browser [read]. They observe *our* pages.

| Tool | Reads | Evidence it yields | Receipt lands | Limits |
|---|---|---|---|---|
| `arsenal/shaders/headless.mjs` | a plan written by `render.py` | PNG frames and each page's own report (`window.__render`), with the renderer string judged twice | under `state/` only for corpus subjects [read] | SwiftShader only; GPU lock; jobs that miss their deadline cost a Chrome restart [read] |
| `arsenal/shaders/lab_shot.mjs` | the lab page | screenshots of the Workbench UI per view, and a "press Run" receipt with the pre-flight verdict | `state/arsenal/shaders/labshots/<run>/` [read] | SwiftShader only |
| `arsenal/lanes/alias_verify.mjs` | any page | every canvas's backing store against CSS size times devicePixelRatio (the fill ratio), and frame-time distribution | `state/arsenal/receipts/alias/run-<stamp>/` [read] | resolution truth, not image quality |
| `arsenal/lanes/chrome_verify.mjs`, `play_verify.mjs` | First Light and the `/play` presets | end-to-end verdict plus screenshots per preset and mode | `state/arsenal/receipts/` [read] | **need Daniel's server on 8793**, so not usable by this workflow |
| `arsenal/lanes/jam_timing.mjs`, `jam_verify.mjs` | the piano page's jam space | timing receipts against a recomputed tempo map, courtesy-gate checks, all on synthetic notes | `state/arsenal/receipts/jam/` by default [read] | start their own server on another port; load-sensitive, so other lanes yield to them [read] |
| `arsenal/lanes/gpu_lock.mjs` | — | who holds the render lock, whether it is stale; runs one command under the lock | `state/arsenal/gpu-render.lock/` [read] | one headless render at a time, bursts under three minutes (`arsenal/GPU-LOCK.md`) [read] |
| `arsenal/lanes/hwdecode_soak.py`, `gst_d3d12_soak.py` | a video file | hardware-decode receipts (PyAV; GStreamer D3D12) | `state/arsenal/receipts/` [read] | GPU decode work |

**The CDP domains the lanes use today** [ran grep over `arsenal/**/*.mjs`]: `Runtime`, `Log`, `Page`
(navigate, captureScreenshot, addScriptToEvaluateOnNewDocument), `Emulation`, `SystemInfo`. **Not used anywhere**:
`Network`, `Tracing`, `Profiler`, `HeapProfiler`, `Debugger`, `Performance`. The injection hook a frame debugger would
need (`Page.addScriptToEvaluateOnNewDocument`) is already in `lab_shot.mjs`, `jam_verify.mjs` and `alias_verify.mjs`.

Outside the repo, two harness browsers exist for runtime observation: Claude in Chrome and the built-in browser pane,
both able to read console messages and network requests. They are session tools, not house verbs, and this workflow did
not use them.

### 3.3 Black-box analysis of recordings (the lane that fits a game-design study best)

For a game we do not own, the safest and often most informative reverse engineering is of its *behaviour* as recorded:
timings, cadence, numbers on screen, sound cues. The house is already strong here.

**`py -m arsenal <verb>`** (top level, `arsenal/__main__.py`):

| Verb | Reads | Evidence it yields | Receipt lands | Limits |
|---|---|---|---|---|
| `probe [--hw]` | a media file | container and stream facts via PyAV; hardware-decode evidence | stdout JSON [read] | media only |
| `analyze` | a media file | timestamped audio features per frame | `--out` JSON, else a summary on stdout [read] | — |
| `storyboard` | a video | motion score per frame, segmented into settled runs and transitions (each with its length), deduplicated picks, a contact sheet and a manifest that declares its thresholds | `state/arsenal/storyboards/<stem>/` by default [read] | a sample, never the video; default 5 fps at 480 px wide [read] |
| `motion` | a storyboard manifest (or a video, analysed first), or a whole directory | pacing numbers: transitions per minute, median and p90 transition length, longest calm | stdout or `--json` [read] | not a quality score; it cannot recover depth inside a transition from a stored manifest, and says so [read] |
| `boost` | an image or frame | a percentile-stretched view of a dark frame, plus a ring / glow / nothing verdict from annulus means | `state/arsenal/receipts/boost/` [read] | luma only |
| `floors` | a frame, or a directory as a census | pinned pixel checks: dead, blown, flat, illegible, with declared exemptions shown | stdout, exit 1 on a hard fail [read] | floors, not taste |

**`py -m arsenal.media <verb>`** (also `py agent_cli.py media <verb>`, and an MCP door `py -m arsenal.media.door`
that is not registered by default) [ran verb list]. Every result has the house shape (`api`, `source`, `params` with
every default declared, `computed_with`, payload, `blind`) and is written as a receipt under
`state/arsenal/media/receipts/<verb>/`; probe facts go to `state/arsenal/media/sidecars/<id>.json` and the catalog is a
SQLite file rebuilt from the sidecars [read]. Originals are opened read-only [read].

| Verb | Evidence it yields (its own measured numbers where given) |
|---|---|
| `doctor` | which ffmpeg the house uses and what the build can do. Today [ran]: build N-124319 (2026-05-03) from `%LOCALAPPDATA%\StemRollerTrio\ffmpeg\bin`, with AMF encoders, `scdet`, `whisper`, `ebur128`, `libplacebo`; packages `scenedetect`, `rapidocr` and `pymediainfo` missing; a warning that `PYTHONUTF8` is not set |
| `probe`, `import`, `find` | streams, every audio track with its name, keyframe interval and full keyframe index (packet-flag scan, about 1 s on a 33-minute file), remembered in the catalog [read] |
| `grab`, `sheet`, `filmstrip` | frames at exact times in one ffmpeg pass; labelled contact sheets whose cells are reproducible (md5 in the index); a filmstrip over the waveform of the same seconds [read] |
| `cut` | frame-exact trims, with `--plan` showing the cost [read] |
| `audio`, `mix`, `qc`, `peaks` | per-track loudness (LUFS, true peak), silences, demux, channel split; export checks; waveform peaks in audiowaveform's format [read] |
| `shots` | scene cuts on a 360p proxy: F1 0.844 with the spike rule, PySceneDetect when installed [read] |
| `words` | speech to text with a time per word (faster-whisper with voice-activity filtering), and a repeated-word check as the cheapest hallucination test [read] |
| `avsync` | the offset and drift between two recordings, or between a recording and a list of event times, by cross-correlating onset envelopes, with a confidence [read] |
| `clockmap`, `events`, `replay` | League of Legends only (below) |
| `export`, `edit` | platform presets with a loudness receipt; the editor's timeline document [read] |

**The League lane is the house's precedent for observing a game properly** (`arsenal/media/league/`) [read]:

- `clock.py` reads the HUD clock from pixels and maps file time to game time across rewinds and slow motion. Its OCR
  engine is `rapidocr`, which is not installed, so it falls back to digit templates or `--ocr-python` [read, ran doctor].
- `hud.py` keeps HUD boxes as fractions of the frame per layout, so a resolution change does not break them [read].
- `live.py` reads Riot's official Live Client Data API (loopback only, up only during a game) [read].
- `replay_api.py` drives Riot's official Replay API on loopback; it never launches the game [read].
- `riot.py` reads cached match-v5 JSON only and never calls Riot [read]; `events.py` pins timeline events to frames.

The pattern: the game's own documented interfaces plus what the screen shows, and never the game's memory or network.
That is the right shape for any game we study but do not own.

### 3.4 Decoders of event streams (the piano tools)

These turn a low-level stream (MIDI events) into structure (chords, keys, cadences) with evidence and times. The same
shape serves any event log we may lawfully read, such as our own game's telemetry.

| Tool | Reads | Evidence it yields | Receipt lands |
|---|---|---|---|
| `py -m arsenal.practice <verb>` (15 verbs: `sessions`, `brief`, `chords`, `progressions`, `keys`, `borrowed`, `colors`, `moment`, `name`, `compare`, `history`, `windows`, `harmony`, `analyze`, `list`) [ran help] | `state/arsenal/performance/<session>/events.jsonl`, read only | harmonic windows by dynamic programming over onsets, keys "with the evidence for each change", cadences, habits | reports under `state/arsenal/receipts/practice-verbs/` [read] |
| `arsenal/practice_riff.py` (`practice riff`) | a jam run plus a session | his notes read against the loop's bars and chords | `state/arsenal/jam/riffs/<run>.json` with `--save` [read] |
| `arsenal/practice_theory.mjs` | a request on stdin | chord names from the *exact* code that names chords on the live page (slices the THEORY block of `piano.js`) | stdout [read] |
| `arsenal/replay_harmony.py` | a frozen replay | windows with pedal-aware sounding, and audition velocities from the voice's own loudness curve | used by the replay server [read] |
| `py -m arsenal.story_corpus oracle` | every session | per-session cadence oracle, each file stamped with the sha256 of the rules judged | `state/arsenal/story/oracle/` [read] |
| `arsenal/nashville.py` | chord names | Nashville numbers; a twin of the browser module, both pinned to one fixture file | — [read] |
| `arsenal/roll.py` | a session | a compact lossless projection (29 times smaller), with the caveat that re-deriving chords gives today's detector, not that night's | — [read] |
| `node arsenal/score_cli.mjs` | a session | clean score, MusicXML and MIDI exports, a bench | `state/arsenal/score/` [read] |
| `arsenal/jam/align.py`, `tempomap.py` | a run and a session | alignment on a four-level ladder with a stated error (2 ms to 150 ms), and a Python/JS tempo-map twin agreeing to 0.001 ms | — [read] |
| `arsenal/take.py`, `arsenal/performance.py` | — | append-only ledgers whose epochs only move forward | `state/arsenal/takes/`, `state/arsenal/performance/` [read] |
| `arsenal/midiports.py` | WinMM and the Windows MIDI Service | what the OS sees, to name the stale layer when the browser's list disagrees | `GET /api/midi/ports` [read] |
| `py -m arsenal.stt` | an audio file | words with timing and a cadence layout that marks low-confidence words | `<stem>.words.json`, `<stem>.cadence.txt` [read] |

The lesson these teach, which belongs in every playbook: when two readings of one stream exist (Python and browser),
pin them to one fixture so they cannot drift (`nashville`, `tempomap`, `practice_theory`).

### 3.5 Stem separation

**Not a house primitive** [found]. What exists, all outside the repo:

- `E:\StemRoller-Trio`: a desktop Demucs app (vocals, drums, bass, other), with its own venv, a PyInstaller build, and
  the ffmpeg build the house now uses [found, read README].
- `E:\ZLUDA-StemRoller`, a `demucs` clone under `%USERPROFILE%\Desktop\Projects\demucs`, StemRoller 3.1.x builds, and
  `amdstems` / `audio_separator` venvs left in an old session scratchpad under `%TEMP%` [found].
- `demucs` and `audio_separator` are **not** importable from the house Python [ran].
- The planned primitive `stems.split` (row L1 of `research/in-flight/video-primitives-2026-10-12/PRIMITIVES-SPEC.md`)
  would run UVR MDX-Net or Demucs on DirectML, pinned to the RX 9070 XT by adapter name, and is waiting on a durable venv
  location, which is Daniel's call [read]. It is GPU work.

### 3.6 Knowledge, search and evidence doors (`py agent_cli.py <verb>`)

| Verb | Reads | Evidence it yields | Receipt lands | Limits |
|---|---|---|---|---|
| `find` | the Everything index of local volumes, by file name | full paths, sizes, dates [ran] | stdout only | names, not contents; a miss is bounded by the index and the query, never "absent" (`tests/test_find_bounded_is_not_absent.py`) [read] |
| `eye` (`ingest`, `find`, `get`, `trace`, `zoom`, `freq`, `standing`, ...) | session transcripts | verbatim records by address (`session:line`), and ancestry walks whose edges say how they are known [ran help] | `state/eye/eye.db` (gitignored) [read] | transcripts only |
| `recall`, `recall-at`, `knowledge-map`, `lookback` | the lesson and note store (akashic-redis on 16379, local fallback) | ranked lessons with source pointers; neighbourhoods; the rationale corpus [ran help] | Redis and the ledger | lessons are only as good as their trigger phrasing |
| `sift` | repo source, tests or docs for a term | evidence packs built first, a fan of differently-framed readers, then dissent before consensus [ran help] | `--out` JSON | repo planes only (it skips `state/`); sends packs to helper models |
| `scout` | the task ledger, locks, past scout verdicts | "is anyone mid-flight here, has this been done", citing ledger ids [ran help] | files itself as an unadjudicated verdict | — |
| `web fetch`, `web search` | a URL, or a query | cleaned text beside the raw bytes, a range API that never truncates silently, a structural pass for PDFs, everything fenced as untrusted [read] | cache `state/web_cache/`; receipts `state/coord/web_fetch_receipts.jsonl` [read]; see finding F2 | search needs a Brave key |
| `ask` | one question, optionally `--with` repo files inlined with line numbers | a helper model's answer; `--preset findings` gives FINDINGS / REASONING / CHECK / BLIND; `--geometry` declares fan shape (partition, lens, panel, adversarial, backbrief) [ran help] | background answers under `state/asks/` [read] | **content goes to a third-party model**: no proprietary decompiled code, samples or secrets unless permitted |
| `manual` (`search`, `ingest`, `list`) | shelved reference documents (Markdown, DocC JSON, HTML, PDF) | labelled passages with breadcrumbs and source links; hybrid search found the right page in the top 5 for 39 of 40 blind questions [read] | `state/manuals/manuals.db` [read] | only what has been shelved |
| `captions` | a YouTube URL | captions only, cleaned to text, never the video [read] | `~/Desktop/captions` [read] | design talks and devlogs, not the games themselves |
| `college` | sources, a lecture, audits | a hash-chained record: source status, one sealed lecture, typed claim verdicts (supported, qualified, disputed, unresolved...), teach-backs, errata [read] | `artifacts/college/<course>/` [read]; see finding F3 | course-shaped, not target-shaped |
| `fence` (`open`, `write`, `seal`, `pv`, `status`) | the four slots | seal-time checks: brief sections, one confidence tag per verdict, citation verification, author independence [read] | `fences/<id>/`, **tracked in git** [ran check-ignore] | public repo |
| `forecast` | a bet | registered expectation with metric, horizon, mechanism and a mandatory "dies when"; calibration later [ran help] | the ledger | — |
| `tally`, `ground`, `compare`, `timeline` | research counters; verbs and seats; domains; events and git | agree/conflict matrices; typed evidence; set differences; one chronological view [ran help] | stdout | — |
| `screen` (and `core/screenspace/capture.py`) | the desktop | a one-shot screenshot with dimensions, DPI scale and sha256; in memory unless asked to persist [read]; `mss` is installed [ran] | transient by default | observe only; acting is gated [read] |

### 3.7 Bifrost and the fence method

- **Bifrost** (`core/comm/`) is the agent bus on Redis Streams: one inbox and cursor per agent, `bifrost-send`,
  `ask --peer` for one durable question to one seat, and promotion of salient messages into the durable ledger
  (`docs/ARCHITECTURE.md:94-105`) [read]. For reverse engineering it is how independent questions are farmed out to
  different seats with different evidence.
- **The fence method** (`docs/method-baseline-2026-07.md`, M1) is the house's answer to correlated blind spots: two
  seats work the same question from separate contexts, varying the *method* (static reading against live drill), neither
  reading the other's half until their own is sealed; the reconciler first checks every citation against the repo and
  retires any section whose citation does not resolve, then sorts verdicts into converged, complementary and divergent
  [read]. For reverse engineering this maps directly onto a static pass and a runtime pass of the same target, and onto
  the clean-room split (one seat reads the target and writes a specification, another builds from the specification
  only) [inferred].

### 3.8 Reverse engineering the house has already done

These are precedents to copy, each with its own boundary already written down.

- **Our own model traffic.** `scripts/wire_journal.py` records the HTTP envelope of our agents' API calls at the httpx
  transport seam, in process, with no TLS interception (`state/wire/`) [read]. The companion study,
  `research/in-flight/api-wire-reverse-engineering-deepseek-2026-08-04.md`, by Heimdall (deepseek), cites file:line or a
  pasted field for every claim and states its sampling rate where it samples [read]. The capture design by the opus5
  seat (`research/in-flight/wire-next/capture-design.md`) labels unrun claims INFER [read].
- **Web pages as craft studies.** Vandor's Saffron study recovered a site's shader architecture from its shipped
  bundle, not from pixels, under the line "techniques transfer; code, copy, brand, assets do not"; the companion study of
  The Watch walked the animation layer live in the browser pane, beat by beat (`research/in-flight/craft-study-*`)
  [read].
- **Our own tool surface.** `docs/library/report/20260716_mcp-surface-reverse-engineering-deepseek_c79c35.md`: a
  read-only reverse engineering of our MCP surface with file:line receipts [read].
- **Method.** `research/in-flight/troubleshooting-re-fan-2026-08-16.md`: a six-branch fan on how expert troubleshooters
  and reverse engineers work (annotated databases, cross-reference chains, library-signature recognition, anchor-point
  triage, notebook discipline), already mapped onto the eye and recall [read].
- **The shader school.** The harvest, dissector, census, Shelf and licence line above are a full clean-room pipeline for
  one domain: collect other people's work privately, study it with evidence, rebuild in our own words, and measure that
  nothing crossed [read].

---

## 4. Not the house, but on the machine

**Python 3.11 packages** [ran `find_spec`]. Present: `pefile`, `magic` (python-magic), `zstandard`, `fitz` (PyMuPDF),
`PIL`, `numpy`, `scipy`, `av`, `cv2`, `librosa`, `soundfile`, `faster_whisper`, `torch`, `pygments`, `networkx`,
`playwright`, `websocket`, `bs4`, `lxml`, `mss`. Absent: `lief`, `capstone`, `unicorn`, `keystone`, `kaitaistruct`,
`construct`, `frida`, `r2pipe`, `elftools`, `UnityPy`, `yara`, `binwalk`, `angr`, `scapy`, `dpkt`, `pyshark`,
`mitmproxy`, `xdis`, `uncompyle6`, `decompyle3`, `lz4`, `brotli`, `py7zr`, `rarfile`, `olefile`, `oletools`,
`pdfminer`, `tree_sitter`, `esprima`, `duckdb`, `mido`, `music21`, `pretty_midi`, `demucs`, `audio_separator`,
`scenedetect`, `rapidocr`, `pymediainfo`. Neither `pefile` nor `magic` is imported anywhere in the repo [ran grep].

**Executables on PATH** [ran `shutil.which`, none executed]: `node`, `npx`, `git`, `yt-dlp`, `dotnet`, `wsl`, `docker`.
Not on PATH: `ffmpeg` (the house finds it through `doctor`), `java`, `go`, `cargo`, `clang`, `gdb`, `lldb`, `objdump`,
`strings`, `7z`, `upx`, `tshark`, `binwalk`, `wasm2wat`, `spirv-dis`, `glslangValidator`, `renderdoccmd`, `exiftool`,
`mediainfo`, `sox`.

**Built into Windows** [found in `System32`, not run]: `wpr.exe` (Windows Performance Recorder, ETW traces), `pktmon.exe`
(packet monitor; can convert to pcapng), `tar.exe` (libarchive), `certutil.exe` (file hashes), `logman.exe`,
`tracerpt.exe`. Most need an elevated prompt for capture [inferred].

**Third-party tools found by name** [found, Everything index, name substring, first three hits per name]:

- Sysinternals Process Monitor and Process Explorer, in `%USERPROFILE%\Desktop\unorg desktop\` (file, registry and process
  activity of programs we run; useful for observing our own builds).
- Universal Extractor 2 (Bioruebe) in the same folder, bundling TrID, ExeinfoPE, PEiD, QuickBMS, GARbro, innounp,
  lessmsi and others. Its provenance on this disk is unverified, it is a bundle of third-party binaries, and several of
  its parts exist to unpack protected executables or decrypt game archives. **The house should not wrap it, and it should
  not be run on the host** [inferred].
- `llvm-objdump.exe` exists only inside ROCm SDK venvs (for example `E:\venvs\rocm10\...\_rocm_sdk_core\lib\llvm\bin\`), an
  incidental disassembler, not a house tool.
- **Not found under these names**: Ghidra, x64dbg, ImHex, radare2, rizin, Wireshark, tshark, Fiddler, mitmproxy, RenderDoc,
  ILSpy, dnSpy, jadx, apktool, Frida, PE-bear, CFF Explorer, AssetStudio, binwalk, VirtualBox, Sysinternals `strings`
  and `sigcheck`, `dumpbin`, `wasm2wat`, PIX. This is a bounded negative: one name substring each, in the Everything
  index, which listed hits on C:, E: and F:.

**Isolation substrate** [found]: `C:\Windows\System32\vmcompute.exe` (Host Compute Service, which backs WSL2 and Docker)
is present; `C:\Windows\System32\WindowsSandbox.exe` is **absent** (the payload sits only in WinSxS, so the optional
feature is not enabled) [inferred from file presence]; `vmms.exe` (the Hyper-V management service) is absent. WSL and
Docker Desktop are installed. Neither WSL2 nor a Docker container is a disposable sandbox for untrusted code as
installed: WSL2 mounts host drives under `/mnt` and can launch Windows programs by default, and containers share the WSL2
VM's kernel and any bind-mounted host folder [inferred from documented defaults; not probed, because a WSL probe was
part of the 2026-09-11 outage].

---

## 5. Findings surfaced while taking the inventory

Observations, each with its evidence. None was fixed here (read-only workflow).

- **F1. `py -m arsenal shader --help` is refused** [ran]. The top-level parser in `arsenal/__main__.py:165-167` gives
  `shader` an `argparse.REMAINDER` argument, which does not capture a leading option, so both `--help` and `-h` print
  the top-level usage and exit 2. Verb-level help works (`py -m arsenal shader dissect -h`), and the full verb list is
  reachable through `arsenal.shaders.cli.main(['-h'])` [ran]. The shader CLI's own docstring says `--help` works.
- **F2. The web door's receipt file is committable.** `state/coord/web_fetch_receipts.jsonl` (425 lines, 97 KB today) is
  re-included by `.gitignore:144` (`!state/coord/**`), is untracked, and shows as `??` in `git status` [ran]. Every URL
  any seat fetches is one `git add -A` away from the public repository. For reverse-engineering work that means target
  download URLs and research trails. Whether that was intended is [unknown]; the door's docstring calls the file
  auditable but does not say public.
- **F3. The college's hash chain does not travel with its lecture.** `artifacts/college/<course>/events.jsonl` is
  ignored by `.gitignore:74` (`*.jsonl`) while `lecture.md` is not [ran check-ignore]. A clone gets the sealed lecture
  without the chain that `college show` checks it against [inferred]. Relevant if the college becomes the evidence
  ledger's base (G2).
- **F4. Fences are public.** `fences/<id>/` is tracked [ran check-ignore]. A reverse-engineering fence must cite private
  evidence by path and hash, never paste third-party code or decompiled output into a half.
- **F5. Two capable libraries sit unused.** `pefile` and `python-magic` are installed and imported nowhere [ran]. They
  are most of a read-only triage verb (G3) already.
- **F6. Optional packages the media lane wants are missing**: `scenedetect`, `rapidocr`, `pymediainfo` [ran doctor].
  The HUD-reading pattern (G11) leans on `rapidocr`.
- **F7. `PYTHONUTF8` is not set** [ran doctor]; the doctor notes non-cp1252 output has crashed 17 agents [read].

---

## 6. The gap list

What a full reverse-engineering arsenal needs that the house lacks, in build order. Each row names the boundary it must
keep. Licences are as published by each project; confirm at install time.

### P0: before any untrusted target is touched

| Gap | Why | Candidates and sources | Where it would live | Boundary |
|---|---|---|---|---|
| **G1. A disposable analysis environment** | With Defender off, a VM is the only containment. Nothing disposable is enabled today (section 4) | Windows Sandbox, built into Windows 11 Pro, discarded on close, with a `.wsb` file that can switch off networking and folder mapping (Microsoft docs, section 9); or a Hyper-V or VirtualBox VM with snapshots and host-only networking; a Linux VM for the Linux-only tools (binwalk, unblob, tshark under REA's own requirements) | outside the repo; the house keeps only the `.wsb` or VM recipe and an intake script | Turning on a Windows feature is a system change: Daniel's call. Samples live in a quarantine folder outside `E:\AI-Setup`, hashed on intake, opened only inside the VM |
| **G2. A reverse-engineering case ledger** (`re case open / observe / infer / unknown / close`) | REA's finding ledger has no target-shaped home. The pieces exist: college's hash chain, the fence's tag checks, the media receipt shape with `blind` | build on `core/library/college.py` and `core/coord/fence_workspace.py` | private record under `state/re/<case>/`, with a public-safe summary projection | Records the target's identity (sha256, size, version, where it came from) and the **permission basis** (we own it, it is open source, its licence allows study, or an exemption applies) before any finding; every finding tagged observed / inferred / unknown with an evidence id (receipt path plus hash plus offset or address) and its search boundary; `close` refuses until every checklist question is marked answered, partial or unresolved |
| **G3. A read-only triage router** (`re triage <file>`) | REA routes the target before choosing a tool; the house has per-format doors but no front door | `python-magic` and `pefile` (installed, F5); stdlib zip and tar; hashes; an entropy map; strings with offsets. FLOSS (Mandiant FLARE) for obfuscated strings, inside the VM | an `arsenal` module with a manifest (`engine: external` is already allowed) | never executes the target; refuses paths inside the repo except fixtures we wrote |
| **G4. The clean-room wall, generalised** | The licence line measures "nothing copied" for the shader corpus only | generalise `arsenal/shaders/licence_line.py` to any registered private study corpus (decompiled code, recovered scripts, data tables); add a dirty-room / clean-room fence template: one seat reads the target and writes a behaviour specification, another builds from the specification alone | `arsenal/` plus a fence template under `fences/` | the specification describes behaviour and numbers, never code or assets |

### P1: the core analysis lanes

| Gap | Why | Candidates and sources | Where it would live | Boundary |
|---|---|---|---|---|
| **G5. Native disassembly and decompilation** | Nothing on the machine today (section 4) | Ghidra (NSA, Apache-2.0; needs a JDK, and `java` is not on PATH); for scripted reads of our *own* binaries in house Python, LIEF (Romain Thomas, Quarkslab), Capstone (Nguyen Anh Quynh), pyelftools (Eli Bendersky); x64dbg (Duncan Ogilvie) for debugging our own builds only. REA itself (morluto) can drive Ghidra, IDA and JADX over MCP if Daniel later wants the machinery | inside the VM (G1) | our own software, open source, or targets whose licence or law permits; never licence checks, DRM or anti-tamper |
| **G6. Managed code, mobile and engine content** | Games are often .NET (Unity Mono), Android or engine archives | ILSpy (ICSharpCode) for .NET assemblies; jadx (skylot) for Android; UnityPy (K0lb3) and AssetRipper for Unity asset inventories | inside the VM | asset copyright: an inventory and measurements may leave the VM, the assets themselves may not; IL2CPP and protected builds are out of scope |
| **G7. Web, JavaScript and Electron depth** | Craft studies did this by hand; the lanes use five CDP domains (section 3.2) | a CDP capture lane for our own pages: `Network` (a HAR), `Tracing`, `Profiler` precise coverage, `Debugger.getScriptSource`; webcrack (j4k0xb) to unbundle and deobfuscate bundles we may study; `@electron/asar` to list Electron archives; Prettier for readable source | `arsenal/lanes/` beside the existing drivers, under the GPU lock and never on 8793 | our pages, open-source apps, and sites studied for technique under the craft-study line; no credentialed sessions of other people's services |
| **G8. A frame debugger for our own WebGL pages** | Shader work is judged by pictures today; a frame capture shows every draw call, its state and its shader source | Spector.js (the Babylon.js team), injected with `Page.addScriptToEvaluateOnNewDocument` into a SwiftShader page, exporting capture JSON; RenderDoc (Baldur Karlsson) later for native GPU frames | a lane beside `headless.mjs`; captures under `state/` | our own pages only; SwiftShader keeps it off the GPU; RenderDoc would be GPU work and is Daniel's call given the TDR history |
| **G9. A format-template library** | The house has hand-written readers for single formats (VTT, SRT, ASS, FFMETADATA, audiowaveform `.dat`, GLSL, Shadertoy JSON, match-v5, MIDI) and no shared way to describe a binary layout | Kaitai Struct (declarative `.ksy` layouts and a public format gallery); `construct` for parsers written in Python; ImHex pattern language inside the VM; `protoc --decode_raw` for unknown protobuf | `formats/` in the repo for specifications we write ourselves, plus the `manual` shelf for official specifications | layouts we write in our own words; a format gallery entry is cited, not vendored, unless its licence allows |
| **G10. Network observation of our own applications** | `wire_journal` covers our model traffic only | `pktmon` (built in); Wireshark and tshark (Gerald Combs and contributors); mitmproxy (Aldo Cortesi, Maximilian Hils) for clients we own; `dpkt` or `scapy` to read captures | captures under `state/`, analysis in the VM for anything not ours | our own devices and apps; never other people's traffic; TLS interception only of our own clients |
| **G11. The game-feel lane, generalised** | The League lane is one game; the Archero-style goal needs the same measurements for any recording Daniel makes of his own play | a generic HUD reader (the `league.hud` box file plus `rapidocr`) for timers, health and damage numbers; a gameplay event-log schema; `stems.split` (L1) to separate sound effects from music; a balance workbench that fits upgrade curves (damage per second, scaling per level) to measured numbers, in the spirit of Joris Dormans' Machinations | `arsenal/media/` and a new design workbench | measures behaviour from our own recordings and public sources (patch notes, wikis, talks via `captions`); mechanics are free to study, assets and presentation are not (*Tetris v. Xio*) |

### P2: later, or only if a target needs it

| Gap | Candidates and sources | Boundary |
|---|---|---|
| **G12. WebAssembly** | WABT (`wasm2wat`, `wasm-objdump`); REA requires WABT 1.0.42 for its WASM route | WAT is not the original source; our own or permitted modules |
| **G13. Firmware and hardware signals** | binwalk (ReFirm Labs), unblob (ONEKEY), sigrok | VM only; our own devices |
| **G14. Process observation verbs for our own programs** | wrap Process Monitor's exported logs and WPR traces as read-only parsers | our own processes |
| **G15. Version diffing** | BinDiff (Google, open source since 2023); Diaphora (Joxean Koret); for JavaScript, a diff of beautified bundles | compare versions of our own or permitted software |
| **G16. Library recognition** | Ghidra's Function ID and BSim (the FLIRT idea the 2026-08-16 fan named) | saves re-reading known library code |
| **G17. Small door fixes from section 5** | F1 shader help, F2 web receipts placement, F3 college chain placement, F6 optional packages, F7 `PYTHONUTF8` | each is Vandor's or Daniel's call; F2 decides whether research trails are public |

**Never in scope, whatever the target** (restating section 1 as a checklist for playbook authors): patching or
emulating licence checks; removing DRM; unpacking commercial protectors; reading or writing an online game's memory or
traffic (Cheat Engine-style tools, bots, packet editors); bypassing anti-cheat, anti-tamper or bot detection; intercepting
anyone else's traffic; building or running malware. The house already has the right instinct here: `harvest.js` stops
on a Cloudflare challenge and hands it to a human rather than working around it [read].

---

## 7. Checklist, revisited

The questions this inventory was asked, and their state.

| Question | State | Evidence and boundary |
|---|---|---|
| The `py -m arsenal shader` verbs: artifact, evidence, receipt, limits | answered | all sixteen verbs from the CLI's own help [ran] and module docstrings [read]; not exercised (no render, GPU-lock work) |
| `py -m arsenal` media, storyboard, motion, boost, floors, analyze, probe, and `arsenal.media` (frames, filmstrip, scene cuts, loudness, transcription, A/V sync) | answered | verb lists [ran], docstrings [read]; numbers are the modules' own |
| `find`, `eye`, `recall`, `sift`, `scout`, `web`, `ask`, `fence` | answered | `-h` output [ran], source [read]; plus `manual`, `captions`, `college`, `forecast`, `tally`, `ground`, `compare`, `timeline`, `screen` |
| `arsenal/practice.py` and the piano harmony and story tools | answered | `-h` [ran], docstrings [read] |
| Stem separation | answered: not a house primitive | Everything index for `demucs` and `stemroller` [ran]; repo grep [ran]; house-Python import check [ran] |
| `arsenal/lanes` headless capture | answered | docstrings [read]; CDP domain grep [ran]; not run (8793, GPU lock) |
| The licence line | answered | docstring [read]; not run (it scans the tree; not needed for the inventory) |
| Bifrost and the fence method | answered | `docs/ARCHITECTURE.md`, `docs/method-baseline-2026-07.md` [read] |
| What the machine has outside the repo | partial | bounded: one name substring per tool in the Everything index, sixty packages, forty executables. Tools installed under other names, inside other venvs or portable folders, would be missed |
| Is a disposable sandbox available | partial | file presence only; enabled Windows features were not queried (needs elevation) and WSL was deliberately not probed |
| The gap list | answered as a proposal | priorities are mine [inferred]; each P0 item needs Daniel's or Vandor's ruling before build |

---

## 8. Credits

- **morluto**, for REA and the discipline section 2 restates (https://github.com/morluto/rea).
- House authors cited above: Heimdall (deepseek) for the API wire study, the opus5 seat for the capture design, Vandor
  for the craft studies, and the seats of the 2026-08-16 troubleshooting fan.
- Tool authors named in section 6 are credited where named; projects without a single named author are credited by
  project.

## 9. Sources

All fetched with `py agent_cli.py web fetch` on 2026-10-13 and answered 200, except the two EUR-Lex pages, which
answered 202 and whose text was not read.

- REA skill: https://github.com/morluto/rea
- Ghidra: https://github.com/NationalSecurityAgency/ghidra (not fetched today)
- Spector.js: https://github.com/BabylonJS/Spector.js
- Kaitai Struct formats gallery: https://github.com/kaitai-io/kaitai_struct_formats
- ImHex: https://github.com/WerWolv/ImHex
- webcrack: https://github.com/j4k0xb/webcrack
- UnityPy: https://github.com/K0lb3/UnityPy
- AssetRipper: https://github.com/AssetRipper/AssetRipper
- BinDiff: https://github.com/google/bindiff
- unblob: https://github.com/onekey-sec/unblob
- FLOSS: https://github.com/mandiant/flare-floss
- Universal Extractor 2: https://github.com/Bioruebe/UniExtract2
- Chrome DevTools Protocol: https://chromedevtools.github.io/devtools-protocol/ (not fetched today)
- Windows Sandbox overview: https://learn.microsoft.com/en-us/windows/security/application-security/application-isolation/windows-sandbox/windows-sandbox-overview
- pktmon: https://learn.microsoft.com/en-us/windows-server/networking/technologies/pktmon/pktmon
- 17 U.S.C. 1201: https://www.law.cornell.edu/uscode/text/17/1201
- 18 U.S.C. 1839: https://www.law.cornell.edu/uscode/text/18/1839
- 37 C.F.R. 201.40: https://www.ecfr.gov/current/title-37/chapter-II/subchapter-A/part-201/section-201.40
- Directive 2009/24/EC: https://eur-lex.europa.eu/eli/dir/2009/24/oj
- Directive (EU) 2016/943: https://eur-lex.europa.eu/eli/dir/2016/943/oj
- *Sega v. Accolade*: https://en.wikipedia.org/wiki/Sega_v._Accolade
- *Sony v. Connectix*: https://en.wikipedia.org/wiki/Sony_Computer_Entertainment,_Inc._v._Connectix_Corp.
- *Tetris Holding v. Xio Interactive*: https://en.wikipedia.org/wiki/Tetris_Holding,_LLC_v._Xio_Interactive,_Inc.
- *Bowers v. Baystate* and *Davidson & Associates v. Jung*: cited by reporter only; not fetched today.
