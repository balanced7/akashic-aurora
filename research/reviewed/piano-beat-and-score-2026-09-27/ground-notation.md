# ground:notation

_Verbatim agent return, workflow wf_fc6a68ac-233, 2026-09-27._

# LENS 6: QUANTIZED NOTES → READABLE SHEET MUSIC

## 0. The brief is wrong about the tree. This layer is already built.

The task text says "no quantization anywhere in the tree." That is false and I verified it by running the code. `arsenal/web/piano/score/` is a 5,962-line engraving pipeline from a prior arc (`research/in-flight/live-sheet-music-2026-09-14/`, slices LS1–LS6, with ratified rulings in `ls1-rulings.md` and `plan-amendments.md`).

I ran it on Daniel's session:

```
node arsenal/score_cli.mjs export 20260927-171534 --take lens6full
S69 lens6full: 4633 note-ons, rhythm unverified, 274 clean measures, 6 forced
  musicxml: 280 measures, 5838 note pieces, metronome marks 7 (rubato 4), freely 1
  LR9a pass · LR9b pass · LR9c pass
```

`tests/score_export.test.mjs`: **84 passed, 0 failed**, 437 fixture exports, 0 bad notes, median **4.6 ms per export** (max 22.7 ms). Everything below is measured against that run, not proposed.

**Do not build this layer. It exists, it is tested, and it is fast enough for realtime.** The work is the four gaps I name in §7.

---

## 1. The pipeline, and which steps are real problems

Documented at `arsenal/web/piano/score/index.js:5-8`, verified by running:

| Step | File | Real algorithmic problem? |
|---|---|---|
| Onset grouping, roll/grace detection | `onsets.js` (229) | **Yes** — chord vs. roll vs. grace at 40–120 ms |
| Beat / tactus tracking | `beat.js` (697) | **Yes** (not my lens) |
| Per-beat division choice | `quantize.js` (267) | **Yes** — Viterbi over {1,2,3,4,6} |
| Hand → staff | `hands.js` (347) | **Yes** — Viterbi, the hard one |
| Voice within staff | `hands.js:assignVoices` | **Yes** — the hardest |
| Written durations under pedal | `measures.js` (361) | **Yes** — sounding ≠ written |
| Ties, rests, bar lines | `measures.js` | **Yes** |
| Pitch spelling | `spell.js`, `nashville.py/js` | **Yes** — solved here |
| Accidental state | `accidentals.js` (59) | **Yes** — solved, bar-local |
| Clef + octave lines | `hands.js:clefsAndOctaves` | **Yes** — solved, 0 violations |
| Beam grouping | `measures.js` → `musicxml.js` | Mostly formatting |
| Spacing / collision | `layout.js` (507) | Formatting, solved in-house |
| Stems, glyphs, page breaks | `layout.js`/`engrave.js` | Formatting — give to Verovio |

---

## 2. Voice separation — real numbers, and they are the honest ceiling

`hands.js` runs a **Viterbi over onset groups**: candidate splits are every pitch gap plus all-left/all-right; costs are span (12/16 semitones), continuity (1/6 per semitone from a 2 s pitch history), crossing (3), non-maximal gap (0.5), figure-switch (3). Voices within a staff use a sustain rule: a note still held at a later onset and below every note of it becomes the lower voice.

**Measured** (`plan-amendments.md:251`, 213 held-out takes):

| | Staff | Voice F1 |
|---|---|---|
| Gate | 0.95 | 0.90 |
| **hands.js live** | **0.9658 PASS** | **0.8588 FAIL** |
| Hindsight ceiling | 0.9658 | 0.8738 |
| With *truth* staves | — | **0.9380** |
| Naive MIDI-60 split | 0.9632 | 0.6715 |

By texture: mixed 0.9981/0.915 · ballad 0.9742/0.843 · **arpeggio 0.918/0.8198**.

**How good can it realistically get?** Staff assignment is solved — 0.966, and the Viterbi buys only +0.003 over a MIDI-60 split on staff, so the staff number is easy. Voice is the real one, and **0.94 is the ceiling of the current rule even given perfect staves**. Getting past that needs a different rule, not tuning. This was tuned and the tuning is exhausted: a second lower-voice rule was tried and *dropped* (0.9365 → 0.9268).

