# Piano theory, next generation: the build spec

| | |
|---|---|
| Status | Build spec, 2026-09-14. Design only: nothing under `arsenal/` edited, no server or browser started, nothing downloaded. |
| Asked for | Daniel, verbatim (Discord, from work): "Do you think we can brush up our chord and scale detection to show things in an even better way? I love where its at now. But I am excited to see what is the next Gen level we can bring it to!" |
| Merges | `design-engine.md` (detection engine, measured), `design-display.md` (placement, measured), `design-pedagogy.md` (what teaches, measured), and two judges (delight and viewer; feasibility and honesty). Where they disagree, section 1 decides. |
| Normative sources | This file wins. For detail it does not repeat, `design-engine.md` 3.1-3.2 (grammar), 4.1-4.4 (costs, bands), 7.1 (live window), 8.1 (scale ranker) and 9.3, 9.6, 9.7 (pivot, backdoor patch, function labels) are normative **with the amendments in section 2**. |
| Coexists with | `research/in-flight/piano-jam-2026-09-14/jam-spec.md` (J0-J10, V2 waves), `research/in-flight/piano-spectacle-2026-09-13/spectacle-spec.md` (P0-P6, D8, Daniel's decisions), `research/in-flight/piano-suggest-lights-2026-09-14/suggest-lights-plan.md` and `fact-check.md` (SG0-SG9) |
| Measured in this pass | Scratch `theory-nextgen/spec/merge_lab.mjs` (read only, counts only) over the 844 real chord windows of S1-S6 used by the judges (1,942 s): the merged ALSO rule, the tighter cluster rule, name lengths. Judge scripts `theory-nextgen/judge/*.mjs` re-run: `cross.mjs`, `labels.mjs`. |
| Privacy | Chord names, numbers, number sequences, counts and durations only. Sessions are S1-S6. No session ids, clock times or transcriptions. Scratch outputs stay in the scratchpad. |
| Naming | Phases **TN0-TN11**, receipts **NG1-NG17**. Other docs' labels (N, D, T, SG, J, P) are cited only as sources. |

---

## 0. In one screen

**The same page, but right.** Next-gen barely changes the look Daniel loves. It makes every clip more truthful, and it
adds one new visual later.

What Daniel gets from this build:

1. **His chords get their real names in the hero label.** His favourite 4 reads `G♭maj13♯11` instead of `B♭m11/G♭`.
   The sus 5 reads as a 5 (`B♭13sus4`), the dominant 11 as a 5 with its 11, and altered dominants get names at last.
   His own vocabulary goes from 18/24 to 24/24 right.
2. **The name he learned stays visible.** When the old page name is still a fair reading of the same notes, the note
   line ends in a small `ALSO B♭m11/G♭`. On real windows this one line covers 61 of the 63 windows where the new name is
   the worse one.
3. **A steadier name.** One name per harmonic window instead of per note: pedal-aware, arpeggio-aware, bass-aware, and
   committed on a 250 ms settle. A chord that grows inside its window updates its suffix in place, with no pop.
4. **One caption in the Nashville row, by priority:**
   - the key change and its interval: `NEW KEY · G MAJOR · DOWN A HALF STEP`;
   - a function word where the row says "outside" today: `PULLS TO 6m`, `FROM A♭ MAJOR`, `BORROWED COLOUR`;
   - the scale when its colour note actually sounds: `IN D♭ MAJOR · G♭ LYDIAN`, with a small diamond under that note's
     chip.
5. **Nothing else enters the recording.** The HUD (never recorded) gains the ranked readings with plain reasons.

After the first night and a phone test: the **key ring** core in the side column (the palette's own fifths wheel, his
loops drawn as shapes, a swing on a sure key change). After that, a **Lesson** view that can put the ring and a roles
row into the frame for lesson clips.

Cut from this round, each with a measured or stated reason (section 5): tension steps, key-top scale capsules, staff
ghost lines, reading pins, the lean chevron, rest cards, the dual-key caption, the four-preset matrix and any new
hotkey.

| Measure (method: `design-engine.md` 1, re-run by the judges) | Page today | Next-gen |
|---|---|---|
| Synthetic fixtures named right (71 with an expected name) | 56 (51 exact) | **71 (67 exact)** |
| Daniel's vocabulary (24) / dominants (10) / rootless, quartal, polychord (5) / plain (32) | 18 / 4 / 2 / 32 | **24 / 10 / 5 / 32** |
| Real windows matching the offline name (983 windows) | 627 | **730** |
| Next-gen right and page wrong / page right and next-gen wrong | | **188 (568 s)** / 63 (107 s) |
| Live replay core agreement, six-session mean (oracle key; no key: 0.568) | 0.497 | **0.577** at 250 ms |
| Live replay time with no name | 25.1% | **13.4%** |
| Backdoor progression C C7 F B♭7 C | F major | **C major (sure)**, 2,872/2,872 node checks |
| Cost of one reading | 0.005-0.009 ms | 0.03-0.05 ms (0.076 ms worst) |

---

## 1. Decisions (where the designs and judges disagreed)

| # | Question | Decision | Why |
|---|---|---|---|
| D1 | Where does the engine live? | **One engine:** a new pure module `arsenal/web/piano/chordread.js`. It gets `Theory` injected, imports only `./nashville.js`, and exports `createReader` and `installReader`. The page installs it at integration (TN7). Node extractors get it through one loader, `theory_node.mjs`. The suggestion design's `readings.js` becomes an adapter over it. | The engine design put `Theory.read` inside the THEORY block, but `piano.js` belongs to the jam build (J9) now, so that phase could not start. A module injected with `Theory` lets TN0-TN4 start today in new files, and page and node run the same code by construction. One reader ends the three-way split (THEORY templates, practice readings, `readings.js`). |
| D2 | What commits the label? | **The live harmonic window (`harmony.js`, 250 ms settle) is the one commit clock.** The label, the rarity bloom, the suggestion engine's held chord and the log's chord event all key off its window id. `harmonySet` never names the label. | Measured: harmonySet core 0.444 at 81.5 changes a minute, the worst of the three pipelines. Pedagogy's "hold each chord" and the display's "label commit" both become this window, not a second tracker. |
| D3 | What is Classic? | **Classic = today's layout and captions, with names from the reader.** A receipt-only query `?engine=templates&chordName=every` reproduces the pre-build page byte for byte (NG10). It is never a setting. | Two engines running live would split the log from the screen. Keeping the 38 templates as `Theory.detectTemplates` costs nothing: they are the reader's fallback path, and ALSO needs them (D5). |
| D4 | Views and settings | **Theory view: Classic / Next-gen**, plus **Chord name: steady / every note**. A **Lesson** toggle arrives only with TN11. Top-bar select only, **no hotkey.** | Four presets, a custom state and 10 keys make a control panel for a player who wants to play. Only Backquote and Digit1/4/8 are free, suggestions took Backquote, and a digit slip mid-take could change the recorded view. |
| D5 | When does a second name show? | **Canvas ALSO = the "was" rule:** the template name (today's page name) when it differs in root or bass from the top reading **and** is itself a reading within 1.5 cost, held 1 s. **HUD only:** the close runner-up (leaning or ambiguous band, plausible, within 0.6). | Measured on 844 windows: the was-rule fires on 104 windows (294 s, 15% of chord time) and covers **61 of 63** loss windows. In every one of those 61 the ALSO name is the page's (= the offline) name. The close rule fires on 66 windows (195 s) and covers **0** losses. The display rule (0.6 / 1.5 known confusion) fired on 253 windows (591 s). The engine rule failed on his favourite chord: `Gbmaj13#11` is clear band, and `Bbm11/Gb` is not in its top 3. |
| D6 | What does "11" mean? | **`11` has its 3rd** (B♭11 = B♭ D F A♭ C E♭; `7(11)` without the 9). **`9sus4` has no 3rd.** G F A C is `F/G`, `ALSO`/HUD `G9sus4`, never `G11`. One lexicon entry. | The display doc's tables said `G11` for a no-3rd shape the engine names `G9sus4`. |
| D7 | Label defects the feasibility judge found | Fixed in TN1 before anything reaches the page: no-3rd family (A1), slash duplicates (A2), cluster (A3). | Each shows Daniel a confident wrong or ugly name: 21 clear-band no-3rd dominant tops (35 s), 24 duplicate runner-ups (41 s), `C D E F` read as `Dm9/C` (clear). |
| D8 | Who owns the Nashville row slot? | **Priority:** rarity banner, then `NEW KEY` caption, then function word, then scale caption, then `IN <key>`. One caption at a time. | Three docs plus spectacle, suggestions and the lean mark each claimed that row. Spectacle D8 (Daniel's decision) gives the banner the row. |
| D9 | Scale caption | **Recorded only when the character note sounds** (the display's naming gate) and the chord is a diatonic colour chord. The name is spelled in the key. Implied-tone scales go to the HUD. Suppressed while a function word shows. | 656 s of "Lydian" is mostly the key prior deciding a ♯11 nobody played; the canvas must not teach a mode he did not play. |
| D10 | Words in the row | Words come from **one lexicon** (`tests/fixtures/theory/lexicon.json`): plain word first, theory name second (dropped first on overflow). "Outside" stays only for real outsiders. | Three wordings existed for one idea ("5 of 6m", "SECONDARY DOMINANT (LEADS TO Am)", "pulls to 6m · secondary dominant"). |
| D11 | Key-change caption | Shown for 2.4 s on a tracker switch whose new key is not provisional and was not shown in the last 30 s. It waits at most 4 s behind a banner. | Minor-third and half-step changes are his signature move and the cheapest TikTok moment. The guard keeps I-I7-IV flip-flops (F, C, then F again) off the recording. |
| D12 | `(no3)` on his surfaces | **Never drawn in the big label or number.** The chip line says `NO 3RD`. The reading keeps the flag, and its band is capped at leaning. | Pedagogy: no `(no3)` or `^` on his surfaces. The fact must still show, so it moves into words. |
| D13 | Long grammar names | **Fit rule:** base size, else shrink to 0.8, else drop the bracketed natural tensions, keeping the altered ones. | Real top names: median 7 characters, p99 14, max 15 (`Ebm(maj9)(11)/D`, `Cm(add9,11)/Eb`, `Absus2(#11,13)`). No doc measured a 170 px fit. |
| D14 | Flicker numbers | Every flicker receipt is scored **after the replay is calibrated to the logged page** (±15%), per minute of chord-window time. | Logged live labels average 147.5 changes a minute (S1 140, S6 394), while the replay of the same page gives 59.7 on the same denominator. "49 against 60" was measured against a replay that under-counts by 2.5x. |
| D15 | Tracker scope | **In:** backdoor patch and "a dominant heading home decides nothing" (both twins), and an additive `candidate.needSec`. **Out:** the dual-key `C or F` caption, the vamp-parent candidate, "Numbers from the centre". `centreOf` goes to the HUD only. | The patch is measured (2,872/2,872). The rest is unmeasured against the suite; the centre fires on 0 of 23 real key areas; a `C or F` caption on a clip reads as the page not knowing. |
| D16 | Key ring | **Core only, after the first night:** numbered nodes, the lit node in its root's pitch colour, a 6-segment fading trail, a 600 ms swing. It lives in the unrecorded side column; in-frame only in Lesson after a phone test. The swing needs a sure switch and never swings back within 30 s. | It is the one idea that is both beautiful and a real lesson (the hue wheel is 200° + 30° per fifth, `piano.js` 307). But it amplifies tracker errors on camera, and the 9:16 fit is 8 px from TikTok's buttons. |
| D17 | Teaching surfaces | Pedagogy's steps T2-T5 are **hard-gated** on NG2 and NG13 green and the first night held. Study stays in chat (`practice brief`, `riff`) this round. | Pedagogy 11.1: teaching through wrong names repeats the wrong family with more confidence. |
| D18 | Rarity names | **Rarity reads the structured reading** (base, tensions, bass) through `parseSuffix`, not a suffix string table. jam-spec V2-F ("Names") is absorbed by TN1 + TN5 + the spectacle owner's adapter. | Spectacle's `COLOUR[info.suffix]` and its "every TEMPLATES suffix has a COLOUR entry" test assume a closed list. The grammar's list is open. |

---

## 2. Engine

### 2.1 The reader (`chordread.js`)

**Grammar, cost model, bands and tags** follow `design-engine.md` 3.1, 3.2 and 4.1-4.5 (prototype `engine.mjs`, 263
lines), with these amendments:

| # | Amendment | Rule | Fixture that proves it |
|---|---|---|---|
| A1 | **No-3rd family.** Today the no-3rd path exists only on dominant, maj7 and major bases, so a no-3rd minor seventh is forced into the dominant family. | A reading with its 3rd omitted takes the **key's diatonic 3rd above its root** for its quality whenever the key is sure, fair, locked or the jam key. With no key, its family is `open`, it gets no number and no scale. `no3` or `rootless`, or a bass on the 7th under altered tensions, caps the band at `leaning`. | `C3 G3 Bb3` in E♭ major reads `Cm7(no3)`, band at most leaning, number `6m⁷` with `NO 3RD`. In F major it reads `C7(no3)`. |
| A2 | **Slash duplicates.** | Drop a slash-path reading whose bass is the 6th, ♭7 or 7th above its upper root when a full-path reading on that root exists (it is the same chord in inversion). If none exists, rename it to the inversion. | `Ab2 Eb3 C4 D4 F4 Bb4` in E♭: `Bbadd9(11)/Ab` is gone from the list and `Bb11/Ab` is in the top 3 (tune the inversion cost if it is not). |
| A3 | **Cluster.** | **Tag:** 3 adjacent notes two semitones apart in a row, or 4 adjacent notes each a step or less apart with at least one semitone (in scratch `merge_lab.mjs`). **Kind:** 4 or more notes spanning at most 5 semitones with an adjacent semitone are `kind: "cluster"` in any band, and the label draws letters as today. The clear-band rule no longer hides a true cluster. | `C4 D4 E4 F4` is a cluster (today `Dm9/C`, clear). `C3 D3 E3 G3` stays `Cadd9`. |
| A4 | **11 against 9sus4** | As D6, in the grammar's suffix rules and the lexicon. | `G2 F3 A3 C4` in C: top `F/G`; `G9sus4` is in the readings; no `G11` anywhere. |
| A5 | **Loss tuning round** | Retune the b13-over-minor, minor-over-its-3rd and 6/9-inversion costs, checked in both directions on the real windows. | NG2: losses at most 63, of which at most 8 in the clear band (measured 16, 25.9 s). |
| A6 | **Honest calibration** | Bands are reported twice: over all windows, and excluding windows with a single reading. | NG2: clear-band agreement at least 0.93 in both. |
| A7 | **Spelling** | Every root the reader, scale view or function labeller prints is spelled with `spellInKey`. | 0 scale roots spelled against the key (the prototype printed `A# Lydian`, `D# Aeolian` in G major). |

**The ALSO selector** (D5), pure and node-tested:

```
alsoOf(result, templateInfo, heldMs):
  if heldMs < 1000 or templateInfo.kind !== "chord": return null
  t = ident(templateInfo.name); top = result.readings[0]
  if norm(t) === norm(identOf(top)): return null
  if root(t) === top.root and bass(t) === top.bass: return null          // a suffix difference only: not a second chord
  r = result.readings.find(x => norm(identOf(x)) === norm(t))
  return r && r.cost - top.cost <= 1.5 ? { name: templateInfo.name spelled in key, kind: "was" } : null

closeOf(result, heldMs):                                                // HUD only
  if heldMs < 1000 or result.band === "clear": return null
  first of readings[1..3] with a different root or bass, cost <= top + 0.6, and path not in {slash with a colour-tone
  bass (b9, 9, #11, b13), slash duplicate, drop}, and flags without no3 or rootless
```

Lab voicings (merge lab, current prototype costs; NG3 requires exactly these):

| Notes | Key | Big name | Band | Canvas ALSO |
|---|---|---|---|---|
| `Gb2 Db3 F3 Ab3 Bb3 C4 Eb4` (his favourite 4) | D♭ | `G♭maj13♯11` | clear | `B♭m11/G♭` |
| `Ab2 Eb3 G3 C4 D4 F4 Bb4` (blooming chord) | E♭ | `A♭maj13♯11` | clear | `Cm11/A♭` |
| `Ab2 D3 G3 Bb3 C4` | E♭ | `A♭maj9♯11` | ambiguous | `B♭13/A♭` (the gospel 5 over 4) |
| `Ab2 Eb3 C4 D4 F4 Bb4` | E♭ | `A♭6/9♯11` | leaning | `B♭11/A♭` |
| `C2 Bb2 F3 A3 D4` | F | `C13sus4` | ambiguous | `B♭maj7/C` |
| `Bb2 Ab3 C4 Eb4 G4` | E♭ | `B♭13sus4` | ambiguous | `A♭maj7/B♭` |
| `G2 F3 B3 Ab4` | C minor | `G7♭9` | clear | `Fdim/G` |
| `G2 F3 A3 C4` | C | `F/G` | ambiguous | none on canvas (template name equals top); HUD close: `G9sus4` |

### 2.2 Interfaces

```js
// arsenal/web/piano/chordread.js (pure; imports ./nashville.js only; Theory is injected)
export const READER_API = "arsenal.piano.chordread/v1";
export function createReader({ Theory, NV }) -> {
  read(notes /* [midi] | [{midi, w}] */, { key, prev /* {root} */, bassMidi, allowRootless = true })
    -> { kind: "chord" | "cluster" | "small", readings: [Reading], band: "clear" | "leaning" | "ambiguous" | "none",
         margin, confidence, tags: [{ tag: "upper structure" | "polychord" | "quartal" | "cluster", ... }] },
  alsoOf(result, templateInfo, heldMs) -> { name, kind: "was" } | null,
  closeOf(result, heldMs) -> Reading | null,
  detect(midiNotes, keyBias) -> info   // today's info shape from the top reading, plus info.readings, info.band,
                                       // info.tags, info.no3; kind "cluster" drawn as today
}
// Reading = { root, suffix, bass, name, cost, p, reasons: [plain strings], base: { id, family }, tensions: [semis],
//             omit: { no3, no5, rootless }, path: "full" | "slash" | "drop" | "template" }
export function parseSuffix(suffix) -> { tones: { [semis]: letterSteps }, family, dominant, tensions }
export function installReader(Theory, NV)
  // Theory.detectTemplates = the original detect; Theory.read = reader.read; Theory.detect = reader.detect
  // (the signature and info shape are unchanged, so every existing caller keeps working)

// arsenal/web/piano/theory_node.mjs (node only): slice THEORY from piano.js, import nashville.js and chordread.js,
// installReader, export { Theory, NV }. The one loader for practice_theory.mjs, pianocue_voicing.mjs,
// suggest_bridge.mjs and the tests.
```

### 2.3 The live window (`harmony.js`)

This is `design-engine.md` 7.1 (onset groups of 50 ms, 700 ms heard extension, 700 ms silence split, new-bass split,
lagged split test at 400 and 900 ms with the pedal discount, 20% chord share, 10 Hz naming, previous-root prior), with
these amendments:

| # | Amendment |
|---|---|
| H1 | **Window-local buffer.** Keep onset groups from the window start plus a 900 ms tail. The prototype's `pipelineLive` rescanned every note since the session began for each onset group (O(N²)). |
| H2 | **Daniel's notes only.** `noteOn(midi, vel, t, source)` ignores every source except Daniel's MIDI, computer keys and Demo. Claude's cues, replays and ghosts never enter (INT invariant 1). |
| H3 | **Two kinds of change.** `changed: "new"` (a new window) commits the label with its pop. `changed: "grow"` (the same window, a richer reading) updates the name in place: no pop, no new trail segment, and rarity treats it as `upgradeOf`. |
| H4 | **Event time, not timer time.** Boundaries come from event timestamps, so a hidden tab (timers throttled to 1 Hz, fact-check 1) yields the same windows and log events. |
| H5 | **Reader inputs:** the shown key (`keyView`), the previous window's root, per-note salience (`design-engine.md` 4.2), and the window's bass. |

```js
// arsenal/web/piano/harmony.js (pure)
export function createHarmonyTracker({ reader, settleMs = 250, heardMinMs = 700, groupMs = 50, silenceMs = 700,
  penaltyMs = 600 }) -> {
  noteOn(midi, vel, t, source), noteOff(midi, t), soundEnd(midi, t), pedal(down, t),
  tick(t, key) -> { window: { id, startT, pcs, salience, bassMidi, heldMs }, reading /* read() result */,
                    also /* alsoOf */, changed: "none" | "grow" | "new", upgradeOf, stats } }
```

The **Chord name** setting picks what drives the label:
- **steady** (recommended, Q3) uses `harmony.js`;
- **every note** keeps today's clock (120 ms after a note-on, 300 ms after a release, over everything sounding), still
  named by the reader.

The log's chord event follows the same setting.

### 2.4 Scales (`scales.js`)

This is `design-engine.md` 8.1 (28 scales on the chord root, family prior, chord tones hard, key prior for unplayed
tones, hysteresis of 0.35 for 1.5 s on the same root), with these changes:

- **Naming gate** (from the display): the character note must be in the window's heard pitch classes, or struck in the
  last 2 s over the same reading.

  | Mode | Character note |
  |---|---|
  | Lydian | ♯4 |
  | Mixolydian | ♭7 |
  | Dorian | natural 6 over a minor 3rd |
  | Aeolian | ♭6 |
  | Phrygian | ♭2 |
  | Locrian | ♭5 |
  | Lydian dominant | ♯4 and ♭7 |
  | melodic minor | natural 6 and 7 over a minor 3rd |

- **Every result says which tones are implied:** `{ name, rootName, set, character, sounded: bool, implied: [pc] }`.
- **`centreOf`** (D Dorian and the like) is computed for the HUD and Study only.

```js
export function rankScales(chordPcs, weights, root, keyName) -> [{ name, rootName, score, set, character, sounded, implied }]
export function createScaleView({ margin = 0.35, holdMs = 1500 }) -> { update(ranked, t, sameWindow) }
export function namingGate(scale, heardPcs, recentPcs) -> boolean
export function centreOf(chords /* [{root, family, seconds}] */, keyName) -> { root, mode, share, tonicShare } | null
```

### 2.5 Function labels, the pivot rule and the tracker patch

**`function.js`** (pure) has a Python twin, `arsenal/harmony_function.py`, and follows the labels of
`design-engine.md` 9.7:
- diatonic;
- secondary dominant, with whether it lands;
- backdoor;
- tritone substitute;
- passing diminished;
- from the old key (the pivot rule, 9.3: 8 s, or until the new tonic has sounded 1.5 s);
- borrowed;
- modal colour;
- chromatic.

It returns lexicon ids, not strings:

```js
export function functionOf({ window, prev, next, area /* {key, since} */, prevArea }) -> { label, target, lexId, detail }
```

**Gospel 5 over 4 against the Lydian 4** (`design-engine.md` 9.9):
- **Live:** the label shows the reading.
- **Log and practice summary:** they take the reading the next window confirms (the bass steps down to the 3: the 5
  over 4).
- **Label:** it swaps in place (H3) only while the window still sounds.

**Tracker** (`nashville.js` and `nashville.py`, TN5):
- **The two rules of `design-engine.md` 9.6:**
  - a backdoor cadence is an arrival;
  - a dominant heading to an I7's root decides nothing until it lands.
- **An additive field:** `state.candidate.needSec` (`holdSec`, doubled within `RECENT_SEC`).
- **Python twin:** `performance.numbering_key` gets the same two rules.

**Left open for the tracker owner, not built here:**
- `C E7 Am F` reads A minor (sure);
- Dorian vamps are numbered in the IV's key;
- a pedalled chord struck once earns only 1.5 s of playing time (`ACTIVE_SEC`), so slow held playing gets its key late.

### 2.6 Test corpus (created in TN0, frozen after; changes go through the conductor)

| File | Contents | Size |
|---|---|---|
| `tests/fixtures/theory/chord_readings_cases.json` | The 73 prototype voicings; the judges' defect voicings (`C3 G3 Bb3` in E♭ and in F, `C4 D4 E4 F4`, `C3 G3 Bb3 D4`, the gospel 5 over 4, `G2 F3 A3 C4`); the 8 ALSO lab voicings of 2.1; the suggestion chips' voicings from `fact-check.md` 5 (`Dbmaj9/F`, `Ab9/Gb`, `Gdim7` must read as themselves); the 17 seed cards' full slots from jam-spec 12 in their card keys; 12-key transpositions of Daniel's 24. Each case: notes, key, expected name, accepted alternatives, expected band ceiling, expected canvas ALSO, tags. | at least 180 cases |
| `tests/fixtures/theory/scale_cases.json` | The 11 scale cases; implied-only cases (Abmaj9 in E♭ with no D: gate closed); the three vamps and his D♭ loop for `centreOf` | at least 20 |
| `tests/fixtures/theory/function_cases.json` | Synthetic progressions: V7-I, a secondary dominant landing and one not landing, backdoor, iv-♭VII7-I, tritone substitute, passing ♯i°7, borrowed 4m, ♭6, ♭7, modal ♭VII, a chromatic outsider, the 9 no-pause key-change shapes as number sequences (`design-engine.md` 9.3), gospel 5 over 4 resolving and not resolving | at least 40 |
| `tests/fixtures/theory/window_sessions/*.json` | Synthetic note streams with his profile (note gaps p25/50/75 of 190/250/400 ms, pedal down 60-95%, arpeggios under pedal, walking bass under held hands, block strikes), with the expected window boundaries | at least 12 |
| `tests/fixtures/theory/lexicon.json` | Every word the row, chip line, HUD and practice verbs may print: `{ id, plain, theory, meaning }`, plus the guard list (never "wrong", "mistake", "error", "should", "correct", "best", "score", "%") | section 3.2 rows plus `design-pedagogy.md` 6.2 |
| `tests/fixtures/nashville_cases.json` (existing, TN5 edits) | New scenarios: backdoor, Fm7-B♭7-Cmaj7, F blues unchanged, `candidate.needSec` | +6 |

Real-session lanes read `py -m arsenal.practice analyze <session> --json` read only. They print counts, seconds and
chord or number sequences only, and nothing from a real session is written to a tracked file.

---

## 3. Display

### 3.1 Play surface: what is drawn, where, when

Reference pixels: 1080 × 1920 (9:16) and 1920 × 1080 (16:9), as `LAYOUT` in `piano.js` 1091.

| Element | 9:16 box | 16:9 box | Recorded | Classic | Next-gen | When it changes |
|---|---|---|---|---|---|---|
| Big chord name | label layer y 148-488, glyphs ≈ 205-365, 170 px | y 41-351, 140 px, left | yes | reader name | reader name | on a window `new` commit (pop); `grow` updates in place |
| Note chips | chip line baseline ≈ 427 | baseline ≈ 287 | yes | as today | as today | live, note by note |
| `NO 3RD` | chip-line caption slot (today's `info.sub`), small × 0.72, caps, ink 0.55 | same | yes | yes | yes | with the name |
| `ALSO <name>` | caption slot, after `NO 3RD` | same | yes | no | yes | 1 s into the window; one label-layer redraw, no fade |
| Character-note diamond | 8 px vector diamond, ivory 0.8, centred under the character note's chip, centre y ≈ 443 (inside the label layer) | centre y ≈ 301 | yes | no | yes | with the scale caption |
| Nashville row | `nns` layer y 471-601, number 76 px, caption 26 px | y 332-452, 64 / 22 px | yes | `in` / `outside <key>` | caption by 3.2 | caption changes swap on commit; the row's existing opacity path handles the banner crossfade |
| Grand staff | unchanged | unchanged | yes | unchanged | unchanged | |
| HUD theory line | DOM | DOM | never | yes | yes | per window |

Rules every element obeys:
- **Motion only at a change.** Nothing theory-related moves while a window holds.
- **No new hues, no new light.** Ivory ink after bloom, never in `LIGHT_BUDGET`.
- **No per-frame texture redraws.** Text changes redraw their layer once; fades use layer material opacity.
- **Daniel's alone.** Claude's notes never reach any of it.

### 3.2 The Nashville row caption

Grammar: `<number>   <plain> · <theory> · <key phrase>`. The number is drawn with superscripts, as today. `<theory>`
is drawn at 0.42 alpha. Overflow drops `<theory>` first, then `<key phrase>`.

| Priority | Situation | Caption (lexicon ids) | Example |
|---|---|---|---|
| 0 | Rarity banner holds the row (spectacle D8) | the banner, which carries the number | `EPIC · A7♭9 · 3⁷♭⁹` |
| 1 | Tracker switch (D11), for 2.4 s; waits at most 4 s behind a banner, else dropped | `NEW KEY · <key> · <interval>` | `NEW KEY · G MAJOR · DOWN A HALF STEP` |
| 2 | From the old key (pivot rule) | `FROM <old key> · IN <key>` | `♭3⁶ᐟ⁹/5   FROM A♭ MAJOR · IN G MAJOR` |
| 2 | Secondary dominant | `PULLS TO <target> · SECONDARY DOMINANT · IN <key>` | `3⁷   PULLS TO 6m · SECONDARY DOMINANT · IN C MAJOR` |
| 2 | Backdoor | `PULLS HOME · BACKDOOR · IN <key>` | `♭7⁷   PULLS HOME · BACKDOOR · IN C MAJOR` |
| 2 | Tritone substitute | `SLIDES TO <target> · TRITONE SUB · IN <key>` | `♭2⁷   SLIDES TO 1 · TRITONE SUB · IN C MAJOR` |
| 2 | Passing diminished | `PASSING · IN <key>` | `♯1°⁷   PASSING · IN C MAJOR` |
| 2 | Borrowed | `BORROWED COLOUR · FROM <parallel key> · IN <key>` | `4m⁶   BORROWED COLOUR · FROM E♭ MINOR · IN E♭ MAJOR` |
| 2 | Modal colour | `BORROWED COLOUR · <mode> · IN <key>` | `♭7   BORROWED COLOUR · MIXOLYDIAN · IN C MAJOR` |
| 2 | Chromatic | `OUTSIDE <key>` (today's words) | `♭5   OUTSIDE C MAJOR` |
| 3 | Diatonic colour chord, scale passes the gate, 700 ms after the window settles | `IN <key> · <scale root> <mode>` | `4maj13♯11   IN D♭ MAJOR · G♭ LYDIAN` |
| 4 | Otherwise | `IN <key>` (today) | `1maj9   IN E♭ MAJOR` |

Gates:
- **Key unsure:** the row dims as today. Only priorities 1 and 4 show, plus `FROM`, which is tied to the switch itself.
- **No key:** "listening for the key" (today).
- **Scale caption:** never the key's own Ionian over 1 or Aeolian over a minor tonic.
- **Loop or Try run:** numbers follow the jam key (jam-spec 8.10), and priority 1 is off because the key is locked.
- **Classic:** today's `in` / `outside` only.

### 3.3 The HUD line (DOM, never recorded)

```
theory · Gbmaj13#11 clear (bass is the root; #11: the Lydian colour; every note in Db major)
       · 2 Ebm13(11)/Gb +0.95 · 3 Dbmaj13/Gb +1.15 · also (was) Bbm11/Gb · close: none
       · Gb Lydian (C sounded) · centre: none · fn diatonic · window 1841 1.6 s · Db major sure · next Ab 2.1/5 s
```

### 3.4 Settings, storage, overrides

| Setting | Values | Default | localStorage |
|---|---|---|---|
| Theory view (top-bar select in the theory group, `blur()` after change) | Classic / Next-gen | **Classic until Daniel answers Q2; then his answer** (recommended: Next-gen) | `arsenal.piano.theory.view` |
| Chord name (same group) | steady / every note | **steady** (Q3) | `arsenal.piano.theory.chordName` |
| Lesson (TN11 only) | off / on | off | `arsenal.piano.theory.lesson` |
| Key ring (TN10 only) | off / side | side once built | `arsenal.piano.theory.ring` |

- **Query overrides** (receipts only, never stored): `?theory=classic|nextgen`, `?chordName=steady|every`,
  `?engine=templates`.
- **REC** never changes a setting.
- **No hotkey.**
- **Receipt hook:** `window.__piano.theory = { reader, harmony, view, frame(), layout(), stats() }`.

### 3.5 Coexistence

| Neighbour | Rule |
|---|---|
| Rarity (spectacle P1-P4) | The bloom is the harmony window. A score commits on `new` and upgrades on `grow`. `intrinsic()` reads `reading.base`, `reading.tensions` and `reading.bass` through `parseSuffix`, so the grammar's open suffix list needs no table edit. The spectacle test "every TEMPLATES suffix has a COLOUR entry" becomes "every base and tension family has a colour". The row's `nnsCover()` covers the whole caption. |
| Legendary foil (E11) | Samples the name glyph line only. The diamond and caption slot never get foil. |
| Jam (J9 landed) | Try `found` stays pitch-class containment (`transport.js`, unaffected). Card "reads as" lines (`page_reads` from `pianocue_voicing.mjs`) switch to the reader through `theory_node.mjs`. Jam receipt A4's exception list ({`one-note-apart` a slot 1, c slot 1, `blooming-chord` slot 4}) is re-derived and may shrink; tell the jam owner. The label stays Daniel's during runs (C11). |
| Suggestions (SG1-SG7) | `readings.js` is an adapter: `readHeld({ midis, bassMidi, key, reader })` maps `reader.read()` to `{core, number, suffix, rootPc, bassPc, bassDegree, cost, pcs}`. SR1's parity target becomes `chord_readings_cases.json`. The "the label calls it" line disappears once TN7 lands, because both use the same reader. Held-chord gates key off the window id. |
| Glass, deck, pill, toast | Untouched this round. |
| Demo, computer keys | The label follows them as today; rarity exclusions unchanged. |
| Hidden tab | `harmony.js` runs on event time (H4). `catchUp` brings the label up to date. |

### 3.6 Later: the key ring core (TN10) and the Lesson view (TN11)

**Ring core** (from `design-display.md` 3.5):
- **Geometry:** twelve positions a fifth apart, numbered in the key, 1 at 12 o'clock; the key window arc behind the
  seven diatonic nodes; the centre letter.
- **The current node** fills with its root's pitch colour (`noteCss`, lightness floor 0.68).
- **Trail:** 6 segments, one per `new` window commit, alpha 0.55 · 0.5^(age / 2.5 s), with repeat etching capped at
  0.7.
- **Key switch:** the content swings the shorter way in 600 ms (3 fifths for his minor-third drop, 5 for his half-step
  drop).
- **Swing gate:** the switch is `sure`, and no swing back to a key shown in the last 30 s.
- **Placement:** the left side column (DOM, never recorded), stacked under the suggestion chips, `min(240, column − 24)`
  px. Hidden when the margin is under 220 CSS px.
- **Not built:** home caret, pull ticks, hollow "could lean" ticks, the candidate window, visited-number labels,
  click-to-play nodes, tension steps.

**Lesson view** (after a phone test and Daniel's ask):
- the ring in frame (9:16 x 636-908, y 664-936 with the staff narrowed to x 110-620; 16:9 x 968-1216, y 156-404);
- the roles row as its own layer at 9:16 y 440-470 (the box the lab actually tested; the doc's 438-472 overlaps the
  `nns` box);
- design-display receipts D-R2, D-R3 and D-R12 before either reaches a recording.

---

## 4. Play and Study

| Moment | Surface | Shows | Never shows |
|---|---|---|---|
| **Play: the recording** | canvas | name (reader, steady window), chips, `NO 3RD`, `ALSO` (was), the row's one caption, the diamond with the scale caption, the staff as today | alternative lists, reasons, costs, bands, counts, `^`, `(no3)`, tension, anything that moves while a chord holds |
| **Play: for his eyes only** | HUD, glass, DOM | the HUD theory line; suggestion chips (their rules); the ring in the side column (after TN10) | new marks on keys this round |
| **Study, this round** | chat: `py -m arsenal.practice brief` and `riff`, through the reader (TN8) | tonight in numbers from the practice windows; function words from the lexicon (plain first); "your 4 wears these colours"; "same move in N keys" as counts from the windows JSON; one question, one try (riff rules) | percentages, scores, clock times on Daniel's surfaces |
| **Study, next** (pedagogy T3-T4, gated by D17) | deck Study tab after V2-B | `design-pedagogy.md` 4.3, lean line, shape shelf | before NG2, NG13 and TN9 |

Words:
- Every string on the canvas, the HUD's plain half and the practice verbs comes from `lexicon.json`.
- Scale and key names are addresses, not face words, so `G♭ LYDIAN` is allowed on the row. The plain gloss ("the bright
  4") lives in chat and Study.
- "Another name for the same notes" replaces "reading" wherever Daniel reads.

---

## 5. Cut or deferred

| Item | Status | Reason | Revisit when |
|---|---|---|---|
| Tension steps and the T formula | cut | Reads as a meter to a viewer (spectacle D12 cut in-canvas gauges). Pull = 1 only for dominants with a 3rd, which are 4% of his chord time; his tension is sus floats (32 windows, 55 s) and ♯11 rubs, so it would sit flat and teach "lush = calm". Weights were illustrative. | a Study-only design with ingredients shown separately (pedagogy 8.1) |
| Scale capsules and note-class marks on key tops | cut | Keys already carry pitch light, ghost rims, moonlight, suggestion ghosts and Try targets; back-edge visibility is unmeasured | after jam and suggestion ghosts ship, with one follow-camera snapshot |
| Voice-leading ghost column and lines on the staff | deferred | About 49 or more commits a minute with 1.8 s per ghost means ghosts almost always on screen; the staff is a canvas texture, so every commit re-uploads it (fails D-R12) | Lesson view, own layer, measured uploads |
| Reading picker and pins | deferred | Pins split the screen from the log, rarity and suggestions; a learner cannot yet choose; ALSO and the HUD show both names | after the lexicon and ALSO settle |
| Lean-and-land chevron | cut | Duplicates the function words and the ring; gated off while the key is unsure (11-33% of time), during pending changes and while he plays fast, so it rarely shows | fold its "landed" pulse into ring TN10 if missed |
| Rest cards | deferred | Fight the banner slot (spectacle D8), distract mid-take, and need the names fixed first | after TN9, with the spectacle owner's slot agreement |
| Dual-key caption `C or F major` | cut | Reads as the page not knowing; dimming is the honest version; unmeasured against the suite | a measured chord-level tracker experiment |
| Home caret, `centreOf` on canvas, "Numbers from the centre" | HUD only | Fires on 0 of 23 real key areas | real vamps appear in his sessions |
| Vamp-parent tracker candidate, scale-fit tracker term | out | Scale fit fails 5 checks at weight 0.3 and 18 at 0.6, fixing neither vamp; vamp parent unmeasured | tracker owner's own experiment |
| Candidate-key dashed window, `TOWARD` caption | deferred | 0.25 alpha unreadable on a phone; needs `needSec` (added in TN5, HUD first) | ring Lesson view |
| Four presets, custom state, Digit1 | cut | D4 | never |
| Display doc tables 3.2 and 3.7 | superseded | Built on guessed template costs that disagree with the engine | replaced by section 2.1 and NG3 |

---

## 6. Phases and file ownership

### 6.1 Gates, as of 2026-09-14

| Build | State in the worktree today | This spec needs |
|---|---|---|
| Jam B1-B3 (cue channel, practice verbs, Nashville and log fixes) | `practice.py`, `log.js`, `cues.js`, `pianocue*.{py,mjs}`, `serve.py` modified, uncommitted | B2 landed before TN8; B3 landed before TN5 |
| Jam J0-J8 | `arsenal/jam/*`, `deck.js`, `glass.js`, `transport.js`, `groove.js`, `tempomap.js`, `practice_riff.py` exist, untracked | nothing (TN7 touches none of them) |
| Jam J9-J10 | not started (`piano.js` unmodified) | J9 committed and J10's first night held before TN7 |
| Spectacle P0-P2 | not started in `piano.js` | P2 committed before TN7 (the banner slot and `nnsCover` exist) |
| Suggestions SG0-SG4 | new files, may start now | SG1 builds `readings.js` as the adapter (6.4) |
| Suggestions SG5, SG7 | wait for jam | SG5 before TN8 (`practice.py`); SG7 in a different `piano.js` wave from TN7 |

Rules, from jam-spec 13.1:
- **Owners:** one owner per existing file per wave; new files belong to their creating phase.
- **Locks:** advisory locks on owned existing files.
- **Commits:** worktrees, with Vandor the sole committer.
- **Tests:** test files namespaced per phase.
- **Ports:** live checks on the phase's own port, never 8793 or 8795-8798; TN7 uses 8801 and TN10 uses 8802.

### 6.2 Phases

| Phase | Starts | Depends on | Scope | Exit |
|---|---|---|---|---|
| **TN0 Contracts and corpus** | now | none | the 2.6 fixtures; lexicon; `Reading` and `TheoryFrame` shapes frozen in module headers | fixtures validate; lexicon guard passes on its own strings |
| **TN1 Reader** | now | TN0 | `chordread.js` (grammar, costs, A1-A7, bands, tags, `alsoOf`, `closeOf`, `parseSuffix`, `installReader`); the real-window lane | NG1, NG2, NG3 |
| **TN2 Live window** | after TN1 | TN1 | `harmony.js`; `harmony_replay.mjs` with the page pipeline calibrated first | NG5 |
| **TN3 Scales** | after TN1 (parallel with TN2) | TN1 | `scales.js` | NG6 |
| **TN4 Function and row** | after TN1 (parallel) | TN1 | `function.js`, `harmony_function.py`, `theoryrow.js` (the pure caption composer of 3.2: priority, drop order, lexicon ids to runs) | NG8, NG9 |
| **TN6 Node loader** | after TN1 | TN1 | `theory_node.mjs`; parity test against the page slice | loader parity: `Theory.detectTemplates` equals today's `Theory.detect` on every fixture |
| **TN5 Tracker, suffix and log twins** | after B3 lands | TN1, TN4 | `nashville.js`: the two rules, `needSec`, `parseSuffix` replacing the hand tables `FAMILY`, `TONE_STEPS`, `DOMINANT`. `nashville.py` twin. `performance.py`: `numbering_key` rules; summary function words through `harmony_function.py`; chord event accepts additive `reading`, `band`, `scale`, `function`, `window` (server first). Not in the same wave as spectacle P4 (`performance.py`). | NG4, NG7 |
| **TN7 Page integration** | its own `piano.js` wave | J9 committed, J10 held, spectacle P2 committed, TN1-TN6 committed; not with SG7 or a V2 integration step | `piano.js`: import and `installReader`; `harmony.js` in `noteOn`, `noteOff`, `soundEnd`, pedal, `renderFrame`; label, chip caption, diamond, row via `theoryrow.js`; HUD; rarity commit and `intrinsic` adapter hook; log fields; settings; `__piano.theory`. Plus `piano.html` selects, `piano.css`, and `arsenal/lanes/theory_verify.mjs`. | NG10-NG14 |
| **TN8 Practice through the reader** | its own `practice.py` wave | B2 landed; J4 and SG5 committed; TN5 | `practice_theory.mjs` loads `theory_node.mjs`; `practice.py` naming through the reader, retiring `extended_readings` and `choose_reading` behind the same verbs; pivot and function words in `brief`, `borrowed`, `colors` | NG15 |
| **TN9 First night** | after TN7 (TN8 recommended) | TN7 | Vandor tells Daniel in chat first ("same notes, clearer name: your 4"); 20 minutes Next-gen with steady names, then 5 minutes every-note; one TikTok test clip on his phone; his answers to Q1-Q3 | NG16 |
| **TN10 Ring core** | after TN9 | TN5, TN9 | `ringmodel.js` (pure), `ringview.js` (DOM side column), `ring-test.html`; `piano.js`, `piano.html`, `piano.css` in their own wave | NG17 |
| **TN11 Lesson view** | Daniel asks, after TN10 | phone test | roles row layer and ring in frame per 3.6; D-R2, D-R3, D-R12 | design-display receipts |
| Pedagogy T2-T5 | gated | NG2, NG13 green; TN9 held; V2-B for the deck tab | `design-pedagogy.md` 12, minus the lean chevron and rest cards (section 5) | W1-W8 |

Rough size, for planning only:
- TN0: half a day.
- TN1: a day and a half (A1-A5 tuning included).
- TN2: a day.
- TN3, TN4, TN6: half a day each.
- TN5: a day.
- TN7: a day and a half.
- TN8: a day.
- TN10: a day.

### 6.3 Who owns which file

`N` = creates, `E` = edits an existing file, blank = read only.

| File | TN0 | TN1 | TN2 | TN3 | TN4 | TN5 | TN6 | TN7 | TN8 | TN10 |
|---|---|---|---|---|---|---|---|---|---|---|
| `tests/fixtures/theory/*.json` (incl. `lexicon.json`) | N | | | | | | | | | |
| `arsenal/web/piano/chordread.js`, `tests/theory_chordread.test.mjs`, `arsenal/lanes/theory_static.mjs` | | N | | | | | | | | |
| `arsenal/web/piano/harmony.js`, `tests/theory_harmony.test.mjs`, `arsenal/lanes/harmony_replay.mjs` | | | N | | | | | | | |
| `arsenal/web/piano/scales.js`, `tests/theory_scales.test.mjs` | | | | N | | | | | | |
| `arsenal/web/piano/function.js`, `theoryrow.js`, `arsenal/harmony_function.py`, `tests/theory_function.test.mjs`, `tests/test_arsenal_theory_function.py` | | | | | N | | | | | |
| `arsenal/web/piano/nashville.js`, `arsenal/nashville.py`, `tests/fixtures/nashville_cases.json`, `tests/nashville_js.test.mjs`, `tests/test_arsenal_nashville.py` | | | | | | E | | | | |
| `arsenal/performance.py`, `tests/test_arsenal_performance.py` | | | | | | E | | | | |
| `arsenal/web/piano/theory_node.mjs`, `tests/theory_node.test.mjs` | | | | | | | N | | | |
| `arsenal/web/piano.js`, `piano.html`, `piano.css`, `arsenal/lanes/theory_verify.mjs` | | | | | | | | E / N | | E (own wave) |
| `arsenal/practice.py`, `arsenal/practice_theory.mjs`, `tests/test_arsenal_practice.py` | | | | | | | | | E | |
| `arsenal/web/piano/ringmodel.js`, `ringview.js`, `ring-test.html`, `tests/theory_ring.test.mjs` | | | | | | | | | | N |

**Edits by other owners, in their own windows** (a one-line import swap to `theory_node.mjs`, or an adapter):

| File | Owner | Change | When |
|---|---|---|---|
| `arsenal/pianocue_voicing.mjs` | J1 (landed), then SG9 | slice loader to `theory_node.mjs`, so `page_reads` uses the reader | after TN6, not in the SG9 wave |
| `arsenal/suggest_bridge.mjs`, `arsenal/web/piano/readings.js` | SG4, SG1 | adapter over `createReader` (3.5) | SG1 if not yet built, else SG7 |
| `arsenal/web/piano/rarity.js`, its fixture | spectacle P1 (or P4) | `intrinsic()` through `parseSuffix`; colour by base and tension family | before TN7, or in spectacle's next wave |
| `arsenal/jam/seed/deck-v1.json` "Page reads" lines, jam A4 exception list | J6 / jam conductor | re-derived with the reader | after TN6 |

### 6.4 Notes to other owners (Vandor sends these)

- **Suggestions (SG1):**
  - `readings.js` is this reader's adapter; `readHeld` gains `reader`. Fact-check 5's concern (a cheapest-reading
    twin reads `Dbmaj9/F` as `Fm7b13`) is covered by the chip voicings in `chord_readings_cases.json`.
  - Backquote is claimed both by suggestions (plan 2.10) and by spectacle's Tasteful toggle (Daniel's decisions: "or
    the ` key"). The conductor must settle it.
- **Spectacle (P1, P2):**
  - Do not name the label from `harmonySet`: core 0.444 at 81.5 changes a minute.
  - The bloom is `harmony.js`'s window.
  - `intrinsic()` must stop keying on the TEMPLATES suffix list.
- **Jam conductor:** A4's reads-as exception list and card "Page reads" lines change with the reader (after TN6).
- **Tracker owner (B3):**
  - TN5 lands the backdoor rules and `needSec`.
  - Still open: `C E7 Am F` reads A minor (sure); `ACTIVE_SEC` delays keys for pedalled held chords.
- **Pedagogy:** the lexicon lives at `tests/fixtures/theory/lexicon.json` (TN0). T-steps are gated by D17.

---

## 7. Receipts

Node and Python receipts run in CI style. Page receipts run headless (isolated Chrome, `--mute-audio`, the three
anti-throttling flags) on the phase's own port. Snapshots go to `state/arsenal/receipts/piano-theory-nextgen/<id>/`.

| ID | Phase | Check | Pass |
|---|---|---|---|
| **NG1** | TN1 | Fixture names (`chord_readings_cases.json`) | The original 71: at least 71 right, at least 67 exact. Groups: plain 32/32, Daniel 24/24, dominants 10/10, rootless, quartal and polychord 5/5; tags 6/6. Defect cases 100%: `C3 G3 Bb3` gives `Cm7(no3)` in E♭ and `C7(no3)` in F, band at most leaning. `C4 D4 E4 F4` is a cluster. `G2 F3 A3 C4` has no `G11`. `Bbadd9(11)/Ab` is absent. Chip voicings read as themselves. Daniel's 24 × 12 keys give identical numbers in every key. Cluster tag false positives on Daniel's 24: at most 4 (measured 4 with the A3 rule; goal 2). |
| **NG2** | TN1 | Real windows, static (lane, counts only) | Same name as offline at least 730/983. Unnamed at most 41. Gains at least 188 windows (568 s). Losses at most 63 (107 s), at most 8 in the clear band (from 16). Clear-band agreement at least 0.93, with and without single-reading windows. Clear-band no-3rd dominant tops **0** (from 21, 35.0 s). Slash-duplicate runner-ups **0** (from 24, 41.1 s). Clear-band cluster tags at most 20 windows (from 94, 266 s; A3 rule measured 20, 64.8 s). |
| **NG3** | TN1 | ALSO | The eight lab voicings exactly as the 2.1 table. On real windows: canvas ALSO at most 110 windows and 300 s (measured 104, 294 s). It covers at least 61 of the losses (any length) and at least 42 held 1 s or more. HUD close at most 70 windows. **0** ALSO names from a colour-tone slash bass, a drop path, no-3rd or rootless readings. |
| **NG4** | TN5 | Suffix parser twins | Every distinct suffix the reader emits over the fixtures and real windows gives identical tones, letter steps, family and dominant in JS and Python. `FAMILY`, `TONE_STEPS` and `DOMINANT` derive from it. `node tests/nashville_js.test.mjs` and `py -m pytest tests/test_arsenal_nashville.py -q` green. |
| **NG5** | TN2 | Live window | **Calibration first:** the page pipeline (120 ms on / 300 ms release over everything sounding) replayed per session gives label changes per minute of chord-window time within ±15% of the logged chord events for S1, S2, S4, S5 and S6 (S3 excluded: its log is incomplete). **Then steady at 250 ms:** six-session core at least 0.577 (at least 0.560 with no oracle key; measured 0.568). Every session's core above page-now's. Unnamed at most 13.5%. Median latency at most 650 ms. Changes per minute below the calibrated page-now in all five sessions. Median label life reported (under 0.3 s blocks TN7). **Cost:** tick p95 at most 0.2 ms; cost at minute 30 within 10% of minute 1. **Hidden tab:** replay with timers at 1 Hz gives identical windows and names. **Isolation:** synthetic `window_sessions` boundaries 100%; Claude-source notes change nothing. |
| **NG6** | TN3 | Scales | 11/11 cases. Same-root flips at most 3/199. Gate-closed cases give no canvas caption. Real windows: seconds of canvas-eligible scale captions (character note sounded) reported apart from implied-only seconds, and 0 canvas captions from implied-only scales. 0 roots spelled against the key. Vamps give D Dorian, A Dorian, A Aeolian. Real key areas firing at most 1/23. His D♭ loop: none. |
| **NG7** | TN5 | Tracker | 2,872/2,872 existing checks plus the new scenarios. `C C7 F Bb7 C` gives C major (sure) with numbers `1 1⁷ 4 ♭7⁷ 1`. `Fm7 Bb7 Cmaj7` gives C major. F blues stays F. The other 13 harness scenarios unchanged. The Python twin gives the same key on the shared scenarios. `candidate.needSec` equals `holdSec` or `2 × holdSec`. |
| **NG8** | TN4 | Function labels | `function_cases.json` 100% in JS and Python. Real windows: at least 6 of the 7 new-key non-diatonic labels at the 9 no-pause key changes become `from <old key>`. Only dominants that land get "secondary dominant"; the 2 add11-shaped chromatic windows stay chromatic. |
| **NG9** | TN4 | Row composer | Scripted sequences (banner during a key change; function word plus scale; unsure key; jam run): every frame has exactly one caption at the table 3.2 priority. Drop order holds at 1060 and 870 px widths. Every string resolves to a lexicon id. Guard words 0. |
| **NG10** | TN7 | Classic | `?theory=classic&engine=templates&chordName=every` against the pre-build page, seeded frozen frame, 9:16 and 16:9: MAE 0, max diff 0. Classic with the reader differs only inside the label and `nns` boxes. |
| **NG11** | TN7 | Layout and width | Every distinct top name from NG2's real set plus the fixtures, at 170 px (9:16) and 140 px (16:9), fits the label box at base size or at the 0.8 shrink; 0 overflow; names needing the bracket drop counted and listed. The chip line with 7 chips, `NO 3RD` and ALSO fits, dropping ALSO first. `NEW KEY · G MAJOR · DOWN A HALF STEP` after the longest number fits in 16:9 by the drop order. Diamond ink at least 8 px from the `nns` ink. Spectacle R7 (banner forms, high-ledger chord) still passes. |
| **NG12** | TN7 | Recording and isolation | REC 5 s in Next-gen against the same seeded run with glass and DOM hidden: MAE 0. REC changes no setting. 60 s of Claude cues, a Loop and a Try against the same run without: window ids, readings, log chord events, tracker histogram and rarity inputs identical. |
| **NG13** | TN7 | Cost and flicker on the page | Frame Δp95 at most 0.2 ms at 1x and 0.5 ms at REC size against `?engine=templates`. Label-layer uploads at most 2 per window (commit, ALSO). `nns` uploads at most 1 per caption change. 0 uploads while a window holds after its ALSO. 60 s seeded replay: label pops equal window `new` events, and 0 pops on `grow`. |
| **NG14** | TN7 | Coexistence | Try `found` 17/17 on the seed cards played exactly (unchanged). Rarity: one scoring per window, and upgrades replace. Suggestions: 0 "the label calls it" lines on the reading fixture. The row-slot sequence of NG9 on the live page. |
| **NG15** | TN8 | Practice | `py -m pytest tests/test_arsenal_practice.py -q` green. `practice name <notes>` prints the reader's ranked list. Page and practice agree 100% on `chord_readings_cases.json`. The 2 real dominant-11 windows (3.1 s) read as 5 chords with their 11. `performance summary` names secondary dominants (13 windows) instead of "chromatic". `practice brief` uses `from <old key>` at key changes. |
| **NG16** | TN9 | First night | Chat note sent before he plays. After 20 minutes he says: whether the names of his top five chords (4, 1, 6m, 2m, 5 families) match his ear; whether ALSO helped or cluttered; steady against every note; how the TikTok test clip reads on his phone. Answers saved under `state/arsenal/jam/riffs/`. |
| **NG17** | TN10 | Ring core | Side column, never recorded (MAE 0 against hidden). Replay of S1-S6's tracker output: swings at most the number of sure switches, and 0 swing-backs within 30 s. Synthetic I-I7-IV with a long IV: 0 swings. Trail segments equal `new` commits. Hue of each node equals `noteCss` of its root. |

---

## 8. Risks

1. **The reference is partly circular.** The prototype borrowed the offline engine's bass-rooted intuitions, so 74%
   agreement flatters both. Only the fixtures are independent, and several of their expected names came from the same
   lens. Daniel's ear (NG16) is the real judge.
2. **Name churn.** The page taught `B♭m11/G♭`. The was-rule ALSO keeps it visible, and the chat note comes before the
   first night. If he prefers the old big names, Q1's alternative adds a setting.
3. **ALSO on 15% of chord time.** The line is small and grey, but it is on the recording. If NG16 says clutter, the
   fallback is ALSO only in the leaning or ambiguous band. That loses the clear-band safety net: 16 of the loss windows
   (25.9 s) are clear.
4. **Flicker may still be high.** The live log shows 73-234 label changes a minute (S6's median label life 0.03 s), and
   no receipt has yet measured the steady window's label life on a calibrated replay. NG5 blocks TN7 if it stays under
   0.3 s.
5. **The tracker caps the numbers and the captions.** Dm7 G7 shows F major, `C E7 Am F` shows A minor (sure), and
   I-I7-IV flips F, C, then F again. D11's guard and the sure-only ring swing limit the damage on camera; they do not
   fix it.
6. **Long names at hero size.** `A♭7♯9♭13/G♭`-class names are rare (p99 14 characters) but untested at 170 px. NG11 and
   the D13 fit rule cover them.
7. **Implied scales.** The canvas gate prevents over-teaching, but the HUD and Study still show implied modes, and they
   must say "implied".
8. **Sequencing.** Daniel's first visible next-gen moment waits for J9, J10 and spectacle P2. TN0-TN6 make that wait
   productive, but TN7 cannot be pulled forward without breaking one-owner-per-file.
9. **Twin drift.** `parseSuffix`, the function labeller and the tracker rules each exist in JS and Python. NG4, NG7,
   NG8 and NG15 are the tripwires.
10. **Cost.** The reader is about 6 times the cost of detect per call. With 10 Hz memoised naming, that stays far under
    NG13's 0.2 ms budget, but only once the O(N²) rescan is gone (H1).

---

## 9. Questions for Daniel (three, each with a recommended default)

1. **Your favourite chord's new name.** The big label would say `G♭maj13♯11` (the name built on your bass: your 4 with
   the bright note), and while the old name still fits the same notes, it stays small after the notes as
   `ALSO B♭m11/G♭`. OK?
   - **Recommended: yes.**
   - Alternative: keep today's names big, with the new name as the small one.
2. **What goes in your videos?** The Nashville row would say a little more, one thing at a time: the new key and how
   far it moved (`NEW KEY · G MAJOR · DOWN A HALF STEP`), `PULLS TO 6m` or `FROM A♭ MAJOR` where it says "outside"
   today, and the scale when its colour note sounds (`IN D♭ MAJOR · G♭ LYDIAN`). The key ring and note roles stay off
   the video until you try them.
   - **Recommended: yes, the Next-gen view in recordings.**
   - Classic (today's look, with the corrected names) stays one select away.
3. **One name per chord, or a name for every note?** The big name would hold still for each chord you mean: a rolled or
   pedalled chord gets one name, and it quietly grows as you add colour. The note chips under it still update on every
   note.
   - **Recommended: steady, and we switch between the two for a few minutes on the first night so you can pick.**

---

## 10. For Vandor, not for Daniel

- **This file overrides** `design-display.md` 3.2, 3.7, 6 and 10, and `design-pedagogy.md` 11.2 and 12's T2 scope,
  where they disagree.
- **ALSO, measured this pass.** The was-rule is not just a churn bridge. It is the engine's safety net: all 61 covered
  losses are covered by the page's former name, and the close rule covers none. Do not time-limit it.
- **Scratch files** (never copied into tracked files):
  - `theory-nextgen/spec/merge_lab.mjs`;
  - the judges' `judge/cross.mjs` and `labels.mjs`;
  - the engine lens's `engine.mjs`, `fixtures.mjs`, `real.mjs`, `replay.mjs`, `scales.mjs`, `nashville-ng.mjs`;
  - `offline/S1-S6.json` (practice analyze output, read only). The S6 verb outputs (`practice_*.txt`) hold clock times.
- **Tracker harness observation** for B3's owner: `ACTIVE_SEC` 1.5 s per strike delays keys for slow pedalled playing.
  It likely feeds the 11-33% "unsure" time.
- **Key collision to settle outside this spec:** suggestions and spectacle both claim Backquote.
- **Ownership reminder:** TN7 and TN10 each need a `piano.js` wave with no other integration step; queue them against
  SG7 and V2-B, V2-D, V2-E, V2-G.

## Appendix: reproduce

```sh
cd C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/theory-nextgen
node fixtures.mjs                 # page vs next-gen, synthetic set
node real.mjs && node replay.mjs  # real windows static; live replay (needs offline/S1..S6.json, read only)
node judge/cross.mjs; node judge/labels.mjs   # defect scans (no-3rd, slash duplicates, cluster, display ALSO)
node spec/merge_lab.mjs           # this spec: was/close ALSO, loss coverage, tighter cluster, name lengths
NG=./nashville-ng.mjs node tracker-compare.mjs && node nashville_ng.test.mjs   # backdoor patch, 2,872 checks
```

## Daniel's decisions (2026-09-14, answered on Discord)

On Discord Daniel answered the questions below, sent with recommended defaults, with: "Yes to all of them! Really good ideas!". Recorded as:
- **Q1 (chord label):** the big label shows the new name (Gbmaj13#11). The old name stays small after the chips as "ALSO Bbm11/Gb".
- **Q2 (captions):** the Next-gen view's captions go in recordings. Classic (today's look with corrected names) is one select away.
- **Q3 (label timing):** one steady name per chord. On the first night we switch between steady and every-note for a few minutes so he can confirm.
