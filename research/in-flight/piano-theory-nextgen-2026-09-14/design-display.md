# Piano theory, next generation: the display

| | |
|---|---|
| Status | Design, 2026-09-14. One lens of the next-gen theory round: **how the page shows it**. No code edited, no server or browser started, nothing downloaded. |
| Asked for | Daniel, verbatim (Discord, from work): "Do you think we can brush up our chord and scale detection to show things in an even better way? I love where its at now. But I am excited to see what is the next Gen level we can bring it to!" |
| Built from | `arsenal/web/piano.js` (THEORY block, overlay `LAYOUT`, `drawLabel`, `drawNumbers`, `drawStaff`, `drawCueChip`, `overlay.update`, the colour section, `tickKey`, `spellForKey`, `drawGlass`, `KEYMAP`), `arsenal/web/piano/nashville.js` (`nashville()`, `createKeyTracker` state), `arsenal/web/piano/glass.js`, `arsenal/practice.py` (`classify`, `extended_readings`, `choose_reading`, `SCALES`), commit messages of `5cff2c61` and `de1334bf`, `research/in-flight/piano-jam-2026-09-14/jam-spec.md` and `design-ux.md`, `research/in-flight/piano-spectacle-2026-09-13/spectacle-spec.md`, `research/in-flight/piano-suggest-lights-2026-09-14/chord-suggestions.md` and `key-lights.md`. |
| Measured tonight | Scratchpad `theory-nextgen/` (not tracked): `display_lab.mjs` runs the page's own THEORY block (extracted verbatim) over the known gap voicings and prototypes alternative readings, note roles, tension and voice-leading pairs (`display_lab.out.txt`). `layout_lab.mjs` checks every proposed box against the existing and planned boxes in both framings, computes the key-ring turns for Daniel's key-change moves, and writes two SVG layout sketches (`layout-916.svg`, `layout-169.svg`). `py -m arsenal.practice keys`, `borrowed` and `colors` on the latest session (S6), read only. |
| Privacy | This file holds chord names, numbers, number sequences and counts only. Sessions are S1-S6 (S6 the latest). No session ids, clock times or transcriptions. |
| Scope | The display: what is drawn, where, when, recorded or not, and the settings. Which templates exist, how a reading is chosen, and how the key tracker decides belong to the engine lens of this round; section 8 lists what the display needs from it. |

---

## 0. The display in one screen

1. **The name stays the hero.** The big chord name, the note chips, the Nashville row and the grand staff keep their
   places and their look. Next-gen adds four quiet layers around them. A **Classic** view is byte-identical to tonight's
   page and always one key away.
2. **Anatomy under the chips.** A thin row under the note chips gives each note its job: `R 5 7 ◇9 3 ◇♯11 ◇13`. Shapes
   carry the family: plain for the chord's own tones, a diamond for colour tones, a ring for notes outside the key, and an
   underbar for the bass. Hover (or tap) any chip, notehead or key for a one-card explanation, which is never recorded.
3. **Two names when the notes have two.** When another reading is close, or is the classic misreading of an upper
   structure over a bass, the chip line ends in `ALSO B♭m11/G♭`. Click the name to see the readings with their roles
   and pin one.
4. **The scale of the moment.** The Nashville caption adds the scale when it is colour and earned: `IN D♭ MAJOR · G♭
   LYDIAN`. On the keys, small capsules on the key tops mark that scale, and a diamond marks its character note (the ♯11
   of a Lydian 4). Capsules are on the unrecorded glass by default; the recording can show them if Daniel chooses.
5. **The key ring.** It is the circle of fifths, numbered in the key, with 1 at the top. The key's seven chords sit in a
   lit window; borrowed chords sit on the flat side, one step outside it. The current chord's node lights in its root's
   pitch colour, and a fading trail joins the last six chords, so his loops draw shapes: the `1-4` line, the `6m-1-4`
   triangle. The page's pitch palette already walks the circle of fifths (hue = 200° + 30° per fifth), so the ring **is**
   the palette's own hue wheel. A modulation turns it.
6. **Key changes as a moment.** While the tracker banks toward a new key, a dashed window grows where that key sits. When
   the key switches, the ring's content swings round by the number of fifths (5 for his half-step drop, 3 for his
   minor-third drop) in 600 ms. The caption reads `NEW KEY · G MAJOR · DOWN A HALF STEP`. Chords of the old key say
   "from A♭ major", never "outside".
7. **Tension steps, not a gauge.** A row of eight small steps under the ring, one per chord, shows how much each chord
   leans. It is built from four parts a viewer can check: rub, pull (a dominant's tritone), notes outside the key, and a
   foreign bass. It moves only when the chord changes. A pull tick on the ring node points at where the chord wants to
   go.
8. **Voice-leading lines on the staff.** For 1.2 s after a change, the previous chord stays as a ghost column, joined to
   the new one: dotted lines for kept notes, solid lines for steps. His favourite `4maj13♯11 → 1maj9/3` shows five kept
   notes and one bass step, which is exactly his hand.
9. **No new colours, no new light.** Modes get words and shapes, never a hue. Hue belongs to the pitch palette,
   moonlight to Claude, gold to Legendary and amber to replays. Every theory mark is ivory ink drawn after bloom, or a
   key-top decal under the bloom threshold, so none of it touches the light budget.

---

## 1. What the page shows today, and where it falls short

### 1.1 What is already good (keep it)

- The name settles before it changes: 120 ms after a note-on, 300 ms after a release (`overlay.update`). A rolled chord
  never flashes partial names.
- The note chips are drawn in voicing order, in trail colours, so the name and the columns agree.
- The Nashville row says "in F major" or "outside F major", as a fact rather than a verdict, and dims while the key is
  unsure.
- The staff is a real grand staff with Bravura glyphs, with ledger lines and accidental stacking that never collide.
- The chord name, the number and the chips are spelled in the shown key (`spellForKey`).

### 1.2 Where the display is limited by what it is given

The page shows **one** reading and says nothing about the notes' jobs, the scale, the key's map, how chords move, or how
a key arrived. The gaps from the last reviews all surface on the display.

**Measured: today's namer against the gap voicings** (`display_lab.out.txt`, the page's own THEORY code; "proposed" means
the lab added `maj9#11`, `maj13#11`, `13sus4`, a no-3rd `11` and `13(11)` with guessed costs that the engine lens will
set):

| Voicing | Page reads today | Cheapest with proposed templates | Runner-up |
|---|---|---|---|
| his favourite 4 in Db: `Gb2 Db3 F3 Ab3 Bb3 C4 Eb4` | `Bbm11/Gb` (4.2) | `Gbmaj13#11` (3.0) | `Bbm11/Gb` (4.2) |
| `Ab2 C3 Eb3 G3 Bb3 D4` | `Cm9/Ab` (3.7) | `Abmaj9#11` (2.6) | `Bb13(11)/Ab`, `Cm9/Ab` (3.7) |
| `Ab2 G3 C4 D4 Bb4` (the same chord, no 5th) | `Bb13/Ab` (3.8) | `Abmaj9#11` (3.0) | `Bb13/Ab` (3.8) |
| `F2 C3 E3 A3 B3 D4 G4` | `Am11/F` (4.2) | `Fmaj13#11` (3.0) | `Am11/F` (4.2) |
| `G2 F3 A3 B3 C4 E4` (Lydian 4 over its 5) | `Fmaj7#11/G` (4.1) | `G13(11)` (3.1) | `Fmaj7#11/G` (4.1) |
| `C2 Bb2 F3 A3 D4` | `Bbmaj7/C` (2.7) | `Bbmaj7/C` (2.7) | `C13sus4` (3.3) |
| `G2 F3 A3 C4` (dominant 11 shape) | `F/G` (1.7) | `F/G` (1.7) | `G9sus4` (2.8), `G11` (2.9) |
| `G2 F3 B3 Ab4` | `Fdim/G` (2.7) | `Fdim/G` (2.7) | `G7b9` (2.8) |

**The S6 facts.**
- **Lydian 4.** It sounded 7 times, and the page's namer had no name for 5 of them. The other 2 it named `Eb11/Db` and
  `Abmaj9/Db`, so **every Lydian 4 in S6 was unnamed or named as another chord on screen**.
- **Chords outside the key are rare.** Borrowed chords took 4.1 s and chromatic ones 1.4 s of 227.8 s of chord time. An
  "outside" mark will therefore be a rare, meaningful event.
- **Voicings are wide.** An average chord holds 6.8 different notes, and 84% of chord time spans two octaves or more, so
  the anatomy row usually has 6 or 7 columns (4.4 checks the width).
- **Key change.** S6 moved from Ab major to G major, a half-step drop that the ring would show as one 5-step swing.

**Two findings that shape the display.**
1. **Everything downstream of the name follows the reading.** In the lab, tension, scale and anatomy all changed with it:
   - Under `Bbm11/Gb`, his favourite 4 gets the scale "Bb Aeolian" and the bass counts as foreign (tension 0.24).
   - Under `Gbmaj13#11` it gets "Gb Lydian" and a root bass (tension 0.15).
   - The same five notes `Ab D G Bb C` score 0.54 as `Bb13/Ab` (a dominant over its 7th, his gospel 5 over 4) and 0.10 as
     `Abmaj9#11`.
   - So the display must draw every layer from **one** chosen reading, and must show the other reading when it is close,
     because the bass really does decide.
