# Teardown card: THE ARSENAL (the creative half of the house)

Date: 2026-10-13. Seat: Vandor (claude), a read-only subagent of the "deconstruct the house" run.
Method: `teardown-card.md` (draft v1). All eight rows are filled, every claim is labelled, loop altitude follows
`docs/pillar-analysis-method.md`, and the card ends with a Great Sage report.
Scope: `arsenal/`. That covers the narrow-waist contract, First Light and its server, the media toolbox
(`arsenal/media`), TikTok, the presentation family, the piano page and its practice and story tools, the jam and the
band, the verification bench, and tonight's shader school (corpus, reader, dissector, census, atlas, library,
composer, twins, cards, Lab, Shelf and the licence line). It also covers how the arsenal joins the rest of the house,
and Daniel's creative arcs.

**What I did NOT change.** I edited no house file except this card. I ran no boot, learn, note, lock, write or
`--write`/`--save`/`--reap` flag, and no git command that changes anything (I used `--no-optional-locks` reads). I did
not connect to port 8793, start any server, open a browser or use the GPU. Side effects I could not avoid, stated so
nobody mistakes them for organic traffic:
- (a) The recall-at hook fired on about 45 of my shell calls. That bumped "surfaced" counters and added
  injection-ledger rows.
- (b) Importing arsenal modules may have refreshed `__pycache__` files (gitignored).
- (c) I wrote scratch files: three in my scratchpad and one stray `/tmp/x` in the Git Bash temp folder (outside the
  repo).
- (d) The licence-line scan read the private corpus into memory. That is its design. It prints only the file, line
  and corpus id for a breach, never the text. I have not reproduced any corpus id or text here.
- (e) Node imported `arsenal/shaders/headless.mjs` to read one exported table. It launched nothing.

**Privacy.** I did not open the practice log, the story oracle, the shader corpus, the licence triage note,
`private/`, or any other private plane. Those planes appear below by role only (corrected at review: an earlier
draft gave their sizes, counts and dates, and "existence metadata is a leak", `core/trust/private_plane.py:17-19`).

---

## The picture in one paragraph (for Daniel)

If the knowledge half of the house is the CPU and memory, **the arsenal is the graphics card and the sound card,
plus the workbench where your art gets made**. Like a discrete GPU, it barely touches the rest of the motherboard. It
does not read or write the house's Redis, ledger or memory at all. It talks to the house through a few narrow ports:
- the `agent_cli media` door;
- the recall-at hint that fires when an agent is about to type `ffmpeg`;
- the piano cue channel (my hand on your piano page).

Inside, it is really five boards on one bus:
- **First Light and its server.** The video and visualizer stage, on port 8793.
- **The piano.** The live page, plus an offline "practice room" that reads your sessions back.
- **The media toolbox.** One set of video tools so agents stop hand-building their own.
- **The shader school.** A parts library for light, built from the shaders you love without copying a line of them.
- **The verification bench.** Meters and test cards, so a seat that cannot watch a render can still measure it.

**Thesis (one sentence).** The arsenal holds a higher evidence standard than most of the house:
- every tool states what it cannot see;
- the licence line is measured, not remembered;
- your live session sits behind fences written into the code.

But its feedback loops close **at your eye and nowhere else**. The instruments exist; the wires that would act on
them either wait at a gate that is yours (by design) or were never connected:
- the licence scan at commit time;
- the toolbox's pre-registered re-measure;
- two forecasts a month past their dates;
- a stale page index.

---

## Row 1: Purpose

- **What it is for.** "Daniel's modular media suite" (`arsenal/__init__.py:1`; the prog description in
  `arsenal/__main__.py:14`). **observed.** Concretely, five purposes, each in its own words:
  1. *First Light*: "Daniel drags a clip from his library onto a page. It plays through a VFX effect, pulses with the
     clip's own audio, and a knob on his Arturia KeyLab 88 mk3 turns the hue. Every run is recorded as a take"
     (`arsenal/FIRST-LIGHT-SPEC.md:8`). **observed.**
  2. *The piano and practice room*: an "offline harmony engine over Daniel's piano practice log, so we can talk theory
     about HIS playing" (`arsenal/practice.py:1`). The live cadence judge exists because Daniel asked for the story of a
     progression to be visible "while it is being played rather than in the report afterwards"
     (`arsenal/web/piano/cadence-live.js:3-8`). **observed.**
  3. *The media toolbox*: "One toolbox for every agent, the editor and the coaching runs". It exists because mining
     five days of runs found "2,437 throwaway scripts", with the contact-sheet grid hand-built 333 times
     (`arsenal/media/README.md:3-6`). **observed.**
  4. *The shader school*: "break down the primitives and group them by category ... so we can have reusable
     structures" (Daniel, quoted at `arsenal/shaders/dissect.py:4` and `census.py:7`), and "import them all into our
     vfx tooling" (`arsenal/shaders/shelf.py:7`). **observed.**
  5. *The quality bar*: "It would be incredible if this fidelity, quality, beauty and elegance could become our
     baseline!" (`arsenal/VISUAL-QUALITY-BASELINE.md:4`). **observed.**
- **For whom.** Daniel first, as the player, the creator and the person who posts to TikTok. Agents second, as tool
  users (the toolbox, the cue channel, the practice verbs). **inferred** from the five purposes above.