**Failure decomposition** (51,643 truth links, 43,852 shared): missed 3,450 staff / 3,572 voice-split / 759 onset-tick; extra 3,208 staff / 1,837 voice-merge / 2,068 onset.

**What it looks like when it fails** — two named modes:
1. **Left-hand arpeggio tops at C4–A4 read as right hand.** Every distance cost prefers the idle right hand. On the page a left-hand figure visibly jumps staves mid-arpeggio. This is the 0.918 arpeggio staff score.
2. **Triads released early under the pedal leave the lower voice.** An inner chord tone detaches into its own voice and drags its own rests behind it.

Both are *legible wrongness* — a reader sees a weird but playable page, not garbage. That matters for the MVP argument.

---

## 3. Pitch spelling — solved, and yes chordread feeds it

Four cooperating pieces, all present:

- **`arsenal/web/piano/spell.js`** — "the one shared speller." Cost model against the key: 0 = key's own scale spelling, 1 = one accidental off, 2 = odd letter (B#/E#/Cb/Fb) or a scale pitch on the wrong letter, 3 = double accidental, triple forbidden. Ties go to the key's spelling, then the bias spelling.
- **`arsenal/nashville.py:222 _respell` / `:253 spell_in_key`** — Python twin, same rules, both run `tests/fixtures/nashville_cases.json`.
- **`arsenal/web/piano/keysig.js`** — `staffAccidental()` and `signaturePlaces()`; key signature adoption with a settle gate (2 bars / 4 s), never mid-chord, max one change per 8 bars.
- **`arsenal/web/piano/score/accidentals.js:24 decideAccidentals`** — bar-local state per *staff position* (letter + octave), courtesy accidentals after bar-line ties.

**Does chordread.js output feed spelling? Yes, as the fallback; key areas are primary.** `chordread.js:21` freezes `ReadResult = { ..., key: key name | null }`. `score_cli.mjs:22-24` states the order: `summary.json nashville.areas` first, **"else the key the page's Nashville tracker logged on chord events."** Confirmed on Daniel's run: `export.json` `keySource: "summary"`, and his session carries

```
areas: G major  (0:00–7:14)  r = 0.9481
       E major  (7:14–end)   r = 0.9763
```

Those r values are high; the key input is not the weak link.

**Receipt that it works** — on 4,633 notes: `unspelledNotes: 0`, 96 accidentals across 280 bars (**median 0/bar, mean 0.34**), `courtesy: 0`, `accClashes: 1`. Visible in the rendered page as a clean G-major signature with almost no accidental clutter.

**This question is answered and closed.** Do not spend effort here.

---

## 4. Note values, rests, ties, beams, grace — and the un-notatable note

`measures.js:19-27` derives *written* duration from *sounding* duration with explicit pedal cases:
- **Pedal up at release** → snap release forward to the beat's division; legato-fill to the next onset when the gap is under one 16th; min one slot; cap at bar end. Staccato mark when held under 40% of its slot.
- **Pedal down** → if sound-end reaches the next onset, write to it; else snap to nearest slot, then a rest.
- **Held bass (voice 4)** → one bar-line tie only, and only when the next bar has no onset in that voice before its midpoint.

Accuracy: **durations exact 0.971** (0.985 when the onset is exact), `barsFullyExact` 0.886 (`plan-amendments.md:241`).

**The un-notatable note has a real answer: the "loose beat" escape hatch.** `quantize.js:29-34` — when the best division costs more than `looseCost` (12), or a collision can't be explained as a roll, the beat is marked loose. The clean pass then places its groups on a d=6 grid by least total displacement; live, it is drawn proportionally as **tape**, which *claims no rhythm at all*. This is the right design: the system refuses to lie rather than forcing a wrong value.

**Grace notes: detected but never written.** `onsets.js:20-22` detects them (single note under 110 ms, leading 30–120 ms, 1–2 semitones away) and `onsets.js:21` says the grid test "belongs to T3." But the emitted MusicXML contains **0 `<grace>` elements**. Detection exists, the notation path drops it. Concrete gap.

**Readability is the real failure, and I measured it on Daniel's own take:**

```
tie elements/bar     median  7.0   mean  7.94   p90 16   max 34
note pieces/bar      median 19.0   mean 20.85   p90 34   max 54
rests/bar            median  3.0
tuplet brackets/bar  median  0.0   mean  1.99   p90  8   max 16
accidentals/bar      median  0.0   mean  0.34
```

