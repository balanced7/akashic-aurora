# /piano presentation: Vandor's blind half

All four looks and the baseline were rendered from the same served bytes: piano.js 84bc05c6, spectacle.js 89b9aa2a and moonwater.js 00e5f656. Every frame is Studio 1080p on the moon theme. This half is review and prototype only; no tracked file was edited. Besides reading the metrics, I looked at the P, Q, R and S frames myself.

## 1. Diagnosis

1. **The music is not the brightest thing on screen.** The moon and the title outshine soft playing about 3x, and the scenery shares the same teal value as the light.
2. **Loud goes whiter instead of more colourful, and soft is 1-2 px hairlines.** Moonwater also repaints every key pastel, which erases the sustain × velocity glow that piano.js already computes.
3. **The words lie or blink.** "4^6/9" prints as "46/9". The headings read what is sounding right now, so they blank between repeats. Daniel's Gbmaj13#11 is named Bbm11/Gb.
4. **The 9:16 frame is wasted.** The bottom 18% is dead reflection, hard reeds run into the subline, and left-hand voicings lose their reeds to a frustum-culling bug.
5. **Moonwater and the harmony views are two design systems.** They use four unrelated palettes, and nothing ties a key to its light and its word.

## 2. Recommendation: Look P as the stage, with grafts

**Why P.** The judges split on the winner: S won on Daniel's words, and R won as an editor and as a practice tool. All three judges put P second. P is the only look that no lens rejects, and it is the most product-shaped: it reuses the page's own OKLCH palette and key glow model instead of inventing new ones.
- R is the best information layer, but it is not a stage.
- S has the best payoff moment, but not an everyday frame.
- Q is a tasteful grade that loses hue identity: its hard frames go pink.

**Thesis: one light, one word.**
- **One light.** The note's own colour is the only saturated light in the frame, the same on the key, reed, lamp, mist and reflection. Playing louder buys width, height and bloom in that hue, never white. Finger plus sustain is the brightest state.
- **One word.** The text sits above the light and never lies or blinks. Theory roles live in the type.

**Grafts**
- **From R:** the type layer (key eyebrow, heavy hero chord with the bass tinted, formula line, progression row, PEDAL pill, dashed pedal-only states), the settled heading, the caption and right-rail safe zones, and the 36-key follow lens for 16:9.
- **From S:**
  - raised Nashville extensions;
  - strike momentum, so repeated notes grow the reed rather than restart it;
  - rarity pips;
  - the budgeted rose window, as an opt-in payoff repainted in P's pitch palette. At the moment it reads pastel and dreamcatcher-like.
- **From Q:** note-lit local mist, a dark reflection pool, the reed cap under the heading, and the lens lift.
- **Keep from P:** the per-strike bead and foot flare, bloom that hugs its sources, and the culling fix.

**Two things I would not graft.**
- **R's role colours on keys and columns.** In the lament walk, when the bass reaches F under the held Ab voicing, Fm7 recolours the held Ab from root vermilion to ♭3 amber and the held Eb from jade to cobalt. That is Daniel's "visibly restarts" complaint moved from motion into colour. Role colour belongs on the numerals in the type; pitch colour belongs on the light.
- **R's type scale before the detector is fixed.** R sets Bbm11/Gb at 340 px and labels Daniel's Gb bass "♭13". Louder type makes detector errors louder, so the detector fix moves up the queue.

## 3. Parameters and implementation slices

v = velocity/127. g is the piano.js key glow.

