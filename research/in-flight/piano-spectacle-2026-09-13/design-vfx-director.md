# The spectacle, directed: rarity tiers for the piano, as a VFX director

Status: design plus a working prototype, 2026-09-13 night. One of three independent designs. I did not read the other two.
Scene: `arsenal/web/piano.js` at HEAD `a886a0af` (three.js r186).
Lab copy: `arsenal/web/piano-lab-vfx.{js,html}`, served at http://127.0.0.1:8793/web/piano-lab-vfx.html.

Daniel, verbatim, tonight: "Can you reload the piano page and make it be perfectly un-aliased, can we make it even more a visual spectacle? Perhaps even having a rarity and fanciness scale xD", then "Lets make the resolution be adaptive to the render window". Rules from earlier tonight still hold. The sustain brightness rule: "brighest when I am pressing sustain and note at same time, velocity should be a factor as well". The bloom must decay instead of stacking (the LIGHT envelope and light budget, PIANO-V2-SPEC section 2).

---

## 0. In one screen

- **Five tiers:** Common, Uncommon, Rare, Epic, Legendary. Each tier is a stack of stage effects. Every tier keeps everything below it and adds more.
- **Tier shows as scale, motion and count, never as a new colour.** Every effect is painted in the chord's own pitch colours. **Gold is the one exception, and it means Legendary and nothing else.**
- **Effects use the three parts of the frame that nothing uses today:**
  - the empty floor below the keys (the bottom ~17% of the 9:16 frame)
  - the gold rail line
  - the dark back of the stage behind the columns
- **The column sky and the text band get the least.**
- **Light comes from a budget, not on top of it.** Epic and Legendary dim the old columns while they play (the house lights), so the spectacle adds contrast, not mean luma.
- **Prototyped and measured headless** on the RX 9070 XT at 1080x1920 (MSAA 4, HalfFloat, UnrealBloom). I built Rare and Legendary, plus the rail pulse, ember lift, light shafts and camera push, which Epic reuses.
  - Frame cost with a Legendary live: **1.38-1.47 ms** per GPU-synced frame, against 1.17-1.87 ms idle. The effects cost less than the bench's noise, about 0.2 ms.
  - The first round had four visible defects, and I fixed all four; section 8 has the snapshots.
- **Rarity is earned from the music and rationed.** The scorer (section 5) adds points for:
  - colour (extensions), mass (notes struck together), span
  - accent (velocity against the last 20 s)
  - pedal, borrowed chords and novelty
  - an **arc**: a crescendo of block strikes

  Gates and tokens keep the rare tiers rare. On 70 s of authored pedalled music, v3 fired 24 Common, 9 Uncommon, 3 Rare, 2 Epic and **exactly one Legendary, on the climax chord**. It is tuned on my own test music, so it must be recalibrated on Daniel's practice logs.

---

## 1. Directing principles (the rules every effect below obeys)

1. **Contrast is the spectacle; light is a budget.**
   - A tier spends light where it takes some away. Epic and Legendary multiply the light-budget density target by 0.85 and 0.65. The existing damping gives a theatre dim (fast, 0.05 s) and return (slow, 1.5 s).
   - Old columns dim. Fresh strikes, held keys and column feet keep full price, exactly as the LIGHT model already rules.
2. **Use the empty stage first.** Floor, rail and back wall are free. The sky between the rail and the staff is shared with the columns. The chord name and staff are protected.
3. **Colour belongs to the chord.**
   - Every effect takes the chord's pitch colours, ordered low to high. Rings wheel them around, the rail maps them along the chord's own key span, and the shafts take one per beam.
   - Tier is carried by scale, motion and count. Gold is reserved for Legendary; a colour that marks a tier must mean one thing.
4. **Only crests cross the bloom threshold (0.9 linear).**
   - Bodies stay under it: ring body ×0.32, shafts ×0.55 of palette, aurora ×0.3.
   - Thin crests, spark cores and the rail's hot core may bloom. This is spec 6.2's "only attacks may cross the bloom threshold".
5. **Protect by shape, not by stencil.** A rectangular mask was visible as a dark box in round 1 (section 8). The protect mask is now a super-ellipse with a 6-9% feather:
   - about 12% effect light at the heart of the chord name
   - 45% inside the staff
   - 100% elsewhere
6. **Everything is a function of the clock.**
   - No frame counts, so a 60 fps recording shows the same effect at any display refresh.
   - Snapshots are reproducible, and a skipped frame skips nothing.
7. **Nothing thin enough to alias.**
   - Ring widths are clamped to at least 2·fwidth, with energy kept (w/we).
   - Beam widths add fwidth of the angle. Points are clamped to at least 2.5 px, with alpha scaled by the covered area.
   - Twinkle is under 2 Hz, never per frame.
   - This is what "perfectly un-aliased" asks of an effect, and it survives an adaptive render scale.
8. **Effects scale with what they touch.**
   - The shimmer's gain is `min(1, 8 / live columns under the chord)` × the stretch's own energy.
   - A 40-column wash made a white bar in round 1 and does not now.
9. **Never:** a full-screen flash, screen shake, a camera move that crops a sounding key, anything over the key fronts, effect light over the chord name, a strobe (section 9 has the full list).
10. **Rarity is part of the effect.** A Legendary every 20 seconds is a Common with a gold hat. The scorer and its token governor are designed with the same care as the shaders.

