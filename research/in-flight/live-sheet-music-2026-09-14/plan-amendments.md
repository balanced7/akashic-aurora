# Live sheet music: plan amendments

| | |
|---|---|
| Date | 2026-09-14 |
| Status | Binding for builders. **Where this file and `live-sheet-music-plan.md` disagree, this file wins.** The plan and `critic.md` are not edited. |
| Built from | `critic.md` corrections C1-C20 and section 3 (internal errors), checked against the plan, the scratch `quant.mjs` (metric and alphabet as actually run) and `arsenal/performance.py` (`KINDS`, `SOUND_END_BY`). |
| Labels | Plan labels (LS, LR, LQ) keep their meaning. New receipts continue the plan's numbering (LR2g, LR3d, LR4i-LR4k, LR8b-LR8d, LR11f-LR11g). "Start value" = not measured yet; the first dated run sets or confirms it. |
| Privacy | Benches over S1..Sn run locally; outputs go to `state/arsenal/score/` (git-ignored). Tracked files carry S-numbers and aggregates only. Fixtures are synthetic. |

---

## 0. Standing rules for LS0-LS5 (added)

1. **No VexFlow yet (LQ1 unanswered).** `score/engrave.js` v1 is our own drawer (the plan's `paintBarReduced` set, moved out of `paint.js`) behind an interface a VexFlow adapter can later implement unchanged:
   ```js
   // score/engrave.js
   export const ENGRAVER_API = "arsenal.piano.score.engrave/v0";
   export function createHouseEngraver(opts) -> {
     name: "house",
     ready(fonts) -> boolean,                     // false until the SMuFL face is loaded; engraveBar draws nothing while false
     measureBar(bar, geom) -> { minWidth, beatWidths: [] },   // pure; constant glyph boxes in staff spaces, no measureText
     engraveBar(ctx, bar, geom) -> { width, boxes: [{ kind, staff, x, y, w, h }], ms },
   }
   ```
   A later `score/engrave_vexflow.js` implements the same three methods (C9 rules apply there). LR11b and LR11e run on the house engraver now.
2. **Spelling is injected, never copied.** `spellForKey` stays in `piano.js` until LS6. Node tests build it read-only from `piano.js` source the way `tests/nashville_js.test.mjs` extracts the THEORY block (with a `theoryUi` stub for `minor`). The lab page uses `nashville.js` `spellInKey` for every tone and labels that as a lab approximation. No twin copy in score code.
3. **Voices before `hands.js`.** In LS2, `measures.js` takes an injected `voiceOf(note)`: truth voices on fixtures, a split at MIDI 60 on local benches. From LS3 it takes `hands.js` output.
4. **Lab page is replay-first (critic M8).** `piano-lab-score.html` takes `events.jsonl` replay as its primary input; live Web MIDI is a bonus. No LR11 receipt may depend on Web MIDI sharing across tabs.

---

## 1. Design corrections

### C1. Written durations under the pedal
**Changes:** plan 6.4 "Durations"; plan 12 "Decided by default" item 1 (pedalled notes as played, now filled under the pedal; mention to Daniel with LQ2, not a new question).

**Rule.** For each note: onset `t_on`, key release `t_off`, sound end `t_se` (the `sound_end` event; if missing, `t_off` when the pedal is up at release, else the next pedal up-crossing), next onset in the same voice `t_next` (chord members share `t_on`), `tol` = one 16th at the local beat (P/4 simple, P/6 compound).

1. **Pedal up from `t_on` to `t_next`:** the plan's rule is unchanged (release snapped forward within the division; legato fill when `t_next − t_off < tol`; staccato when held < 40% of the slot).
2. **Pedal down at release, or pressed between release and `t_next`:**
   - if `t_se ≥ t_next − tol`: written end = `min(t_next, bar end)`;
   - if `t_se < t_next − tol`: written end = `t_se` snapped to the nearest slot of the beat's division (never before onset + one slot), then a rest to `t_next`.
   - A pedal lift before `t_next` ends the sound, so the lift cap follows from `t_se`.
3. **Lowest voice of the lower staff:** C7 overrides.
4. **Shortest written value** = one slot of the beat's chosen division (was: a 16th).
5. **Staccato** only in case 1.

**Receipts.**
- LR4h (durations exact on fixtures): the LS0 generator gains the pedal model in section 7 LS0. The threshold is still set at the first measurement.
- **LR8b (new):** S1..Sn clean copies, pedalled bars (pedal down ≥ 50% of the bar): median rests per voice per bar **≤ 1**. Fixtures: rests per voice per bar reported against truth.

### C2. Rhythm alphabet
**Changes:** plan 6.4 cost formula, section 3 method, LS0 generator, LR4; plan 11 item 6 (sextuplets move from v2 into v1).

**Rule.** Per-beat divisions and simplicity costs (start values, tuned on LS0 fixtures in LS2 without changing the order):

| Beat | Set | λ |
|---|---|---|
| Simple meter (quarter = 24 ticks), feel straight | {1, 2, 3, 4, 6} | λ1 = 0, λ2 = 0.5, λ4 = 1.5, **λ6 = 1.75**, λ3 = 2.0 |
| Simple meter, feel triplet (C11) | {1, 2, 3, 4, 6} | λ1 = 0, λ3 = 0.5, λ6 = 1.5, λ2 = 1.75, λ4 = 2.0 |
| Compound meter (dotted quarter = 36 ticks) | {1, 3, 6, 2} | λ1 = 0, λ3 = 0.5, λ6 = 1.5, λ2 = 1.75 |

- **d = 8 (32nds, 3 ticks):** simple meters only (36/8 is not an integer). Behind option `div8`, **off** by default. LS2 turns it on for one suite run and keeps it on only if LR4a and LR4d each drop by ≤ 0.5 points and the 32nd fixture's onsets exact improves. Record the decision in section 5.
- Everything else in the cost is unchanged: fit term, 0.8 continuity, 0.8 bar-back, 6 per collision, σ₀ 40 ms, EMA 0.05, clamp 15-60 ms, f > 0.875 goes to the next beat, loose ceiling 12.
- **Loose beats** (5 or 7 groups that fit no division, or cost > 12) are drawn proportionally live, as before. Export: TPQ 24 cannot hold 5 or 7 tuplets, so the clean copy places groups in time order on the beat's d = 6 grid, minimizing total displacement. Distinct groups merge into `<chord/>` only when there are more than 6, closest pair first. Each such beat is flagged `loose: true` in `score.json`. Quintuplets wait for a TPQ change (v2).
- **Check on the critic's own caveat (LS1 bench, report only):** the share of S1..Sn beats with 5+ groups that sit where the tracker's ×2 family level is live. If it is high, the ×2 button is the fix, not d = 6.

**Receipts.**
- LR1: section 3 tables reproduce in `s3Compat` mode (DIVS {1, 2, 4, 3} for every meter, including 12/8, as `quant.mjs` ran).
- LR4a-e: thresholds unchanged, run with the amended alphabet on the section 3 suite. A drop below threshold is a failure, not a retune.
- **LR4j (new):** sextuplet-arpeggio suite. Onsets exact and bars onset-exact are set at the first measurement. False d = 6 on s3-suite beats whose truth is d ∈ {1, 2, 3, 4}, oracle beats: **≤ 1%** of non-empty beats (start value).
- LR5: threshold unchanged.

### C6. Tape collision push
**Changes:** plan 2.1 tape, 7.3 geometry, LR11a. Lands in LS5 (`layout.js`, `paint.js`).

**Rule.** One time axis for both staves; each onset group (a T1 chord or roll) is one column. Units: s = 15 px, v = 120 px/s.
- **Column width** w = **1.4 sp** (21 px), + **1.0 sp** (15 px) if any head in it has an accidental, + **1.18 sp** (17.7 px) if it holds a second. Across the two staves, the wider staff sets w.
- **Placement**, per new column i, with debt D (px right of nominal time):
  ```
  want = t_i·v + D_prev ;  min = x_prev + w_prev
  if want < min:  x_i = min                                           // push
  else:           x_i = want − min(D_prev, 0.5·(want − min))          // reclaim half the spare space
  D_i = x_i − t_i·v, clamped to [0, D_max]; if the clamp binds, x_i = t_i·v + D_max (overlap allowed and counted)
  ```
- **D_max** = min(**180 px** (1.5 s), right band edge − playhead − 2 columns). In 9:16 (band x 110-940, playhead at 70% = x 691), D_max = 180.
- **Placed columns never move.** Live and review use the same causal pass, so they match.
- **Ticks:** a faint tick every **1 s** at x = T·v + D(T), with D interpolated linearly between the neighbouring columns. Duration lines end at the warped x of their sound end.

**Receipts.**
- LR11a timings: unchanged.
- **LR11f (new):** overlapping noteheads per minute of tape. An overlap is two heads on the same staff in different columns whose boxes (1.18 × 1.0 sp, shrunk 0.1 sp per side) intersect.
  - Fixture: a 1.5 s run at 10 single-note groups/s gives **0**. A 4 s run at 10/s is reported.
  - S1..Sn replays: reported per session (S12 is the dense case); threshold set at the first measurement.

### C7. Held bass
**Changes:** plan 6.4 "held bass". Option `heldBass: true` stays the default.

**Rule.** For notes in the lowest voice of the lower staff:
- written end = min(`t_se`, next onset in that voice, end of the note's bar);
- **at most one bar-line tie**, only when the next bar has no onset in that voice before its midpoint (beat 3 in 4/4, beat 4 of 12 in 12/8, the second half-bar in 3/4 and 6/8);
- with the tie, the end is min(`t_se`, the next onset in that voice, the end of the next bar);
- the pedal line carries any remaining ring;
- ties inside a bar from the 6.5 beat-3 split do not count toward the one tie.

**Receipts.**
- LR4h fixtures include long pedalled bass (section 7 LS0).
- **LR8c (new):** bar-line ties per held-bass note ≤ 1 on every S1..Sn clean copy (100%, a construction check). LR8's "≤ 2 ties per bar" median is unchanged.

### C8. Accents
**Changes:** plan 6.5 "Dynamics", accents.

**Rule.**
- **v1 default `accents: "off"`**: no accent marks in live, clean or export.
- `accents: "voice"` (option, not the default): +**25** over the running median velocity of the last **16** notes in the **same voice**, at least **2** notes between accents in that voice, and never the top note of a chord unless the whole group clears +25.
- Turning `"voice"` on by default is a later decision, recorded in section 5 with its LR8d numbers.

**Receipts.** **LR8d (new):** accents per minute on S1..Sn: **0** with defaults; reported with `"voice"`.

### C11. Triplet feel under a simple meter
**Changes:** plan 6.3 (suggestions), 6.4 (λ table), LQ3 wording, section 3 (compound set).

**Rule.**
- **Feel is his setting:** `setOptions({ feel: "straight" | "triplet" })`, default `straight`, remembered per session. It swaps the simple-meter λ table (C2 table). It is ignored in compound meters.
- **Subdivision chip** in `meter.js`, from the tempo lane's grid test (`beat.js` exposes `subdivision: 1 | 2 | 3`): over the last **32** beats, grid 3 when thirds beat halves and exceed **25%** of on-beat salience.
  - "sounds like triplets?" when feel is straight and grid 3 holds for **8** consecutive decisions (one per second);
  - "sounds straight?" is the mirror;
  - no `steady` gate: the band must be `steady` or `loose`, not `free` or `hold`;
  - a chip only suggests; nothing changes until he accepts.
- **Clean pass:** `clean(events, { feel })` and CLI `--feel straight|triplet`. Default: the take's setting.

**Receipts.**
- **LR4k (new):**
  - 12/8 fixtures run under meter 4/4 with oracle beats at the dotted quarter: onsets exact and bars onset-exact reported for straight and for triplet. Triplet must beat straight; the margin is set at the first measurement.
  - 12/8 fixtures under 12/8 with the compound set {1, 3, 6, 2}: bars onset-exact **≥ 0.94**, the LR4a bar (section 3 reached 0.971 with the simple set).
- **LR3d (new, LS3):** the "triplets?" chip appears within 32 beats in **≥ 90%** of 12/8-under-4/4 fixtures, and in **≤ 5%** of straight 4/4 and 3/4 fixtures (start values).

---

## 2. Internal errors, restated

**TPQ rationale (plan 1, tick unit; C13, corrected again).**
- At TPQ 12, a 12/8 duplet eighth is 18 / 2 = 9 ticks, and a sextuplet 16th in a quarter is 12 / 6 = 2 ticks. **12 holds both.** The critic's line that 12 cannot hold sextuplets is itself wrong.
- 12 fails on 32nds (12 / 8 = 1.5) and on compound quadruplet 16ths (18 / 4 = 4.5).
- TPQ 24 holds every v1 value:
  - simple beat 24 → d 1, 2, 3, 4, 6, 8 = 24, 12, 8, 6, 4, 3;
  - compound beat 36 → d 1, 2, 3, 6 = 36, 18, 12, 6 (and quadruplet 9, 32nds 3).
- **Decision unchanged: TPQ 24.** The plan's "(9)" is the 12/8 quadruplet 16th, not the duplet.

**Timing spread to jitter rows (plan 3 point 2, 11 item 4, 13 point 2; C14).**
- The lanes' 35-55 ms is the spread of a **gap**. With independent per-note jitter, gap spread = √2·σ, so per-note σ ≈ **25-39 ms** (an upper bound: drift included).
- Interpolating the live, oracle-beat sweep (15 ms 99.7%, 30 ms 92.7%, 45 ms 65.0%) gives **≈ 95% at 25 ms and ≈ 76% at 39 ms** bars onset-exact against a click: about 1 wrong bar in 20 to 1 in 4, not "1 in 3 to 1 in 14" or "65-93%".
- This is a registered prediction for LR15.
- **LR15 (changed):** record the quantizer's adaptive σ per take. It is already per note, so no √2. Any comparison with a lane gap spread divides that spread by √2.

**What "bars exact" counts (plan 0, 3, LR4; C10).**
- `quant.mjs` `score()` marks a bar right when every onset **position** is right. Durations, rests, ties, voices, hands and spelling are not scored.
- Metric names from LS0 on:
  - `onsetsExact`;
  - `beatsExact` (same positions and same normalized division);
  - **`barsOnsetExact`** (the old "bars exact");
  - **`barsFullyExact`** (onsets, written durations, rests, ties and voice assignment all equal truth; reported from LR4h on, no threshold in LS2).
- LR4a-e read "bars onset-exact". Their numbers are unchanged.

**LR4f conditioning (C10).**
- **LR4f (restated):** *conditional* onset accuracy of the inferred rung, counted only inside tracker intervals whose ends match consecutive true beats within 70 ms. ≥ 0.95 [0.974]; coverage reported [0.443 all, 0.242 rub2]. It says nothing about wrong levels or phases.
- **LR4i (new): precision of shown rung-4 bars.**
  - Setup: fixtures with only rung 4 available and the meter set to truth.
  - Count: every bar the live view draws metric (LR4g gate on) that reaches settled.
  - A bar is correct only if both bar lines lie within 70 ms of true bar lines (so level ×2 / ×1.5 and phase errors fail) and every onset in it is exact.
  - Report precision (correct / shown) and the shown share (shown / all bars).
  - **Target ≥ 0.80.** If missed, raise the rung-4 metric gate (periodicity strength floor, now 4.5) in 0.5 steps until it holds, and record the new floor in section 5. Do not lower the target.

**Other wording fixes (no receipt change).**
- Plan 0: "inferred downbeats are right only 17% of the time" becomes "downbeat F-measure 0.17".
- Plan 0 (C12): add "without a jam loop, the song listener or taps, the live panel is mostly tape (steady 0-12% of his time)".
- Plan 1 (C18): 2604.22290's 97.3% used ground-truth beats **and downbeats**, with no noisy-beat test. It supports rung 1 only.
- **Taps model (plan 3).** The ±30 ms row is iid error per beat, which models the listener rung. **LR4c is relabelled "listener rung (iid beat error)".** Taps get LR2g (C4 below).
- **Section 3's 12/8 run** used the simple set, not the stated compound set. This is covered by the LR1 `s3Compat` note and LR4k.

---

## 3. Deferred items (outside LS0-LS5)

| # | What | Lands in | Done now, inside LS0-LS5 |
|---|---|---|---|
| **C3** | Free takes: Save take offers **tap-along replay** plus a note click for "1"; forced bars only if skipped. LQ2 reworded per critic "suggested shape" item 2, with the recommended default "tape live; tap-along for the saved copy". LR15's free-take clause becomes "tape live; saved copy tapped along, or flagged unverified if skipped". | **LS7** (Save take, Clean last take UI); LR15 in LS9 | LS2: `clean(events, { taps: [t_ms], one: t_ms })` treats external taps as rung 3 with full hindsight (agents anchored at taps). LS4: CLI `--taps <file.json>`. `score.json` top-level `rhythm: "jam" \| "song" \| "tapped" \| "inferred" \| "unverified"`. A span with no rung 1-3: `score.json` keeps tape measures; MusicXML gets forced bars at the rough BPM with **every** measure marked `freely`, and `rhythm: "unverified"`. |
| **C4** | Hands-free tap: a left-foot switch on the KeyLab 88 mk3 Aux input (short press = tap, press ≥ 500 ms = "This is 1", start value). **A question for Daniel** (possible purchase), asked with LQ2. | After the jam gate, **LS6 or later** (`onMidiMessage` mapping in `piano.js`) | LS0 count-in fixture and **LR2g** (below). Rung 3 from count-in taps stays valid for **K = 4 bars** after the last tap (start value, set from LR2g); after that, rung-4 rules apply (metric only while `steady`). |
| **C5** | Continuous CC64 (half-pedal) logging. | With the **`log.js` change after the jam gate** (alongside the LR16 timestamp decision), with Daniel's OK, since it changes new sessions | LS4 `midi.js`: `performance.mid` (SMF **type 0**, PPQ 500, tempo 500,000 µs) writes CC64 **127 at each down-crossing and 0 at each up-crossing** at the logged times. Drop "half-pedal kept" (plan 6.5, 7.4). **LR9b (restated):** every on, off and CC64-crossing time equals the log's `t_ms` with 0 ms error; CC64 values ∈ {0, 127}. |
| **C9** | VexFlow fonts: no unpinned `loadFonts`. Either `setFonts` against the page's loaded `Bravura` face, or pin `VexFlow.Font.HOST_URL` to versioned `@vexflow-fonts/...@x.y.z/` paths first. Plan a substitute for Academico. Gate on `fontState.smufl`. LQ1 wording: "pinned, fonts included". | The **VexFlow adapter** (`engrave_vexflow.js`) after **LQ1** = yes: LS5 lab if the answer comes before LS5 closes, else LS6 | The house engraver's `ready(fonts)` gate. Layout uses constant glyph boxes, so metrics never depend on font load. The lab page registers `FontFace("Bravura")` from the same pinned URL string `piano.js` uses. No new host. |

**Other critic items: where they go.**

| # | Placement |
|---|---|
| C10, C13, C14, C18 | Section 2 above |
| C12 | Plan 0 wording (section 2) |
| **C15** | **LS5.** A settled beat widens to its content: min width = Σ over columns of (1.18 head + 1.0 if accidental + 1.18 if second + 0.4 padding) sp, never below 96 px. **LR11g (new):** overlapping glyph boxes per settled bar on the dense fixtures (12, 24, 43, 67 onsets; 10-head chords, accidentals, seconds): **0** with widening on; reported with it off. **LR11e (restated):** mean head x shift at settle ≤ 0.5 sp on beats that did not widen (0 by construction for the slot-placed house engraver); widened beats reported separately. |
| **C16** | **LS5** `layout.js`: 9:16 score band right edge ≤ **940 px**, bottom ≤ **1436 px** (asserted in a layout test). 16:9 placement stays with LQ4. LR12 (LS6) also checks that the band sits inside those bounds in the MP4. |
| C17 | **LS6.** Ask Daniel first: hide the "now" staff while the score is on, or give `drawStaff` the hand split. Nothing in LS0-LS5. |
| C19 | Lane errata only. Settled for builders: `performance.mid` is SMF type 0; the pedal line is painted by time by us (no `PedalMarking`). |
| C20 / M7 | **LS6:** the transcriber feed sits beside `logged()`, not inside it, and copies the demo and cue exclusions. |
| M6 | Lead-sheet view: v2, offered to Daniel as the "readable on a phone" mode. Not in LS0-LS5. |
| M9 | The same as C5 plus LR16. |

---

## 4. Receipt changes at a glance

| Receipt | Slice | Change | Threshold |
|---|---|---|---|
| LR1 | LS0 | Reproduce section 3 in `s3Compat` (DIVS {1, 2, 4, 3} everywhere) | exact seeds; ±1 point |
| **LR2g** | LS1 | New. Count-in: 4 taps (±30 ms iid), then no taps for N = 1, 2, 4, 8 bars under rub1 and rub2; bars onset-exact against N | reported; sets K (C4) |
| **LR3d** | LS3 | New. Subdivision chip (C11) | ≥ 90% hit / ≤ 5% false (start) |
| LR4a-e | LS2 | Read "bars onset-exact"; run with the C2 alphabet; LR4c relabelled listener rung | unchanged |
| LR4f | LS2 | Restated as conditional accuracy | unchanged |
| LR4h | LS2 | Uses the C1 and C7 rules and the pedal-model fixtures; `barsFullyExact` reported | set at first measurement |
| **LR4i** | LS2 | New. Precision of shown rung-4 bars | ≥ 0.80 target; the gate floor moves, not the target |
| **LR4j** | LS2 | New. Sextuplet suite; false d = 6 | set at first / ≤ 1% (start) |
| **LR4k** | LS2 | New. 12/8 under 4/4 by feel; 12/8 compound set | triplet > straight; ≥ 0.94 |
| LR8 | LS3/LS4 | Plus **LR8b** rests per voice per bar in pedalled bars, **LR8c** held-bass bar-line ties, **LR8d** accents per minute | ≤ 1 median; ≤ 1 per note; 0 by default |
| LR9b | LS4 | Crossings only, CC64 ∈ {0, 127} | 0 ms |
| LR11b, LR11e | LS5 | Run on the house engraver; LR11e excludes widened beats | unchanged |
| **LR11f** | LS5 | New. Tape overlaps per minute | 0 on the 1.5 s fixture; S1..Sn set at first |
| **LR11g** | LS5 | New. Settled-bar glyph collisions | 0 with widening |
| LR15 | LS9 | Per-note σ, no √2; free-take clause per C3 | unchanged otherwise |

---

## 5. Threshold changes

Any loosened, raised or newly fixed threshold, and any gate floor moved to meet a target (LR4i), goes here **before** the receipt is claimed: date, receipt, old → new, measured value, why.

| Date | Receipt | Old → new | Measured | Why |
|---|---|---|---|---|
| | | | | |

---

## 6. Slice checklist (LS0-LS5)

None of these slices touch jam-held files. No git state changes: the seat-holder commits.

**LS0: fixtures and metrics**
- [ ] `tests/fixtures/score/gen.mjs`: deterministic by seed, TPQ 24, with an `s3Compat` mode (LR1).
- [ ] New synthetic families, all with ground-truth durations and voices:
  - [ ] sextuplet arpeggios, 5+ groups in 10-22% of beats;
  - [ ] 32nd figures;
  - [ ] pedal model: changes per harmony, 30% of notes released at 20-60% of written length under the pedal, `sound_end` events with `by`;
  - [ ] long pedalled bass (about 20% ringing past a bar);
  - [ ] voiced top line (+15-25 velocity);
  - [ ] 12/8 played under 4/4;
  - [ ] count-in taps;
  - [ ] tape density runs (1.5 s and 4 s at 10 groups/s).
- [ ] Metric helpers: beat F ±70 ms, Acc1/Acc2, flips, bands, `onsetsExact`, `beatsExact`, `barsOnsetExact`, `barsFullyExact`, duration exact, rung-4 shown precision, rests per voice per bar, accents per minute.
- [ ] `tests/score_fixtures.test.mjs`: LR1.

**LS1: onsets and beat**
- [ ] `onsets.js` and `beat.js` per plan 6.1-6.2, plus `subdivision` output and count-in rung-3 validity (K = 4 start).
- [ ] `tests/score_beat.test.mjs`: LR2a-g, LR3a.
- [ ] Local bench over S1..Sn (`score_cli.mjs bench` arrives in LS4; a scratch runner is fine here): LR3b, LR3c, and the C2 ×2-family report. Outputs to `state/arsenal/score/`.

**LS2: rhythm and settle**
- [ ] `quantize.js`: the C2 alphabet and λ tables, feel, `div8` off, loose export on the d = 6 grid.
- [ ] `measures.js`: the C1 and C7 duration rules, injected `voiceOf`.
- [ ] `settle.js`.
- [ ] `index.js`: `clean()` options `taps`, `one`, `feel`, and the `rhythm` flag.
- [ ] `tests/score_quantize.test.mjs`, `tests/score_settle.test.mjs`: LR4a-k, LR5, LR6a-c.
- [ ] Re-run the section 3 tables with the amended alphabet and the compound set; put them in the slice receipt. Decide `div8` and record it in section 5.

**LS3: hands, marks, meter**
- [ ] `hands.js`.
- [ ] `marks.js`: accents off, `"voice"` option, pedal notches.
- [ ] `meter.js`: meter suggestion plus subdivision chip.
- [ ] Spelling injected (section 0 rule 2).
- [ ] `tests/score_hands.test.mjs`: LR7, LR3d.
- [ ] LR8 with LR8b-d on local S1..Sn clean copies.

**LS4: export and CLI**
- [ ] `musicxml.js`: `freely` on every measure of unverified spans, `sign="no"` on line pedals.
- [ ] `midi.js`: SMF type 0 for `performance.mid` with CC64 0/127 crossings; SMF type 1, PPQ 480 for `quantized.mid`.
- [ ] `arsenal/score_cli.mjs clean|export|bench` with `--at`, `--seconds`, `--meter`, `--one`, `--bpm`, `--feel`, `--taps`; writes only under `state/arsenal/score/`.
- [ ] `tests/score_export.test.mjs`, `tests/test_score_export.py`: LR9a-c. Prepare one `take.musicxml` for LR10 (Daniel's drill).

**LS5: lab page**
- [ ] `layout.js`: 9:16 band ≤ 940 px right and ≤ 1436 px bottom; beat widening; tape push (C6).
- [ ] `paint.js` (tape, open bar, pedal line, header).
- [ ] `engrave.js` house backend with the section 0 interface and font gate.
- [ ] `piano-lab-score.html/.js`, replay-first.
- [ ] `tests/score_layout.test.mjs`: LR11f and LR11g geometry, C16 bounds.
- [ ] Headless page check on your own port (never 8793 or 8796; stopped after): LR11a-e timings on this machine.
