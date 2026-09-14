# Chord suggestions while Daniel holds a chord

| | |
|---|---|
| Status | Research and design, 2026-09-14. No code edited, no server or browser started, nothing installed. |
| Asked for | Daniel, verbatim (Discord): "Could we add some cool features like suggesting chords to play when you are holding a chord down?" |
| Built from | `arsenal/web/piano.js` (overlay `LAYOUT`, label settle, key tracker wiring, top bar), `arsenal/web/piano/nashville.js`, `glass.js`, `cues.js`, `transport.js`, `deck.js`, `arsenal/practice.py` (moves, loops, readings), `arsenal/pianocue_voicing.mjs`, `research/in-flight/piano-jam-2026-09-14/jam-spec.md`, `design-music.md`, `design-ux.md`, the house ideas (`heimdall.md`, `navi.md`, `sunshine.md`, `vandor-integration.md`), `research/in-flight/piano-spectacle-2026-09-13/spectacle-spec.md` (banner boxes). |
| Measured tonight | `py -m arsenal.practice progressions` (quality and exact levels), `borrowed`, `keys` and `history` over the six logged sessions, run locally into the scratchpad. `py -m arsenal.practice name` and `node arsenal/pianocue_voicing.mjs` on the worked-example voicings (section 6). |
| Privacy | This file holds only chord numbers, number sequences and counts from the log. No session ids, no clock times, no transcriptions. The habit data the engine uses is computed locally from `state/arsenal/performance` (git-ignored: `.gitignore` line 122, `state/*`) and never written to a tracked file. |

---

## 0. The feature in one screen

1. **When.** He holds a chord still for a moment (the chord name has settled for 700 ms and no new note has
   started for 450 ms). Nothing shows while he plays fast, while REC runs, or while a Loop or Try run leads.
2. **What.** Two to four small chips appear beside the chord name. Each chip is one next chord: letters, its
   Nashville number, and one reason word: **home**, **your move**, **borrowed colour**, **slide**, **new key**,
   **stretch** (plus **lift** and **surprise**, section 3.4).
3. **From where.** Three sources, blended and labelled:
   - **theory** in the current key (cadences, functions, deceptive moves, secondary dominants, borrowed colours,
     Lydian and Mixolydian options, chromatic slides, the key-change pivots he already uses);
   - **his habits**: what he actually played after this number, from the practice log, computed on this machine;
   - **stretch**: one sound near his growth edge (tension and contrast) that he rarely plays.
4. **Voiced near his hands.** Each suggestion is voiced from the notes he is holding: common tones stay, other
   fingers move to the nearest note. The page's own chord namer must read the voicing back as the chord.
5. **Hover, hear, play.** Hover a chip: its new keys light as ghosts on the unrecorded glass. Click: Claude plays
   "the move" (his chord, then the suggestion). Play it yourself: the chip pulses once, and new chips follow the
   new chord. Nothing is ever required.
6. **Never in a take by default.** Chips live in the DOM beside the canvas (or on the glass), so REC records only
   him. An opt-in "show in recording" draws them in a reserved canvas slot.
7. **Jam-space ready.** A pure `suggest.js` engine, a `habits` route, a "Keep as card" action that makes a
   **try this next** card, and a `keys: {arrive, stay, lift}` field per chip that the key lights reuse later.

---

## 1. What his log says (the evidence the engine stands on)

Six logged sessions, about 1,980 seconds of chord time in total. The progressions verb counts chords held 0.5 s or
more and merges repeats, and it lists only moves played at least twice within one session. So the sums below
undercount one-off moves; the engine's habits builder uses every move (section 2.3).

### 1.1 What follows what (numbers with quality only, summed over the six sessions)

| After a | Times | What came next (counts) |
|---|---|---|
| 4 | 110 | 1: 45, 5: 24, 6m: 19, 5sus: 10, 2m: 8, 3m: 4 |
| 1 | 90 | 4: 45, 6m: 17, 2m: 15, 2: 4, 5: 3, 5sus: 2, 4m: 2, 4sus: 2 |
| 6m | 73 | 1: 26, 4: 23, 5: 10, 2m: 6, 5sus: 4, 3m: 2, 2sus: 2 |
| 2m | 36 | 4: 16, 6m: 10, 1: 8, 5: 2 |
| 5 | 33 | 6m: 17, 1: 6, 3m: 4, 4: 3, 2m: 3 |
| 5sus | 13 | 6m: 6, 2m: 3, 4: 2, 1: 2 |
| 3m | 10 | 4: 8, 1: 2 |
| 2 (major) | 7 | 4: 7 |

Three-chord moves he repeats most: `1 4 1` (15), `4 1 4` (14), `6m 1 4` (13), `4 5 6m` (12), `6m 4 1` (10),
`4 1 6m` (10).

At the exact level the pairs are thinner but show his colours: `1maj9 -> 4maj13#11` (4), `4maj9 -> 1maj9` (4),
`1maj9 -> 4maj9` (3), `6m7(11) -> 4maj13` (3).

### 1.2 His cadences, his colours, and the gap

- **Cadences by kind** (the `history` verb): `4 -> 1` 29 times; `5 -> 6m` 11 times; `5sus -> 1`, `b7 -> 1` and a 5
  over a 1 pedal resolving to 1, once each. He lands home through the 4 (plagal) and lets the 5 fall to the 6m (the
  deceptive move). **The plain 5 (or 5^7) to 1 cadence is essentially absent.**
