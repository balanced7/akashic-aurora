# Arc census: the house visual methodology and its instruments

Status: in-flight research (one of seven readers, shader school night) · Date: 2026-10-13 · Seat: claude (Vandor), census subagent
Scope as briefed: `arsenal/floors.py`, `arsenal/boost.py`, `arsenal/motion.py`, `arsenal/storyboard.py`, `arsenal/lanes/`
(the GPU lock and the headless Chrome lanes), `arsenal/GPU-LOCK.md`, `scripts/vfx_probe_*.py`, `scripts/ui_shot.py`, the
visual test files (`tests/*vfx*`, `*floors*`, `*looks*`, `*spectacle*`, `*glass*`, the shader-craft currency pin), how renders
are verified (receipts, reference images, colour metrics, Chrome flags), and `docs/method-baseline-2026-07.md` plus
`docs/CONDUCT.md` as they apply to visual work.

Method: read every file in scope, then followed the evidence one hop out where the method actually lives (the
piano-presentation fence, the light-instruments round, the Synthesia bake-off measurement summary, the adaptive
anti-aliasing study, the 2026-09-14 tool review, the new shader harness written tonight, the media receipt module).
Read-only commands only: `git log` / `git ls-files` (no writes), two greps over tests, and three small CPU-only runs on
images already on disk: `py scripts/vfx_probe_chroma.py` (twice) and `py -m arsenal floors --dir
fences/piano-presentation/evidence` (twice). No browser, no server, no GPU render, nothing from the shader corpus opened.

Citations are `file:line`, relative to `E:\AI-Setup`. Following the house's own rule (`docs/method-baseline-2026-07.md:94-101`),
claims I concluded rather than read or ran are marked **(inferred)**. Anything marked **(ran)** I observed tonight.

---

## 0. The answer in one page (for Daniel)

The house already has a real **visual method**, and it is good. It just lives in five places at once: a skill
(`shader-craft`), a quality baseline doc, two design docs for the piano, a fence's reconciliation, and the habits baked
into a dozen scripts. Read together, they describe one loop:

1. **Build** a look from your words, with one clear motion idea and a geometric fact you can test before anything is
   pretty (`arsenal/VISUAL-QUALITY-BASELINE.md:23`, `:56-63`).
2. **Judge** it two ways at once. A *machined floor* that a blind seat can check from numbers (is the frame dead, blown
   out, flat, unreadable, stuttering?), and a *crafted ceiling* that only eyes can judge, which is your gate
   (`.claude/skills/shader-craft/SKILL.md:8-11`, `design/CONTRACT.md:106-119`). The best rounds rendered every candidate on
   the **same fixtures from the same served bytes**, put blind judges with different lenses on them, and kept the numbers
   beside the scores, never instead of them (`fences/piano-presentation/half_vandor.md:3`,
   `research/in-flight/piano-light-instruments-2026-09-17/brief.md:180-197`).
3. **Pin** what was decided: a failing test written first, invariant tests for geometry, a golden hash where the output
   must not move, saved looks with conflict-safe storage, and a declared, signed exemption where a black frame is the design
   (`arsenal/floors.py:120-137`, `tests/piano_lean.test.mjs:634-655`, `tests/piano_looks_store.test.mjs:137-166`).
4. **Ship** with a receipt that says what was measured, under what conditions, and what was *not* measured
   (`arsenal/floors.py:245-246`, `arsenal/lanes/chrome_verify.mjs:42-46`), through the verified-done gate
   (`.claude/skills/verified-done/SKILL.md:12-25`).

The hardware analogy: the instruments are a **test bench**. `floors` is the power-on self-test (it catches a dead or
shorted board, not a slow one). `boost` is the gain knob on an oscilloscope (it makes a faint signal visible so two people
stop arguing about what is there). `storyboard` and `motion` are the logic analyser (they turn a video into a timeline of
events). The **GPU lock** is bus arbitration with a watchdog: one device on the bus at a time, a heartbeat so a dead holder
is detected, and a log of every forced release (`arsenal/GPU-LOCK.md`, `state/arsenal/gpu-render.lock.reaps.jsonl`, 9
reaps so far, every one a dead or over-time holder). The lookdev panel is a blind listening test on a fixed benchmark
suite.

What is missing for "tweak one module and have everything update" is not method, it is **plumbing**:

- **Five separate browser drivers** each carry their own copy of the same DevTools client and their own Chrome flag list,
  and the flag lists have drifted (two lanes default to a *visible* window although the house rule says headless only;
  section 8).
- **Five different brightness formulas** and **three colour definitions** are in use across the metrics (section 7).
- The **acceptance floors the piano fence actually needed** (title vs gesture brightness, lit area per band, pressed-key
  colour, repeat continuity, flicker) were written into a reconciliation and **never built into the floors tool**. Tonight
  I ran the floors over the seven evidence frames that the fence diagnosed as underexposed, washed out and hairline-thin:
  **all seven pass every floor (ran)**. The floor is honest about this (it says a pass "never" means good,
  `arsenal/floors.py:306-309`), but it means the house's real visual acceptance still lives in prose.
- Most defects the 2026-09-14 tool review found are **still in the code** (section 8), and the node test suites that pin
  looks, the GPU lock and the referee are **outside the ship gate** (section 4).

Section 9 lists the clean places to cut shared modules. The single best seam already exists: `arsenal/media/receipt.py`
describes itself as "the storyboard/motion/floors manifest habit in one place" (`arsenal/media/receipt.py:1-5`).

---

## 1. The reusable methodology: how a look is built, judged, pinned and shipped

This is the synthesis. Each step names where the house already does it, so the method can be lifted into one shared kit
rather than re-derived per arc.

### 1.1 Build

| Step | What the house does | Where |
|---|---|---|
| Start from Daniel's words, verbatim | Every brief opens with intent and his words; the fence brief quotes seven of his lines before any analysis | `docs/CONDUCT.md:23-26`, `fences/piano-presentation/brief.md:5-27` |
| One sentence, a focal form, three observable criteria | "Write the intended visual experience in one sentence. Choose the focal form, motion hierarchy, palette roles and three observable acceptance criteria." | `arsenal/VISUAL-QUALITY-BASELINE.md:59` |
| A concrete motion idea, with a testable invariant first | Gyre: a spinning arm whose stem stays fixed; the invariant (radius preserved under every rotation) is pinned before elaboration | `arsenal/VISUAL-QUALITY-BASELINE.md:23`, `tests/gyre_motion.test.mjs:5-26` |
| Separate timescales | immediate source motion, slower overall movement, lingering history | `arsenal/VISUAL-QUALITY-BASELINE.md:14`, `:25` |
| Simulate the cause, not three symptoms | one ray-marched medium gives bloom, god rays and streaks that cannot disagree | `.claude/skills/shader-craft/SKILL.md:96-97` |
| Variants differ in form, not palette | "A palette swap alone does not fulfill a request for a new silhouette or motion identity." | `arsenal/VISUAL-QUALITY-BASELINE.md:31` |
| Prototype without touching product files | Lookdev looks are "runtime override scripts"; the brief forbids product edits during a round; the card-art renderer serves a patched copy of a module through a browser route instead of editing it | `research/in-flight/piano-synthesia-mode-2026-09-15/lookdev-straight-lines/straight-lines-proposal.md:3`, `fences/piano-presentation/brief.md:87`, `scripts/piano_card_art.py:20-23` |
| The machined floor of shader writing | house template, `highp` always, counts injected once, derivatives only on continuous values, ping-pong feedback, cost = pixels × steps × emitters | `.claude/skills/shader-craft/SKILL.md:37-93`, cookbook `:245-254` |
| Outside shaders: techniques transfer, code does not | ingest wraps by `#define`, refuses what cannot work, licence gate before public use | `.claude/skills/shader-craft/references/house-glsl-cookbook.md:60-69`, `tests/test_vfx_ingest.py:1-17` |

