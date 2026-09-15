# Chord accuracy: what the field does, what our next-gen design lacks

| Field | Value |
|---|---|
| Type | research (in flight), lane: CHORD ACCURACY TECHNIQUES |
| Date | 2026-09-14 |
| Author | Vandor (claude seat), research subagent |
| Status | Research only. No `arsenal/` edits, no servers, no downloads. Web sources cited inline and in section 6. |
| Compares against | `research/in-flight/piano-theory-nextgen-2026-09-14/theory-nextgen-spec.md` (TN0-TN11, NG1-NG17) and `design-engine.md` (grammar 3, costs 4, live window 7) |
| Privacy | One read-only count over the practice logs (pedal CC64 values at logged crossings). No names, times or transcriptions. |

Daniel, on Discord (verbatim):

> "I wonder how we can make this be the ultimate practice / jamming tool, are there any other projects that are similar that we could look at for features we can integrate? Any ideas on how to improve chord accuracy? I also love how our system shows you the chord for notes arpegiated with sustain! What other detections or analysis do you think would be really cool to display?"

---

## 0. In one screen

**Where we stand.** Our next-gen design already does most of what the research field does, and in a few places it goes
further:
- **Segmenting.** The offline engine splits a session into windows by dynamic programming over a misfit cost. That is
  the same idea as the segment models that score how well a whole stretch of notes fits a chord.
- **Naming.** A grammar builds names from root, base, tensions and bass, the same way large-vocabulary systems split a
  chord into parts.
- **Honesty.** The reader returns ranked names with calibrated confidence bands. Most published systems return one
  label.

The gaps are not in the reader's core. They are in five areas around it:

1. **We have no ground truth.** Every accuracy number compares against our own offline engine, which the spec admits is
   partly circular. The field scores against human labels and assumes several names can be right: expert annotators
   agree on only 73% of simple major/minor labels and 54% of complex ones (CASD).
2. **We don't use the future.** In the leaning and ambiguous bands the right name is already in the top 3 for 91-95% of
   windows, but it comes first only 56-69% of the time. Choosing among those names using the chords before and after is
   the cheapest real gain we have.