Seven ties per bar, median. The LS3 bench flagged the same thing and left it open (`plan-amendments.md:253`: worst session ties 6/bar, tuplet brackets 4.5/bar — both recorded **FAIL**). The diagnosis in the repo is correct: ties are *intra-bar spelling splits of long pedal-filled values*, and on oracle beats the same code produces **0 ties and 0 brackets**. So this is not an engraving bug. **It is the beat grid's error surfacing as tie clutter.**

---

## 5. Tooling — installed and run, not guessed

| Tool | Installable here? | What it does | What we'd still write |
|---|---|---|---|
| **Verovio 6.3.0** | **Yes.** Zero deps. Installed, ran. | MusicXML/MEI → engraved SVG. **Loaded the 1.4 MB / 280-bar score in 336 ms; rendered a page in 16–56 ms; 12–14 pages.** | Nothing. It is a pure consumer of what we already emit. |
| **music21 10.5.0** | **Yes.** Deps only `webcolors`, `jsonpickle` — **no numpy constraint at all.** | Analysis, MusicXML round-trip, an independent validator | Not needed in the render path |
| **partitura 1.9.0** | **Yes.** `lark-parser`, `mido`, `xmlschema`, `elementpath` — all pure Python | Score↔performance alignment, match files | Not needed yet |
| **abjad** | **NO.** Hard fail: `Preparing metadata (pyproject.toml) did not run successfully` → `invalid command 'bdist_wheel'` | — | Don't. |
| **MuseScore / LilyPond** | **Absent from this machine.** Both are heavy GUI/binary installs | Batch PDF | Avoid; Verovio covers it |
| **Direct MusicXML** | **Already done**: `musicxml.js` (387 lines), MusicXML 4.0 partwise | — | Two fixes, below |

The brief's numpy worry does not apply to any of these. None of the three viable ones touches numpy.

---

## 6. I found a real defect by rendering with Verovio

The house verifier LR9a passes — it checks beam structure **against the transcriber's own model**. An independent consumer disagrees:

```
verovio load: 651 [Error] Adding 'beam' to a 'chord'
              337 [Error] MusicXML import: Chord starting point has not been found
               18 [Error] Adding 'tuplet' to a 'chord'   (cascade)
               16 other                          = 1,016 errors, 337 chords mis-imported
```

**Root cause, `arsenal/web/piano/score/musicxml.js:369`:**

```js
beam: beamOf.get(it), tuplet: k === 0 ? bracketOf.get(it) : null,
```

`tuplet` is correctly gated to the chord's principal note (`k === 0`). **`beam` is not.** Per MusicXML 4.0, `<beam>` belongs on the chord's first note only. So every subsequent `<chord/>` member also carries the beam: **1,028 offending notes across 166 of 280 measures**, and the principal carries it too in 819 of 1,163 chord runs (0 cases of members-only) — so it is pure duplication.

**Proven, not theorized.** Stripping exactly those 1,028 elements from a copy took Verovio from **1,016 errors → 0**, and the page rendered in 16 ms. The fix is one conditional: `beam: k === 0 ? beamOf.get(it) : null`.

Second, smaller: one `[Warning] MusicXML import: octave for 'fdogefs' could not be closed`. Opens and stops balance 26/26 with no per-lane imbalance, so this is a placement/ordering nuance, not a leak. Low priority. **I did not root-cause it.**

The rendered page is attached above — that is Daniel's own playing, engraved, with G-major signature, dynamics, `con Ped.`, `rubato`, triplet brackets and an 8va line. It is real notation today.

---

## 7. The minimum viable output for a drummer — and why it is *not* the full score

**The grid is not trustworthy, and that is the finding that should drive the decision.**

On Daniel's take, **every one of the 274 bars is `kind: "tape"`** and `rhythm: "unverified"`. Not one bar earned "metric." This is not a fluke: the LS3 bench recorded **"Only 2 of 1,969 bars are metric at rung4Floor 8"** — 0.1% across 18 sessions.

I measured what the grid is doing:

```
beat period over 809 beats → BPM:  p10 81.6 | median 94.6 | p90 127.7   (p90/p10 = 1.56)
played minus notated position:     median +3.0 ms, sd 27.9 ms
                                   |error| median 12 ms
                                   65.5% within ±20 ms, 10.1% beyond ±50 ms
RH vs LH at the same notated tick:  median +0.0 ms  (n=559)
```