### 1.2 Judge

The judging method that produced the best results (the piano-presentation fence, the Synthesia bake-off, the
light-instruments round) has seven parts. None of them is written down in one place.

1. **Same fixtures for every candidate.** The fence used three: quiet (Db6/9 at velocity 38), hard (same chord at 112),
   dense (Gbmaj13#11 at 112), plus an optional repeat frame (`fences/piano-presentation/half_vandor.md:131-141`). The
   light round used six named fixtures: single strikes across the range at three velocities, a pedalled low chord, a pedal
   lift mid-chord, a staccato run, a glissando, fast repeats (`research/in-flight/piano-light-instruments-2026-09-17/brief.md:180-187`).
2. **Same served bytes.** Each half records the file hashes it rendered from, and checks served equals disk
   (`fences/piano-presentation/half_vandor.md:3`; `straight-lines-proposal.md:110`). The jam lane stamps page-file hashes at
   start and end because "other lanes edit the piano page too" (`arsenal/lanes/jam_verify.mjs:90-91`).
3. **Numbers beside the picture, never as the gate.** "Metrics sit NEXT to the image, never as a gate"
   (`.claude/skills/shader-craft/references/house-glsl-cookbook.md:47-50`); "Beauty remains an authored judgment"
   (`arsenal/VISUAL-QUALITY-BASELINE.md:19`); the design fails if the soft case loses its form, a strike erases an old one,
   or hard "merely gets whiter", and "passing numeric checks alone does not establish beauty"
   (`arsenal/SPECTACLE-DESIGN.md:133-135`).
4. **Blind judges with distinct lenses, then a merging judge.** Fence: wow / rhythm-game / pianist-learning
   (`straight-lines-proposal.md:14-24`). Light round: Daniel's magic / strike realism / sustain truth / craft, three judges
   per entry and a fourth to merge, "the house does not rank seats. Daniel picks"
   (`research/in-flight/piano-light-instruments-2026-09-17/panel.md:3`).
5. **Controls.** A hidden-entry baseline separates machine drift from the entry's cost ("Most of the frame-time increase is
   therefore machine drift", `research/in-flight/piano-synthesia-mode-2026-09-15/final/measure-summary.md:61-64`); a
   same-velocity control pair before judging a soft/hard fix (`research/in-flight/rill-3d-tools-review-2026-09-14/assessment.md:77`);
   an in-memory counterfactual that toggles one suspected cause and back (black bars traced to one material flag,
   `measure-summary.md:28-36`).
6. **A reference image when the question is fidelity.** The anti-aliasing study rendered a 16-samples-per-pixel ground
   truth of one frozen, seeded frame and scored every option by mean error, edge error (Sobel mask), PSNR (peak
   signal-to-noise ratio) and temporal shimmer under a slow pan, plus GPU-synchronised cost
   (`research/in-flight/piano-spectacle-2026-09-13/adaptive-resolution-aa.md:133-174`). This is the house's only true
   "golden reference" method for pixels.
7. **Daniel picks from real frames, side by side.** "Done looks like: Daniel sees two or three looks as real frames side by
   side, portrait and landscape" (`fences/piano-presentation/brief.md:27`); "Daniel tries the three looks on a live page
   before anyone polishes one" (`fences/piano-presentation/reconciliation.md:216`); taste is gated "at milestones, not
   per-commit" (`design/CONTRACT.md:117-119`).

### 1.3 Pin

| Kind of pin | Example | Where |
|---|---|---|
| Red first, then green (pre-registration, M3) | floors exemptions: RED commit 20:53, RED-fix 20:54, mechanism 20:58 on 2026-09-17 | `git log -- arsenal/floors.py` (ran); `docs/method-baseline-2026-07.md:182-193` |
| Geometry invariants | radius preserved, stem fixed, rider camera rigid, wind zero at the emitter | `tests/gyre_motion.test.mjs:5-94` |
| Golden hash of draw calls | the lean painter's same-colour cases hashed per view against values taken before a design decision | `tests/piano_lean.test.mjs:634-655` |
| Saved looks as data | 17 visual settings in 4 groups, an apply order, settings refused while recording | `tests/piano_looks_registry.test.mjs:85-106`, `:174-202` |
| Conflict-safe storage | server revision numbers, a 409 conflict merges by id and retries once, offline changes queue and replay | `tests/piano_looks_store.test.mjs:137-198`, `tests/test_arsenal_looks_route.py:84-96` |
| Old records never rewritten | additive defaults for old preset libraries, failures keep the library intact | `tests/gyre_presets.test.mjs:17-50` |
| Recipes outside browser storage | known control values plus launch URLs, with an honest scope line ("URLs recreate motion families rather than identical frames") | `arsenal/visual-references/2026-09-21/gyre-recipes.json` (schema `arsenal.gyre.reference-recipes/v1`), `arsenal/VISUAL-QUALITY-BASELINE.md:43-52` |
| Declared expected absence | an exemption must carry reason, owner, date; it is scoped to named floors; the number still prints; the table ships empty and a test goes red if it grows | `arsenal/floors.py:120-137`, `tests/test_floors_exemptions.py:57-62` |
| The skill stays true | every path the shader skill names exists; every line its cookbook quotes is in the source *and in HEAD* | `tests/test_shader_craft_skill_cites_live_surfaces.py:26-47`, `:142-160` |

### 1.4 Ship

1. **Fresh evidence, one real render eyeballed** (`.claude/skills/verified-done/SKILL.md:12-25`).
2. **The ship gate**: boundaries, doc currency, wiring, reconciliation gate (M1), pre-registration (M3), verbatim
   citation (M6), then the full pytest suite as a ratchet (`scripts/ship.py:28-57`). Caveat in section 4: the node visual
   suites are not in it.
3. **A receipt with conditions and confessions.** The Gyre receipt is the model: viewport, buffer size, MSAA, GPU and
   backend, ten-second samples after a one-second warm-up, interval counts, and an explicit split between what was
   exercised and what was "inspected in code" (`logs/gyre-20260921/results.md:7-21`). The baseline makes this a rule:
   "report observed success, proposed improvement and unverified behavior separately"
   (`arsenal/VISUAL-QUALITY-BASELINE.md:78`).
4. **Credit precisely**: Daniel's physical inspiration and discoveries, earlier presets by name, "similar design
   vocabulary is evidence of continuity, not proof that a particular older shader was copied"
   (`arsenal/VISUAL-QUALITY-BASELINE.md:54`).
5. **Fold back**: every new defect class becomes a lesson and a line in the skill (`.claude/skills/shader-craft/SKILL.md:141-142`).

---

## 2. Instrument census

### 2.1 `arsenal/floors.py`: the visual floors (API `arsenal.floors/v0`)

- **What it is**: four cheap pixel checks so "an eye is never spent on what a histogram can catch" (`arsenal/floors.py:1-8`).
  `not_dead` (mean luma ≥ 0.020 and peak ≥ 0.15, `:61-69`), `not_blown` (≤ 8% of pixels with all three channels ≥ 250,
  `:72-80`), `variety` (luma standard deviation ≥ 0.010, `:83-88`), `legibility` (contrast (Lhi+.05)/(Llo+.05) on the 5th
  and 95th luma percentiles ≥ 4.5, `:91-100`).
- **Honest bounds** in its header: "These are FLOORS, not a quality score" (`:10-13`). Regions are fractions of the frame
  so they survive resolution changes (`:13`, `:28-31`).
- **Floors belong to targets**: sets `canvas` (dead, variety, blown), `label` (legibility), `frame` (all), because
  legibility on a canvas is "a category error" that produced a 4.47-vs-4.5 false positive (`:110-117`).
- **Receipt**: per floor its threshold and measured value; per frame `pass`, `verdict` (pass / exempt / fail), declared and
  applied exemptions, and `not_measured` (`:241-246`). A broken floor is a failed floor, not a traceback (`:219-221`).
  Census mode counts frames, failures per floor, unreadable frames, exemptions on their own line, unused declarations, and
  three `blind` sentences (`:266-310`).
- **CLI**: `py -m arsenal floors <frame> | --dir D [--set canvas|label|frame] [--region x,y,w,h] [--no-exempt]`
  (`arsenal/__main__.py:71-85`, `:329-415`); exemptions on by default "because a lane that cannot honour a declared absence
  tends to grow an UNDECLARED one instead" (`:343-345`).
- **Tests**: `tests/test_floors.py` (dark-but-alive passes, `:24-30`; region scoping, `:33-40`; census names its blind
  spots, `:97-113`), `tests/test_floors_exemptions.py` (11 pins on the exemption contract).
- **Ran tonight**: all 7 frames in `fences/piano-presentation/evidence/` pass with `--set canvas` and with the default set.

### 2.2 `arsenal/boost.py`: the referee (API `arsenal.boost/v0`)

- **Why**: on 2026-09-18 a vision model saw "concentric rings" and an eye saw "near-uniform" in a frame whose whole signal
  sat in the bottom 5% of brightness (`arsenal/boost.py:3-8`).
- **What**: `boost()` stretches luma between the 1st and 99th percentiles to full range, for eyes (`:34-43`); `annuli()`
  measures mean luma in six concentric rings (`:46-61`); `radial_summary()` calls it `banded` when brightness rises away
  from the centre before falling, and always gives the reason in a sentence (`:64-77`).
- **CLI** writes the stretched PNG to `state/arsenal/receipts/boost` (`arsenal/__main__.py:231-249`).
- **Tests**: `tests/boost.test.mjs` drives the Python module from node (12 checks), with `E:/AI-Setup` hard-coded as the
  path (`tests/boost.test.mjs:24`, `:61`).

### 2.3 `arsenal/storyboard.py`: dynamic capture (API `arsenal.storyboard/v0`)

- **Why**: "a slow procedural preset reads as a black frame" in a single screenshot (`arsenal/storyboard.py:3-10`).
- **What**: per sampled frame a small luma image plus an 8-bin colour histogram (`:43-61`); a change score that is half
  pixel motion and half histogram shift (`:64-72`); hysteresis segmentation into settled runs and transitions, so a slow
  fade is one long transition (`:94-126`); picks (middle of a settled run, peak of a transition, `:139-153`); duplicate
  removal by difference hash *and* palette, because "solid red and solid blue are hash-identical" (`:181-214`); a contact
  sheet and a manifest that declares its own sampling (`:251-323`). Defaults: 5 samples per second, 480 px wide, low 0.020,
  high 0.080, 3 settle frames (`:33-39`).
- **Tests**: `tests/test_storyboard.py` (a synthetic hard cut found at t = 1.0 s, `:34-42`; hysteresis keeps a fade as one,
  `:56-62`; the flat-frame dedupe trap, `:65-80`).

### 2.4 `arsenal/motion.py`: the temporal twin of the floors (API `arsenal.motion/v0`)

- Reads a stored storyboard manifest (never decodes video) and reports transitions per minute, transition fraction,
  medians and p90 (90th percentile) durations, longest calm (`arsenal/motion.py:59-111`).
- The banding thresholds are **declared** ("a judgement that is not written down is a taste pretending to be a number",
  `:31-33`). It reports `unknown`, never a fake zero, when there is nothing to measure (`:85-87`), and states its sampling
  stride as the resolution floor (`:88-90`). It refuses to fake settle depth inside a transition (`:12-16`).
- **Tests**: `tests/test_motion.py` (6 pins, every number hand-computed from the segment table).

### 2.5 `scripts/vfx_probe_metrics.py` and `scripts/vfx_probe_chroma.py`: the cockpit probes

- Both are self-tests of DeepSeek's "Proposal A: structured render output"
  (`research/in-flight/vfx-studio-agent-side-deepseek-report-2026-08-02.md:39`). The first decodes PNGs by hand, only
  filter type 0, so it returns nothing on canvas-exported PNGs (`scripts/vfx_probe_metrics.py:66-69`; the chroma probe's
  header records this, `scripts/vfx_probe_chroma.py:21-23`).
- The chroma probe adds hue, saturation, opponent chroma and per-pair luma and chroma deltas (`:50-196`). Its inputs are
  hard-coded to specific snaps (`:234-238`), so it is a one-off experiment, not a tool.
- **Ran tonight**: on this host it **crashes before printing a number** (`UnicodeEncodeError` on the arrow character in the
  Windows cp1252 console). With `PYTHONIOENCODING=utf-8` it runs: Michelson contrast is identical (0.8584) on all three
  palette variants, which matches the skill's "identical to sixteen digits" story, **but the per-pixel luma delta is not
  blind**: 6.2% to 11.8% of pixels change by more than 10 levels, against 13.1% to 15.3% for chroma. The probe's own verdict
  is "Chroma delta is 1.5x luminance. Mild validation." **(ran)** The transferable lesson is narrower than the skill states
  (`.claude/skills/shader-craft/references/house-glsl-cookbook.md:47-50`): *scalar summaries* of brightness are blind to a
  palette change; *per-pixel paired differences* are not.

### 2.6 `scripts/ui_shot.py`: eyes for the console

- Headless Chromium through Patchright or Playwright, at the contract's two viewports (1280x860 and 900x820), dark scheme,
  device scale 1, `--force-color-profile=srgb` (`scripts/ui_shot.py:35`, `:92`, `:100-101`); optional 2.5-second rAF
  (requestAnimationFrame) timing probe with mean, p50, p95, worst, frames over 16.7 and 33 ms, and running CSS animations
  (`:48-67`); console errors captured (`:124-132`); a JSON report beside the PNGs (`:139-142`).
- It treats "networkidle never settles on a console with live pollers" as normal, not a failure (`:105-108`).
- It does **not** take the GPU lock (no lock call anywhere in the file).
- Pinned only indirectly: the shader skill's currency test checks that `--label`, `--fps`, `--viewport` still exist
  (`tests/test_shader_craft_skill_cites_live_surfaces.py:61`).

### 2.7 `arsenal/lanes/gpu_lock.mjs` and `arsenal/GPU-LOCK.md`: one render at a time

- **Rules**: headless only with the three anti-throttling flags; bursts under three minutes; jam lanes first; never touch
  port 8793 (`arsenal/GPU-LOCK.md:20-29`).
- **Why it carries an owner**: on 2026-09-15 a scratch harness, `ab_shot.mjs`, died holding a bare directory lock and every
  waiter spun for about 11 minutes (`arsenal/GPU-LOCK.md:31-38`). `ab_shot.mjs` itself was never tracked (it appears only in
  these two comments).
- **Protocol** `arsenal.gpu-lock/v1`: an atomic `mkdir`, an `owner.json` written by rename, a heartbeat file touched every
  15 s by a worker thread so a busy main thread still beats, stale after 60 s of silence, a dead pid, or a hold cap (10 min
  default, 60 max), reaps by rename with an identity check, a reap log, inheritance for child processes
  (`arsenal/GPU-LOCK.md:40-135`, `arsenal/lanes/gpu_lock.mjs:23-297`).
- **Evidence it works**: `state/arsenal/gpu-render.lock.reaps.jsonl` holds 9 reaps (2026-09-17 to 2026-10-10): 7 dead
  owners, 2 past their cap, including two lookdev subagents on 2026-10-10 **(ran: read the log)**.
- **Tests**: `tests/gpu_lock.test.mjs`, 18 named cases from stamp to jam yield (`tests/gpu_lock.test.mjs:5-20`).
- **Who takes it**: the table lists five lanes (`arsenal/GPU-LOCK.md:139-145`) but not `alias_verify.mjs`
  (`arsenal/lanes/alias_verify.mjs:218`) or tonight's `arsenal/shaders/headless.mjs` (`:324-329`), both of which take it.

### 2.8 The Chrome lanes on the real GPU

| Lane | Verifies | Lock | Default window | Default app port |
|---|---|---|---|---|
| `arsenal/lanes/chrome_verify.mjs` | First Light end to end: WebGL2 on hardware (not software), shader compiled, hardware video decoder, zero dropped frames, epochs, takes (`:253-264`) | yes (`:55`) | **visible** (`:28-29`) | 8793 (`:24`) |
| `arsenal/lanes/play_verify.mjs` | every preset compiles as visualizer and over a clip, fake audio input moves the meters, dropped frames ≤ 0.5% (`:217-227`) | yes (`:55`) | **visible** (`:30-31`) | 8793 (`:26`) |
| `arsenal/lanes/alias_verify.mjs` | resolution truth (backing store ÷ CSS size × device pixel ratio), MSAA granted vs requested, frame-time distribution, a still (`:1-22`) | yes (`:218`) | headless (`:54`) | 8793 (`:48`) |
| `arsenal/lanes/jam_verify.mjs`, `jam_timing.mjs` | the jam space; own server on a private port, isolated state dir, refuses 8793, atmosphere off by default so it measures the classic look | yes, no yield (`jam_verify.mjs:1386`) | headless (`:171-173`) | refuses 8793 (`:67-70`) |

Each lane writes `api: "arsenal.receipt/v0"` with a `not_measured` list and a `verdict` of named boolean checks
(`chrome_verify.mjs:38-47`, `:253-265`; `play_verify.mjs:41-51`, `:213-229`).

### 2.9 The shader harness written tonight: `arsenal/shaders/headless.mjs` and `arsenal/shaders/render.py` (untracked)

- Renders shader pages **on the CPU** (SwiftShader) in a private headless Chrome, because a corpus of strangers' ray
  marchers "is exactly the workload that trips" the AMD driver (`arsenal/shaders/headless.mjs:8-14`).
- Refuses to render unless both the browser's GPU report and a WebGL2 context name SwiftShader and no hardware, and judges
  the renderer again on every page before keeping a frame (`:60-71`, `:165-186`, `:269-275`); the Python twin
  `judge_renderer` (`arsenal/shaders/render.py:85-102`) says it is checked against the JavaScript one by
  `tests/test_shader_harness.py` (`render.py:22-24`, `headless.mjs:60-61`), **which does not exist yet** (`ls tests/`, ran).
- Fresh profile per launch, `--remote-debugging-port=0`, so it can only talk to the Chrome it started; kills only its own
  process tree (`headless.mjs:16-28`). Works in bursts of 170 s under the lock and defers the rest (`:21-23`, `:366-375`).
- Reproducible stills of feedback shaders: the page "advances the runtime from a reset to each t" (`render.py:17-18`), the
  cookbook's "true still" protocol (`.claude/skills/shader-craft/references/house-glsl-cookbook.md:52-58`) built into the
  harness.
- A validated receipt (`arsenal.shader-render/v1`): `ok` is only allowed with a software renderer, every frame written,
  and status `done` (`render.py:406-441`); each frame carries mean luma and a `flat` flag (fewer than 3 grey levels,
  `render.py:82`, `:360-371`); the licence line names author and licence on every receipt (`render.py:26-27`, `:467-488`).

### 2.10 Scratch instruments that carried the real judging

These live in `research/in-flight/` or `state/` and were each built for one round:

- **The anti-aliasing bench** (`research/in-flight/piano-spectacle-2026-09-13/adaptive-resolution-data/scripts/aa_bench.mjs:1-114`):
  seeded frozen frame, 16-sample reference, MAE, edge MAE, PSNR, shimmer, GPU-synchronised cost, 14 configurations, 4
  window cases. Its own CDP launcher `cdp.mjs` repeats the lane flags.
- **The Synthesia measurement look** (`research/in-flight/piano-synthesia-mode-2026-09-15/final/measure-summary.md:7-24`,
  `:135-159`): a scratch look injected into the page to measure rise speed, bead separation, wash-out at strike,
  brightness-velocity correlation, halo area, p95 frame time, draw calls.
- **The light-round verification lane**: "Send `render please light-<seat>-<name>` on the bus" and receive stills, strips
  and measurements within an hour (`research/in-flight/piano-light-instruments-2026-09-17/brief.md:176-178`). A render
  service by convention, not by code.

### 2.11 `scripts/piano_card_art.py`

A sixth renderer: Brave plus Playwright on SwiftShader, rendering instrument card art from `127.0.0.1:8793`, 3x
supersampled wireframes, no GPU lock (`scripts/piano_card_art.py:1-30`, `:60-67`).

---

## 3. How renders are verified here

### 3.1 The receipt grammar (the house's strongest shared habit)

Every visual instrument writes a JSON object with: an `api` version string; the parameters it used (declared, not hidden);
the measured numbers next to their thresholds; and confession fields. The confession field has three spellings:
`not_measured` (`arsenal/floors.py:245`, `arsenal/storyboard.py:289-293`, `arsenal/lanes/chrome_verify.mjs:42`), `blind`
(`arsenal/motion.py:73-90`, `arsenal/floors.py:305-309`), and `note` (`arsenal/shaders/render.py:487`). The media arc already
unified this as `result(verb, src, params, payload, blind)` with a content id for the source file and a `computed_with`
block (`arsenal/media/receipt.py:1-5`, `:60-80`).

### 3.2 Reference images ("golden" pixels)

There is **no tracked golden-image test** for any visual surface. What exists instead:

- a golden **hash of draw calls** (not pixels) for the lean painter (`tests/piano_lean.test.mjs:634-655`);
- a 16-sample **rendered reference** per run in the anti-aliasing study (`adaptive-resolution-aa.md:143-148`);
- **PSNR (peak signal-to-noise ratio) against the source** for video cuts, with a 30 dB floor (`arsenal/media/cut.py:73`,
  `:748-757`), the only shipped pixel-comparison gate in `arsenal/`;
- **deliberate absence** of pixel-exact replay for the piano atmosphere: "Default-atmosphere pixel-exact replay from a held
  frame clock is not established" (`arsenal/SPECTACLE.md:198-202`). The fence accepted a `captureSimState` /
  `restoreSimState` seam to fix this (`fences/piano-presentation/reconciliation.md:57`, `:185-186`); a grep of `arsenal/`
  finds no such names (ran). The classic look has a seeded spark scatter for takes and controls (`arsenal/web/piano.js:953`,
  `:5254-5257`).

### 3.3 Colour and brightness metrics

| Metric | Formula in use | Where |
|---|---|---|
| floors luma | Rec. 709 weights (0.2126 / 0.7152 / 0.0722) on gamma-encoded sRGB, deliberately not linearised | `arsenal/floors.py:53-57` |
| storyboard luma, dHash | Rec. 601 weights (0.299 / 0.587 / 0.114) | `arsenal/storyboard.py:55`, `:169` |
| probe luma | Rec. 601 | `scripts/vfx_probe_chroma.py:45-46`, `scripts/vfx_probe_metrics.py:82-84` |
| shader harness frame facts | Pillow's `convert("L")` (Rec. 601 by Pillow's definition, **(inferred)**) | `arsenal/shaders/render.py:365-369` |
| AA bench edge mask | Rec. 709 | `aa_bench.mjs:69` |
| chroma (probe) | opponent chroma √((R−G)²+(G−B)²+(B−R)²)/√2 and HSV saturation | `scripts/vfx_probe_chroma.py:59-77` |
| chroma (fence acceptance) | OKLCH chroma of pressed keys (≥ .12 soft, ≥ .18 hard) | `fences/piano-presentation/half_vandor.md:111` |
| contrast | WCAG-shaped ratio on gamma luma (floors); Michelson (probes) | `arsenal/floors.py:91-100`; `scripts/vfx_probe_chroma.py:96-109` |

