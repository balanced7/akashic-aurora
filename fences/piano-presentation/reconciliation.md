# RECONCILIATION — piano-presentation

Conductor: Vandor. 2026-09-15.

**Inputs:**
- **Blind halves** in this folder:
  - Heimdall (systems and budget);
  - Navi (information design and pedagogy);
  - Sunshine (feeling and play), relayed from Bifrost because his worktree cannot write here;
  - Vandor (a look-development panel of four looks rendered on the real page, judged blind).
- **Asta** filed no half. His 06:24 request to Vandor carries his self-critique and a proposed but unbuilt `arsenal/ENVIRONMENT-PASS.md`, and is treated as his contribution.
- **Rill** filed no half by the deadline. His instruments (floors, storyboard, coupling) and their checked review (research/in-flight/rill-3d-tools-review-2026-09-14/) stand in for his lane, and the acceptance work below is his when he is back.

## What Daniel said during the round

**Answers to the four picks, verbatim:**
- **Look:** "Would it be too much to try 1-3?" The options were P luminous ink with grafts, R editorial theory, and S spectacle ladder. The sheet he chose from is `evidence/07-lookdev-choices-portrait.jpg`.
- **Colour:** "I'm leaning towards 1 but would like to see how 2 works". Option 1 is colour = the note on the light, with the chord job in the words; option 2 is colour = the chord job everywhere.
- **Hero:** "1 with 2 and 3 later so we can play with it". That is: name what I played now; show where it is going, and both, later.
- **Capture:** "Both". That is: 1440p60 live, and a 4K offline re-render.

**Relayed by Asta, verbatim:** "I feel like we are missing something fundamental." / "there is a reason synthesia and guitar hero look so good, make something to wow me please."

## The finding: the missing foundation is time with a point of contact

Synthesia and Guitar Hero share one grammar before any art:
- x is pitch, aligned to the keys;
- y is time, so a note is an object whose length is its duration;
- a hit line gives a flash at the exact frame of contact;
- the field keeps moving, so quiet playing stays alive and legible.

Our page has no temporal axis:
- Every strike spawns an ephemeral gesture above the keys, not aligned to its key and not ordered in time.
- History evaporates, and a still frame cannot show what was played two seconds ago.
- The harmony modes are diagrams floating in the sky.
- The contact is faint (pressed-key chroma about .06 against a floor of .12).

Eight harmony modes could not fix this, because they all describe *what is sounding now*.

**Convergence, reached blind:**
- Sunshine: "Notes rise in stable pitch lanes, but as memory rather than exhaust... Repeated notes create beads... Finger-held notes are solid, pedal-held notes hollow."
- Navi: the note that moved, drawn as a thread between chords.
- Vandor's panel: every judge punished hairline gestures, invisible repeats and a strobing heading.
- Asta's own unbuilt proposal: "key-aligned played-history ribbons".
- The 09-13 piano-ideas panel ranked **Upright Roll first of six**. A prototype exists, untracked: `arsenal/web/piano/schemes/upright-roll.js`.

**Ruling:** the stage is a **Rising Roll**. Played notes become bars rising from their keys, and their length is time. The worlds, fog and water are the backdrop, the harmony modes are an optional overlay, and the words ride on top.

## Accepted and declined, by seat

**Heimdall.**
- **Accepted:**
  - 1440p60 (Ultra) is the live delivery tier.
  - 4K is not a live capture tier; it is an offline re-render (Daniel: "Both").
  - H.264 via WebCodecs for every tier.
  - A recording pre-roll: prime renderer and encoder about 4 s, discard it, and bind acceptance on `skipped == 0`.
  - A sim `captureSimState` / `restoreSimState` seam, so pixel receipts work with the atmosphere on, scoped to this machine and driver.
  - The do-not-build list: no second render context, no parallel recorders, no 4K bloom at the full Cinema particle count, no cross-driver determinism claims.
  - Keep `dt` clamped at 1/30.
- **Note:** 60 fps at 1440p is measured at 48-54 today, so the roll must earn its frames. Its budget is part of acceptance.

**Navi.**
- **Accepted:**
  - The naming ladder: chord name, then Nashville, then key, then the note that moved, then suggestions.
  - "12 notes" is never a headline; the count appears only for a true cluster.
  - At most three rungs visible at once.
  - Names aggregate over a pedalled arpeggio.
  - The moved-note thread as a one-beat verb.
  - Teaching (next-chord whisper, ghost rims) only in Try or Hover.
- **Answered by Daniel:** name what I played is the hero; forward lean comes later, as toggles.
- **Extended:** in the roll, the chord name and Nashville number are *written at the chord's onset row* and rise with it, so the progression is a readable sentence. The pinned top zone shows the current chord.