Read those together. The rubato threshold in the code is 1.08. **The grid is breathing by 1.56.** That is not rubato at a stable pulse — that is the tracker changing its mind about the tactus, which is exactly the 120 ms / 160 ms two-subdivision collision the brief predicted. And the RH/LH offset is *exactly zero* — there is no measurable hand-spread signature, which for a pianist-drummer is itself suspicious and suggests the grid is being fitted *to* the notes rather than the notes measured *against* a pulse.

**So the honest MVP is not a score. It is a grid you can argue with.**

A microtiming readout built on this grid would be measuring the tracker's wobble and selling it to Daniel as his feel. That is the one outcome worse than no feature: it would tell a drummer he rushes when the software drifted. **Ship nothing that reports "your timing" until a bar can earn "metric."**

What I would put in front of him instead, in order:

1. **A tempo curve with a confidence band** — beat period over time, shaded where the tracker is unsure, over the piano roll he already has (`scripts/piano_roll_render.py`). He is a drummer. A tempo curve is a *native* object to him in a way a treble clef is not. It needs no voice separation, no spelling, no tie logic — none of the layer that is failing.
2. **The IOI histogram with subdivision lines drawn on it.** His 120/160 ms double cluster becomes visible *as* two subdivisions of one pulse. This directly answers "the strange rhythmic stuff that didn't come out how I wanted," and it needs zero notation.
3. **Deviation-from-grid, but only on bars that earned "metric"** — and if that is 0.1% of bars, the honest output is "I can't vouch for any bar yet," which is a true and useful statement.
4. **The engraved score as the artifact, not the analysis.** It is beautiful, it is already produced, it is worth having — but at median 7 ties and 19 note-pieces per bar it is a *keepsake and a proof*, not a reading of his playing. Do not position it as the deliverable.

The argument in one line: **notation is a lossy compression whose loss is exactly the thing he asked us to capture.** Everything the score throws away — the ±28 ms, the tempo breathing, the subdivision ambiguity — is the performance. Give him the residual first, and the score second.

---

## 8. Recommended stack

**Add Verovio. Add nothing else.**

```
py -m pip install verovio          # zero deps, 336 ms load, 16 ms/page on the real take
```

Optionally `music21` (3 pure-Python deps, no numpy) as an **independent** MusicXML validator — its value is precisely that it is not our code, which is how the beam defect surfaced. `cairosvg` if PNG is wanted.

**Reject:** abjad (won't install), LilyPond and MuseScore (absent, heavy, and Verovio already renders in 16 ms), partitura (capable but nothing needs it yet — a capability with no retirement rule is debt).

**Cost:** one pip install, one dependency, zero new code in the render path. Verovio consumes `take.musicxml` unchanged.

**The four gaps, ordered by value per unit of work:**

1. **Fix `musicxml.js:369`** — one conditional, proven to take 1,016 Verovio errors to 0. Then add a Verovio-load assertion to `tests/score_export.test.mjs` so a foreign consumer guards the export from here on. This is the single highest-value line in the whole lens.
2. **Build the drummer view of §7** — tempo curve + IOI histogram over the existing roll renderer. No notation dependency, uses `performance.py`'s existing IOI machinery (`arsenal/performance.py:1389-1416`).
3. **The beat tracker** (not my lens, but it gates everything) — 0.1% metric bars is the root cause of the 7-ties-per-bar clutter, since the same engraver produces **0 ties on oracle beats**. Fixing the grid fixes readability for free. **Do not retune the engraver.**
4. **Voice F1 0.859 → 0.94** — needs a new rule (group figures by beat after quantization), not tuning; the repo already exhausted tuning and recorded it. Leave it; it fails *legibly*.

**Not verified:** I did not run the full `score_hands`/`score_beat`/`score_quantize` suites (only `score_export`, 84/84). I did not root-cause the octave-shift warning. I did not test Verovio's realtime incremental path — only whole-score load, which at 336 ms for 11.5 minutes of music is already far inside a live budget but is not the same as bar-by-bar streaming. The microtiming numbers in §7 are computed against a grid the system itself declines to certify, and should be read as a measurement *of that grid*, not of Daniel's timing.