The tool review measured the consequence of the floors choice: white text on grey 90 reads 2.61 where true WCAG gives about
6.9 (`research/in-flight/rill-3d-tools-review-2026-09-14/assessment.md:51-52`).

### 3.4 Headless Chrome flags

| Flag set | Purpose | Where |
|---|---|---|
| `--disable-backgrounding-occluded-windows --disable-renderer-backgrounding --disable-background-timer-throttling` | "A covered or background window throttles rAF and timers, which would make every fps and drop number meaningless" | `arsenal/lanes/chrome_verify.mjs:65-66`, `play_verify.mjs:65-66`, `jam_verify.mjs:92-93`, `headless.mjs:54-56`, `aa cdp.mjs` |
| `--headless=new` | no window, no stolen focus | lanes; default **off** in chrome_verify and play_verify |
| `--mute-audio --autoplay-policy=no-user-gesture-required` | media plays without a person | chrome_verify, play_verify, jam lanes |
| `--use-fake-device-for-media-stream --use-fake-ui-for-media-stream` | fake microphone for visualizer sweeps | `play_verify.mjs:67` |
| `--use-angle=swiftshader --enable-unsafe-swiftshader` (+ `--disable-d3d11`, no hardware video, software compositing) | never touch the AMD GPU | `arsenal/shaders/headless.mjs:47-58`; `scripts/piano_card_art.py:67` (without the fence flags) |
| `--force-device-scale-factor=N` | device pixel ratio cases | `aa cdp.mjs`, alias_verify |
| `--force-color-profile=srgb` | colour-stable screenshots | `scripts/ui_shot.py:92` only |
| throwaway `--user-data-dir`, `--no-first-run`, `--no-default-browser-check` | never touch Daniel's profile | every lane |