---

## 2. The tier ladder

The Trigger column is a summary; section 5 has the exact rules. "Measured on test music" is v3 over 70 s of my authored music, 55 s of which are active play.

| Tier | Trigger | What happens on screen | Duration | Target frequency | Measured on test music |
|---|---|---|---|---|---|
| **Common** | any settled chord-name change (the label pop) | one pair of colour fronts runs out along the rail from under the chord | 0.6-1.0 s visible | every chord change, ~10-30/min | 24 in 70 s |
| **Uncommon** | score ≥ 2.5: an extended chord, a wide span or an accent | two rail fronts (echo +0.12 s), an ember lift of 90 ballistic sparks from the chord's keys | ~1.9 s | ~3-6/min | 9 |
| **Rare** | score ≥ 4.5, ≥ 3 notes struck within 80 ms, and a Rare token (cap 3, refill 10 s) | + floor shockwave ring; spark fountain (300); a shimmer band rides up the chord's columns; **RARE** banner | ~2.0 s (banner 1.9 s) | ~1-3/min | 3 |
| **Epic** | score ≥ 6, ≥ 4 struck, accent ≥ +12 over the 20 s mean, and an Epic token (cap 2, refill 45 s) | + second, wider ring (+0.18 s); a fan of 7 light shafts; 2.5% camera push; house lights −15%; fountain 520; **EPIC** banner | ~3.3 s | ≤ 1/min | 2 |
| **Legendary** | score ≥ 8, ≥ 5 struck, accent ≥ +22 or velocity ≥ 112, and the Legendary token (cap 1, refill 180 s, none before ~45 s). In practice an **arc** (a crescendo of block strikes) or a borrowed fortissimo | **gold**: three rings (the third thin gold), gold rail held 1.7 s, gold and palette fountain (900), gold shafts, aurora ribbon with a gold hem, dispersion shimmer, **chord name in gold foil** with a sheen sweep, camera push 5.5% with +1.1° elevation and +1.3° yaw, house lights −35%, **LEGENDARY** banner | ~5.2 s | ≤ 1 per ~3 min; 0-1 per 60 s TikTok | 1 (on the climax) |

---

## 3. The effects catalogue

Compositing summary (the "before bloom" passes are inside `EffectComposer`, the "after" ones are in the overlay scene):

| Effect | Tier | Object | Blend | Pass | Depth test | Draw calls |
|---|---|---|---|---|---|---|
| E1 Rail pulse | 0+ | 58×1.4 quad at the rail (z −3.26) | additive | main, before bloom | yes | 1 |
| E2 Ember lift | 1 | fountain Points system | additive | main, before bloom | yes | shared with E4 |
| E3 Floor shockwave | 2+ | 260×260 plane on the floor (y −2.27) | additive | main, before bloom | yes (the piano occludes it) | 1 |
| E4 Spark fountain | 2+ | Points, 2000 cap | additive | main, before bloom | yes | 1 |
| E5 Column shimmer | 2+ | inside the trail shader | additive (as the trails) | main, before bloom | as the trails | 0 |
| E6 Tier banner | 2+ | Canvas2D layer, 760×100 | alpha | overlay, after OutputPass | no | 1 |
| E7 Light shafts | 3+ | 70×40 quad behind the columns (z −4.12) | additive | main, before bloom | yes | 1 |
| E8 Camera push | 3+ | camera distance, elevation and yaw offsets | n/a | n/a | n/a | 0 |
| E9 House lights | 3+ | multiplies the light-budget density target | n/a | n/a | n/a | 0 |
| E10 Aurora ribbon | 4 | 150×60 plane far behind (z −30) | additive | main, before bloom | yes (the floor hides its foot) | 1 |
| E11 Gold foil name | 4 | mesh sampling the label's own texture | alpha | overlay, after OutputPass | no | 1 |
| E12 Gold rail, dispersion fringe | 4 | uniforms of E1 and E5 | as the host | as the host | as the host | 0 |

Every effect mesh is `visible = false` except while it can be lit, so an idle frame pays nothing. At peak a Legendary adds 5 scene draw calls and 2 overlay draws.

### E1 Rail pulse (Common and up)
- **What:** fronts of the chord's colours run outward along the gold rail line from under the chord's centre. It is the heartbeat on every chord change.
- **Geometry and shader:**
  - six pulse slots `(cx, t0, speed, gain)`
  - speed 36-44 world units/s
  - head a gaussian with σ ≈ 0.42 u, wake 18% of the head, decay τ 0.55 s, life ≤ 1.8 s
  - vertical profile: a thin core (σ 0.042 u) plus a 22% halo (e^−6|dy|)
  - colour maps the palette along the chord's x span, so each stretch of rail is lit in the colour of the key below it
- **Gains by tier:** Common 0.45 (one pair), Uncommon 0.8 plus an echo, Rare 1.0, Epic 1.1, Legendary 1.25 plus a third echo at +0.26 s, plus the gold rail (E12).
- **Bloom:** the thin core crosses the threshold at gain ≥ 1, so the rail sparkles; the halo does not.
- **Cost:** about 1% of the frame's pixels × a 6-slot loop, well under 0.02 ms.
- **Never:** runs past the keyboard ends (smoothstep at |x| 25.6-26.6); lights the key tops.

