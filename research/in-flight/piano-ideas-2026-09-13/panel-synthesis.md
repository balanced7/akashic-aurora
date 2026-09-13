# Piano visualizer design round: synthesis

## 1. Ranked menu

How the list is ordered: first by how many judges put a scheme in their top three (merged schemes pool their votes), then by the total of the averaged scores. Every score is the mean of the three judges, rounded to one decimal. When proposals were merged, each one keeps its own scores.

### 1. Upright Roll
**Merged:** Upright Roll with Rehearsal Roll. All three judges put it in their top two.

Your FL piano roll stood on its end: every note grows straight up out of the real 3D key you pressed as a solid bar, and a bright cap on top gets thicker the harder you hit. When you let go and the pedal holds the note, the bar turns into a hollow glass tube that fades like a dying string, and every pedal lift cuts all the tubes off along one straight line.

- **Scores, Upright Roll:** wow 7.0 · theory 6.7 · sustain 9.0 · feasible 5.7 · fit 9.3 (total 37.7)
- **Scores, Rehearsal Roll:** wow 6.3 · theory 6.3 · sustain 9.0 · feasible 6.3 · fit 9.0 (total 37.0)
- **Effort:** medium. The proposals estimate about 380–450 lines. Judges agree the core fits one night; chord tags, the mud tint and the odometer scroll should wait for a second night.
- **Biggest risk:** chord hairlines and tags would take their names from `Theory.detect` run over every sounding note, pedal-held ones included (piano.js:1131). Riding the pedal through a change would then name a cluster or the wrong chord. `harmonySet()` has to land first.

### 2. Orbit
**Merged:** Orbit with Fifths Clock, Fifths Compass and Fifths Maelstrom. Judges 1 and 3 picked it; all three called the four ring designs near-duplicates and said to build at most one.

All 88 keys fold into one circle of fifths, so each chord draws its own shape: a major chord is one triangle turned round the circle, minor is its mirror image, and a dominant 7th has a tension line cutting straight through the middle. The key you're in shows as a lit arc, borrowed notes land outside it, and a thin spoke to the bass note shows your inversions and slash chords.