Two lanes judge the renderer in **opposite** directions, both correctly: First Light must prove it runs on the GPU
(`webgl2_on_the_gpu: !swiftshader`, `chrome_verify.mjs:254`); the shader harness must prove it does not
(`headless.mjs:63-71`). A shared launcher needs the renderer policy as a parameter.

### 3.5 Time and frame rate

The house separates three things that are easy to confuse (synthesis **(inferred)** from the cited lines): **rAF
delivery** ("not GPU timing or physical scanout", `arsenal/VISUAL-QUALITY-BASELINE.md:74`); **GPU-synchronised frame
cost** (a 1-pixel `readPixels` after each frame, `adaptive-resolution-aa.md:169-174`); and **encoded video cadence**
("Render-loop fps alone is not evidence of encoded video cadence", `arsenal/SPECTACLE.md:157`). The design contract's
"a headless seat CANNOT measure real FPS" (`design/CONTRACT.md:121-125`) refers to the harness's hidden browser pane;
`--headless=new` Chrome does composite and ran rAF at 240 Hz in the AA study (`adaptive-resolution-aa.md:173-174`). The
canonical screening method is "warm up, then use the existing ten-second measurement", extended through the slowest
motion cycle for a sustained claim (`arsenal/VISUAL-QUALITY-BASELINE.md:74`).