**Sunshine.**
- **Accepted:**
  - The three depths (instrument, memory, meaning).
  - The state grammar: finger-held solid, pedal-held hollow rim, released breath, velocity as attack not permanent opacity, and a pedal lift closing rims on one line.
  - "A preset changes poetry, not truth."
  - Reward meaning not activity; no scores or red mistakes.
  - The phrase arc, quiet to curiosity to build to arrival to afterglow, with an arrival spent once or twice a minute.
  - Names settle after the sound.
  - The rolling clip buffer.
  - The P0 to P3 feature order, and "a beautiful lie about which notes sound is not beautiful."
- **Declined for v1:** his "no rarity grades." Daniel asked for "a rarity and fanciness scale", so S's rarity moment stays, but only as an opt-in Spectacle-look payoff, never a score.
- **His question** (feel versus understand) goes to Daniel after the first playable build, when he can answer it with the thing in front of him.

**Vandor's panel.**
- **Accepted:**
  - "One light, one word".
  - Note colour as the default, with a role-colour toggle, because Daniel wants to see option 2.
  - The three looks as **skins on the same roll**: Luminous (P), Poster (R) and Spectacle (S).
  - Grafts: R's lettering, S's momentum and opt-in rare moment, Q's note-lit mist.
  - The quick fixes (below).
  - The measurable floors.
- **Declined:** R's role colours on the light itself, as the default. It stays available because Daniel wants to see it.

