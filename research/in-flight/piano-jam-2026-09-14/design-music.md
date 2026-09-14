# Piano jam: the music engine (backing loops, sound, riff analysis, starter loops)

| | |
|---|---|
| Status | Design, in flight, 2026-09-14. Nothing built. No code edited, no server or browser started. |
| Lane | Music engine. Siblings: `design-ux.md` in this folder (deck, transport UI, strip, marks, report card) and the FL bridge lane `research/in-flight/fl-jam-bridge-2026-09-14/` (virtual MIDI, FL sync, local inventory). |
| Read | `arsenal/web/piano/cues.js`, `arsenal/pianocue.py`, `arsenal/pianocue_voicing.mjs`, `arsenal/web/piano.js` (THEORY templates, MIDI input, log hooks), `arsenal/web/piano/log.js`, `arsenal/performance.py`, `arsenal/practice.py`, `arsenal/serve.py` (cue routes), `arsenal/PIANO-V2-SPEC.md`, the spectacle spec, the practice receipts `state/arsenal/receipts/practice-verbs/s1-*`, the four sessions under `state/arsenal/performance/`, `design-ux.md`, and the FL lane's `virtual-midi-and-sync.md` and `local-inventory.md`. |
| Measured | Register, velocity, pedal and onset gaps over his four sessions; scale fit over two of them; the voicing bridge on 57 draft loop chords plus alternates. Scripts: scratchpad `jam/stats.py`, `jam/scale_proto.py`, `jam/voice_loops.py`. |

Daniel, tonight:

> "I want us to be able to play in this space, can you make verbs so you can play chord progressions or show loops of
> chords for me to try, I can then riff on that and play with it and we can discuss it"

> "so I can click and hear concepts you are describing and have a visual for them, we can make chord templates"

> "I just play it by feel" / "I know a little bit but not much >__< this is intuition and memory"

---

## 0. The engine in one screen

1. **Two settings decide what a loop sounds like.** `backing` is which notes Claude plays: `full`, `comp`, `bass` or
   `pad`, as `design-ux.md` names them. `groove` is when Claude plays them: `hold`, `swell`, `ballad`, `pulse`, `arp`
   or `gospel`. A call-and-response pattern can sit on top of any groove.
2. **A band voicer** (a new style in the voicing bridge) keeps Claude under his hands. The bass goes in E1-D3. `full`
   chords go in D3-G4 (A4 at most). `comp` stays under C4, reaching E4 only for a chord's defining colour. Every
   adjacent pair respects low-interval limits. The whole loop is voiced as a ring, so the last chord leads back into
   the first.
3. **One pure groove generator** (`arsenal/web/piano/groove.js`) turns (card, settings, seed, pass, bar) into notes.
   It is deterministic: the page plays it, Python can call it through a node bridge for the FL route, and "Hear pass N
   with the loop" rebuilds exactly what sounded.
4. **The transport** keeps the UX design's bar lines on the `performance.now()` clock, with a tempo map. It hands the
   player one bar at a time, with that bar's pickups. So tempo changes, swaps and stops land on bar lines without
   cancelling anything already queued.
5. **The sound** is a darker "keys" preset of Claude's voice (round sine bass) plus a new sustaining `pad` timbre, at
   base velocity 44. The duck is gentle: -3 dB, held 1.2 s. Optional MIDI out goes to FL on a loopback: bass on
   channel 1, chords on channel 2, with an echo guard. Nothing gets downloaded without Daniel's OK.
6. **The jam record** gains a tempo map, settings by bar, each chord's tones, scale and voicing, and a tap-along
   calibration. With those, the analysis can rebuild every bar line and every Claude note.
7. **Riff analysis** (`py -m arsenal.practice riff`) aligns his notes to the bars. Each note gets a class against its
   chord's scale: in the chord, colour (9/11/13), rub, passing, slide-in, or outside. From those classes it infers
   scales per chord, and it names a mode only when the mode's own note actually sounds. It also measures his timing
   against his calibration, splits phrases, finds motifs and scores echoes. Talking points come out in plain words,
   each with a time and a replay command.
8. **Eleven starter loops** come from his own moves: the Lydian 4, the gospel 5 over 4, blooming chords, the walking
   bass, the half-step slide, the minor-third drop, borrowed colours, the sunrise ending. Three stretch him: the real
   5 with its 3rd, the same shapes on white keys, and a Dorian vamp for rhythm.

---

## 1. Evidence this design stands on

### 1.1 His playing, measured

