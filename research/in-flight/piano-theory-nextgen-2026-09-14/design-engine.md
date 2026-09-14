# Next-gen chord and scale detection: the engine

| Field | Value |
|---|---|
| Type | design (in flight), lens: THE DETECTION ENGINE |
| Date | 2026-09-14 |
| Author | Vandor (claude seat) |
| Status | Prototyped and measured in scratch. No arsenal/ code touched (the jam space build owns `arsenal/web/piano.js` and several modules). |
| Coexists with | `research/in-flight/piano-jam-2026-09-14/jam-spec.md` (deck, glass, ghosts, Try), `research/in-flight/piano-spectacle-2026-09-13/spectacle-spec.md` (rarity banner borrows the Nashville row; harmonySet; bloom tracker), `research/in-flight/piano-suggest-lights-2026-09-14/chord-suggestions.md` (its proposed `readings.js`) |
| Privacy | Daniel's sessions (state/arsenal/performance, git-ignored) were replayed read only. This file holds only chord names, Nashville numbers, number sequences, counts and durations. Sessions are S1-S6 in start order. No clock times, no transcriptions. |

Daniel, on Discord from work (verbatim):

> "Do you think we can brush up our chord and scale detection to show things in an even better way? I love where its at now. But I am excited to see what is the next Gen level we can bring it to!"

---

## 0. In one screen

What changes for Daniel:

1. **His own chords get their real names.**
   - His most-held chord is the Lydian 4 with everything on it (`4maj13#11`). Today it reads `6m11/4`, a minor chord over the wrong root, or has no name at all. Next-gen names it right.
   - The same holds for `maj9#11`, `13sus4`, the dominant 11 with its 3rd, altered dominants and upper structures.
2. **Honest second names.**
   - When the notes really are two chords (`Bb11/Ab` or `Ab6/9#11`), the page names the likelier one and adds a small "also Bb11/Ab" line.
   - The engine's confidence is calibrated: its "clear" readings agree with the offline engine 95% of the time.
3. **Steadier, pedal-aware reading.**
   - A live harmonic window (onsets, bass notes, pedal lifts) replaces "name everything sounding".
   - Arpeggios under the pedal read as one chord.
   - A walking bass under a held chord reads as slash chords of that chord.
4. **A scale line.** `in Eb major · Ab Lydian`: the scale that fits the chord and what he plays over it. It covers the major modes, the melodic and harmonic minor modes, pentatonics and blues, with hysteresis.
5. **Function words instead of "outside".** `5 of 6m`, `backdoor 5`, `from Db major` (the old key at a key change), `borrowed from Eb minor`.

Headline numbers (method in section 1):

| Measure | Page today | Next-gen prototype |
|---|---|---|
| Synthetic fixtures named right (71 with an expected name) | 56 (51 exact) | **71 (67 exact)** |
| of which: plain vocabulary (32), must not regress | 32 | **32** |
| of which: Daniel's vocabulary (24) | 18 | **24** |
| of which: dominants and alterations (10) | 4 | **10** |
| of which: rootless, quartal, polychord voicings (5) | 2 | **5** |
| Real windows whose name matches the offline reading (983 windows, 2,110 s) | 627 (64%) | **730 (74%)** |
| Real windows the page leaves unnamed (145) | 145 | **41** (104 named) |
| Live replay, time with the right root and quality (six-session mean, 120 ms settle) | 0.497 | **0.616** |
| Live replay, time with no name | 25.1% | **13.3%** |
| Label changes per minute | 60 | 60 at 120 ms, **49 at 250 ms** (the recommended settle) |
| Backdoor progression C C7 F Bb7 C | F major | **C major** (patched tracker, 2,872/2,872 node tests pass) |
| Cost of one reading | 0.005-0.009 ms (detect) | 0.03-0.05 ms (6-8 notes) |

---

## 1. What was measured, and how

### 1.1 Prototype (scratch, reproducible)

All files are in `C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/theory-nextgen/`:

| File | What it is |
|---|---|
| `load.mjs` | Slices the page's THEORY block (as `arsenal/practice_theory.mjs` does) and imports `arsenal/web/piano/nashville.js` |
| `engine.mjs` | The next-gen reader: grammar, cost model, ranked readings, tags, confidence |
| `fixtures.mjs` | 73 synthetic voicings (71 with an expected name, 2 tag-only); page vs next-gen; `--md` writes `fixtures-table.md` |
| `gaps.mjs`, `real.mjs` | Every offline window of S1-S6 through page and next-gen; the key-change, secondary-dominant, dominant-11 and scale counts; before/after moments |
| `replay.mjs` | Live replay of all six sessions' `events.jsonl` through three label pipelines, scored against the offline windows |
| `scales.mjs` | Chord-scale ranker, scale hysteresis, tonal-centre detector |
| `tracker.mjs`, `tracker-compare.mjs` | Key tracker harness (page model: `pcHistory` decays over 12 s, 0.5 + vel/127 per note-on, 10 Hz ticks, chords comped on every beat) |
| `nashville-ng.mjs`, `nashville-ng2.mjs` | Patched copies of `nashville.js` (backdoor cadence; scale-fit variant) |
| `nashville_ng*.test.mjs` | `tests/nashville_js.test.mjs` pointed at those copies |
| `bench.mjs` | Timing and confidence calibration |
| `offline/S1..S6.json` | `py -m arsenal.practice analyze <session> --json`, read only |

### 1.2 Reference data

- **Synthetic fixtures.** The expected names come from lead-sheet convention and the jam deck's cards (jam-spec 12.1-12.6), not from either engine. Each fixture has an expected name and the alternatives that also count as right.
- **Real windows.** The offline engine (`arsenal/practice.py`) sees each session in both directions. It segments harmonic windows by dynamic programming and names each window's notes (`detect_notes`), with its reading rules on top of the page's namer.
  - Both engines were asked to name exactly the notes the offline window handed the page's namer.
  - The offline reading is a reference, not ground truth: next-gen borrowed some of its intuitions (a reading rooted on the held bass), so agreement is partly by construction. The fixtures are the independent check.
- **Live replay.** Each session's notes (on, off, sound_end, pedal) were replayed in time. Three pipelines produce a label timeline:
  - **A, page now:** `Theory.detect` over everything sounding (held and pedal-held notes).
  - **B, harmonySet:** spectacle P1's set (held notes, pedal-held notes within 1.5 s of onset, plus the lowest pedal-held note), through `Theory.detect`.
  - **C, next-gen:** causal live harmonic windows named by `engine.mjs` (section 7).

  Each timeline was scored against the offline windows:

  | Metric | Definition |
  |---|---|
  | exact | root, suffix and bass pitch class all equal |
  | core | root pitch class and quality family equal (major, minor, dominant, sus, dim, half-dim, aug) |
  | unnamed | time with no chord name |
  | changes per minute | label changes per minute of played window time |
  | latency | median time from a window's start to the first matching live label, over windows of 1 s or more |

  The key comes from the offline area key in all three pipelines, so chord reading is measured apart from key tracking.
- **Key tracker.** 14 scripted progressions through the harness, plus the full `tests/nashville_js.test.mjs` suite (2,872 checks) against each patched copy.