**Asta.**
- **Accepted:** his diagnosis that the result "still feels plain and insufficiently compelling in motion," and the played-history ribbons idea.
- **Declined:** pairing the ribbons with a richer environment in the same pass. The environment waits until the roll is the stage.
- **Kept, but not as the stage:** his harmony modes (overlay), voice identity, momentum and water systems (they feed the roll's contact and backdrop), and conversation and replay.

## Presentation spec v1

**Layers (9:16, y from the top):**

| Band | Content |
|---|---|
| 0-7% | Nothing (platform chrome) |
| 7-24% | Meaning: current chord (hero) and Nashville number, key eyebrow; one secondary line at most |
| 24-70% | Memory: the Rising Roll, receding slightly in depth into fog and backdrop; chord names written at onset rows at the roll's edge; moved-note threads |
| 70-84% | Instrument: keys, the contact line, flashes |
| 84-100% | Reflection only, carrying no information |

In 16:9, a 36-key lens follows the hands (τ .7 s) and the meaning zone sits top-left. Nothing goes in the right rail of 9:16.

**The roll:**
- **Lanes:** one lane per key, and a bar starts within 1 px of the key top.
- **Scroll:** 180 px/s at 1080 wide, or the jam tempo while a loop runs.
- **State:** a finger-held bar grows with a solid core. A pedal-held bar is a hollow rim in the same hue, and a pedal lift closes the rims on one horizontal line. Released bars rise as history that thins and desaturates with height.
- **Repeats:** every strike starts a new bar with a gap, so beads, never restarts.
- **Contact:** on note-on, in the same rendered frame, the key depresses and glows in pitch colour, and a flash, short spark burst and lit mist puff appear, all scaled by velocity.

**Colour:**
- The default is the page's OKLCH pitch colour, the same on the key, bar, flash, mist and reflection. Velocity raises chroma and core brightness, never white.
- A toggle switches to role colour (root, 3rd, 5th, 7th, extensions) so Daniel can compare. In role mode, a held bar keeps the colour it was struck with, so nothing recolours when the chord moves under it.

**Words:**
- The settled chord name and a Nashville number with correct superscripts (4⁶ᐟ⁹, never "46/9").
- The chord reader built tonight (`chordread.js`, TN2 wiring with the shared speller) fixes names such as Gbmaj13#11 (today "Bbm11/Gb").
- 0 blank frames between repeats. Contrast ≥ 4.5:1.

**Looks (skins, selectable):**

| Look | Roll material | Backdrop | Words | Special |
|---|---|---|---|---|
| Luminous (P) | Glossy saturated bars, bloom hugging the source (threshold .88) | Moonlit lake as a dark silhouette, note-lit mist (from Q) | R's lettering, softened | none |
| Poster (R) | Flat bold bars | Black stage | Large type, formula line, progression row, role chips | none |
| Spectacle (S) | Pearl and silk bars with momentum on repeats | Lake | S's raised extensions | Opt-in rare-chord rose window and rarity word, spent at most once or twice a minute |

**The phrase arc (P1, Sunshine):** a bounded energy envelope from density, spread, velocity, bass motion, harmonic change and pedal. Arrival makes motion converge for 150-250 ms, the voicing briefly reads as one shape, colour warms, the name appears after the sound, and there is a 1-2 s afterglow. The camera never swoops.

## Feature set, in order

**P0, truth and the stage:**
- the Rising Roll with contact and state grammar;
- note colour, with the role toggle;
- the settled heading with correct Nashville superscripts;
- the three looks as skins;
- the quick fixes;
- the recording pre-roll with `skipped == 0`.

**P1, phrasing:** the moved-note threads, the energy envelope, arrival and afterglow, and the chord reader wired in with the shared speller.

**P2, play:** notice markers and replay, next-chord whisper and "both" hero modes as toggles (Daniel: "later so we can play with it"), the rolling clip buffer, and the offline 4K re-render (recorder frame-clock seam).

**P3, delight:** fingerprint callbacks, the Spectacle rare moment tuned by ear, and the richer environment (ENVIRONMENT-PASS terrain and foliage).

**Quick fixes** (from Vandor's slices, small, in Asta's modules):
1. `strands.frustumCulled = false`
2. A shared `formatNumber`, stop stripping '^'
3. `ctx.shownInfo()` as the settled heading for every view
4. The key loop composes on `k.glow` and `noteColor`
5. `noteColor` passed through ctx
6. Bloom targets and moon demotion
7. `__piano.three` and framing handles

## Acceptance

**Live-playing (the roll):**
- **Contact:** note-on to flash and key glow in the same frame (≤ 16.7 ms at 60 fps). The bar starts within 1 px of the key top.
- **Duration:** bar length equals held time × scroll speed, within 1 frame.
- **Repeats:** 6 × Eb4 in 2 s give 6 beads with gaps ≥ 4 px at 1080 wide.
- **Voicings:** Gbmaj13#11 (Gb2 Db3 F3 Ab3 Bb3 C4 Eb4) gives 7 separable bars with lane gaps ≥ 2 px at the 36-key lens. A stranger can name the keys from a still.
- **Soft versus hard (same hue):** flash area ≥ 3×, core luminance ≥ 1.6×, hard chroma ≥ soft chroma.
- **Sustain:** core versus rim is distinguishable at phone size through a dense pedalled arpeggio.

**Frame and words** (from Vandor's floors):
- frame median luma .05-.09;
- title p99 ÷ soft gesture p99 ≤ 1.6;
- pressed-key chroma ≥ .12 soft and ≥ .18 hard;
- label contrast ≥ 4.5:1;
- nothing below 30 px in 9:16.

**Budget and capture (Heimdall):**
- Ultra 1440p with 250 live bars and bloom: p95 frame ≤ 16.7 ms, one canvas.
- REC with pre-roll: `skipped == 0` and decoded frames = requested.
- With the snapshot/restore seam, the same MIDI and seed give identical frames with the atmosphere on.

**Instruments** (Rill's lane): a per-take `check_take`:
- no video stream is a FAIL;
- real frame rate from count ÷ duration;
- capture gaps over 3× median spacing;
- floors on the meaning band and the roll band;
- a slit-scan strip through the roll for repeat continuity.

**By eye:**
- the Synthesia test (read the last 3 s of playing from a still);
- the Guitar Hero test (every strike feels like it hit something);
- Sunshine's glance, squint and mute tests;
- Daniel keeps playing instead of managing the view.

## Slices and seats

| # | Slice | Seat | Depends on |
|---|---|---|---|
| 1 | `piano/roll.js`, the Rising Roll: lanes, bars, state grammar, beads, contact, note colour. Built from `schemes/upright-roll.js` prior art, mounted by spectacle behind a setting so it can be A/B'd live | **Asta** | Integration commit |
| 2 | The quick fixes (1-7 above) | **Asta** | Integration commit |
| 3 | `piano/typeset.js`: settled hero chord, Nashville superscripts, onset-row names in the roll, key eyebrow, safe zones | **Vandor** | Slice 1 interface |
| 4 | Three looks as skin presets (Luminous, Poster, Spectacle), plus the colour toggle | **Asta**, Vandor reviews | 1, 3 |
| 5 | Recording pre-roll plus `skipped == 0` receipt; the snapshot/restore seam design and pins | **Heimdall** drafts and pins (read-only exec); Asta or Vandor applies | Integration commit |
| 6 | `check_take` and floors on roll and meaning bands; fixes from the tool review | **Rill** | 1 |
| 7 | Hierarchy and wording review; moved-note thread spec | **Navi** | 3 |
| 8 | Feel review on the first playable build; arrival and afterglow design (P1) | **Sunshine** | 1, 3, 4 |
| 9 | TN2: chord reader plus shared speller wired into the page | **Vandor** | Integration commit |
| 10 | Offline 4K re-render: recorder frame-clock seam | **Asta** with Vandor | 5 |

**Order:** the integration commit, then slices 1, 2, 5 and 9 in parallel, then 3 and 6, then 4, then 7 and 8 on the first playable build. Daniel tries the three looks on a live page before anyone polishes one.