### 3.6 The GPU risk ladder (synthesis, **(inferred)** from the cited rules)

| Tier | Where the GL runs | Rule |
|---|---|---|
| Cockpit (Bifrost console) | the tab already open; the bench renders through it via a job queue | "Never a second GPU context to look at your own work" (`.claude/skills/shader-craft/SKILL.md:56-64`); the harness browser preview killed Claude Desktop on 2026-08-12 (cookbook `:23-26`); `scripts/vfx_render.py:9-19` rejected headless CDP for this reason |
| Arsenal pages (piano, First Light, Play) | headless Chrome on the real GPU | under the lock, bursts under 3 min (`arsenal/GPU-LOCK.md:20-29`) |
| Strangers' shaders (corpus) | headless Chrome on SwiftShader (CPU) | refuse if hardware is named (`arsenal/shaders/headless.mjs:8-14`) |

The cockpit and Arsenal arcs gave **different answers** to "where does the GL run" (`scripts/vfx_render.py:13-15` vs the
lanes). Both answers are defensible; a shared renderer service has to carry both.

---

## 4. The visual tests, by the briefed globs

| Glob | Files | What they pin |
|---|---|---|
| `tests/*floors*` | `test_floors.py`, `test_floors_exemptions.py` | the four floors, regions, census, exemption contract (section 2.1) |
| `tests/*vfx*` | `test_vfx_ingest.py` (13), `test_vfx_feed_and_lease.py` (19), `test_arsenal_fl_vfx.py` | ingest wraps and refuses honestly; one renderer tab holds a lease, every job posts its picture and reason (`test_vfx_feed_and_lease.py:1-20`). **False friend**: `test_arsenal_fl_vfx.py` is FL Studio's "VFX Script" MIDI band, not visuals (`tests/test_arsenal_fl_vfx.py:1-6`) |
| `tests/*looks*` | `piano_looks_registry.test.mjs`, `piano_looks_store.test.mjs`, `test_arsenal_looks_route.py` | look descriptors, apply order, recording refusals, revision conflicts, offline queue, route security |
| `tests/*spectacle*` | `piano_spectacle.test.mjs` | velocity, dry/wet staccato, pedal release, cadence, re-strikes keep their history, bounded voices, spring stable across frame rates (`tests/piano_spectacle.test.mjs:3-57`) |
| `tests/*glass*` | **none** | no test file name matches (ran: `ls tests`) |
| shader-craft currency | `test_shader_craft_skill_cites_live_surfaces.py` | paths exist, quoted lines in source and HEAD, module seam, sketch dialect, verbs and flags (`:72-168`) |
| one hop out | `boost.test.mjs`, `gpu_lock.test.mjs`, `test_motion.py`, `test_storyboard.py`, `gyre_motion.test.mjs`, `gyre_presets.test.mjs`, `piano_lean.test.mjs`, `test_hero_avatar_mount_is_race_free.py`, `test_arsenal_shader_first_light.py`, `test_shader_corpus.py` | see sections 1.3 and 2 |