- **Numbers he holds longest:** `4maj13#11` (172 s, all six sessions), `1maj9` (167 s), `4maj13` (100 s), `4maj9`
  (96 s), `6m11` (92 s), `1add9` (71 s).
- **Dominant chords with their 3rd** (qualities 7, 9 and 13): about 35 s of the 1,980 s, under 2%. His 5 chords are
  add9, add11, sus and no-3rd shapes. This is the measured growth edge: a real V7 with its 3rd.
- **Secondary dominants:** `3^7 -> 6m` lands several times (he knows that pull). `2^7` (the 5 of the 5) appears
  several times and lands on its target only once: he uses the 2 major as Lydian light, not as a pull.
- **Borrowed from the parallel minor:** 4m, b7, b6, b3 and 1m all appear, briefly (under 5 s each).

### 1.3 His key changes (key areas that change without a pause)

| Move | Times | The hinge he used, in numbers |
|---|---|---|
| Down a minor third | 2 | the old `4maj13` became the new key's b6, then the new `1add9`; the old `2m9/4` became the new key's `4m`, then the new `1maj7` |
| Down a half step | 1 | the old `4maj13#11` slid down a half step and became the new key's `4maj7` |
| Up a whole step | 1 | the old `3m7/5` became the new key's `2m`, then its `6m11` |
| Up a fourth | 1 | the old `5add9` turned minor and became the new key's `2m` |
| To the parallel minor | 1 | `1maj9/3` became `1m11` |

After a pause he also moved up a half step once and to other keys several times; those are new sections, not
pivots, and the engine does not learn hinges from them.

### 1.4 A finding that shapes the engine: the page misreads his favourite chord

His most-held chord, played as `Gb2 Db3 F3 Ab3 Bb3 C4 Eb4` in Db major:
- the page's namer (and so the big label and the Nashville row) says `Bbm11/Gb = 6m11/4`;
- `practice name` reads it as `Gbmaj13#11 = 4maj13#11`, "the Lydian 4", and lists `6m11b13/4` only third.

THEORY's templates have no `maj9#11`, `maj13#11` or `13sus4` yet (jam-spec v2 wave V2-F). If the engine took the
page's label at its word it would suggest what follows a **6m** while he is holding his **4**, and every "your move"
count would come from the wrong row of the table. **The engine reads the held chord with the practice verbs' reading
rules (bass-aware, cheapest reading), not with the label.** Section 2.2 says how the page gets those rules.

---

## 2. The engine

### 2.1 What "holding a chord" means

| Input | Source on the page | Rule |
|---|---|---|
| The notes | `sounding` (finger-held plus pedal-held) and the struck groups | The **held group** is every note struck since the last bass onset, with pedal-held notes from before that bass left out. A pedal that rings the old chord under a new bass never blends the two. |
| The hands | the MIDI numbers of the held group | Left hand: notes below the widest gap under C4. Right hand: the rest. The voicer (2.5) anchors to these exact keys. |
| Settled | `overlay.shown` (label settles 120 ms after a note-on, 300 ms after a release) | The reading must stay the same for **700 ms** (practice counts chords from 0.5 s; 700 ms is past his note-gap p75 of 363-448 ms, so a passing chord rarely qualifies). |
| Not busy | note-on times | **450 ms** with no new note-on, and fewer than 6 note-ons in the last 2 s. After a busy spell, 1.2 s of calm before chips return. |
| Key | `keyView` (the tracker), a locked key, or the jam key (jam-spec 8.10) | "sure" or "fair": numbers shown, theory at full weight. "unsure": chips show letters only, theory weight halves, doors (3.3) are off. No key: habits and voice-leading neighbours only. |
| Pedal blur | the reading's cost | A held group of more than 7 pitch classes, or a reading cost over 3.5, shows nothing. Silence is better than a guess. |

### 2.2 Reading the held chord

The engine needs `{degree, quality, suffix, bass degree}` in the shown key, from the practice verbs' reading
(`extended_readings` and `choose_reading` in `arsenal/practice.py`), not from `Theory.detect`'s label alone.

- **Today** those rules exist only in Python. `arsenal/practice_theory.mjs` goes the other way: it lets Python call
  the page's namer.
- **Proposal:** a JS twin, `arsenal/web/piano/readings.js`, pure, checked against `practice name` on a shared fixture
  (`tests/fixtures/readings_cases.json`, synthetic voicings only), the same way `nashville.js` and `nashville.py`
  share `nashville_cases.json`. The page already imports the pure `nashville.js`, so this is the same pattern.
- **Core number** is the degree plus quality (`4`, `6m`, `5sus`), as `practice.core_number` makes it. Habits are
  looked up by core number, with the exact number as a tiebreak.

### 2.3 Source A: his habits (computed locally)

- **Builder:** `py -m arsenal.practice habits` (a new verb, delegated like `riff`) runs `chord_sequences` over every
  session in `state/arsenal/performance` at both levels and counts:
  - 2-chord moves `after[core][next core]` with `min_count = 1`;
  - 3-chord context `after[prev core, core][next core]`;
  - his usual colour per core number: the exact number with the most held time (4 as `4maj13#11`, 1 as `1maj9`,
    6m as `6m11`);
  - his usual bass per move (for example 1 as `1/3` after a 4, when that is what he does).