### E2 Ember lift (Uncommon)
- 90 sparks from the E4 system, split across the chord's notes.
- Up speed 1.8-4 u/s; life 1.0-1.9 s; they rise a finger's width and fall back.
- A hint that something is gathering, never a burst.

### E3 Floor shockwave (Rare and up)
- **What:** a ring expands on the stage floor from under the chord.
  - Its front arc sweeps the empty floor band below the keys.
  - About 0.5 s later its back arc rises out from behind the rail, behind the column feet.
  - The piano body occludes the middle, through the depth test.
  - This is the effect that says "3D stage" best (round-1 snapshot `rare-2-+0.6s`).
- **Math:**
  - radius `R·(1 − e^(−age/0.5))`, fast out and slowing, like a shockwave, not a ripple
  - width `w₀·(0.35 + 1.2·age/dur)`, widening as it spends itself
  - a sharp outer front (gaussian at 0.3·w), an exponential inner wake, a hot crest line
  - life `(1 − age/dur)²`
- **Rings by tier:**

  | Ring | When | R (u) | Duration | w₀ | Gain | Colour |
  |---|---|---|---|---|---|---|
  | 1 | Rare+, at t0 | 26 | 1.7 s | 0.55 | 1.0 (1.35 Legendary) | palette; gold on Legendary |
  | 2 | Epic+, t0 + 0.18 s | 32 | 1.9 s | 0.8 | 0.7 | palette |
  | 3 | Legendary, t0 + 0.36 s | 38 | 2.2 s | 0.35 | 0.6 | thin gold |

- **Colour:** the chord's palette wheels around the ring angle (twice around, drifting at 1.5 steps/s); gold on Legendary.
- **Anti-aliasing:** `we = max(w, 2·fwidth(d))`, with the body scaled by `w/we`, so a far ring thinner than a pixel is widened with its energy kept.
- **Fog:** the ShaderMaterial has no scene fog, so it fades by camera distance from 55 to 130 u.
- **Cost:** covers ~25-30% of the frame only while alive; a 4-slot loop, estimated at 0.05-0.1 ms.
- **Never:** draws on the keys (it is a floor plane under a depth test); flashes the floor (the crest is a line, the body is ×0.32).

### E4 Spark fountain (Rare and up)
- **What:** ballistic sparks from the chord's key backs: up, drag, falling back under gravity (8.4 u/s²).
  - This is a separate system from the core's rising embers, so the two read as different events.
- **Counts:** Rare 300 over 0.35 s; Epic 520; Legendary 900 over 0.55 s, 55% gold.
- **Up speed:** 9 / 10 / 11 u/s × (0.45-1.0). Life 1.0-2.3 s; size 0.14-0.40 world units.
- **Anti-aliasing and flicker:** point size ≥ 2.5 px with alpha × (natural px² / 6.25), so no sub-pixel flicker. Twinkle 1.75 Hz; the centre goes white-hot.
- **Where:** spawns at z −3.22, behind the key backs, so a spark can fall onto the keys but never covers a key front.
- **Cost:** 900 small points at the column feet (overdraw concentrated there), included in the bench. CPU: one 104 KB attribute upload per trigger. Production should use `updateRanges`.
- **Honest read:** at the follow camera's closest span these read as glitter plumes 100-200 px tall at the column feet, not a tall fountain. Taller would enter the staff; in 9:16 that is the right trade.

### E5 Column shimmer (Rare and up)
- **What:** a band of light rides up the chord's columns at 3.2× the trail speed (~21 u/s). The light moves faster than the column, so each column looks charged by the strike.
  - This is my "slow-motion shimmer", inverted: the columns keep their speed, the light races.
- **Band:** σ 0.8 u growing +0.5 u/s. Colour: the column's own, lifted 15% toward white.
- **Legendary:**
  - a second band 0.45 s behind
  - a gold tint
  - a **dispersion fringe**: red leading, blue trailing, like light through a prism, and still two thin gaussians
- **Budget:** gain = stretch energy × 1.6 (clamped to 1) × `min(1, 8/columns under the chord)`. A dimmed old stretch shimmers dimly; a 40-column wash thins out.
- **Cost:** a 2-iteration loop in the trail fragment shader behind a uniform branch, only while active (≤ 2.6 s).

### E6 Tier banner (Rare and up)
- **What:** the tier word in letter-spaced caps (Archivo 700, 36 px, tracking 0.42 em), hairline rules fading outward, and one gem per tier step under the word.
- **Where:**
  - 9:16: y 490-590, between the note-chip line and the staff top. That is inside TikTok's safe band: below the top tabs, left of the right-rail icons.
  - 16:9: under the chord name at (500, 400).
- **Ink:**
  - Rare #79b8ff, Epic #c79bff, Legendary #ffc766
  - tier ink appears only on the 3 px rules and the 5 px gems, because blue and violet are also pitch colours
  - the word stays warm ivory, except Legendary's gold gradient
