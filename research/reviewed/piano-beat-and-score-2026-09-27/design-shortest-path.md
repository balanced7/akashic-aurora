# design:shortest-path

_Verbatim agent return, workflow wf_fc6a68ac-233, 2026-09-27._

I have what I need. All four lenses are right that the pipeline exists; two of their central claims do not survive my own measurement.

## Corrections to the grounding, with receipts

**The brief is wrong and all four lenses are right about that.** A complete causal tracker + transcriber exists: `arsenal/web/piano/score/` (19 modules), `beat.js` 43,828 bytes, `quantize.js`, `index.js`, plus `research/in-flight/live-sheet-music-2026-09-14/` (7 docs, 360 KB). Confirmed no deviation/microtiming/swing/syncopation code anywhere: grep over `score/*.js` returns only a rhythm-spelling comment at `measures.js:220`.

**C1 — NEW, and it reorders the whole build: a supplied beat unlocks the entire take. No lens tested this.** I synthesized a whole-take taps file and ran the shipped CLI:

| | bars metric | bars tape | `rhythm` | tape notes |
|---|---|---|---|---|
| inferred (`lens6full`) | **0** / 274 | 274 | `unverified` | 32 |
| tapped (`tapprobe`) | **275** / 277 | 2 | `tapped` | 12 |

`index.js:447` sets `kind` metric only when every tick drew bars; `ladder()` (`beat.js:122-129`) gives bars on the inferred rung *only while* `mode === "steady"`, which on his takes is 0–6.8%. The tape verdict is entirely the steady gate. The engraver, quantizer and tuplet brackets all work — 264 tuplet groups came out.

**C2 — FALSIFIED: fixing the grid does not fix readability.** The notation lens's core diagnosis ("the same engraver produces 0 ties on oracle beats… it is the beat grid's error surfacing as tie clutter. Do not retune the engraver"). Going from 0 metric bars to 275:

```
INFERRED  ties/bar med 8.0  mean 8.61  p90 18  max 44   pieces/bar 23
TAPPED    ties/bar med 7.0  mean 8.37  p90 18  max 44   pieces/bar 23
```

Essentially unchanged. The "0 ties on oracle beats" result must have come from synthetic fixtures whose notes were generated on a grid. On his playing, written duration median is 0.50 beat, only 11.3% of notes exceed one beat and 30 exceed a bar — so the ties are beat-line spelling splits of ordinary 8ths/16ths in sustained polyphony, intrinsic to the material. **Reject "fix the grid and readability comes free."**

**C3 — both lenses' grid-bias stories are wrong, in different ways.** Measuring against the real `beat.js` grid (n=4586): **52.4% of on-beat notes are *exactly* 0.000 ms** — the grid is anchored to them. The remaining 787 average +15.95 ms. So it is neither "0 by construction" (realtime lens) nor a clean "grid is early by 3–6 ms, bias removal mandatory" (quantization-feel lens, whose figure came from a librosa stand-in grid and does not survive on the real one). Every slot mean is *positive* (+2.0 to +20.2), and `|mean|/sd` is **0.05–0.56** — the systematic part is at most half the noise.

**C4 — per-slot millisecond headlines are ~2× overclaims.** Split-half by time, anchoring on-beats excluded: profile shape correlates **r = 0.886**, but individual slot means move **±6–10 ms** between halves (the 1/4 slot: +2.36 → +12.72). So "your off-16ths are early by 5–6 ms" and "triplet 8ths +18.7 ms late" are not supportable. The *shape* replicates; the per-slot number does not.

**C5 — taps expire after ~4 bars.** `beat.js:434`: `tapUntil = t + c.tapValidBars * tactusPerBar() * p` with `tapValidBars: 4`. The tempo-induction lens's "one take where he taps the beat and marks bar 1 converts the entire lane" is wrong — taps must be continuous. Resolved below by tapping along to *playback*.

**C6 — Verovio is not installed.** `py -m pip list`: librosa 0.10.2, numpy 2.4.4, scipy 1.17.1 present; **verovio, music21, partitura absent** (py 3.11.9). The notation lens's 336 ms/16 ms receipts are from some other environment. Nothing in stages 1–2 below needs it.