**The node suites are outside the ship gate.** The gate runs pytest only (`scripts/ship_gate.py:193`). Six Python tests
wrap specific node suites (cadence, edit timeline, jam tempo map, Nashville, score export twice; ran: grep of
`tests/*.py`), and none of them wraps `boost.test.mjs`, `gpu_lock.test.mjs`, `piano_looks_*.test.mjs`,
`piano_spectacle.test.mjs` or the `gyre_*` suites. The baseline lists them as commands to run by hand
(`arsenal/VISUAL-QUALITY-BASELINE.md:80-87`). A look, the referee or the GPU lock can therefore break without the ship
door noticing **(inferred from the two greps)**.

---

## 5. The house method, applied to visual work

### 5.1 `docs/method-baseline-2026-07.md`

| Practice | Visual receipt | Gap |
|---|---|---|
| P0 proportionality (`:21-30`) | "Scale verification to the changed behavior" (`arsenal/VISUAL-QUALITY-BASELINE.md:69`) | none |
| M0 taxonomy first (`:54-67`) | the fence's finding "the missing foundation is time with a point of contact", which reclassified the problem from "prettier modes" to "a temporal axis" (`fences/piano-presentation/reconciliation.md:24-47`) | none |
| M1 fenced dual pass, method-diverse (`:69-80`) | blind halves by lane, rendered lookdev vs information design vs budget (`fences/piano-presentation/brief.md:69-89`) | M1-BRIEF's five sections are only partly followed: the fence brief orders CHARTER, THE QUESTION, INPUTS, LANES, RULES, OUTPUT (`brief.md:3-99`) |
| M2 SOTA grounding (`:164-180`) | GPU Gems, animation principles, music-colour research translated into choices (`arsenal/SPECTACLE-DESIGN.md:31-57`) | none |
| M3 pre-registered acceptance (`:182-193`) | floors RED before GREEN; the light round published its fixtures and judging lenses before entries (`brief.md:180-197`) | fence floors written as prose, never as failing tests |
| M4 crash drills (`:195-209`) | GPU lock "live" case hard-kills a holder (`tests/gpu_lock.test.mjs:9-10`) | none for renders |
| M5 live exercise (`:211-220`) | Gyre receipt drove real controls in a visible browser (`logs/gyre-20260921/results.md:17-23`) | none |
| M6 verbatim records (`:222-235`) | Daniel's answers quoted in the reconciliation (`reconciliation.md:14-22`) | none |
| M7 evidence-first forensics (`:237-248`) | the hero avatar race (`tests/test_hero_avatar_mount_is_race_free.py:3-20`) | none |
| M8 honest bounds (`:250-260`) | every instrument's `blind` / `not_measured`; "4K rendering is available; smooth 4K60 browser recording has not been achieved" (`arsenal/SPECTACLE.md:155-156`) | none |
| M10 guards for every law (`:273-282`) | the skill currency pin, the exemptions tripwire | GPU-LOCK "headless only" and "never 8793" have no guard; two lanes violate them by default |

### 5.2 `docs/CONDUCT.md`

- **L1 intent before task, L2 his words verbatim** (`:23-26`): every visual brief tonight and in September opens this way.
- **L3 one "that's right" before any build** (`:26-27`): the fence put frames before Daniel and built only after his picks
  (`reconciliation.md:14-22`).
- **L4 red is a gem; all-green dashboards get audited** (`:28-29`): the floors census on the fence evidence is exactly an
  all-green dashboard that deserves an audit (section 0).
- **L11 the adversary takes an artifact** (`:42-44`, `:87-107`): the visual judges work on rendered fixtures, which is the
  rule's healthy form; "same refuters pointed at finished fixes caught two" (`:102-104`).
- **"A preset changes poetry, not truth"** (Sunshine, accepted in `reconciliation.md:77`): a look may change how the music
  is drawn, never which notes are shown as sounding.

---

## 6. Binding rules and taste rulings found

1. **Taste is Daniel's, at milestones; the floor is checked blind and never claims the ceiling.**
   `.claude/skills/shader-craft/SKILL.md:8-11`, `design/CONTRACT.md:117-119`.
2. **Numbers sit beside the picture, never as the gate.** cookbook `:47-50`; `arsenal/VISUAL-QUALITY-BASELINE.md:19`.
3. **Report no FPS you did not observe; FPS from a visible window or a trace.** `design/CONTRACT.md:121-125`,
   `.claude/skills/shader-craft/SKILL.md:133-135`.
4. **Never silently lower resolution to earn an FPS claim; record CSS viewport, DPR and actual drawing buffer; an exact 4K
   claim needs an observed 3840x2160 buffer.** `arsenal/VISUAL-QUALITY-BASELINE.md:16`, `:72`.
5. **Target native pixels and 60 fps minimum; p95 at or below about 16.7 ms.** `arsenal/VISUAL-QUALITY-BASELINE.md:16`, `:73`.
6. **One headless render at a time on the GPU, under the lock, bursts under 3 minutes; jam lanes first; never touch port
   8793; never `chrome.exe --version`.** `arsenal/GPU-LOCK.md:3-29`.
7. **Never open a second GPU context to look at your own work (cockpit); never preview a shader page in the harness
   browser.** `.claude/skills/shader-craft/SKILL.md:61-64`, `:147`.
8. **Corpus shaders render only on SwiftShader; renders of other people's work stay under `state/` and name author and
   licence.** `arsenal/shaders/headless.mjs:8-14`, `arsenal/shaders/render.py:26-27`; the night's licence line (task brief).
9. **Techniques transfer; code, copy, brand and assets do not; a licence gate stands before public use of the geodesic
   core.** cookbook `:60-69`.
10. **Colour roles, not hues; alarm colours only on alarms.** `design/CONTRACT.md:62-66`.
11. **One light, one word: the note's own colour is the only saturated light; louder buys width, height and bloom in that
    hue, never white.** `fences/piano-presentation/half_vandor.md:20-22`, accepted `reconciliation.md:86-90`;
    light-round house rule "Colour stays the note's colour, saturated. Nothing clips to white"
    (`research/in-flight/piano-light-instruments-2026-09-17/brief.md:155-157`).
12. **A strike adds momentum; it never rewinds a motion already in flight.** `arsenal/SPECTACLE-DESIGN.md:3-6`.
13. **Velocity legible, sustain truthful, pedal alone animates nothing, dispose returns to baseline, nothing downloaded at
    runtime, both framings composed.** `research/in-flight/piano-light-instruments-2026-09-17/brief.md:150-169`.
14. **An exemption hides a red, never a measurement; it needs reason, owner and date; the table ships empty.**
    `arsenal/floors.py:120-137`.
15. **A rate over no time is unknown, not zero.** `arsenal/motion.py:85-87`.
16. **A reproducible still of a feedback effect is clear history plus a fixed settle, never a seek.**
    `.claude/skills/shader-craft/SKILL.md:87-90`, cookbook `:52-58`.