- **The outcome that would make it worth keeping.** Daniel makes and shares art he is proud of, faster, and agents
  stop rebuilding the same tools. The second half has a pre-registered test: hand-built grids, hand-typed ffmpeg
  paths and single-image read streaks each halved, per agent-hour of media work, one week after v0
  (`research/in-flight/video-primitives-2026-10-12/PRIMITIVES-SPEC.md:768-772`). **observed.** No equivalent
  pre-registered test exists for the first half; it is judged by Daniel's eye (`VISUAL-QUALITY-BASELINE.md`, "Beauty
  remains an authored judgment"). **observed.**

## Row 2: Observables (what we can see without trusting its self-description)

All values were read today, 2026-10-13, between about 09:35 and 10:00 local time.

| what | value | source |
|---|---|---|
| code | 465 tracked files under `arsenal/` (115 .py, 108 .js, 31 .mjs, 31 .glsl, 26 .html, ...), 130,660 lines of py/js/mjs/glsl/frag; **117 more files untracked** on disk (582 total, excluding caches) | `git ls-files`, `find` |
| history | 119 commits since `d8fb56b4` (2026-09-13, First Light). Per ISO week: W37 20, W38 42, W39 2, W40 10, W41 14, W42 31 | `git log -- arsenal` |
| tests | about 110 test files named for the arsenal family | `ls tests` |
| doors | `py -m arsenal`: 14 verbs. `py -m arsenal.media`: 20 verbs. `py -m arsenal shader`: 16 verbs. `agent_cli media`: a passthrough. A media MCP door exists but is **not registered** in any of the 5 config files I checked | runs; grep of `.mcp.json`, `~/.claude.json`, both settings files |
| servers | **8793 First Light is LISTENING** (process 48156; I did not connect). 8797 shader lab: not running. The census lists six ports for one family of pages: 8787, 8793, 8795, 8796, 8797, 8799 | `netstat -ano`; `arc-arcs.md:735-739` |
| registry | 32 module manifests: 17 media, 7 present, 8 from the September contract; **0 GLSL** | `py -m arsenal inspect` |
| shader library | 99 modules: 68 house files plus 31 legacy bench chunks read in place. They provide 278 functions. `lib lint`: "no floor broken". **`index.json` is STALE** | `shader lib list / lint / index` |
| atlas | 13 families, 81 categories, 575 parts (P0 193, P1 265, P2 117). **All 193 P0 parts are built**. 235 parts are fully built; 269 of 736 planned function names | `shader atlas`, `--status P0 --json` |
| licence line | the private corpus; scanned 5,105 files in 36 s. **31 breaches, all in 9 untracked files.** 365 hits sit inside the baseline (273 entries held, 0 grown); 226 are exempt | `py -m arsenal shader licence-line` |
| private planes (role only) | `state/arsenal` (git-ignored) holds the receipts, the media oracles, the shader corpus and its work, the score, the practice log and the story oracle. Sizes, counts and dates are deliberately not given | `.gitignore:136` |
| takes | take folders exist (a private plane: role only) | folder listing |
| governance | the conductor's task ledger holds **one** arsenal task (T399, done). The forecast registry holds F011 (hit) plus **F012 and F013, both OPEN, 23 and 29 days past their horizons** | `task list`, `forecast list`, registry fold |
| GPU render lock | free | `node arsenal/lanes/gpu_lock.mjs status` |

**Lived experience (observed, my own session).** The recall-at hook pushed the `media` verb at me twice, at exactly
the moments I typed `py -m arsenal.media`. So the toolbox's reach wire works, at least for impressions.

## Row 3: Mechanism (how inputs become what we observe)

### 3.1 The narrow waist (the contract of 2026-09-13)

Think of this as the PCIe spec that every card on the bus agrees to. Every part is **observed** in code:
- **Exact time.** A time is (clock, epoch, ticks, timebase). Ticks are integers and the timebase is an exact fraction,
  so "nothing here ever passes through a float". An epoch changes on seek or loop, so a value from before a seek can
  never be compared with one from after it (`arsenal/timebase.py:1-7`).
- **Typed ports.** 18 port types, 9 memory domains (cpu, d3d11, webgl, ...), and a caps check where "unknown is not a
  yes" (`arsenal/mediatypes.py:7-27`, `:51`).
- **Module manifests and one registry.** `arsenal/registry.py`; manifests in `arsenal/modules/*.json`.
- **A graph and a loud plan.** `py -m arsenal plan` prints every node, engine, licence and copy boundary
  (`arsenal/plan.py`; I ran it, see V8).
- **The take ledger.** Append-only; "Epochs only move forward" (`arsenal/take.py:1-7`).

### 3.2 First Light's server (port 8793)

- Standard library only, bound to 127.0.0.1 (`arsenal/serve.py:1-4`, `:37`). **observed.**
- It serves Daniel's library roots (`E:\Video Output E`) by id with HTTP Range, so the browser can seek
  (`serve.py:38`, `:66-70`). **observed.**
- It also routes the practice log, takes, the piano cue channel, the jam and deck, Edit mode, saved looks and the MIDI
  port census (route strings in `serve.py`). **observed.**
- The pages it serves: `first-light`, `play`, `piano` (5,505 lines of JS on three.js r186), the four study pages
  (Gyre, Crystal studies, Chord tree, Wind), the piano lab pages, Edit mode and house-round (`arsenal/web/`).
  **observed.**

### 3.3 The piano and its practice and story tools

A loop of six parts, each **observed**:
1. **The live page records a session** into the practice log. That log is append-only, with idempotent uploads so a
   browser can resend after a reload, and it lives under `state/arsenal/performance`: "Daniel's playing never leaves
   the machine" (`arsenal/performance.py:1-10`).
