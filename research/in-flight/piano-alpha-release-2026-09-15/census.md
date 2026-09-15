# Piano alpha release: census (read-only)

- **Date:** 2026-09-15
- **Brief (Daniel, verbatim):** "Lets see if we can't package what we have into an alpha release that is designed to work with any midi keyboard or midi USB adapter! Hopefully a single click install with instructions on how to integrate their preferred flavor of Ai assistant!"
- **Scope:** evidence only, no plan decided. Citations are `file:line` against the working tree on 2026-09-15, with HEAD at `2cf7131f` for `arsenal/web/piano.js`.
- **Method:**
  - Ran `git ls-files` and grep.
  - Ran `py -c` import census of `arsenal.serve`.
  - Sent GET requests only to the running server on 127.0.0.1:8793.
  - Nothing was installed, downloaded, POSTed or restarted.
  - Personal content is withheld. Where a GET returned session ids or paths, only the status code is recorded.

---

## 0. What ships today: the shape in one table

| Layer | Files | Size |
|---|---|---|
| Page | `arsenal/web/piano.html` (170 lines), `piano.js` (4,575 lines), `piano.css`, `arsenal/web/piano/**` (63 tracked files) | about 1.93 MB tracked, including 6 test or harness pages (162 KB) |
| Server | `arsenal/serve.py` plus `performance, pianocue, take, timebase, registry, presets, plan, graph, nashville, jam/*` | about 0.90 MB of Python |
| Optional Node bridge | `arsenal/pianocue_voicing.mjs` (84 KB), `practice_theory.mjs`, `groove_bridge.mjs` | needs `node` on PATH |
| Untracked, in flight (NOT shipped) | `piano-lab-{res,vfx,judge-res,judge-head}.{html,js}`, `piano/listen/`, `piano/recorder.js`, `piano/recorder-test.html` | from `git status` |

- `/` redirects to `/first-light`, not `/piano` (`serve.py:226-231`). A launcher must open `/piano` explicitly.
- `arsenal/web/piano/score/**` is **lab-only**. `piano.js` never imports it (its imports are `piano.js:13-30`). Only `piano-lab-score.html` uses it.

---

## 1. Runtime dependency map

### 1a. Python

| Item | Evidence | Class |
|---|---|---|
| Python 3.11.9 on this machine; the repo targets 3.11+ stdlib | `py --version`; `requirements.txt` header ("CORE ... NO third-party packages") | core |
| The serve path is **stdlib-only** | `serve.py:1` docstring ("uses only the standard library"); imports at `serve.py:8-32`. An import census of `arsenal.serve` found no third-party modules; only site hooks (`pywin32_bootstrap`, `sitecustomize`) appeared, and they belong to this machine's site-packages. | core |
| PyAV (`av`) for `/api/analysis`, `/api/probe` | lazy import at `serve.py:142`, `serve.py:387`; First Light routes that `/piano` does not use | not needed |
| `py` launcher assumed in docs and help | `__main__.py:3` (`py -m arsenal serve`) | house-only (macOS and Linux use `python3`) |
| Node.js (`node` on PATH) for chord voicing and name resolution | `pianocue.py:447` (`shutil.which("node")`), `jam/resolve.py:102-107`. A missing bridge answers 503 (`jam/runs.py:819-820`). Also `practice.py:1328`, `practice_riff.py:1345`. | optional (the jam deck resolve, the `pianocue` and `practice` verbs) |

### 1b. Network and CDN fetches made by `/piano`

| Fetch | Evidence | Without it | Class |
|---|---|---|---|
| three.js r186 `build/three.module.js` + `examples/jsm/` from jsDelivr | import map `piano.html:16-23` | The page never boots. After 15 s the boot banner says three did not load (`piano.html:159-165`). | core (vendor it) |
| three addons: EffectComposer, RenderPass, UnrealBloomPass, OutputPass, RoundedBoxGeometry | `piano.js:14-18` | same | core |
| three addons: Reflector, BufferGeometryUtils, GPUComputationRenderer | `moonwater.js:1-3`, `spectacle-worlds.js:1-2`, `spectacle.js:1` | The atmosphere fails. It is error-isolated: toast plus fallback (`piano.js:4548-4556`). | core (vendor it) |
| Google Fonts CSS: Archivo, JetBrains Mono, Noto Music, Outfit, Jost | `piano.html:8-10` | Falls back to system fonts. `loadFonts` times out at 9 s (`piano.js:1684-1686`). | optional (self-host for privacy and offline use) |
| Bravura SMuFL font from `cdn.jsdelivr.net/npm/@vexflow-fonts/bravura@1.0.2` | `piano.js:1674-1683` | The staff glyphs fall back; a warning is logged. | optional |
| Scheme modules probed with `fetch(new URL('./piano/schemes/<id>.js'))` | `piano.js:1571` | A probe entry that 404s is not listed | core (same origin) |
| mediabunny@1.56.2 from jsDelivr | `piano/recorder.js:45` (untracked, not imported by `piano.js`) | n/a today | not on the path |
| VexFlow library | **not used**; only the Bravura font package | n/a | n/a |

- **Vendoring note (from knowledge, verify at build):** since roughly r17x, `three.module.js` imports a sibling `three.core.js`. Vendor both files and keep the import map.
- **Vendoring note:** `serve.py` `STATIC_TYPES` has no `.woff2` or `.ttf` (`serve.py:41-45`). Self-hosted fonts would be served as `application/octet-stream` (`serve.py:310`). Add the type.

### 1c. Server endpoints the page calls