17. **Analogous palette, never a rainbow; colour eases through HSV the short way round.**
    `.claude/skills/shader-craft/SKILL.md:101-104`.
18. **Do not apply an idle animation floor indiscriminately; musical performance may call for genuine rest.**
    `arsenal/VISUAL-QUALITY-BASELINE.md:65`; "Silence: motion settles... no automatic visual climax"
    (`arsenal/SPECTACLE-DESIGN.md:70`).
19. **Load and update are different actions; validate the whole preset before applying; old records are never silently
    rewritten.** `arsenal/VISUAL-QUALITY-BASELINE.md:37`.
20. **Daniel's media ruling for this suite: no forbidden-tool rules, best and most stable wins.** (house memory index,
    media suite project 2026-09-13; cited from the session context, not from a repo file).

---

## 7. Duplication: the same concept, built several times

1. **The DevTools (CDP) client `connect(wsUrl)`** is copied in `arsenal/lanes/chrome_verify.mjs:88`, `play_verify.mjs:89`,
   `jam_verify.mjs:148`, `jam_timing.mjs:139`, `alias_verify.mjs:105`, `tests/score_lab.test.mjs:112`,
   `arsenal/shaders/headless.mjs:84` (whose comment names chrome_verify as "the house CDP client"), and
   `research/in-flight/piano-spectacle-2026-09-13/adaptive-resolution-data/scripts/cdp.mjs`. `waitFor` likewise.
2. **Chrome launch flag lists** are hand-written in each of those files plus `scripts/ui_shot.py:92` and
   `scripts/piano_card_art.py:67`, and have drifted (section 3.4 and 8).
3. **Brightness (luma) formulas**: five definitions across floors, storyboard, both probes, the shader harness and the AA
   bench (section 3.3).
4. **"Is this frame flat or dead"**: `floors.floor_variety`/`floor_not_dead` (`arsenal/floors.py:61-88`),
   `render.frame_facts` `flat` (`arsenal/shaders/render.py:82`, `:360-371`), the probes' "Proposal F" uniform-render warning
   (`scripts/vfx_probe_chroma.py:306-309`), and the 2026-08-02 proposal itself.
5. **Contact sheets**: `arsenal/storyboard.py:235-248` (fixed 320x180 cells, no labels), `arsenal/shaders/render.py:688`,
   the bench's `renderSheet` (per `scripts/vfx_render.py:14-15`), lookdev choice sheets in scratch
   (`straight-lines-proposal.md:3`), the AA study's `crops.py`.
6. **Image input/output stacks**: PyAV for floors and storyboard (`arsenal/floors.py:34-39`, `arsenal/storyboard.py:218-232`),
   Pillow for the probes and the harness (`scripts/vfx_probe_chroma.py:24-29`, `arsenal/shaders/render.py:365`), a
   hand-rolled PNG decoder in the old probe (`scripts/vfx_probe_metrics.py:32-79`).
7. **Receipt shapes**: `arsenal.receipt/v0` (lanes), per-instrument APIs with `not_measured`/`blind`, the media `result()`
   shape, `arsenal.shader-render/v1` with its own validator, and `ui_shot`'s unversioned report (`scripts/ui_shot.py:89`).
8. **Frame-time probes**: `ui_shot`'s 2.5 s rAF probe (`scripts/ui_shot.py:48-67`), `alias_verify`'s 180-frame distribution
   (`alias_verify.mjs:21`, `:51`), the Gyre 10 s method (`logs/gyre-20260921/results.md:7`), the AA bench's GPU-synchronised
   cost (`adaptive-resolution-aa.md:169-174`), the Synthesia "Ultra p95" with a hidden-entry control.
9. **Fixtures**: each round authored its own render fixtures (fence quiet/hard/dense; the six light fixtures; the AA phrase,
   `aa_bench.mjs:24-45`; Play's fake audio input). No tracked shared render-fixture file exists (grep for the fence fixture
   names over `arsenal/`, `tests/`, `scripts/` finds only theory test cases, ran).
10. **Viewports and framings**: the contract's two console viewports (`design/CONTRACT.md` via `scripts/ui_shot.py:21-23`),
    the piano's 9:16 and 16:9, alias_verify's DPR list `1,1.5,2` (`alias_verify.mjs:49`), the AA study's four window cases
    (`adaptive-resolution-aa.md:185-192`), the quality tiers Studio/Ultra/Cinema (`arsenal/SPECTACLE.md:131-135`).
11. **Saved looks / presets**: piano looks registry and store with a server route, Gyre presets in browser storage with
    separate libraries per port (`arsenal/VISUAL-QUALITY-BASELINE.md:52`), reference recipes JSON, `design/vfx-presets.json`,
    First Light's preset bank (covered in depth by `arc-piano-core.md` and `arc-first-light-present.md`).
12. **Renderer judgement**: `judgeRenderer` (JS) and `judge_renderer` (Python) twins (`headless.mjs:62-71`,
    `render.py:85-102`), plus the inverse check in `chrome_verify.mjs:254`.
13. **Region presets**: `CANVAS_REGION` and `KEYBOARD_REGION` for two page layouts only (`arsenal/floors.py:28-31`); the
    fence's 9:16 bands (`reconciliation.md:105-111`) and the review's proposed spectacle region (`assessment.md:57-58`) are
    prose.

---

## 8. Drift and defects found (each with its evidence)

1. **Most defects from the 2026-09-14 tool review are still in the code.** `arsenal/storyboard.py` has one commit, from the
   same night as the review (`git log`, ran); `arsenal/floors.py`'s later commits added census mode and exemptions only.
   Still present by reading:
   - storyboard thresholds are fixed numbers (`arsenal/storyboard.py:35-36`), so Asta's spectacle still reads as "one settled
     moment" (review defect 1, `assessment.md:33-34`);
   - a pick shows the frame *before* the change: scores are indexed by the step into the next sample (`storyboard.py:76`),
     picks take that index (`:147-150`) and look up the sample with the same index (`:275-276`), while its time comes from the
     later sample (`:278-279`) (review defect 6, `assessment.md:48-49`);
   - a file with no video stream raises instead of failing, because `load_rgb` runs outside the per-floor `try`
     (`arsenal/floors.py:208`; review defect 3);
   - legibility is computed on gamma luma (`floors.py:53-57`) and the CLI default runs every floor including legibility on
     the whole frame (`floors.py:209`; review defect 7);
   - `not_blown` counts only pixels where all three channels clip (`floors.py:77`), so a saturated coloured blow-out reads
     0.0 (review item 10);
   - no frame-rate or capture-gap check exists anywhere (`check_take` and `capture_gap` appear only in research and fence
     docs, grep ran; review defect 4).
2. **The fence's acceptance floors were never built.** Title ÷ soft-gesture brightness, lit fraction per band, hard ÷ soft
   area, pressed-key chroma, repeat continuity, flicker (`fences/piano-presentation/half_vandor.md:100-118`,
   `reconciliation.md:166-199`) exist only as prose; `arsenal/floors.py` still has four floors (`:103-108`). Slice 6
   (`check_take` and band floors, `reconciliation.md:210`) has no code. **Ran:** all seven fence evidence frames pass every
   existing floor.
3. **Two lanes open a visible Chrome by default** although the house rule is "Headless Chrome only"
   (`arsenal/GPU-LOCK.md:22` vs `arsenal/lanes/chrome_verify.mjs:29`, `play_verify.mjs:31`). Their own comment explains why
   headless matters ("so a run can't steal focus", `chrome_verify.mjs:28`).