| Area | Value | From |
|---|---|---|
| Pigment | `ctx.noteColor` (OKLCH); chroma ×(1+.30v); gain (.92+.55v)·heldGain. heldGain: held+pedal 1.18, held 1.00, pedal-only .82, τ .12 s | P |
| Saturation slope | If hard ≥ soft fails the floor, steepen chroma across v, e.g. .60→1.0 | S |
| Reed width (world units) | 9:16: .95+1.10v²; 16:9: 1.60+1.50v² | P |
| Reed height | Soft floor 6.5 world units, hard about 4× soft; momentum h·(1+.45m), w·(1+.5m), τ 1.4 s, cap 1.5 | S |
| Reed cap | NDC .38 in 9:16 (below a compact heading); .70 in 16:9 | Q/S, retuned |
| Strike accent | Bead e^(−1.8s), foot flare e^(−5s); lamp flare at most once per 150 ms per voice | P + rate cap |
| Bloom | Threshold .88; strength .48+.30·force; radius .18; mip factors [1, .8, .5, .22, .07] | P |
| Moon | Disc ×.60, halo ×.45; must stay below the bloom threshold | P/Q |
| Scenery | Q's aerial perspective: rock ×(.18+moon·.46), haze .0042, max .86. P's silhouette is the fallback | Q |
| Mist | Lamp falloff w/(1.2+d²·.10); alpha ×(.70+.42·min(\|lit\|², 2.5)) | P+Q |
| Keys | From k.glow: tint min(1, 2.5g). Whites #cfcdc4 → pigment by .95·tint. Emissive: white .06·tint+.55g², black .10·tint+.90g². Skip cue and ghost keys | P |
| Camera 9:16 | Lens shift −.22·h | Q/S |
| Camera 16:9 | 36-white-key span, follow τ .7 s, widen when the hands exceed it | R |
| Heading | First chord shown immediately at full brightness; changes settle 80 ms; hold 4.5 s; practice mode dims it 25% after 2 s | R + judges |
| Type (9:16) | Hero root cap height ≥ 180 px at weight ≥ 500; secondary text ≥ 44 px; nothing under 30 px | R/S |
| Rarity and vault | Pips and word ≥ 44 px. S's gate. Budget floor 0 instead of .30, so there is no "sticky cathedral" | S |

Slices are ordered cheapest-high-impact first. S = small, M = medium, L = large.