Attacks are note-ons grouped within 50 ms (the practice verbs' `ONSET_GROUP_MS`). "Top" is the highest note of each
attack; "bottom" is the lowest note of attacks with two or more notes. Onset gaps are the times between attacks, from
120 ms up to 2 s.

| Session | Length | Notes | Velocity p10/50/90 | Top median / p90 | Bottom median | Pedal down | Onset gap p25/50/75 |
|---|---|---|---|---|---|---|---|
| S1 | 5:25 | 1093 | 35 / 55 / 71 | Bb4 / E6 | Eb2 | 57% | 188 / 296 / 448 ms |
| S2 | 5:09 | 1440 | 35 / 56 / 78 | Bb4 / C6 | F3 | 84% | 192 / 216 / 363 ms |
| S3 | 22:13 | 3806 | 29 / 46 / 71 | B4 / F6 | Eb3 | 61% | 194 / 252 / 394 ms |
| S4 | 3:55 | 1132 | 32 / 49 / 71 | Db5 / Eb6 | F3 | 95% | 234 / 316 / 402 ms |

What follows from it:
- His top line lives from Bb4 up. A backing whose top voice stays at or under G4 leaves at least a minor third clear
  below his median top note, and A4 is the most it may ever reach.
- His touch is soft: median velocity 46-56. The backing's base velocity is 44, at the bottom of his range, so Claude
  never plays louder than he does.
- His notes come fast: median gaps of 216-316 ms. Eighths at 72-90 bpm (333-417 ms) sit a little slower than his own
  note rate, so a `pulse` never hurries him.
- His pedal is down 57-95% of the time. The analysis must time a note by its onset and a capped length, never by how
  long the pedal kept it sounding.

### 1.2 What he plays, in pitch terms (scale prototype)

Each onset was weighted by 1, measured against the key, and scored against candidate scales:
`coverage - 0.04 x (size - 5) - 0.05 x (degrees used under 2%)`.

| Stretch | Onsets | Share on degrees 1 2 3 4 5 6 7 | Best fits (score) |
|---|---|---|---|
| 010120, Eb major area 1:27-4:00, all | 373 | .24 .07 .20 .13 .18 .07 .09 | major .912, major without the 4 .818, Mixolydian .776, major pentatonic .769, Lydian .731 |
| same, top note of each attack | 247 | .24 .10 .19 .10 .18 .07 .11 | major .908, without the 4 .851, pentatonic .785, Lydian .765 |
| 012540, Db major, whole session, all | 1132 | .22 .13 .17 .08 .17 .13 .09 | major .912, without the 4 .869, pentatonic .822, Lydian .783 |
| same, top note of each attack | 759 | .23 .15 .16 .08 .17 .12 .10 | major .916, without the 4 .880, pentatonic .823, Lydian .792 |

The five pitch classes outside the key each came to under half a percent.

What follows from it:
- Scale inference over a whole key only ever answers "the major scale": coverage is 0.99-1.00. "Lydian" is the same
  key's notes seen from the 4 chord, so modes are inferred **per chord**, and named only when the mode's own note
  sounds (section 9.7).
- He uses the 4th and the 7th about one note in five (17-22%). He is not a pentatonic player, and a report must not
  say he is.
- Slide-in notes from outside the key are almost absent. One half-step approach is an honest first stretch, not a
  correction.

### 1.3 The voicings the bridge gives today

`pianocue_voicing.mjs` ran with `--voice-lead` on 57 chords from a first draft of the starter loops:
- **Too high.** `spread` put the top voice at C5 or higher on 14 of 57 chords; `drop2` did on 15 of 57. Both went up
  to Eb5, inside his top line.
- **Too low.** In the draft sunrise ending, `spread` voice-leading sank Gbmaj9 to F#1 F2 Ab2 Bb2 Db3. Every adjacent
  pair there is below its low-interval limit: F#1-F2 a major 7th, F2-Ab2 a minor 3rd, Ab2-Bb2 a major 2nd, Bb2-Db3 a
  minor 3rd. `drop2` put Ebmaj9 up at D5 in the same loop.
- **Greedy voice-leading.** Each chord leads from the one before, and nothing leads the last chord back to the first.
  A loop needs that wrap move most of all.
- **Names drift with voicing.** Bbm11/Gb without its F reads back as Ab11/Gb (spread and drop2); the close voicing
  with the F reads exact.
- **The page lacks some of his names.** THEORY's TEMPLATES has no `maj9#11`, `maj13#11` or `13sus4`. The page reads
  Abmaj9#11 as Cm9/Ab, Abmaj13#11 as Cm11/Ab, Gbmaj13#11 as Bbm11/Gb and Ab13sus4 as Ebm9/Ab. So his signature Lydian
  chords have no name on his own screen (`design-ux.md` 4.1 found the same).
- **Gm7/Bb loses a sliding voice.** For the page to call it Gm7/Bb, the bridge leaves out its D (G Bb D F are also the
  notes of Bb6). That removes one of the two voices that slide in "Gm7/Bb to Gbmaj7/Bb".

### 1.4 The page, the log and the machine

- **Log clock.** Cue notes carry `meta.source` and stay out of the log (cues.js header). The log's `t_ms` is page-clock
  seconds (`performance.now()/1000`) minus the session's start (log.js `tms`). Bar lines on the performance clock
  therefore line up with his notes directly.
- **Unknown kinds.** `performance.validate_event` rejects any kind outside on/off/pedal/chord/sound_end, and the whole
  batch with it. `design-ux.md` 9.1 names this hazard.
- **MIDI echo.** In piano.js, `midiRank` gives every input not named "daw" rank 1, and "All inputs" binds every input
  ranked above 0. `onMidiMessage` ignores the channel. A loopback port's input side would therefore bring Claude's
  MIDI out straight back in as Daniel's notes: drawn, logged and key-tracked.
- **The cue player and voice.** The player starts a cue at `now() + 50 ms + at_ms`, so any lateness in handing a cue
  over becomes note timing. The voice skips MIDI whenever a note is given `{time}` instead of `{at}`, sends on channel
  1 (0x90) only, and allows 24 voices of polyphony.
- **Audio setup** (FL lane inventory). Scarlett 2i2 4th Gen; FL on Focusrite USB ASIO, 48 kHz, 256-sample buffer
  (about 5.3 ms). Installed keys and pads include Arturia Stage-73 V2, Piano V3, Analog Lab V, Kontakt 8 and FL Keys.
- **Virtual MIDI.** `midisrv` is running and the in-box loopback transport is present, but no user loopback exists.
  The SDK Runtime and Tools that create loopbacks are not installed, and neither is loopMIDI. The FL lane found this,
  and my own read-only check agrees: `sc query midisrv` shows RUNNING; there is no `C:\Program Files\Windows MIDI
  Services` and no Tobias Erichsen folder.

---

## 2. Where the engine lives

| Part | File (proposed) | Pure? | Used by |
|---|---|---|---|
| Band voicer (section 4) | `arsenal/pianocue_voicing.mjs`, new style `band` with `backing` and `ceiling` | yes (node) | card publishing, `pianocue loop`, kept-card edits, re-voicing on a key change |
| Chord facts: tones, scale, class (9.5) | `arsenal/pianocue.py`, from the bridge's tone roles plus `practice.classify` | yes | card JSON, live marks, riff analysis |
| Groove generator (section 5) | `arsenal/web/piano/groove.js`, an ES module with no DOM | yes | the page transport; `arsenal/groove_bridge.mjs` for Python (FL route, Hear pass N, riff) |
| Transport (section 6) | `arsenal/web/piano/transport.js` (UX phase J2) | no | page |
| Timbres, levels, MIDI out (section 7) | additions to `createClaudeVoice` and `createCuePlayer` in `cues.js` | no | transport, cue player |
| Jam record and calibration (section 8) | page plus server routes (UX 9.1), `pianocue jam calibrate` | no | analysis, reports |
| Riff analysis (section 9) | `arsenal/practice_riff.py`, verb `riff` in `arsenal/practice.py` | yes | report cards, chat |

```
card (chords, key, bpm) --bridge: band voicer + chord facts--> card JSON with voicings, tones, scales
        |
page transport (bar clock, tempo map) --one bar + pickups--> groove.js --steps--> cue player --> Claude's voice
        |                                                                               \--> MIDI out (optional)
        +--> jam record (tempo map, settings, chords, calibration) --> server --> practice riff --> report card
his KeyLab --> page noteOn --> practice log (his notes only) ---------------------------------/
```

**Two routes, one generator:**
- **Route P, the page (tonight, no downloads).** The page transport schedules the groove into Claude's built-in
  voice, and can also send it by MIDI out to an FL instrument once a loopback exists.
- **Route F, FL (after Daniel's OKs, per the FL lane's topology in its section 5.5).** A Python sequencer follows FL's
  MIDI clock and sends the same groove material into FL on a "Claude Backing" loopback. The page draws, and logs bar
  beacons. Because both routes call `groove.js`, the same card, settings, seed and pass give the same notes on either.

---

## 3. What the engine needs from a card and a jam

`design-ux.md` section 10 owns the card's shape. The engine adds fields per chord and a settings block per jam. Field
names are proposals; the protocol design names them for good.

### 3.1 Per chord (computed server-side when a card is published or edited)

```json
{ "text": "Bbm11/Gb", "number": "6m11/4", "beats": 4,
  "tones": { "root": 10, "third": 1, "fifth": 5, "seventh": 8, "ninth": 0, "eleventh": 3, "bass": 6 },
  "scale": [10, 0, 1, 3, 5, 6, 8], "scale_name": "Bb Aeolian", "class": "diatonic",
  "voicings": { "full": [42, 51, 56, 58, 60, 61, 65], "comp": [42, 49, 56, 58], "bass": [42] },
  "roles":    { "full": ["bass", "eleventh", "seventh", "root", "ninth", "third", "fifth"], "comp": ["bass", "third", "seventh", "root"], "bass": ["bass"] },
  "reads_as": null, "omits": [] }
```

- `tones` maps each role to a pitch class, in the card's written tonic. The bridge already knows each role
  (`tonesOf`); it just has to return the pitch classes too.
- `scale`, `scale_name` and `class` follow the rules in 9.5.
- `voicings` and `roles` come from the band voicer (section 4). The MIDI numbers in this example are illustrative.
- **On a key change, re-voice rather than shift.** `design-ux.md` 4.3 transposes by moving every note -6..+5 semitones.
  With register bands, a +5 shift lifts a G4 top voice to C5, into his register, and a -6 shift can drop the bass
  below E1. Re-voice in the new key on the bridge (one node call, about 100 ms) and cache the result per key; shift
  only as a fallback while the bridge answers.

### 3.2 Per jam: settings (all change on the next free bar, section 6.3)

| Field | Values | Default | Meaning |
|---|---|---|---|
| `backing` | full, comp, bass, pad | comp (UX) | which notes (5.12) |
| `groove` | hold, swell, ballad, pulse, arp, gospel | per card; else ballad under 80 bpm, pulse from 80 | when the notes sound (section 5) |
| `level` | 1..127 | 44 | base velocity L (7.3) |
| `humanize` | 0..1 | 0.6 | timing, roll, velocity and length variation (5.1); 0 = machine-exact, for receipts |
| `seed` | 32-bit int | random at start | makes the humanising repeatable |
| `feel`, `swing` | straight / swing / triplet; ratio 1.0..2.2 | straight 1.0 (gospel: swing 1.6) | where offbeat eighths fall (5.1) |
| `walk` | 0, 1, 2 | 1 | bass approach notes (5.8) |
| `push` | bool | false (gospel: true) | the next chord arrives on the & of the last beat |
| `spice` | 1, 2 | 1 | 2 adds the gospel half-step approach chord |
| `bass_mode` | written, pedal | written | `pedal` holds one bass note under every chord (5.8) |
| `ceiling` | a note | G4 (hard A4) | the top of Claude's register |
| `call` | null or {pattern, respond, motif} | null | call and response (5.10) |
| `count_in` | 0..2 bars | 1 | UX 5.1 |
| `passes` | 0 = until stopped, or N | 0 | stop at the top after N passes |
| `ending` | cut, home | cut | `home` lands on the loop's first chord at the stop (6.3) |

Verbs (the verbs lane may rename them): `pianocue loop <card or chords> --key --bpm --groove --backing --count-in`,
`pianocue jam set --groove arp --at bar|top`, `pianocue tempo 76 [--ramp-bars 4]`, `pianocue stop --at bar|top
--ending home`, `pianocue jam status`, `pianocue jam calibrate`. Each one sends a remote deck action (UX section 10)
that carries these fields; the courtesy gate (UX section 8) applies to anything that makes sound.

Validation: 1..64 chords; beats per chord 1..16, whole beats; meter 2..7; bpm 30..240; a ramp of at most 64 bars;
at most 7 notes per voicing (a bass and up to 6 upper voices).

---

## 4. The band voicer (new style `band` in `pianocue_voicing.mjs`)

### 4.1 Registers

| backing | bass | upper voices | top voice: soft / hard | upper voices |
|---|---|---|---|---|
| full | E1-D3 (28-50), preferring C2-B2 (36-47) | D3 up to the ceiling (50-67) | F4 (65) / A4 (69) | 4 (pulse uses 3 of them, 5.5) |
| comp | the same | C3-B3 (48-59); the defining colour may reach E4 (64) | B3 / E4 | 2-3 (4 over a foreign bass: 3rd, 7th, root, colour) |
| bass | the same | none | none | 0 |
| pad | as full | as full | as full | 4 |

His zone is C5 and up; A#4-B4 is a buffer. `--ceiling` moves the whole upper band down or up an octave at most (for
example, `--ceiling C5` when he plays low and wants a fuller bed).

### 4.2 Which tones

Roles come from the bridge's `tonesOf`: root, third or sus, fifth, seventh or sixth, ninth, eleventh, thirteenth.