4. **Three lanes and the card-art renderer default to port 8793**, Daniel's server, which the lock doc says never to touch
   (`arsenal/GPU-LOCK.md:29` vs `chrome_verify.mjs:24`, `play_verify.mjs:26`, `alias_verify.mjs:48`,
   `scripts/piano_card_art.py:66`). Only the jam lanes enforce the rule (`jam_verify.mjs:67-70`). Whether reading (not
   restarting) Daniel's server is acceptable is a call the doc does not make **(inferred)**.
5. **`scripts/ui_shot.py` drives Chromium on the GPU without the lock** (no lock call in the file), and
   `scripts/piano_card_art.py` drives Brave on SwiftShader without it. The shader harness takes the lock even on SwiftShader
   (`headless.mjs:324-329`). The rule says "every lane that drives Chrome against the GPU" (`arsenal/GPU-LOCK.md:3-5`),
   which leaves CPU renders ambiguous.
6. **"The three flags" means two different trios**: the anti-throttling flags in `arsenal/GPU-LOCK.md:22` and the
   SwiftShader flags in `arsenal/shaders/headless.mjs:47-49` ("The three flags the contract requires").
7. **The chroma probe crashes on this host's console** before printing a number (ran), and it is the probe the shader
   skill names as the "numbers next to the image" step (`.claude/skills/shader-craft/SKILL.md:130-131`). Its headline
   claim needs narrowing (section 2.5).
8. **A cited test does not exist yet**: `tests/test_shader_harness.py` is named as the twin-drift guard in
   `arsenal/shaders/render.py:22-24` and `arsenal/shaders/headless.mjs:60-61`; both files are untracked work from tonight
   (`git ls-files`, ran). This is a work-in-progress state, not necessarily a defect.
9. **The GPU-LOCK "who takes it" table is incomplete** (missing alias_verify and the shader harness, section 2.7).
10. **The node visual suites do not gate shipping** (section 4).
11. **`tests/boost.test.mjs` hard-codes `E:/AI-Setup`** (`:24`, `:61`), so it fails on any other checkout path.
12. **The determinism seam accepted on 2026-09-15 is not built** (section 3.2), so pixel receipts with the atmosphere on are
    still impossible, and the jam lane still measures with atmosphere off (`jam_verify.mjs:62-64`).

---

## 9. Seams: clean places to cut shared modules

Ordered by how much duplication each removes per line written **(inferred ranking)**.

1. **One receipt shape: adopt `arsenal/media/receipt.py`.** It already has the source content id, declared params,
   `computed_with`, payload, `blind`, and write-or-say-why (`arsenal/media/receipt.py:24-80`). floors, boost, storyboard,
   motion, the lanes' `arsenal.receipt/v0`, the shader harness and ui_shot can each map onto `result(verb, src, params,
   payload, blind)` with a one-line shim; `not_measured`, `blind` and `note` become one field.
2. **One browser launcher and CDP client: `arsenal/lanes/cdp.mjs`.** Lift the `Browser` class from
   `arsenal/shaders/headless.mjs:117-221` (fresh profile, port 0 with DevToolsActivePort, own-process-tree kill, console and
   exception capture, renderer report) and the `connect` with fail-fast close (`:84-114`). Flag profiles as named data:
   `GPU_HEADLESS` (anti-throttle + headless + mute), `SOFTWARE` (SwiftShader + GPU fence), `FAKE_MEDIA`, `DPR(n)`; renderer
   policy `require: "hardware" | "software"` (sections 3.4). Every lane and research bench then imports it, and a guard
   test can assert that no lane spawns `chrome.exe` itself (M10).
3. **One colour-science module for metrics: `arsenal/vision/colour.py` (name illustrative).** Linearise sRGB, Rec. 709
   relative luminance, OKLab/OKLCH chroma (the fence's unit), WCAG contrast on linear light, per-pixel paired deltas. floors,
   storyboard, the probes and `render.frame_facts` call it. This settles review defect 7 and the five-formula drift in one
   place.
4. **Floors as data, per look: an acceptance spec file.** The fence's floors are already in a table shape (measure,
   region band, floor, baseline, best measured, `half_vandor.md:100-118`). Make them `arsenal.look-acceptance/v1` JSON next to
   each look, with named regions (the 9:16 bands, `reconciliation.md:105-111`) and relational measures (ratio of two
   regions' p99, lit fraction above a threshold, chroma of pressed keys), executed by an extended `floors`. This is the
   "tweak one module" lever for acceptance: one spec drives the lane, the census and the panel's measurement column.
5. **A tracked visual-fixture library and viewport matrix: `arsenal/fixtures/visual/` (illustrative).** The fence's three
   fixtures, the light round's six, the AA phrase, the fake-audio sweep, plus the framings, DPRs and quality tiers, each
   with an id that receipts cite. The theory arc already does this for chord cases (`tests/fixtures/theory/`).
6. **One contact-sheet / side-by-side primitive.** Labels burned in, source aspect kept, no black cells, before/peak/after
   for transitions (the review's fixes, `assessment.md:54-55`), used by storyboard, the shader filmstrip, lookdev choice
   sheets and the bench.
7. **A judging-panel kit**: an M1-BRIEF template with the five sections in order (`docs/method-baseline-2026-07.md:102-113`),
   the lens list, the control rules (hidden-entry baseline, same-velocity pair, counterfactual toggle), the scoring card,
   and the "Daniel picks" step. The light-round brief (`brief.md:125-197`) is the best existing draft.
8. **A render service, by code instead of convention.** The light round's "render please" lane (`brief.md:176-178`) and the
   bench's job queue (`scripts/vfx_render.py:124-172`) are the same idea at two GPU-risk tiers: submit a job, get a receipt
   and PNG paths back. The shader harness's plan/result protocol (`arsenal.shader-headless-plan/v1`, `headless.mjs:37-38`)
   is the most complete implementation and could serve all three tiers with a renderer policy.
9. **Wrap the node visual suites into pytest** using the existing pattern (`tests/test_score_export.py:20`) so looks, the lock
   and the referee gate shipping.
10. **One frame-time probe** implementing the baseline's definitions (warm-up, 10 s window, p95, worst interval, missed-budget
    percentage, rAF vs GPU-synchronised clearly labelled, `arsenal/VISUAL-QUALITY-BASELINE.md:73-74`), replacing the four
    variants in section 7.

---

## 10. Honest bounds

- I did not render anything, so every statement about how a lane behaves on the GPU is from its code and its stored
  receipts, not from a fresh run.
- I read the scratch harnesses only where they were cited by tracked docs; the lookdev scripts in old session scratchpads
  were not opened (they are outside the repo and outside scope).
- `arsenal/shaders/` was being written while I read it (files stamped 02:09 to 02:47); line numbers there may move.
- Section 9's names (`arsenal/vision/colour.py`, `arsenal/fixtures/visual/`) are proposals, not existing paths.
- The other six readers cover the bench (`arc-vfx-bench.md`), the piano core (`arc-piano-core.md`), the piano studies
  (`arc-piano-studies.md`) and First Light/present (`arc-first-light-present.md`) in depth; I cite them only for boundaries.

## 11. One calibrated question for Daniel

When a look passes every number but you do not like it, should the house record your "no" as a named, dated taste ruling
next to the look's acceptance spec (so the next look is judged against it too), or keep taste rulings out of the specs and
only in the conversation?