- **Scores, Orbit:** wow 7.0 · theory 9.0 · sustain 9.0 · feasible 3.7 · fit 5.3 (total 34.0)
- **Scores, Fifths Clock:** wow 7.7 · theory 8.7 · sustain 8.7 · feasible 3.3 · fit 4.7 (total 33.0)
- **Scores, Fifths Compass:** wow 8.0 · theory 8.3 · sustain 7.7 · feasible 2.0 · fit 4.3 (total 30.3)
- **Scores, Fifths Maelstrom:** wow 8.3 · theory 5.3 · sustain 5.3 · feasible 2.0 · fit 4.7 (total 25.7)
- **What the merge keeps:** Orbit is the base (one ghost, a bass spoke, a borrowed-note ring). From Clock, the "guess it" toggle. From Judge 1, the 3D keyboard stays, with filaments fired from the projected keys instead of a flat key strip.
- **Effort:** medium as proposed (about 500 lines, about 350 if the roll's helpers land first). Compass and Maelstrom were large. Judges see it as a second-night build.
- **Biggest risk:** the key arc and the "BORROWED" tags depend on `estimateKey`, whose pitch-class history decays with a 12 s time constant and wobbles in chromatic passages. A wrong key guess would teach the wrong lesson, so it needs hysteresis before it rotates.

### 3. Function Colours
**Merged:** Voice Columns with Nocturne Roll. Judge 1 picked Voice Columns and Judge 3 picked Nocturne Roll, both as a theory layer rather than a standalone look.

Each note is coloured by its job in the chord: gold for the root, teal for the 3rd and 7th, lavender for 9ths, 11ths and 13ths. That makes it plain your lush sound is extensions stacked over a thin root. A held note changes colour when the harmony moves under it, and voice threads let you watch a 7th fall into the next chord's 3rd.

- **Scores, Voice Columns:** wow 6.7 · theory 9.3 · sustain 6.0 · feasible 3.3 · fit 8.0 (total 33.3)
- **Scores, Nocturne Roll:** wow 6.0 · theory 8.3 · sustain 9.0 · feasible 3.7 · fit 6.0 (total 33.0)
- **What the merge keeps:** Nocturne's 5-family palette and `degreeOf`, added as a new `COLOUR.mode` on the Upright Roll. Pitch hue stays the default. Voice Columns' 7th-to-3rd threads come later. Nocturne's `harmonySet()` is a prerequisite for everything.
- **Effort:** medium as proposed (Voice Columns about 380 lines, Nocturne about 550). Judges put either standalone at 550–600+ lines; as a colour mode on the roll it is much smaller.
- **Biggest risk:** role colours are only as good as chord detection. Until `harmonySet` lands, riding the pedal through a change colours notes wrongly, and split-and-recolour churns on rolled chords.

### 4. Prism
Standalone. Judge 2 picked it as the next-night wow preset.

Each key fires a ray of light into twelve rainbow lanes, one per note name, so all your octaves of C stack into one bar and a chord type makes the same barcode in any key. Out-of-key notes light up at the edges, and chord names scroll up the side like a lead sheet writing itself.

- **Scores:** wow 8.0 · theory 7.0 · sustain 9.0 · feasible 4.3 · fit 6.0 (total 34.3)
- **Effort:** medium, about 450 lines including the shared scaffolding. Judges 1 and 3 say it is more than one night.
- **Biggest risk:** rays from keys at the edges run almost flat across the 150 px ray band. They cross each other in two-handed playing and sweep as the follow camera moves, which crowds the band and makes it crawl.

### 5. Progression Runway
Standalone.

Every note is a lit glass block sliding away from the keys down a mirrored runway toward the horizon, trailing a painted stripe for as long as the pedal holds it. Each chord change plants a road sign with the chord name and scale degree, amber when it's in the key and pink when it's borrowed.

- **Scores:** wow 9.0 · theory 7.0 · sustain 7.3 · feasible 2.0 · fit 6.0 (total 31.3)
- **Effort:** large. The proposal says 520–620 lines; judges say 600+, a weekend project.
- **Biggest risk:** perspective squashes time. After a few units you can't read voicings or chord spacing, which undercuts the harmonic-rhythm lesson it promises.

### 6. Ring-Out
Standalone.

Every sounding note gets a mixer meter with a peak-hold tick that decays by register, so bass lingers and treble dies the way real strings do. The pedal lifts a visible damper rail, close low intervals under the pedal turn orange as mud, and a readout tells you whether your melody sings over the chord ("melody +18").

- **Scores:** wow 5.0 · theory 6.0 · sustain 8.7 · feasible 6.3 · fit 4.7 (total 30.7)
- **Effort:** medium, about 350 lines. Judge 3 calls it the cheapest build.
- **Biggest risk:** the string-decay model (about 1.75 s at A4) is wrong for real pianos and most Kontakt patches, so a meter falls while Daniel can still hear the note. All three judges flagged this.

**Did not rank:** Resonance Plumes (total 28.7). See Dissent.

---

## 2. Build first: Upright Roll

This is a new "Upright Roll" preset beside the current look. It uses Upright Roll's layout and receipt, parts from Rehearsal Roll, and Nocturne Roll's `harmonySet`.

Checked in piano.js before writing this:
- The trails use `AdditiveBlending` (line 475) with a halo pad of `aW*1.2` (line 487) and a foot glow (line 520), all feeding bloom at threshold 0.9 (line 371).
- CC64 is thresholded at 64 in `onMidiMessage` (line 1209).
- The render loop already runs on `requestAnimationFrame` at native refresh (line 1641), and REC is paced to 60 fps (line 1615).
- The overlay is already composited after bloom (lines 1609–1611). The text stays sharp; what kills it is the bright columns behind it.

So the framerate request needs no work: the new preset only has to stay clock-driven, never frame-counted.

### Build plan, tonight

1. **Harmony fix, in the THEORY block with node tests.** Add `harmonySet(sounding, t)`: held notes, plus pedal-held notes struck within the last 1.5 s. `currentInfo()` (line 1131) detects over that set instead of every sounding key. This is the only change that touches the existing look's chord label; it is a naming bug fix.
   - *My addition, not in any proposal:* add a test that a pedalled bass note struck more than 1.5 s before the right-hand chord still counts as the bass. Otherwise inversions and slash chords over a pedal point lose their bass.
2. **Scheme switch.** Add a `SCHEMES` registry and a `#scheme-select` next to `#color-select` (around line 1522), saved through `safeSet("arsenal.piano.scheme")`.
   - The options are **Aurora** (today's trails, the default, left byte-identical) and **Upright Roll**.
   - `noteOn`, `noteOff` and `setSustain` call the active scheme's `start / release / end / pedal(on, raw, t) / frame(t, dt)`.
   - Switching toggles `trailMesh.visible` against the roll meshes, clears the roll's slots, and re-runs the `applyFraming` path so the overlay picks up the scheme's LAYOUT entry and lens shift.
   - The switch lives in the HUD only, never on the recorded canvas.
3. **Roll mesh.** Copy the trail instancing: same attributes `aX aW aT0 aT1 aT2 aVel aColor`, same slot recycling, same `uNow` placement, so bars stay time-based.
   - Use two pools, white keys (renderOrder 1) and black keys (renderOrder 2), with `NormalBlending` and premultiplied alpha.
   - No halo pad and no foot glow. White bars are 0.72 wide; black bars 0.40 with a 0.05 dark outline.
   - **Held part (aT0 to aT1):** solid pitch hue, L = 0.46 + 0.36·v^0.8, kept under the bloom threshold.
   - **Onset cap:** height 0.10 + 0.22·v at L 0.92, multiplied by 1 + 1.2·exp(−age/0.12). This is the only part that crosses bloom, and its thickness shows velocity in a still frame.
   - **Pedal tail (aT1 to aT2):** a hollow 2 px fwidth outline at alpha 0.7·exp(−tailAge/1.5), floor 0.28, interior fill about 0.07.
   - `burst()` fires only when v > 0.7, so sparks mark accents.
   - Skip Upright Roll's odometer scroll and 16° elevation tonight. Judges 1 and 3 doubt them, and the keys keep their current drama.
4. **Layout for 9:16.** A top band at y 230–630 holds the label on the left (with auto-fit for long names such as `Ebm(maj7)/Bb`) and the staff on the right.
   - Set `uTop` for this scheme by unprojecting screen y ≈ 650 onto the trail plane, so the roll fully fades out before the band. The frustum formula at line 706 won't do that.
   - Change the lens shift from 0.25 to about 0.21 (line 704) so the key fronts sit at or above y 1520.
   - In 16:9, the roll fades by y ≈ 380 under the existing label and staff positions.
5. **Pedal.** Store the raw value (`sustainValue = d[2]`) and leave the note threshold at 64.
   - Add a 12 px amber pedal lane pinned inside the left edge: a 64-slot instanced strip on the same clock, pedal-down at T0 and pedal-up at T2.
   - The rail line eases from copper to amber while the pedal is down.
   - Nothing new is needed for the lift cut: `setSustain(false)` already ends every unheld note at the same `t` (lines 1104–1112), so all hollow tails end on one line.
   - Half-pedal visuals wait until a logged session shows the pedal sends values other than 0 and 127.
6. **Receipt.** Add Upright Roll's "pedal storm" demo phrase: four octaves of pedalled arpeggios, 30+ notes under one pedal. The CDP receipt asserts:
   - the mean luminance of the label and staff band stays within 5% of silence
   - the key fronts are at or above y 1520
   - no roll pixel exceeds the bloom threshold outside onset caps

   Then replay one of Daniel's own logged, pedalled takes through `window.__piano.midiMessage` (line 1663) as the acceptance test.

### Second night
- Chord hairlines at each chord's earliest note-on, with dark-pill name tags. Clamp them inside the frame next to the pedal lane, not anchored to the bass lanes; all three judges flagged clipping or crowding there.
- The "rolled 84 ms ↑" caption.
- The mud tint, tested against settled-chord membership, not freshness (Judge 1).
- Function Colours as a `COLOUR.mode`.
- The MIDI-clock grid. It needs `onMidiMessage`'s `d.length < 2` early return reworked, because clock bytes are one byte long (line 1202).

### How sustain reads in dense pedalled passages
- **Nothing bright passes behind the text.** The label and staff sit in a band the roll has faded out of.
- **Nothing stacks.** Normal blending, no halos and gutters between lanes mean a pixel is at most one bar's colour. Thirty pedalled notes make thirty thin tubes, not a wall.
- **Pedalled notes never bloom.** Tails are hollow and decay to a floor; only onset caps flash. Bloom therefore follows how often he strikes, not how long he holds the pedal.
- **The pedal is its own object.** It shows in the amber lane, the rail colour and the one-line cut on lift, not as extra brightness on the notes.
- **The name stays right.** `harmonySet` keeps the chord label correct while the pedal rides across a change.

---

## 3. Sustain everywhere

These behaviours were agreed across the designers and judges:

1. **Solid means your finger, hollow means the pedal.** Held notes are filled; notes sounding only through the pedal are outlines or hollow rings. This came from Rehearsal Roll, Upright Roll, Ring-Out, Nocturne Roll, Orbit, Fifths Clock, Fifths Compass and Prism, and all judges endorsed it.
2. **Never sum light.** Use normal blending in strict lanes, or merge each pitch class by maximum rather than sum (Prism, the ring designs). No design may let 20 pedalled notes add up to white. All three judges confirmed the cause in code: additive blending plus the 1.2× halo pad plus bloom at 0.9.
3. **Only attacks and held cores cross the bloom threshold.** Pedal tails, smoke and fills stay under it.
4. **Pedalled notes decay to a floor while the pedal stays down.** Time constants in the proposals range from about 1.1 to 3 s, and floors from about 0.12 to 0.3. A long pedal dims but stays readable.
5. **A pedal lift is one visible clearing.** Every hollow tail ends on the same line, or every hollow ring collapses together, matching what the ear hears.
6. **Draw the pedal once.** It gets its own object (a lane, a bracket, a gold ring stroke, a rail, or the Ped. and release glyphs), never a per-note glow.
7. **The label and staff are protected by layout.** A top band, a clear zone or a dark eye; never bright geometry behind the text.
8. **Name harmony from `harmonySet`, not from every sounding note.** Proposed by Nocturne Roll and Orbit, and adopted by Judges 1 and 3 as a prerequisite for any scheme that names chords.
9. **Keep the engine threshold at 64 and log the raw CC64 value.** Build half-pedal visuals only after confirming the KeyLab pedal sends continuous values; all three judges warned it may send only 0 and 127.
10. **Everything is time-based.** Native-refresh drawing and 60 fps REC are already in place, and any feedback simulation uses a fixed 60 Hz step.
11. **Prove it with a pedal-storm receipt.** Band luminance is measured against silence, and the key fronts sit at or above y 1520.

---

## 4. Note log and theory banter

### What to log
The page keeps a 30-minute ring buffer and sends a batch every 2 s to a new `POST /api/piano-log` route beside `/api/recordings` in serve.py. On `pagehide` it flushes with `sendBeacon`. The server appends to `state/arsenal/piano-log/YYYYMMDD-HHMMSS.jsonl`. Every row has the take ledger's `{t, kind}` shape so it can move into `take.py` later. `t` is `clock()` in seconds with millisecond precision.

| kind | fields | hooked at |
|---|---|---|
| `session` | wall-clock ISO time, input port name, framing, scheme | page load, input switch |
| `note_on` | `m`, `v` | `noteOn` |
| `note_off` | `m` (the finger release, aT1) | `noteOff` |
| `sound_end` | `m`, `by: "release" \| "pedal" \| "repeat"` (aT2) | `trails.end` call sites |
| `cc64` | `v`, the raw 0–127 value, logged only when it changes | `onMidiMessage` |
| `chord` | `tOnset`, `name`, `notes` (MIDI), `spelled` (e.g. "F2"), `bass`, `key`, `keyR`, `numeral`, `borrowed`, `unnamed` (cluster), `rollMs`, `rollDir`, `topVel` and `restVel`, `pedalAcross` (pedal held through the change), `prevDur` | where `overlay.shown` is replaced (lines 1029/1032) |
| `rec` | `state: start \| stop`, `file` | `startRecording` / `stopRecording` |
| `mark` | `src` (the learned MIDI signature) | a KeyLab pad or button, MIDI-learned once and stored locally; shows a HUD-only tick, never on the canvas |

Storing release time and sound-end time separately, plus the raw CC64 value (Judge 3), is what turns "you rode the pedal through that change" into a checkable fact. Rough volume: about 3 MB per hour of dense playing.

### Session summary format
A node digest extracts the THEORY block the same way the tests do and folds a session into one card, `<session>.digest.md`. Agents read only the card; the raw JSONL stays on disk so any claim can be checked. The card can also be saved as an Akashic note so any seat can pick up the thread. Values below are placeholders.

```
# Piano session 2026-09-14 21:40 · 48 min · 3,912 notes · 211 pedal changes
keys: C major 62% · A minor 21% · Eb major 9% · unsure 8%     rec: 21:52-21:55 (piano-...webm)
pedal: continuous? no (0/127 only) · changes re-pedalled after the chord: 14/22 · ridden across: 8/22 · median lift after change: +90 ms
progressions (key-free, count): IV-V-iii-vi x9 · ii-V-I x6 · I-bVII-IV x4
borrowed/chromatic: bVII @12:41 12:58 · iv (minor) @31:12 · V7/ii @18:05
voicings: LH shells R-7 x31 · rootless 9ths x12 · top-note range E4-C6 · widest spread 3.5 oct @22:10
dynamics: melody over chord avg +11 vel · rolled chords 38% (median 62 ms, up)
unnamed shapes: @27:48 C2 G2 | D4 F#4 B4 (x3)
marks:
  mark 1 @31:10  transcript (-8s..+4s):
    +0.00s Fmaj9 (F2 C3 | A3 C4 E4 G4) ped down · IV in C
    +1.43s Fm6   (F2 C3 | Ab3 D4 F4)   ped ridden across · iv (borrowed)
    +2.90s Cmaj9 (C2 G2 | E4 B4 D5)    ped re-pedalled +110 ms · I
answers so far: iv borrowed -> "by ear" (x2)
```

The agent's rules:
- Open with **one** question anchored to a timestamp or mark he can replay. Don't lecture.
- Answer in three steps: name it, say why it works using his actual notes, and give one thing to try next.
- Write his answer ("on purpose", "by ear", "no idea") back onto the card, so habits add up across sessions into a harmonic fingerprint.
- `mark` rows inside a REC window double as clip candidates.

### Three example questions (placeholders filled from a real card)
1. **Borrowed chord:** "At mark 1 you went Fmaj9, then Fm6, then Cmaj9. That A♭ is the minor iv borrowed from C minor, the bittersweet drop. Did your hand find it, or were you reaching for that sadness on purpose?"
2. **Pedal habit:** "You re-pedalled cleanly on 14 of 22 changes, but at 18:05 you held the pedal straight through G9 into Cmaj9 and both chords blurred together. Was that wash the point, or want to try lifting just after the new chord lands?"
3. **Unnamed shape:** "Three times tonight you held a shape the detector couldn't name: C2 G2 under D4 F♯4 B4. It could be read as Cmaj9♯11 with no 3rd, as a D triad over C, or as a Lydian colour chord. Which one sounds like what you meant?"

---

## 5. Dissent

### Where judges disagreed
- **Which roll is the base.** Judge 1 builds on Rehearsal Roll with Upright Roll folded in. Judges 2 and 3 build on Upright Roll and use Rehearsal Roll as a parts bin. Judge 2 gave Upright Roll the only 10 for fit.
- **Upright Roll's camera.** Judge 1 says the odometer scroll, camera-up billboard and 16° elevation add risk and flatten the keyboard. Judge 3 doubts the claim that bars in flight don't rescale when the camera zooms. Judge 2 is fine with the core but says the odometer rebase and label auto-fit push it past one night.
- **The third pick.** Judge 1 chose Voice Columns (theory layer), Judge 2 chose Prism (wow preset), Judge 3 chose Nocturne Roll (function colour plus `harmonySet`). Judge 2 picked no ring scheme and calls Orbit a second-night build.
- **Orbit's keyboard.** Judge 1 says keep the 3D keys and fire filaments from them. Judge 2 treats Orbit as dependent on Nocturne's flat strip and helpers. Judge 3 counts the flat strip as a loss.
- **Compass's tension gauge.** Judge 1 checked the pinned values and they add up (G7 0.34, Cdim7 0.56, Dm9 0.07). Judge 2 calls the weights untuned. Judge 3 says the gauge and shockwave will fire on non-cadences, and that a tritone laser on maj7♯11 marks colour, not tension.
- **Resonance Plumes on sustain.** Judge 3 gave 7 (the saturating OKLab accumulator really stops white-out). Judge 1 gave 5 (held and pedalled notes read as blur on blur). Wow: Judge 3 gave 9, the others 8.
- **Maelstrom's wow.** Judge 1 gave 7; Judges 2 and 3 gave 9. All three agree the spin smears the shapes it claims to teach.
- **Nocturne Roll's fit.** 7, 6 and 5. The judges split on how much its premium look offsets losing the 3D keys and bloom.
- **Smaller splits.** Prism feasibility (4, 5, 4) and Voice Columns theory (10, 9, 9). On Fifths Clock, Judge 2 says the centre numeral repeats the label, while Judge 3 says the shrinking ghosts land on top of it.
- **MIDI-clock grid.** Judge 1: drop it tonight. Judge 2: a good follow-up once loopMIDI runs from FL. Judge 3: needs the one-byte early return fixed first.

### Ideas worth keeping that didn't rank
- **Prism's max-per-pitch-class merge.** Judge 3 calls it the best anti-washout rule of the twelve. Prism also offers a REC loop seam (hold `recorder.stop()` until the scene is back at rest, so the last frame matches the first) and a single eased first-hit bloom kick for the TikTok hook.
- **Resonance Plumes' saturating OKLab energy accumulator** (lightness capped below bloom; chromatic playing goes silver), and `Theory.roughness`, which reacts to voicing rather than just chord name.
- **Fifths Clock's "guess it" toggle** for slow name-the-chord clips (Judge 1).
- **Fifths Compass's cadence captions** ("DECEPTIVE CADENCE") as hooks, once key and cadence detection are trustworthy.
- **Ring-Out's melody-balance readout and low-interval mud tint.** Judge 1 says to steal both; Judge 2 suggests it as an overlay element rather than a whole scheme.
- **Rehearsal Roll's "rolled 84 ms ↑" caption** (Judge 3) and the MIDI-clock grid for playing ahead of or behind FL's beat.
- **Maelstrom's pure helpers** `fifthsSteps` and `classify` (flat side and sharp side of the key). They are cheap, node-testable, and useful to the digest.
- **Progression Runway's colour code**: amber for diatonic numerals, pink for borrowed ones. It works for any scheme's chord tags.
- **Upright Roll's label auto-fit** for long chord names.
- **Judge 1's overall gap:** none of the twelve schemes logged notes. The logger in section 4 is about 40 lines on the page side, doesn't depend on the scheme, and should land tonight with whichever preset wins.

Files read: `E:\AI-Setup\arsenal\web\piano.js` (lines 440–590, 690–760, 1005–1220, 1585–1642, plus searches), `E:\AI-Setup\arsenal\serve.py` (routes), `E:\AI-Setup\arsenal\take.py` (event shape), `E:\AI-Setup\state\arsenal\receipts\piano-dev\20260913-213004-r4-916-demo-a.jpg`. No files were modified.