1. **The third or the sus tone:** required (full, comp).
2. **The seventh or the sixth:** required when the chord has one (full, comp).
3. **The defining colour:** any altered tone named in the suffix (b9, #9, #11, b13, b5, #5). Required in full and in
   comp. This is why the Lydian card's comp still floats.
4. **Named colours:** the 9, 11 or 13 in the suffix (9, maj9, m9, add9, 6/9, 11, m11, add11, 13, maj13, m13). Required
   in full, left to him in comp.
5. **The root in the upper voices:** required when the bass is not the root (a slash chord), in full and in comp, so
   the chord keeps its identity.
6. **The natural fifth:** optional. It fills a free voice, and it becomes required when the round-trip gate (4.8) needs
   it. Bbm11/Gb needs its F.
7. **The bass pitch class is never doubled** in the upper voices. The one exception is the root of a root-position
   chord, allowed only when there would otherwise be fewer than 3 upper voices (sus2).
8. **If the required tones outnumber the voices,** voices = required (at most 6: Bbm11/Gb needs root, b3, 5, b7, 9 and 11 over its Gb). Otherwise fill in this order: named
   colours not yet in, the fifth, then the doubled root.

Worked counts. m11: b3, b7, 9, 11. maj7#11: 3, 7, #11 plus the 5th. Bb11/Ab: D, C, Eb, Bb. 7sus4: 4, b7, 5. m6: b3, 6,
5. sus2: 2, 5, doubled root.

### 4.3 Candidates

Upper voices, for the chosen pitch classes P (n of them):
1. For each ordering of P (at most 120), place the first note on its one instance in [lo, lo+11], and also an octave
   up if that still fits.
2. Place each later note on the first instance above the note before it, or the instance an octave above that. That
   gives at most 120 x 2 x 2^(n-1) raw shapes (1920 for n = 5).
3. Keep a shape only if all of these hold:
   - every note is at or under the hard top;
   - no adjacent pair breaks its low-interval limit (4.4);
   - the upper span is 24 semitones or less;
   - no two voices are 13 semitones apart (a minor 9th), unless the chord's name has a b9;
   - the top two voices are not a minor 2nd apart.
4. Remove duplicates, sort by static cost (4.5), and keep the best 40.

The bass: its pitch class in [28, 50] (at most two octaves). Pair each bass with the upper shapes whose lowest note
is at least 7 semitones above it and passes the limit for that pair.

### 4.4 Low-interval limits (the lowest allowed lower note of an adjacent pair)

| Interval | m2 | M2 | m3 | M3 | P4 | TT | P5 | m6 | M6 | m7 | M7 | 8ve | m9 | M9 | 10th+ |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Lowest lower note | E3 (52) | Eb3 (51) | C3 (48) | Bb2 (46) | Bb2 (46) | B2 (47) | Bb1 (34) | F2 (41) | F2 (41) | F2 (41) | F2 (41) | none | E2 (40) | Eb2 (39) | none |

These are the usual arranging guidelines, with middle C = C4, and they are constants that can be tuned. The draft
sunrise ending's F#1 F2 Ab2 Bb2 Db3 fails four of them (1.3).

### 4.5 Static cost S (lower is better)

```
S = 0.5 * |mean(upper) - centre|             centre: full 58 (Bb3), comp 55 (G3)
  + 1.0 * max(0, top - soft_top)
  + 0.3 * distance(bass, [36, 47])
  + 0.3 * max(0, 10 - (lowest_upper - bass)) + 0.3 * max(0, (lowest_upper - bass) - 24)
  + 0.4 * (inner minor seconds)
  - 0.4 * [the top voice is the 9th, #11/11 or 13th]   (his lush sound: colour on top)
```

### 4.6 Move cost T(a, b) between consecutive chords

```
T = sum of |movement| over matched upper voices    (sorted pairing when the counts match; else the best assignment,
                                                    plus 1.5 per voice added or removed)
  - 1.0 * (upper MIDI notes present in both)       (common tones held: they tie in the groove, 5.1)
  + 0.8 * max(0, |top_b - top_a| - 3)              (a smooth top line matters most)
  + bass: 0 if the same note; 5 if the same pitch class in another octave;
          otherwise 0.15 * min(|d|, 7) + 0.6 * max(0, |d| - 7)
  + 1.0 * [the bass and top voice move in parallel octaves or fifths]
```

The same chord twice in a row must keep its voicing: T is 0 for the identical voicing and 3 for anything else.

### 4.7 The ring

Chords c0..c(N-1), each with its candidates K_i (at most 40, after the round-trip filter):

```
for each start candidate x in K_0:
    D_0(x)  = S(x)
    D_i(y)  = S(y) + min over z in K_(i-1) of ( D_(i-1)(z) + T(z, y) )      for i = 1..N-1
    total(x) = min over y in K_(N-1) of ( D_(N-1)(y) + T(y, x) )            the wrap move back to the top
choose the x with the lowest total; backtrack the rest
```

The cost is N x K^3 move evaluations: 512,000 for an 8-chord loop, well under a second in node. N = 1 simply takes the
lowest S. A card played once (Play, `passes: 1`) uses an open chain with no wrap term. Ties go to the lower total S,
then to the lower MIDI list, so the output is deterministic.

### 4.8 Round-trip gate

Before the ring runs, each full and pad candidate goes through `Theory.detect` with the key's bias, the way the
bridge's `readBack` already does. Only candidates reading `exact` or `enharmonic` are kept.

If none survive:
1. Add the omitted optional tones one at a time (up to 6 upper voices) and try again.
2. If still none, keep the best shape, set `reads_as` to the page's reading, and warn, as `design-ux.md` 4.1's
   "reads as" line expects.

`comp` and `bass` are not gated. They leave colours to him by design, their label is the card's chord, and the page
never names cue notes anyway.

### 4.9 What it fixes, and its receipt (R-M1)

It fixes the three failures in 1.3: tops above C5, a bass sinking into mud, and no wrap move.

R-M1 runs over every starter loop (section 10), in the card's key and in each of Eb, F, D, Gb, Db and C, for full and
comp. It passes when:
- every full voicing reads `exact` or `enharmonic`;
- every top is at or under A4, and every comp top at or under E4;
- no adjacent pair is under its limit;
- the wrap move costs no more than the loop's largest other move;
- the same request gives byte-identical output.

---

## 5. Grooves (`arsenal/web/piano/groove.js`, pure)

```
bar(card, settings, pass, barIndex) -> [{ beat, midi, vel, len, role, voice, tie, ms }]
```

- `beat` counts from the bar's downbeat, and is negative for pickups. A bar owns its pickups: the push on the & of 4
  and the approach bass on beat 4 of the bar before (6.2).
- `len` is in beats. `ms` is the humanising offset, applied after beats are turned into milliseconds.
- `voice` is `bass`, `upper`, `motif` or `tick`.
- `tie: "next"` marks a note that carries into the next bar when the same note is voiced there (5.1).

### 5.0 Words used below

Beats in a chord are 0, 1, 2, 3; `&1` is the offbeat eighth after beat 1, placed by `feel`. L is `level` plus the
groove's offset (7.3). u1..un are the upper voices, from the bottom; the top voice is un. The tables are for a 4-beat
chord; 2-beat and 3-beat chords follow each groove's note.

### 5.1 Rules every groove shares

- **Ties.** Where a note sounds to the end of its chord and the next chord voices the same MIDI note in the same role
  group, the next strike is skipped and the note carries on. In the page this is one player call: `extend` moves the
  note's release (6.2). With the `keys` timbre, a tied note keeps decaying; that decay is the sound of a lament.
- **Gate.** A note that sounds "to chord end" is released 0.03 beat before the next chord, unless it ties.
- **Humanising** (h = `humanize`). The random source is mulberry32, seeded with FNV-1a-32 of
  `"${seed}:${pass}:${bar}:${voiceIndex}"`, so JavaScript and the node bridge draw the same numbers. Normal draws come
  from Box-Muller.
  - Timing: upper strikes N(0, 5h ms), bass N(0, 2.5h ms), both clamped to +-12h ms. A downbeat bass is never earlier
    than -4 ms.
  - Roll: a chord struck together rolls bottom-up, voice i at i x r. For hold and gospel, r ~ U(4, 9) x h ms. For
    ballad, r ~ U(8, 14) x h ms (25-40 ms across 4 voices: the soft ballad roll). Pulse and arp never roll.
  - Velocity: `L + accent + round(N(0, 2.5h)) + breath + arc`.
    - `breath` is a per-bar random walk: steps of -1, 0 or +1 (probabilities 0.3, 0.4, 0.3), times h, clamped to +-4.
    - `arc` is `round(3h x sin(pi (k + 0.5) / B))` for loop bar k of B, so the middle of the loop swells a little and
      the top relaxes (he plays with real arcs).
    - Passes 1 and 2 get -2 more (settling in). The top voice never goes above L + 2 unless a table says otherwise.
  - Length: x (1 + U(-0.03, 0.03) x h).
- **Feel.** An offbeat eighth sits at r/(1+r) of the beat, where r is the swing ratio: 1.0 gives 0.5 (straight), 1.6
  gives 0.615, 2.0 gives 0.667. `triplet` puts offbeats at 2/3 and allows triplet cells.

### 5.2 `hold` (held voicings)

| At | Who | Velocity | Length |
|---|---|---|---|
| 0 | bass | L+2 | to chord end (ties if the next bass is the same note) |
| 0 | upper, rolled | L-4, top voice L | to chord end; tied notes carry |
| 2 | upper voices that are not tied (keys timbre only, chord of 4+ beats, beat of 0.6 s or more) | L-12 | to chord end: a soft "breath" re-strike so a decaying tone doesn't die |

With the `pad` timbre there is no breath row. A 2-beat chord uses row 0 only.

### 5.3 `swell` (pad timbre)

| At | Who | Velocity | Length |
|---|---|---|---|
| 0 | bass | L-2 | to chord end + 0.5 beat |
| 0, 0.25, 0.5, 0.75 | u1, u2, u3, u4 (staggered entries) | L-6 | to chord end + 1 beat (a crossfade into the next chord) |

The attack time is min(1.5 beats, 1.2 s). An identical note in the next chord ties instead of re-attacking.

### 5.4 `ballad`

| At | Who | Velocity | Length |
|---|---|---|---|
| 0 | bass | L+4 | 1.9 (0.95 before a beat-4 approach) |
| 0 | upper, rolled (r 8-14 ms) | L-2, top voice L+2 | 1.95 |
| 2 | second bass: the natural 5th nearest the first bass, if the chord has one, is in root position and the note is in range; else the root again | L-2 | 1.9 (0.95 before an approach) |
| 2 | inner upper voices (all but the top) | L-10 | 1.95 |
| 3 | approach bass (walk of 1 or more, next bass differs, 5.8) | L-6 | 0.9 |

A 2-beat chord uses the beat-0 rows, plus an approach on beat 1. In meter 3, beat 0 has the bass and upper voices,
and beats 1 and 2 have the inner upper voices at L-10 for 0.8 beat (a waltz).

### 5.5 `pulse` (upper voices = 3: the 3rd or sus, the 7th or 6th, and the top colour)

| At | Who | Velocity | Length |
|---|---|---|---|
| every eighth: 0 &0 1 &1 2 &2 3 &3 | upper | L-4 + accent, accents by eighth [+6, -6, -2, -6, +3, -6, -2, -4] | 0.28 beat |
| 0 | bass | L+2 | 1.9 |
| 2 | bass (root) | L | 1.9 (0.95 before an approach) |
| &3, push on, next chord differs | the next chord's upper voices instead | L-2 | ties through the next chord's beat 0, whose upper strike is skipped |

In meter 3 there are 6 eighths, with accents [+6, -6, -2, -6, +2, -6].

### 5.6 `arp` (broken chords)

- **Bass** on beat 0 at L+4, held to chord end.
- **Upper voices** one per eighth, following a pattern of voice numbers (a number above n means the top voice):
  - `updown` (default): [1, 2, 3, 4, 3, 2, 1, 2];
  - `up`: [1, 2, 3, 4, 1, 2, 3, 4];
  - `rolling`: [1, 3, 2, 4, 1, 3, 2, 4].
- **Velocity** L-8 + 2 x (voice number - 1), so the top voice is the loudest; +3 on eighths 0 and 4.
- **Length.** Each note is held to chord end (a pedal), capped at 3 s. A voice struck again releases its previous
  strike (the voice already restrikes this way). Everything releases 0.02 beat before the next chord, unless the next
  chord holds the same note.
- **Rate.** At 64 bpm and slower the rate becomes sixteenths, the pattern played twice per bar.
- **Meters.** Meter 3 uses [1, 2, 3, 4, 3, 2]. Meter 6 (6/8, a beat = a dotted quarter) uses the same six eighths
  per bar.

### 5.7 `gospel` (feel swing 1.6, push on, by default)

| At | Who | Velocity | Length |
|---|---|---|---|
| 0 | bass root | L+4 | 1.4 |
| &1 | bass an octave up (if that is 52 or lower; else an octave down) | L-6 | 0.4 |
| 2 | bass root | L | 1.4 |
| &3 | approach bass when the next bass differs: a half step below it (above if below E1) | L-4 | 0.45 |
| 0 | upper, rolled (r 4-9 ms); skipped when the previous bar pushed | L | 1.3 |
| &1 | upper voices minus the lowest (a stab) | L-6 | 0.35 |
| &2 | upper voices minus the lowest | L-8 | 0.3 |
| &3 | push: the next chord's upper voices (next chord differs); a stab at L-8 for 0.3 when it is the same chord | L+1 | ties through the next beat 0 |
| 3 (spice 2 only) | the next chord's upper voices a half step higher (an approach chord), then the push at &3 | L-6 | 0.45 |

Gospel needs meter 4; in meter 3 it falls back to ballad.

### 5.8 The bass line

- **Register.** The voicer chooses the bass note in E1-D3. Groove octave notes stay within E1-E3 (28-52).
- **Approach notes** (`walk`), from this bass b to the next bass nb, with d = nb - b:
  - |d| of 2 or less: none (it already steps).
  - |d| of 3-4: a passing note from the key's scale between them (the one nearest the middle; the lower of two). If
    no key note lies between, the chromatic middle (the lower).
  - |d| of 5 or more: a half step below nb (above, if below E1).
  - `walk: 2` also uses a fifth below nb (when that is E1 or higher) on even passes, for variety.
- **`bass_mode: pedal`.** One bass note (the loop's tonic, or a given note) sounds under every chord, re-struck on the
  first bar of every 2 at L-2. The voicer treats each chord as a slash chord over it, so the gate reads, for example,
  Bb7sus4/Eb.
- **Written lines,** such as the lament Bbm11 -> Bbm11/Ab -> Bbm11/Gb, are played as written. The voicer's
  common-tone term keeps the upper structure identical, those notes tie, and only the bass walks.

### 5.9 Meters

Meter 4 has every groove. Meter 3 has hold, swell, ballad (the waltz), pulse and arp. Meter 6 has hold, swell, arp,
and ballad with the bass on eighths 1 and 4. Meters 2, 5 and 7 have hold, swell and pulse (eighths accented +6 on
each beat).

### 5.10 Call and response

`call: { pattern: "CR" | "CCRR" | "CRRR" | "CCCR", respond: "bed" | "silent", motif: true }`. The pattern repeats bar
by bar from the top of the loop.

- **Call bars.** The groove plays at L. With `motif`, Claude also plays a short tune in C5-C6 (72-84): his register,
  which is empty while he listens.
  - Rhythm, by call number c mod 3:
    - T0: [0, &0, &1, 2 held 1.5];
    - T1: [&0, 1, &1, 3 held 1];
    - T2: [0, 1, &1, &2, 3 held 1].
    A 2-bar call uses T(c+1) in its second bar, its last note held.
  - Pitches:
    - Start on the chord tone (3rd, 5th, 7th or 9th) nearest E5 (76).
    - Each next note moves along the chord's scale (9.5) by the contour steps [+1, +1, -1, +2, -1].
    - The last note goes on the colour (9, #11, 13, or 11 on a minor chord) nearest the step's landing, held: a
      question.
  - Velocity L+12, humanised as upper voices.
  - The next call reuses the same rhythm moved to the next chord's scale degrees (a sequence), so an echo comes
    naturally.
- **Response bars.** `bed`: bass and upper voices once on beat 0 at L-10, held to the bar's end. `silent`: nothing.
  The bar clock keeps running; the strip says `you` (UX).
- **Analysis.** The pattern plus the tempo map (section 8) mark every call and response window, and the generator
  rebuilds the motif notes.

### 5.11 Count-in

As `design-ux.md` 5.1: 20 ms sine ticks, 2 kHz on beat 1 and 1.5 kHz on the others, velocity 60, one bar by default,
on bar -1. Ticks always sound in the page's built-in voice, even when the backing goes to FL by MIDI (FL has no tick
instrument). Bar 0's pickups (a push, an approach) play over the last beat of the count-in.

### 5.12 Backing and groove together

| backing | Notes the groove uses |
|---|---|
| full | the band `full` voicing |
| comp | the band `comp` voicing: 2-3 upper voices; pulse and arp work over the voices that exist |
| bass | the bass rows of the groove only (approach notes included) |
| pad | the `full` voicing with groove forced to `hold`, base velocity 45 (UX section 10), pad timbre |

---

## 6. Transport and timing

### 6.1 The clock (kept from `design-ux.md` 5.1)

Bar lines sit on the `performance.now()` clock and are never accumulated. The clock is a **tempo map**, a list of
segments `{bar, t_ms, bpm}`, optionally with a ramp `{to_bpm, to_bar}`.

- A plain segment. For bar n inside a segment starting at bar b with tempo B, in meter m:
  `t(n) = t_ms + (n - b) x m x 60000 / B`. A beat position x inside bar n is `t(n) + x x 60000 / B`.
- A ramp from B0 at bar b0 to B1 at bar b1, where u counts beats from b0 and Lb = (b1 - b0) x m:
  - tempo(u) = B0 + (B1 - B0) x u / Lb
  - t(u) = t0 + (60000 x Lb / (B1 - B0)) x ln(tempo(u) / B0), when B1 is not B0.
- After the ramp, a new plain segment starts at bar b1.

Only the map's inputs are stored. Every time is computed from them.

### 6.2 Handing bars to the player

- **When.** Bar n, with its pickups, is generated and handed to the cue player at `H(n) = t(n) - (1 beat + 150 ms)`.
  One beat covers the earliest pickup (the ballad's beat-4 approach); 150 ms is margin over the player's 60 ms
  lookahead.
- **How** (change needed in `cues.js`). The player must take an absolute start: `player.handle(cue, { at: perfMs })`,
  with `base = at` instead of `now() + 50 ms`. Otherwise the worker timer's own wake lateness lands in every note.
- **Ties** (also a player change). `player.extend(cueId, step, offAt)` moves a note's release. A tied note is handed
  with its release at the next downbeat + 30 ms. When the next bar is handed and continues the note, the transport
  extends it. When a change or stop lands there instead, nothing needs doing: the note just ends at the bar line.
- **Why a bar and not a pass** (UX 5.1 queues a whole pass). A pass of 8 bars at 60 bpm is 32 s of queued steps. A
  tempo change, a swap, a groove change or a stop at the bar line would each have to cancel queued steps. The player
  has no partial cancel, and `clear` would also silence Claude's other cues. Handing one bar at a time leaves at most a
  bar and a beat queued, so every change lands on "the first bar not yet handed" with nothing to cancel.

### 6.3 Changes

**Rule: a change lands on the first bar line at least 1 beat + 150 ms away when it arrives.** The strip shows
`queued . bar N`, and the jam record logs the bar where it actually landed.

| Change | Lands | Notes |
|---|---|---|
| another Loop (swap) | the next free bar | a new jam record (UX 9.1); the count-in is skipped because the clock continues |
| tempo | the next free bar | a new map segment; `--ramp-bars k` adds a ramp segment instead |
| key | the top of the next pass (UX) | voicings come from the per-key cache (3.1) |
| groove, backing, level, humanize, feel, walk, push, spice | the next free bar | settings are stored by bar (section 8) |
| call pattern | the next free bar that starts a pattern cycle | |
| stop, `at: bar` | the next free bar line | nothing is handed for that bar; held notes release at its downbeat through the voice's own release |
| stop, `at: top` or `passes: N` | the end of the pass | |
| `ending: home` | at the stop bar line | the loop's first chord in `hold`, at L, for 2 bars, then a 1.5 s release |
| clear | at once | the existing clear, which also cancels Claude's other cues |

### 6.4 Steady over minutes

- **Timer.** The player's worker timer (`cues.js createTimer`) wakes at each H(n), plus every 100 ms for beat pips.
  Every H(n) is computed from the map.
- **Sound placement.** The voice maps a note's `at` onto the audio clock with `getOutputTimestamp()`, which pairs a
  context time with the moment that sample reaches the output. Proposal: **fit that mapping instead of using the
  newest pair.**
  - Keep a (performanceTime, contextTime) sample from each wake over the last 10 s, fit a least-squares line, and map
    through the fit.
  - Re-seed the fit when a new sample lands more than 5 ms off the line (a device change or a glitch).
  - Why: the newest pair changes only once per audio callback, about every 10 ms in Windows shared mode, and carries
    that callback's timing noise into each note. The fit averages the noise away. It also follows the slow drift
    between the system clock and the sound card's clock, which typically differ by tens of parts per million, a few
    ms per minute.
  - The fit already gives speaker times, so do not add `outputLatency` on top of it.
- **Lateness.** A note already more than 20 ms past its time when the voice would get it is dropped and counted. The
  exception is a bass on a downbeat, which still plays up to 40 ms late. Nothing plays later than that; "late music is
  worse than none" is the voice's own rule.
- **Hidden window.** Dedicated worker timers are not throttled the way page timers are (cues.js relies on this), and a
  page playing audible sound is exempt from Chrome's hidden-tab throttling (FL lane 4.1). On the MIDI-only route the
  page makes no sound, so only the worker keeps time; R-M4 tests that case.
- **Device change.** If the AudioContext's state leaves `running`, the transport stops at once (a clear of its own
  notes), the jam record stops with reason `device`, and the strip says so. Restarting is a new Loop.
- **Polyphony.** 40 voices while a jam runs (24 today). Estimated worst cases:
  - arp at 60 bpm: about 10 voices (bass, 4 held, restrikes);
  - pulse at 96 bpm: about 8 (3 voices, a 0.28-beat gate, release tails);
  - gospel: about 12 with ties and stabs;
  - plus any Play cues on top.

  The steal rule is unchanged.

### 6.5 Route F (FL as the clock)

Per the FL lane (5.1, 5.2, 5.5):
- Python follows FL's MIDI clock, smoothed over 24-96 ticks, with bar numbers corrected by the bridge script's beacons.
- It asks `arsenal/groove_bridge.mjs` for each bar's events in beats, turns beats into times from its own tempo and
  phase, and sends them on the "Claude Backing" loopback: bass on channel 1, chords on channel 2 (the FL lane's
  assignment).
- The page listens to the same port (every port is shared) to draw the notes, and logs the bar beacons it receives
  over SSE as the jam record's tempo map.
- The steady offset between beacon and sound (FL's 256-sample buffer plus the hop) is absorbed by the calibration
  (8.2).

### 6.6 Receipts

Headless, in an isolated Chrome with the anti-throttling flags and `--mute-audio`, on the builder's own server (the
PIANO-V2 hard rules).

| ID | Check | Pass |
|---|---|---|
| R-M2 | groove.js unit tests (node) | the same inputs give byte-identical events; with humanize 0 every event sits exactly on its table position; transposing the card moves every pitch and changes no timing; ties and pickups belong to the right bar; meters 3 and 6 follow 5.9 |
| R-M3 | a 10-minute soak: pulse, full, 92 bpm, humanize 0, a click-like test timbre; an AudioWorklet probe before the destination records the sample frame of each onset | every onset within 1 ms of its bar-line time mapped through the fitted clock; p99 error at most 2 ms; drift slope under 0.1 ms/min; a tempo change and a stop at bar 200 land on the bars the strip announced. If `--mute-audio` changes `getOutputTimestamp`, the receipt says so |
| R-M4 | as R-M3 with the window covered, and again on the MIDI-only route (no page audio) | worker wake lateness p99 at most 10 ms; zero dropped notes |

---

## 7. The sound

### 7.1 Who leads

His Kontakt piano leads. The backing stays apart from it in two ways:
- **Register:** the band voicer (section 4).
- **Timbre:** rounder and darker than an acoustic piano, or sustaining where his piano decays.

### 7.2 Timbres (additions to `createClaudeVoice`)

| Timbre | For | Sound |
|---|---|---|
| `keys` (backing preset of today's felt/electric piano) | ballad, pulse, arp, gospel, bass | Today's partials, with the sawtooth's gain x 0.6 and a darker filter: bright = min(6000, f(2 + 7v^2) + 200 + 1200v^2). Hard strikes bark less than Claude's Play voice, and the backing stays under his piano's brightness. Notes below E2 (40) play sine partials only, a round bass that doesn't fight his left hand. Optional auto-pan tremolo (4.5 Hz, depth 0.15), off by default. |
| `pad` (new, sustaining) | hold, swell, pad | Per strike: two sawtooths at -6 and +6 cents plus one sine. Lowpass at Q 0.7, cutoff min(3200, 500 + 1400v) Hz, with a shared 0.12 Hz LFO moving the cutoff +-12%. Attack 0.12 s (swell: from the groove), sustain at peak, release time constant 0.35 s (about 2.4 s to -60 dB). Peak = VOICE_LEVEL x 0.5 x (0.3 + 0.7v^2). A voice ends only at release. |
| `tick` | count-in | the UX ticks (5.11) |

### 7.3 Levels

- **Base velocity** L = 44. Groove offsets: hold -2, swell -4, ballad 0, pulse -4, arp -2, gospel +2. Motif notes
  L+12 (5.10).
- **Master.** "Claude volume" (UX default 70) stays the master. His piano's level against Claude's cannot be measured
  on Route P today (open question 4), so it is set by ear: the deck's slider, or `pianocue jam set --level`.
- **Duck** (proposed amendment to UX 5.1, which uses gain 0.5 while any of his notes struck in the last 0.8 s, back
  over 400 ms):
  - Proposal: gain 0.7 (-3 dB), attack 80 ms, held until 1.2 s after his last onset, then a release with a 0.6 s time
    constant.
  - Why: his median gap between attacks is 216-316 ms (1.1). With UX's setting the backing sits 6 dB down the whole
    time he riffs, then swells back within 400 ms at every rest longer than 0.8 s: a pump on each breath. A 3 dB dip
    held through phrase breaths still clears space and keeps the bed steady.

### 7.4 MIDI out to FL (Route P)

1. **A loopback port. Both options are downloads, so Daniel decides.**
   - The FL lane recommends Microsoft's Windows MIDI Services SDK Runtime and Tools, then permanent loopback pairs.
     The in-box transport is already on this machine.
   - loopMIDI is the alternative.
   - Until one exists, the backing uses the built-in voice only.
2. **The page.** `voice.setMidiOutput(port)` plus `setInternal(false)` for backing notes; ticks stay internal.
   - Channels: bass on channel 1, upper voices and motif on channel 2 (the FL lane's assignment). Today's cues.js
     sends channel 1 only, so `midiNoteOn` needs a channel argument.
   - MIDI sends need `at` (performance time), mapped through the same fit (6.4). Today a note given `{time}` skips
     MIDI.
3. **FL** (Daniel does these or approves them; they are FL settings):
   - enable the loopback input with a port number;
   - put a keys instrument (for example Arturia Stage-73 V2) or a pad (Analog Lab V) on channel 2 of that port;
   - put a bass (FL Transistor Bass, or a Kontakt bass) on channel 1;
   - leave Daniel's piano on the KeyLab port;
   - do not send master sync to this port.
4. **Echo guard** (piano.js, two small changes):
   - `midiRank` returns -1 for an input whose name matches the chosen MIDI output, or matches `/loopback|loopmidi/i`;
   - `onMidiMessage` drops channel 1 and 2 notes arriving from any port other than a KeyLab while a Claude MIDI output
     is active.

   Without these, "All inputs" feeds Claude's notes back in as Daniel's (1.4).
5. **Timing.** `midi_offset_ms` (default 0) sends MIDI earlier to cover FL's buffer: 256 samples, about 5.3 ms, plus
   the plugin. Tune it by ear against the page's ticks, or with the tap-along (8.2). The precision of Chrome's
   timestamped `send` through a loopback on Windows has not been measured (FL lane open question 1). The FL lane's
   click drill must be done before trusting it.
6. **Velocity.** `midi_vel_offset` (default 0), set by ear per instrument.

### 7.5 Recording

Follow `design-ux.md` section 7:
- In `auto`, Claude's built-in sound is not in the recorded track during REC.
- On the MIDI route the backing is part of his FL mix, so it is in anything that records his interface.

The deck says so next to the MIDI out choice (UX already specifies that line).

---

## 8. The jam record, as the analysis needs it

### 8.1 Additions to `design-ux.md` 9.1

```json
{ "jam": "j-20260914-214012-3f1a", "session": "20260914-212001-...", "card": "c-lament-bass", "rev": 3,
  "kind": "loop", "key": "Db", "meter": 4, "view": "auto",
  "bar0_t_ms": 612400, "stopped_t_ms": 746800, "passes": 11, "count_in_bars": 1,
  "engine": "groove/1", "route": "page", "midi_offset_ms": 0,
  "tempo_map": [ { "bar": 0, "t_ms": 612400, "bpm": 60 },
                 { "bar": 24, "t_ms": 708400, "bpm": 60, "to_bpm": 66, "to_bar": 28 },
                 { "bar": 28, "t_ms": 723664, "bpm": 66 } ],
  "settings": [ { "bar": 0, "backing": "full", "groove": "ballad", "level": 44, "humanize": 0.6, "seed": 90210,
                  "feel": "straight", "swing": 1.0, "walk": 1, "push": false, "spice": 1, "bass_mode": "written",
                  "ceiling": "G4", "call": null } ],
  "chords": [ { "text": "Bbm11", "number": "6m11", "beats": 4, "tones": { "root": 10, "third": 1, "fifth": 5,
                "seventh": 8, "ninth": 0, "eleventh": 3 }, "scale": [10, 0, 1, 3, 5, 6, 8], "scale_name": "Bb Aeolian",
                "class": "diatonic", "voicing": [46, 56, 60, 61, 63], "roles": ["bass", "seventh", "ninth", "third", "eleventh"] } ],
  "calibration": { "offset_ms": -14, "iqr_ms": 11, "taps": 14, "at": "2026-09-14T21:38:02Z" },
  "stop": { "reason": "stop", "bar": 44 }, "late_dropped": 0 }
```

(Illustrative. The ramp's end time is 708400 + 60000 x 16 / 6 x ln(66/60), which rounds to 723664.)

- `bar0_t_ms` is the downbeat of bar 0, after the count-in. All times are on the practice log's clock.
- `tempo_map` and `settings` rebuild every bar line and every Claude note exactly: the generator is deterministic
  (section 5), and the voicings are stored.
- A swap ends the record (UX); a key change mid-jam adds `key_changes: [{bar, key, chords}]`.
- The `jam` log kind (UX 9.1's hazard) stays the log lane's to add. `performance.summarize` must then skip that kind:
  `practice.sounding` and `pianocue._note_spans` already ignore kinds they don't handle, but summarize was not checked
  here.

### 8.2 Tap-along calibration (`pianocue jam calibrate [--bpm 80]`)

- One bar of count-in, then 16 ticks. He taps any key on each tick.
- For ticks 3-16: a tap within +-150 ms of a tick pairs with it, and offset = tap t_ms - tick t_ms.
- With at least 10 pairs, it stores the median offset and the IQR in `state/arsenal/piano/calibration.json`
  (git-ignored), and copies them into each jam record.
- What the offset contains: his taps are logged when MIDI arrives, but he hears his own sound from FL later (buffer
  plus plugin) and the tick when the page plays it. So it holds FL's delay plus his own tapping habit. That is exactly
  the baseline his playing should be measured against.
- What he is told, in words: "You tap 14 ms ahead of the page's clock. That includes FL's delay, so from now on your
  timing is measured against your own tap."

---

## 9. Riff analysis (`arsenal/practice_riff.py`, verb `py -m arsenal.practice riff <session|latest> [--jam ID|all] [--json] [--out PATH]`)

Read only, like the other practice verbs. Reports made from real sessions go under
`state/arsenal/receipts/practice-verbs/`. Everything below is computed on the log's clock.

### 9.1 Inputs and outputs

- **Inputs:** the session's events (his notes only; cue notes are never logged), and the jam records whose
  `[bar0_t_ms - 1 bar, stopped_t_ms + 2 beats]` overlaps the session.
- **Output:** JSON `arsenal.practice.riff/v0` (9.13) and markdown, plus what `design-ux.md` 9.3 asks for:
  - per bar, his top notes' degrees against the loop chord (most played, and per pass);
  - the share of his notes in the chord, colour and outside;
  - outside notes with times;
  - top-line range per pass, velocity per pass, where he rested, pedal share.

### 9.2 The grid

- **Bar lines.** From the tempo map (6.1). For an onset at time t: its bar n, beat b = beat position within the bar
  (exact inside ramps, from the ramp formula), whole beat j = floor(b), and phase p = b - j.
- **Grid classes.** Candidate grid points, each measured as p's distance to the nearest point:
  - quarter {0, 1};
  - eighth {0, s, 1}, where s = r/(1+r) from the jam's swing ratio;
  - triplet {0, 1/3, 2/3, 1};
  - sixteenth {0, .25, .5, .75, 1}.

  The class is the coarsest grid with a point within TOL = 0.08 beat (71 ms at 68 bpm): `beat`, `offbeat`, `triplet`,
  `sixteenth`, or `free` when none fits. Deviation (ms) = the signed distance to that point, times the beat length.
- **Metric weight** w_m: beat 1 = 1.0; beat 3 in meter 4 = 0.8; other beats = 0.6; offbeat eighth = 0.4;
  triplet/sixteenth = 0.3; free = 0.3.

### 9.3 His notes

- **Attacks.** Note-ons grouped within 50 ms (`ONSET_GROUP_MS`, as the practice verbs).
- **Top line.** The highest note of each attack, when that note is C4 (60) or above. Below that it is left-hand
  material; the threshold moves up to the backing's ceiling + 1 when he plays with `backing: full`.
- **Length** of a top-line note: until the next top-line onset or its `sound_end`, whichever comes first, capped at
  2 beats. The pedal must not stretch it (1.1).
- **Weight** w = w_m x clamp(length in beats, 0.25, 2).
- Every note is classified. Talking points about melody use the top line; "all notes" figures are reported
  separately.

### 9.4 Which chord a note is heard against

- **Normally,** the loop chord sounding at the onset (from the stored chord beats and the bar lines).
- **Anticipation.** The note is judged against the next chord when all of these hold:
  - the next change is at most min(0.5 beat, 300 ms) away;
  - the pitch class is a chord tone of the next chord;
  - it is not a chord tone of the current one.

  It is flagged `anticipates`.
- **Suspension.** A note struck before a change that keeps sounding at least 0.5 beat after it is also judged against
  the new chord. It is flagged `suspension resolved` when it is a rub or outside against the new chord and the next
  top-line note, within 1 beat, steps (2 semitones or less) to a chord tone of the new chord.

### 9.5 Chord facts: tones and scale (computed at publish time, stored in the card and the jam record)

- **Tones (T):** the pitch classes of the named chord's roles, **plus the bass pitch class** (so a slash bass is never
  a rub).
- **Scale (S),** in this order:
  1. the card names a scale: use it;
  2. otherwise the **section scale**: the 7-note scale on the loop's tonic (major, natural minor, harmonic minor,
     melodic minor, Dorian, Mixolydian, Lydian, Phrygian) that contains the most chords whole, ties going to the key's
     own scale. Every chord that fits it uses it. A two-chord Dm11 | G13 vamp gets D Dorian, so B natural is the 13 of
     G and the 6 of D, not a clash;
  3. chords that do not fit go by `practice.classify` (the practice verbs' own rules):

| class | S |
|---|---|
| diatonic | the key's scale; in a minor key, harmonic minor when the chord holds the raised 7th |
| borrowed | the parallel key's scale that fits (`fits` from classify) |
| modal | that mode on the key's tonic |
| secondary dominant, target minor (2m, 3m, 6m) | Phrygian dominant on the chord's root (root, b9, 3, 4, 5, b13, b7). F7 in Db major gets F Gb A Bb C Db Eb |
| secondary dominant, target major (4, 5) | Mixolydian on the root: the key's scale with the chord's 3rd raised. F9/A in Eb gets F G A Bb C D Eb |
| chromatic | by quality: maj7/6/add9 Lydian; dominant 7 Lydian dominant; m7/m9/m11 Dorian; m6 melodic minor; m7b5 Locrian natural 9; dim7 whole-half; sus Mixolydian |

  In every case, any chord tone missing from S replaces the scale note with the same letter.
- **Rubs (A)** (internal name `avoid`; the word Daniel sees is "rub"). A scale note that is not a chord tone and sits a
  half step above a chord tone. Exceptions:
  - on dominant chords, b9 and b13 are colours (altered tensions), not rubs;
  - on sus chords, the major 3rd is a rub (it cancels the sus).

  Checked against his loops:
  - Ebmaj9: Ab is a rub, C a colour.
  - Abmaj7#11: no rubs.
  - Cm11: Ab is a rub.
  - Bb13: Eb is a rub.
  - Bb7sus4: D is a rub.
  - Bbm11/Gb: none (Gb is the bass).
  - Abm6: Gb is a rub.
  - F7 in Db: Gb and Db are altered colours; Bb is a rub.
- **Colour labels,** by interval from the root: 1 b9, 2 9, 3 #9, 5 11, 6 #11, 8 b13, 9 13 (`practice.TENSIONS`).

### 9.6 Note classes (first matching rule wins)

| # | Class | Rule | UX word (6.4) |
|---|---|---|---|
| 1 | chord tone (root, 3rd, 5th, 7th, 6th, sus, bass) | pitch class in T | in the chord |
| 2 | colour (with its label) | in S, not in T, not a rub | colour |
| 3 | passing | a rub that is short (under 1 beat) on a weak position (w_m under 0.6) and steps (2 semitones or less) to a chord tone or colour within 0.5 beat | colour |
| 4 | rub | a rub otherwise (held, or on a strong beat) | colour (the report names the rub) |
| 5 | slide-in (approach) | not in S, at most min(0.5 beat, 300 ms) long, and the next top-line note within 1 beat is 1 semitone away and a chord tone or colour; noted `from below` or `from above` | outside |
| 6 | enclosure | two notes around a target (above then below, or below then above), the second landing on the target within 1 beat, where the target is a chord tone | outside |
| 7 | blue note | a b3 (interval 3) over a chord with a major 3rd, followed within 0.5 beat by the 3rd | outside |
| 8 | outside | anything else; also noted `in the key, not this chord` when the pitch class is in the key's scale (for example the key's D natural over the borrowed Abm6) | outside |

**Why the report's labels are finer than the live marks.** UX 6.4 marks "in the chord" when the pitch class is in the
NOW chord's *voicing*. Proposed amendment: use the chord's tones T. With `comp` the voicing leaves out the 5th and
every colour, so a plain 5th would get a colour diamond. The live marks and the report should agree.

### 9.7 Scales and modes

**Per chord.** Only for a chord with at least 12 top-line notes over it, across the jam.
1. Build a histogram h over intervals from the chord's root, weighted by w, normalised to sum to 1.
2. Score candidate scales rotated to the root: the seven modes of major, melodic minor, Lydian dominant, altered,
   harmonic minor, Phrygian dominant, major and minor pentatonic, minor blues (minor pentatonic + b5), major blues
   (major pentatonic + b3), whole-half diminished, whole tone.
   `score = coverage - 0.04 x (size - 5) - 0.05 x (scale degrees with share under 0.02)`.
   This is the formula prototyped in 1.2, where over whole keys it picked the major scale (0.908-0.916) over major
   pentatonic (0.769-0.823).
3. Report the best, the runner-up and the margin.

**Naming gate (honesty).** A mode is named only when its own note carries at least 5% of the weight over that chord:

| Mode | Its own note |
|---|---|
| Lydian | #4 (6) |
| Mixolydian | b7 (10) |
| Dorian | 6 (9), with a b3 |
| Aeolian | b6 (8), with a b3 |
| Phrygian | b2 (1) |
| Locrian | b5 (6), with a b3 |
| Lydian dominant | #4 and b7 |
| altered | b9 or #9, and b13 |

A pentatonic is named only when every one of its 5 degrees is used and the scale's 4th and 7th together carry 3% or
less. Otherwise the report says "the notes of Eb major".

Example: over Abmaj7#11 in Eb, "you played Ab Lydian: the D, its #11, came up 9 times" is said only if the D really
carried 5% or more.

**Per key and per pass.** The same scoring over key-relative intervals names the parent scale and the lean: the share
on the 4th and 7th, 17-22% in his sessions (1.2). Per pass, the shares of colour, rub and outside are tracked for the
growth point (9.12, T13).

### 9.8 Rhythm

- **Placement.** Signed deviations of onsets in the `beat`, `offbeat`, `triplet` and `sixteenth` classes, minus the
  calibration offset. The median gives:
  - `ahead` when 12 ms or more early, `behind` when 12 ms or more late, `on` otherwise, provided the IQR is 60 ms or
    less;
  - `loose` when the IQR is over 90 ms.

  Reported separately for downbeats and offbeats. Without a calibration: `not calibrated`, and only spread and drift
  are claimed.
- **Drift.** The Theil-Sen slope of deviation against time. "Pushing ahead" is -6 ms/min or steeper over at least
  2 minutes; "dragging" is +6 ms/min or steeper.
- **Swing.** Pairs of top-line onsets on a beat and on the offbeat after it (phase 0.4-0.75) with nothing between. The
  median ratio r = p/(1-p): straight under 1.2, light swing 1.2-1.6, swing 1.6-2.2, triplet feel above 2.2. Compared
  with the jam's `feel`.
- **Syncopation.** The share of attack length weight on offbeats. Anticipations of chord changes come from 9.4.
- **Density and rests.** Top-line onsets per bar, per pass; bars with no onset of his.

### 9.9 Phrases and motifs

- **Split.**
  - A top-line gap (from one note's capped end to the next onset) of at least max(1 beat, 600 ms) ends a phrase.
  - A phrase over 4 bars splits at its longest inner gap of 0.5 beat or more.
- **For each phrase:**
  - start (pass, loop bar, beat, session m:ss);
  - length in bars, rounded to 0.5;
  - pickup: its first onset falls in the last beat before a bar line and it continues past that line;
  - range;
  - contour: `rising` (end at least 3 above start, peak in the last third), `falling`, `arch` (peak in the middle
    third, both ends at least 3 below it), `valley`, or `flat` (range of 4 or less);
  - landing: the class and label of its last note.
- **Regularity.** A histogram of phrase lengths: the most common length, its share, and whether it matches the loop's
  length or half of it.
- **Motifs.**
  - Sequences of 3-5 top-line notes keyed by their intervals (so they are transposable) and their onsets on an eighth
    grid.
  - Kept when they occur 3 or more times, or twice in 2 different passes.
  - Reported with pitch names spelled in the key and every time.
- **Question and answer.** Consecutive phrases A and B count as a pair when all of these hold:
  - their lengths are within 0.5 bar of each other;
  - the gap between them is 1 bar or less;
  - their onset sets (eighth grid, from each phrase's first bar line) have a Jaccard similarity of 0.5 or more.

  The pair is noted `question/answer` when A lands on a colour and B on a chord tone of a 1 chord.

### 9.10 Call and response

For each call window (consecutive C bars) and the response window after it, the response window being [start -
0.25 beat, end + 0.25 beat]:
- **Answered:** any onset of his in the response window. **Entry:** the first onset's beat offset (negative is a
  pickup).
- **Intrusion:** his note weight inside the call window, not counting its last 0.5 beat, divided by his total weight.
- **Rhythm similarity J:** the Jaccard similarity of eighth-grid onset positions, each measured from its own window's
  start.
- **Contour similarity:** both pitch sequences resampled to 8 steps (step interpolation by note order), then Spearman
  rho.
- **Pitch overlap:** the cosine of duration-weighted pitch-class histograms.
- **Label:**
  - `echo`: J of 0.5 or more and rho of 0.6 or more;
  - `mirror`: J of 0.4 or more and rho of -0.4 or less;
  - `variation`: J of 0.3 or more, or rho of 0.4 or more, or cosine of 0.7 or more;
  - `new idea`: anything else with notes;
  - `silent`: no notes.

### 9.11 Per pass (the UX report's lanes and pass selector)

For each pass:
- top-line range;
- velocity median and p90 (the arc);
- the shares of in the chord, colour and outside;
- rests;
- pedal share (from the practice verbs' pedal spans);
- the most-played degree per bar;
- one plain fact that picks the pass out ("pass 7: your widest top line").

### 9.12 Talking points

- **Rules.** Facts only, each with its numbers, its session times, its pass and bar, and a replay command
  (`pianocue replay <session> <m:ss> --seconds 6`).
- **Words.**
  - in the chord / colour / outside (UX), rub, slide-in, pickup, landing, top line;
  - theory names only in brackets after the plain words ("the #11 (the Lydian sound)");
  - never "wrong", never a score.
- **Selection.**
  - salience = type weight x min(1, count / 5) x 1.25 when the point concerns the card's concept note (the #11 on the
    Lydian card, the 3rd of the real 5) x 0.5 when the same point was made for this card in its last report;
  - the report card takes the top 3 of different types (UX 9.3); chat takes up to 6.

| Type | Template (gate) | Weight |
|---|---|---|
| T1 colour on top | "Over Cm11 (6m11) your top line leaned on the 9, D: 11 of 26 notes, first at 1:12." (label at least 20% of that chord's colour weight, 4 or more notes) | 1.0 |
| T2 mode | "Over the 4 chord you played Ab Lydian: the D, its #11, came 9 times." (naming gate 9.7) | 1.1 |
| T3 landings | "8 of your 12 phrases landed on a colour, mostly the 9." (6 or more phrases) | 0.9 |
| T4 held rub | "At 1:12 you held Ab over Ebmaj9 for 2 beats: it rubs a half step against the G. At 0:50 the same Ab passed quickly and sat fine." (1 or more held rubs; pairs with a passing use when one exists) | 1.0 |
| T5 key note over a borrowed chord | "Over Abm6 (4m, borrowed) you played D natural, the key's note, 3 times; the chord's scale has Db." (2 or more) | 1.0 |
| T6 no slide-ins | "None of your 412 notes left Eb major." (outside plus slide-in under 0.5% and 100 or more notes) | 0.8 |
| T7 slide-ins used | "You slid into G from a half step below 4 times, first at 0:42." (3 or more) | 0.8 |
| T8 placement | "Against your tap-along you sat about 20 ms ahead, most of all on beat 1." (calibrated, gates in 9.8) | 0.7 |
| T9 drift | "From 2:10 you pushed ahead by about 8 ms a minute." (9.8) | 0.6 |
| T10 phrase length | "Your phrases were mostly 2 bars (9 of 12), and 7 started with a pickup." (6 or more phrases) | 0.8 |
| T11 motif | "You came back to Bb-C-Eb (up a step, up a third) 4 times: 0:42, 1:10, 1:55, 2:30." (9.9) | 0.9 |
| T12 call and response | "You answered all 6 calls; 3 echoed my rhythm, 1 turned it upside down." (pattern present) | 1.0 |
| T13 growth | "Colours went from 12% of your notes in passes 1-2 to 31% in the last two." (4 or more passes, change of 10 points or more) | 0.8 |
| T14 anticipations | "You arrived early on the chord change 5 times (the gospel push)." (3 or more) | 0.7 |
| T15 suspension | "At 1:40 your Eb over Bb7sus4 held into Ebmaj9 and stepped down to D: a suspension, resolved." (1 or more) | 0.8 |

- **One question** (UX 9.3): the highest-salience ambiguous moment (a held rub, an outside note of 1 beat or more, an
  unusual landing), put as a question about intent, with the moment's replay range. "At 1:12 the G natural rubbed
  against the Gb in the bass. Did you want that rub?"
- **One thing to try,** the first of these that applies:
  1. the card's concept note came up fewer than 2 times: "land your top note on it in bar N";
  2. held rubs recur (3 or more): "let the rub pass quickly, or step it down to the chord tone";
  3. no slide-ins (T6): "slide into the 3rd of chord X from a half step below";
  4. placement ahead or behind by 20 ms or more: "lay back" or "lean in";
  5. every phrase started on a downbeat: "start one phrase a beat early";
  6. in call and response, only new ideas: "echo my rhythm once".

  Each is published as a Try card (UX 9.3).

### 9.13 Output shape (JSON)

```json
{ "api": "arsenal.practice.riff/v0", "session": "...", "constants": { "...": "..." },
  "jams": [ { "jam": "j-...", "card": "c-...", "key": "Db", "calibration": { "offset_ms": -14 },
      "chords": [ { "index": 0, "text": "Bbm11", "number": "6m11", "notes": 38,
                    "shares": { "in_chord": 0.46, "colour": 0.41, "outside": 0.13 },
                    "colours": { "9": 0.22, "11": 0.15 }, "rubs": [ { "at": "1:12", "note": "Gb4", "beats": 2.0 } ],
                    "scale": { "best": "Bb Aeolian", "score": 0.91, "runner_up": "Bb Dorian", "named": false } } ],
      "passes": [ { "pass": 1, "range": ["Db5", "Ab5"], "vel_median": 51, "shares": {}, "rests": 1, "pedal": 0.82,
                    "degrees_by_bar": ["9", "11", "13", "4"] } ],
      "rhythm": { "placement_ms": { "all": -8, "downbeats": -15, "offbeats": -2 }, "iqr_ms": 34, "drift_ms_per_min": null,
                  "swing_ratio": 1.1, "offbeat_share": 0.38, "anticipations": 5 },
      "phrases": [ { "at": "1:04", "pass": 2, "bar": 1, "beat": -0.5, "bars": 2.0, "pickup": true, "contour": "arch",
                     "landing": { "class": "colour", "label": "9" } } ],
      "motifs": [ { "intervals": [2, 3], "names": ["Bb", "C", "Eb"], "times": ["0:42", "1:10", "1:55"] } ],
      "call_response": [ { "call_bars": [1, 2], "answered": true, "entry_beats": -0.5, "J": 0.57, "rho": 0.71, "label": "echo" } ],
      "notes": [ { "t_ms": 64210, "at": "1:04", "pass": 2, "bar": 1, "beat": 3.5, "note": 73, "name": "Db5", "chord": 0,
                   "class": "colour", "label": "9", "w": 0.8, "grid": "offbeat", "dev_ms": -11, "flags": ["anticipates"] } ] } ],
  "talking_points": [ { "type": "T2", "text": "...", "times": ["0:42"], "replay": "pianocue replay ... 0:40 --seconds 6",
                        "evidence": { "count": 9, "share": 0.07 } } ],
  "question": { "text": "...", "replay": "..." }, "try": { "text": "...", "card": { "target_notes": [69], "bar": 4 } } }
```

(The numbers are illustrative.)

### 9.14 Without a jam record (free play)

Chords come from `practice.analyze` windows, labelled "chords read from your own playing", with each window's scale
from its class. There is no grid, so sections 9.8, 9.10 and the placement points are left out ("no loop, no beat to
measure against"). Classes, scales, phrases (split by gaps of 600 ms or more) and motifs still run.

### 9.15 Constants (all written into the output, so every number can be reproduced by hand)

| Name | Value | | Name | Value |
|---|---|---|---|---|
| ONSET_GROUP_MS | 50 | | SCALE_MIN_NOTES | 12 |
| LINE_MIN_NOTE | 60 (C4) | | MODE_OWN_NOTE_MIN | 0.05 |
| LINE_LEN_CAP | 2 beats | | PENT_4_7_MAX | 0.03 |
| GRID_TOL | 0.08 beat | | SCALE_SIZE_COST / UNUSED_COST / UNUSED_SHARE | 0.04 / 0.05 / 0.02 |
| ANTICIPATE_MAX | min(0.5 beat, 300 ms) | | PLACEMENT_MIN_MS / MAX_IQR / LOOSE_IQR | 12 / 60 / 90 |
| SUSPEND_MIN | 0.5 beat | | DRIFT_MIN | 6 ms/min over at least 2 min |
| PASSING_MAX | under 1 beat, weight under 0.6, step within 0.5 beat | | SWING_BANDS | 1.2 / 1.6 / 2.2 |
| SLIDE_IN_MAX / RESOLVE | min(0.5 beat, 300 ms) / 1 beat | | MOTIF_N / MIN | 3-5 / 3 (or 2 in 2 passes) |
| PHRASE_GAP / MAX_BARS | max(1 beat, 600 ms) / 4 | | ECHO J, rho / MIRROR rho | 0.5, 0.6 / -0.4 |
| Metric weights | 1.0 / 0.8 / 0.6 / 0.4 / 0.3 / 0.3 | | TP_MIN_COUNT (patterns) | 3 |

### 9.16 Tests (R-M7)

- **Synthetic jam fixtures.** A known loop and tempo map, plus a planted riff: chord tones; 9 #11s over the 4 chord; a
  held rub and a passing one; 3 slide-ins; an enclosure; pickups; 2-bar phrases; a motif played 4 times; a +20 ms
  late lean with a calibration of -10; swing 1.6. The verb must report each one with the planted counts and times.
- **Invariance.** Transposing the whole fixture by any interval changes no class count and no talking point except
  the spelled names.
- **Tempo map.** A ramp puts beat positions within 1 ms of the formula.
- **No jam record.** No rhythm section, and no claim of placement.
- **R-M8, with Daniel.** One real jam over loop 1. He reads the report and says whether each fact matches what he
  remembers.

---

## 10. Starter loops

The titles match `design-ux.md` 4.7 where the idea is the same.

- **Numbers** are as the voicing bridge printed them tonight (`jam/voice_loops.py` and the alternate checks). Every
  chord below reads back `exact` or `enharmonic` in at least one voicing. The band voicer must keep that true (R-M1).
- **Split bars** use `chord:beats` (the `progression` syntax), for example `Gbsus2:2 Gbadd9:2`.
- **Fit or stretch.** "Fit" means it is his own move. "Stretch" names the one new thing.

| # | Title | Key . bpm . bars | groove / backing | Chords, then numbers | Fit or stretch |
|---|---|---|---|---|---|
| 1 | The Lydian 4 chord | Eb major . 68 . 4 | hold / full | Ebmaj9 \| Abmaj7#11 \| Cm11 \| Bb7sus4/Eb = 1maj9 \| 4maj7#11 \| 6m11 \| 5^7sus4/1 | fit |
| 2 | The gospel 5 over 4 | Db major . 72 . 4 | gospel (push, swing 1.6) / full | Gbmaj9 \| Ab11/Gb \| Fm9 \| Bbm11 = 4maj9 \| 5^11/4 \| 3m9 \| 6m11 | fit; stretch: the gospel pushes |
| 3 | Blooming chord, call and response | Db major . 66 . 8 | arp / full; call CCRR, respond bed, motif | Gbsus2:2 Gbadd9:2 \| Gbmaj9 \| Gbmaj9 \| Gbmaj9 \| Dbsus2:2 Dbadd9:2 \| Dbmaj9 \| Dbmaj9 \| Dbmaj9 = 4sus2 4add9 \| 4maj9 x3 \| 1sus2 1add9 \| 1maj9 x3 | fit; stretch: two bars of listening, then answering |
| 4 | Walking bass under a held chord | Db major . 60 . 4 | ballad / full | Bbm11 \| Bbm11/Ab \| Bbm11/Gb \| F7sus4:2 F7:2 = 6m11 \| 6m11/5 \| 6m11/4 \| 3^7sus4 3^7 | fit, ending on a real dominant |
| 5 | The half-step slide | Eb major . 70 . 4 | ballad / full | Ebmaj9 \| F9/A \| Fm9/Ab \| Bb9sus4 = 1maj9 \| 2^9/#4 \| 2m9/4 \| 5^9sus4 | fit |
| 6 | Down a minor third to a new home | Gb major, then Eb major . 72 . 8 | pulse / comp | Gbmaj9 \| Ebm11 \| Cbmaj7#11 \| Db7sus4 \| Ebmaj9 \| Cm11 \| Abmaj7#11 \| Bb7sus4 = (in Gb) 1maj9 \| 6m11 \| 4maj7#11 \| 5^7sus4, (in Eb) the same numbers | fit; stretch: the pulse groove |
| 7 | Borrowed colours | Eb major . 66 . 4 | ballad / full | Ebmaj9 \| Abm6 \| Cbmaj7#11:2 Dbmaj9:2 \| Ebmaj9 = 1maj9 \| 4m6 \| b6maj7#11 b7maj9 \| 1maj9 | fit |
| 8 | Suspended 5, then the real 5 | Eb major . 70 . 8 | ballad / full | Ebmaj9 \| Cm11 \| Fm9 \| Bb7sus4 \| Ebmaj9 \| Cm11 \| Fm9 \| Bb13 = 1maj9 \| 6m11 \| 2m9 \| 5^7sus4 \| 1maj9 \| 6m11 \| 2m9 \| 5^13 | stretch: his growth edge |
| 9 | The sunrise ending | Eb . 60 . 8 | swell / pad | Ebm11 \| Ebm11 \| Cbmaj7#11 \| Bb7sus4:2 Bb7:2 \| Gbmaj9 \| Gbmaj9 \| Abm6 \| Ebmaj9 = 1m11 \| 1m11 \| b6maj7#11 \| 5^7sus4 5^7 \| b3maj9 \| b3maj9 \| 4m6 \| 1maj9 | fit (a showpiece), with a real 5 |
| 10 | Same shapes, white keys | C major . 72 . 4 | pulse / full | Cmaj9 \| Am11 \| Fmaj7#11 \| G7sus4:2 G13:2 = 1maj9 \| 6m11 \| 4maj7#11 \| 5^7sus4 5^13 | stretch: geography |
| 11 | Two-chord Dorian vamp | D minor . 88 . 2 | pulse / comp | Dm11 \| G13 = 1m11 \| 4^13 | stretch: rhythm |

### Why each one, and what the riff report listens for

1. **The Lydian 4 chord.**
   - Why: session 20260914-010120 found the Lydian 4 six times between 2:04 and 3:36, and held Bb7sus4/Eb for 15.1 s
     over an Eb pedal from 2:36 (receipt `s1-harmony.md`).
   - The page has no name for Abmaj9#11 (it reads Cm9/Ab, 1.3), so the loop plays Abmaj7#11. In full the voicer may
     still add the Bb as a colour on top; the card's `reads_as` says so when it does.
   - Listen for: the D (the #11) in his top line over bar 2, and the rub Ab over Ebmaj9.
2. **The gospel 5 over 4.**
   - Why: session 20260914-012540 held Ab11/Gb for 8.5 s, and moved Ab11/Gb to Bbm11/Gb twice from 0:52.
   - The order 4-5-3-6 is the "royal road" progression, here with the 5 standing on the 4 in the bass. The same card
     in Eb reads Abmaj9 | Bb11/Ab | Gm9 | Cm11.
   - Listen for: anticipations (T14), and landings on the 9 of Fm9 (G).
3. **Blooming chord, call and response.**
   - Why: session 20260914-012540 opened on Gbmaj9 to Gbmaj13 (0:00-0:05), and played Gbadd9 to Gb6/9 three times
     from 1:16.
   - Claude blooms in bars 1-2 and 5-6, with the motif. Bars 3-4 and 7-8 are his, over a held bed; repeated chords tie.
   - Listen for: echoes (T12), and whether his answer adds one note at a time too.
4. **Walking bass under a held chord.**
   - Why: in session 20260914-012540, Bbm11/Gb was his longest chord (10.8 s), with Bbm11 at 7.5 s, Bbm11/Ab at
     7.1 s, and a chromatic F7/A at 1:35.
   - Bar 4's F7 holds A natural, the note outside Db major that pulls back to Bb. Bbm11/Gb reads exact only with its F
     (1.3), and the round-trip gate keeps it.
   - Listen for: A natural in bar 4, and where it goes. The UX report example asks exactly this.
5. **The half-step slide.**
   - Why: his slide F9/A to Fm9/Ab, from tonight's reading. Only one note moves, A to Ab, which is the bass and the
     chord's 3rd at once (the bridge measured 1 semitone of movement).
   - UX's second example, Gm7/Bb to Gbmaj7/Bb, loses one of its sliding voices in the page's naming (1.3). Keep it as a
     Play card, not a loop.
   - Listen for: A natural over F9/A, then Ab over Fm9/Ab, in his top line (does the melody slide too?).
6. **Down a minor third to a new home.**
   - Why: tonight's reading lists his key drops F to D and Gb to Eb. Every chord here reads back in its section's key.
   - The wrap from Bb7sus4 to Gbmaj9 rises a minor third, and Bb is Gb's 3rd, so both directions get practised.
   - Against one tonic (UX 4.3: a card has one), the Eb half would be 6maj9 | #4m11 | 2maj7#11 | 3^7sus4. That was
     worked out by hand; the bridge must confirm it.
   - Variation, bridge-verified: F major to D major with the same numbers (Fmaj9 Dm11 Bbmaj7#11 C7sus4 | Dmaj9 Bm11
     Gmaj7#11 A7sus4).
   - Listen for: G, C and D naturals arriving at bar 5 (three notes of Gb major rise a half step).
7. **Borrowed colours.**
   - Why: session 20260914-010120 heard Abm (4m) at 0:05, 5:15 and 5:23; Abm(add9) at 4:13 and 5:22; Bmaj7#11/A#
     (b6maj7#11/5) at 4:18 and 4:37; and Dbadd9/Ab (b7add9/4) at 0:01.
   - The page spells Cbmaj7#11 as Bmaj7#11 in Eb (enharmonic). Bars 3-4 are the Aeolian b6-b7-1 cadence that
     `practice.py` names.
   - Listen for: Cb and Gb (the borrowed notes) against the key's C and G over bars 2-3 (T5).
8. **Suspended 5, then the real 5.**
   - Why: session 20260914-010120 held suspended 5 chords for 18.1 s (Bb7sus4/Eb alone 15.1 s). Each of its five
     longest 5 chords with a major 3rd (Bb/Eb, Bb11/Ab, Bbadd11/Eb, Bbadd11, Bbadd9/F) also had the 4th (Eb) or lacked
     the 7th.
   - Bar 8's Bb13 has D and Ab with no Eb: the tritone that pulls to Eb and G.
   - Listen for: his top note on the downbeat after Bb13, and Eb held over Bb13 (a rub, T4).
9. **The sunrise ending.**
   - Why: tonight's reading named his ending Eb minor, then a Gb major climax, then Eb major. Session 20260914-010120
     went from Eb major (1:27-4:00) to Eb minor (4:00-5:25), with Eb major borrowed back at 5:05.
   - This loop's draft broke both of today's voicings (1.3).
   - Listen for: the G natural of the last bar, and whether the Gb major bars lift his top line (per-pass range, 9.11).
10. **Same shapes, white keys.**
    - Why: tonight he played in Eb, F, D, Gb and Db, where black keys anchor the hands. These are loop 1's numbers
      (plus loop 8's real 5) in a key where every chord's scale is white keys.
    - Listen for: B (the #11) over bar 3, the B-F tritone of G13, and habit notes Bb, Eb and Ab (outside, T5/T8).
11. **Two-chord Dorian vamp.**
    - Why: all four sessions are in free time, so there is nothing yet to measure his time against. At 88 bpm eighths
      are 341 ms apart, a little slower than his median gaps (216-316 ms), so eighths are easy and syncopation is the
      stretch.
    - One scale (D Dorian, all white keys), and one telling note: B natural, the 13 of G and the 6 of D.
    - Listen for: placement and swing (T8, with a calibration), phrase lengths (T10), B against Bb.

**A first night, in order:**
1. Loop 1 (meet the transport on a sound he loves).
2. Loop 3 (a conversation).
3. Loop 4 (the A natural).
4. Loop 8 (the growth edge).
5. Loop 11, after a tap-along calibration, or loop 10.

---

## 11. Alignment with `design-ux.md`

**Adopted as written:**
- one transport with bar lines on `performance.now()`;
- launches quantised to bar lines;
- count-in ticks;
- backing names full/comp/bass/pad, and pad at velocity 45;
- the jam record and its log-kind hazard;
- marks words;
- jam view and recording policy;
- the courtesy gate;
- report card limits: three facts, one question, one thing to try.

**Proposed amendments (each explained above):**
1. A second setting, `groove` (hold/swell/ballad/pulse/arp/gospel), beside `backing` (0 and section 5).
2. Hand the player one bar with its pickups, not one pass, with an absolute `at` and `extend` in the player (6.2).
3. The duck at -3 dB, held 1.2 s after his last onset, instead of gain 0.5 over 0.8 s (7.3).
4. "In the chord" marks from the chord's tones, not the voiced pitch classes (9.6).
5. Re-voice per key on the bridge instead of shifting -6..+5 (3.1).
6. Jam record additions: tempo map, settings by bar, chord facts and voicings, calibration (8.1).
7. R-J4 measured where the sound lands, sample-accurate (R-M3), as well as step lateness in JavaScript.

`comp` here is 2-3 upper voices under C4, reaching E4 only for a defining colour; UX says "bass and shell under C4".
This is the same idea, with one exception made for the Lydian card and its kin.

---

## 12. Build order and receipts

| Phase | Scope | Receipts |
|---|---|---|
| M1 | Band voicer in the bridge (4.1-4.8), `tones` pitch classes, chord facts in `pianocue.py` (9.5), per-key cache | R-M1, node tests |
| M2 | `groove.js` and `groove_bridge.mjs` (section 5) | R-M2 |
| M3 | Transport hooks with UX J2: bar hand-off, `at`/`extend` in the player, the fitted clock, the lateness rule, polyphony 40; the `keys` and `pad` timbres; duck | R-M3, R-M4; levels by ear with Daniel |
| M4 | Jam record additions, `pianocue jam calibrate`, the `jam` log kind (log lane first) | round trip: the analysis rebuilds bar lines within 1 ms |
| M5 | `practice riff` (section 9) and report data for UX 9.3 | R-M7, then R-M8 with Daniel |
| M6 | MIDI route: channels, `midi_offset_ms`, echo guard, once Daniel has approved a loopback | the FL lane's click drill, with a dated receipt |

---

## 13. Open questions

1. **A loopback for MIDI out.** Microsoft's Windows MIDI Services SDK Runtime and Tools (the FL lane's
   recommendation), or loopMIDI? Both are downloads that need Daniel's OK. Until then the backing uses the built-in
   voice.
2. **His chord names on screen.** Add `maj9#11`, `maj13#11` and `13sus4` to the page's THEORY templates? His signature
   Abmaj9#11 and Gbmaj13#11 read today as Cm9/Ab and Bbm11/Gb. The starter loops use maj7#11 so labels and screen
   agree.
3. **Amendments to `design-ux.md`.** Accept the seven in section 11?
4. **Where Chrome's sound goes.** Does Chrome play to the Focusrite? If so, the backing is in the "Loopback L + R" mix
   that PLAY-NIGHT analyses, and in any interface recording, and his piano's level cannot be measured separately for
   an automatic backing level.
5. **The FL route's clock and instruments.** Once the MIDI route exists, which FL instruments take channels 1 and 2?
   And does the page stay the clock (Route P), or does Python follow FL's clock (Route F, the FL lane's topology)?
6. **Calibration.** Will Daniel do a 20-second tap-along before rhythm talk? Without it, placement is reported as "not
   calibrated".
7. **Spectacle banners during a jam.** Does a Claude loop count as "looping" for the banner gate (the spectacle spec:
   zero banners while he loops)? Proposed: his riffs over a Claude loop stay eligible, and Claude's notes never score.
8. **The `jam` log kind.** The log lane adds it to `performance.validate_event`, and `performance.summarize` must skip
   it. That skip was not verified in this pass.