2. **The key tracker is deliberately patient.** A new key must lead for about 5 s of playing (`holdSec`, doubled if that
   key was shown within 30 s). A key change therefore appears late unless the display shows the tracker *hearing* it.
   The tracker already exposes `candidate {name, tonic, mode, r, heldSec}`.

---

## 2. Principles (a builder checks every element against these)

1. **One hero, quiet helpers.** The chord name stays the largest ink on screen. No theory element is larger than the note
   chips (41 px in 9:16), except the ring's node numbers, which are 24 px on a 272 px ring.
2. **Earned, not always on.** Each helper appears only when it has something true to add:
   - the scale name for colour chords, once the mode's character note sounds;
   - the alternative reading only when it is close;
   - the key-change caption only at a switch;
   - the home caret only when home is not the key's 1.
3. **Motion only at a change.** While a chord is held, nothing theory-related moves. Fades already running may finish.
   Chord changes, key switches and a settled reading are the only triggers. Fades are 120-300 ms; the one swing is
   600 ms. Nothing breathes, blinks or scrolls in the frame.
4. **No new hues.** The pitch palette owns hue. Theory ink is the overlay's ivory `rgba(244, 241, 234, a)`, plus a dark
   ink for marks on white key tops. The reserved colours are in 3.9.
5. **No new light.** Overlay layers are composited after bloom, so they never glow and never enter `LIGHT_BUDGET`.
   Stage decals on key tops are `MeshBasicMaterial`, `toneMapped: false`, at most 0.35 linear, which is under the 0.9
   bloom threshold.
6. **Shapes carry the classes, everywhere the same.** The same vocabulary appears in the anatomy row, the key marks, the
   ring and the card:

   | Shape | Meaning |
   |---|---|
   | plain | the chord's own tone |
   | ◇ diamond | colour (9, 11, 13 and altered tones) |
   | ○ ring | outside the shown key |
   | underbar | the bass |
   | dashed | not yet or not sure (a candidate key, a stretch chip) |

   This matches the jam's marks (`design-ux.md` 6.4: dot, diamond, open ring).
7. **Honest words.** Every word can be checked against the notes. Unsure keys dim numbers, and the scale name hides.
   Wording guard as the riff analysis (jam-spec 11.4): never "wrong", "mistake", "error", "score", "best", "%",
   "should" or "correct".
8. **Daniel's alone.** Claude's cue notes, replays and ghosts never reach any theory layer (INT invariant 1). The display
   reads `overlay.shown`, `keyView` and `sounding`, and writes nothing back: no `detect()` input, no log, no tracker, no
   rarity.
9. **What you see is what you record.** REC never changes the theory view (as spectacle 5.3). The glass-only list
   (section 5) is fixed and short.

---

## 3. The elements

### 3.1 Chord anatomy: the roles row and the note card

**The roles row** is a new overlay layer, `anat`, directly under the note chips.

- **Columns.** Each chip gets a column as wide as `max(chip width, role width) + 14 px`, and the chip and its role are
  centred in it. When the row is on, the chip line uses these columns (when it is off, the chip line is drawn exactly as
  today).
- **Content.** The row holds one role per distinct pitch class, in the chip order.
- **Updates.** The row redraws only when the label redraws, and crossfades with the label's pop.

Role labels come from the primary reading's template tones (semitones and letter steps above the root, the `TONE_STEPS`
twin in `nashville.js`):

| Semitones | Letter steps | Role | Family | Drawn |
|---|---|---|---|---|
| 0 | 0 | `R` | root | 700, ink 0.94 |
| 3 / 4 | 2 | `♭3` / `3` | 3rd (shape) | 700, ink 0.94 |
| 5 / 2 | 3 / 1 in sus chords | `4` / `2` | 3rd (shape: it replaces the 3rd) | 700, ink 0.94 |
| 6 / 7 / 8 | 4 | `♭5` / `5` / `♯5` | 5th | 500, ink 0.55; `♭5` and `♯5` count as colour |
| 9 | 5 in `6`, `m6`, `6/9` | `6` | 7th family (shape) | 700, ink 0.94 |
| 9 (in dim7) / 10 / 11 | 6 | `𝄫7` / `♭7` / `7` | 7th (shape) | 700, ink 0.94 |
| 1 / 2 / 3 | 1 | `♭9` / `9` / `♯9` | colour | ◇ + 600, ink 0.8 |
| 5 / 6 | 3 | `11` / `♯11` | colour | ◇ + 600, ink 0.8 |
| 8 / 9 | 5 | `♭13` / `13` | colour | ◇ + 600, ink 0.8 |

Marks:
- **Outside the key:** a pitch class not on the shown key's scale gets ○ instead of ◇ (outside wins), while the key is
  "sure", "fair" or locked. Unsure or no key: no ○.
- **Bass:** a 3 px ivory underbar, 70% of the column width, 4 px under the role baseline.
- **Glyphs:** ◇ and ○ are drawn as 8 px vector shapes (`ctx.moveTo` paths), never font glyphs. Flats and sharps use the
  label's music font, inline (not raised), at 0.8 of the row size.
- **Clusters and intervals:** a cluster has no roles, and the row stays empty. An interval shows `R` and its interval
  number (`♭3`, `5`, `♯11`). A single note shows nothing.

**Also reads** (3.2) rides at the end of the **chip line**, in today's caption slot. It uses the caption's font (small ×
0.72, caps, ink 0.55): `ALSO B♭m11/G♭`, with the chord's flats, sharps and suffix set by `cueTextRuns` rules.

**The note card** is a DOM element and never recorded. It is `<div id="theory-card">` inside `.stage`, 280 px wide, with
the panel look of the deck. It opens on:
- hovering a note chip, a role, a staff notehead or a sounding key for 250 ms (hit rects come from `__piano.theory.layout()`,
  converted from reference pixels by `framing.w / canvas CSS width`; keys are ray-cast);
- a touch tap, which holds the card 3 s;
- a KeyLab pad in v2 (with the jam's pad learn).

It closes 400 ms after the pointer leaves.

```
+-----------------------------------------------+
| C4   ◇ ♯11 of G♭maj13♯11                      |
| the raised 4th: the Lydian note of this 4     |
| in D♭ major it is the 7 (a note of the key)   |
| over the bass G♭: a tritone                   |
| in B♭m11/G♭ (also) it is the 9                |
+-----------------------------------------------+
```

- **Lines:** at most 5, each a fact about the notes: role and family word; what that family does (a fixed one-line
  gloss per role); its degree in the key; its interval over the bass; its role in the alternative reading.
- **A key that is not sounding:** "not in this chord · in G♭ Lydian it would be the 13".
- The card follows the reading pin (3.2).

### 3.2 Alternative readings

**When `ALSO` shows** (setting `close`, the default), all three must hold:
1. **A runner-up exists** in the engine's readings (section 8) with a **different root or bass**. A different suffix on
   the same root and bass never shows; the roles row already says that.
2. **It is close, or it is a known confusion:**
   - close: it costs at most **0.6** more than the primary; or
   - known confusion, at most **1.5** more: one reading is an upper structure over a foreign bass and the other is rooted
     on that bass (`F/G` against `G11`; `Bbmaj7/C` against `C13sus4`; `Bbm11/Gb` against `Gbmaj13#11`).
3. **The label has settled for 400 ms.** Then `ALSO` fades in over 250 ms.

Setting `always` shows the best runner-up whenever one exists; `off` never shows it.

**What the lab cases would show** (after the engine lens adds the templates):

| Notes | Big name | Chip line ends |
|---|---|---|
| his favourite 4 | `G♭maj13♯11` | `ALSO B♭m11/G♭` (+1.2, known confusion) |
| Lydian 4 over its 5 | `G13(11)` | `ALSO Fmaj7♯11/G` (+1.0, known confusion) |
| `C2 Bb2 F3 A3 D4` | `B♭maj7/C` | `ALSO C13sus4` (+0.6) |
| `G2 F3 A3 C4` | `F/G` | `ALSO G11` (+1.2, known confusion: the missing dominant-11 name, now visible) |
| `G2 F3 B3 Ab4` | `Fdim/G` | `ALSO G7♭9` (+0.1) |
| `Ab2 D3 G3 Bb3 C4` | `A♭maj9♯11` | `ALSO B♭13/A♭` (+0.8, known confusion: the gospel 5 over 4) |

**Reading picker.** Clicking the big name on the canvas opens a DOM popover beside it (never recorded):

```
+---- these notes read as ------------------------------+
| (•) G♭maj13♯11    4maj13♯11    the 4, Lydian           |
|     R  5  7  ◇9  3  ◇♯11  ◇13                          |
| ( ) B♭m11/G♭      6m11/4       a 6m over the 4          |
|     ◇♭13  ♭3  5  ♭7  R  ◇9  ◇11                        |
| ( ) D♭maj13/G♭    1maj13/4     the 1 over the 4         |
|  [ Pin for these notes ]   [ Hear ]   [ Reset pins ]    |
+-------------------------------------------------------+
```

- **Contents:** at most 3 readings. Each shows its roles, its number in the shown key, and a plain gloss from the reason
  vocabulary.
- **Hear** plays the notes Daniel holds through Claude's voice. Source is `claude`, so the notes never reach `sounding`.
- **Pin:** a pin is keyed by `pitch-class set + bass pitch class`, stored in `arsenal.piano.theory.pins` (at most 200,
  the oldest dropped).
  - It changes what the **display** shows for those notes: the big name, the roles, the Nashville row, the scale, the
    ring node and tension.
  - It **never** changes the practice log's chord event, the key tracker, rarity or suggestions. Those keep the engine's
    primary, which keeps every analysis reproducible.
  - While a pin is active, the HUD line (not recorded) says `pinned`.
- **Receipts only:** a pin can be refused by `?pins=off`.

### 3.3 Scale and mode

**Which scale.** The display shows the scale the engine gives for the primary reading in the shown key (section 8). This
is the live twin of the jam def's `scale` and `scale_name` (MUSIC 9.5). The lab's reference behaviour:
- **Diatonic chord:** the key's own scale seen from the chord root (4 → Lydian, 2m → Dorian, 5 → Mixolydian, 6m →
  Aeolian, 3m → Phrygian, 7° → Locrian, 1 → Ionian).