---

## 2. Today's engine, and the anatomy of its misses

`arsenal/web/piano.js` THEORY block (lines 22-268):
- 38 fixed templates (lines 77-115).
- `matchSet` tries only sounding notes as roots (124-140), so there are no rootless readings.
- The bass costs one of two amounts: +0.6 if it is the chord's 3rd, 5th or 7th, +1.5 otherwise (134).
- A foreign bass under a simple upper chord adds +1.7 (195-200).
- Every sounding note weighs the same, pedal-held or not (`currentInfo`, 1928-1938).
- It returns one name, with no alternatives, no confidence and no scale.

The offline twin (`arsenal/practice.py`) adds bass-aware extended readings (`extended_readings` 1424, `choose_reading` 1475), but not live.

What the fixtures and the real windows show, grouped by cause:

| Cause | Examples (page reading, with the right name) | Where it bites |
|---|---|---|
| Missing names get reinterpreted as a minor chord over its 3rd or 6th | `Cm9/Ab` for Abmaj9#11; `Cm11/Ab` for Abmaj13#11; `Bbm11/Gb` for Gbmaj13#11; `Dm9/G` and `Fmaj7/G` for G13sus4; `Abmaj7/Bb` for Bb13sus4 | His signature Lydian 4 and suspended 5 |
| No name at all | 145 real windows. The largest are all `4maj13#11` and `4maj9#11`, in Db, Eb, F#, Ab, F and D | 2 of the 6 moments in 6.4 open with it |
| Altered dominants and upper structures | `C E Bb D Gb A` for C13#11; `Emaj7#11/C` for C7#9b13; `F#7/C` for C7b9#11; `Adim/B` for B7b9; `G B F C D` for G7(11) | Dominant with its 3rd (his growth edge, chord-suggestions 1.2) |
| Quartal | `A9sus4/E` for the So What voicing (Em7(11)) | |
| The offline twin forbids the 11 over a major 3rd with a 7th (`practice.py` 1457) | Its reading list for `Bb2 F3 Ab3 C4 D4 Eb4` has no Bb11 at all (it offers Ab6/9(#11)/Bb) | 2 real moments (3.1 s) read as a Lydian 4 over the 5 in the bass |
| Temporal | Pedal blends two chords; harmonySet ages arpeggio notes out (replay B is worse than A: section 7.3) | Every pedalled bar |

---

## 3. The chord grammar (replaces the template list)

A reading is **root + base + tensions + omissions + bass**. The grammar generates every lead-sheet name; nothing is hand-listed per chord.

### 3.1 Bases

| Base | Tones (semitones) | Cost | Family | Allowed tensions | Omissions |
|---|---|---|---|---|---|
| (major) | 0 4 7 | 0.0 | maj | 9, 11, #11 | 3rd (+1.4, only over its root with its 5th) |
| m | 0 3 7 | 0.1 | min | 9, 11, b13 | |
| dim | 0 3 6 | 1.0 | dim | | |
| aug | 0 4 8 | 1.2 | aug | 9, #11 | |
| sus4 | 0 5 7 | 1.5 | sus | 9 | |
| sus2 | 0 2 7 | 1.6 | sus | #11, 13 | |
| 7 | 0 4 7 10 | 0.9 | dom | b9 9 #9 11 #11 b13 13 | 5th (+0.3), 3rd (+1.1), root (+1.3, rootless) |
| maj7 | 0 4 7 11 | 0.9 | maj | 9, 11, #11, 13 | 5th, 3rd (+0.8), root |
| m7 | 0 3 7 10 | 0.9 | min | 9, 11, b13, 13 | 5th, root |
| m7b5 | 0 3 6 10 | 1.3 | hdim | 9, 11, b13 | root |
| dim7 | 0 3 6 9 | 1.4 | dim | 9, 11, b13, maj7 | |
| 6 | 0 4 7 9 | 1.2 | maj | 9, #11 | 5th |
| m6 | 0 3 7 9 | 1.4 | min | 9, 11 | 5th |
| m(maj7) | 0 3 7 11 | 1.7 | min | 9, 11, 13 | 5th |
| 7sus4 | 0 5 7 10 | 1.3 | sus | b9, 9, 13 | 5th |
| 7#5 / maj7#5 / 7b5 | | 1.9 / 2.1 / 2.1 | dom / aug / dom | few | |

### 3.2 Naming rules (the lead-sheet way)

- **Stacking.** 7 + 9 is `9`; + 13 is `13`; 9 + 11 with the 3rd present is `11`, the dominant 11 with its 3rd. Without the 9 it is `7(11)`.
- **maj7 and m7.** maj7 + 9 is `maj9`, + 13 is `maj13`. m7 + 9 + 11 is `m11`; without the 9 it is `m7(11)`. m7 + 13 is `m13`.
- **7sus4.** + 9 is `9sus4`; + 13 is **`13sus4`**.
- **Altered tensions** follow the stacked name: `maj9#11`, **`maj13#11`**, `13#11`, `13b9`, `7#9b13`, `7b9#11`, `6/9#11`. Natural leftovers go in brackets: `13(11)`, `m13(11)`.
- **Triads with added tones.** `add9`, `add9(#11)`, `m(add9)`, `m(add11)`, `sus2(#11)`, `sus4(9)`.
- **Marks.** `(no3)` is shown. A missing 5th is a reason, not part of the name.

### 3.3 One source for every consumer

`nashville.js` keeps hand tables: `FAMILY` (232), `TONE_STEPS` (210) and `DOMINANT` (427). The Python twin `arsenal/nashville.py` does the same. Every new suffix would need three table edits in two languages.

Proposal: a suffix parser in both twins derives tones, letter steps, family and "dominant" from the suffix string. The node and Python tests then check it against THEORY's own readings for every fixture. This is the same twin-and-test pattern `nashville_cases.json` already uses.

---

## 4. Ranked readings: the cost model

### 4.1 Search

For every one of the 12 roots, including roots that are not sounding, and every base, a reading is valid when:
- every base tone sounds or is an allowed omission;
- every other pitch class is an allowed tension;
- no tension clashes (b9 with 9, 9 with #9, b13 with 13, 11 with #11).

Three more paths run alongside:
- **Slash:** the chord above a bass that appears only as the lowest note, 4 or more pitch classes, +1.6.
- **Faint note:** a pitch class with salience under 0.35 may be dropped as passing, at +0.3 plus its salience.
- **Fallback:** if the grammar yields nothing, `Theory.detect`'s template reading is kept (for example `Fm(add9)/Ab` without its 5th), at its cost + 0.5.

### 4.2 Cost terms

| Term | Cost |
|---|---|
| Base | table 3.1 |
| Natural tension (9, 11, 13) | +0.35 each |
| Altered tension (b9, #9, #11, b13) | +0.45 each |
| b13 over a minor chord | +1.2 over a minor 7th, +1.4 over a minor triad, and never without its 5th (then it is a #5) |
| b13 over a half-diminished 7th | +0.7 |
| 11 over a major 3rd | dominant +0.45 (+0.2 when the 9 is present: the `11` chord); major triad +0.4; maj7 +0.9 |
| #11 or b13 as the only tension, 5th missing | +0.6 (C E Gb Bb stays C7b5) |
| Bass is the 3rd / 5th / 6th or 7th | +0.55 / +0.6 / +0.7 |
| Bass is a tension | +1.4 |
| Extended chord in inversion | +0.25 for each tension beyond the first |
| Bass is the 7th under altered tensions | +0.3 |
| Sus chord over its own 7th | +0.3 |
| 7(11) (no 9) over its own 7th | +0.35 |
| Root sounds faintly (salience under 0.3) and is not the bass | +0.3 |
| Every note in the shown key | -0.15 |
| Same root as the previous window | -0.1 (a lament bass under a held Bbm11 stays Bbm11/Ab) |

**Salience** is per pitch class: `min(1, 1.4 x heard share of the window) x (0.6 + 0.4 x velocity/127)`. In the replay the bass is the lowest note below middle C whose pitch class holds at least half the window.

### 4.3 Output shape

```js
{ readings: [ { root: 6, suffix: "maj13#11", bass: null, name: "Gbmaj13#11", cost: 2.2, p: 0.91,
                reasons: ["bass is the root", "#11: the Lydian colour", "every note in Db major"] },
              { name: "Ebm13(11)/Gb", cost: 2.95, ... }, ... ],
  band: "clear" | "leaning" | "ambiguous" | "none", margin: 0.75, confidence: 0.91,
  tags: [ { tag: "upper structure", triad: { root: 8, q: "" } } ] }
```

### 4.4 Confidence bands, calibrated on the real windows

- **clear:** margin of at least 0.5 to the runner-up, and cost at most 2.5.
- **leaning:** margin of at least 0.2, and cost at most 3.2.
- **ambiguous:** everything else.
- `p` is a softmax over the top six costs (temperature 0.3), multiplied by an absolute-fit term, so a lone reading that needs a lot of naming is not called sure.

| Band | Windows | Seconds | Top reading agrees with offline | Offline reading in the top 3 |
|---|---|---|---|---|
| clear | 627 | 1,473 | **0.95** | 0.99 |
| leaning | 122 | 285 | 0.69 | 0.95 |
| ambiguous | 95 | 184 | 0.56 | 0.91 |
| two pitch classes or fewer (detect keeps them) | 93 | 110 | n/a | n/a |

The bands mean what they say. An ambiguous reading is right about half the time, but the right name is in its top 3 nine times in ten. That is why the page should show the second name only for leaning or ambiguous chords.

### 4.5 Voicing tags (words for the "why", never the name)

| Tag | Rule | Fixtures |
|---|---|---|
| upper structure | a major or minor triad made of 2 or more of the chord's tensions, avoiding its root, 3rd and 7th | C13#11 shows "D triad over C7"; Abmaj13#11 shows the Bb triad (the Lydian II) |
| polychord | the voicing splits at its widest gap into two different triads with no shared pitch class | D over C (C6/9#11), F# over C (C7b9#11) |
| quartal | 3 or more stacked perfect 4ths covering all but one interval | So What (Em7(11)), D G C F |
| cluster | 3 or more adjacent notes a step or less apart | C D E F |

**Measured problem:** the cluster tag also fired on 9 of Daniel's 24 voicings (normal close 9-3-#11 spacings).
- Rule for the build: 4 adjacent notes, at least one of them a semitone apart, or 3 with two semitones.
- A chord with a clear reading never shows the cluster word.

---

## 5. Results: synthetic fixtures

73 voicings; 71 carry an expected name and 2 are tag-only. Full table: scratch `fixtures-table.md`.

| Group | Fixtures | Page right | Next-gen right |
|---|---|---|---|
| plain vocabulary | 32 | 32 | 32 |
| Daniel's vocabulary (jam deck cards, his most-held numbers) | 24 | 18 | 24 |
| dominants and alterations | 10 | 4 | 10 |
| rootless, quartal, polychord | 5 | 2 | 5 |
| **total** | **71** | **56 (51 exact)** | **71 (67 exact); expected name in top 3: 71** |
| voicing tags wanted | 6 | n/a | 6 |

Misses fixed:

| Notes (key) | Page | Next-gen (band) |
|---|---|---|
| Gb2 Db3 F3 Ab3 Bb3 C4 Eb4 (Db) | Bbm11/Gb | **Gbmaj13#11** (clear) |
| Ab2 Eb3 G3 Bb3 C4 D4 (Eb) | Cm9/Ab | **Abmaj9#11** (clear) |
| Ab2 Eb3 G3 Bb3 C4 Eb4 D5 F5 (Eb), blooming chord card | Cm11/Ab | **Abmaj13#11** (clear) |
| G2 D3 F3 A3 C4 E4 (C) | Dm9/G | **G13sus4** (clear) |
| Bb2 Ab3 C4 Eb4 G4 (Eb) | Abmaj7/Bb | **Bb13sus4** (ambiguous, Abmaj7/Bb second) |
| C3 G3 Bb3 Eb4 F4 (Bb) | F9sus4/C | **Cm7(11)** (clear) |
| C2 E3 Bb3 D4 F#4 A4 (F) | no name | **C13#11**, upper structure (clear) |
| C2 E3 Bb3 Eb4 Ab4 (F minor) | Emaj7#11/C | **C7#9b13** (leaning) |
| G2 B2 F3 C4 D4 (C) | no name | **G7(11)**, the dominant 11 with its 3rd (clear) |
| B2 D#3 A3 C4 (E minor) | Adim/B | **B7b9** (clear) |
| E2 A2 D3 G3 B3 (D) | A9sus4/E | **Em7(11)**, quartal (clear) |
| C3 E3 G3 F#4 A#4 C#5 (C) | F#7b9/C | **C7b9#11**, polychord (clear) |

Honest ambiguities kept:
- **Ab2 Eb3 C4 D4 F4 Bb4.** The gospel 5 over 4: next-gen says `Ab6/9#11` with `Bb11/Ab` in its top 3; the page says `Bb11/Ab`. The notes are both chords; what comes next decides (section 9.9).
- **Ab2 F3 Eb4 G4 C5.** Next-gen reads `Abmaj13` with `Fm9/Ab` second; after F9/A (the half-step slide card) the continuity prior still leans Abmaj13. Both are right.

---

## 6. Results: Daniel's real windows (static, same notes)

### 6.1 Agreement

983 offline chord windows from S1-S6, 2,110 s, each with 3 or more notes, a key and an offline name.

| | Page | Next-gen |
|---|---|---|
| Same name as the offline reading | 627 | **730** |
| Same root and quality | 629 | **741** |
| Unnamed | 145 | 41 |

Where the two disagree with each other: 352 windows, 836 s.

### 6.2 Both directions

850 windows with a root and 3 or more pitch classes.

| | Windows | Seconds |
|---|---|---|
| Both right | 542 | |
| Next-gen right, page wrong | **188** | **568.4** |
| Page right, next-gen wrong | 63 | 106.8 |
| Both wrong | 57 | |

### 6.3 The largest gains and losses

Gains, by seconds summed across sessions (page number, then next-gen, then offline):

| Seconds | Sessions | Page | Next-gen | Offline |
|---|---|---|---|---|
| 26.3 | S3 | no name | 4maj13#11 | 4maj13#11 |
| 25.7 | S4 | no name | 4maj13#11 | 4maj13#11 |
| 20.9 | S5, S6 | no name | 4maj13#11 | 4maj13#11 |
| 16.5 | S5, S6 | no name | 4maj13#11 (no 3rd) | 4maj13#11 |
| 15.4 | S3 | 2m11/4 | 4maj13 (no 3rd) | 4maj13 |
| 15.1 | S1 | 5^7sus4/1 | 1sus4(9) | 1sus4(9) |
| 12.6 | S4 | 6m11/4 | 4maj13#11 | 4maj13#11 |
| 12.5 | S4 | no name | 4maj9#11 | 4maj9#11 |
| 11.7 | S3, S5 | 2^9sus4/6 | 6m7(11) | 6m7(11) |
| 11.1 | S3 | no name | 4maj9#11 | 4maj9#11 |

Losses (page right, next-gen wrong):

| Seconds | Page, offline agrees | Next-gen (band) |
|---|---|---|
| 5.8 | 2m13/4 | 4maj13#11 (no 3rd) (ambiguous) |
| 5.7 | 2m11/6 | 6m7b13(11) (ambiguous) |
| 4.8 | 2m13/4 | 4maj13#11 (clear) |
| 4.4 | 1^6/9/5 | 6m7(11)/5 (ambiguous) |
| 3.8 | 2m11/6 | 4maj13/6 (ambiguous) |
| 3.6 | 2m11/3 | 1add9(11)/3 (clear) |
| 3.2 | 1^6/9/3 | 6m7(11)/3 (leaning) |
| 3.1 | 5^13/2 | 2m6/9(11) (leaning) |

The losses are the mirror image of the gains: 2m-over-4 against 4maj13#11 on the same notes, a 6/9 in inversion against a minor 7(11).
- Two are clear-band errors: 4.8 s and 3.6 s.
- The rest are leaning or ambiguous, so the "also" line would show the page's name beside them.
- The receipt for the build (section 12) holds both directions: gains at or above 188 windows, losses at or below 63.

### 6.4 Before and after on real moments

For each session, the six consecutive windows in one key where the two engines disagree most. Numbers only; the scale line is next-gen's (section 8).

| | Sequence |
|---|---|
| **S1 in Eb major** | |
| page | 1add9/4 · (no name) · 5^11/4 · 5add9/2 · (no name) · 5^7sus4/1 |
| next-gen | 1add9/4 · 4sus2(#11) · 4add9(#11) · 5add9/2 · 1maj7(no3) · 1sus4(9) |
| offline | 4maj13 · 4sus2(#11) · 4add9(#11) · 5add9/2 · 1maj7 · 1sus4(9) |
| scale | Ab Lydian · Ab Lydian · Ab Lydian · Bb Mixolydian · Eb Ionian · Eb Ionian |
| **S2 in Eb major** | |
| page | 2m9/6 · 6^7sus4/5 · 5^6/9 · (no name) · (no name) · (no name) |
| next-gen | 4maj13/6 · 5sus2(13) · 5^6/9 · 2m13(11) · 4maj9#11(no3) · 1maj7(no3) |
| offline | 2m9/6 · 5sus2(13) · 5^6/9 · 2m13(11) · 4maj9#11 · 1maj7 |
| **S3 in Eb major** | |
| page | (no name) · 2^9sus4/6 · 2m11/4 · 2m(add9)/5 · (no name) · (no name) |
| next-gen | 6^7(no3) · 6m7(11) · 4maj13(no3) · 5^13(no3) · 5^13(11) · 6^7(no3) |
| offline | 6^7 · 6m7(11) · 4maj13 · 5^13 · 2m13(11)/5 · 6^7 |
| **S4 in Db major** | |
| page | (no name) · (no name) · 4maj7#11 · 2m13/4 · 5^11/4 · (no name) |
| next-gen | 4maj13#11 · (no name) · 4maj7#11 · 4maj13#11 · 4^6/9#11 · 4maj13#11 |
| offline | 4maj13#11 · 4add#11 · 4maj7#11 · 2m13/4 · 4^6/9(#11) · 4maj13#11 |
| scale | Gb Lydian throughout, Eb Dorian on the 2m13/4 reading |
| **S5 in F# major** | |
| page | 2^9sus4/6 · 1maj9/3 · 2m · 2m11/4 · (no name) · 5^6/9/6 |
| next-gen | 6m7(11) · 1maj9/3 · 2m · 4maj13(no3) · 4maj9#11/6 · 3m(add11)/6 |
| offline | 6m7(11) · 1maj9/3 · 2m · 4maj13 · 6m9b13 · 6^9 |
| **S6 in G major** | |
| page | b6maj7#11 · 6m7 · 2^9sus4/6 · 2m11/6 · b3^6/9 · 5^7sus4/2 |
| next-gen | b6maj7#11 · 6m7 · 6m7(11) · 6m7b13(11) · 1m(add11)/b3 · 2m7(11) |
| offline | b6maj7#11 · 6m7 · 6m7(11) · 2m11/6 · b3^6/9 · 5^7sus4/2 |

S1-S4 read clearly better. S5 and S6 end on windows where next-gen and the page both disagree with the offline engine, or next-gen is worse (the 6m7b13(11) and 1m(add11)/b3 readings). Those two shapes are the b13-over-minor and minor-over-its-3rd cases to tune next.

**Prototype bug:** scale roots are spelled without the key ("A# Lydian" for Bb in G major); the build spells them with `spellInKey`.

---

## 7. Temporal harmony, live (the offline windows brought to the page)

### 7.1 The live harmonic window (prototype `replay.mjs` `pipelineLive`)

| Step | Rule | Offline twin (`practice.py`) |
|---|---|---|
| Onset groups | note-ons within 50 ms are one attack | `ONSET_GROUP_MS` |
| Heard extension | a note counts as heard for at least 700 ms after its onset (grace notes under 100 ms excepted), so a broken chord is one chord | `HEARD_MIN_MS`, `GRACE_MS` |
| Silence | at least 700 ms with nothing heard always starts a new window | `SILENCE_SPLIT_MS` |
| New bass | a new lowest note below middle C, with a different pitch class, starts a window at once | "a bass moving to a new root counts as a real change" |
| Lagged split test | 400 ms and 900 ms after each attack (causal), compare the misfit of one window against the split plus 600 ms of penalty, halved when the pedal lifts from 200 ms before to 400 ms after the attack; misfit is the pitch-class-ms heard while left out, or missing while kept in | `harmonic_windows` dynamic programming, `WINDOW_PENALTY_MS`, `PEDAL_DISCOUNT`, `PEDAL_NEAR_MS` |
| Chord set | pitch classes heard for 20% or more of the window, with salience (section 4.2) | `CHORD_SHARE` 0.5 offline (live keeps lighter tones and lets the reader drop faint ones) |
| Naming | at 10 Hz while the window grows; memoised on the salience-bucketed input | one node call per session |
| Continuity | the previous window's root is the reader's prior | `resolve_over_third`, `merge_same` |

### 7.2 What it gives the page

- **Pedal-aware.** A pedal ringing the old chord under a new bass never blends: the new bass opens a new window.
- **Arpeggio-aware.** An arpeggio stays one window.
- **Lament bass.** A walking bass under held hands gives `6m11 · 6m11/5 · 6m11/4 · ...` and, over the 4, the Lydian 4.
- **One window, many consumers.** The window is the unit the spectacle's bloom tracker (spectacle 4.2), the rarity scorer and the suggestion engine's "held chord" (chord-suggestions 2.1) each re-derive today.

### 7.3 Replay results (six sessions, means)

| Pipeline | Settle | Core | Exact | Unnamed | Changes per minute | Median latency |
|---|---|---|---|---|---|---|
| A page now | 120 ms | 0.497 | 0.378 | 25.1% | 60 | 583 ms |
| A page now | 250 ms | 0.469 | 0.351 | 25.1% | 47 | 958 ms |
| A page now | 400 ms | 0.434 | 0.314 | 25.1% | 37 | 1,158 ms |
| B harmonySet (spectacle P1) | 120 ms | 0.444 | 0.259 | 26.6% | 81.5 | 392 ms |
| C next-gen | 120 ms | **0.616** | 0.407 | **13.3%** | 60 | **458 ms** |
| **C next-gen** | **250 ms** | **0.577** | 0.373 | **13.4%** | **49** | 625 ms |
| C next-gen | 400 ms | 0.532 | 0.336 | 13.4% | 40 | 842 ms |

Per session, core agreement, A at 120 ms against C at 120 ms (C is higher in all six):

| | S1 | S2 | S3 | S4 | S5 | S6 |
|---|---|---|---|---|---|---|
| A 120 ms | .391 | .547 | .532 | .532 | .505 | .474 |
| C 120 ms | **.507** | **.652** | **.699** | **.708** | **.555** | **.571** |

Exact agreement is lower in S2 (.411 to .408) and S5 (.393 to .359), where the grammar's names differ from the offline engine's spelling of the same chord.

Decisions from the numbers:
1. **Settle 250 ms.**
   - Next-gen at 250 ms beats today's page at 120 ms on agreement (0.577 against 0.497), unnamed time (13.4% against 25.1%) and flicker (49 against 60 changes per minute).
   - It costs 42 ms of median latency.
2. **Do not name the label from harmonySet.** On these sessions it is worse than today on every measure except latency, and flickers most (81.5 changes per minute). Keep it for visuals that want recency.
3. **Hysteresis belongs at the window, not at the reading.**
   - A sticky variant (keep the shown reading while it is within 0.35 cost of the best) changed core agreement by 0.01 at most and changes per minute by 1.3 at most.
   - Label flicker comes from notes arriving, so the settle and the window boundaries are the controls.

---

## 8. Scale and mode detection

### 8.1 Chord-scale ranker (`scales.mjs`)

28 scales on the chord's root:
- the 7 major modes;
- the 7 melodic minor modes (melodic minor, Dorian b2, Lydian augmented, Lydian dominant, Mixolydian b6, Locrian #2, altered);
- the 7 harmonic minor modes;
- major and minor pentatonic, blues (minor), blues over a dominant (b3 and b5 against its own 3rd);
- whole tone and both diminished scales.

Score, lowest wins:

| Term | Cost |
|---|---|
| Family prior | major modes 0 (Phrygian, Locrian 0.1); melodic minor 0.35-0.5; harmonic minor 0.4-0.7; pentatonics 0.25; blues 0.35; symmetric 0.6 |
| Chord tone outside the scale | +5 (effectively a hard rule) |
| Melody or passing pitch class outside the scale | +4 x min(1, 2 x its heard share) |
| Key prior | +0.35 per scale tone outside the shown key's scale; this decides tones nobody played (Abmaj9 in Eb is Lydian because D is in Eb) |
| Pentatonic with fewer than 3 melody pitch classes | +0.6 |
| Symmetric scale over fewer than 5 chord tones | +0.3 |

Hysteresis:
- A new chord that the shown scale cannot hold switches at once.
- Within the same root, a challenger must beat the shown scale by 0.35 for 1.5 s of playing.

### 8.2 Measured

- **Synthetic cases: 11/11.**

  | Chord | Scale |
  |---|---|
  | Abmaj13#11 in Eb | Lydian |
  | Abmaj9 in Eb, no 4th heard | Lydian |
  | Cmaj9 in C | Ionian |
  | Dm7 in C | Dorian |
  | Am7 with an F melody | Aeolian |
  | G7 | Mixolydian |
  | C7#11 | Lydian dominant |
  | G7#9b13 into Cm | altered |
  | E7b9 in A minor | Phrygian dominant |
  | C7 with Eb Gb melody | blues |
  | Cm7 with a pentatonic melody, in Bb | Dorian |

- **Real windows** (850 windows, 32.5 minutes):
  - Seconds by scale: Lydian 656, Ionian 434, Aeolian 363, Mixolydian 237, Dorian 176, Phrygian 51. Everything else is under 7 s each (harmonic minor, Lydian #2, Phrygian dominant, Locrian, Lydian dominant, melodic minor, blues, Mixolydian b6, altered).
  - **92% of chord time is a mode of the area's key.** The line says which mode, and it is steady.
  - Of 199 back-to-back windows on the same root, the raw ranker flips scale 19 times; **with hysteresis, 3 times.**
- **Caveat.** Much of the Lydian time is his 4 chord with the key deciding the #11. The line must mark implied tones:
  - "Ab Lydian" when D sounds;
  - "Ab Lydian (from Eb major)" in lighter ink when D is only implied.

  The build receipt counts both.

### 8.3 Tonal centre (the mode a vamp lives in)

`centreOf(chords, key)`, inside one key area:
1. Weigh chord time.
2. Add +0.15 to the chord that starts a repeating 2-4 chord cycle.
3. The centre is the top chord, when all of these hold:
   - it is not the key's tonic;
   - it holds at least 40% of the time and at least 1.5 times the tonic chord's;
   - its quality fits its mode (minor for Dorian, Aeolian or Phrygian; major or dominant for Lydian or Mixolydian);
   - the area has at least 20 s of chords;
   - for Lydian: a share of 50% or more and the tonic under 10%, because his 4 leans home.

| Case | Centre |
|---|---|
| Dm7 G7 vamp in C major | **D Dorian** (share 0.82) |
| Am7 D vamp in G major | **A Dorian** (0.65) |
| Am F C G in C major | **A Aeolian** (0.40 against tonic 0.25) |
| 6m 4 1 5 with a long 6m in Eb | **C Aeolian** (0.62) |
| His 1maj9 4maj13#11 loop in Db, starting on 1 or on 4 | none (stays Db major) |
| Real key areas, S1-S6 | **0 of 23** fire |

Before the guards, 2 real areas fired: a 9 s area read as Locrian, and an F# major area heavy on the 4 read as B Lydian. Both were wrong for his ear; the guards remove them.

---

## 9. Function labels and every known gap

### 9.0 Summary

| # | Gap | Cause | Fix | Before, then after | Status |
|---|---|---|---|---|---|
| 1 | No dominant-11 name offline | `practice.py` 1457 forbids 11 over a major 3rd with a 7th | grammar 3.2: `11` and `7(11)` with the 3rd, +0.45 (+0.2 with the 9) | 2 real moments: `5sus2(#11,13)/6`, then `6^7(11)`; `4sus2(#11,13)/5`, then `5^7(11)`. Fixture Bb11 exact. | prototyped |
| 2 | No maj9#11, maj13#11, 13sus4 on the page | fixed template list | grammar | Daniel's group 18/24, then 24/24. 104 of 145 unnamed real windows named. His top-held chord right. | prototyped |
| 3 | Borrowed labels on old-key chords at a key change | `classify` (`practice.py` 1680) judges each window only in its own area's key | pivot rule 9.3 | 9 key changes with no pause: 7 non-diatonic labels in the new key's first 8 s, **6 of them fit the old key** | measured, proposal |
| 4 | Dorian vamps numbered in the IV's key | Krumhansl-Kessler (KK) correlation cannot see modes | centre caption + parent from the vamp's notes (9.4) | harness: Dm7 G7 shows **F major** (6m7 2^7 outside), worse than reported; Am7 D/A shows A major (unsure). Centre detector: D Dorian and A Dorian. | measured, part prototyped |
| 5 | I-I7-IV with a long IV | dwell and histogram; no V evidence | dual-key display 9.5 | harness: with a later V it shows F at 15 s, C from 21 s, F again from 60 s; with no V, F (sure). Unchanged by the patch. | measured, proposal |
| 6 | Backdoor dominant (C C7 F Bb7 C) reads F major | `hear()` credits the I7's arrival when Bb7 fits F major and not C (`nashville.js` 562-564) | 9.6 patch | F major (fair), then **C major (sure)**. 2,872/2,872 tests. The other 13 scenarios unchanged. | prototyped |
| 7 | Secondary dominants labelled only "chromatic" | `performance.py` summary knows only borrowed and chromatic (1101, 1573, 1869); the page caption says "outside" | shared function labeller 9.7 | offline `practice.py` already finds 13; the summary and the live caption cannot say it | proposal |
| 8 | Aeolian loops shown as the relative major, by design | design | numbers kept; centre caption "A Aeolian" (8.3) | Am F C G: 6m 4 1 5 in C major, then the same numbers plus "A Aeolian" | prototyped |
| 9 | New: C E7 Am F reads A minor (sure) | leading tone from E7, home-chord rule off | open, for the tracker owner | A minor in both the page and the patch | measured |
| 10 | New: gospel 5 over 4 against Lydian 4 on the same notes | the notes allow both | context rule 9.9 | fixture: Ab6/9#11 first, Bb11/Ab second | proposal |

### 9.1 Dominant 11

The page's templates already name `Bb11` (with its 3rd). The offline engine cannot:
- its reading list for `Bb2 F3 Ab3 C4 D4 Eb4` does not contain Bb11;
- over an Ab bass it falls to a Lydian 4 reading.

Next-gen's grammar permits the 11 over the 3rd with a cost, so `Bb11`, `G7(11)` and `Bb11/Ab` all exist and rank. `practice.py` adopts the engine (section 12, phase N6) instead of patching line 1457 alone.

### 9.2 maj9#11, maj13#11, 13sus4 (and the rest of his colour)

These fall out of the grammar. The page effects that key off names must learn them together:
- the rarity table (spectacle V2-F);
- the Nashville fixtures;
- the Python twin.

The jam spec already scheduled that (jam-spec C19, V2-F).

### 9.3 Old-key chords at a key change (pivot)

The 9 key changes with no pause, as number sequences. "(old)" marks a window before the change; brackets give the label the new key gave it, and its number in the old key.

| Session | Change | Windows |
|---|---|---|
| S1 | Eb major to Eb minor | 7 · b3 · 1-2 · 1m11 · 1 · 1-b3 · 4 |
| S1 | Eb minor to Eb major | (old) 1m · 1-2 · 1maj9 · 1maj7 · 4-b6 [borrowed; fits the old key as 4-b6] · 1 |
| S1 | Eb major to Eb minor | (old) 1-3 · b2-1 [modal] · 5-1 · 4m · b6/b3 · 1^5 |
| S2 | Bb major to Eb major | (old) 5add9 · 2m(add9,11) · 2m9/4 · 4maj13#11 · 6m(add9,11) |
| S3 | F# major to Eb major | (old) 2m9/4 · b3^6/9/5 [borrowed; old 1^6/9/3] · 1maj7 · 1add11/3 · 4m9 [borrowed; old 2m9] |
| S3 | F major to D major | (old) 4maj13 · b7^6 [borrowed; old 5^6] · 1add9 · 1 |
| S3 | F# major to Eb major | (old) 4maj7 · b3add9/b7 [borrowed; old 1add9/5] · 1add11 · 2m13(11)/1 |
| S5 | F# major to Ab major | (old) 3m7/5 · b7maj9/4 [modal; old 1maj9/5] · 6m11 · 6^5 |
| S6 | Ab major to G major | 4maj7 · 4maj7 · 5sus4 · 2^7sus4/6 · 1add11/4 · 5sus4 |

**Rule.** From the start of a new key area until its tonic chord has sounded for 1.5 s, or 8 s have passed, a chord that is diatonic in the previous area's key is labelled `from <old key>` and numbered in both keys ("b3^6/9/5 · was 1^6/9/3").
- Live, the same rule applies to the tracker's switch moment.
- This is the hinge the suggestion design already learns from (chord-suggestions 1.3). The label and the suggestion engine should share one hinge detector.

### 9.4 Dorian vamps

The tracker's numbers are wrong twice:
- **wrong parent key:** F major instead of C major for Dm7 G7, because F dominates the notes and G7's B is light;
- **not the centre:** the ear hears D.

A scale-fit term in `rankKeys` (score minus FIT_W times the share outside the key's scale) was tried and **rejected**:
- FIT_W 0.3 fails 5 existing tests; 0.6 fails 18;
- the failures are the D C G D Mixolydian cases, a comped C blues, and C D7 G G7 C C;
- neither vamp was fixed.

Proposal:
1. **Vamp parent from its own notes.** When a cycle of 2-4 chords repeats (the same cycle detection as `centreOf`), take the union of its chord pitch classes.
   - If exactly one major scale holds that union, offer that key to the tracker as a loop candidate, with the normal hold rules.
   - Dm7 G7 gives {C D F G A B}: C major only. Am7 D/A gives {A C D E F# G}: G major only.
   - D C G D gives {D F# A C E G B}: G major only. That is the Mixolydian case the tests keep in D major, so the candidate must lose to the tracker's own home-chord and cadence evidence. The receipt is the existing suite passing.
2. **Centre caption plus an option.**
   - The row reads `in C major · D Dorian`.
   - A setting, Numbers: from the key (default) or from the centre, numbers `1m7 4^7 in D Dorian` (minor-tonic numbering with the natural 6 flagged diatonic).

### 9.5 I-I7-IV with a long IV

Honestly ambiguous: C C7 F-F-F is V V7 I in F as much as I I7 IV in C.
- Harness result: F at 15 s, C from 21 s, then F again from 60 s while the IV holds 12 beats. With no V at all, F (sure).
- The patch does not change it, and a loop-start prior would fight Daniel's habit of starting loops on his 4 (chord-suggestions 1.1: after a 4, the 1 follows 45 times).

**Proposal: say both.** While an I7-shaped arrival is undecided (`pending` in `hear()`) and the two ranked keys are a fifth apart within the margin:
- the key caption reads `in C or F major`;
- the number shows both, the second smaller (`1^7 · 5^7`).

This is the existing "unsure because the runner-up is a fifth away" state (`nashville.js` 725-735) made visible, not a new guess.

**Next experiment (not run).** Chord-level fit rather than note-level: seconds of chords outside the shown key, against the challenger. G after the long F is outside F major. The D C G D tests are the guard.

### 9.6 Backdoor dominants (patch, measured)

Two changes to `hear()`, in scratch `nashville-ng.mjs`:
1. **Backdoor cadence.** A dominant seventh followed within `CAD_WINDOW` by a major chord a whole step up (Bb7 to C) is an arrival, credited to that key like V7 to I once it holds `CAD_SETTLE`.
2. **A dominant heading home decides nothing yet.**
   - While an I7's arrival is pending, a dominant whose resolution (a fifth down or a whole step up) is the I7's root waits for where it lands.
   - Landing on that root makes the arrival colour.
   - The dwell rule (C D7 G G7 C C) is checked first, so it still credits C.

Scenario results:

| Scenario | Want | Page tracker | Patched |
|---|---|---|---|
| C C7 F Bb7 C | C major | F major, numbers 5 5^7 1 4^7 5 (fair) | **C major, 1 1^7 4 b7^7 1 (sure)** |
| Fm7 Bb7 Cmaj7 (backdoor ii-V) | C major | C major | C major |
| C D7 G G7 C C | C major | C major | C major |
| F blues (F7 Bb7 C7) | F major | F major (sure) | F major (sure) |
| ii V I, F/A C/G Dm Bbmaj7, gospel 5 over 4 loop, Daniel's Db loop, Aeolian loop | as named | right | right |
| Node suite (`tests/nashville_js.test.mjs`, 2,872 checks) | | 2,872 pass | **2,872 pass** |

The Python twin `performance.numbering_key` needs the same two rules, plus a shared scenario in the fixtures.

### 9.7 One function labeller for page, summary and practice

A pure `function.js` with a Python twin returns, for a chord in context (previous and next windows, area, previous area):

| Label | Rule | Row words |
|---|---|---|
| diatonic | in the key (a minor key includes its harmonic and melodic 6 and 7) | `in Eb major` |
| secondary dominant | major 3rd plus b7 on a root a 5th above a diatonic target, or a major triad there that lands on the target | `5 of 6m` (`5 of 6m, lands`) |
| backdoor | dominant 7 on b7 resolving to I, or iv to bVII7 to I | `backdoor 5` |
| tritone substitute | dominant 7 a half step above its target, landing there | `sub 5 of 1` |
| passing diminished | #i°7 or #iv°7 stepping up to the chord a half step above | `passing` |
| from the old key | rule 9.3 | `from Db major` |
| borrowed | in the parallel key | `from Eb minor` |
| modal colour | Mixolydian, Lydian, Dorian or Phrygian in the key's tonic | `Mixolydian colour` |
| chromatic | none of these | `outside Eb major` (today's word, now only for real outsiders) |

Measured on the offline windows (all 1,196 windows including non-chords):

| Class | Windows |
|---|---|
| diatonic | 929 |
| note | 94 |
| broken chord | 68 |
| borrowed | 26 |
| modal | 19 |
| chromatic | 19 |
| line | 17 |
| secondary dominant | 13 |
| passing bass | 7 |
| bass line | 4 |

Only 2 of the 18 "chromatic" chord windows are even shaped like a dominant of a diatonic target, and both are add11 shapes, not real dominants. The fix is naming the function everywhere, not moving these windows. The summary (`performance.py`) and the live row are where "secondary dominant" is missing.

### 9.8 Aeolian by design

Unchanged numbers (Nashville charts number Am F C G from C). The centre caption adds `A Aeolian` when 8.3 fires. On real sessions it never did, so there is no added noise for Daniel today.

### 9.9 Gospel 5 over 4, or the Lydian 4

Same notes, two chords, decided by what follows. `Ab Eb C D F Bb` in Eb reads `Ab6/9#11` first and `Bb11/Ab` second.
- **Rule (live, after the fact; offline, in both directions):**
  - If the next window's bass steps down to the 3 (G) or the chord moves to 1/3, the held window is **5^11/4** (the gospel lean).
  - If the bass holds or goes back through 4 to 1, it stays **4^6/9#11**.
- **Live:** the label shows the reading first. When the next window confirms the other reading, the log and the practice summary take the confirmed one, and the label crossfades the name in place only if the window is still sounding.
- **Offline:** `_dominant_over_4` (`practice.py` 2321) covers the no-3rd case today; extend it to this one.

---

## 10. How it shows on the page (coexisting with the other designs)

| Place | Today | Next-gen | Constraint honoured |
|---|---|---|---|
| Big label (`drawLabel`, `LAYOUT.label`) | detect's one name | top reading, spelled in the shown key (`spellForKey`), committed on the window settle (250 ms) | label layer sacred (spectacle 5.6); cue notes never reach the engine (jam INT invariant 1) |
| Second line (note chips plus the `sub` caption) | "power chord", interval names | for leaning or ambiguous readings held 1 s or more: `also Bb11/Ab` | chips keep his pitch colours (jam C12); role marks never recolour a chip |
| Nashville row (`drawNumbers`, `LAYOUT.nns`) | `1maj9   in Eb major` or `outside Eb major` | `4maj13#11   in Eb major · Ab Lydian`; a function word replaces "outside" (`5 of 6m`, `backdoor 5`, `from Db major`); an implied scale in lighter ink; dual key when undecided (9.5) | the rarity banner borrows the row for 2-3 s and carries the number (spectacle D8, Daniel's decision); the scale and function words fade with the row |
| Staff | unchanged | unchanged | |
| HUD (DOM, never recorded) | key and raw key | the top 3 readings with reasons ("bass is the root; #11: the Lydian colour"), the band, the window's notes and salience, the scale runner-up | recordings stay clean |
| Try mode `found` (jam 8.4) | detect name equality | engine identity: root, family and bass; the "reads as" line uses the ranked list | |
| Chord suggestions | proposed its own `readings.js` twin of practice (chord-suggestions 2.2) | uses this engine's `readHeld` (the live window) | one engine, one reading |
| Rarity (spectacle 4.2) | commits on overlay name changes | the bloom is the harmony window; score its settled reading, upgrade in place as it grows | passing and upgrade rules unchanged |
| Practice log `chord` events | name, key, number | add `reading` (top 3 ids, costs), `band`, `scale`, `function`, `window` id | log schema lane: `performance.py` `KINDS` first, as spectacle P4 does |

---

## 11. Interfaces

```js
// THEORY block (pure; node-extracted by practice_theory.mjs, pianocue_voicing.mjs and the tests, so no imports)
Theory.read(notes /* [midi] | [{midi, w}] */, { key, prev /* {root} */, bassMidi, allowRootless = true })
  -> { readings: [{ root, suffix, bass, name, cost, p, reasons }], band, margin, confidence, tags }
Theory.detect(midiNotes, keyBias)  // unchanged signature and shape: the top reading mapped to {kind, root, suffix, bass,
                                   // name, sub, pcNames, notes, cost}, plus info.readings / info.band / info.tags
Theory.parseSuffix(suffix) -> { tones: {semis: letterSteps}, family, dominant }  // also in nashville.js and nashville.py

// arsenal/web/piano/harmony.js (pure): the live window
createHarmonyTracker({ settleMs = 250, heardMinMs = 700, groupMs = 50, silenceMs = 700, penaltyMs = 600 })
  -> { noteOn(m, vel, t), noteOff(m, t), soundEnd(m, t), pedal(down, t), tick(t, key)
       -> { window: { id, startT, pcs, salience, bassMidi }, reading, shown, changed, upgradeOf } }

// arsenal/web/piano/scales.js (pure)
rankScales(chordPcs, weights, root, keyName) -> [{ name, root, score, set, implied: [pc] }]
createScaleView({ margin = 0.35, holdMs = 1500 }) -> { update(ranked, t, sameWindow) }
centreOf(chords /* [{root, family, seconds}] */, keyName) -> { root, mode, share, tonicShare } | null

// arsenal/web/piano/function.js (pure) + arsenal/harmony_function.py (twin)
functionOf({ window, prev, next, area, prevArea }) -> { label, words, target? }
```

`Theory.read` lives in the THEORY block so the three extractors and the node tests keep working unchanged. The prototype engine is 263 lines.

---

## 12. Build order and receipts

The jam build owns `piano.js` now, so phases N0-N4 add new pure modules and fixtures only, and N5 waits for the jam waves to land.

| Phase | Work | Receipt (numbers from this study are the floor) |
|---|---|---|
| **N0** | `tests/fixtures/chord_readings_cases.json` (the 73 voicings, grown), engine as a pure module with node tests | 71/71 right, at least 67 exact; plain group 32/32; tags 6/6; cluster false positives on Daniel's group at or below 2 of 24 (from 9) |
| **N1** | `Theory.read` in THEORY; `Theory.detect` as its wrapper; `parseSuffix` in `nashville.js` and `nashville.py`; the Nashville fixtures gain the new suffixes | `tests/nashville_js.test.mjs` and `test_arsenal_nashville.py` pass; real-window static at or above 730/983, losses at or below 63, gains at or above 188; calibration: clear-band agreement at or above 0.93 |
| **N2** | `harmony.js` plus a read-only replay lane `arsenal/lanes/harmony_replay.mjs` (like spectacle's `rarity_replay.mjs`) | six-session means at 250 ms: core at or above 0.577, unnamed at or below 13.5%, changes per minute at or below 49, median latency at or below 650 ms, and every session's core above page-now's |
| **N3** | `scales.js`, `centreOf`, implied-tone marking | 11/11 scale cases; same-root flips at or below 3/199; vamps give D Dorian, A Dorian, A Aeolian; real areas at or below 1/23 firing; Daniel's loops never |
| **N4** | `function.js` plus the Python twin; tracker backdoor patch in both twins; pivot rule | 2,872/2,872 plus new backdoor and pivot scenarios; pivot: 6 of 7 old-key labels become `from <old key>`; secondary dominants named in the summary |
| **N5** | `piano.js` integration (label, second line, row, HUD, Try, rarity commit, log fields) | spectacle R7 layout (no collisions, byte-identical layers at k = 1 with detail Off); log schema route first |
| **N6** | `practice.py` naming through `Theory.read` (the bridge returns readings), retiring `extended_readings` and `choose_reading` behind the same verbs | `tests/test_arsenal_practice.py` green; `practice name` prints the engine's ranked list |

---

## 13. Risks and open questions

### 13.1 Risks

1. **Self-referential reference.** The offline engine is a design sibling. The 74% agreement flatters both, so the independent fixtures and Daniel's ear are the real judges.
2. **Name churn.** The page taught him `Bbm11/Gb` for his favourite chord, and next-gen says `Gbmaj13#11`. Mitigations:
   - the `also` line;
   - a one-time note in the practice brief ("same notes, clearer name");
   - question 1 below.
3. **Remaining losses.** 63 windows (107 s): 2m-over-4 against 4maj13#11 and 6/9 inversions, 2 of them in the clear band. The b13-over-minor and minor-over-its-3rd costs need one more tuning round, gated on both directions (N1 receipt).
4. **Implied scales.** The key prior names tones nobody played (much of the 656 s of Lydian). Mark implied tones, or the line will over-teach.
5. **The key tracker is the ceiling for numbers.** Dm7 G7 shows F major, and C E7 Am F shows A minor (sure). The engine cannot fix numbers in the wrong key. Sections 9.4 and 9.5 are proposals with named guards, not fixes.
6. **Latency.** +42 ms median against today at the recommended settle. The label commits at 250 ms, while visuals that want immediacy (trails, sparks) never waited for the label.
7. **Cost.** About 6 times detect per call (0.05 ms at 7 notes), still negligible at 10 Hz with memoisation.
8. **Ownership.** `piano.js` (jam build), the rarity names table (spectacle V2-F) and the suggestion `readings.js` must converge on this one engine. Sequence N5 after the jam waves and tell the suggestion design its `readings.js` is this module.
9. **Observation (harness).** A chord struck once and held under the pedal for a whole bar accrues only 1.5 s of tracker "playing time" per strike (`ACTIVE_SEC`). Slow held-chord playing gets a key late; with comping on each beat the vamps got one in 6-15 s.

### 13.2 Questions for Daniel (each with a default)

1. **Your favourite chord's name.** Full lead-sheet name on the big label (`Gbmaj13#11`), with the number `4maj13#11` beside it? Default: yes. The simpler `Gbmaj7#11` stays available as a "Names: simple" setting.
2. **Scale line in recordings.** Should `· Ab Lydian` appear in the recorded frame? Default: yes, small, and only when the colour note (the #11 here) actually sounds; implied scales stay on the HUD.
3. **Two names at once.** When the notes honestly are two chords (`Bb11/Ab` or `Ab6/9#11`), show the second as a small "also" line once the chord has held a second? Default: yes, never in the big label.

---

## Appendix: reproduce

```sh
cd C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/theory-nextgen
node fixtures.mjs            # page vs next-gen on the synthetic set (--md for the table)
node gaps.mjs && node real.mjs   # needs offline/S1..S6.json: py -m arsenal.practice analyze <session> --json (read only)
node replay.mjs              # live replay: A (page now) and C (next-gen) at 120/250/400 ms settles
node scales.mjs              # scale and centre cases
node tracker.mjs && NG=./nashville-ng.mjs node tracker-compare.mjs
node nashville_ng.test.mjs   # the real node suite against the patched tracker
node bench.mjs               # cost per reading, band calibration
```