3. **Note weight ignores physics and meter.** A note counts by how long it is heard and how hard it was struck. Piano
   decay, register, metrical accent and passing tones that resolve by step (Temperley's rule) are not used.
4. **The pedal is treated as on or off.** In Daniel's own logs, logged pedal presses carry CC64 values spread across
   64-126, so his controller sends pedal depth. The page cuts it at 64 and logs only the crossing.
5. **Nothing learns from him.** Corrections, his own vocabulary and his own chord-to-chord habits never feed back. The
   research on personalising chord labels (Koops) and on sparse human corrections (Serenade) says they should.

**Top improvements, by value for effort** (full list in section 4):

| # | Improvement | Effort | Expected gain |
|---|---|---|---|
| C1 | Gold set from Daniel's ear, with several accepted names per window | M | Makes every other number trustworthy. It replaces the circular reference. |
| C2 | Field-standard scoring (mir_eval vocabularies, Harte export, over/under-segmentation) | S | Separates boundary errors from naming errors, and makes our numbers comparable with the literature |
| C3 | Pick among the top 3 names using neighbouring chords (fixed-lag re-ranking) | S-M | Estimated **+2 to +4 points** of static agreement (ceiling +7.1), all on leaning and ambiguous windows |
| C4 | Separate confidence for root, family, bass and extensions | S | Less flicker (extension-only changes become `grow`). Root and bass can show early. |
| C5 | Texturised synthetic streams built from `groove.js` | S-M | Thousands of labelled boundary cases instead of 12 |
| C6 | Salience v2: decay, register, passing tones that resolve by step | M | Aims at the melody-note losses (`6m7b13(11)`-type names) |
| C7 | Pedal depth plus re-pedal detection | S-M | Cleaner window boundaries in pedalled bars |
| C8 | "Call it": corrections that apply in all 12 keys | M | Each correction fixes that voicing in every key, for good |

---

## 1. How the field names chords

### 1.1 Segmentation: where one chord ends

| Approach | How it cuts | Source |
|---|---|---|
| **Event partition plus graph search** | A candidate boundary at every note-on and note-off. Each possible segment is scored by its best template, and a shortest-path search picks the partition. The greedy HarmAn search gets within about 1% of the full search's score and reaches about 76% event accuracy on the KP corpus. | Pardo and Birmingham, *Computer Music Journal* 2002 |
| **Semi-Markov CRF** | Labels whole segments, not frames. A segment is scored on **purity** (how many of its notes are in the chord), **coverage** (whether each chord tone appears), bass, chord bigrams and metrical accent, plus figuration detection and duration weighting. It beats a discriminative HMM by wide margins (TAVERN 78.0% against 57.0%). Temperley's rule-based Melisma still wins on KP and Rock. | Masada and Bunescu, TISMIR 2019 |
| **Preference rules** | Change harmony on strong beats. A note that does not fit is fine if a step-neighbour soon follows it (ornamental dissonance). Roots prefer to move a short way on the line of fifths. | Temperley, Melisma harmony program |
| **Hidden semi-Markov model** | Models chord duration directly, so harmonic rhythm is a learned distribution rather than a smoothing constant. Chord-quality templates act as fixed priors. | Uehara, arXiv 2403.04135 (2024) |
| **Boundary-aware neural** | A separate boundary head predicts chord changes and modulates the encoder with FiLM. The decoder then fills in root, quality and bass step by step. | BACHI, Yao et al., ICASSP 2026 |
| **Pedal in performance MIDI** | Transcription work extends a note's offset until the pedal lifts or the same key is struck again. Continuous pedal depth matters because a binary cut at 64 loses press, release and direction-change information. | Kong et al. 2020 (arXiv 2010.01815); streaming transcription with pedal (arXiv 2503.01362); Zhang et al. 2025-26 (arXiv 2510.03750) |

### 1.2 Note salience: which notes count, and how much

- **Duration and coverage** (semi-CRF). A note's weight is its share of the segment's time, and a chord is penalised for
  tones it expects but does not hear.
- **Metrical accent** (semi-CRF, Temperley). Notes and chord changes on strong beats weigh more.
- **Figuration** (semi-CRF, AugmentedNet). Arpeggios and Alberti patterns are recognised as one chord. AugmentedNet
  goes further: it trains on block-chord realisations deliberately broken into textures (a split bass, an Alberti
  pattern, syncopation), because plain block chords did not transfer to real keyboard textures.
- **Root salience and register** (Parncutt 1988, a revision of Terhardt). A chord's root is inferred from weighted
  "root-support" intervals (octave, 5th, major 3rd, minor 7th, 9th, minor 3rd). The model outputs a root, how ambiguous
  it is, and a 12-value weight vector. Later variants give lower tones more weight.
- **Non-chord tones as a first-class task** (AnalysisGNN, CMMR 2025). A dedicated module flags passing and non-harmonic
  notes and removes them from every downstream task.
- **Ornamental dissonance** (Temperley). A note that does not fit is excused when a half or whole step follows it
  closely.

### 1.3 Model families, with numbers

| Family | Example | What it gets right | Limits | Numbers |
|---|---|---|---|---|
| Template / rule | Pardo-Birmingham; tonal.js `Chord.detect` | Transparent, instant, no data needed | Fixed vocabulary, no context; tonal.js returns every name the note set matches, with no ranking by bass or key | about 76% event accuracy on KP (HarmAn) |
| Rule system with context | Melisma (Temperley) | Meter, line of fifths, ornament rule | Hand-tuned | KP 81.9%, Rock 77.9% event accuracy (as reported by Masada-Bunescu) |
| Discriminative segment model | semi-CRF | Learned weights over purity, coverage, bass, meter | Small label set (triads and 7ths) | BaCh 83.2%, TAVERN 78.0%, Rock 70.1% |
| Joint context model | Mauch-Dixon DBN (audio) | Infers metric position, key, chord and bass together | Audio-side; heavy | TASLP 2010 |
| Decomposed large vocabulary | Jiang et al., ISMIR 2019 | A chord becomes triad + bass + 7th + 9th + 11th + 13th, each with a small vocabulary; this beats the long tail of rare qualities | Audio-side | ISMIR 2019 |
| Transformer | Harmony Transformer v2 | Strong segmentation from local attention | Needs labelled data | POP909-CL full chord 82.2% |
| Boundary + iterative decoding | BACHI | Decodes root, then quality, then bass, like ear training | Pop and classical vocabularies only | Classical (DCML + WiR) root 77.8%, quality 79.0%, bass 77.0%, full 68.1%; POP909-CL full 82.4% |
| Graph neural network | ChordGNN, AnalysisGNN | Note-level features (spelling, duration, metrical position), onset-level output | Score input, not performance | Classical full 58.5% (from BACHI's table) |
| Multitask CRNN | AugmentedNet (ISMIR 2021) | Root, quality, inversion, key, degree, harmonic rhythm and pitch-class sets together; texturised synthetic data | Score input | 6 corpora: ABC, BPS, HaydnSun, TAVERN, WiR, WTC |
| LLM as coordinator | Chang et al. 2025 (audio) | GPT-4o reconciles key, beat and chord tool outputs | Slow, audio | +1 to +2.77 points on the MIREX metric |

**The pattern.** Full-chord accuracy sits well below accuracy on each part: 68% full against 77-79% per part in
classical. Our own measurements show the same gap (core 0.577 against exact 0.373 at 250 ms). Naming the extensions and
the bass is the hard part everywhere.

### 1.4 Key and function context

- **Joint key-chord inference** (Mauch-Dixon; AugmentedNet's multitask key and degree outputs). Key and chord are
  decided together, not one after the other.
- **Chord language models help, but modestly.** Chord-level language models with a separate duration model add about 2
  points (Korzeniowski and Widmer 2018, arXiv 1808.05335). Complex frame-level language models add almost nothing over
  simple smoothing (arXiv 1702.00178). Lesson: put context at the **chord** level, not the frame level. That agrees with
  our spec's finding that hysteresis at the reading level barely changed agreement.
- **Priors from big corpora.** Chordonomicon (666,000 songs, each progression stored as a weighted transition graph)
  could give a generic prior on chord moves. It is pop and guitar heavy, so its moves are not Daniel's.

### 1.5 Evaluation: how the field scores

| Metric | Definition (mir_eval) | Why we want it |
|---|---|---|
| `root` | root only | same as our "core" minus the family |
| `thirds`, `triads` | root and 3rd; root and triad quality up to the 5th | family-level truth |
| `sevenths` | only maj, maj7, 7, min, min7 are scored; other labels are excluded | standard comparison point |
| `tetrads` | the whole quality folded into one octave, extensions included | closest to our "exact" |
| `*_inv` | the same, plus the bass must match | our slash names |
| `mirex` | right if it shares at least 3 pitch classes | a lenient floor |
| **WCSR** | each comparison weighted by duration | our "time with the right name" |
| **seg, overseg, underseg** | directional Hamming distance between the boundary sets | **scores boundaries apart from names**. We have no equivalent. |

**Syntax.** Harte et al. (ISMIR 2005) define a text grammar for chord labels, such as `C:maj7(9,#11)/3`. mir_eval,
JAMS and most datasets read it.

**Human ceiling.** In the Chordify Annotator Subjectivity Dataset (CASD, 50 songs, 4 experts), annotators overlap on
about 73% of labels in the major/minor vocabulary and 54% in the most complex one. For Daniel's vocabulary, one "right
answer" per window is the wrong model. The spec's ALSO line is already the right instinct.

**Conventions conflict too.** Dilemmadata (2026) found that two major Roman-numeral corpora encode the same musical fact
differently: vocabulary size, extension conventions, special chords. Our lexicon and `parseSuffix` should state their
conventions explicitly.

### 1.6 Datasets

| Dataset | What | Fit for us |
|---|---|---|
| POP909-CL (2025-26) | 909 pop piano arrangements (MIDI) with human-corrected chords, beats, keys and time signatures. The corrections added about 15 points of full-chord accuracy over the original POP909 labels. | Best external check for **plain vocabulary on piano MIDI**. Few maj13#11 chords. |
| When in Rome (TISMIR 2023) | Over 2,000 functional analyses of 1,500 works | Function labels, pivot and secondary-dominant cases |
| BPS-FH | Beethoven sonata first movements with functional harmony | Classical piano texture; arpeggio stress tests |
| DCML / Distant Listening, Dilemmadata | Note-wise Roman-numeral annotations, reconciled | Conventions reference |
| CASD | 4 experts' labels for 50 songs | How to score with several right answers |
| Chordonomicon | 666,000 progressions, as graphs | Generic transition prior (C11) |
| PiJAMA (TISMIR 2023), Aria-MIDI (ICLR 2025) | Large piano MIDI corpora transcribed from audio, pedal included, **no chord labels** | Unlabelled stress tests: flicker, unnamed time and label life on jazz and pedalled piano |

### 1.7 Personalisation and learning from corrections

- **Chord label personalisation** (Koops, de Haas, Bransen and Volk 2017; extended in *Neural Computing and Applications*
  2018). One model learns a shared, interval-based representation of chords and then outputs each annotator's own
  vocabulary. Learning from several references beat learning from one.
- **Serenade** (Koops, Micchi, Manco and Quinton 2023). The model predicts, a human corrects a few low-confidence spots,
  and the model predicts again under those constraints. Each correction also fixes the labels around it.
- **Conformal prediction** (Angelopoulos and Bates, arXiv 2107.07511). Turns any scorer into a set of names that holds
  the truth at a chosen rate (for example 90%), using a small calibration set. It is the principled version of "show a
  second name when unsure".

### 1.8 What products do

- **DAW detectors.** On a KVR thread (May 2025), users rate Studio One, Cubase, RapidComposer and Logic. The common
  complaints:
  - names that are too clever: a plain add9 read as `F#11`, or as maj7 when add9 was meant;
  - no awareness of the chords before and after, or of voice leading.
  - These are exactly the failure modes our ALSO line and context work target.
- **Scaler Detector** (Scaler Music, late 2025). Detects key, scale and chords from audio or MIDI, live or from a file.
  The product page does not disclose the method, the vocabulary or any accuracy figures.
- **tonal.js** `Chord.detect`. A pitch-class-set lookup that returns every matching name. An `assumePerfectFifth` option
  lets it name chords with no 5th. It is the common baseline in JavaScript tools, and ours is well past it.

---

## 2. Our design against the field

| Technique | Field | Next-gen status | Evidence |
|---|---|---|---|
| Segment scoring with a boundary penalty | semi-CRF purity and coverage; Pardo-Birmingham | **Has** (offline DP; live lagged split test) | design-engine 7.1; `practice.py` `harmonic_windows`, `WINDOW_PENALTY_MS` |
| Figuration and arpeggio as one chord | semi-CRF, AugmentedNet | **Has** (700 ms heard extension, onset groups) | 7.1; Daniel's favourite feature |
| Pedal at boundaries | transcription offset extension | **Partial.** Pedal-held notes count as heard; a lift near an attack halves the split penalty. On/off only, and only crossings are logged. | 7.1; `piano.js` `setSustain` |
| Pedal depth | Zhang et al. 2025-26 | **Lacks.** The controller sends depth (section 3.2); it is thresholded at 64. | |
| Decomposed vocabulary | Jiang 2019, BACHI | **Has for naming** (grammar: base + tensions + omissions + bass). **Lacks per-part confidence.** | 3.1-3.2, 4.3 |
| Ranked readings, calibrated confidence | rare (BACHI and ChordGNN return one label) | **Has, and ahead of the field** (bands: clear 0.95, leaning 0.69, ambiguous 0.56) | 4.4 |
| Several right answers | CASD, Koops | **Partial** (ALSO line; fixtures accept alternatives). No human-labelled gold set. | spec D5, NG3 |
| Metrical accent, strong-beat changes | Temperley, semi-CRF, Mauch-Dixon | **Lacks.** A beat grid exists only inside jam runs (`tempomap.js`) and in the planned practice-along BPM. | |
| Decay and register in salience | Parncutt; physical piano decay | **Lacks.** Salience is heard share x velocity; bass is special-cased. | 4.2 |
| Passing tones that resolve by step | Temperley, AnalysisGNN | **Partial.** A generic "faint note" drop under 0.35 salience; no step-resolution test. | 4.1 |
| Chord-level context | Korzeniowski LM; Mauch-Dixon | **Minimal.** Same-root prior -0.1, key prior -0.15, one bespoke look-ahead (gospel 5 over 4). | 4.2, 9.9 |
| Explicit duration / harmonic-rhythm prior | HSMM | **Lacks** (fixed 600 ms penalty) | |
| Learned weights | semi-CRF, neural | **Lacks.** Every cost is hand-tuned (A5 is another hand round). | 4.2, spec A5 |
| Field-standard metrics | mir_eval WCSR, seg | **Lacks.** Custom core, exact and unnamed only. | 1.2 |
| Harte export | datasets, mir_eval | **Lacks** (`parseSuffix` could emit it) | spec 2.2 |
| Learning from corrections | Serenade, Koops | **Lacks** | |
| Synthetic texturised training and test data | AugmentedNet | **Partial.** 12 hand-written `window_sessions`; `groove.js` already renders textures. | spec 2.6 |

---

## 3. Two local facts that change the plan

### 3.1 The reference is circular, and the field says labels are plural

- The spec's own risk 1: the offline engine shares the reader's intuitions, so 74% agreement flatters both.
- CASD shows even experts diverge on complex labels about half the time.
- Consequence: before tuning A5 or adding context, build a small human-labelled set that accepts several names
  (C1). Every other gain below is estimated against the offline engine and must be re-checked there.

### 3.2 Daniel's pedal is continuous

- Read-only count over six sessions' `events.jsonl`: logged pedal events carry values spread across 64-126 (127 is
  uncommon), plus a few values between 1 and 63.
- `setSustain` logs only the crossing of 64 (`piano.js` 1976-1983), so the value is whatever the controller sent as it
  crossed.
- A switch pedal sends only 0 and 127. His KeyLab pedal therefore sends a continuous signal, and the page discards the
  depth.
- Half-pedalling and quick "flutter" re-pedals are boundary evidence we never see.

---

## 4. Concrete improvements

Effort: S is half a day or less, M is 1-2 days, L is 3 or more days, following the spec's sizing. Gains are estimates
unless marked measured. Each item names its receipt, the check that shows the gain is real.

### C1. Gold set from Daniel's ear (the measuring stick)

- **What.** 150-300 windows from S1-S6, weighted toward leaning, ambiguous and loss windows. Each gets his accepted
  names (one or more) and a "none of these" option.
- **Where.** A chat verb (`practice label`): the cue channel plays the window's voicing on the page, Daniel picks from
  the top 3 or types a name, and answers go to `state/arsenal/...` (git-ignored). No recorded surface.
- **Why.** Circular reference (3.1); CASD's plural truth.
- **Effort.** M (verb and storage). About 20 minutes of Daniel's time per 100 windows.
- **Gain.** No accuracy by itself. It turns NG2 from agreement with our own engine into accuracy against his ear. It
  lets C3, C6, C9 and C10 be tuned without fooling ourselves, and it is the calibration set for C10.
- **Receipt.** At least 150 labelled windows. Report each engine's top-1 and top-3 hit rate against the gold set, next
  to the offline-agreement numbers.

### C2. Field-standard scoring layer

- **What.**
  - `toHarte(reading)` via `parseSuffix` (for example `Gb:maj7(9,#11,13)`, with the bass as a degree).
  - A lane that scores the reader and live pipelines with root, thirds, triads, sevenths, tetrads and their `_inv`
    variants (WCSR), plus seg, overseg and underseg against the offline windows and against C1.
  - Use mir_eval if the conductor approves the install, or reimplement the six comparisons (about 150 lines) in the
    existing lane.
- **Why.** Our "core 0.577" mixes boundary errors with naming errors. seg separates them. The numbers become comparable
  with BACHI's root/quality/bass/full table.
- **Effort.** S.
- **Gain.** Diagnostic. Expected to show that a real share of live core misses are boundary misses (the replay's
  static-to-live drop from 0.74 to 0.58 hints at this). That redirects tuning toward C5-C7.
- **Receipt.** The lane prints all metrics for pipelines A and C at 120, 250 and 400 ms.

### C3. Fixed-lag re-ranking with neighbouring chords

- **What.** When a window closes, re-rank its top 3 names by cost plus a transition score:
  - Movement of the root in fifths (the line of fifths).
  - Moves that stay inside the key.
  - A shared-tone or bass-step bonus.
  - 9.9's gospel rule as one case of the general rule.
- **Two outputs.**
  - The log and practice summary take the re-ranked name.
  - The live label swaps in place (H3 `grow`) only while the window still sounds.
  - Offline, run a semi-Markov Viterbi pass over the whole session with the same scores.
- **Why.** Chord-level language models add about 2 points (Korzeniowski); frame-level ones add nothing, which fits the
  spec's hysteresis result. Our bands leave unusual room: the right name is in the top 3 for 95% of leaning windows and
  91% of ambiguous ones.
- **Effort.** S-M (pure function over `readings`; the Viterbi pass is in the lane).
- **Expected gain** (arithmetic on design-engine 4.4, not measured):
  - If context closes half the gap between top-1 and top-3: leaning +0.13 x 285 s = 37 s, ambiguous +0.175 x 184 s =
    32 s, about **+3.6 points** of static agreement over 1,942 s.
  - Ceiling if it closes the whole gap: +7.1 points.
  - Realistic range: +2 to +4. Clear-band windows (1,473 s) are untouched by design.
- **Risk.** The offline reference itself uses context (`resolve_over_third`, `merge_same`), so agreement may rise by
  construction. Confirm on C1.
- **Receipt.** Gains and losses in both directions on the real windows (the NG2 format). The C1 top-1 hit rate rises.
  Clear-band agreement does not drop.

### C4. Separate confidence for root, family, bass and extensions

- **What.** Sum each reading's probability `p` over the top readings into separate probabilities for root, family,
  bass, and the tension set.
- **Commit rules.**
  - Root and bass commit at the settle.
  - A change that keeps root and bass is always `grow` (no pop, no new trail segment).
  - The HUD shows "root sure, colour unsure".
- **Why.** BACHI and Jiang both find that the parts are easier than the whole (68% full against 77-79% per part). Our
  core-to-exact gap says the same.
- **Effort.** S (arithmetic on `readings`; a rule in `harmony.js`).
- **Gain.**
  - Fewer pops: the share of label changes that keep root and bass converts directly to `grow`. Count it first in the
    replay; it is unmeasured.
  - Better Try `found` and rarity inputs, which can key on the confident parts.
- **Receipt.** Replay: pops per minute against today's 49, with that share reported. Calibration of each part's
  probability against C1 (reliability table).

### C5. Texturised synthetic note streams from `groove.js`

- **What.** Render Daniel's 24 voicings and the 17 seed cards, in 12 keys, through textures with known windows and
  names:
  - block;
  - rolled (a 60-250 ms sweep);
  - arpeggio under pedal;
  - bass then chord;
  - walking bass under held hands;
  - melody over a pad, with passing and step-resolving notes;
  - grace notes;
  - re-pedal at a change, and half-pedal.
- **How.** `groove.js` already turns voicings into timed events with `arp_ms` and humanise, so the generator is mostly
  a fixture writer.
- **Why.** AugmentedNet found plain block chords did not transfer to real keyboard textures, and texturised synthetic
  data did. `window_sessions` currently has 12 hand-written streams.
- **Effort.** S-M.
- **Gain.** Boundary and salience tuning (C6, C7, C9) gets thousands of labelled cases. It also directly tests "an
  arpeggio under the pedal reads as one chord", the behaviour Daniel loves.
- **Receipt.** At least 2,000 generated streams. seg at least 0.9 and exact names at least 0.9 on block and rolled
  textures; the other textures reported per texture.

### C6. Salience v2: decay, register, passing tones that resolve by step

- **Decay.** Heard weight decays exponentially from the onset, slower in low registers (piano strings ring longer).
  The pedal keeps the tail alive, and a key release without pedal ends it. This replaces the flat heard share.
- **Register.** Notes below about C3 get root-support weight in the manner of Parncutt, beyond the one-bass rule. The
  top voice is a melody candidate.
- **Step-resolving passing tones** (Temperley, AnalysisGNN). A pitch class that sounds under 400 ms, is not re-struck,
  and is followed within 300 ms by a note a half or whole step away in the same voice is marked passing. It is left out
  of the chord set but stays eligible for the scale line.
- **Metrical accent**, only when a beat grid exists (jam runs, practice-along BPM). Onsets on beats weigh 1.2 and
  chord changes on beats get a boundary bonus.
- **Why.** The spec's open losses (`6m7b13(11)`, `1m(add11)/b3`) are extension names caused by passing melody notes.
  The generic faint-note drop cannot tell a lingering colour tone from a passing one.
- **Effort.** M (`harmony.js` salience; mirrored in the offline lane).
- **Gain.** Aims at the 63 loss windows (107 s). Estimate: remove a third to half of the b13 and 11 over-namings.
  Unmeasured; check on C1 and C5.
- **Receipt.** Losses at most 40 with gains held at 188 or more (NG2 format). Passing-tone texture exact names at least
  0.85 on C5.

### C7. Pedal depth and re-pedal detection

- **What.**
  - Log CC64 as a thinned curve: value changes of 8 or more, or every 50 ms while moving. This is a log schema change
    in the log-schema lane (`performance.py` KINDS first).
  - In `harmony.js`:
    - Depth under about 90 damps partially, so heard weight decays faster.
    - A dip-and-return within 350 ms (a re-pedal), even one that never crosses 64, counts as a strong boundary signal,
      a full `PEDAL_DISCOUNT` at that time.
    - A slow half-release clears the upper notes first (a heuristic).
- **Why.** Section 3.2; Zhang et al. show binary pedal loses press, release and direction information. A re-pedal is
  how pianists mark a harmony change.
- **Effort.** S-M (log field plus window rule). The receipt needs new sessions logged with the curve.
- **Gain.** Fewer blended windows at pedalled changes, and fewer false splits inside a held pedal. Estimate: seg
  improves most in S1 and S6 (the lowest-core sessions). Unmeasured.
- **Receipt.** On C5 re-pedal and half-pedal textures, boundary seg at least 0.9. Live replay on new sessions reports
  seg against pipeline C without depth.

### C8. "Call it": corrections that stick in every key

- **What.** From the HUD (DOM, never recorded) or the C1 verb, Daniel picks the right name for a window. Each correction
  is stored as a key-free fingerprint: the interval set above the bass, plus the bass's degree in the key when a key is
  set, mapped to the chosen reading's base, tensions and bass degree. Three effects:
  1. **Exact memo.** The same fingerprint in any key gets the chosen name first. The runner-up stays the ALSO name.
  2. **Propagation** (Serenade). Windows in the same session with the same fingerprint are re-named, and the log is
     corrected.
  3. **Weight nudge.** A perceptron step moves the cost terms that separated the wrong top name from the chosen one.
     The step is capped, and every fixture receipt must still pass.
- **Why.** Koops (personal vocabulary), Serenade (a few corrections, constrained re-prediction).
- **Effort.** M (store, fingerprint, HUD control, verb). No new hotkey (spec D4).
- **Gain.** Each correction fixes that voicing in all 12 keys at once. His vocabulary is concentrated (a few chords
  hold most of his chord time), so 20-30 corrections should cover most of his loss time. Estimate.
- **Guards.**
  - Corrections never override a fixture in `chord_readings_cases.json` without a conductor-approved fixture change.
  - The memo is shown in the HUD as "your name".
- **Receipt.** A correction replayed on all 12 transpositions gives identical names. NG1 and NG2 stay green after 30
  scripted corrections.

### C9. Rolled-chord onset grouping

- **What.** Replace the fixed 50 ms onset group with a sweep detector: notes arriving in one direction of pitch with gaps
  of 90 ms or less, the whole sweep 300 ms or less, are one attack.
- **Why.** Lush pedalled playing rolls chords, and a 50 ms group splits a roll into several micro-attacks. The first
  few notes then get named (latency and flicker) before the chord is complete.
- **Effort.** S.
- **Gain.** Fewer labels that live under 0.3 s (the spec's NG5 blocker). Measure roll spans in the logs first.
- **Receipt.** On C5 rolled textures, 1 window per roll. Live replay median label life rises; latency rises at most
  60 ms.

### C10. Conformal ALSO sets

- **What.** With C1 as the calibration set, compute a nonconformity score (the cost gap to the top reading) and a
  threshold giving 90% coverage. The canvas ALSO shows when that set holds more than one name with a different root or
  bass.
- **Why.** Angelopoulos and Bates: calibrated sets of names with guaranteed coverage. This replaces hand thresholds
  (0.5 margin, 1.5 cost) with a measured guarantee.
- **Effort.** S once C1 exists.
- **Gain.** ALSO fires exactly as often as the uncertainty demands, which caps the 15% of chord time currently spent
  showing ALSO on recordings and keeps the loss safety net.
- **Keep the was-rule.** The spec found it covers 61 of 63 losses, so conformal ALSO is added next to it, not in place
  of it, until C1 shows the conformal set covers those losses too.
- **Receipt.** Coverage on held-out C1 windows is at least 0.88. ALSO time is reported against the was-rule's.

### C11. Personal transition and vocabulary prior

- **What.** From confirmed names only (C1 and C8 labels plus the clear band), build counts of Daniel's number-to-number
  moves and vocabulary. A small log-probability term, capped at 0.3 cost, goes into C3's re-ranking.
- **Generic fallback.** Chordonomicon's transition graph, transposed to numbers, if the conductor approves the download.
- **Why.** Koops: personal vocabularies are real. His habits are measured (after a 4, the 1 follows 45 times).
- **Effort.** M.
- **Gain.** It separates the mirror losses (2m over 4 against 4maj13#11 on the same notes) by what he usually means.
  The gain is bounded by C3's ceiling.
- **Risk.** Self-reinforcement if the engine's own guesses feed the prior. Hence confirmed names only.
- **Receipt.** C1 top-1 rises over C3 alone. No fixture regresses.

### C12. Harmonic-rhythm prior (duration)

- **What.** Replace the fixed 600 ms window penalty with a cost based on duration: minus the log-probability of the
  window's length under a lognormal fitted to his window durations. When a beat grid exists, use duration in beats and
  favour 1, 2 and 4 beats.
- **Why.** HSMM (Uehara) and Korzeniowski's duration model: modelling duration explicitly is where segment models beat
  frame smoothing.
- **Effort.** M (offline DP first, then the live lagged test).
- **Gain.** Fewer over-splits in slow pedalled playing and fewer under-splits in fast comping. Reported as overseg and
  underseg (C2). Unmeasured.
- **Receipt.** seg improves on C5 and on real replays without losing core.

### C13. Name levels as reductions, not a second engine

- **What.** "Names: simple" (spec Q1's alternative) becomes a fixed reduction of the full reading, following the mir_eval
  ladder: full, then tetrad (maj7#11), then seventh (maj7), then triad. Deliberate add9-type colour stays in the name,
  so the simple level never swaps it for a 7th, 11th or 13th.
- **Why.** The KVR complaints are over-analytical names in DAW detectors. Dilemmadata shows conventions differ. One
  engine and one log, several views.
- **Effort.** S.
- **Gain.** Fewer names he perceives as wrong when he means a plain colour. It also gives a cleaner TikTok label option.
- **Receipt.** Each reduction is consistent with mir_eval `sevenths` and `triads` on the fixtures.

### C14. External sanity runs and a neural second opinion (later)

- **External runs.**
  - Run the reader, with no retuning, on POP909-CL's MIDI (root, quality, bass, full, as BACHI reports them) and on a
    When-in-Rome piano subset.
  - This guards the plain vocabulary (the "must not regress" group) against overfitting to Daniel. BACHI's 82.4% full
    chord is a reference, not a target, because POP909-CL labels are beat-synchronous and pop-vocabulary.
- **Neural second opinion.**
  - Optionally, a small BACHI or AugmentedNet style model trained on POP909-CL plus C5 streams plus C1, run offline
    only.
  - It is used as a **disagreement detector**: windows where it and the reader disagree go to the front of the C1
    labelling queue (active learning). It never names the live label: latency, and no training data for maj13#11-type
    colour.
- **Effort.** M for the external runs (downloads need approval). L for the neural model.
- **Gain.** Protects the plain-vocabulary floor. Makes Daniel's labelling time about twice as productive by spending it
  on disputed windows (estimate).
- **Receipt.** Published-format metrics on POP909-CL. Labelling queue yield: corrections per 10 windows shown.

### Priority and fit with the TN phases

| Tier | Items | Lands in |
|---|---|---|
| **Now: measure honestly** | C2, C5, C1 | TN0 (fixtures grow: texturised streams, Harte export, gold-set format); C1's verb in the practice lane after TN8's owner window |
| **Next: cheap accuracy** | C3, C4, C9 | TN1 (re-ranking and per-part confidence are pure functions over `readings`); TN2 (`harmony.js` sweep grouping, `grow` rule) |
| **Then: signal quality** | C6, C7, C12 | TN2, plus the log-schema lane for the pedal curve (performance.py KINDS first) |
| **After the first night (TN9): learn from him** | C8, C10, C11, C13 | A new accuracy phase after TN9; HUD only, never recorded |
| **Later** | C14 | Needs download approval; offline only |

### What not to do

- **Don't put a neural model on the live label.** Every published symbolic model is trained on pop or classical
  vocabularies, and full-chord accuracy tops out around 68-82% on those. None covers Daniel's colours, and all add
  latency.
- **Don't add frame-level smoothing or HMM smoothing to the label.** The literature (arXiv 1702.00178) and our spec
  (hysteresis at the reading level) agree it barely helps. Context belongs at the chord level (C3).
- **Don't tune A5 against the offline engine alone.** Every hand round against a sibling engine deepens the circularity.
  Build C1 first, or at least in parallel.

---

## 5. Open questions

1. **Gold-set time.** Will Daniel spend about 20 minutes labelling about 100 disputed windows by ear, with the page
   replaying each voicing? It is the single highest-value input for accuracy work.
2. **Pedal curve logging.** Logging CC64 changes (thinned) grows the practice log. Does the log-schema owner accept a
   `pedal_depth` kind, and at what thinning?
3. **Downloads.** Do we fetch POP909-CL (and optionally Chordonomicon, and mir_eval) for external sanity runs, or
   reimplement the metrics and stay offline?
4. **Name levels.** Should "simple" names be a recording option (C13), given that the TikTok audience is not
   theory-literate?
5. **Do corrections count as teaching?** Should a "Call it" correction also feed the jam deck ("you call this your
   bright 4"), or stay in the engine only?

---

## 6. Sources

Segmentation, salience, models:
- Pardo and Birmingham, Algorithms for Chordal Analysis (CMJ 2002): https://interactiveaudiolab.github.io/assets/papers/pardo-birmingham-cmj02.pdf
- Masada and Bunescu, Chord Recognition in Symbolic Music: A Segmental CRF Model (TISMIR 2019): https://transactions.ismir.net/articles/10.5334/tismir.18 and https://arxiv.org/abs/1810.10002
- Temperley, Melisma harmony program: https://www.link.cs.cmu.edu/music-analysis/harmony.html ; Melisma v2: https://davidtemperley.com/melisma-v2/
- Uehara, Unsupervised Learning of Harmonic Analysis Based on Neural HSMM with Chord Quality Templates (2024): https://arxiv.org/abs/2403.04135
- Yao, Chen, Dubnov and Berg-Kirkpatrick, BACHI (ICASSP 2026): https://arxiv.org/abs/2510.06528 ; project page https://andyweasley2004.github.io/BACHI/ ; POP909-CL: https://github.com/AndyWeasley2004/POP909-CL-Dataset
- Chen and Su, Attend to Chords / Harmony Transformer (TISMIR 2021): https://transactions.ismir.net/articles/10.5334/tismir.65 ; HT v2: https://github.com/Tsung-Ping/Harmony-Transformer-v2
- Karystinaios and Widmer, ChordGNN (ISMIR 2023): https://arxiv.org/abs/2307.03544 ; AnalysisGNN (CMMR 2025): https://arxiv.org/abs/2509.06654
- Nápoles López, Gotham and Fujinaga, AugmentedNet (ISMIR 2021): https://archives.ismir.net/ismir2021/paper/000050.pdf
- Jiang et al., Large-Vocabulary Chord Transcription via Chord Structure Decomposition (ISMIR 2019): https://archives.ismir.net/ismir2019/paper/000078.pdf
- Chang, Chen, Chen and Su, Enhancing ACR through LLM Chain-of-Thought Reasoning (2025): https://arxiv.org/abs/2509.18700
- Parncutt root-finding model, implementation and notes: https://github.com/pmcharrison/parn88 ; Revision of Terhardt's model: https://www.semanticscholar.org/paper/Revision-of-Terhardt's-Psychoacoustical-Model-of-of-Parncutt/6d56c97425d5941319cd373c2897eee42711e62e

Context and language models:
- Mauch and Dixon, Simultaneous Estimation of Chords and Musical Context from Audio (TASLP 2010): https://www.eecs.qmul.ac.uk/~simond/pub/2010/Mauch-Dixon-TASLP-2010.pdf
- Korzeniowski and Widmer, Improved Chord Recognition by Combining Duration and Harmonic Language Models (2018): https://arxiv.org/abs/1808.05335
- On the Futility of Learning Complex Frame-Level Language Models for Chord Recognition: https://arxiv.org/pdf/1702.00178
- Chordonomicon (2024): https://arxiv.org/abs/2410.22046

Pedal:
- Kong et al., High-resolution Piano Transcription with Pedals (2020): https://arxiv.org/abs/2010.01815
- Streaming Piano Transcription with Sustain Pedal Detection (2025): https://arxiv.org/pdf/2503.01362
- Zhang, Fang, Wang and Fujinaga, Evaluating High-Resolution Piano Sustain Pedal Depth Estimation (2025-26): https://arxiv.org/abs/2510.03750

Evaluation, syntax, datasets:
- mir_eval chord module: https://mir-eval.readthedocs.io/latest/api/chord.html
- Harte et al., Symbolic Representation of Musical Chords (ISMIR 2005): https://ismir2005.ismir.net/proceedings/1080.pdf
- Koops et al., Annotator subjectivity in harmony annotations of popular music (JNMR 2019): https://www.tandfonline.com/doi/full/10.1080/09298215.2019.1613436 ; CASD: https://github.com/chordify/CASD
- Gotham et al., When in Rome (TISMIR): https://transactions.ismir.net/articles/10.5334/tismir.165
- BPS-FH functional harmony dataset: https://github.com/Tsung-Ping/functional-harmony
- Hentschel, Karystinaios, Widmer and Neuwirth, Dilemmadata (2026): https://arxiv.org/abs/2606.31595
- PiJAMA (TISMIR): https://transactions.ismir.net/articles/10.5334/tismir.162 ; Aria-MIDI (ICLR 2025): https://arxiv.org/pdf/2504.15071

Personalisation and uncertainty:
- Koops, de Haas, Bransen and Volk, Chord Label Personalization (2017): https://arxiv.org/abs/1706.09552
- Koops, Micchi, Manco and Quinton, Serenade: human-in-the-loop ACE (2023): https://arxiv.org/abs/2310.11165
- Angelopoulos and Bates, A Gentle Introduction to Conformal Prediction: https://arxiv.org/abs/2107.07511

Products:
- KVR forum, Best DAW for accurate chord detection (May 2025): https://www.kvraudio.com/forum/viewtopic.php?t=620490
- Scaler Detector: https://scalermusic.com/products/scaler-detector/
- tonal.js chord-detect: https://github.com/tonaljs/tonal/tree/main/packages/chord-detect