- **Timing:** in 0.14 s (scale-x 0.94→1.0 over 0.35 s); hold 1.2 s (Rare), 1.8 s (Epic), 2.8 s (Legendary); out 0.6 s.
- **Compositing:** overlay scene after OutputPass with alpha, so it is crisp and never blooms. The canvas is drawn once per trigger.

### E7 Light shafts (Epic and up)
- **What:** a fan of seven beams from the rail under the chord, behind the columns (z = TRAIL_Z − 0.7).
  - The fan spans ±0.51 rad with slow sway at incommensurate phases.
  - The beams shoot up with a front at 42 u/s.
- **Shader:**
  - one quad, 7 angular gaussians with width 0.03-0.06 rad plus 0.7·fwidth(angle)
  - radial falloff e^(−r/15), faded in from r 0.4-2.2 so the origin is not a hot spot
  - moving motes (0.8-1.0)
  - envelope in 0.3 s, hold to 1.7 s, out by 3.3 s
- **Colour:** one palette colour per beam. Legendary: the centre beam gold, the others 55% gold.
- **Gain:** Epic 0.9, Legendary 1.2. The body peaks around 0.2-0.3 linear.
- **Cost:** the quad covers ~35% of the frame; a 7-loop, estimated at 0.1-0.2 ms.
- **Honest read:** this is the most "theatrical" element, and it reads cleanly in every snapshot.

### E8 Camera push (Epic, Legendary)
- **Mechanism:** multiplies the follow camera's distance by `(1 − push)` and adds elevation and yaw on top of its slow drift.

  | Tier | Push | Elevation | Yaw | Rise | Hold | Return |
  |---|---|---|---|---|---|---|
  | Epic | 2.5% | +0.008 rad | 0 | 0.8 s | 0.4 s | 1.8 s |
  | Legendary | 5.5% | +0.02 rad (+1.1°) | +0.022 rad (+1.3°) | 1.0 s | 0.8 s | 2.4 s (smoothstep) |

- **Never:** shake, cut, or crop the chord's keys. The follow frame is span + 6 u, and 5.5% leaves about 3 u of margin at span 16.
- **Production:** scale the push by framing (16:9 is the full keyboard and shows the cheeks at the edges), and skip the push while the follow camera is panning faster than 1.5 u/s.

### E9 House lights (Epic, Legendary)
- **Mechanism:** `densityTarget *= fxState.dim`. dim = 1 − 0.15·bump(Epic) − 0.35·bump(Legendary: rise 0.25 s, hold 2.2 s, fall 1.2 s).
- **Effect:** the existing budget damping dims fast and recovers slowly. Only old light dims: fresh strikes, held notes and feet keep full price.
- **Where the spectacle's light comes from:**
  - the share of near-white pixels **fell** from 0.0084 to 0.0013-0.0054 during a Legendary
  - mean luma rose at most +0.06 (section 6)

### E10 Aurora ribbon (Legendary)
- **What:** a curtain far behind the stage (z −30) whose hem waves just above the rail.
  - The hem is three incommensurate sines: spatial 0.09 / 0.23 / 0.57, temporal 0.31 / 0.53 / 0.97.
  - The fold is cubed into ray-like stripes, and there is a gold hem line.
- **Curtain:** decays up as e^(−h/4.5). v1 used /10, which bloomed into a sky of out-of-focus colour.
- **Colour:** gold-leaning palette at the hem, the chord's upper palette above.
- **Envelope:** in 0.9 s, hold to 3.2 s, out by 5.2 s.
- **Cost:** the largest quad (~60% of the frame while visible), estimated at 0.2-0.3 ms.
- **Honest read:** the gold hem reads as a golden wave behind the columns, and in 16:9 it is the best single element of the set. The haze above it is the weakest part of the design: soft, low-contrast colour at the top of the frame. If Daniel doesn't love it, cut to hem-only.

### E11 Gold foil chord name (Legendary)
- **What:** an overlay mesh at the chord label's position and scale that samples the label's own canvas texture.
  - Glyph cores only: alpha ≥ 0.78, main line only (uv above the note chips).
  - It paints a vertical foil gradient: pale gold (1.0, 0.93, 0.70) at the letter tops, amber (0.93, 0.60, 0.20) at the feet.
  - A diagonal sheen sweeps left to right from 0.2 to 1.2 s.
- **Timing:** in 0.18 s, hold 2.9 s, out 0.8 s.
- **Compositing:** alpha after OutputPass, so the name never blooms, never grows and is never redrawn. It changes the ink, not the shape.
- **Readability:** the foil keeps well over 10:1 contrast on the dark scrim. All eight Legendary snapshots read clearly.

### E12 Gold rail and dispersion shimmer (Legendary)
- The rail line holds gold at 0.9 for 1.7 s and fades over 1.4 s, with the pulse heads riding over it.
- The dispersion fringe is described under E5.

### Designed, not prototyped
- **E13 Key-front glint (Uncommon and up):** a 0.25 s specular sweep across the chord's lit key fronts: a band in x on the key emissive, or a thin additive quad on the front faces. Trivial cost; ties the effect to the fingers.
- **E14 "Held breath" time dilation (Legendary option):**
  - Warp the trail clock: speed 0.35 for 0.8 s, then 2.04 for 0.5 s. Net lag is zero and the clock stays monotonic, so the columns hang, then surge.
  - Every trail time must be stamped in the warped clock (aT0/aT1/aT2 and the pedal ring index); keys and sparks stay real-time.
  - Build it only after the Neon Trails scheme extraction lands, because it touches the core of the LIGHT model's time base.