2. **The practice verbs** read sessions offline, in both directions in time (`arsenal/practice.py`, 5,325 lines,
   read-only by its own rule at `:3-5`). `practice_riff.py` reads Daniel's notes against a jam run.
3. **The story oracle** runs the practice analyzer over every session and writes the private answers the live judge
   is proven against (`arsenal/story_corpus.py:1-12`).
4. **The live cadence judge** (`arsenal/web/piano/cadence-live.js`) is a "rule-for-rule twin" of `practice._cadence`.
   It allocates nothing and is pinned to the oracle by `tests/piano_cadence_live.test.mjs`. **It is imported only by
   its tests**, so it is not yet on the page (grep, V13 run).
5. **My hand on the page**: the cue channel. `POST /api/piano/cue` and a server-sent-event stream (`arsenal/pianocue.py:1-12`)
   let an agent light things on Daniel's live page; a cross-site request gets a 403.
6. **Around it**:
   - the replay companion on 8796 (`arsenal/replay.py:3-4`);
   - private question cards (`arsenal/conversation.py:1`);
   - Nashville numbers, as a Python/JS twin pair (`arsenal/nashville.py:1-4`);
   - the jam, with cards, runs and a tempo map, also a twin pair (`arsenal/jam/__init__.py`);
   - the FL Studio band: pattern files Daniel drags in himself, and "Nothing here talks to FL"
     (`arsenal/band.py:1-6`);
   - the MIDI port census for the Rescan hint (`arsenal/midiports.py:1-12`).

### 3.4 The media toolbox (`arsenal.media`, built 2026-10-12)

Twenty verbs. Each one follows four house rules, all **observed** in `arsenal/media/README.md:12-24`:
1. Originals are never touched.
2. Every ffmpeg call goes through `ff.run()`.
3. Every result has one house shape (`api`, `source`, `params`, `computed_with`, payload, and **`blind`**, which says
   what the tool cannot see) and is written as a receipt.
4. Failures are closed, with a one-line reason.

**The house clock ruling.** File time means seconds from the file's start, and the container offsets are converted at
the edges. It is pinned on MPEG-TS fixtures (`README.md:26-48`). **observed.**

**Four doors**, each **observed**:
- the CLI;
- `agent_cli media` (`agent_cli.py:5406`, `:9360`);
- an MCP door, "Register (Daniel's call; nothing registers it automatically)" (`arsenal/media/door.py`);
- manifests `arsenal/modules/media.*.json`.

