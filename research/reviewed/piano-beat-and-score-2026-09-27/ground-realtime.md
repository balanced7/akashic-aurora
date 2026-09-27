# ground:realtime

_Verbatim agent return, workflow wf_fc6a68ac-233, 2026-09-27._

## The premise in the task brief is false, and that changes the whole answer

"NOTHING INFERS a tempo from what the human plays. There is no onset analysis, no beat tracking, no quantization anywhere in the tree" — this is wrong. A complete causal beat tracker and live sheet-music transcriber was built on 2026-09-14/15 and is in the tree now, 5,459 lines under `E:\AI-Setup\arsenal\web\piano\score\`:

| File | Line 1 says | What it is |
|---|---|---|
| `score/onsets.js:1` | "Onset groups for live sheet music" | chord/roll/run/grace grouping, salience for the tracker, explicit finality (`avail`) |
| `score/beat.js:1` | "Beat, rough BPM and steadiness from expressive MIDI" | IOI induction + up to 24 competing agents (Dixon BeatRoot, run causally), periodicity strength, lag-2 settled beats, tatum meter, taps, "This is 1", ÷2/×2/2↔3 family |
| `score/quantize.js:1` | "Per-beat rhythm" | per-beat division over {1,2,3,4,6} with a cost model; causal `decide()` **and** non-causal `cleanDivisions()` Viterbi |
| `score/measures.js`, `hands.js`, `meter.js`, `marks.js` | | bars, written durations, ties, voices, clefs, meter suggestion, pickups |
| `score/settle.js:1` | "Bar states for a live score that settles without rewriting itself" | the commit-and-revise machine, `settleBeats: 4` (`settle.js:22`) |
| `score/index.js:89` `createTranscriber`, `:665` `clean` | | the live pipeline and the offline pipeline, same code |
| `score/layout.js`, `paint.js`, `engrave.js`, `ribbon.js`, `musicxml.js`, `midi.js`, `export.js` | | engraving, MusicXML, MIDI |

Plus `arsenal/web/piano-lab-score.js:1` (live lab page, Web MIDI + replay, 9:16 band) and `arsenal/score_cli.mjs:1` (Node CLI over the practice logs). Research: `research/in-flight/live-sheet-music-2026-09-14/` (7 docs, 360 KB), receipts in `state/arsenal/score/` (14 dated JSON files), tests `tests/score_{beat,quantize,settle,hands,layout,export,fixtures,lab}.test.mjs` + `tests/test_score_export.py`.

I re-ran it this session on Daniel's take from today (`node arsenal/score_cli.mjs clean 20260927-171534-085f6ee9`): **4,633 note-ons → 274 measures, 4,601 notes placed in bars, 32 left as tape, 285 tuplet groups.** It works. The question is no longer "can we", it is "why does it not claim the rhythm", and the answer is on record.

---

## 1. What changes when tracking must be causal — the latency floor, measured

All numbers below are from dated receipts in the repo, not from my head.

| Consumer | Lag | Source |
|---|---|---|
| **Onset usable** | 40 ms (chord window) to 60 ms (near-chord across hands) after its first note | `onsets.js:31-37`; `tempo-meter.md` 6.8 |
| **Tick clock** | 250 ms (`tickMs`, `beat.js:70`) | so cursor/pip lag = 40-60 ms + up to 250 ms ≈ **under ½ beat** |
| **(a) Tempo estimate** | readouts start at 4 s; **mean 9.4 s** until the shown BPM is within 8% of truth for 2 s, and 4 of 81 synthetic pieces never get there. `bpmShown` additionally waits 1 bar with no flip, no gap, no hold (`shownConfirmBars: 1`, `beat.js:78`) | `tempo-meter.md` §4.2 "Other synthetic receipts" |
| **(b) Beat phase** | lag 0 for the cursor (agent beats); **lag 2 beats** for the beats notation uses — a hit beat takes its onset time, a miss is interpolated between neighbours | `tempo-meter.md` 4.1 step 5, 6.8 |
| **(c) Bar / downbeat** | phase decision runs once a second and needs `phaseHold: 4` consecutive decisions with margin, and 2 bars of beats to exist → **4-8 s**. Synthetic downbeat F **0.578** overall, **0.173 on strong rubato** | `index.js:1` header (phase rules), `beat.js:75`, `tempo-meter.md` §4.2 |
| **(d) A bar I would show as notation** | bar end + `settleBeats: 4` → **~2 bars / 8 beats behind the playhead** (4 beats for the bar to finish + 4 to settle) ≈ **6 s at 80 bpm** | `settle.js:14,22`, `index.js:65` |

Tempo *changes* lag more: a 70→95 bpm step was recovered in 4.9-10.3 s; a sudden double-time lags about 2 bars (`tempo-meter.md` §4.2, 6.5 line "recovered in 5-10 s").

**The floor that actually bites is not latency — it is confidence.** The tracker is gated: a bar is drawn as metric only while the steadiness band reads `steady` for the bar's whole span (`beat.js:127`, rung ladder). On Daniel's own 21 sessions the band reads `steady` **0% to 6.8% of the time** (`state/arsenal/score/ls1fix-r1-bench-2026-09-15.json`, `steadyShareRange: [0, 0.068]`; e.g. S4 steady 0 / loose 0.128 / free 0.857). And the reason that gate exists is honest: on random onsets the share of notes landing on the tracker's grid is 0.62, statistically identical to strong rubato's 0.60 — **the tracker bends to fit random notes**, so grid fit cannot be used as confidence. Periodicity strength can (random p90 3.2 vs metronomic p10 6.9). `tempo-meter.md` §3 item 5.

Consequences on real data, both measured by me this session:
- Today's take: all 274 measures came out `kind: "tape"`. Per-bar band: 8 bars `steady`, ~143 `loose`, ~140 `free`.
- The LS5 live receipt on a 180 s replay of S12 through the live ribbon: `tapeBars: 71`, `trBars: 73`, **`commits: 0`** (`state/arsenal/score/ls5-lab-2026-09-15.json`). Zero metric bars drawn.

So: **realtime notation is already engineered and already runs; on his solo playing it correctly declines to notate.** That is the finding to give him, and it is not a defect — it is the system refusing to fake a grid. Strong-rubato downbeat F of 0.173 says what faking it would cost.

**Cost is a non-issue.** Causal tick on S12 (7,502 ticks): mean **0.033 ms**, p95 **0.156 ms** (`ls1fix-r1-bench`, LR3c, threshold 0.2). Transcriber p95 **0.275 ms per onset group** (`ls2-bench`, LR5, threshold 0.5). Engrave a 67-onset bar p95 **0.2 ms**; tile upload to WebGL p95 **≤ 1.3 ms** (`ls5-lab`, LR11b/d). Whole 23-session offline export: **2,071 ms for 131.3 minutes of music = 3,805× realtime** (`ls4-bench-2026-09-15.json`). There is no performance argument against doing this live.

## 2. Commit and revise — the N is settled, with numbers

`settle.js` is the pattern, already built: bars go `open` → `settling` → `settled`. A settled bar's content is final — `upsert()` with a different signature on a settled bar is **refused and counted** (`settle.js:32-36`), and `drop()` never removes one. Corrections learned late (a level flip, "This is 1", a key change) are **forward-only**: they start at `firstUnsettled()`.

Relabel churn against 8 beats of hindsight, pooled over 21 of his sessions (`ls2-bench-2026-09-15.json`, LR6b):

| Settle at | onsets that would change | metric bars that would change |
|---|---|---|
| lag 0 | **2.78%** (range 1.0-4.6%) | 0 |
| lag 1 beat | 1.19% | 0 |
| lag 2 beats | **0.035%** | 0 |
| lag 4 beats | **0.000%** | 0 |

LR6a: 1,998 settled bars across the full replay, **zero changed after settling**. So N = 2 beats is already near-perfect and N = 4 (shipped) is exact on this corpus. N is not the problem; the steady gate is.

**What he sees while a bar is provisional** — three visual states, all built (`piano-lab-score.js:10-13`): an open bar repaints proportionally (`paint.js`), a settling bar re-engraves in **light ink**, a settled bar is engraved once in full ink and never drawn on again (LR11d: `drawCallsAfterSettle: 0` over 84 settled tiles). The honest cost: **median 68.7 notehead/label changes per minute** in the open+settling bars, range 11-137 across sessions (`ls2-bench`, LR6c). That is roughly one visible change per second in the provisional tail. For a drummer watching his own bar form, that flicker is the thing to tune, and LR11e measured the crossfade shift at settle (mean notehead x-shift, threshold ≤ 0.5 staff space).

## 3. How it attaches here

**How events leave the page today.** `piano.js:19` imports `createPerformanceLog` from `piano/log.js`; `piano.js:2585` `LOG_ENDPOINT = "/api/performance"`; `piano.js:2593` builds the log. Nothing is sent per note: `log.js:146` `flushMs = 1000` — queued events become one numbered batch every second (`log.js:335`), buffered in IndexedDB, uploaded by one uploader holding a cross-tab Web Lock. Server: `serve.py:317` (GET probe), `:325` (`_performance_get`), `:345-349` (`open` / `events` / `close` POST), handler `serve.py:531`. Events land at `performance.py:213` appending `events.jsonl`; `performance.py:1179` `summarize()`, and **`performance.py:1391-1417` already groups onsets in Python** with `ONSET_MERGE_MS = 40` (`performance.py:41`) and writes an `ioi_histogram`.

**Where the analyzer must sit: in the browser.** Not a preference — arithmetic:
- In-page: onset available at 40-60 ms, tick every 250 ms, cost 0.03 ms/tick. Total lag to a beat pip ≈ 0.3 s.
- Behind the log: **≥ 1 s of batching before the first byte leaves** (`flushMs`), plus HTTP, plus the uploader is deliberately lazy and backs off to one try per 60 s when the server is unreachable (`log.js:146` `uploadEveryMs`, and `piano.js:2586-2600` deliberately points the log at port 9 when routes are absent). The log is engineered to *lose nothing*, not to be *prompt*. Feeding a realtime analyzer from it would fight its design.

So: **analysis in JS in the page; Python downstream for verification and archival, never in the live loop.** That is what the tree already does, and `score/*.js` are written for it — every module's first line says "pure ES module: no DOM, no clock".

**Precedent for in-page live analysis — it is strong.** `piano.js:2779` `currentInfo()` runs the chord reader and key tracker on a dirty flag (`detectDirty`, set in `noteOn`/`noteOff`/pedal/key changes), called from the render loop at `piano.js:3264` and `:4458`, and its result is what gets logged as a `chord` event (`piano.js:2624` `logChord`). The reader itself is a pure injected module: `chordread.js:1-30` — `createReader({ Theory, NV })`, frozen result shapes, tested against `tests/fixtures/theory/`. **A beat/score HUD would be structurally identical**: pure module, injected, dirty-flag driven, fed by a 250 ms tick instead of per-note.

**The remaining wiring is one named, gated slice.** `live-sheet-music-plan.md` §9: LS0-LS5 are built; then a gate — *"Jam build committed; `piano.js`, `piano.html`, `piano.css`, `serve.py` clean in git"* — then **LS6 Integration: feed events; score layer; HUD; header; REC**. LS6's first item (move `spellForKey` to `piano/spell.js`) is already done (`piano.js:29` imports it). Right now `git status` shows `arsenal/web/piano.js` and `arsenal/web/piano.html` modified, so the gate is not clean as of this moment.

## 4. What to show live, cheaply — ranked by drummer-value ÷ cost

`beat.js:639-642` already returns, every 250 ms: `{ bpm, bpmBeat, bpmShown, mode, band, per, hitShare, cv, readout, source, drawing, period_ms, factor, levelBpm, family, beats, settled }`. `meter.js:1-40` already models the header, the meter suggestion chip and the subdivision chip. **Tiers 1-3 below are computed today and thrown away for want of a HUD.**

1. **Pulse-confidence meter + band word** (`steady` / `loose` / `free` / `hold`) — free, already computed (`beat.js:614-622`). This is the highest-value readout in the system for him, because it is the machine saying *"I can hear your pulse"* or *"I cannot"*, and on his takes the answer is usually the second one. Showing it turns an invisible refusal into information.
2. **`bpmShown` + beat pip + ÷2 / ×2 / 2↔3 family buttons + tap + "This is 1"** — free, all built (`beat.js:639-642`, `family`). Measured display stability: 0.26-0.68 flips/min, ×2 flips 0-0.14/min (`ls1fix-r1-bench`, LR3b).
3. **Subdivision / feel chip** ("sounds like triplets?") — free, built (`meter.js:28-33`, `chipRule: "grid"`, 8 consecutive decisions).
4. **A feel lane: per-note deviation from the written grid, in ms, as a strip under the staff — NOT BUILT, and it is the one a drummer would actually want.** The data is already retained: every note in the clean score carries `t_ms` and `perf: { t_ms }` alongside its grid `tick`/`pos`, and each measure carries `beats_ms` and `sigma_ms`. I derived it this session on today's take (4,586 notes):

   ```
   deviation from the written grid:  p5 -44   p25 -2   median +2   p75 +20   p95 +61 ms
   median |deviation| 12 ms,  stdev 32 ms
   by slot:  1/4 |dev| 18.8   1/3 +18.7 median (late!)   1/2 19.0   2/3 -5.3   3/4 20.0
   ```
   His triplet 8ths sit a median **+18.7 ms late** and his second-triplet **5 ms early** — that is phrasing, in milliseconds, out of data the pipeline already produced. **Caveat, stated as a limit: the grid is anchored on his own onsets (a hit beat takes its onset time), so the on-beat slot is 0 ms by construction and the off-beat numbers are measured against an interpolated line between his beats, not against a smooth tempo curve.** To measure feel properly you need the non-causal tidy pass (`tempo-meter.md` 6.9, slice TM4, not built): one smooth tempo map per phrase, then residuals against it.
5. **Swing-ratio gauge** — not built; **no swing measurement exists anywhere in the score lane** (`grep swing` hits only `arsenal/band.py:886-910`, `_swing16`/`NEO_SOUL_SWING`, which *generates* swung hats). Once the feel lane exists this is a few lines: the first/second-eighth duration ratio on `d=2` beats.
6. **Syncopation heat** — not built. Only a notation rule mentions it (`measures.js:220`). Needs a weight model chosen and argued (Longuet-Higgins/Keith or Sioros), so it is design-cost, not code-cost. Lower ratio than 4 and 5.
7. **Full live notation** — built, but gated to 0-6.8% of his playing. Lowest ratio *today*, highest *after* the tidy pass and LS9 retuning.

**One root-cause item that gates everything in tier 4-5.** `piano.js:3513` `onMidiMessage(ev)` reads `ev.data` and **discards `ev.timeStamp`**; `noteOn` then stamps `clock()` itself, so every logged onset carries the render-frame delay of the handler that saw it. The synthetic injection path at `piano.js:4602` already fakes a `timeStamp` that nobody reads. `tempo-meter.md` 6.10: the prototype found **±25 ms of added jitter moves the beat level on up to 69% of readouts on some sessions**. If we are going to show a drummer his timing in milliseconds, we must fix the timestamp source first, or we will be showing him our own frame jitter and calling it his feel. It is a small change and the measurement drill (TM-D) is already specified.

## 5. Offline and online cannot drift, because there is only one implementation

**Do not copy the tempomap twin pattern here.** That pattern (`arsenal/web/piano/tempomap.js` ↔ `arsenal/jam/tempomap.py:1-6`: "The Python twin... Every function here has a camelCase twin there that does the same arithmetic in the same order, and both run `tests/fixtures/jam/tempomap_cases.json`", verified to 0.001 ms by `tests/test_arsenal_jam_schemas.py:4-5` + `tests/jam_tempomap.test.mjs`) exists because the **jam server** needs bar↔epoch arithmetic in Python at runtime. It is two implementations held together by a fixture — real, working, and a permanent tax.

The score lane already avoids that tax by construction:
- `score/*.js` are pure — "no DOM, no clock" on the first line of every file; the clock is passed in.
- The **live** page imports them: `piano-lab-score.js:19-24`.
- The **offline** CLI imports the same files under Node: `score_cli.mjs:42-47`.
- `clean()` (`index.js:665`) is *the same transcriber* in `deferred: true` mode (`index.js:670`) — no bar settles until its segment closes, then each segment is quantized once with the Viterbi divisions. Live and clean differ by a flag, not by a codebase.
- `beat.js` is deterministic by construction: `addGroup()` only queues, `tick()` does the work, and the clock is monotonic (`tick(T)` throws `RangeError` on a backward T) — "so a replay and the live page agree" (`beat.js:14`).
- `tests/score_quantize.test.mjs:214` asserts clean and live agree on the same events.

**So the answer to "what should be shared" is: everything, and it already is.** The rule to write down and keep: *the analysis core stays single-source in pure JS; Python reads artifacts, never re-implements analysis.* That is already the shape of `tests/test_score_export.py` — an independent Python-stdlib reader that verifies the JS output's MusicXML and MIDI (`state/arsenal/score/ls4-py-2026-09-15.json`: 23 exports, 30,352 notes, LR9a/b/c all pass, 0 unmatched ties, 0 ms MIDI error). Python as the adversarial verifier is worth keeping; Python as a second tracker is not.

**One drift landmine to flag now:** `performance.py:1391` already groups onsets in Python at `ONSET_MERGE_MS = 40` with a comment pointing at `onsets.js`, and there is **no shared fixture between them**. `onsets.js` has since grown near-chord (60 ms / 7 semitones), roll merging and grace detection that the Python has not. Two onset groupers, one comment, no test. Either delete the Python grouper in favour of reading the CLI's output, or give the pair a shared fixture the way `tempomap` has one.

---

## Limits — what I did not verify

- **I did not open the lab page in a browser this session** and did not test live Web MIDI input. The LS5 receipt's live steps are a replay of S12 (`steps` end at `"S12-180s"`), not a Web MIDI drill. `piano-lab-score.js:7` calls live MIDI a "bonus"; `live-sheet-music-plan.md` §9 flags cross-tab Web MIDI sharing on Windows as "medium confidence".
- **I did not re-measure the synthetic numbers.** Beat F 0.642, Acc1 0.710, downbeat F 0.578, meter 81.5%, the 9.4 s convergence — all from `tempo-meter.md` §4.2 (held-out seeds 37/41/53, 81 pieces), dated 2026-09-14. I re-ran only the offline CLI on one real session.
- **LR4g** ("live view never shows metric bars from rung 4 outside `steady`", threshold 0 bars) — I found the threshold in the plan and the enforcing code (`beat.js:127`), but did not locate a dated measured row for it. LR6a and LR6b I did verify in `ls2-bench-2026-09-15.json`.
- **The microtiming table in §4 is mine, written this session**, not an existing receipt, and its on-beat column is circular (grid anchored on his onsets). Nothing was committed; the run wrote only `state/arsenal/score/20260927-171534-085f6ee9/rt-lens/score.clean.json`.
- **I did not assess whether the LS6 gate is passable** beyond noting `arsenal/web/piano.js` and `arsenal/web/piano.html` are modified in `git status`.
- **madmom / music21 / librosa**: I did not need to evaluate them and did not test any install. Nothing above requires a new dependency — `score_cli.mjs` is "Node CLI, zero dependencies" and the live path is browser JS. `librosa.beat.beat_track` with a precomputed onset envelope would be a *second* tracker to compare against, which is slice TM5's job (an offline upper bound on labelled takes), and `tempo-meter.md` §7 already argues the case: all strong symbolic models are offline, trained on classical piano, and score downbeat F 14-28% on ASAP — worse than what is running here.
- **The 69-session corpus**: the LS4 bench covered 23 sessions (those existing on 2026-09-15). The other 46 have never been run through the pipeline. Re-running `node arsenal/score_cli.mjs bench` would cost about 6 s of CPU by the measured rate and would be the cheapest new evidence available.