**Confirmed as stated:** `musicxml.js:369` beam bug — my independent count: **1,028** chord members carry `<beam>`, **0** carry `<tuplet>`, 166 measures. `quantize.js:106` computes `e` and discards it (again at `:195` for the σ EMA). `quantize.js:143` computes `runnerUp`; grep over `arsenal/` + `tests/` shows **nothing reads it**. `cleanDivisions` takes σ as a **single scalar** for a whole segment, and `index.js:346` passes `q.sigma()` — the *end-of-segment* value. `piano.js:3513` reads `ev.data` and discards `ev.timeStamp`; `:4602` fakes one nobody reads. Grid breathing p90/p10 = **1.57** against a rubato threshold of 1.08.

---

# Architecture: the Feel Lane

**Design axiom, forced by C1+C3:** a feel claim measured against a grid inferred from the same notes is circular — 52.4% circular, measured. So **the beat reference must come from the human.** Everything else follows.

## Components

**1. Tap capture — zero new capture code.** A tap session *is* a performance session. He plays back a take and taps along on one pitch (or the pedal); the existing `log.js` → `serve.py:345` → `performance.py:213` path records it unchanged.
- `scripts/taps_from_session.py` — **new, ~40 lines.** In: a tap session's `events.jsonl` + `--pitch N` + `--offset-ms` (playback start alignment). Out: `taps.json` `{taps_ms:[...], one_ms, session, tap_session, pitch, offset_ms, captured_at}` — exactly what `score_cli.mjs --taps` already parses (`score_cli.mjs:92-96`). Solves C5: continuous taps for the whole take, without tapping while playing.