**Neighbours.** TikTok (`arsenal/tiktok.py`, Daniel's drag-and-drop daily tool, `arsenal/tools/tiktok-ready.cmd`) and
the presentation family (`arsenal/present`: one scene, several targets).

### 3.5 The shader school (built 2026-10-13, overnight)

A parts pipeline. Hardware analogy: datasheets in, a standard-cell library out, with a multimeter on every cell.
1. **Corpus** (private). Shaders Daniel loves, harvested through a signed-in browser and a clipboard door, saved whole
   under `state/arsenal/shaders/corpus/` (gitignored) (`corpus.py:1-12`, `cli.py:35-40`). **observed.**
2. **Reader and dissector.** A GLSL reader (`glsl.py`) turns code into evidence. A raymarch is "a loop whose body
   calls a distance function and advances t by what it returned"; detectors match "the SHAPE of the math"
   (`dissect.py:4-11`). **observed.**
3. **Census.** It counts how often each technique recurs and what travels together; "the frequency table orders the
   library's build list" (`census.py:1-9`). **observed.**
4. **Atlas.** A Markdown parts catalogue that Daniel gates (`primitive-atlas-draft.md`, 198 KB). It is converted to
   `atlas.json` by `atlas_build.py`, and a pin fails if the two drift (`atlas_build.py:4-9`). **observed.**
5. **Library and composer.** House GLSL modules (Apache-2.0, "written fresh from the mathematics") in
   `arsenal/web/glsl/`. One resolver and composer in Python (`modules.py`) has a browser twin (`modlib.js`), and both
   emit dependency-ordered GLSL for webgl2, webgl1, three.js or Shadertoy-style hosts (`modules.py:1-10`). **observed.**
6. **Meters.** Every library module has a CPU twin in numpy: "Like a bench multimeter beside the oscilloscope"
   (`twins/__init__.py`). Test cards are rendered on SwiftShader with a NaN probe (`cards.py:1-9`). There is a lint
   of craft floors. **observed.**
7. **Lab and Shelf.**
   - The lab server runs on 8797: loopback only, read-only, with a Host-header check against DNS rebinding.
     **observed** (`shaders/serve.py:1-40`).
   - It refuses 8793 outright. **observed** (the same docstring).
   - A study-only shader gets a 403 for its pictures and source. **observed** (the same docstring).
   - The Shelf is "a parts drawer of datasheets": the Loved shaders as licence-safe cards (`shelf.py:7-12`).
     **observed.**
   - The Workbench pages live in `arsenal/web/lib/workbench/` (8 files, all untracked at the time of reading).
     **observed.**
8. **The licence line.** Every file git would commit is cut into 12-token shingles and compared with every corpus
   pass. Breaches present at commit `9d6f29ff` form a baseline that "may only shrink". Its limits are printed on every
   run (`licence_line.py:1-60`). **observed.**

### 3.6 The verification bench

Each part is **observed**:
- **Floors.** "Pinned assertions on pixels, so an eye is never spent on what a histogram can catch" (`floors.py:1-8`).
- **Motion.** Pacing as a number, "so a seat that cannot watch video" can compare twenty takes (`motion.py:1-9`).
- **Boost.** Radial banding.
- **Storyboard.** A contact sheet that declares its own denominators.
- **Coupling.** Which audio channels each preset really reads.
- **Lanes.** Chrome, jam timing, play and alias verifiers.
- **The GPU render lock.** "One headless render at a time on this machine's GPU" (`arsenal/GPU-LOCK.md:3`).
- **The SwiftShader harness.** It keeps shader-school renders off the GPU entirely and judges each page's renderer
  string (`arsenal/shaders/headless.mjs:1-14`, `:69`).

### 3.7 How the arsenal joins the rest of the house

- **Arsenal → house.** No imports of `core`, `agent`, `scripts` or Redis anywhere in `arsenal/` (grep). One tool
  shells out to `agent_cli bifrost-sync --consume` (`arsenal/tools/qm.py:75`). **observed.**
- **House → arsenal.**
  - `agent_cli.py` (the `media` verb) and four scripts import it: `ask_vision.py`, `piano_card_art.py`,
    `piano_roll_pack.py` and `checkers/check_door_parity.py`. **observed.**
  - Recall-at's verb channel reads the `media` help text (`tests/test_arsenal_media_reach.py`). **observed.**
- **Shared with the cockpit.**
  - The 31 legacy bench chunks in `design/vfx-chunks/` are read in place by the library. **observed**
    (99 = 68 + 31).
  - The `shader-craft` skill.
  - The Bifrost console's look (8787), whose `bifrost_ui.py` is DeepSeek's to change (`build-spec-reconciled.md:21`).
    **observed.**
- **Governance runs on a different track.** Arsenal work is steered by its own documents:
  - specs (`FIRST-LIGHT-SPEC`, `PIANO-V2-SPEC`, `PLAY-NIGHT-SPEC`);
  - the contract fence (`fences/media-arsenal-contract/`);
  - build specs with numbered rulings (`research/in-flight/shader-school-2026-10-13/build-spec-reconciled.md`);
  - memory.

  It is not steered by the conductor's ledger (one task) or `docs/ROADMAP.md`, which "neither mentions the visual
  arcs in any depth" (`arc-arcs.md:85-87`). **observed** (task ledger) and **observed by a sibling** (ROADMAP).

### 3.8 Daniel's creative arcs (spot-checked, not re-derived)

Tonight's arc census (`research/in-flight/shader-school-2026-10-13/arc-arcs.md`, sections 2 and 4) maps about fifteen
"visual machines" built in two months. The timeline:

| dates | arcs |
|---|---|
| 08-01 onward | the cockpit and the VFX bench |
| 09-13 | the media contract, First Light, Play, the 3D piano for TikTok |
| 09-14/15 | the jam, Spectacle, Moonwater, instruments |
| 09-21/22 | Gyre, the crystal studies, the visual baseline |
| 09-28 | the presentation family |
| 10-07 | the studies enter git; NOW PLAYING designed |
| 10-12 | the toolbox and Edit mode |
| 10-12/13 | the story layer and the lean light |
| 10-13 | the shader school |

Its headline: every machine has its own power supply, sound card and colour chip (at least 9 note-colour
implementations, 22 files with their own animation loop, 6 MIDI inputs), and the shader-school module core is "the
first shared bus" (`arc-arcs.md:24-52`). **observed by a sibling.** I spot-checked four of its claims (V13 and the
fork checks). Three had already drifted within hours; see trap 4.

## Row 4: First principles (each tested: what evidence or law does it rest on?)

| # | principle | test: what it rests on | verdict |
|---|---|---|---|
| P1 | **Techniques transfer; code does not.** The repo is public under Apache-2.0; the corpus is mostly CC BY-NC-SA 3.0 (`shaders/__init__.py:5-11`) | an external law: the NonCommercial and ShareAlike terms cannot be relicensed as Apache. 0 files tracked under `state/arsenal` (git) | **axiom, with evidence** (observed) |
| P2 | **Daniel's playing never leaves the machine** (`performance.py:4-5`) | the operator's value (a valid axiom per the card); enforced by `state/*` in `.gitignore:136` | **axiom** (observed) |
| P3 | **Time is exact or it is wrong.** Integer ticks, fraction timebases, epochs; the house clock ruling | measured offsets: MPEG-TS starts at 1.4 s, the first frame sits 0.021 s in (`media/README.md:31-34`) | **axiom, with evidence** (observed) |
| P4 | **A seat cannot see its own render, so visuals must become numbers, but beauty stays authored** (`floors.py:4-8`, `motion.py:7-9`, baseline "Beauty remains an authored judgment") | true for the main text seats (`motion.py:7`: "this model cannot"); a vision seat exists (`scripts/ask_vision.py`) | **constraint, partly an assumption**: it holds per seat, not for the house (inferred) |
| P5 | **Daniel's GPU is fragile.** One GPU render at a time; the shader lab renders on the CPU; nothing renders live on page load | `GPU-LOCK.md:3`; `headless.mjs:10-14`; build-spec ruling 5; the crash history is cited at `arc-arcs.md:128-130` | **axiom, with evidence** (observed) |
| P6 | **Daniel's live session is sacred.** Never port 8793; an approved look never moves without him | the operator's value; written into code twice (`shaders/serve.py:59` declares 8793 forbidden and `:102-108` refuses it; the twin is `headless.mjs:64`), tested in V15 | **axiom** (observed) |
| P7 | **"Agents use what is in reach and ignore what is not"** (`PRIMITIVES-SPEC.md:746`) | one mining (2,437 scripts; `ui_shot.py` used 0 times while 41 agents wrote 170 browser rigs) | **an empirical regularity, not a law.** Its *remedy* ("a hint at the moment of action changes behaviour") is an **assumption until the pre-registered re-mine runs** (trap 1, inferred) |
| P8 | **"A rule kept by memory fails on the first tired night"** (`licence_line.py:7-9`) | the house's own history (the pre-commit gate that silently no-opped until 2026-08-01, `scripts/githooks/pre_commit.py:64-70`; the mirror accidents, `scripts/mirror.py:27-33`) | **axiom, with evidence**, and violated by its own corollary (see Loop A3) |
| P9 | **Two languages, one truth: a twin with a parity pin** (jam tempo map, cadence judge, module core, CPU twins) | a method, not a law; it holds where measured (V10b: 278 of 278) | **method** (observed) |