- **Weighting:** tonight's sessions count double, and older sessions decay with a 30-day half-life.
- **Evidence gate for the words "your move":** at least 3 times across at least 2 sessions. Below that, a habit
  still adds score but the chip may not say "your move".
- **Output:** `state/arsenal/practice/habits.json` (git-ignored), holding counts and numbers only: no session ids,
  no times, no letters. The server serves it on `GET /api/practice/habits` from state and never tracks it.
- **Per key:** counts are key-free (numbers), so a move learned in F# major suggests itself in Db major. That is the
  lesson "numbers stay the same in every key".

### 2.4 Source B: theory in the current key

All rules are written in numbers, major key first. Minor keys use the parallel rows in brackets. Every rule carries
a **function prior T** from 0 to 1 and a reason word.

| Held | Candidates (T) | Reason words |
|---|---|---|
| 1 | 4 (0.8), 6m (0.7), 2m (0.7), 5 or 5sus (0.6); `1^7 -> 4` gospel pull (0.5); `3^7 -> 6m` (0.5); b7 (0.5); `#1°7` passing to 2m (0.4) | lift, your move, pull, borrowed colour, stretch |
| 2m | 5 (0.9), `2m/5` (0.8), 4 (0.7), `1/3` (0.6), 6m (0.5) | home-ward, lift |
| 3m | 6m (0.8), 4 (0.7), `3^7` (make it major: 0.5, pull to 6m), `b3°7` slide to 2m (0.4) | pull, slide |
| 4 | **1 (1.0)**, 5 (0.8), `5/4` gospel lift (0.8), 6m (0.7), 4m then 1 (0.6), `1/5` (0.6), b7 then 1 (0.5), `#4°7` then `1/5` (0.5), 2m (0.5) | home, lift, borrowed colour, stretch |
| 5, 5^7 | **1 (1.0)**, 6m (0.8), 4 (0.5), b6 (0.5, the borrowed surprise), 3m (0.4) | home, surprise, borrowed colour |
| 5sus | `5^7` then 1 (0.9: the sus lands), 1 (0.8), 6m (0.6), 2m (0.5) | stretch, home, surprise |
| 6m | 4 (0.8), 2m (0.7), 1 (0.6), 5 (0.6), `6m/5` walking bass (0.5), `2^7` pull to 5 (0.4) | your move, pull |
| 2 (major, Lydian light) | 4 (0.7), `2^7 -> 5` (0.6, let it pull), 5 (0.6) | pull, stretch |
| 4m, b7, b6, b3 (borrowed) | 1 (1.0), b7 after b6 (0.8), 4 after b3 (0.6) | home |
| X^7 (a secondary dominant) | its target (1.0), the target's relative (0.5) | pull, surprise |
| [1m] | [4m, b6, b7, `5^7` with the raised 3rd, b3] | [same words] |

**Chromatic slides** (T 0.4): the same shape a half step down (every finger), the bass alone a half step (`4 -> #4°7
-> 1/5`, `1/3 -> b3°7 -> 2m7`), and a chord's 3rd alone down a half step (4 to 4m).

**Doors** (T 0.4), from his own hinges (1.3), so each door is also a habit:

| Door | Rule | Reason |
|---|---|---|
| Down a minor third | re-read the held 4 as the b6, or the held `2m/4` as the `4m/b6`, of the key 3 semitones down; the next chord is that key's 1 | new key |
| Down a half step | the same number a half step down (`4 -> 4` in the new key) | slide |
| Up a whole step | the held 3m becomes the new key's 2m | new key |
| Up a fourth | the held 5 turns minor and becomes the new key's 2m | new key |
| Parallel | 1 becomes 1m | borrowed colour |

### 2.5 Source C: stretch (the growth edge)

- **Familiarity h** per exact number comes from the log, the same number the spectacle rarity scorer uses (`Φ = F × h
  + novelty`). Stretch candidates are theory candidates with `1 - h ≥ 0.7`, so he rarely plays them.
- **His measured edge (1.2)** ranks these first:
  1. a real 5 with its 3rd resolving to 1 (`5^7`, `5^9`, `5^13`): plagal 29 times, the 5-to-1 cadence almost never;
  2. a diminished passing chord (`#4°7`, `#1°7`, `b3°7`): `m7b5` appears once, for under a second, and `dim7` never;
  3. a secondary dominant that actually lands (`2^7 -> 5`, `6^7 -> 2m`): the 2 major floats and almost never pulls;
  4. letting a sus resolve (`5sus -> 5^7 -> 1`).