| # | File(s) | Change | Size |
|---|---|---|---|
| 1 | moonwater.js | `strands.frustumCulled=false` | S |
| 2 | piano.js → moonwater.js, harmony-renderer.js | Shared `formatNumber` (degreeRuns); stop stripping '^' | S |
| 3 | piano.js, moonwater.js, harmony-renderer.js | `ctx.shownInfo()` settled label read by every heading | S |
| 4 | moonwater.js | Key loop composes on k.glow and noteColor; keep the cue/ghost skip | S |
| 5 | piano.js, moonwater.js | Pass noteColor into ctx; reeds, lamps and point lights use it | S |
| 6 | moonwater.js, piano.js, spectacle.js | Bloom targets and mip factors, moon demotion, save/restore on theme exit | S |
| 7 | piano.js, spectacle.js | `__piano.three`, `__piano.framing.patch`, lens shift, reed cap via uNoteBounds.z | S |
| 8 | piano.js THEORY | Prefer the bass-root reading within a cost margin (Gbmaj13#11); node tests | M |
| 9 | harmonic-voices.js, moonwater.js | lastAttack, held and momentum per voice; reed shader with width floor, bead and foot | M |
| 10 | moonwater.js | Scenery, mist and water constants moved to `style` uniforms | M |
| 11 | new piano/typeset.js | Hero, formula, progression and PEDAL pill, composited after bloom and redrawn only on change; retire the HUD title | M |
| 12 | harmony-renderer.js | noteColor palette, face emission by v², no per-frame full-canvas upload | M |
| 13 | spectacle-motion.js, moonwater.js | `state.ladder` (rarity, vault budget); rose window in pitch colour; opt-in | L |

## 4. Information hierarchy

**Practice, at the keys (usually 16:9):**
1. Keys: which note, how hard, and whether it is sustained.
2. Chord name and Nashville number, settled, then dimmed.
3. Formula line (role-coloured degrees).
4. Progression row (the last three chords).
5. Reeds, for voice continuity and dynamics.
6. Scenery, recessed. The rarity word and the vault are off.

**TikTok, 9:16 bands:**

| Band (y) | Content |
|---|---|
| 0-7% | Nothing (top bar) |
| 7-30% | Hero chord, then the Nashville progression row (1 → 1maj7/7 → **1⁷/♭7**); rarity pips only when earned |
| 30-68% | Light: reeds, mist, and the rose window when earned |
| 68-81% | Keys |
| 81-100% | Reflection only; it is under the caption, so it carries no information |
| x > 860 px | No text and no chips (right rail) |

## 5. Acceptance

| Measure (9:16 unless noted) | Floor | Baseline | Best measured |
|---|---|---|---|
| Frame median luma | .05-.09 | .09-.13 | P .047, Q .081 |
| Title p99 ÷ soft gesture p99 | ≤ 1.6 | ~3.5 | S 1.5, P 1.6 |
| Soft gesture lit fraction (30-70% band) | ≥ .03 | .0095 | Q .029 |
| Hard gesture lit fraction | .20-.55 | .24 | P .31, Q .55 |
| Hard ÷ soft lit area | 3-10× | 7-25× (Tonnetz 1.3-2.1×) | – |
| Hard ÷ soft reed height / width | ≥ 2.5× / ≥ 1.8× | – | S ~4× / ~3× |
| Lit-pixel saturation | Soft ≥ .30; hard ≥ soft in ≥ 7/8 fixtures, both orientations | 0/8 | S 8/8; P holds (3/8) |
| Pressed-key chroma, soft / hard | ≥ .12 / ≥ .18 | .057 / .066 | P .136 / .199 |
| Label contrast | ≥ 4.5:1 against the p95 background in the glyph box; octave digits ≥ 18 px | about 40 px subline in #a0b8b1; 10 px octave digits | – |
| Reed pixels above .2 luma inside the heading box | 0 | Fails | P fails |
| Repeat continuity (6× Eb4) | Heading non-blank in m0-m5 and the 2.0 s still; reed x and hue constant; lit area ≥ 80% of the first strike; each strike gives a p99.9 step ≥ .05 within 100 ms | Heading blank m3-m5; steps .002-.011 | R, S hold the heading |
| Flicker (10 Hz trill) | Frame mean luma swing < 10% | – | – |
| Performance | Ultra p95 composer ≤ 12 ms on the RX 9070 XT, heading included | – | S 11.8 ms (vault) |
| Gbmaj13#11 fixture | Titled with root Gb | Bbm11/Gb | – |
| Cue and ghost keys | Unchanged in the jam fixture | – | All looks break them |

**By eye**
- With sustain down, the held key is visibly the brightest.
- Soft and hard are distinguishable from across the room.
- A soft Db6/9 is a complete picture on a phone at arm's length.
- Eb is the same colour on the key, reed, lamp and reflection, in Moonwater and in Tonnetz.
- Six Eb4 strikes read as six strikes, not as one held note, and nothing restarts.
- A rare chord gets a "whoa" without hiding the voicing.
- Daniel plays for 20 minutes and is not tired.

## 6. Frames for Daniel, side by side

Root `L` = `C:/Users/L5/AppData/Local/Temp/claude/E--/bee0f118-f0f5-4b8a-a0d8-66aee48f3df1/scratchpad/lookdev`. The three frames are the same fixtures for every look: quiet, hard, and dense.

| Look | Quiet | Hard | Dense |
|---|---|---|---|
| Baseline | `L/baseline/moonwater/portrait/db69-v38.jpg` | `…/db69-v112.jpg` | `…/gbmaj13s11-v112.jpg` |
| Look P | `L/looks/A/frames/atmosphere/portrait/db69-v38.jpg` | `…/db69-v112.jpg` | `…/gbmaj13s11-v112.jpg` |
| Look Q | `L/looks/B/final/portrait/db69-v38.jpg` | `…/db69-v112.jpg` | `…/gbmaj13s11-v112.jpg` |
| Look R | `L/looks/C/final/portrait/db69-v38.jpg` | `…/db69-v112.jpg` | `…/gbmaj13s11-v112.jpg` |
| Look S | `L/looks/D/it3/atmosphere/portrait/db69-v38.jpg` | `…/db69-v112.jpg` | `…/gbmaj13s11-v112.jpg` |

An optional fourth frame, `repeat-m3-v112.jpg` in the same directories, shows the heading strobe or the fix for it.

## 7. Questions for Daniel

1. Should colour mean the **note** (Eb is always yellow, and held notes never change) or its **job in the chord** (the root is always red, which reads with the sound off)? I recommend the note on the light and the job in the words.
2. How much of the moonlit lake do you want to keep: dark silhouettes (P), a graded valley (Q), or a black stage (R)?
3. Should the rare-chord rose window and the "EXQUISITE" word be for TikTok only, or also on while you practise?