## Row 5: Capabilities (what you would need to HAVE to build or run it)

- **Skills.**
  - GLSL and shader mathematics; WebGL2 and three.js.
  - ffmpeg, PyAV and media timing.
  - Music theory (cadences, Nashville numbers, voicing).
  - Audio DSP.
  - Python and Node.
  - The craft judgement to tell a cosmetic preset from a driven one.

  **inferred** from the module list.
- **Tools.**
  - Chrome: hardware decode for First Light; headless with SwiftShader for the lab.
  - FFmpeg builds (two are in use, V11), PyAV, numpy, faster-whisper.
  - Web MIDI and an Arturia KeyLab 88 mk3.
  - OBS, FL Studio.
  - The League client's replay API on 2999.

  **observed** (specs, `media/__main__.py:38`).
- **Data.**
  - Daniel's recordings (`E:\Video Output E`).
  - The practice log.
  - The private corpus, which exists **only on this machine**. The licence test skips "a fresh clone has none"
    (`tests/test_glsl_licence_line.py:720-722`).

  **observed.**
- **Access.**
  - A signed-in Shadertoy browser session; the harvest needs one human click (`cli.py:147-150`). **observed.**
  - The League replay, which dies with patch 26.21 on 2026-10-21 (`media/README.md:82`). **observed.**
- **People and money.**
  - Daniel's eye and gate decisions.
  - claude seats as builders and judge; Heimdall (DeepSeek) fencing every stage.
  - Navi is "past her spend grant" (`build-spec-reconciled.md:28`).

  **observed.**

## Row 6: Required steps (build order from nothing; what blocks what)