- **One degree stranger** (Sunshine's distance rule): a stretch chip is at most one step from something he played
  tonight. It changes one thing (a 3rd added, a bass moved a half step), never three.
- **At most one stretch chip**, and never labelled "your move".

### 2.6 Blending, ranking and slots

**Score per candidate (weights illustrative, to be tuned by ear on the first night):**

```
score = 0.40·H + 0.35·T + 0.15·E + 0.10·N − R
  H  habit share: P(next | prev, held) backing off to P(next | held), core-number level, smoothed (k = 1)
  T  theory prior (2.4)
  E  ease = exp(−movement / 8), movement = the cheapest note matching from his held keys (the bridge's `movement`)
  N  novelty = 1 − h (only counts for stretch candidates)
  R  penalties: same reading as held (1.0); shown for this reading 3 times this session and never played (0.3);
     outside the key while the key is unsure (0.2)
```

**Slots, not one ranked list.** A single list would show 1, 1/3, 1maj9 and 1add9 as four chips.
1. **One chip per core number.** Its best-scoring voicing and bass win.
2. **HOME:** the best tonic-function candidate (1, or 1m in minor; the 4 or 6m when the held chord already is the
   1: then the slot's word is **lift**).
3. **YOUR MOVE:** the best habit that passes the evidence gate and is not already in HOME. When HOME is also his top
   habit, that chip shows both words (`home · your move`) and YOUR MOVE takes his next habit.
4. **COLOUR:** the best borrowed, modal, slide or pull candidate.
5. **STRETCH:** the best stretch candidate. With the default of 3 chips, COLOUR and STRETCH take turns: the same held
   reading shows COLOUR the first time and STRETCH the next.
6. **A door** replaces COLOUR only when all hold: the key area has lasted 60 s of playing; the held chord matches a
   hinge row (1.3); he is resting (the rest detector); and no door was offered in the last 30 s.

**Count:** 2, 3 (default) or 4 (adds the next habit or the other of COLOUR and STRETCH).

### 2.7 Stability: no flicker

- **Recompute** at most every 100 ms (the key tracker's own tick). **Change chips** only when the held reading
  (core number plus bass degree) changes, or the key changes.
- **Re-voicing** the same chord (new voicing, same reading) keeps the chips and re-voices only their ghosts.
- **Order is frozen per reading.** A new candidate replaces a shown one only if it beats it by 0.15 for 1.5 s of
  holding. Chips never move under the mouse (the deck's rule).
- **A new chord** fades the chips out over 120 ms at the first note-on that changes the reading, so a stale chip is
  never visible. They fade back in over 250 ms once 2.1 passes again.
- **A key change** by the tracker crossfades the chips (300 ms) and never pops them.
- **Honest dimming.** While the key is "unsure" the chips drop their numbers, like the Nashville row dims.

### 2.8 Voicing near his hands (and respecting his numbers)

The bridge's `voice_lead` keeps each style near its own register, not near his hands. From his held
`Gb2 Db3 F3 Ab3 Bb3 C4 Eb4`, the bridge's `spread` with voice-leading moved 6 to 23 semitones per suggestion (a b7
chord jumped to `B2 Bb3 Db4 Eb4 Gb4`, 23). Hand-near voicings of the same suggestions moved 1 to 8 (section 6). So
suggestions need their own **near** voicer.

1. **Targets:** the suggestion's chord tones, plus his usual colour for that core number (2.3), plus required
   tones: the 3rd and 7th for a dominant, the #11 for a Lydian 4, the lowered 3rd for 4m.
2. **Bass:** a slash chord's bass, else the root. Pick the octave nearest his held bass (within 7 semitones),
   preferring a step. When his habit for this move uses a slash (1 as `1/3` after a 4), use it.
3. **Upper voices:** common tones stay on the same key. Each other voice moves to the nearest target within 2
   semitones; a voice with no target that near lifts off. A required tone still missing goes in at the nearest
   octave inside his right-hand span. Never above his top note plus 2 semitones; never below the bridge's
   low-interval limits (`design-music.md` 4.4).
4. **Read-back gate:** the page's `Theory.detect` must read the voicing as the suggestion (`exact` or
   `enharmonic`). Otherwise, try variants (natural 5th added or dropped, one moving voice left in place). If none
   reads as itself, the chip shows the page's reading on its hover line ("your screen will call this ...").
5. **Numbers** are formatted by the page's own `nashville()` with the Minor setting (tonic or relative), and letters
   by `spellForKey`, so a chip always agrees with the Nashville row that will appear when he plays it.

The same voicer runs in node for the CLI (section 5.3): a `near` style beside `band` in `pianocue_voicing.mjs`,
with one shared fixture.

### 2.9 Learning from what he does (without touching the practice log)

- **Accepted:** he plays the suggestion's core number within 4 s of the chips showing (the Try `found` rule: every
  chord pitch class sounding for 150 ms, any voicing).
- **Ignored:** the chips were shown for 2 s or more and he played something else.
- **Where it goes:** a per-page count `{reading, chip core, shown, accepted}`, first in localStorage
  (`arsenal.piano.suggest.stats`), later in `state/arsenal/jam/suggest/stats.json` through a jam route. Never a new
  event kind in the performance log: `performance.validate_event` refuses unknown kinds and the whole batch with them
  (`design-music.md` 1.4).
- **Use:** three ignores of the same chip for the same reading demote it for 10 minutes. Accepts add nothing to the
  habits source: that already learns from what he plays.

---

## 3. Presentation

### 3.1 Where the chips go (no collisions)

**The rule:** suggestions are private hints, like the deck. They are **never** drawn on the recorded canvas unless
he opts in (3.6), so no canvas element can be covered in a take.

| Framing and screen | Placement | Clear of |
|---|---|---|
| **9:16** with a left margin ≥ 220 CSS px (his usual desktop view: the deck overlays the right margin) | A DOM column `<aside id="suggest">` in the **left** margin, 200-320 px wide, its first chip level with the label layer's centre (label box y 148-488, scaled to CSS), stacked downward | Everything on the canvas. The deck is on the right. The toast moves only for the deck. |
| **9:16** with a narrow margin (fullscreen on a portrait screen) | On the glass, in the cue chip's top band (reference y 28-144), only while no CLAUDE chip is up; it fades out when a cue arrives | Label from y 148; CLAUDE chip (yields to it); the TikTok header is irrelevant on the unrecorded glass |
| **16:9** | On the glass, in the cue chip's slot (reference x 50-950, y 464-568), only while no CLAUDE chip is up | Label y 41-351; Nashville row y 332-452; banner y 344-440; staff x 1240-1880. The 16:9 rail height is unmeasured (`design-ux.md` 5.3): the S3 receipt must show the chips end at least 60 px above the trail foot. |
| **Deck open, dock mode** | The column moves into the deck's Now header as one row of chips | The deck's own layout |

**Yields:** the CLAUDE chip always wins its slot (Claude is speaking). A rarity banner never shares a box with the
chips; while a Legendary banner holds, the chips wait (dimmed to 0) so the moment gets his eyes.

### 3.2 The chip

```
+------------------------------+
|  D♭maj9/F        1maj9/3     |   name (nameRuns / suffixRuns look), number with superscripts
|  HOME · YOUR MOVE            |   reason words, small caps, 0.62 alpha
+------------------------------+
```

- Ink matches the page's overlay (ivory). A thin moonlight hairline marks it as Claude's hint (Claude's colour,
  `#C8DCFF`), but it carries no CLAUDE word: it is not Claude playing.
- **stretch** chips get a dashed hairline, the only visual difference; no colour ranks one chip over another.
- Letters only while the key is unsure (2.7).
- **Hover line** (one sentence, plain words, after 600 ms): the move in hand terms and the evidence. For example:
  "keep your right hand; drop the bass a half step to F. After a 4 you went home to 1 in 45 of 110 moves." Counts
  appear only here, never on the chip face (Sunshine: no scores on the face).

### 3.3 Ghost keys on the glass

- **A new ghost state `suggest`** in `glass.js`: a solid hairline rim at 0.3 alpha (0.4 on black keys), no fill, no
  breathing. It is distinct from Try's `target` (filled, breathing) and `incoming` (dashed).
- **Only the keys that change are drawn:** `arrive` keys (to press) get the rim. `stay` keys get nothing (his fingers
  are already there). `lift` keys get nothing in v1; in v2 a dotted inner rim, so "let go of this" is visible.
- **Default: ghosts only while a chip is hovered or focused.** Setting `chips + keys` also ghosts the first chip's
  `arrive` keys at half that alpha.
- **Always the glass, never the 3D keys**, even outside REC. Suggestions do not follow the jam view's `auto` rule,
  so they never have to move surfaces mid-take.
- **Budget:** the glass projects at most 24 keys; a suggestion adds 1-5 `arrive` keys.

### 3.4 Reason vocabulary (fixed, plain words)

| Word | Means (hover wording) | Source |
|---|---|---|
| home | "the chord that feels like arriving" | theory (tonic function) |
| your move | "you went here after this chord n times" | habits, evidence gate |
| lift | "moves up and away from home; the gospel 5 over 4 lives here" | theory (4 and 5 functions) |
| surprise | "sounds like it will go home, then doesn't" | theory (deceptive: 5 to 6m, 5 to b6) |
| pull | "a chord that leans hard toward the next one" | theory (secondary dominants) |
| borrowed colour | "a shade taken from the minor key on the same home note" | theory (parallel key) |
| slide | "every finger (or just the bass) moves a half step" | theory plus his hinge |
| new key | "this chord is also a door into another key" | his hinges (1.3) |
| stretch | "a sound you rarely play, one step from what you did" | growth edge (2.5) |

A chip shows at most two words. Theory words are "a handle, never a verdict" (Sunshine): no "correct", "should" or
"wrong".

### 3.5 Hear, accept, toggle

| Action | What happens |
|---|---|
| **Hover** a chip for 250 ms (the deck's chip timing) | `arrive` ghosts on the glass, silent |
| **Click** | Claude plays **the move**: his held voicing, then the suggestion, 0.8 s each, `keys` timbre, velocity 44, through `createClaudeVoice`. The notes are Claude's (`source: "claude"`), so they never reach `sounding`, the log, the key tracker or rarity (INT invariant 1). Clicking unlocks the voice as the deck's buttons do. |
| **Shift-click** | the suggestion alone |
| **Play it** (the real accept) | the `found` rule (2.9); the chip pulses once in size (1.0 to 1.15 to 1.0 over 200 ms, like `found`), then the chips follow the new chord |
| **Keep as card** (the chip's `...`) | makes a **try this next** card (5.2) |
| **KeyLab pads** (v2, with V2-G pad learn) | pads 1-4 hear chips 1-4, hands never leave the keys |
| **Keyboard** | one free key toggles the chips. The jam spec has taken A, K, `\`, `'`, `-`, `=` and the brackets; the key must be checked against `KEYMAP` at integration (N for "next" is the candidate) |

**The toggle** sits in the top bar's theory group, beside Numbers, Minor and Key:

```
Suggest [ off | chips | chips + keys ]      localStorage arsenal.piano.suggest (default: chips)
```

The deck's `[...]` settings hold the rest: how many (2, 3 or 4); stretch on or off (on); sources (theory, my moves:
both on); only one-finger moves (off: Sunshine's "Keep Three, Move One" as a filter); bass-only moves (off:
Sunshine's "Moving Floor"); show in recording (off).

### 3.6 Recordings (default: no)

- **Default:** the DOM column and the glass are outside `MediaRecorder`'s canvas, so a take holds none of it. The
  receipt (S4) checks recorded frames are identical with suggestions on and off.
- **Opt-in "show in recording"** (for teaching clips): a canvas layer built with `makeLayer()` in the strip's
  reserved slot. 9:16 uses x 180-900, y 1108-1192 (compact form y 1120-1170). 16:9 uses x 1240-1824, y 548-628.
  - It never shows while a jam run's stage strip (v2) is on screen: they share the slot.
  - It keeps the spectacle protect mask (effect light held at 35% or less under the plate).
  - A small credit `SUGGESTED BY CLAUDE` rides line 2, as `BACKING BY CLAUDE` does, so a viewer knows the chips were
    not his idea.

---

## 4. Restraint rules (the summary a builder checks against)

1. 2-4 chips, default 3, one per core number, at most one stretch and at most one door.
2. Show only after 700 ms settled and 450 ms without a note-on; never during fast playing, REC (default), a Loop or
   Try run, a Legendary banner hold, or a pedal blur.
3. Chips change only when the reading or key changes; order frozen per reading; 0.15 margin for 1.5 s to replace.
4. "your move" needs 3 plays across 2 sessions; stretch is never "your move"; every word comes from 3.4.
5. Voicings near his hands, read back by the page's own namer, or the chip says what the screen will call it.
6. Never sounds on its own: sound only on his click.
7. Never touches `sounding`, the practice log, the key tracker, rarity or the light budget.

---

## 5. How it plugs into the jam space

### 5.1 Modules and interfaces

```js
// arsenal/web/piano/readings.js (pure): the practice verbs' reading, twin of practice.extended_readings/choose_reading
export function readHeld({ midis, bassMidi, key, minor }) -> { core, number, suffix, bassDegree, cost, pcs } | null

// arsenal/web/piano/suggest.js (pure, no DOM; runs in the page and in node)
export function createSuggester({ habits /* habits.json */, detect /* Theory.detect */, nashville, spell,
  near /* voicer */, now = () => performance.now(), settings }) -> {
  update({ held /* midis + struck times */, sounding, pedal, key, keyConfidence, busy, resting, run, rec, banner })
    -> { state: "hidden" | "waiting" | "shown", reading, chips: [Chip] },
  accept(midis), hover(chipId), stats(), setSettings(s) }

// Chip
{ id, core: "1", number: "1maj9/3", name: "Dbmaj9/F", reasons: ["home", "your move"], source: ["theory", "habit"],
  score, T, H, E, N, voicing: [41, 49, 53, 56, 60, 63], movement: 3,
  keys: { arrive: [41], stay: [49, 53, 56, 60, 63], lift: [58] },
  reads: { page: "Dbmaj9/F", match: "exact" }, hover: "keep your right hand; ...", evidence: { after: 110, went: 45 } }

// arsenal/web/piano/suggest-view.js (DOM): the column, chips, hover line, the in-recording layer
export function createSuggestView({ root, stage, glass, voice, player, framing, deck, isRecording }) -> {
  render(result), layout(), clear(), dispose() }
```

`glass.draw()` gains `ghosts.suggest: [midi]`. In `piano.js`: `renderFrame` calls `suggester.update(...)` after
`tickKey`; `noteOn` feeds it `busy`; the top bar gets the Suggest select.

### 5.2 Cards: "try this next"

**Keep as card** on a chip makes a two-chord card through the existing routes (`POST /api/piano/deck/cards`, jam-spec
5.1):
- `group: "try"`, `kind: "progression"`, `key`: the shown key;
- `chords`: `[held reading, suggestion]` in numbers, each with `notes` (his held voicing as captured by DATA 2.10,
  and the near voicing);
- `title` from the reason ("Home from your 4", "The borrowed 4 minor, from your 4"), `why` from the hover line,
  `try`: "Hold the first, then move only the keys that light";
- `source.kind: "suggest"`, a new provenance value that goes through the J0 contract owner (jam-spec 13.1 rule 3);
- `created_by: "daniel"`, `source.saved_by: "claude"`.

Heimdall's **question and answer pair** maps directly: a stretch chip kept as a card holds the stretch as the
question and the chip after it (usually home) as the answer.

### 5.3 CLI, so Claude and the page agree

`py -m arsenal.practice next CHORD|NOTES [--key "Db major"] [--after PREV] [--count 3] [--json]` prints the chips
the page would show, with scores, reasons, near voicings and evidence counts.
- It runs `suggest.js` through a node entry (`arsenal/suggest_bridge.mjs`, the way `pianocue_voicing.mjs` runs the
  page's THEORY), so CLI and page are byte-identical.
- Claude uses it in chat ("what would you play after this?") and to publish try-this-next cards from the CLI:
  `pianocue card add --from-suggest`.

### 5.4 Inside a jam run

| Run mode | Suggestions |
|---|---|
| Play, Loop | hidden; the band is leading |
| Try | hidden; Try has its own target and incoming ghosts |
| v2: "other nexts" over a Loop | on the transport's `onPosition` `next` slot: chips for what could replace the loop's next chord; Keep as card makes a variant card (`variants`, DATA 2.4) |
| Riff analysis (v2) | the accept and ignore counts for a run feed one talking point: "you took the borrowed 4m twice; you never took the stretch" |

### 5.5 Build order (after J10, keeping jam-spec 13.1 ownership)

| Step | Scope | Owner files | Exit |
|---|---|---|---|
| S0 contracts | reading fixture, candidate tables, reason vocabulary, habits JSON schema, Chip shape; `source.kind: "suggest"` | `tests/fixtures/suggest/*`, `arsenal/jam/schemas.py` (via the conductor) | fixtures validate |
| S1 habits | `practice habits` verb (delegated module `arsenal/practice_habits.py`), `GET /api/practice/habits` | `practice_habits.py`, a 3-line `practice.py` registration, `serve.py` route | synthetic sessions give known counts; payload has no ids or times |
| S2 engine | `readings.js`, `suggest.js`, `suggest_bridge.mjs`, `practice next` | new files | S1, S2, S5, S6 below |
| S3 near voicer | `near` style | `pianocue_voicing.mjs` (J1's file) | S2 read-back receipt |
| S4 view and glass | `suggest-view.js`, the `suggest` ghost state | new file; `glass.js` (J8's file) | S3 |
| S5 integration | top-bar select, `renderFrame`, `noteOn`, settings | `piano.js`, `piano.html`, `piano.css` (J9's files) | S4 |
| S6 first night | Daniel holds chords for 10 minutes | none | Daniel says which chips he took and which felt wrong |

V2-B (discussion in the deck) also edits `deck.js` and `glass.js`: run S4 after V2-B lands, or hand `glass.js` to one
of them for that wave.

### 5.6 Later: the key lights

The chip's `keys` field is the whole contract. A lights adapter, whatever hardware the lights research picks,
consumes `{arrive, stay, lift}` for the hovered chip (or the first chip in `chips + keys` mode) under the same
timing, stability and restraint rules:
- `stay`: dim white;
- `arrive`: moonlight;
- `lift`: off (or a brief dim red in a teaching mode).

**One difference:** the recording default cannot protect a physical light. A phone camera filming his hands records
the lights, so the lights toggle needs its own "off while REC" setting (on by default).

---

## 6. Worked example: holding his favourite chord in Db major

Numbers and counts come from the log; the voicing is an illustrative spread of the chord he holds longest
(`4maj13#11`), not a copied moment.

**He holds** `Gb2 Db3 F3 Ab3 Bb3 C4 Eb4` with the pedal down, the key tracker sure of Db major.
- The big label says `Bbm11/Gb`, and the Nashville row `6m11/4` (1.4).
- The engine reads `Gbmaj13#11 = 4maj13#11`: core number **4**, the Lydian 4.
- His habits after a 4 (1.1): 1 went 45 times, 5 24, 6m 19, 5sus 10, 2m 8, 3m 4, out of 110. In his Db major
  session, `4 -> 5 -> 6m` came 6 times.

**Candidates, voiced near his hands.** Every voicing was checked with `practice name` and the voicing bridge, whose
read-back is the page's own namer. Movement is the cheapest note matching from the held keys.

| Chip | Number | Reasons | How the hands move | Movement | Page reads it as | Score |
|---|---|---|---|---|---|---|
| **D♭maj9/F** | `1maj9/3` | home · your move | bass Gb2 down a half step to F2; lift Bb3; the right hand stays | 3 | `Dbmaj9/F` (exact) | 0.40·0.41 + 0.35·1.0 + 0.15·0.69 + 0 = **0.62** |
| **A♭9/G♭** | `5^9/4` | your move · lift | keep the Gb bass; Db3 to C3, F3 to Eb3 | 3 | `Ab9/Gb` (exact) | 0.40·0.22 + 0.35·0.8 + 0.15·0.69 + 0.10·0.5 = **0.52** |
| B♭m11 | `6m11` | your move | move only the bass, Gb2 up to Bb2: the right hand is already a Bbm11 | 4 | `Bbm11` (exact) | 0.40·0.17 + 0.35·0.7 + 0.15·0.61 + 0.10·0.1 = 0.41 |
| **G♭m6/9** | `4m6/9` | borrowed colour | Bb3 down to A3 (the 3rd darkens), F3 to Eb3, C4 to Db4 | 4 | `Gbm6/9` (the page detects `F#m6/9` and respells it) | 0 + 0.35·0.6 + 0.15·0.61 + 0.10·0.7 = **0.37** |
| G°7 | `#4°7` | stretch | bass up a half step to G2; F3 to E3, C4 to Db4, Eb4 to E4; lift Ab3. Then `D♭/A♭` (`1/5`): the bass walks Gb, G, Ab | 6 | `Gdim7` (exact) | 0 + 0.35·0.5 + 0.15·0.47 + 0.10·0.95 = 0.34 |
| A♭9 | `5^9` | stretch | a real 5 with its 3rd (C3), then home | 6 | `Ab9` (exact) | same core number as `Ab9/Gb`, so only the better of the two is shown |
| F maj13#11 | `4maj13#11` of C major | slide (door) | every finger down a half step: his half-step key change | 7 | `Am11/F` (the page lacks the name) | 0.26, a door only |
| B♭add9 | `1add9` of B♭ major | new key (door) | the 4 he holds is the b6 of Bb major; his minor-third drop used exactly `4maj13 -> 1add9` | 8 | `Bbadd9` (exact) | 0.27, a door only |

**What he sees (default 3 chips):**
1. `D♭maj9/F 1maj9/3` HOME · YOUR MOVE
2. `A♭9/G♭ 5^9/4` YOUR MOVE · LIFT
3. `G♭m6/9 4m6/9` BORROWED COLOUR. Next time he holds a 4 in this session, the third chip is `G°7 #4°7` STRETCH.

**Why these, in plain words:**
- **Chip 1** is where he goes most, and it costs him three semitones: drop the bass a half step and let go of one
  note.
- **Chip 2** is his gospel lift. Keeping the Gb bass under an Ab chord makes it a dominant 7th in disguise (the Gb is
  the Ab chord's 7th), so it leans straight into chip 1: the Gb in the bass falls a half step to F, and the C rises
  to Db. Chips 2 and 1 in that order are the textbook resolution he almost never plays (1.2), reached with his own
  hand shape.
- **Chip 3** changes one idea: the 3rd of his 4 chord drops a half step. That is the seed card "the borrowed 4 minor".
- **The read-back gate matters here.** The one-finger version (only Bb3 to A3, movement 1) has no name on the page
  (it reads as a seven-note cluster), so the engine picks the `Gbm6/9` voicing, which the screen names.
- **The floor chip** (`B♭m11`, 0.41) appears with the count at 4, or with the "bass-only moves" filter: the same
  right hand over a new floor, exactly what the page's label was already hinting.
- **The doors** stay hidden until he has been in Db major for a minute and rests on this chord. Then one of them
  replaces chip 3.

**The bridge's register problem, measured on the same held chord.** The bridge's `spread` voicings with
`voice_lead`, started from this held voicing, moved 6 (`Dbmaj9/F`), 9 (`Ab7/Gb`, `Gbm6`), 12-13 (`Ab7`, `Bbm11`)
and 23 (`Cbmaj9`) semitones. That is why 2.8 adds the `near` voicer.

**A second, shorter case: holding a 5sus.** After a 5sus his log shows 6m 6 times, 2m 3, 4 2, 1 2 (13).
- HOME: 1. YOUR MOVE · SURPRISE: 6m.
- STRETCH: "let the sus land". His sus 4th falls a half step to the 3rd (`5sus4 -> 5^7`), then 1. That is the
  authentic cadence again, one finger away from what he already holds.

---

## 7. Receipts (checks before calling it built)

| # | Check | Pass |
|---|---|---|
| S1 | Transposition: 40 synthetic held voicings across all 12 keys | identical cores, numbers and reasons in every key; letters follow `spellForKey` |
| S2 | Read-back: every chip voicing in the fixture through the page's `Theory.detect` | `exact` or `enharmonic`, or the chip carries a reads-as line; zero silent mismatches |
| S3 | Collision: chip rects against the canvas box, `LAYOUT` label, Nashville row and cue boxes, banner (both forms), strip, staff, TikTok zones; both framings; margins 180, 220, 400 px; the 16:9 trail foot measured | zero intersections on canvas; column outside the canvas when the margin is 220 px or more; 60 px above the 16:9 trail foot |
| S4 | Clean recording: a seeded note stream with suggestions shown, 5 s REC, against the same run with suggestions off | every recorded frame MAE 0 (opt-in off) |
| S5 | Flicker: offline replay of synthetic sessions (his note-gap profile: p25/50/75 of 190/250/400 ms, pedal down 60-95%) through detect, tracker and `suggest.js` | chip-set changes with an unchanged reading: 0; chips shown during busy spells: 0; a stale chip visible after a reading change: under 120 ms |
| S6 | Honesty: habits payload and chips | no session ids or times in `habits.json` or the route; "your move" only with 3 plays in 2 sessions; stretch never "your move"; every word in the 3.4 table |
| S7 | Isolation: `window.__piano` counters while clicking every chip for 60 s | `sounding`, log events, tracker histogram and rarity events unchanged by Claude's notes |
| S8 | Privacy: `git status` after a habits build | no tracked file changed; tests use synthetic sessions only |

---

## 8. Questions for Daniel (each with a default)

1. **How many chips?** Default 3 (home, your move, one colour or stretch taking turns). Would 2 feel calmer?
2. **Keys that light:** only when you hover a chip (default), or always for the first chip?
3. **Clicking a chip plays "the move"** (your chord, then the suggestion). Or would you rather hear just the new
   chord?

## 9. For Vandor (not for Daniel)

- **Label versus function.** The page names his `4maj13#11` as `6m11/4` (1.4), so the engine must read chords with
  the practice rules (`readings.js` twin) until V2-F adds the templates. V2-F would also make chip names match the
  label more often.
- **Bridge register.** `voice_lead` anchors to the style's register (`REGISTER_WINDOW` around the plain voicing), not
  to held notes. Suggestions need the `near` style (2.8); it is J1's file.
- **Undercounting.** `practice progressions` lists moves played at least twice per session; the habits builder must
  use `min_count = 1` and weight by recency, or rare-but-real moves vanish.
- **No new log kinds.** Accept and ignore stats stay out of `performance.py` (batch-400 hazard).
- **Ownership overlap.** `glass.js` gains a `suggest` ghost state (J8's file). `piano.js`, `piano.html` and
  `piano.css` are J9's. V2-B also edits `deck.js` and `glass.js`: sequence S4 after it.
- **Unverified.** The keyboard toggle key (N) is unchecked against `KEYMAP`. The 16:9 rail and trail-foot height is
  still unmeasured (inherited from `design-ux.md` 5.3).
- **Privacy check done.** This file holds no session ids and no clock times. The scratchpad outputs used to write
  it (per-session `progressions`, `borrowed`, `keys` and `history` text) stay in the scratchpad.