- **E15 Staff note pulse (Rare and up):** the chord's noteheads get a 0.4 s ring in the staff canvas (redraw at 30 Hz only during the pulse). Readable by construction.
- **E16 Mythic (secret sixth):** off by default, summoned from a KeyLab pad for a staged TikTok moment. Legendary, plus a ring palette cycling through the chord's own hues only, plus E14.

---

## 4. Timelines

**Rare (t = trigger, i.e. the settled chord name)**
```
0.00  rail fronts x2 (the second at +0.12)     ring 1 starts (R 26, 1.7 s)     fountain emits over 0.35 s
0.03  shimmer band leaves the rail (3.2x trail speed)
0.05  RARE banner in (0.14 s)
0.25  ring front arc crossing the floor band        sparks at apex
0.60  ring back arc rises behind the rail            shimmer reaches the staff (45% there)
1.00  sparks falling onto the rail                   ring fading (life^2)
1.39  banner out (0.6 s)
1.70  ring gone     2.0  sparks gone     2.6  shimmer gone
```

**Legendary**
```
0.00  gold rail on (0.1 s); rail fronts x3 (+0.12, +0.26); ring 1 gold (1.35); fountain 900 over 0.55 s (55% gold)
      house lights begin to dim (0.25 s to -35%); camera push begins (1.0 s ease)
0.03  gold shimmer band (+ second band at 0.48); dispersion fringe
0.05  shafts shoot up at 42 u/s (gold centre); LEGENDARY banner in
0.10  foil in on the chord name (0.18 s); aurora begins to fade in (0.9 s)
0.18  ring 2 (palette, R 32)      0.20-1.20  foil sheen sweeps left to right
0.36  ring 3 (thin gold, R 38)
1.00  camera at full push (5.5%, +1.1 deg elev, +1.3 deg yaw), holds 0.8 s
1.70  shafts start to fade (out by 3.3)       1.80  gold rail starts to fade (1.4 s)
2.47  house lights start to recover (1.2 s fall, then the budget's own 1.5 s recovery)
2.95  banner out      3.18  foil out (0.8 s)      3.20  aurora out (by 5.2)
4.20  camera home     5.20  everything idle
```

---

## 5. The scorer and the governor ("fanciness", v3 as prototyped)

It is a pure function of the event stream plus a little session state. It runs once each time the chord name settles.

**Inputs, per settled chord:**
- **harmony:** finger-held notes, plus pedal-held notes struck in the last 1.5 s. This is PIANO-V2-SPEC 6.1's `harmonySet`, so an accumulated pedal wash is not scored as an 11th chord.
- **strike:** notes whose onsets fall within 80 ms of the newest one.
- **accent:** the strike's mean velocity minus the mean of the 20 s before it.

**Points:**

| Part | Rule | Points |
|---|---|---|
| colour | extensions in the harmony chord: 13/11 · 9 · 7/6 · sus/dim/aug | 3 · 2.5 · 1.5 · 1 |
| slash | a slash chord (F/A, C/G) | 0.5 |
| density | pitch classes over 4 | 0.5 each, cap 1.5 |
| span | strike span ≥ 24 / ≥ 36 semitones | 1 / 1.5 |
| mass | strike ≥ 4 / ≥ 6 notes | 0.5 / 1 |
| accent | ≥ +12 / ≥ +22 over the 20 s mean | 1 / 2 |
| loud | velocity ≥ 112 | 0.5 |
| pedal | pedal down with a real strike | 0.5 |
| borrowed | a harmony tone outside the key | 1.5 |
| novelty | a chord name not yet heard this session (with a real strike) | 0.5 |
| fatigue | 3+ times in the last 60 s | −1.5 |
| **arc** | the 3rd or later block strike in a run, each ≥ 4 louder within 12 s, ending ≥ 105 | **1.5** |

**Tiers and gates:**
- **Score thresholds:** Uncommon ≥ 2.5, Rare ≥ 4.5, Epic ≥ 6, Legendary ≥ 8.
- **Gates** demote one step at a time:
  - Legendary needs 5+ struck and an accent of at least +22 or velocity 112
  - Epic needs 4+ struck and an accent
  - Rare needs 3+ struck together
- **Tokens** (the rarity governor): a tier without a token demotes one step.

  | Tier | Cap | Refill | Start |
  |---|---|---|---|
  | Rare | 3 | 1 per 10 s | 3 |
  | Epic | 2 | 1 per 45 s | 1 |
  | Legendary | 1 | 1 per 180 s | 0.75, so none before ~45 s of play |

**How it got there: three runs on the same 70 s of authored music.**

The music was the wash_check score (36 s of pedalled F/A, C/G, Dm, Bbmaj7 arpeggios, pedal changes, then an 8-bar pedal hold), a loud spread F chord, then a coda crescendo: Bbmaj9/D at 96, C9sus4/G at 102, C9sus4 at 108, Fmaj9 at 120.