1. **The narrow waist first.** Exact time, port types and caps, manifests and registry, graph and plan, take ledger.
   Everything later plugs into it. (This was the 2026-09-13 order: `d8fb56b4` "exact-time kernel, loud plan, take
   ledger".) **observed.**
2. **A loopback server with library roots and Range serving.** Without it, nothing reaches a browser. **inferred.**
3. **The practice log**, append-only and idempotent. It blocks every offline verb and the oracle. **inferred** from
   the import chain `story_corpus → practice → performance`.
4. **The verification bench before visual iteration**: floors, storyboard, lanes, the GPU lock. Without it, every
   defect costs a human look (`floors.py:4-7`). **inferred.**
5. **The media toolbox, with all four doors in the same commit as each primitive.** Reach is the whole point
   (`PRIMITIVES-SPEC.md:752-766`, "built WITH each primitive, not after"). **observed.**
6. **The shader school.** The licence line must come before the library's licence, because ruling 2 rests the
   Apache licence on that measurement (`build-spec-reconciled.md:13-14`). Then the order is reader → dissect →
   census → atlas (Daniel gates) → library, twins, lint and cards → composer → Lab and Shelf. Hosts come last: the
   bench, Studio, and First Light, which "waits for Daniel: an approved look" (ruling 7). **observed.**
7. **The critical path today** runs through Daniel's gates:
   - the one question (auto-update approved looks, or show a before and after);
   - the cadence judge's visible mark;
   - registering the MCP door;
   - the OBS track setup (`media/README.md:78`).

   **observed.**

## Row 7: Invariants and failure modes

| invariant | how it is held | what a break looks like from outside |
|---|---|---|
| Originals are never touched | inputs opened read-only; outputs go to `--out` or state (`media/README.md:14-16`) | a changed recording; I did not test this |
| Loopback only; never 8793 | constants plus code refusal on both twins (V15) | Daniel's piano drops, or the corpus is reachable off the machine |
| No corpus code in a tracked file | the scan plus a test that pins tracked files (`tests/test_glsl_licence_line.py:937-970`) | a public commit carrying someone else's code. **Today the scan is red (V1)** |
| Daniel's playing stays local | `state/*` gitignored | a session file in git; 0 today (observed) |
| Epochs only move forward | `take.py:6-7`; `StaleEpoch` | a seek that compares stale times; a refused batch |
| One GPU render at a time; the lab never on the GPU | the lock (`GPU-LOCK.md`); forced SwiftShader (`headless.mjs:69`) | a TDR: the desktop app crashes and will not relaunch (memory index: "GPU Driver Crashes Desktop App") |
| Approved looks never move without Daniel | ruling 8; the one question | a look he signed off changes overnight |
| One writer per edit document | a rev counter; a stale PUT returns 409 (`media/README.md:61`) | an agent and Daniel overwrite each other |

**Failure modes I observed, not just predicted:**
- The library's page index is stale (V4). Pages that read `index.json` see an older module list, and nothing on the
  page says so. **inferred** from `modules.py:1124-1127`.
- Three **tracked** lab pages (`piano-lab-res.html`, `-vfx.html`, `-judge-res.html`) load scripts that are
  **untracked** (`<script src="/web/piano-lab-*.js">` at line 98 of each). On a fresh clone those pages are broken,
  and publishing the scripts would breach the licence line (V1). **observed** (git status and the src lines);
  **inferred** (the consequence on a clone).
- Render jobs live in server memory; a restart loses their state (`media/README.md:74`). **observed** (a named seam).

## Row 8: Verification (predictions that could fail, the test, the result)

| # | prediction (made before looking) | cheapest test | result |
|---|---|---|---|
| V1 | The licence line holds: exit 0, no breach | `py -m arsenal shader licence-line` (36 s; writes nothing, by grep) | **FAILED.** 31 breaches in 9 files, **all untracked**: 25 in the four `piano-lab-*.js` forks (dated 09-13 and 09-14), 2 in `research/reviewed/reverse-engineering-2026-10-13/audio-music.md` (lines 1490-1491, written 09:23 today by a parallel workflow, still uncommitted at 09:45), 3 in untracked tests, 1 in `CarConcept.glb`. The tracked tree is clean beyond its baseline: 273 entries held, 0 grown. |
| V2 | Tonight's P0 build list is not fully built yet | `shader atlas --status P0 --json` | **FAILED, in the house's favour.** 193 of 193 P0 parts are built. |
| V3 | The library passes its own floors | `shader lib lint` | **HELD.** "99 modules, no floor broken". |
| V4 | The page index is current | `shader lib index` (no `--write`) | **FAILED.** "index.json is STALE"; exit 1. Other workflows are adding modules right now (`shaders/twins/` written at 09:33). |
| V5 | The documented door `py -m arsenal shader --help` lists the verbs (`arsenal/__main__.py:166`, `shaders/__init__.py:4`) | run it; also `-h`; also the module directly | **FAILED.** Both say "unrecognized arguments". `py -m arsenal.shaders.cli --help` works but lists **5 of the 16** verbs. Root cause **inferred** from code: (a) the `REMAINDER` passthrough at `__main__.py:167` does not capture a leading option; (b) run as `__main__`, the module is a second copy, so the extensions register into the other copy's `VERBS` (`dissect.py:2183` and its siblings write `cli.VERBS`). |
| V6 | The GLSL modules sit in "the one registry" (`modules.py:8`; `registry.py` already validates a `shader` block) | `py -m arsenal inspect` | **FAILED.** 0 of 32 manifests are GLSL; `lib manifests --write` has never been run into `arsenal/modules/`. |
| V7 | The arsenal's forecasts were scored after their horizons | forecast registry fold (read) | **FAILED.** F012 (First Light end to end, horizon 2026-09-20) and F013 (Piano v2, at least 58 fps, horizon 2026-09-14) are still OPEN. |
| V8 | The September graphs still plan against today's grown registry | `py -m arsenal plan arsenal/graphs/{first-light,play-night}.json` | **HELD.** Both exit 0. Minor: the separator prints as a replacement character on a cp1252 console. |
| V9 | Every Play preset actually reads audio | `py -m arsenal coupling` | **HELD, literally.** 8 of 8 read at least 2 channels. The census's own verdict rates 1 of 8 "cosmetic" (`aurora-ribbons`). |
| V10 | Every library module names an existing CPU twin | parse each module header; check the file exists | **HELD**, 68 of 68. But only **1 of 68** uses the documented `file:fn` form (`twins/__init__.py`); 67 name the file only. |
| V10b | At least 90% of the provided functions have a same-named twin (the "grep finds both halves" rule) | regex over the twin files, with a negative control that returned False | **HELD.** 278 of 278 (100%). |
| V11 | The two ffmpeg finders (TikTok's and the toolbox's) pick the same binary | call `tiktok.find_ffmpeg()` and `media.ff.locate()` (both read-only by inspection) | **FAILED.** TikTok uses imageio's bundled 7.1; the toolbox uses a saved StemRoller build (source: config). The cost is low today: TikTok encodes with libx264 (`tiktok.py:945`), and both builds carry it and AMF. The README names this seam (`media/README.md:62`, `:67`). |
| V12 | The doctor's path loads no numpy, PyAV or OpenCV ("must not pay for", `media/__init__.py:7`) | `py -X importtime` on `arsenal.media.__main__` + `ff`; control on `arsenal.floors` | **HELD.** 0 heavy imports; the control registered numpy (1), so the test could fail. (I did not call `doctor` itself, because it can write a caps cache.) |
| V13 | The census's claims still hold: `piano.js` about 5,480 lines; the WebCodecs recorder and the raster policy are still unplugged | `wc -l`; grep importers | **HELD.** 5,505 lines; `recorder.js` is imported only by `recorder-test.html`, `raster-policy.js` only by its test. |
| V14 | The GPU render lock is free (no burst mid-run) | `gpu_lock.mjs status` (no `--reap`) | **HELD.** `"held": false`. |
| V15 | The shader server refuses 8793 and non-loopback binds, and accepts 8797 | call the pure `validate_bind()` (no socket); read the browser twin's exported table | **HELD.** 8793 refused; `0.0.0.0` refused; 8797 and port 0 allowed; twin table `{8793: ...}`. |

---

## Loop altitude (does the signal flow back?)

| loop | value chain | status | evidence |
|---|---|---|---|
| A1 the story loop | Daniel plays → practice log → offline analysis → oracle → live judge → **the page shows the story** → Daniel hears and sees it | **built to the last link; that link waits at Daniel's gate.** This is a deliberate fence, not a defect | `cadence-live.js` imported only by tests; the gate is cited in the memory index, "no visible mark before it" |
| A2 the reach loop | agents hand-roll ffmpeg → mining → toolbox and hint → agents adopt it → **re-mine** → reword the hints | **OPEN at the re-measure.** It is pre-registered for about 2026-10-19, but I found no task, forecast or schedule for it. The reach test pins the *impression* (the hint surfaces), not the *adoption* | `PRIMITIVES-SPEC.md:768-772`; `tests/test_arsenal_media_reach.py`; `task list`, `forecast list` |
| A3 the licence loop | corpus → technique → house module → **scan** → commit → public | **measured, not gated.** No pre-commit, pre-push or CI step runs the scan (search: `scripts/githooks`, `scripts/mirror.py`, `.github`, `scripts`, `core`, `agent`). CI cannot run it, because the corpus exists only here, so the test skips there. The test's own comment says "Commit a file only after the CLI reads it clean", which is a rule kept by memory, and the CLI has been red since mid-September because of four untracked forks | V1; `pre-push:40-42`; `test_glsl_licence_line.py:958-961` |
| A4 the parts loop | Loved shaders → dissect → census → atlas (Daniel gates) → library → twins, lint, cards → Lab and Shelf → Daniel's taste → atlas rulings | **closed through a document gate**, the best-closed loop here: the atlas is regenerated from the Markdown Daniel reads, and a pin fails on drift. One link lags: the page index (V4) | `atlas_build.py:4-9`; V2, V3, V10b |
| A5 the upgrade loop | a module improves → surfaces that use it update | **OPEN by design.** It waits on "the one question" (auto-update, or a before and after) | `build-spec-reconciled.md:37-40` |
| A6 the calibration loop | forecast at the gate → score at review | **OPEN.** Two arsenal forecasts are unscored, 23 and 29 days late | V7 |
| A7 the look loop | render → numbers (floors, motion, coupling, cards) → Daniel's eye → baseline document | **partly closed, honestly bounded.** The numbers are floors and say so; beauty is authored | `floors.py:10-13`; the baseline doc |
| A8 the registry loop | GLSL module → manifest → `inspect` and `plan` graphs | **not connected.** The registry can validate a shader block, but holds none | V6 |

## The five traps, where I saw them

1. **False first principles.**
   - P7's remedy ("a hint at the moment of action changes behaviour") is an assumption until the re-mine runs. The
     reach test pins only the hint.
   - Smaller docstring sentences that no longer match the code:
     - "`py -m arsenal shader --help` lists the verbs" (V5);
     - "one registry for the whole house" (V6);
     - "names its twin ... `<area>.py:fn`" (V10: 1 of 68);
     - the `arsenal/__main__.py:1` verb list (it names 7 of 14).
2. **Chesterton's fence.**
   - **The four untracked lab forks.** They exist so the judging harnesses could fork the piano core beside
     Daniel's untouched page (`PIANO-V2-SPEC.md:26`, cited at `arc-arcs.md:431`). Keeping them untracked is
     *correct*, because they carry corpus-shared runs. Do not delete them; declare them local.
   - **The licence test pins tracked files only.** This is a judge's ruling: "a test that fails on someone else's
     uncommitted file tests the machine, not the repo". Keep it; add a staged-files gate instead.
   - **The two ffmpeg finders.** TikTok's tests pin its order, and converging "waits for Daniel"
     (`media/README.md:62`). Leave them.
   - **The cadence judge kept off the page.** Daniel's gate. Leave it.
   - **The lab on its own port.** So that "a hung SwiftShader burst ... must not take the piano down"
     (`shaders/serve.py:4-6`). Keep it.
3. **Reductionism.**
   - The licence line's real behaviour lives in a coupling. Every part is right on its own: the scanner, the
     test's scope ruling, and the forks staying untracked. Together they make an alarm that is always red, so it
     stops being read (inferred). The leak is in the loop, not in any part.
   - Likewise, the toolbox's worth lives in an agent's moment of action, not in the toolbox.
4. **The map is not the territory.** Tonight's arc census, written hours ago, has already drifted on three points:
   - the library folder "contains just `modlib.js`" (now 68 module files);
   - `lean.js` was "untracked" (now tracked and wired into `piano.js`);
   - `piano.js` was 5,480 lines (now 5,505).

   One more instance: the atlas header counts *function names* (269 of 736) while the rows count *parts* (235 of
   575), on one screen with no unit change marked.
5. **Goodhart.**
   - The reach test measures impressions, not adoption (A2).
   - The coupling census counts uniform references, a proxy for "reads the music"; 1 of 8 presets passes it
     cosmetically (V9).
   - **The counter-example worth copying:** the licence line prints its own limits every run ("this guards against
     pasting, not against derivation"), and floors call themselves floors, not quality. The arsenal names its
     Goodhart edges better than most of the house.

---

## Great Sage report

> **Notice.**
> - The licence scan is red: 31 breaches in 9 untracked files.
>   - 25 sit in four month-old `piano-lab-*.js` forks.
>   - 2 sit in a reverse-engineering research note written at 09:23 today and not yet committed
>     (`research/reviewed/reverse-engineering-2026-10-13/audio-music.md:1490-1491`).
>   - The tracked tree holds its baseline exactly (273 held, 0 grown). (V1)
> - No commit hook, push hook or CI step runs that scan. CI cannot, because the corpus lives only on this machine
>   (`test_glsl_licence_line.py:720-722`, `pre-push:40-42`).
> - Three tracked lab pages load scripts that are untracked (line 98 of each).
> - The page index of the GLSL library is stale (V4). The registry holds 0 GLSL modules of 32 (V6).
> - `py -m arsenal shader --help` errors, and the module-direct route shows 5 of 16 verbs (V5).
> - Forecasts F012 and F013 are unscored, 23 and 29 days past their horizons (V7).
> - The toolbox's pre-registered re-mine (due about 2026-10-19) has no task or forecast.
> - The media MCP door is unregistered.
> - The arsenal imports nothing from the house core; the house reaches it through `agent_cli media` and four scripts.
> - All 193 P0 parts are built. 278 of 278 library functions have a same-named CPU twin. Lint is clean. The bind
>   fences hold. The GPU lock is free.
>
> **Analysis.**
> - The arsenal is a discrete card on the house's bus: high internal discipline, very narrow coupling (from the
>   import grep, the four doors, P1-P6).
> - Its loops close at Daniel's eye or a document he gates (A1, A4, A5, A7) and almost never by machine. That is
>   right for taste, and wrong for the licence line, which is a legal floor, not a taste (from A3 and P1).
> - The always-red licence CLI is the most dangerous state an alarm can be in: one that is right, ignorable, and
>   one `git add` away from a public breach. The four forks keep it red; the missing staged-files gate keeps it
>   unenforced (from V1 and A3).
> - The arsenal is governed by specs, fences, rulings and memory, not by the conductor's ledger. So its forecasts
>   and its re-measure fall through the house's scoring machinery (from V7, A2, and the one task in the ledger).
>
> **Unknown.**
> - Whether First Light met F012's four criteria. Takes exist; I did not read them.
> - Whether `CarConcept.glb`'s hit is printable noise in a binary or an embedded shader.
> - Whether anyone still opens the lab fork pages.
> - Whether the toolbox has changed agent behaviour since 2026-10-12.
> - What the private licence triage note already says (not opened).
> - Anything rendered, played or served. I opened no page and touched no server.
> - Not exercised:
>   - the presentation targets;
>   - the band;
>   - the League tools;
>   - Edit mode;
>   - the cue channel;
>   - the replay companion;
>   - `practice.py`'s 5,325 lines beyond their docstring.
> - Search boundary:
>   - `arsenal/**` code and docs;
>   - `tests/` names, plus `test_glsl_licence_line.py`, `test_arsenal_media_reach.py`, `piano_cadence_live.test.mjs`;
>   - `scripts/githooks`, `scripts/mirror.py`, `.github/workflows/ci.yml`;
>   - five MCP config files;
>   - the task ledger and the forecast registry;
>   - `research/in-flight/{shader-school-2026-10-13,video-primitives-2026-10-12}`;
>   - the folder names under `state/arsenal` (their sizes were measured, and are withheld here).
>
> **Proposal** (smallest first; nothing is deleted; each part's reason for existing is stated):
> 1. *Now, a message only.* Tell the reverse-engineering workflow that `audio-music.md:1490-1491` shares corpus
>    runs, before it commits that note. Exists because: research notes quote what they study; this one quoted too
>    long a run.
> 2. *One line each.*
>    - Make `py -m arsenal shader --help` reach the shader parser (route a leading `-h`/`--help` to `shader_main`).
>      Exists because: the `REMAINDER` passthrough lets shader verbs own their parsing.
>    - Correct three docstrings: `arsenal/__main__.py:1` (7 of 14 verbs); `twins/__init__.py` (the `file:fn`
>      form); `modules.py:8` ("the one registry", until A8 is decided).
> 3. *Daniel's call, no code.* Declare the four `piano-lab-*.js` forks local-only, with an ignore rule or a move
>    under `state/`, so a red licence scan means something again. Exists because: the judging harnesses forked the
>    piano core beside his untouched page (`PIANO-V2-SPEC.md:26`). They must never be published, and today their
>    tracked HTML pages are broken on any clone. Decide alongside whether those three pages stay tracked.
> 4. *Small slice.* Add a `--staged` scope to `licence-line` and call it from `pre-commit` when the corpus is
>    present (skip when absent, as the test does). Exists because: "a rule kept by memory fails on the first tired
>    night" (`licence_line.py:7-9`). It keeps the judge's ruling intact, because staged files are your own.
> 5. *Owner's step.* The shader-library workflow runs `py -m arsenal shader lib index --write` when tonight's
>    builds settle (it is theirs, not mine).
> 6. *Scheduling.* Register the toolbox re-mine (about 2026-10-19) as a forecast or task, so purpose 3 gets its
>    verdict. Ask Daniel the two questions that are his:
>    - register the media MCP door?
>    - run the League replay before 2026-10-21?
> 7. *Scoring.* Score or void F012 and F013 (Vandor, with Daniel's word on whether First Light ran end to end).
> 8. *Design conversation.* Should the 68 GLSL modules join `arsenal/modules/` (that would triple the registry), or
>    should the registry federate? And the one question that already waits: auto-update approved looks, or show a
>    before and after.
> 9. *Leave alone, on purpose.* The two ffmpeg finders (V11: low cost, pinned order, Daniel's call). The cadence
>    judge off the page (his gate). The lab on its own port.
>
> **Verification.** 16 predictions, all run read-only:
> - 9 held: V3, V8, V9, V10, V10b, V12, V13, V14, V15. V10b and V12 had working negative controls.
> - 7 failed: V1, V4, V5, V6, V7, V11, and V2, which failed in the house's favour.
>
> **Proceed?** YES / NO. Every proposal waits for Daniel:
> - 1 is a message to a sibling workflow, time-sensitive while that note is uncommitted.
> - 2 is three one-liners.
> - 3 is his decision about his own lab pages.
> - 4 is a small slice.
> - 5-7 are bookkeeping.
> - 8 is a conversation.