| Endpoint | Caller | What it does | Degrades gracefully? | Class |
|---|---|---|---|---|
| `GET /piano`, `GET /web/*` | `piano.html:12,14,167` (absolute `/web/` paths) | static files, path-contained (`serve.py:238-241,317-321`) | n/a | core |
| `GET /api/performance` (route probe) | `piano.js:2525` | lists sessions | **Yes.** Without it the log is pointed at port 9 and buffers locally (`piano.js:2514-2540`). | optional |
| `POST /api/performance/open`, `/<id>/events`, `/<id>/close` | `piano/log.js:78,146,385` (fetch keepalive and sendBeacon) | Practice log. Events are batched about every 1 s into `events.jsonl`; close writes the summaries (`performance.py:3-13,301-331`). | **Yes.** Buffers to IndexedDB and a localStorage stash (`log.js:103,128-141`). | optional (privacy-sensitive) |
| `GET /api/piano/cues/status` + SSE `GET /api/piano/cues?caps=jam1,deck1&page=<id>` | `piano.js:3037-3041`; `piano/cues.js:159-218` | The assistant's "hand": server-to-page cues plus deck and jam frames | **Yes.** A 404 gives status "no routes" and no retry (`piano.js:3038`). A server that is down gets endless reconnects (`piano.js:3036`). | optional (the assistant feature) |
| `GET /api/piano/deck`, `/deck/cards/<id>`, `/deck/cards/<id>/resolve` | `deck.js:398,425,463` | chord cards; resolve runs the Node bridge | **Yes.** Warns and shows empty (`deck.js:397-403`); resolve answers 503 with no node. | optional / labs |
| `POST /api/piano/deck/cards/<id>/update`, `/keep`, `/deck/templates` | `deck.js:1018,1209,1223`; payloads hardcode `by: "daniel"` | edits cards | Fails with a warning | labs; house identity baked in |
| `GET /api/piano/replay` | `deck.js:1188`, `piano/replay.js:250` | "Hear me" replay from the practice log | fails soft | labs |
| `GET /api/piano/jam`, `GET /api/piano/jam/runs/<id>`; `POST /api/piano/jam/start`, `/owner`, `/runs/<id>/ack`, `/launch`, `/control` | `transport.js:487,651,664,717,732,1007,1048`; `deck.js:1591` | The jam band (Claude's backing, try-in-time) | fails soft | labs |
| `POST /api/recordings?name=piano` | `piano.js:3662` | Saves the REC take under the **first library root** / `arsenal-renders` (`serve.py:621-654`) | **Yes.** Toast with a Download link for the blob (`piano.js:3670-3674`). | core (REC), but the root is house-only |
| iframe `http://127.0.0.1:8796/web/conversation.html` → `/api/conversation`, `/api/conversation/responses` | `piano/conversation-dock.js:2,16` (loaded unconditionally, `piano.html:168`); `piano/conversation.js:4,104,112` | Conversation cards served by a **separate** replay server (`replay.py:3,20`) | The button appears; the dock is dead if 8796 is not running | house-only |

**Server routes `/piano` never calls (First Light and Play suite; leave them out of the alpha):**
- `/first-light`, `/play`
- `/api/library`, `/api/resolve`, `/api/takes`, `/api/presets`
- `/api/media/*`, `/api/probe/*`, `/api/analysis/*`, `/api/graph/*`
- `POST /api/plan`, `/api/take/*`

These are at `serve.py:234-237,244-252,262-266,274-286`.

**Live GET probe (2026-09-15):**

| Endpoint | Result |
|---|---|
| `/api/health` | 200 `{"ok": true, "api": "arsenal.serve/v0", "version": "0.1.0"}` |
| `/api/piano/cues/status` | 200 (1 listener) |
| `/api/piano/deck` | 200 (rev 17: this house's seeded deck) |
| `/api/piano/jam` | 200 (idle) |
| `/api/piano/replay` | 400 without a query |
| `/api/presets`, `/api/takes`, `/api/performance`, `/api/library` | 200 (content withheld: session ids and absolute paths) |
| `/piano`, `/web/piano.js` | 200 |

### 1d. Local state paths

| Path | Written by | Evidence | Class |
|---|---|---|---|
| `<repo>/state/arsenal/performance/<session>/{session.json, events.jsonl, summary.json, summary.md}` | practice log | `performance.py:32,207-213,273,330-331` | optional, **private** |
| `<repo>/state/arsenal/jam/` (deck cards, runs, `seed/moments-v1.json`) | deck and jam; `serve()` also closes unclosed runs at startup | `jam/cards.py:1-13,33-35`; `jam/runs.py:97,756`; `serve.py:675` | labs, private |
| `<library root>/arsenal-renders/*.webm` / `*.mp4` | REC upload | `serve.py:49,634-653` | core, but root = `E:\Video Output E` (`serve.py:38`) |
| `<repo>/state/arsenal/takes` | First Light takes | `take.py:22` | not the piano |
| `<repo>/state/arsenal/replay` | conversation cards (8796 server) | `conversation.py:15` | house-only |
| Reads `arsenal/jam/seed/deck-v1.json` (17 cards) | only when seeded via `POST /api/piano/deck/seed` | `jam/cards.py:34,466-470,514-518`; `jam/runs.py:835,928-931` | labs. **A stranger's deck starts empty.** |
| Browser: 53 `localStorage` keys `arsenal.piano.*`, IndexedDB log buffer | page | `piano.js:287-288,1202,3317`; `log.js:103,169` | core (per-browser) |

**Packaging-critical:** every state root is computed **relative to the package file**, as `Path(__file__).resolve().parents[1] / "state"`:
- `performance.py:32`
- `take.py:22`
- `jam/cards.py:33`
- `conversation.py:15`

Inside a PyInstaller onefile that resolves into a temp extraction directory that is deleted on exit. In a read-only install location (Program Files, a signed `.app`) the writes fail.

### 1e. House-only couplings (what breaks on a stranger's machine)

| Coupling | Evidence | Impact on `/piano` |
|---|---|---|
| Redis 16379 / Akashic store | not imported on the serve path (import census); only `ai_setup_mcp.py` → `agent_cli.py:338` (`create_store(prefer_redis=True)`) | none for the page; the house MCP is unusable for strangers |
| Bifrost bus | `arsenal/tools/qm.py:9,28,74-75` only (not imported by serve) | none; exclude `arsenal/tools/` |
| Agent seats in names | scheme ids `synth-vandor/-navi/-heimdall/-sol`, plus probe-only `synth-asta`, `synth-rill` (`piano.js:1205-1214`) | cosmetic (display names are neutral); the probes 404 |
| LLM or Claude API key | **none.** No `anthropic`, `openai` or `api_key` in `arsenal/**/*.py`; no LLM hosts in the web files. "Claude" is any local agent that POSTs cues (`pianocue.py:1-18`). | none, which is good news for "any assistant" |
| Spotify | no hits in `arsenal/` | none |
| Hardcoded `E:\` | `serve.py:38` (`DEFAULT_ROOTS = [r"E:\Video Output E"]`), `__main__.py:19` | REC upload `mkdir`s under `E:\...` (`serve.py:634-635`). With no E: drive the POST returns 500, and the page falls back to Download. On macOS or Linux `Path("E:\\Video Output E")` is a **relative** path, so it creates a stray directory under the working directory. `/api/library` also exposes absolute paths (`serve.py:245`). |
| Hardcoded ports | `conversation-dock.js:2` (8796), `conversation.js:4` (8793) | dead Conversation button |
| KeyLab-named logic and copy | `piano.js:3318-3341` (ranking, echo guard), `piano.html:31` ("88 keys"), `piano.html:149` ("Play the KeyLab"), `piano.js:2` | see section 2 |
| Windows-only calls | none on the serve path. `lanes/gst_d3d12_soak.py:270-496` (ctypes, winreg) and `tools/qm.py:33,134` (tasklist, taskkill) are off the path. | none; exclude `lanes/` and `tools/` |
| Personal identity in API payloads | `by: "daniel"` at `deck.js:1018,1223` and `transport.js:732`; "Claude" hardcoded as the assistant name across the UI (`piano.html:102-121`) | cosmetic, but visible |

---

## 2. MIDI: "any MIDI keyboard or USB adapter"

### 2a. Mechanism

- **Web MIDI in the browser only.** There is no server-side bridge.
  - `navigator.requestMIDIAccess({ sysex: false })` at `piano.js:3342-3351`.
  - `sysex: false` means no extra permission tier.
- **Auto-connect at boot:**
  - First `navigator.permissions.query({name:"midi"})` (`piano.js:4564-4569`).
  - If denied, status is "MIDI permission denied: allow it in site settings".
  - Otherwise it calls `connectMIDI()`.
- **Hot-plug:**
  - `midi.access.onstatechange = () => refreshMidiInputs()` (`piano.js:3346`) rebuilds the select.
  - It marks "(disconnected)" (`piano.js:3369`).
  - It re-binds and calls `allNotesOff()` when the bound set changes (`piano.js:3395`).
  - The "Connect MIDI" button becomes "Rescan" (`piano.js:3348`, `piano.js:4009`).
- **Device selection:**
  - The `<select id="midi-select">` (`piano.html:35-39`) lists every input.
  - With more than one input it adds "all inputs except DAW ports" (`piano.js:3371`).
  - The choice is stored **by port name** (`piano.js:3317,3373-3376,3396`).
  - With nothing stored, it picks the highest `midiRank` (`piano.js:3334-3341,3377-3380`):
    - a KeyLab MIDI port scores 3
    - another KeyLab port scores 2
    - any other input scores 1
    - any name containing "daw" scores -1 and is excluded
    - Claude's loopback out scores -2 and is never bound

### 2b. Message handling (`piano.js:3400-3418`)

| Message | Handling |
|---|---|
| Note on `0x9n` | velocity > 0 is a note on; **velocity 0 is a note off** (`3407`, also `noteOn` guards `vel <= 0` at `2587`) |
| Note off `0x8n` | note off (`3408-3409`) |
| CC64 sustain | `setSustain(value >= 64, raw)` (`3411`); the HUD shows "down (CC64)" (`3989`) |
| CC120 / CC123 | panic: all notes off plus hush the assistant (`3412`) |
| Everything else (clock, channel and poly aftertouch, pitch bend, program change, CC1, CC66 sostenuto, CC67 soft) | **ignored** (`3413-3414`) |
| Channel | **all 16 channels merged**: `type = d[0] & 0xf0` (`3405`); no channel filter or selector |

### 2c. Range and board-size assumptions

- The drawn keyboard is fixed at **MIDI 21-108**: `const KEY = { first: 21, last: 108, ... }` (`piano.js:415`). The cue protocol uses the same range (`pianocue.py:51`).
- Notes outside 21-108 are still logged and still count toward key detection (`piano.js:2597`, `2610-2613`). They get no key, trail or scheme event (`piano.js:2598-2609`).
- **25/49/61/76-key boards all fall inside 21-108.**
  - The camera follows the sounding and recent notes (`piano.js:1112-1141`, `framing.follow`), so a small board's span is framed rather than lost in the 88.
  - A hardware octave shift just transposes the note numbers, so it works.
  - The on-screen instruments still draw an 88-key body. The KeyLab model narrows via `keySpan` hints (`piano.js:1198-1201,1410-1411`).
- **The computer keyboard is a fallback without MIDI:**
  - Z-/ and Q-P rows, Space for sustain, arrow keys shift the octave by up to ±3 (`piano.html:150`, `piano.js:3420-3430,4113-4120`).
  - A procedural Demo also works (`piano.js:3470-3474`).

### 2d. KeyLab 88 mk3 specifics

| Assumption | Evidence | Stranger impact |
|---|---|---|
| Auto-pick prefers `/keylab/` names; "DAW" substring ports are excluded | `piano.js:3334-3341` | A generic board still gets rank 1. On a machine with several rank-1 inputs (virtual loopMIDI ports, secondary "MIDIIN2 (...)"-style ports some USB devices expose on Windows, from knowledge), the first listed wins, which is non-deterministic. A device whose name contains "DAW" is silently skipped. |
| The echo guard names "Daniel's keyboard" | `piano.js:3319-3331` (`isDanielsKeyboard`) | works generically (stored choice or the single bound input); naming only |
| No KeyLab-specific CCs, pads, sysex or DAW-port parsing | only CC64, 120 and 123 are read | good |
| Instrument "KeyLab 88 mk3" 3D model | `piano.js:1217`; `instruments/keylab88mk3.js:12` says "No brand lettering or logo anywhere on the model" | product name in the menu; trade-dress caution (section 6) |
| Idle copy "Play the KeyLab", brand-sub "88 keys" | `piano.html:149,31` | copy change |

### 2e. Browser support and what the user is told

| Browser | Web MIDI | Page behaviour |
|---|---|---|
| Chrome, Edge (Windows, macOS, Linux) | yes. `127.0.0.1` is a secure context. | works |
| Firefox | gated behind a site-permission add-on prompt (Firefox 108+) | The page calls `requestMIDIAccess`; a refusal sets "MIDI blocked: ..." (`3350`). The add-on flow on `127.0.0.1` is **unverified**; drill it before promising Firefox. |
| Safari (macOS, iOS) | none | `navigator.requestMIDIAccess` is undefined, so status becomes "Web MIDI is unavailable in this browser" (`3343`) |

**The user is effectively told nothing:**
- `setMidiStatus` only writes `midi.status` (`piano.js:3399`).
- It is rendered only in the HUD row `hud-midi` (`piano.js:3974`).
- The HUD is `hidden` by default (`piano.html:132`) and toggled with H (`piano.js:3758`).
- The select just says "not connected" (`piano.html:37`).

### 2f. Concrete MIDI gaps for "any keyboard"

1. **No visible MIDI status or onboarding.** Unsupported browser, denied permission and "no inputs found" states are all hidden in the HUD (`piano.js:3343,3350,3399,3974`; `piano.html:132`).
2. **No channel filter.** Keyboards with drum pads usually send pad notes on channel 10 (typical of the KeyLab and many controllers, from knowledge), and those would be drawn and logged as piano notes (`piano.js:3405`). Layer, split or DAW-thru setups on several channels double up.
3. **MPE and multi-channel collisions.** `sounding` is keyed by note number only (`piano.js:2591,2599`). The same note on two channels (MPE, or two players) collides. Per-note pitch bend and pressure are ignored (`3414`).
4. **No sustain polarity invert.** Many cheap keyboards with a "wrong" pedal polarity send CC64 inverted, so the pedal would read as stuck down. There is no option; the threshold is fixed at 64 (`piano.js:3411`). Half-pedal is not drawn (only the raw value is passed).
5. **Other pedals ignored.** No CC66 sostenuto or CC67 soft pedal (`3413-3414`).
6. **Fragile auto-select.** The ranking is KeyLab-biased and ties are non-deterministic; the "daw" substring is excluded by default (`piano.js:3334-3341,3377-3380`).
7. **Windows port exclusivity (from knowledge).** With the classic WinMM driver, a port a DAW already holds may enumerate in Chrome but fail to open. Needs a troubleshooting line; Windows MIDI Services on recent Windows 11 relaxes this. Unverified here.
8. **Bluetooth MIDI (from knowledge).** Chrome on Windows has no native BLE MIDI (it needs a bridge app). macOS BLE MIDI appears through Audio MIDI Setup. Document it; do not promise it.
9. **House copy** (`piano.html:31,149`) and the KeyLab-first ranking read as "for one keyboard".
10. **No MIDI-learn or diagnostics panel.** Only the HUD's last-bytes readout exists (`piano.js:3417,3974`), and it is hidden.

---

## 3. Privacy and shipping hygiene

### 3a. Repository status

- **Public:** `origin https://github.com/balanced7/akashic-aurora.git` (`git remote -v`).
- **Licence:** Apache-2.0 (`LICENSE`); `NOTICE` reads "Copyright 2026 balanced7".
- **The practice data is git-ignored:** `.gitignore:122` has `state/*`, confirmed with `git check-ignore -v state/arsenal/performance`. The only tracked `state/` subtrees are `state/coord`, `state/drills` and `state/ci` (15 files).
- **Untracked `state/arsenal/` on this machine** (names and counts only; none of it may ship):

| Directory | Files |
|---|---|
| `band` | 30 |
| `cache` | 86 |
| `jam` | 24 |
| `performance` | 92 |
| `receipts` | 2,942 |
| `replay` | 3 |
| `score` | 2,373 |
| `takes` | 86 |

### 3b. Web-file scan

| Check | Result |
|---|---|
| Email addresses, the operator's own name handles, `sk-ant` keys, `DESKTOP-` hostnames in `arsenal/` | **none** |
| Real-looking session ids (`\d{8}-\d{6}-[0-9a-f]{8}`) in `arsenal/` | Only synthetic 2030-dated ids: `practice_riff.py:413`, `lanes/jam_verify.mjs:354` (labelled "synthetic"), `jam/schemas.py:1060`, `piano/deck-test.html:333` |
| The name "Daniel" in `arsenal/web` | 177 occurrences in 20 files, mostly comments. `piano.js` alone has 111, and `piano.js:1174-1175` quotes Daniel verbatim. Payload literals `by: "daniel"` at `deck.js:1018,1223` and `transport.js:732`. The test page `cues-test.html` has 12. |
| Tracked seed deck | `arsenal/jam/seed/deck-v1.json` holds 17 cards. The schema forbids moments or replays in the tracked seed ("the repo is public, so a seed card never carries moments", `jam/schemas.py:1270-1291`). Moment links live in the git-ignored `state/arsenal/jam/seed/moments-v1.json`. |
| Test fixtures | Tests declare their data synthetic: `tests/jam_groove.test.mjs:9`, `test_arsenal_practice.py:1-3`, `test_arsenal_jam_store.py:3`, `test_arsenal_jam_seed.py:15`, `test_arsenal_pianocue.py:4`, `test_arsenal_jam_cli.py:5`. Fixture session ids and dates are 2030 with page id `p-0a1c`. **Unverified:** I found no header in my search stating the `tests/fixtures/jam/riff_lydian_*` event streams (329 events each in the `l1` case) were synthesized rather than transcribed. Confirm before any fixture ships; the alpha need not ship tests at all. |

### 3c. What a clean alpha folder must exclude (allowlist recommended over denylist)

- `state/**` entirely: the performance, jam, takes, receipts, score, replay, band and cache directories.
- `arsenal/web/piano-lab-*`, `arsenal/web/piano-next.*`, the untracked `piano/listen/` and `piano/recorder*`.
- The test and harness pages: `piano/*-test.html`, `schemes/*-harness.html`.
- The First Light and Play suite: `first-light.*`, `play.*`, `replay.html`, `conversation.html`, `presets/`, `shaders/`, `graphs/`, `modules/`.
- These Python modules: `analysis.py`, `storyboard.py`, `floors.py`, `band.py`, `fl/`, `lanes/`, `tools/`, `replay.py`, `replay_harmony.py`, `conversation.py`.
- The spec markdowns, which carry house narrative: `PIANO-V2-SPEC.md`, `SPECTACLE*.md`, `PLAY-NIGHT-SPEC.md` and the rest.
- `piano/conversation*.js`, `piano/conversation.css` and the `<script>` at `piano.html:168`.
- `tests/fixtures/**`, unless provenance is confirmed.
- `__pycache__/`, which is present locally and ignored.

### 3d. Local-server security (it matters once strangers run the server)

- **It is bound to `127.0.0.1` only** (`serve.py:34,662`).
- **Origin checks exist only on some routes.** The cue POST checks Origin (`serve.py:520-522`), and so do the jam and deck POSTs (`serve.py:596-599`).
- **The practice-log POSTs have no Origin check** (`serve.py:287-292`). `_read_json` does not enforce a Content-Type (`serve.py:204-209`). Any website the user visits could therefore send a CORS-simple `text/plain` POST into the practice log.
- **No `Host` header check anywhere.** A DNS-rebinding page could read `GET /api/performance`, `/api/library` (absolute paths) and `/api/takes`.
- The recordings POST requires a video Content-Type, which is non-simple, so a browser preflights it, and the server has no `OPTIONS` handler. It is safe by accident.

---

## 4. Packaging options for "single click install"

The facts from the repo that shape every option:
- The server is stdlib Python, about 0.9 MB.
- The page is about 1.9 MB plus CDN libraries.
- Node is optional and only for the voicing, resolve and practice verbs.
- State paths are package-relative (section 1d).
- Web MIDI needs Chromium or Firefox-with-add-on.

Sizes and signing details below are from general knowledge (not measured here). Verify before quoting publicly.

| Option | Install friction | Size (approx.) | Signing, SmartScreen, Gatekeeper | Web MIDI inside | Offline | Update path | Fit with this codebase |
|---|---|---|---|---|---|---|---|
| **A. Hosted static web app** (GitHub Pages or similar) | Lowest: open a URL in Chrome or Edge | a few MB (after vendoring) | none | Chrome and Edge yes; Safari no; Firefox add-on | only with a service worker (none today; no manifest or SW in `arsenal/web`) | instant | **Works for the core visual.** Chord, key and Nashville detection is client-side (`nashville.js`, `chordread.js`, `spell.js`, `keysig.js`; no server calls in them). Demo and computer keys work. REC falls back to Download (`piano.js:3670-3674`). The log buffers locally forever, pointed at port 9 (`piano.js:2522-2537`). Cues show "no routes" (`piano.js:3038`); the deck is empty (`deck.js:397-403`). **Breaks:** the absolute `/web/...` and `/api/...` paths (`piano.html:12,14,167`) need root hosting or a rewrite; the assistant integration needs a local helper anyway (an HTTPS page calling `http://127.0.0.1` runs into Chrome's local-network-access prompts, from knowledge). |
| **B. Portable zip + embedded Python + double-click launcher** | Unzip, double-click `Start Piano.cmd`, which runs the server and opens `/piano` | Windows embeddable Python 3.11 about 11 MB zipped, plus the app about 3 MB, plus vendored three and fonts about 2-3 MB. **+ about 30 MB zipped** if Node is bundled. | `python.exe` in the embeddable zip is PSF-signed. A launcher script extracted from a Mark-of-the-Web zip may raise an "Open File – Security Warning" (unblock via Properties). There is no official embeddable Python for macOS, so it would need a relocatable build (python-build-standalone). An unsigned binary on macOS gets quarantined; Sequoia requires Settings, then Privacy & Security, then "Open Anyway". | Opens the **default browser**, which may be Safari or Firefox. On Windows the launcher can open **Edge**, which is preinstalled on 10 and 11 and has Web MIDI, as `msedge --app=http://127.0.0.1:8793/piano`. That gives an app-like window with guaranteed Web MIDI and no shell to build. | yes, once CDN assets are vendored | Manual re-download. A state dir outside the app folder survives upgrades. | **Closest to today.** Needs: state root moved to a per-user dir (section 1d); library root default changed (`serve.py:38`); `/` → `/piano`. Embeddable-Python quirk: its `python311._pth` ignores `PYTHONPATH` and the cwd, so add the app dir to the `._pth` file. |
| **C. PyInstaller or Nuitka single exe** | Download and run one exe | about 8-15 MB (stdlib only) | **Unsigned exes trigger SmartScreen "unknown publisher".** PyInstaller onefile bootloaders are a frequent AV false positive; Nuitka less so. Code signing (an OV/EV certificate or a cloud signing service) is the real fix. macOS needs Developer ID plus notarization. | browser, as in B | yes | manual | The onefile temp extraction dir **breaks all package-relative state paths** (`performance.py:32`, `take.py:22`, `jam/cards.py:33`) unless rewritten. The Node bridge (`pianocue.py:447`) is not bundled. Web assets need `_MEIPASS`-aware `WEB` (`serve.py:36`). |
| **D. Electron shell** | Installer or portable exe; feels native | about 90-110 MB download, about 250 MB unpacked | Same signing story as C, but the Windows installer is more visible. macOS **must** be notarized or Gatekeeper blocks it. | **Yes** (Chromium). Electron approves permission requests by default unless a handler is set; allow `midi` explicitly. | yes | electron-updater / Squirrel (needs signed builds for smooth updates) | Node is built in, so **`pianocue_voicing.mjs` and `practice_theory.mjs` run in-process** and the separate `node` dependency disappears. The Python server needs a sidecar (bundle B inside) or a port to Node (about 0.9 MB of Python; the log store, cue hub and jam API). Biggest build effort. |
| **E. Tauri shell** | Small installer | about 3-10 MB plus any sidecar | same signing needs as D | **Windows: WebView2 is Chromium, so yes.** **macOS: WKWebView has no Web MIDI.** Linux: WebKitGTK, no. macOS would need a native MIDI plugin (for example Rust `midir`) plus a JS shim for `requestMIDIAccess`. | yes | Tauri updater (signed) | Python sidecar via PyInstaller inherits C's issues; Node is not bundled. **Fails the macOS MIDI requirement without native work.** |
| **F. PWA** | "Install app" from Chrome or Edge on a hosted or localhost page | a few MB cached | none (it is a site) | Chromium yes; Safari and iOS no | yes, with a service worker | automatic on reload | Needs a `manifest.json` and service worker (none exist). Absolute-path caveat as in A. Can be layered on A or B: install the localhost page as an app. |

**Windows-first observation:** B combined with launching Edge in app mode (`--app` to `127.0.0.1:8793/piano`) gets:
- single double-click;
- guaranteed Web MIDI on every Windows 10 and 11 machine;
- no shell and no signing spend.

It reuses the stdlib server unchanged apart from the path and default fixes.

**macOS observation:**
- No option avoids either signing and notarization, or a Gatekeeper click-through.
- Tauri lacks Web MIDI.
- Electron is the only shell that carries Web MIDI.
- A browser-based B needs Chrome installed.

---

## 5. AI assistant integration

### 5a. What exists today that an assistant could use

| Surface | Evidence | House coupling |
|---|---|---|
| **Cue REST API: the assistant plays on the page.** `POST /api/piano/cue {"cue": {type: play or hover or sequence or clear, notes 21..108, velocity, hold_ms, arpeggio_ms, sound, label, detail, steps}}` | contract `pianocue.py:1-18`; route `serve.py:506-533`; the Origin check allows a missing Origin, so curl and CLIs work (`serve.py:520-522`) | none; generic already |
| `GET /api/piano/cues/status` (listeners, pages, caps) | `serve.py:255-256` | none |
| CLI verbs `py -m arsenal.pianocue`: play, hover, progression ("Abmaj9#11 \| Bb7sus4/Eb"), replay, clear, voicing (print only), status | `pianocue.py:20-22,795+` | Needs Node for chord names and voicings (`pianocue.py:447`). "py" is Windows-only. |
| Jam CLI verbs: card, deck, loop, try, jam, template | `jam/cli.py` (subcommands); `pianocue.py:21-22` | Node for resolve; `by: daniel` identities |
| **Practice analysis verbs** `py -m arsenal.practice`: sessions, brief, chords, progressions, keys, borrowed, colors, moment, name, compare, history, windows, harmony, analyze | `practice.py:34-43`. `brief` is described as "the one Claude reads before talking to Daniel (under ~80 lines)". | Needs Node (`practice.py:1328`). The copy is addressed to Daniel. |
| `py -m arsenal performance list \| summary <id\|latest> \| prune` | `__main__.py:70-79,242-291` | none |
| `GET /api/performance` (list), `GET /api/performance/<id>` | `serve.py:260-268`. The per-session GET returns `summary` **only for closed sessions**, else null (`performance.py:336-342`). | none |
| summary.md narrative "ending with questions for Daniel" | `performance.py:12-13,353-362` | copy addressed to Daniel |
| **A live chord, key or Nashville stream for assistants** | **Does not exist.** Detection runs in the page. Chord events reach the server only inside practice-log batches, about every 1 s (`log.js:146`, `performance.py:36-38` KINDS include `chord`, with `nns`/`nns_key` fields). No HTTP route reads an open session's events. SSE `/api/piano/cues` is server-to-page only. | to build |
| MCP servers in the repo | `.mcp.json` → `ai_setup_mcp.py`: FastMCP (`mcp`, `anyio`) wrapping `agent_cli` with a Redis-preferring store (`ai_setup_mcp.py:59-69`; `agent_cli.py:338`). **No piano or arsenal tools** (grep hit only an unrelated line 719). Cursor configs in `scripts/static/mcp/*.json` belong to the same house server. | house-only; not reusable |
| Assistant instruction files | `AGENTS.md` (191 lines, no arsenal or piano mention); `.cursor/rules/akashic-memory.mdc` (house); no `CLAUDE.md` or `GEMINI.md` at root | house-only |
| Conversation cards (question cards plus saved answers) | `conversation.py`, `replay.py` (8796), `piano/conversation*.js` | house-only today |

### 5b. Options per assistant (client capabilities from knowledge as of mid-2026; verify at build time)

| Assistant | Best-fit integration | Exists | To build |
|---|---|---|---|
| Claude Code (CLI or IDE) | Local **stdio MCP server** (`claude mcp add` or project `.mcp.json`) plus a `CLAUDE.md` template; it can also shell out to the verbs | cue REST, verbs, summaries | a small `piano-mcp` exposing tools: `status`, `list_sessions`, `session_brief`, `moment`, `name_voicing`, `play` / `hover` / `progression` / `clear`, and later `now` (live chord). A `CLAUDE.md` template. |
| Claude desktop app | Local stdio MCP via its config file | same | same MCP, plus a copy-paste config snippet |
| ChatGPT desktop | Custom connectors expect **remote** MCP, not local stdio (hedged) | cue REST | Copy-paste prompt plus an "export brief" button or file. A local REST doc. |
| OpenAI Codex CLI | MCP via its config (`~/.codex/config.toml`); reads `AGENTS.md` | verbs, REST | the same MCP; a piano-scoped `AGENTS.md` template |
| Cursor | `.cursor/mcp.json` plus `.cursor/rules/*.mdc` | REST, verbs | the same MCP; a rules template |
| Gemini CLI | MCP via `settings.json`; `GEMINI.md` context | REST, verbs | the same MCP; a `GEMINI.md` template |
| VS Code Copilot | `.vscode/mcp.json` | same | the same MCP; a config snippet |
| Local models (LM Studio, Ollama front-ends) | LM Studio has MCP support; Ollama needs an MCP-capable client (hedged) | REST | the same MCP; copy-paste prompts; documented REST |
| Anything else | A documented **local REST (+ SSE) API** and copy-paste prompts | cue POST, status, performance GET | an OpenAPI or markdown API doc; a `GET` route for an open session's recent chord events or an SSE "now" stream |

**Cross-cutting build items:**
1. **A Python-only voicing path, or bundled Node.** Every naming verb shells out to `node` today (`pianocue.py:447`, `jam/resolve.py:102`, `practice.py:1328`).
2. **Neutral copy.** Replace "Claude" and "Daniel" addressing in the UI and summaries (`piano.html:102-121`, `performance.py:12-13`, `practice.py:37`) with a configurable assistant and user name.
3. **An MCP implementation choice.** A stdlib JSON-RPC stdio server keeps the "no third-party packages" property. FastMCP adds the `mcp` dependency, which `ai_setup_mcp.py:67` already uses.

---

## 6. Licences and attribution

| Asset | Source | Licence | Evidence | Flag |
|---|---|---|---|---|
| three.js r186 core + addons (EffectComposer, RenderPass, UnrealBloomPass, OutputPass, RoundedBoxGeometry, Reflector, BufferGeometryUtils, GPUComputationRenderer) | jsDelivr npm `three@0.186.0` | MIT | `piano.html:19-20`; addon imports in section 1b | Include the MIT notice when vendoring |
| Bravura (SMuFL music font, Steinberg) | npm `@vexflow-fonts/bravura@1.0.2` | SIL OFL 1.1 | `piano.js:1674`; `score/paint.js:20` | Include the OFL; VexFlow code is not used |
| Archivo, JetBrains Mono, Noto Music, Outfit, Jost (plus Raleway on the lab page) | Google Fonts | SIL OFL 1.1 | `piano.html:10`; `piano-lab-instruments.html:11` | Self-host. Loading from Google sends the user's IP (a GDPR concern in the EU). |
| mediabunny 1.56.2 | jsDelivr | MPL-2.0 (from knowledge; verify) | `piano/recorder.js:45` (untracked) | Not on the alpha path |
| Audio | none | n/a | No audio files anywhere in `arsenal/web`. The assistant's voice is oscillator synthesis: three detuned oscillators, sine and sawtooth (`piano/cues.js:1019-1058,1238`). | clean |
| 3D instruments (concert grand, upright, suitcase EP, vintage synth, crystal grand, KeyLab) | built in code; procedural `CanvasTexture`/`DataTexture` (counts in `instruments/*.js`, `moonwater.js`, `spectacle*.js`) | Apache-2.0 (repo) | no `.glb`, `.gltf`, `.png`, `.jpg`, `.hdr` or `.ktx` in `arsenal/web` (grep) | **Trademark caution:** "KeyLab 88 mk3" is an Arturia product name in the menu (`piano.js:1217`), and the model reproduces that product's layout (the file says no logo or lettering, `keylab88mk3.js:12`). `glass-piano.js:7` cites Kawai CR-40A proportions (dimensions only, low risk). |
| Icons, images | none found | n/a | n/a | clean |
| Krumhansl-Kessler key profiles | published research constants | n/a | `performance.py:76`; `piano.js:246` | clean |
| Seed deck (17 cards) | authored in-house | Apache-2.0 | `arsenal/jam/seed/deck-v1.json` | clean (privacy rule enforced by the schema) |
| Scheme and instrument code authored by fleet agents | this repo | Apache-2.0 | `schemes/*.js`, `instruments/*.js` | Attribution by callsign is internal naming, not a licence issue |

---

## 7. Proposed alpha scope (grounded in the findings; for Vandor to accept or reject)

### MUST
1. **Neutral first-run MIDI flow.**
   - Show the MIDI status in the top bar, not only the HUD (`piano.js:3399,3974`; `piano.html:132`).
   - Show a banner for Safari (no Web MIDI), Firefox (add-on prompt) and denied permission.
   - Replace "Play the KeyLab" and "88 keys" copy (`piano.html:31,149`).
   - Make auto-select deterministic: prefer hardware ports over virtual ones and remember the choice (`piano.js:3334-3380`).
2. **A channel selector** (omni by default) with an "ignore channel 10 pads" toggle (`piano.js:3405`).
3. **A sustain-polarity invert** toggle (`piano.js:3411`).
4. **Vendor three r186 plus the used addons, Bravura and the five Google fonts** for offline use and privacy (`piano.html:10,19-20`; `piano.js:1674`). Add `.woff2` to `STATIC_TYPES` (`serve.py:41-45`).
5. **Move state out of the package.** The per-user data root:
   - Windows: `%LOCALAPPDATA%\...`
   - macOS: `~/Library/Application Support/...`

   The code to change is `performance.py:32`, `take.py:22`, `jam/cards.py:33`. The REC default root moves to the user's Videos folder (`serve.py:38`).
6. **The launcher opens `/piano`** (`serve.py:226-231` redirects `/` to First Light). Suggested: a Windows portable zip with embedded Python that opens Edge `--app` (section 4, option B).
7. **Hide house-only surfaces:**
   - the Conversation dock (`piano.html:168`)
   - the probe schemes `synth-asta` and `synth-rill` (`piano.js:1212-1213`)
   - the First Light and Play routes and pages
   - `by: "daniel"` literals (`deck.js:1018,1223`; `transport.js:732`)
8. **An allowlist export** of the alpha folder (section 3c). No `state/`, labs, tests, spec markdowns or `lanes/`/`tools/`.
9. **Origin and Host checks on every POST and on private GETs** before strangers run the server (`serve.py:204-209,287-292`; section 3d).
10. **Practice-log disclosure.** Local-only, a visible On/Off (already at `piano.html:96-100`), and a "delete my practice data" path (the CLI prune exists at `__main__.py:253-271`; there is no UI).
11. **`THIRD-PARTY-NOTICES`** covering three (MIT) and the fonts (OFL), plus the Apache `LICENSE` and `NOTICE`.

### SHOULD
1. **The Node decision.** Either bundle Node (about 30 MB) or give the voicing and naming bridge a Python or in-browser path. Otherwise the assistant's chord verbs, the deck resolve and the practice verbs are dead on a stranger's machine (`pianocue.py:447`, `jam/resolve.py:102`, `practice.py:1328`).
2. **A small local `piano-mcp` server** plus templates (`CLAUDE.md`, `AGENTS.md`, `.cursor/rules`, `GEMINI.md`) plus copy-paste prompts and a REST doc (section 5b).
3. **A read route for live and near-live harmony.** Recent chord, key and Nashville events of the open session, or an SSE "now" stream (section 5a gap).
4. **Neutral assistant naming** in the UI: "Assistant" in place of "Claude" (`piano.html:101-121`), configurable.
5. **An auto-seed of the 17-card deck** on first run if deck cards ship (`jam/runs.py:835,928-931`); the deck is otherwise empty.
6. **A MIDI diagnostics panel** (last bytes, per-channel activity), promoting the hidden HUD readout (`piano.js:3417`).
7. **A rename of the "KeyLab 88 mk3" instrument label** to a generic name (`piano.js:1217`).

### LATER
- Jam band, try-in-time, deck editing, the replay "Hear me" and conversation cards (`transport.js`, `deck.js`, `replay.js`, `conversation*.js`).
- Score engraving and MusicXML export (lab-only today).
- Electron shell with signed installers and auto-update; a notarized macOS build.
- A PWA manifest and service worker.
- The hosted static demo build (absolute-path rewrite).
- MPE-aware note keying by (channel, note) (`piano.js:2591`); CC66 and CC67.
- The untracked recorder (mediabunny MP4) and the listen/ DSP work.

### Keep in the alpha
- The 3D keys, trails and sustain visuals.
- Schemes: Classic, Upright Roll, Straight Roll, Bead & Beam, Glow Echo, Afterglow Roll.
- Instruments: page keys, concert grand, upright, suitcase EP, vintage synth, crystal grand, KeyLab (renamed).
- Spectacle and Moonwater atmosphere; 9:16 and 16:9 framing.
- Chord name, Nashville numbers, key and key signature.
- Computer keys and Demo; REC with Download fallback.
- The practice log (local); cue REST (assistant plays and hovers).

---

## 8. Open questions for Daniel (five, each with a recommended default)

1. **Does the assistant's hand (cues) ship in alpha-1, and do the jam band and deck?**
   *Default:* ship cues (play, hover, progression, clear) with a small MCP; keep the jam band, deck and conversation cards in a hidden "labs" flag until the Node question is settled.
2. **Practice log for strangers: on or off by default?**
   *Default:* on, local-only, with a first-run notice and a one-click "delete my practice data". It is what makes the assistant integration useful.
3. **First platform and signing spend.**
   *Default:* Windows portable zip (embedded Python, opens Edge in app mode), unsigned for the alpha, with documented SmartScreen and "unblock" steps. macOS as "run from source with Chrome" until a $99/yr Apple Developer ID is approved. Revisit Electron at beta.
4. **The KeyLab 88 mk3 instrument: keep the name, rename it, or drop it?**
   *Default:* keep the model, rename the menu entry to a generic "88-key studio controller", and mention it in the README as inspired by Daniel's own board.
5. **Where does the alpha live: a folder in `balanced7/akashic-aurora` releases, or a new slim public repo produced by an allowlist export?**
   *Default:* a new slim repo generated by an export script from this repo, so strangers never clone the house (and `state/` can never leak by accident).
