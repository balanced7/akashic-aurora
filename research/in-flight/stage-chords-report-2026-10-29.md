# Stage chord phrasing: the review's fixes (2026-10-29)

Daniel, 2026-10-29: "lets also land the chord phrasing." and "i dont want blacks to be crushed, i just want black to be
black for us to truly have an hdr fidelity light setup that has pure black as something that is just in the scene without
crushing other things".

**Outcome.** All eight findings reproduced. Six are fixed at the root, each with a test that failed before the fix and
passes after it: F1, F2, F4, F6, F7 and F8b. F3 has a partial fix and F5 has new checks. F8a, the open half of F3 and
the KeyLab half of F6 need Daniel's decision or an engine change. Results:
- Node tests: 27 of 27 chord tests (6 new), 232 of 232 stage tests.
- GPU chords phase: 19 of 19 pass. The 7 new checks all fail against the page before the fix.
- GPU regression (load, kick, engine): passes.

The finish (black floor, crush) was not touched. BREATH only lowers the scene's own light, so at the bottom of a fade
the room goes black while anything that emits light still shows.

## Commits (branch stage-chords, not pushed)
- `be9898eca` Recogniser and ensembles: F1, F2, F4, F6, F8b, plus 6 tests.
- `7a03e7782` Page wiring: canFade, the lost key-up (F7), the fade's corner label (F3), README.
- `077831c38` Receipts: the 7 new GPU checks (F5), and the replay now runs the ensembles too.

## Findings

| id | reproduced with | fix | test (fails before, passes after) |
|---|---|---|---|
| F1 chord adds a punch | join_repro.mjs: a refused punch came back on (+5.6 % peak); a re-strike got a fresh punch (+19 %). GPU before the fix: refused 5 got punchFrom 165.83; re-strike went 170.04 -> 171.00 | `Ensembles.attack` now only moves a punch earlier, which makes it weaker, or leaves it alone. A refusal (-Infinity) stays refused, and a re-strike (presses > 1) keeps its old punch | node "F1"; GPU "refused stays refused", "re-strike keeps its tap's punch", "no punch newer than its own press" |
| F2 strum + key splits into two attacks | probe.mjs: 4,5,6 and then 1 at 10 ms landed in two lineages. In the takes: 2 splits in 202217 and 4 in 202610 | A key within W of a strum's first key now joins the strum | node "F2"; GPU "mash 4 5 6 + 1 is one attack" (grammar 1, singles 2). The takes' splits are now 0 and 0 |
| F3 latched fade, nothing on screen | level_time.mjs on take 195842: the light is below half for 73 % of the playing time and ends at 0 | **Partial.** A quiet corner label ("breath N % · Esc back") shows while the light is below the look's, even with the HUD hidden. It is page text over the canvas, not drawn into the picture. Whether the fade should stay put or hold and then release is **Daniel's call** | GPU "label shows with the HUD hidden, goes after Esc" |
| F4 sweep takes over with nothing to fade | probe.mjs: eighths 1 2 3 4 5 at full light; keys 3, 4 and 5 were swallowed | New `Grammar({canFade})` option backed by `Ensembles.canFade`. A run that cannot move the light (up at full, down at black) fires its keys as normal. A step past full or black ends the sweep (`limit`) and that key fires | node "F4" x2; GPU "eighths up the row fire every key" (grammar 2 kicks, was 1). Replay: 0 fade keys moved nothing |
| F5 checks blind to F1 | the old "attacks" count read the field F1 overwrote | New checks read kick.js's records directly. One invariant covers it: no punch is ever newer than its own first press | the 7 new GPU checks |
| F6 frame settle splits a chord | Unit level, phone / KeyLab / C sources (number keys stayed open through the slow-run candidate) | A gesture stays open 50 ms past W (`settleSlackMs`) | node "F6" (failed before) |
| F7 a lost key-up eats later presses | GPU before the fix: 1 down twice gave 1 press | A key-down for a key already held, when it is not the OS's auto-repeat, releases the old press first | GPU "lost key-up is a new press" (2 and 2) |
| F8b re-strike first takes the chord's attack | unit level | A re-strike never becomes the chord's attack; the first fresh kick does | node "F8b" |

## Deferred (decisions or other owners)
- **F3 semantics: Daniel's call.** Should a fade stay put (as built) or follow the design's hold-for-N-beats-then-release?
  Take 195842 still sits below half for 73 % of the playing and ends black. The new label makes this visible but does
  not change it.
- **F4 continuation window: Daniel's call.** Any neighbouring key within 450 ms still counts as a fade step, including a
  deliberate hit. That 450 ms is a constant from the design. A tighter window would be about twice the run's measured
  gap; his gaps are p50 185 ms and p90 222 ms.
- **F6, KeyLab half.** The engine sends no timestamp with its pad events, so KeyLab chords still use the time each pad
  event reaches the page. That needs a change on the engine side (arsenal/keylab), outside this track.
- **F8a: Daniel's call, plus stage-v3.** BREATH also dims manual LASER, HERO, MORPH and DROP hits (through the lasers'
  master). Keeping hits bright under a fade needs a change in lasers.js, which stage-v3 owns.
- **F5, rest.** I did not run a low-velocity chord in the drop. The punch invariant covers the same failure exactly
  and is not confused by the demo's own pads.

## Receipts
- GPU chords, after the fix: `state/arsenal/receipts/stage-20261029-133252/receipt.json`, 19 of 19 in 42 s. In the
  stills, `chords-5-breath-bottom.png` shows a black room with the emitters still lit and the label at the top right.
- GPU chords, before the fix: `stage-20261029-133206` and `stage-20261029-133341`. All 7 review checks FAIL.
- GPU regression: `stage-20261029-133532`, phases load, kick and engine, all pass.
- Replay (counts only, gitignored): `grammar-replay-pc-20261029-133018.json`, `grammar-replay-os-20261029-133019.json`.
  On take 195842 (pc clock): 12 fades (was 13), 46 keys taken over by fades (was 48), 0 fade keys that moved nothing,
  0 strum splits.
  Light below half for 0.731 of the playing time, ends at 0.

## Merge notes for stage-v3
No edits to kick.js, programmer.js, lasers*.js or atmos.js. The ensemble reads two kick.js record fields, `presses` and
`from`, and lowers `punchFrom`. The page's cancelPending still writes `holdEnd`.