| Version | Common | Uncommon | Rare | Epic | Legendary | What went wrong or right |
|---|---|---|---|---|---|---|
| v1 (all sounding notes, 250 ms strike, cooldowns) | 18 | 15 | 3 | 2 | 1 | **the Legendary misfired on an arpeggio** (Dm11 at 33.9 s, from pedal accumulation); cooldowns then demoted the real climax |
| v2 (harmony set, 80 ms strike, relative accent, tokens) | 11 | 22 | 4 | 2 | 0 | no misfires, but the build-up spent the Epic tokens and the climax got Rare; Uncommon far too common |
| v3 (+ arc, Uncommon ≥ 2.5) | 24 | 9 | 3 | 2 | **1** | **Legendary on the climax** (65.98 s, Fmaj9 vel 120, score 9 including arc 1.5 and accent 2); the arpeggio section gave 2 Rare and 0 Epic |

Receipts: `state/arsenal/receipts/piano-spectacle/vfx/{auto,auto-v2,auto-v3}/vfx-check.json`. The `fxLog` field has every fire with its parts, gates, strike size, velocity and mean.

**Honest caveat:** I tuned v3 on music I wrote, so this is evidence the rules can do the right thing, not calibration. Calibration comes next:
- **Calibrate on Daniel's own playing.** Replay the practice log's `events.jsonl` (the other build's `state/arsenal/performance/<session>/`) through the scorer offline. It is pure, so no browser is needed.
- **Set thresholds by percentile of his chord changes:** Rare ≈ top 8%, Epic ≈ top 2%, Legendary ≈ top 0.3% and requiring an arc or a borrowed fortissimo. Check the target rates per 10 minutes.
- **Use the steady key tracker's borrowed flag** from the Nashville build instead of my Krumhansl scale test. Add a **resolution bonus**: borrowed→tonic (iv→I, bVII→I) +1, and V→I at the top of an arc +0.5.
- **Cross-session novelty from the log:** "the first Bbmaj9/D you have ever logged" +1. Daniel will love being told that.
- **A summon pad:** a KeyLab pad or CC fires a chosen tier for a staged TikTok moment. A settings toggle **Spectacle: off / subtle / full**, where off is byte-identical to today (the meshes invisible, the uniforms zero).

---

## 6. Light budget and readability, measured

The metrics come from the same frame as each snapshot (`vfx_check.mjs`, SHOT):
- `luma`: mean Rec.709 luma
- `white`: share of pixels whose darkest channel is above 0.85
- `staff`: mean luma in the staff box (spec acceptance < 0.6)
- `labelBg`: mean luma of the chord-name box's non-text pixels (luma < 0.7)

All figures are v2 unless marked v1.

| Shot | luma | white | staff | labelBg |
|---|---|---|---|---|
| Rare, before | 0.171 | 0.0081 | 0.150 | 0.103 |
| Rare +0.25 s | 0.197 | 0.0090 | 0.200 | 0.113 |
| Rare +0.6 s | 0.188 | 0.0090 | 0.215 | 0.161 |
| Rare +1.0 s | 0.177 | 0.0090 | 0.187 | 0.211 |
| Rare +3.0 s, effect over | 0.167 | 0.0084 | 0.180 | 0.189 |
| Legendary, before | 0.138 | 0.0084 | 0.108 | 0.042 |
| Legendary +0.3 s | 0.189 | 0.0054 | 0.165 | 0.055 |
| Legendary +0.8 s | 0.197 (v1 0.210) | 0.0043 | 0.228 | 0.058 |
| Legendary +1.4 s | 0.170 | 0.0013 | 0.229 | 0.066 |
| Legendary +2.2 s | 0.167 | 0.0012 | 0.217 | 0.087 |
| Legendary +6.0 s, over | 0.129 | 0.0092 | 0.157 | 0.110 |
| Dense wash (40 notes in 4 s, pedal down) | 0.182 | 0.0016 | 0.218 | 0.077 |
| Wash + Legendary +0.8 s | **0.235 (v1 0.296)** | 0.0031 (v1 0.0117) | **0.291 (v1 0.420)** | 0.131 |
| Wash + Legendary +1.6 s | 0.227 | 0.0019 | 0.305 | 0.170 |
| 16:9 Legendary, before | 0.127 | 0.0057 | 0.095 | 0.033 |
| 16:9 Legendary +0.8 s | 0.193 | 0.0015 | 0.124 | 0.054 |

Reading the table:
- **Legendary adds at most +0.06 mean luma, and the near-white share goes down.** The house lights take back what the effect spends; the foil turns the one big white element (the name) gold.
- **The Rare labelBg rise is the columns, not the effect.** The "before" shot is 1 s after the strike, before the columns reach the label box, and labelBg stays at 0.189 after the effect has ended.
- **The dense wash is the stress case.**
  - v1's shimmer drew a white horizontal bar across 40 columns: +62% luma, staff 0.42.
  - The v2 budget holds it to +29%, staff 0.29, which is under the spec's 0.6 with margin.
  - Visually the wash + Legendary frame is busy but not washed; every notehead is visible.

---

## 7. Performance

**Method:**
- `__piano.bench(n)` renders n frames synchronously, each forced to finish with a 1-pixel `readPixels`, and returns the mean ms.
- Headless Chrome (`--headless=new` plus the three anti-throttling flags), ANGLE D3D11 on the **AMD Radeon RX 9070 XT**, 1080x1920, HalfFloat MSAA 4, UnrealBloom, OutputPass, overlay.
- Receipts: `state/arsenal/receipts/piano-spectacle/vfx/hook/vfx-check.json` and `hook-v2/vfx-check.json`.

| Condition | v1 ms/frame | v2 ms/frame |
|---|---|---|
| idle (240 frames) | 1.165 | 1.867 |
| a held 6-note chord (240) | 1.189 | 1.773 |
| Rare live (90) | 1.270 | 1.392 |
| Legendary live (90) | 1.378 | 1.466 |
| Legendary + Epic + Rare stacked (90) | 1.394 | 1.499 |
| dense wash + Legendary (90) | 1.463 | 1.467 |

- **Reading:** v1 is the cleaner run: Legendary costs about +0.19 ms over a held chord, and the worst stack about +0.27 ms. In v2 the idle run came out slower than the live ones, which shows the bench noise (~0.5 ms, warm-up and scheduling) is larger than the effect cost. Either way the whole frame is under 1.9 ms against 16.7 ms at 60 fps.
- **Not measured:** fps from a visible window, and recording-while-rendering. By the shader-craft floor I claim no fps number, only synced frame cost.
- **Real risk, a first-trigger hitch:** three.js compiles a program the first frame its mesh is visible, so the first Rare or Legendary of a session can stall a frame or several. Fix: at boot, set every effect mesh visible with zero gain, call `renderer.compileAsync(scene, camera)`, then hide them.
- **Adaptive resolution** (Daniel's other ask tonight):
  - The effects read `uRes` from `composer.readBuffer`, and the protect regions are fractions of the frame, so they follow a changing render size.
  - Two pixel constants must scale with the render scale: the fountain's 2.5 px point minimum, and the banner's canvas size, which should be drawn at output resolution like the label.

---

## 8. The prototype: files, hooks, snapshots, and my honest read

**Files:**
- `arsenal/web/piano-lab-vfx.js` and `.html`: a lab copy from HEAD plus the patch. Current state is v3.
  - Rebuild: `git show HEAD:arsenal/web/piano.js > arsenal/web/piano-lab-vfx.js`, then `node patch_lab.mjs`.
- `research/in-flight/piano-spectacle-2026-09-13/prototype-vfx/`:
  - `fx_module.js`: the effects, overlay and scorer, final v3
  - `patch_lab.mjs`: shimmer uniforms and shader, camera offsets, overlay hook, house lights, render-loop call, note-on hook, test hooks
  - `fix_v2.mjs`, `fix_v3.mjs`: the round fixes, as applied
  - `vfx_check.mjs`: the headless driver
  - `piano-lab-vfx.v1.js`: the round-1 lab file

**Hooks** (lab only):
- `__piano.fx(tier, notes?)` fires a tier on the sounding notes
- `__piano.fxLog()` returns every fire with the scorer's reasons
- `__piano.bench(n)`, `__piano.clock()`
- `?fx=auto` turns the scorer on

**Runs:**
- `node vfx_check.mjs hook 9611 <label>` covers:
  - Rare over a pedalled Bbmaj9 (velocity 100)
  - Legendary over a pedalled Fmaj9/A across three octaves (velocity 118)
  - a 40-note pedalled wash with a Legendary on top
  - a 16:9 Legendary
  - the benches
- `node vfx_check.mjs auto 9612 <label>` plays the authored music with the scorer live.
- **All runs: no page errors, no shader errors.**

Snapshots are in `E:/AI-Setup/state/arsenal/receipts/piano-spectacle/vfx/`.

**Round 1 (`hook/`), as first built:**
- `rare-1-+0.25s.jpg`: the floor ring's front arc sweeps the empty floor below the keys in the chord's colours; the shimmer shows as bright bulges on each column; the fountain is a fizz at the feet; RARE reads cleanly between the chips and the staff; the name is untouched. **Good.**
- `rare-2-+0.6s.jpg`: the ring's back arc rises above the rail behind the columns, the best 3D cue in the set; the shimmer is subdued inside the staff. **Good.**
- `rare-3-+1.0s.jpg`: sparks fall onto the rail as specks; calm. **Fine.**
- `leg-1-+0.3s.jpg`: the strongest frame of round 1. Gold foil name, gold banner, gold rail with pulse heads, double ring in the floor band, the shaft fan. **But the shimmer bulges burned to white blobs** and lost their hue.
- `leg-2-+0.8s.jpg`: **defect:** the protect mask shows as a dark rectangle around the chord name, and the aurora's upper curtain is a sky of blurred purple and orange mush.
- `leg-4-+2.2s.jpg`: the gold hem wave behind the columns reads well; the rectangle is still visible.
- `wash-1-leg+0.8s.jpg`: **defect:** the shimmer across 40 columns forms a white horizontal bar; luma +62%.
- `wide-1-leg+0.8s.jpg`: in 16:9 the gold aurora ribbon across the frame is lovely; the rectangle around the name is visible.

**Round 2 (`hook-v2/`), after the fixes (soft mask, shimmer budget, low aurora, taller fountain):**
- `leg-1-+0.3s.jpg`: the shimmer keeps each column's hue (pastel lifts, not white). **Fixed.**
- `leg-2-+0.8s.jpg`: no rectangle; the haze fades softly around the name. The fountain is glitter plumes. The gold ribbon sits behind the columns at staff-bottom height. The top of the frame still has soft haze, which is the weakest element.
- `leg-4-+2.2s.jpg`: the gold ribbon plus the shaft fan behind the risen columns is the Legendary look; no mask artifacts.
- `wash-1-leg+0.8s.jpg`: no white bar; +29% luma; the staff and every notehead are readable; busy, not washed. **Fixed.**
- `wide-1-leg+0.8s.jpg`: the cleanest frame of the whole study. Gold name top left, banner under it, shafts and ribbon across the stage, gold floor rings under the keyboard.
- `rare-2-+0.6s.jpg`: glitter plumes about 150 px up the columns; the ring's back arc; RARE banner.

**Scorer run (`auto-v3/`):**
- `auto-coda-4+1.0.jpg`: **the scorer's own Legendary, on the climax** (Fmaj9 at velocity 120, 0.38 s in).
  - Gold name, LEGENDARY banner, the beam fan (wide, because the chord spans five octaves), the gold ribbon, gold floor rings, glitter at the feet.
  - Luma 0.169; the staff is readable, including the ledger-line bass notes.

**What I'd still change before shipping:**
- **The aurora's upper haze:** cut to hem-only, or give it real structure.
- **The fountain:** it is honest glitter, not a fountain. Fine for 9:16; 16:9 could afford +30% height.
- **A per-slot palette** so a new trigger doesn't recolour rings already in flight (section 10).

---

## 9. What never happens

- **No full-frame light:**
  - no full-screen flash, fade to white or additive full-frame quad
  - no screen shake, whole-frame chromatic aberration or pumping vignette
- **No effect hides a key:**
  - nothing draws over the key fronts
  - rings are a depth-tested floor
  - sparks spawn behind the key backs
  - shafts and aurora sit behind the columns
  - the camera push is capped so the chord's keys stay framed
- **No effect light at the heart of the chord name** (≤ 12%), and ≤ 45% inside the staff. Banner and foil never change a glyph's shape or position.
- **No tier hue as scene light.** Gold is the only non-pitch light, and only on Legendary.
- **No per-frame randomness:** no flicker, grain or strobe (twinkle ≤ 2 Hz). No animation driven by frame count.
- **No sub-pixel line or point:** fwidth widening with energy kept; a 2.5 px point minimum.
- **No light that outlives its budget:** Epic and Legendary dim old columns; the shimmer scales down with column count.
- **No rarity inflation:**
  - no Legendary in the first ~45 s, never two within 180 s, at most 2 Epics per 45 s
  - nothing scored from pedal accumulation alone
  - nothing fires on a pedal lift, which is its own clearing
- **Spectacle off means byte-identical to today.**

---

## 10. Risks and open questions

1. **Scorer overfit:** v3 is tuned on my authored music. Calibrate thresholds on Daniel's logs (section 5) before anyone calls a tier "right".
2. **First-trigger shader compile hitch:** precompile at boot with `compileAsync` (section 7).
3. **Shared palette uniform:** every live effect shares one palette uniform, so a second trigger within ~2 s recolours the earlier rings mid-flight. Fix with a per-slot palette row in a small DataTexture.
4. **Palette blending:** RGB blending between distant hues passes through grey mud (shader-craft ceiling). The lab narrows the blend (smoothstep 0.35-0.65); production should blend in OKLab.
5. **Scheme conflict.** PIANO-V2-SPEC 6.2 says new schemes "never sum light". Upright Roll is normal-blended with no additive halos, and additive rings and shafts conflict with that scheme's rules.
   - The spectacle director should ask the active scheme for a blend policy.
   - Under a strict scheme: rings become normal-blend hairlines, the shafts become alpha-blended, and the shimmer is off.
   - Neon Trails keeps the additive set behind its density guard.
6. **Integration shape** (this is the proposal):
   - A core module `piano/spectacle.js`: `createSpectacle(ctx) → { onChord(info, frame), trigger(tier, notes, why), update(dt, t, frame), resize(framing), dispose() }`.
   - It owns rail, floor, fountain, shafts, aurora, banner, foil, camera and house lights.
   - A scheme may implement an optional `spectacle(tier, t, notes)`; the shimmer is Neon Trails' implementation of it.
   - The scorer belongs next to THEORY as pure, node-testable code.
7. **Readability over a lit label box:** tall columns reaching the name are today's look, not the effects'. The planned readability plate (spec section 2) helps both.
8. **TikTok UI:** captions at the bottom and the icon rail on the right can cover the floor ring's lower arc. The ring is garnish there, never information.
9. **Base drift:** `piano.js` and `piano.html` are modified in the working tree by the concurrent build; git status showed them modified at the end of this session, and I never wrote them. The lab is based on HEAD `a886a0af` and must be re-based onto piano-next for integration.
10. **Unmeasured:** visible-window fps, recording load (WebCodecs plus effects), and a real KeyLab session. Ship behind the off / subtle / full toggle, default subtle (Common to Rare), with Epic and Legendary one click away.