**2. `arsenal/web/piano/score/feel.js` — new, pure ES module** (`no DOM, no clock`, matching every sibling's contract). The only new analysis organ.
- In: a score output object (`{meter, segments, measures[{beats_ms, …}], notes[{id, t_ms, bar, pos, dur, voice, staff}]}`) — i.e. what `index.js:614` already writes to disk. Plus `gridRef` provenance.
- Out: a `FeelReport` (contract below).
- It consumes the **export**, not internal state, so it runs offline today on files already on disk and live later on the same object. That is the seam.

**3. Two patches to `quantize.js` — extend, do not parallel.**
- `fitOf` (`:101`) returns `devs: e[]` alongside `fit`. `decide()` and `cleanDivisions()` carry `devs` and `sigma` per beat into their return objects (`:199`, `:253`).
- `cleanDivisions` accepts `sigmaOf: (bb) => number` so the Viterbi uses the live pass's **per-beat** σ instead of one end-of-segment scalar. Per-beat σ spans 2.7–3.2× within a segment, so the fit term is currently mis-weighted by up to 10×.
- `margin = runnerUp.cost − cost` is promoted into the returned decision so it stops being computed-and-discarded.

**4. `arsenal/web/piano/score/syncopation.js` — new, pure.** LHL per note, per stream. Separate module because it is testable against published examples independently of any grid.

**5. `arsenal/score_cli.mjs feel <session>` — new subcommand.** Emits `feel.json` beside the existing `performance.mid` / `quantized.mid` / `take.musicxml`.

**6. `scripts/feel_render.py` — new.** In: `feel.json` + `roll.txt`. Out: SVG/PNG. Reuses `scripts/piano_roll_render.py`. **Rule: Python reads artifacts, never re-implements analysis.** (The `tempomap.js`↔`tempomap.py` twin tax is not repeated. The existing drift landmine — `performance.py:1391` grouping onsets at `ONSET_MERGE_MS = 40` with no shared fixture against `onsets.js` — is why.)

## Data contract

```
FeelReport = {
  api: "arsenal.piano.feel/v0",
  grid: {                        // provenance. every number below is void without it
    source: "taps" | "jam" | "song" | "inferred",
    rhythm: "tapped" | "jam" | "inferred" | "unverified",
    hash:   sha1 of concat(measures[].beats_ms),   // invalidation key
    rev, take, session,
    trust: "reference" | "circular"   // "circular" iff source === "inferred"
  },
  notes: [ {                     // joined to score notes by stable note.id
    id, bar, pos, d, slot,       // slot = round(posInBeat/beatTicks*d)
    dev_ms,                      // t_ms − grid time. signed. early negative
    dev_beat,                    // dev_ms / P     <- the portable unit
    dev_grid,                    // dev_ms / (P/d) ; |·|>0.5 = nearer another slot
    P, sigma, margin             // margin < marginFloor => reading is a coin flip
  } ],
  profile: [ {                   // per (segment, d, slot), and per stream
    seg, d, slot, stream, n, mean_ms, sd_ms, ratio,   // ratio = |mean|/sd
    split_half_delta_ms,         // C4: the honest error bar
    claimable: bool              // ratio >= 1 AND |split_half_delta| < |mean|/2
  } ],
  swing: [ { seg, n, median_x, ratio, ci95: [lo,hi], sigma_x_ms, verdict:
             "straight"|"swung"|"triplet"|"sloppy", claimable } ],
  syncopation: [ { bar, stream, lhl, wnbd, notes: [{id, weight}], phase_source } ],
  tuplets: [ { bar, beat, d, max_abs_dev_ms, margin, flag: "clean"|"thin"|"spurious" } ],
  limits: [ string ]             // printed on every rendering. non-empty by design
}
```

Four contract rules the measurements force:

1. **`grid.trust` is mandatory and `"circular"` is not renderable as feel.** If `source === "inferred"`, `feel_render.py` prints the tempo curve and refuses the per-slot table. This is the 52.4% finding made structural.
2. **`dev_beat`/`dev_grid`, not `dev_ms`, is the primary.** 10 ms at 87 bpm and at 230 bpm are different musical facts; his grid breathes 1.57×.
3. **`claimable` gates every displayed number.** Measured `ratio` is 0.05–0.56 everywhere and split-half deltas are ±10 ms, so with today's data almost nothing is claimable — and that is the honest output, not a bug.
4. **Retirement/invalidation:** `feel.json` is derived, never an atom. It is recomputed from `events.jsonl` + the committed grid. A `FeelReport` whose `grid.hash` does not match the score it is rendered against is **discarded, never migrated**. Deviations never enter MusicXML as notated content.

## Algorithms, and why over the named alternatives

| Choice | Over | Reason |
|---|---|---|
| **Taps (rung 3) as the feel reference** | inferred rung 4 | Only a human reference breaks the 52.4% circularity. And it is the only rung that yields metric bars: 0/274 → 275/277, measured. |
| **Keep `beat.js` (BeatRoot multi-agent) for BPM/tempo curve** | global ACF/tempogram; librosa DP; bar-pointer HMM; madmom | ACF gives "confident noise" (whole-take peak r 0.034 with 7 rivals inside 14%); librosa DP made an octave error (162 vs 97 bpm) and held beat intervals to ±12% against a 39% real tempo range; HMM is 1,000+ lines and met-align scores 56.5 F live; madmom needs an install with known numpy pain and would be a *second* tracker. *(ACF/librosa/HMM figures are the tempo-induction lens's, not independently re-measured by me.)* Also: it is already tested (133 receipts) and costs 0.046 ms per 250 ms tick. |
| **Keep per-beat cost + Viterbi over {1,2,3,4,6}** | fixed 16th grid; HMM | A fixed grid cannot express triplets at all. The existing model already caught all clean triplets in the take when called as `index.js:346` calls it. |
| **Per-beat σ into the clean pass** | the shipped single scalar | σ varies 2.7–3.2× inside a segment; the snapshot mis-weights the fit term up to 10×. |
| **LHL 1984 as primary syncopation measure, per stream (Sioros 2011 extension)** | Keith 1991; WNBD; Pressing; Toussaint | Keith is unnormalised and becomes a note-density proxy (corr −0.118 with LHL; it *inverts* the ranking of a sparse displaced figure vs a dense run). WNBD knows the beat but not the bar. LHL alone is **per-note attributable** — you can point at the notehead. Per-stream because for a drummer syncopation is per-limb; `hands.js` already assigns streams. |
| **Swing measured on quantizer-confirmed `d=2` beats only** | raw IOI ratios | Conditioning is decisive: unconditioned σ_x 0.024–0.140 beat ("sloppy everywhere"), conditioned 0.018–0.038. Unconditioned samples mix 16th offbeats into a pair statistic. |

## Triplets, swing, syncopation — specifically

**Triplets.** Three onsets fitting the 3-grid is a *signal*, not an ambiguity (3-grid rms 6.3–13 ms vs 4-grid 34–58 ms on real beats). The genuine ambiguity is a triplet with the middle note missing vs a swung pair — timestamp-identical, resolvable only at phrase level by whether the 1/3 position is occupied *anywhere* in the window.

Two new gates on any engraved tuplet bracket, both cheap, both closing real failures I can point at:
- **`max_abs_dev_ms` gate.** Three beats in this take read `d=3` with internal deviations of +41/−70, +74/−41, +22/−66 ms — two notes ~73 ms apart near the half-beat, spread across a 3-grid to dodge the `collision: 6` penalty. **These would engrave as triplets with 70 ms errors inside them.** Any bracket whose worst member exceeds ~0.25 × (P/d) is flagged `spurious` and demoted to the runner-up reading.
- **`margin` gate.** The entry beat of a triplet run is the one at risk: closed form, d=3 beats d=4 for a perfect triplet only while σ < 0.0575·P to *enter* but 0.1179·P to *hold* — a high entry barrier and a near-unbounded retention basin. The single beat the live pass missed was the run's first. Brackets with margin below floor render as ambiguous with the alternative available, not silently resolved.

**Swing.** Reported as a distribution, never a number: `median_x`, `ratio = x/(1−x)`, bootstrap CI, `sigma_x_ms`, `n`, and the four-way verdict (σ_x > 0.06 beat → sloppy; |median−0.5| < 0.03 → straight; late + 1/3 occupied ≥3 times → triplet; late + not → swung). **Withheld entirely when `ratio < 1`** — saying "you swing" when the systematic part is under half the random part is overclaiming, and on this take it is.

**Syncopation.** LHL requires committed bar phase, so every record carries `phase_source` (`jam` → `song` → `"This is 1"` → inferred): a one-beat phase error rewrites every score in the bar.

## How microtiming is preserved rather than quantized away

The loss is already being computed and thrown away twice — `quantize.js:106` and `:195`. Nothing needs re-deriving:

1. **`performance.mid` is already lossless** (1 tick = 1 ms, every logged event, 0 ms error under receipt LR9b) and `quantized.mid` already holds the grid. Both are on disk for this session. What is missing is the **join**: `note.id → {bar, pos, dev_ms}`. That is `feel.json`.
2. **The score keeps notated positions unchanged.** A drummer must be able to read it. Deviations live in the sidecar, never in MusicXML.
3. **A deviation ribbon** under the staff — one signed tick per note against a zero line, early left / late right. Hosted in `ribbon.js`, which already interpolates against real `t` (`:372`), rather than a new surface.
4. **`dev_grid` makes the loss legible**: |dev| median 12.3 ms, p90 53.0, p99 105.0. At a 634 ms beat, 53 ms is 8% of a beat — audible, and his. It is kept, not discarded.

## Build order, each stage falsifiable

**Stage 1 — a reference, and the one-line bug. (Smallest thing that tells him something true.)**
Ship: `taps_from_session.py`; the `musicxml.js:369` fix (`beam: k === 0 ? beamOf.get(it) : null`); `feel.js` emitting `notes[]` + `grid` only; `score_cli.mjs feel`; a tap-vs-play plot in `feel_render.py`. No profile table, no swing, no syncopation.
*Artifact:* "Here is where your notes sat relative to the beat **you** tapped." Non-circular, needs no notation, native to a drummer.
- **Passes if:** a tapped run yields `rhythm: "tapped"` and ≥90% metric bars (I measured 275/277 with synthetic taps); chord members carrying `<beam>` goes 1,028 → **0**; and **tap-to-tap agreement on the same take, tapped twice, has median |Δ| below 25 ms.**
- **Fails if** the two tap passes disagree by more than the deviations being claimed (median |Δ| > 40 ms). Then taps are not a reference and **the entire feel lane is dead as designed** — fall back to reporting the tempo curve only. This is the stage that can kill the design, which is why it is first.

**Stage 2 — the feel report, with its own error bars.**
Ship: `devs` + per-beat σ + `margin` through `quantize.js`; `profile[]` with `split_half_delta_ms` and `claimable`; swing with CI; the tuplet `max_abs_dev` and `margin` gates; the deviation ribbon.
- **Passes if:** the per-slot profile shape replicates split-half at **r ≥ 0.8** (I measure 0.886) *and* across two independent takes; and the tuplet gate flags the three known spurious `d=3` beats while keeping all 14 clean triplets.
- **Fails if** cross-take profile r < 0.5, or `claimable` is false for every slot on a tapped take. Then his feel is not measurable at this resolution; ship the tempo curve and the IOI histogram with subdivision lines, print the limit, and retire the profile table.

**Stage 3 — syncopation per stream, then live.**
Ship: `syncopation.js`; per-stream joins via `hands.js`; then wire `feel.js` into the live HUD behind LS6 (which is gated on `piano.js`/`piano.html` being clean in git).
- **Passes if:** LHL reproduces published worked examples exactly; per-stream LHL ranks a kick-on-1-plus-displaced-snare bar *differently* from an empty-on-1 bar (the monophonic collapse cannot); live `feel.js` stays under 0.5 ms per onset group.
- **Fails if** per-stream scores track `hands.js` voice errors more than the music — testable, since voice F1 is 0.859 and staff is 0.966: if syncopation disagreement concentrates in the bars where voices are wrong, the measure is reporting our voice bugs.

**Prerequisite that gates stages 2–3, not a stage:** `piano.js:3513` discards `ev.timeStamp` and stamps `clock()` in the handler, adding render-frame delay to every onset. ±25 ms of jitter moves the shown beat level on up to 69% of readouts on some sessions. **Measure the handler delay first, then fix** — if we show a drummer milliseconds, they must not be our frame jitter. Small change, drill already specified.

## Honest limits — what this will get wrong, and how he'd notice

1. **Tapping cannot be done while playing** (taps expire in 4 bars), so the reference always comes from a *second* pass over playback. **He'd notice** the feel report exists only for takes he went back and tapped.
2. **Nothing here makes the score readable.** 7–8 tie elements and 23 note-pieces per bar, unchanged by a perfect grid (C2). **He'd notice** the engraved page still looks dense. Position it as a keepsake and a proof; the analysis is the deliverable.
3. **Almost nothing will be `claimable` at first.** `ratio` is 0.05–0.56 across every slot today. **He'd notice** a report that says "straight eighths, and I can't yet distinguish your off-16th placement from noise." That is the design working.
4. **Voice errors leak into per-stream syncopation.** Voice F1 0.859, ceiling 0.938 even with perfect staves — tuning is exhausted. **He'd notice** a left-hand arpeggio jumping staves mid-figure, and syncopation scores that move with it.
5. **Phase errors rewrite syncopation wholesale.** Downbeat F is 0.578 overall and 0.173 on strong rubato, and his wobble is squarely in the strong-rubato class. **He'd notice** bar lines in the wrong place — which is why `--one` / "This is 1" is required, not optional.
6. **One take, one player, no external ground truth.** All 69 sessions are unlabelled; `BEAT_PARAMS` was tuned on synthetic playing only and TM5 never happened. Split-half and 4-segment replication are *within* one take.
7. **Not verified by me:** I did not run the JS test suites this pass (I ran `score_cli.mjs clean` and `export` end to end); I did not re-measure the lenses' synthetic figures (beat F 0.642, downbeat F 0.578, the librosa 162 bpm, the ACF r 0.034); I did not open the lab page or test live Web MIDI; I did not read the 360 KB plan corpus, so parts of this may already be specified or ruled on there — **read `plan-amendments.md` and `ls1-rulings.md` before treating any of it as new**; I did not measure the actual MIDI handler delay; I did not test a Verovio install.

## The single riskiest assumption

**That his taps are an independent reference for his own intended pulse.**

Everything above hangs on taps breaking the circularity I measured. But a drummer tapping along to playback of his own rubato playing will *entrain to what he hears* — reproducing his own timing drift in the tap track. The reference then agrees with the notes by construction, the circularity returns at one remove, and it comes back **worse**: the system stops saying `unverified`, promotes 275 bars to `metric`, and asserts a rhythm with confidence it has not earned. A grid that is merely *consistent* looks exactly like a grid that is *correct* — that is precisely why my synthetic-tap run produced 275 metric bars while proving nothing about accuracy.

The Stage 1 test is aimed straight at it: **tap the same take twice, on different days, and measure tap-to-tap agreement.** If the two tap tracks agree to within ~25 ms he has a stable internal pulse and it is a real reference. If they disagree by more than the effects we want to report, no amount of downstream engineering rescues the feel claim, and the honest product is a tempo curve with a confidence band plus an IOI histogram with subdivision lines drawn on it — both of which need none of this architecture.

**Files:** `E:\AI-Setup\arsenal\web\piano\score\{beat.js,quantize.js,index.js,musicxml.js,onsets.js,measures.js,ribbon.js,hands.js}`, `E:\AI-Setup\arsenal\score_cli.mjs`, `E:\AI-Setup\arsenal\web\piano.js`, `E:\AI-Setup\research\in-flight\live-sheet-music-2026-09-14\`, `E:\AI-Setup\scripts\{piano_roll_render.py,piano_roll_pack.py}`. New: `arsenal\web\piano\score\feel.js`, `arsenal\web\piano\score\syncopation.js`, `scripts\taps_from_session.py`, `scripts\feel_render.py`. My receipts (scratch): `C:\Users\L5\AppData\Local\Temp\claude\E--\a90a987a-4b74-4e3e-9a06-cad82f47b6b7\scratchpad\{beamcheck.py,dev.py,split.py,taps.json}`; the tapped-grid run is on disk at `E:\AI-Setup\state\arsenal\score\20260927-171534-085f6ee9\tapprobe\`.