- **Otherwise:** the mode that changes the fewest notes of the key while holding every chord tone. For example, `Abm6` in
  Eb gives Ab melodic minor, 2 notes changed.

**The caption** extends the Nashville row's small-caps key caption, after a ` · `:

| Setting | Shown when |
|---|---|
| `colour chords` (default) | the scale is not the key's own Ionian or Aeolian over its 1 **and** passes the naming gate |
| `always` | passes the naming gate (so `IN C MAJOR · D DORIAN` over a Dm7 too) |
| `off` | never |

- **Naming gate** (the live twin of the riff's gate): the mode's character note sounds. Lydian needs the ♯4, Mixolydian
  the ♭7, Dorian the natural 6 over a minor 3rd, Aeolian the ♭6, Phrygian the ♭2, Locrian the ♭5, Lydian dominant the
  ♯4 and ♭7, melodic minor the natural 6 and 7 over a minor 3rd. It counts if the note is in the chord, or was struck in
  the last 2 s over the same reading. Otherwise the caption stays as it is today.
- **Timing:** it appears 700 ms after the reading settles (the suggestions' dwell) and fades in over 250 ms. A reading
  change fades it out over 120 ms at once.
- **Unsure key:** hidden.
- **Examples:**
  - `4maj13♯11   IN D♭ MAJOR · G♭ LYDIAN`
  - `4m6   BORROWED · IN E♭ MAJOR · A♭ MELODIC MINOR`: a borrowed chord's caption leads with the class word (3.5)
    instead of "outside".

**Scale on the keys.** Setting: `off` / `glass` (default) / `stage`.
- **Capsule:** a small capsule on each key top of the current scale, at the back of the key (from 8% to 16% of the key's
  length from its back edge, 36% of its width, centred). The back edge is chosen because hands cover the fronts, and the
  9:16 follow camera sees the backs.
- **Ink:** `rgba(24, 26, 34, 0.55)` on white keys, `rgba(244, 241, 234, 0.5)` on black keys.
- **Character note:** a diamond, 30% of the key width, instead of a capsule.
- **Scale tones outside the shown key** (the Cb of `Abm6` in Eb): the capsule splits into two dots, the "outside" shape.
- **Sounding keys:** the capsule gives way to the note-class mark (3.4).
- **Crossfade:** 200 ms on a scale change. The scale persists while the reading does; silence fades the capsules out with
  the label (0.62 alpha at rest, gone at 4.5 s).
- **Glass (unrecorded):** drawn through `glass.js` face projection (the rest-pose top face, the same homography as the
  ghost rims). There are **at most 24 keys** per frame, taken nearest the sounding notes' centroid, so a 16:9 view with
  about 33 scale keys in sight shows the 24 around the hands.
- **Stage (recorded):**
  - one `InstancedMesh` of decal quads 0.002 u above each key top, parented to the key's press motion, so a pressed key
    carries its capsule down;
  - alpha-blended, depth-tested, at most 0.35 linear;
  - AA through an analytic `fwidth` edge (spectacle 5.1 rule 7);
  - one draw call, precompiled with the spectacle effects.
- **Never** a light, a glow, a key-front lip mark or anything on the key fronts (spectacle 5.1 rule 9).

```
 back edges of the key tops, D♭ major, a held G♭maj13♯11 (G♭ Lydian), his notes G♭ D♭ F A♭ B♭ C E♭

  key       C   D♭  D   E♭  E   F   G♭  G   A♭  A   B♭  B   C   D♭  D   E♭
  scale     ◆   ▬       ▬       ▬   ▬       ▬       ▬       ◆   ▬       ▬       ◆ = C, the ♯11 (character)
  sounding  ◇   ●       ◇       ●   ●       ◇       ●               ●           ● chord tone  ◇ colour  ○ outside
```

### 3.4 Note classes on the keys (his sounding notes)

- **Marks:** every key Daniel is sounding (finger or pedal) gets its class mark at the capsule position.
  - Shapes: ● a 7 px dot for the chord's own tones, ◇ a 9 px diamond for colour tones, ○ an 8 px open ring for notes
    outside the shown key.
  - Classes: the same families as the roles row.
  - Drawn two-tone, a dark core with an ivory edge, so the mark reads on any pitch-lit key.
- **Surface:** marks follow the Scale-on-keys setting (glass or stage).
- **Lifetime:** a mark lives while its note sounds and fades 0.6 s after its sound ends. At most 12 at once, the newest
  winning, as the jam's marks do.
- **During a jam Loop or Try**, the key marks switch to the jam's reference: the loop's NOW chord, drawn on the glass
  always (`design-ux.md` 6.4). The roles row keeps describing Daniel's own label (jam-spec C11: the label is his alone).
- **Not on the staff.** Noteheads keep their pitch colours and the staff stays as readable as today. The roles row and
  the card carry the classes.

### 3.5 The key ring

**Geometry.** Twelve root positions a fifth apart, numbered in the shown key, with **1 at 12 o'clock** and clockwise
sharpward:

```
                          1
                  4               5
            ♭7                          2m
          ♭3              D♭              6m          ← the key's letter, faint, in the centre
            ♭6                          3m
                  ♭2              7°
                         ♯4
```

| Part | Look |
|---|---|
| Key window | a 10 px ivory arc at 0.30 behind the seven diatonic positions (4 through 7°) |
| Diatonic nodes | 22 px radius discs, `rgba(12, 13, 18, 0.85)`, a 2 px ivory rim at 0.6, the number (24 px, 700) with its diatonic quality: `1 5 2m 6m 3m 7° 4` |
| Other positions | 6 px dots at ivory 0.22. Their number (16 px, ink 0.45) appears outside the ring at radius + 26 only when that position was visited in the last 60 s |
| Flat side | a dashed arc at 0.15 behind `♭7 ♭3 ♭6 ♭2`, the borrowed shade: one step outside the window is a shade of the parallel minor |
| Centre | the key's letter, 44 px, 800 weight, ivory 0.28 (`D♭`); in minor numbering "tonic", `C♯m` |
| Scrim | a radial disc `rgba(1, 2, 6, 0.5)` at the centre fading to 0 at radius + 24, like the staff's scrim, so the columns behind stay visible |

**The chord's node.**
- **Light.** The current chord's node fills with its root's pitch colour (`noteCss` with the overlay lightness floor
  0.68), its number in dark ink `rgba(8, 8, 12, 0.9)`. On a change it pulses in size once: 1.0 → 1.12 → 1.0 over 200 ms,
  size only, never brightness (the jam's `found` rule).
- **Quality beyond the diatonic one.** The label takes the chord's number without extensions: `4m` on the 4 node, `2⁷`
  on the 2 node.
- **Outside the key.** A borrowed or chromatic chord gets a dashed rim (the "outside" shape).
- **Pull tick.** A secondary dominant (`classify` → `secondary dominant`, target known) gets an 11 px chevron on its rim
  aimed at its target node, one step anticlockwise for a V of something. A backdoor `♭7⁷` aims clockwise at 1. The tick
  length follows the chord's `pull` part (3.7). A 0.45 sus pull draws it at half length.
- **Could lean.** When the alternative reading (3.2) has pull ≥ 0.5 more than the primary (`A♭maj9♯11` also reading
  `B♭13/A♭`), the tick is drawn hollow.

**Home caret.**
- **Shape:** a 12 px ivory triangle at radius + 30, pointing at the node that sounds like home.
- **Which node:** the one with the most chord time over the last 16 s of playing, with at least 2 arrivals.
- **When:** only when that node is **not** 1.
- **What it covers:**
  - the Aeolian loop the tracker numbers in the relative major (home caret on 6m, caption `A AEOLIAN`);
  - the Dorian vamp numbered in the key of the IV (caret on 2m, `D DORIAN`);
  - a Mixolydian vamp (caret on 5).
- **Numbers never change:** they follow the tracker and the Minor setting. The caret and the caption say where home
  sounds. The caption appears under the naming gate (3.3).

**The trail.**
- **Segments:** one straight line between consecutive chord nodes, per label change (not per voicing). A repeated
  reading on the same node adds nothing.
- **Look:** 3 px in 9:16 (2.5 in 16:9), an OKLab gradient from the old root's pitch colour to the new one's, drawn with
  `noteCss` at alpha a.
- **Fade:** a = 0.55 · 0.5^(age / 2.5 s). A segment is removed below 0.04 or after 8 s. At most **6** segments (setting
  4 / 6 / 8).
- **Growth:** a new segment grows from the old node to the new one over 180 ms, a comet with a bright head of 1.5x width.
- **Loops etch:** a segment that repeats within 16 s adds +0.1 to its peak alpha, capped at 0.7. A four-chord loop
  settles into a steady shape and needs no counter.
- **Cadence:** a V⁷ → I, IV → I or ♭VII → I arrival the tracker **credits** (section 8) pulses the 1 node in size once
  over 240 ms. An arrival the tracker leaves undecided (I → I⁷ → IV) gets no pulse: the display never claims more than
  the tracker heard.
- **His loops, drawn** (moves from the six-session counts in `chord-suggestions.md` 1.1):
  - `1 4 1` and `4 1 4` are one short chord between 12 and 11 o'clock, bright from repetition;
  - `6m 1 4` is a triangle 3 → 12 → 11 o'clock;
  - `4 5 6m` is a triangle 11 → 1 → 3 o'clock;
  - the deceptive `5 → 6m` is a two-step chord on the right.

**Interaction** (the ring is also a map to play from; DOM hit testing on the canvas box or the side ring; nothing
recorded):

| Gesture | Effect |
|---|---|
| hover a node 250 ms | ghost keys of that chord on the glass (the `suggest` ghost state of `chord-suggestions.md` 3.3), voiced near his hands when he holds a chord (the `near` voicer), else the card-style `spread` in his register |
| click a node | Claude plays it: the chord name and number as the cue label, `keys` timbre, velocity 44, `source: claude`. It never reaches `sounding`, the log, the tracker or rarity |
| shift-click | Claude plays the held chord, then that chord (the suggestions' "move") |
| click the centre letter | opens the Key select (the top bar's), where a key can be locked |

**Jam and suggestions on the ring** (v2 of this display): while a Loop runs, the loop's NOW and NEXT roots get moonlight
hollow rims on the glass, at the projected ring box. They are glass-only because they are Claude's. A hovered
suggestion chip's core number gets a dotted rim on its node, also on the glass.

### 3.6 Key-change moments

**Hearing a new key.**
- **Trigger:** while the tracker's `candidate` exists for at least 1 s and no key is locked (by hand, or the jam key of
  jam-spec 8.10).
- **What shows:** a **dashed window arc** where the candidate's seven diatonic positions sit relative to the shown key.
  Its alpha is 0.25 · min(1, heldSec / needSec), which needs `needSec` from the tracker (section 8).
- **No words, no numbers change.** The dashed window disappears over 300 ms if the candidate drains away.

**The switch.**
1. **Numbers stay put.** 1 is always at the top. What turns is the content: the trail, the dashed window and the
   visited-position dots. It rotates by the signed number of fifths between the two tonics, the shorter way (a tritone
   turns sharpward). The lab's counts for his moves:

   | Move | Fifths | Ring turns |
   |---|---|---|
   | down a minor third (his hinge, twice) | 3 sharpward | 90° anticlockwise |
   | down a half step (S6, and a hinge) | 5 sharpward | 150° anticlockwise |
   | up a whole step | 2 sharpward | 60° anticlockwise |
   | up a fourth | 1 flatward | 30° clockwise |
   | up a half step | 5 flatward | 150° clockwise |
   | to the parallel minor, numbered as its relative major | 3 flatward | 90° clockwise |

2. **Tween:** 600 ms, cubic ease in and out, no overshoot. The dashed window lands on the fixed window and becomes solid
   as the old window's arc fades. The centre letter crossfades (`A♭` → `G`) over the same 600 ms. The trail keeps its
   pitches: the old `D♭` segment end (the old 4) swings to 6 o'clock, where D♭ sits in G major (♯4). His next chord, C,
   lands at 11 o'clock (the new 4). The line between them is the long diagonal of a far move.
3. **Caption:** the Nashville row's caption becomes `NEW KEY · G MAJOR · DOWN A HALF STEP` for 2.4 s, then
   `IN G MAJOR`.
   - Interval words come from the tonic motion: half step, whole step, minor third, major third, fourth, "a tritone
     away", or "same notes, new home" for relative keys.
   - Overflow order: drop `NEW KEY ·`, then the interval.
   - If a rarity banner holds the row when the switch lands, the caption waits and shows when the row returns, but only
     if the switch was at most 4 s earlier. The swing itself never waits.
4. **Old chords are not outside.** For 8 s after a switch, a chord outside the new key but diatonic in the previous one
   is captioned `FROM A♭ MAJOR`, drawn without ○ marks and without a dashed rim. While a candidate is at least half-banked,
   a chord diatonic in the candidate but outside the shown key is captioned `TOWARD G MAJOR`. This is the display's
   answer to the review gap "a chord from the old key at a key change is labelled borrowed in the new key".

```
   hearing (tracker banking)      the swing (600 ms)            landed
          1                              1                           1
      4       5                      4       5                   4 ←C    5
   ♭7   ,- - - -.  2m            ♭7     ↺ 5 fifths  2m        ♭7            2m
  ♭3   ( A♭ ·  G )  6m          ♭3       ·         6m        ♭3      G       6m
   ♭6   `- - - -'  3m            ♭6                3m         ♭6      /      3m
      ♭2  dashed  7°                ♭2         7°               ♭2  /    7°
          ♯4 window                      ♯4                       D♭ (old 4)
                                                               NEW KEY · G MAJOR · DOWN A HALF STEP
```

### 3.7 Tension

**The number.** T is between 0 and 1, from pitch content read through the display's primary reading. It never uses
velocity: loudness is not tension (as rarity's tier). Weights are illustrative, to be tuned by ear on the first night:

```
T = 0.30·rub + 0.35·pull + 0.20·outside + 0.15·bass
  rub      min(1, 0.5·(half-step pairs + tritone pairs among the pitch classes) / 3)
  pull     1 when the reading's root (or the bass, when it is the root) has its major 3rd and ♭7 (a dominant's tritone);
           0.45 for a sus dominant (4th and ♭7, no 3rd of either kind); else 0
  outside  min(1, pitch classes off the shown key's scale / 2); 0 while the key is unsure or absent
  bass     0 on the root; 0.25 on the 3rd or 5th; 0.6 on anything else (a 7th, a colour, a foreign bass)
```

**Measured in the lab:**

| Chord (key) | T | Parts (rub, pull, outside, bass) |
|---|---|---|
| Cmaj9 (C) | 0.05 | 0.17, 0, 0, 0 |
| Abm6, the borrowed 4m (Eb) | 0.15 | 0.17, 0, 0.5, 0 |
| his favourite 4 as `Gbmaj13#11` (Db) | 0.15 | 0.5, 0, 0, 0 (as today's `Bbm11/Gb`: 0.24) |
| G7 (C) | 0.40 | 0.17, 1, 0, 0 |
| G13(11), Lydian 4 over its 5 (C) | 0.50 | 0.5, 1, 0, 0 |
| G7b9 (C), read `Fdim/G` | 0.64 | 0.33, 1, 0.5, 0.6 |

| Progression | Steps |
|---|---|
| C C7 F B♭7 C (the backdoor, a known tracker gap) | 0 → 0.50 → 0 → 0.60 → 0 |
| his lift in Db: 4maj13♯11 → 5⁹/4 → 1maj9/3 | 0.15 → 0.49 → 0.09 |
| Cmaj9 A7♭9 Dm9 G13 Cmaj9 | 0.05 → 0.74 → 0.05 → 0.45 → 0.05 |

**Why steps, not a gauge.** The spectacle judges cut every in-canvas meter, gauge and combo for rarity because they
gamify. Tension is a description of harmony, and it is drawn to read like one.

**Tension steps.**
- **Shape:** a row of the last **8** chords, one step each, newest on the right. Each step is a 14 px wide rounded bar
  with its height = T of the box height, ivory 0.5, and 10 px between steps. The newest bar's top has a 5 px dot.
- **Motion:** the row shifts only when the label changes. It never scrolls with time.
- **Arrival:** a step whose chord is a credited arrival (the 1 pulse) gets a 2 px ivory baseline tick.
- **Words:** they appear only in the card. Hovering a step opens it: `G13 · pulls toward C (its 3rd and 7th, a
  tritone) · one colour rub (the 13 against the 7th)`. Tone words: `rest` under 0.15, `colour` 0.15-0.35, `lean`
  0.35-0.55, `pull` at 0.55 or more.

**Where.** Setting: `off` / `side` (DOM, default) / `frame` (under the ring, with the Map view or Full).

### 3.8 Voice-leading lines on the staff

- **Trigger:** each time the label commits a new name (the label pop), the staff draws the **previous** chord as a ghost
  column beside the new one, and joins them. Setting: `off` / `on change` (default).
- **Ghost column:**
  - at `noteX − 6.5·s`; noteheads at 35% alpha in their pitch colour, chroma reduced to 40%;
  - no accidentals; ledger lines at 35%, at most one beyond the staff.
- **Pairing:** a minimum-movement pairing of the two sorted voicings (dynamic programming; a voice with no partner costs
  7 semitones, as `display_lab.mjs` `voiceLead`). Pairs crossing between the treble and bass staves draw no line.
- **Lines** run from the ghost head's right edge to the new head's left edge:
  - **Kept note:** a dotted horizontal line (3 px dash, 5 px gap), ivory 0.45, 1.5 px.
  - **Step** (1-2 semitones): a solid slanted line, ivory 0.45, 1.5 px.
  - **Leap** (more than 2): no line. **Lifted voice:** its ghost head only. **Arriving voice:** nothing extra.
- **Timing:** lines and ghost appear with the pop, hold 1.2 s and fade over 0.6 s. A re-commit within 0.4 s (a rolled
  chord settling) redraws them.
- **Collision rule:** computed per draw. The ghost column is omitted when any of its note boxes comes within 0.3·s of the
  new chord's accidental glyph boxes. The staff never gains ink over its accidentals.
- **During a Try:** off, because the ghost rims' `hold` state already shows kept notes.
- **Measured pairings:**

  | Change | Kept | Steps | Leaps | Lifted | Arriving |
  |---|---|---|---|---|---|
  | `4maj13♯11 → 1maj9/3` in Db (his favourite move) | 5 | 1 (the bass G♭ → F) | 0 | 1 (B♭) | 0 |
  | `G13 → Cmaj9` | 1 | 2 | 1 | 0 | 1 |
  | `Ebmaj9 → Abm6` | 0 | 3 | 1 | 1 | 0 |

```
 treble ═══════════════════════════════════════════════
              (E♭)· · · · · · · · · · E♭        kept: dotted
              (C) · · · · · · · · · · C
 bass   ═══════════════════════════════════════════════
              (B♭)                              lifted: ghost only
              (A♭)· · · · · · · · · · A♭
              (F) · · · · · · · · · · F
              (D♭)· · · · · · · · · · D♭
              (G♭)──────────────────╲ F         step: solid
```

### 3.9 The colour and mode language

| Ink | Means | Owner |
|---|---|---|
| Pitch palette: OKLCH hue = 200° + 30° × fifths index of the pitch class, gamut-mapped | Daniel's notes, keys, trails, chips, noteheads; **chord roots on the ring**; trail gradients | page (unchanged) |
| Moonlight `#C8DCFF` | Claude's hand, chips and cues | jam |
| Ghost rims `#3E5277` on ivory, `#C7D6F2` on black | ghosts (target, incoming, hold, suggest) | jam, suggestions |
| Gold | Legendary, and nothing else | spectacle |
| Amber `rgba(242, 181, 74)` | `YOU`, replays | cue chip |
| Ivory `rgba(244, 241, 234, 0.15-0.94)` | every theory word, role, arc, rim, line, step | **this design** |
| Dark ink `rgba(24, 26, 34, 0.55)`, dark core `rgba(8, 8, 12, 0.9)` | marks on white key tops; numbers on lit ring nodes | **this design** |

**Modes get no colour.** A mode is named in words (the caption, the card) and drawn as shapes:
- its window on the ring (the key's seven positions);
- where the chord's root sits in that window;
- the character-note diamond on the keys.

**Why the ring cannot fight the palette.** The palette's hue already steps 30° per fifth (`noteLch`), so neighbouring
ring positions are neighbouring hues. The ring is the palette's own wheel: a key's window is a 210° arc of hues, and a
modulation turns the wheel. The page's colour comment ("a modulation visibly shifts the palette") gains a map to point
at.

**Light budget.** Unchanged by construction.
- Overlay layers are composited after `OutputPass`.
- Stage key-top decals are at most 0.35 linear, alpha-blended and small in area. They are not trail light, and
  `uDensity` never reads them.
- The receipt D-R8 checks mean luma.

---

## 4. Placement

All coordinates are reference pixels (1080 × 1920 or 1920 × 1080), as `LAYOUT`. New layers are made with `makeLayer()`,
drawn under the adaptive-resolution transform once spectacle phase 0 lands. The trail and steps are thin quads in
`overlayScene`, with per-segment alpha as uniforms, so fading needs no texture redraw.

### 4.1 9:16

| Element | Box | Size, baseline | View | Recorded |
|---|---|---|---|---|
| TikTok header | y 0-150 | never text (the CLAUDE chip is glass during REC) | | zone |
| CLAUDE chip (INT) | x 50-1030, y 28-144 | unchanged | | per jam view |
| Chord label | x 10-1070, y 148-488; glyphs y ≈ 205-365 | unchanged | all | yes |
| Note chips (+ `ALSO`) | y ≈ 397-427 ink (392-436 box) | chip line baseline ≈ 427; `ALSO` in the caption slot | anatomy+ | yes |
| **Roles row** (`anat`) | x 10-1070, y 438-472 | 26 px, baseline 462, ink ≈ 443-462 (16 px under the chips' ink) | anatomy+ | yes |
| Nashville row | x 10-1070, y 471-601 | unchanged; ink top ≈ 493 (31 px under the roles' ink); caption gains scale / key-change text | all | yes |
| Rarity banner, phrase card | y 478-576 (compact 486-536) | unchanged; borrows the Nashville row | | yes |
| Staff (Classic, Anatomy) | x 110-970, y 500-1100 | unchanged, + ghost column and lines | | yes |
| **Staff, theory panel** (Map, Full) | x 110-620, y 500-1100 | `s` 24 as today; chord column at 0.66 of the staff width instead of 0.6 | map, full | yes |
| **Key ring** (Map, Full) | x 636-908, y 664-936; centre (772, 800) | node ring radius 104, nodes 22, numbers 24 px; ink right edge ≈ 898 | map, full | yes |
| **Tension steps** (Full, or `frame`) | x 662-882, y 948-974 | 8 steps, 14 px wide | full | yes |
| Pedal mark | x 177-345, y 990-1086 | unchanged (inside the panel staff too) | | yes |
| Jam strip (v2 stage), suggestions opt-in | x 180-900, y 1108-1192 | unchanged | | per their specs |
| Rail, keys | y ≈ 1370; keys 1370-1590 | capsules and marks on key tops (stage setting) | full | stage only |
| TikTok buttons | x ≥ 916, y 800-1596 | ring box 8 px clear, ink 18 px clear | | zone |
| TikTok caption band | y ≥ 1596 | nothing added | | zone |

**Wireframe: Anatomy view, 9:16** (Classic is this without the roles row, the `ALSO` and the staff lines)

```
        x 0         270         540         810        1080
 y    0 +------------------------------------------------------+
        | . . . . . . . TikTok header: no text . . . . . . . . |
  28-144|      ( CLAUDE · A♭maj7♯11    4maj7♯11 in E♭ major )  |  cue chip (glass while REC)
    150 +- - - - - - - - - - - - - - - - - - - - - - - - - - - +
    205 |                                                      |
        |                 G♭maj13♯11                           |  the name (170 px), unchanged
    365 |                                                      |
    427 |     G♭  D♭  F   A♭  B♭  C    E♭      ALSO B♭m11/G♭   |  chips + ALSO
    462 |     R   5   7   ◇9  3   ◇♯11 ◇13                     |  roles row (new)
        |     ‾‾                                               |  bass underbar
    552 |     4maj13♯11    IN D♭ MAJOR · G♭ LYDIAN             |  Nashville row (the banner borrows it)
    620 |  𝄞 ════════════════════════════════════════════   |B |
        |           (E♭)· · · · · · E♭                        |T |  staff: ghost column + lines, 1.2 s
        |           (C) · · · · · · C                         |N |
    800 |  𝄢 ════════════════════════════════════════════   |S |
        |           (G♭)────────╲ F                           |  |
    980 |      Ped                                            |  |
   1108 |       [ jam strip v2 / suggestions opt-in ]         |  |
   1370 |================== rail ===============================|
        |  keys (capsules and marks on the glass by default)   |
   1596 | . . . . . . . . TikTok caption band . . . . . . . . .|
   1920 +------------------------------------------------------+
```

**Wireframe: Map view, 9:16** (Full adds the tension steps in frame and the capsules on the stage keys)

```
        x 110                 620 636            908 916   1080
    552 |     4maj13♯11    IN D♭ MAJOR · G♭ LYDIAN             |
    586 |  ,---------------------.                          |T |
    620 |  | 𝄞 ═══════════════   |           1              |i |
    664 |  |                     |      4    ●    5         |k |  ring x 636-908, y 664-936
        |  |     (E♭)· · · E♭    |   ♭7    ╱       2m       |T |  ● = the lit 4 node (G♭'s pitch colour)
    800 |  |     (C) · · · C     |  ♭3   ●━━━ D♭    6m       |o |  trail: 1→4 (bright), 4→5 (newest)
        |  | 𝄢 ═══════════════   |   ♭6            3m       |k |
        |  |     (G♭)───╲ F      |      ♭2      7°          |  |
    936 |  |                     |           ♯4             |b |
    948 |  |  Ped                |    ▁  ▃  ▂  ▅  ▁  ▂  ▁  ▁ |t |  tension steps (Full)
   1100 |  '---------------------'                          |n |
   1108 |       [ jam strip v2 / suggestions opt-in ]        |s |
```

### 4.2 16:9

| Element | Box | Size, baseline | View | Recorded |
|---|---|---|---|---|
| Chord label | x 50-950, y 41-351, left-aligned | unchanged; chip line baseline ≈ 287 | all | yes |
| **Roles row** | x 50-950, y 296-326 | 22 px, baseline 316 (ink ≈ 41 px above the Nashville ink top ≈ 357) | anatomy+ | yes |
| Nashville row | x 50-950, y 332-452 | unchanged; baseline 406 | all | yes |
| Rarity banner | x 60-940, y 344-440 | unchanged | | yes |
| CLAUDE chip, suggestions on glass | x 50-950, y 464-568 | unchanged | | per jam view |
| **Key ring** | x 968-1216, y 156-404; centre (1092, 280) | node ring radius 96, nodes 20, numbers 22 px | map, full | yes |
| **Tension steps** | x 988-1196, y 416-440 | 8 steps, 12 px wide | full | yes |
| Staff | x 1240-1880, y 12-532 | unchanged (no narrowing in 16:9), + ghost column and lines | all | yes |
| Jam strip (v2 stage) | x 1240-1824, y 548-628 | unchanged | | per jam view |
| Rail, keys, column tops | **unmeasured** (as `design-ux.md` 5.3) | receipt D-R2 measures them and requires the ring and steps to stay above the tallest column top at rest, or accepts the scrim over columns | | |

```
   x 50                     950 968        1216 1240                  1880
 y  41 +----------------------------------------------------------------+
       |  G♭maj13♯11                   |      1       | 𝄞 ═══════════   |
       |                               |  4   ●   5   |    o  (E♭)· · ·E♭|
   287 |  G♭ D♭ F A♭ B♭ C E♭  ALSO B♭m11/G♭ ♭7 ╱  2m  |    o            |
   316 |  R  5  7 ◇9 3 ◇♯11 ◇13        | ♭3 ●━D♭  6m   | 𝄢 ═══════════   |
   406 |  4maj13♯11  IN D♭ MAJOR · G♭ LYDIAN ♭2  7°  3m |  (G♭)──╲ F       |
   440 |                               |  ▁ ▃ ▂ ▅ ▁ ▂  |                 |
   516 |  ( CLAUDE · ... )             |              | [ jam strip v2 ] |
       |                                                                |
       |        columns rise from the keys (rail height unmeasured)     |
  1080 +----------------------------------------------------------------+
```

### 4.3 The side column (DOM, never recorded)

When the ring or steps are not in the frame (the Classic and Anatomy views, or the `side` setting), and the stage has a
left margin of at least 220 CSS px, they live in the left margin column. `chord-suggestions.md` 3.1 already puts that
column there for suggestion chips. The deck stays on the right.

```
 +---- left margin (DOM) ------------+  +------ canvas 9:16 ------+  +---- deck ----+
 | SUGGEST            (suggestions)  |  |                         |  |              |
 |  D♭maj9/F  1maj9/3  HOME · MOVE   |  |      G♭maj13♯11         |  |              |
 |  A♭9/G♭    5⁹/4     MOVE · LIFT   |  |                         |  |              |
 | ─────────────────────────────── |  |                         |  |              |
 | KEY            D♭ major · sure    |  |                         |  |              |
 |        (ring, 240 px, letters     |  |                         |  |              |
 |         on the rim on hover)      |  |                         |  |              |
 | TENSION  ▁ ▃ ▂ ▅ ▁ ▂ ▁ ▁          |  |                         |  |              |
 | ─────────────────────────────── |  |                         |  |              |
 | THIS NOTE  (the card, 3.1)        |  |                         |  |              |
 +-----------------------------------+  +-------------------------+  +--------------+
```

- **Width:** 200-320 px; the ring is drawn at `min(240, column width − 24)` px.
- **Vertical position:** the suggestion chips start level with the label's centre, and the key block starts level with
  the staff's top line.
- **Narrow margin** (fullscreen on a portrait screen): the side ring and steps are hidden. The card still opens, over
  the canvas, as DOM.

### 4.4 Collision receipt (lab, tonight)

`layout_lab.mjs` against the boxes above, the spectacle map and the jam map, both framings:

| Check | Result |
|---|---|
| New boxes against every existing box and zone, 9:16 | **no intersections**. The narrowed staff's box meets the Nashville row's layer box (y 586-601, above that row's ink) and the pedal mark, both exactly as today's staff does |
| Roles row, 9:16 | 1 px from the Nashville row's **layer box**; by ink ≈ 31 px (roles ink ≤ 462, Nashville ink ≥ 493) and ≈ 16 px under the chips' ink |
| Ring, 9:16 | 8 px from the TikTok button column by box, ≈ 18 px by ink; 16 px from the narrowed staff; 88 px under the banner |
| Tension steps, 9:16 | 12 px under the ring box; 134 px above the jam strip |
| New boxes, 16:9 | **no intersections**; ring 18 px right of the label box, 24 px left of the staff box; roles row ≈ 41 px of ink above the Nashville row |
| Width, 9:16 roles row | 7 columns ≈ 7 × 58 px + `ALSO B♭m11/G♭` ≈ 400 px ≈ 806 px, inside 1060 (estimate: the receipt measures with `measureRuns`) |
| Width, Nashville caption with key change | `4maj13♯11` ≈ 222 px + gap 60 + `NEW KEY · G MAJOR · DOWN A HALF STEP` ≈ 684 px ≈ 966 px, inside 1060 (estimate; the overflow order in 3.6 applies) |

**SVG sketches:** scratchpad `theory-nextgen/layout-916.svg` and `layout-169.svg`. They show the boxes, with the ring
drawn with its window, nodes, centre letter and a sample trail.

### 4.5 Coexistence rules

| Neighbour | Rule |
|---|---|
| **Rarity banner** (spectacle 5.6) | It takes the Nashville row. The scale caption and the key-change caption fade with the row (`spectacle.nnsCover()`). The key-change caption waits (3.6). The roles row, `ALSO`, ring and steps are outside the banner box and stay. |
| **Legendary foil** (E11) | Samples the label's main glyph line only; the roles row is its own layer and never gets foil. |
| **Spectacle protect mask** | Add the ring box and the steps box at ≤ 35% effect light (as under the banner plate), and the roles row at ≤ 35%. E7 shafts (rail up to y 700) and the E10 hem (y 950-1150) pass behind the ring and steps; R2 and R3 luma limits then hold with the Map view on. |
| **CLAUDE chip, jam view** | Theory layers are Daniel's: the jam view's `auto` rule never moves them. Claude's own ring marks (3.5, v2) are glass-only. |
| **Jam run** | While Play, Loop or Try runs, the Nashville row and the ring number in the jam key (jam-spec 8.10), and the candidate window is off (the key is locked). During Try, capsules dim to 50% so the target rims lead, staff lines are off, and key marks use the NOW chord on the glass (3.4). |
| **Suggestions** | Chips yield their slot to the CLAUDE chip (their rule). Ring node hover uses their `suggest` ghost state. Chips and the theory card never overlap in the side column (stacked, 4.3). |
| **Ghost rims** | Rims sit at the key-top edge (6% inset); capsules sit inside, at the back. Both stay visible. |
| **Deck, pill, toast** | Unchanged: the right margin and the bottom. The reading picker and card clamp themselves inside `.stage` and left of the deck. |
| **Demo, computer keys** | The display follows the label, so it shows them. Rarity stays excluded as spectacle R9 says. |
| **Hidden tab** | Nothing draws. `catchUp` already brings the label, key and numbers up to date, and the display rebuilds its trail from the label commits in that stretch (at most 6 kept). |

---

## 5. Recorded or glass-only

| Element | Stage (recorded) | Glass or DOM (never recorded) |
|---|---|---|
| Name, chips, Nashville row, staff | yes (unchanged) | |
| Roles row, `ALSO` | in Anatomy, Map and Full | |
| Scale caption, key-change caption, `FROM` / `TOWARD` captions | in every view but Classic | |
| Staff ghost column and lines | in every view but Classic | |
| Key ring, trail, home caret, pull tick, candidate window, the swing | Map and Full | the side ring in Classic and Anatomy |
| Tension steps | Full, or `frame` | `side` (default) |
| Scale capsules and note marks on keys | `stage` setting (Full's preset) | `glass` (default) |
| Note card, reading picker, hover ghosts from ring nodes, pinned-reading notice | | always |
| Claude's and suggestions' marks on the ring (v2) | | always |
| HUD theory line | | always (the HUD is never recorded) |

The HUD gains one line:
`theory map · Gbmaj13#11 (also Bbm11/Gb +1.2) · Gb Lydian · T 0.15 · Db major sure · pins 0`.

---

## 6. Settings and defaults

**The top bar** gains one select in the theory group, beside Numbers, Minor and Key:
`<label class="field" for="theory-select">Theory <select id="theory-select">` with Classic / Anatomy / Map / Full (and
`custom`, shown when an individual setting was changed). It follows the `nns-select` pattern, with `blur()` after a
change.

| Setting | Values | Classic | Anatomy | Map | Full | localStorage |
|---|---|---|---|---|---|---|
| Theory view | classic / anatomy / map / full / custom | | | | | `arsenal.piano.theory.view` (default **map**, Q1) |
| Roles under the chips | off / on | off | on | on | on | `arsenal.piano.theory.roles` |
| Also reads as | off / close / always | off | close | close | close | `arsenal.piano.theory.alts` |
| Scale name | off / colour chords / always | off | colour chords | colour chords | colour chords | `arsenal.piano.theory.scaleName` |
| Scale on keys | off / glass / stage | off | glass | glass | stage | `arsenal.piano.theory.keys` |
| Key ring | off / side / frame | off | side | frame | frame | `arsenal.piano.theory.ring` |
| Trail length | 4 / 6 / 8 chords | | 6 | 6 | 6 | `arsenal.piano.theory.trail` |
| Tension steps | off / side / frame | off | side | side | frame | `arsenal.piano.theory.tension` |
| Voice-leading lines | off / on change | off | on change | on change | on change | `arsenal.piano.theory.lines` |
| Key-change moment | swing + caption / swing only / off | off | swing + caption | swing + caption | swing + caption | `arsenal.piano.theory.keyChange` |
| Pinned readings | list, Reset | | | | | `arsenal.piano.theory.pins` (≤ 200) |

- **Classic** is byte-identical to the page before this build (receipt D-R1).
- **Where the fine settings live:** in a `[...]` theory menu opened from the select's neighbour button. In the deck's
  settings once the deck lands.
- **Keyboard: `Digit1`** cycles Classic → Anatomy → Map → Full. `KEYMAP` gives every letter to notes except H and F,
  and the jam spec took A and K. Digits 2, 3, 5, 6, 7, 9 and 0 are notes; 1, 4 and 8 are free. 1 sits at the row's edge,
  away from the upper-row notes, so a slip while playing is least likely. Verify against `KEYMAP` at integration.
  `e.repeat` never re-triggers; the Ctrl, Meta and Alt guards stay.
- **Query overrides for receipts** (never stored): `?theory=classic|anatomy|map|full`, `?pins=off`.
- **REC** never changes any theory setting.
- **First load after the build:** one toast, `New: Theory view (Map). Press 1 to switch, Classic is the old look.`

---

## 7. Motion and timing (every theory motion)

| Trigger | What moves | Duration |
|---|---|---|
| Label commit (pop) | roles row crossfades with the label; trail segment grows; node size pulse; tension steps shift one; staff ghost and lines appear | 180 ms growth, 200 ms pulse; lines hold 1.2 s, fade 0.6 s |
| Settled 400 ms | `ALSO` fades in | 250 ms |
| Settled 700 ms and gate passed | scale caption fades in; capsules crossfade to the new scale | 250 ms / 200 ms |
| Reading changes | scale caption out; `ALSO` out | 120 ms |
| Tracker-credited arrival | 1 node size pulse; baseline tick under the step | 240 ms |
| Candidate banks | dashed window alpha follows `heldSec / needSec` | continuous, at most 0.25, no motion |
| Key switch | content swing; centre letter crossfade; caption | 600 ms; caption 2.4 s |
| Silence | everything fades with the label (0.62 at rest, gone at 4.5 s); the trail keeps fading on its own clock | as the label |
| Hover or click (DOM) | card and picker in and out | 120 ms in, 400 ms out |

**Motion budget.** While a chord holds, the frame's theory ink is still. At most one "event" motion runs at a time: a
key swing supersedes a node pulse, and it never waits for a banner.

**Clock.** Every envelope is a function of `clock()` seconds, never of frame counts (spectacle 5.1 rule 6).

---

## 8. What the display needs (contracts), and where the code goes

### 8.1 One frame of theory

The display draws from one object built once per label commit, plus per-frame fields for fades. It is pure and has no
DOM.

```js
// arsenal/web/piano/theoryframe.js (pure)
export function buildTheoryFrame({ shown /* overlay.shown */, midis /* sounding */, key /* keyView */, tracker /* state */,
  readings /* engine: {primary, alts} */, pins, prev /* last frame */, minor, t }) -> {
  reading: { name, number, suffix, rootPc, bassPc, cost, pinned },
  alts: [{ name, number, cost, kind: "upper structure"|"inversion"|"root position"|"foreign bass", confusion: bool }],
  roles: [{ pc, name, role, family: "root"|"third"|"fifth"|"seventh"|"colour", outsideKey, bass }],
  scale: { name, rootPc, pcs, characterPc, named } | null,
  klass: { class: "diatonic"|"borrowed"|"modal"|"secondary dominant"|"chromatic", detail, target } | null,
  tension: { T, rub, pull, outside, bass, altPull },
  key: { name, tonic, mode, confidence, locked, jam }, candidate: { name, tonic, steps, progress } | null,
  home: { pc, number, sec } | null,
  lead: { pairs: [{ from, to }], kept, steps, leaps, lifted, arriving } | null,
  captions: { scale, keyChange, from, toward } }
```

### 8.2 What the engine lens provides (not this file)

| Need | Source |
|---|---|
| `readings.primary` and `readings.alts` with cost and kind | the reading rules this round settles: the page's templates (with `maj9#11`, `maj13#11`, `13sus4` and a dominant-11 name) plus a JS twin of `practice.extended_readings` / `choose_reading` (the `readings.js` of `chord-suggestions.md` 2.2). The display needs the runner-ups, not only the winner |
| `scale` for a reading in a key, with the naming gate | a live twin of MUSIC 9.5 / riff 11.3 step 6 |
| `klass` | a JS twin of `practice.classify` (secondary-dominant target included) |
| `tracker.candidate.needSec` | **additive** field in `createKeyTracker`'s state: the hold the candidate needs (holdSec, doubled if shown within RECENT_SEC). Today the display could only guess 5 s |
| `tracker.arrival` | **additive**: `{at, from, to, credited}` when `hear()` credits or declines a cadence, so the ring pulses only on credited arrivals |
| `home` | computed in `theoryframe.js` from label commits (most chord time over 16 s of playing, at least 2 arrivals); no engine change |

`nashville.js` and `nashville.py` share a fixture. The two additive tracker fields must come through that fixture's
owner, and the Python twin (`performance.numbering_key`) can ignore them.

### 8.3 Modules and ownership

| File | New or existing | Role | Owner and timing |
|---|---|---|---|
| `arsenal/web/piano/theoryframe.js` | new, pure | 8.1; tension; home; captions; the pairing (`voicelead`) | this display's build; node-tested |
| `arsenal/web/piano/theoryview.js` | new | Canvas2D drawers: `drawRoles`, `drawAlso`, `drawRing`, `drawSteps`, `drawStaffLead`; the trail and steps quads; `layout()` rects | this display's build |
| `arsenal/web/piano/theorycard.js` | new, DOM | the card, the reading picker, the side column's key block; hit testing | this display's build |
| `arsenal/web/piano/glass.js` | existing (J8) | `draw()` gains `theory: { capsules: [{midi, shape}], marks: [{midi, cls}] }` under the same 24-key cap | after the jam's J8 and the suggestions' S4 |
| `arsenal/web/piano.js` | existing (J9, spectacle) | integration only: `LAYOUT` gains `anat`, `ring`, `steps` and the panel staff box; `drawStaff` takes a column fraction and a `lead` argument and records `inkTop` / `inkBottom`; `drawLabel` takes the column widths; `drawNumbers` takes the caption; `overlay.update` builds the frame on commit; the top-bar select; `Digit1`; `window.__piano.theory = { view, frame(), layout(), stats() }` | **after** the jam build (J9, J10) and spectacle P2 land and are committed, because both edit the overlay |
| `arsenal/web/piano.html`, `piano.css` | existing | the select, the card and picker styles, the side column block | with `piano.js` |

---

## 9. The known gaps, and what the display does with each

| Gap (reviews of `5cff2c61`, `de1334bf`) | Today on screen | Next-gen display |
|---|---|---|
| No dominant-11 name (read as a Lydian 4 over the 5 bass) | `F/G`, or `Fmaj7♯11/G` | big name per the engine; `ALSO G11` or `ALSO Fmaj7♯11/G` (known confusion); roles show the ♭7, 9 and 11 over the G bass |
| No `maj9#11` / `maj13#11` / `13sus4`; voicings read back as `Cm9/Ab` | wrong root on the label, numbers, scale and tension | with the templates, the right root; the old reading stays visible as `ALSO`; tension for his favourite 4 falls from 0.24 to 0.15 and its scale becomes G♭ Lydian |
| Borrowed labels on old-key chords at a key change | "outside \<new key\>" | `FROM A♭ MAJOR` for 8 s; `TOWARD G MAJOR` while the candidate is half-banked; the dashed window before the swing |
| Dorian vamps numbered in the IV's key | `2m 5` in C major, nothing else | numbers unchanged; home caret on 2m; `IN C MAJOR · D DORIAN` once the natural 6 sounds |
| I-I7-IV with a long IV can read as a cadence into IV | the key flips | the candidate window shows the page leaning before any flip; the 1 node pulses only on arrivals the tracker credits |
| Backdoor dominant (C C7 F B♭7 C) reads as F major | "in F major" | `♭7⁷` node with a pull tick aimed at 1; steps 0 → 0.50 → 0 → 0.60 → 0 make the lean visible; the key shown still follows the tracker |
| Secondary dominants labelled only "chromatic" | "outside C major" | node label `3⁷` with a pull tick to 6m; caption `3⁷   SECONDARY DOMINANT (LEADS TO Am) · IN C MAJOR` (spectacle 2.3 wording) |
| Aeolian loops shown as the relative major (by design) | `6m 4 1 5` in C major | unchanged numbers; home caret on 6m; `IN C MAJOR · A AEOLIAN` when the ♭6 sounds; the Minor setting still renumbers |

---

## 10. Build order and receipts

### 10.1 Phases (after jam J10 and spectacle P2 are committed; the engine lens's readings twin first)

| Phase | Scope | Exit |
|---|---|---|
| D0 contracts | `TheoryFrame` shape; fixtures `tests/fixtures/theory_display/*.json`, synthetic voicings only (the lab's cases plus 12-key transpositions); the two tracker fields through the fixture owner | fixtures validate |
| D1 pure | `theoryframe.js`: roles, alternatives filter, tension, home, captions, pairing; node tests beside the Nashville tests | D-R6, D-R7, D-R11 in node |
| D2 anatomy | roles row, `ALSO`, scale caption, `FROM` / `TOWARD` captions, Classic byte-identity | D-R1, D-R2 (rows), D-R3 |
| D3 staff | ghost column and lines; the panel staff box and column fraction; `inkTop` / `inkBottom` | D-R2 (staff), D-R5 |
| D4 ring | ring, trail, caret, pull tick, candidate window, swing, steps; protect-mask boxes | D-R2 (ring), D-R8, D-R9, D-R12 |
| D5 keys and hands | capsules and marks (glass through `glass.js`, stage decals); card, picker, pins, ring hover and click | D-R4, D-R10 |
| D6 settings | select, presets, `Digit1`, query overrides, toast, HUD line, `__piano.theory` | all receipts green, snapshots looked at |
| D7 with Daniel | 20 minutes of real playing in Map view, then Full; one TikTok test recording | Daniel says what reads well on his phone and what is too much |

### 10.2 Receipts

All run headless per spectacle section 7. Snapshots go to `state/arsenal/receipts/piano-theory-display/<receipt>/`.

| ID | Check | Pass |
|---|---|---|
| D-R1 | **Classic is today.** Seeded frozen frame (`lab.seed`, `sim`, `freeze`) with `?theory=classic` against the build before D2 | MAE 0, max diff 0, in 9:16 and 16:9 and in a snapshot |
| D-R2 | **Collisions.** `__piano.theory.layout()` rects (measured ink from `measureRuns`, ring ink radius, steps) against the label glyph box, chips, Nashville ink, both banner forms, staff `inkTop` / `inkBottom`, pedal mark, strip, CLAUDE chip, TikTok zones; both framings; k = 0.5, 1, 2; plus a high-ledger chord (C6-C7 with flats), a 10-pitch-class wash and the longest caption | zero intersections by ink; roles ink ≥ 8 px from chips and Nashville ink; ring ink ≥ 12 px from the TikTok button column; 16:9 ring and steps above the measured column tops, or under the protect mask |
| D-R3 | **Legibility at phone size.** Recorded frames downscaled to 540 × 960 | role cap height ≥ 7 px; ring numbers ≥ 9 px; ivory text contrast ≥ 4.5:1 against the local background under its scrim (sampled over a dense wash) |
| D-R4 | **Isolation.** 60 s of clicking ring nodes, the picker's Hear, pinning and unpinning, hovering keys | `sounding`, log events, tracker histogram and rarity events identical to the same run without the clicks |
| D-R5 | **Recording.** REC in each view, 5 s, seeded; the glass and DOM hidden in a second run | recorded frames identical between the two runs (glass and DOM never recorded); REC left every setting unchanged |
| D-R6 | **Wording.** Every rendered string (captions, card, picker, HUD) over the fixtures and a synthetic session | none of the guard words; every number equals a frame field |
| D-R7 | **Readings shown.** The lab cases | big name and `ALSO` exactly as 3.2's table (after the engine lens lands); a pin changes the display and **not** the log's chord name |
| D-R8 | **Light.** `spectacle_check.mjs` score with Full theory against Classic; then spectacle R2 and R3 with Full theory on | Δ mean luma ≤ +0.003 and white share unchanged against Classic; R2 and R3 still pass |
| D-R9 | **Flicker.** Offline replay of synthetic sessions with his note-gap profile (p25/50/75 of 190/250/400 ms, pedal down 60-95%) through detect, tracker and `theoryframe.js` | trail segments = label commits; roles row redraws = label redraws; `ALSO` toggles ≤ 1 per settled reading; no swing without a tracker switch; no candidate window shorter than 1 s; theory ink still while a chord holds (frame diff inside theory boxes = 0 after fades end) |
| D-R10 | **Keys.** Capsules in 9:16 and 16:9, glass and stage, with a Try running | glass keys ≤ 24; stage decal draws +1; capsules at 50% during Try; marks follow the NOW chord during a run; A9's glass-to-stage alignment method gives ≤ 1.5 px mean error |
| D-R11 | **Key changes.** Synthetic sessions Ab → G major, Eb → C major, D → E major, C → F major | swings of 5, 3, 2 and 1 fifths the shorter way; captions `DOWN A HALF STEP`, `DOWN A MINOR THIRD`, `UP A WHOLE STEP`, `UP A FOURTH`; `FROM` captions for 8 s |
| D-R12 | **Frame time.** `lab.bench`, idle, held chord, chord changes at 4 per second, key swing, at 1x and REC size, Full against Classic | Δp95 ≤ 0.2 ms at 1x, ≤ 0.5 ms at REC size; overlay texture uploads ≤ 1 per commit per layer, plus the steps and caption layers; trail and steps quads never re-upload a texture |

---

## 11. Questions for Daniel (three, each with a recommended default)

1. **How much theory in the frame by default?**
   - **Recommended: Map.** Roles under the chips, a second name when the notes have one, the scale when it is a colour,
     staff lines on each change, and the key ring beside a slightly narrower staff in 9:16, all recorded.
   - Alternative: Anatomy. The staff stays exactly as wide as now, and the ring lives beside the canvas, off the video.
     Classic (tonight's look) is always one press of `1` away.
2. **When the same notes have two good names, which one goes big?**
   - **Recommended:** the name rooted on your bass goes big (`G♭maj13♯11`), with the other small after the chips
     (`ALSO B♭m11/G♭`). Clicking the name lets you pin the one you mean for those notes.
   - Alternative: always keep the page's first reading big and show the rooted one as the `ALSO`.
3. **Scale marks on the keys in your videos?**
   - **Recommended:** on the glass only (you see them, the video does not), with Full putting them on the keys in the
     recording when you want a lesson clip.
   - Alternative: on the keys in every recording from the Map view up.

---

## 12. For Vandor (not for Daniel)

- **Keys.** `KeyN` is a computer-key note (`KEYMAP` A3), so the suggestions' candidate toggle key collides. Tell that
  design's owner. `Digit1` is proposed here and must be re-checked at integration.
- **Lab numbers are design inputs, not settled values.**
  - The proposed template costs (`maj9#11` 2.6, `maj13#11` 3.0, `13sus4` 2.9, no-3rd `11` 2.5, `13(11)` 3.1) were
    guessed to test the display. The engine lens sets them together with the spectacle rarity table and the Nashville
    fixtures (jam-spec V2-F).
  - The tension weights are illustrative.
  - The known-confusion margin (1.5) and the close margin (0.6) should be tuned on the fixture set.
- **Unmeasured.**
  - The 16:9 rail and column-top height (inherited from `design-ux.md` 5.3).
  - The roles-row and caption widths are estimates from font sizes; D-R2 measures them.
  - The back-edge capsule's visibility under Daniel's hands in the 9:16 follow camera needs one snapshot.
- **Ownership.** `piano.js`, `piano.html` and `piano.css` belong to the jam build (J9) and spectacle; `glass.js` to J8
  and then the suggestions' S4. Nothing here starts before those land. The two tracker fields go through the
  `nashville_cases.json` owner.
- **Isolation stands on INT invariant 1.** Pins are display-only by design, so every analysis stays reproducible. If a
  pin ever feeds the log, the practice verbs and the page will disagree.
- **Scratch files** (`C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/theory-nextgen/`):
  - `theory_block.js`: the THEORY block extracted verbatim;
  - `display_lab.mjs` and `.out.txt`;
  - `layout_lab.mjs` and `.out.txt`;
  - `layout-916.svg`, `layout-169.svg`;
  - `practice_keys.txt`, `practice_borrowed.txt`, `practice_colors.txt`: S6 verb output, which holds times and stays in
    the scratchpad.
- **Privacy check.** This file holds S-labels, chord names, numbers and counts only. No session ids or clock times were
  copied from the verb outputs.
