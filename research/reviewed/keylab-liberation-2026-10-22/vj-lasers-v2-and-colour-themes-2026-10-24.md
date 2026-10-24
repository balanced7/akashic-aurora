# Lasers v2 and colour themes: research and the build spec (2026-10-24)

Workflow run wf_68f265a8-6a5 (task wmi9gzrml). Verbatim; local scratch paths shortened.

Daniel (verbatim, 2026-10-24): "for the lasers perhaps we can do a triple strobe, or a one two flicker, it could be timed to the bpm of the track once its established from a database, I can also tap the tempo button or the tap button to the right of record on the keylab. I think this way the lasers can be even cooler, we can also alternate which lasers fire as well as have multi color bursts. I want there to be a lot of variety and strong color themes" -- and after this pass was launched: "we could have another button to make the lasors vibrate like how our piano strings do! t t tou blur blur flash would look so sick!, or if they did that in a 3d shape like a circle, triangle or any other cool looking pattern!" (that second ask is folded in at build time).


---

## The build spec (verbatim)

# Lasers v2 and colour themes: the build spec

This is the designer's spec, dated 2026-10-24. It covers research and design only. I changed nothing in the repo, on the KeyLab, or on the servers at 8793 and 8794.

The scratch folder is `<session scratchpad>\lasers\`. It holds three scripts:
- `build_themes_v2.py` builds and validates the theme library at the end of this spec. Its output is `themes_library_v2.json` and `themes_library_v2.compact.json`.
- `verify_themes.py` re-checks the colour researcher's numbers.
- `safety_numbers.py` computes the worst-case numbers in section 4.

Daniel's words (verbatim, today): "for the lasers perhaps we can do a triple strobe, or a one two flicker, it could be timed to the bpm of the track once its established from a database, I can also tap the tempo button or the tap button to the right of record on the keylab. I think this way the lasers can be even cooler, we can also alternate which lasers fire as well as have multi color bursts. I want there to be a lot of variety and strong color themes"

North star: "trigger a vast array of visual effects through a simple interface and combos, for the variety and fidelity to be high"

## For Daniel, in plain words

- **Pad 2 stays your laser pad, and it gets much deeper.**
  - A soft hit fires one sharp burst. A medium hit fires a one-two flicker. A hard hit fires a triple strobe.
  - All of them land on the beat.
- **Hit it again inside the same bar and it answers bigger.**
  - More heads fire, and they use two colours.
  - The third press brings a crown of beams from the centre.
  - Leave the pad alone for a bar and it settles back.
- **Hold it and the lasers keep strobing in time until you let go.** In a build it is a roll that speeds up with the snare. In a drop it is a push-pull between kick and bass.
- **No two hits look the same.**
  - Each hit draws from shuffled decks: a shape, an order of heads (left-right, mirrored pairs, centre-out, a chase, a shuffle) and a colour split.
  - Today's burst is kept as one of the shapes, and a "classic" switch brings back today's pad 2 exactly.
- **The timing comes from one clock.**
  - The song database gives the tempo as soon as a track starts.
  - The detector finds where the beats fall.
  - Your Tap button, to the right of Record, overrides both. One tap on a kick puts the beat there. Four taps take over tempo and beat until you stop.
  - The Tap button blinks on the beat, brighter on the ONE, so you can see whether the lights are with the music.
- **Colour comes from 21 themes in 8 families.**
  - They are built from the measured Q-dance palettes and your saved looks (Violet & Rose, Golden Wings).
  - Fader 1 walks through them, and a new theme lands on the next bar.
  - A theme sets the scene, the lasers, the effects and your pad lights together.
- **The lasers never strobe the whole screen.**
  - They are thin beams covering a few percent of the screen, and red is never strobed.
  - A frame limiter checks every frame as the last line of defence.
- **Four choices are yours** (section 6): Tap and FL's tempo, tapping on the ONE, the fader and dial roles, and the velocity tiers.

## 0. What this builds on (checked in the code today)

### The rig as it stands

**Today's laser burst** (`vj.js:1258-1266`):
- It draws in the accent overlay, at most 4 at once.
- The origin cycles by serial number: bottom-centre, left, right, top.
- Velocity sets the beams (3+9·vel), the spread (0.4+1.3·vel rad) and the core width (1.2+2.4·vel px).
- The colour is the pad's colour.
- The envelope is attack 0.012 s and decay 0.9 s, with velocity scaling the decay by 0.6–1.4 (`vj-core.js:353, 589`). There is no gate.

**The overlay feeds back** (`vj.js:198, 1296`): it draws `max(trail, fresh)` with keep = exp(−dt/(0.03+0.17·trails)). At the default trails of 0.5, light lingers about 115 ms. A 16th note at 150 BPM is 100 ms, so a strobe drawn there would smear.

**The Laser Cathedral** (`vj-laser-cathedral.frag:146-191`):
- It has 12 heads on the pad grid.
- Odd and even heads aim at mirrored foci, and the foci step on every beat.
- Each pad fans its own head.
- It reads only the 16×6 strip, which is Play's contract.

**The strip has room** (`vj.js:1126-1168`). Row 2 texel 9 uses only `.x` (the star count), so texel 9's `.yzw` and texels 10–14 are free. The headline brief established that new data for presets must travel in the strip, never as new uniforms.

**The page's BeatClock** (`vj-core.js:657-739`) holds a queue of predicted beats. It takes phase from the last fired beat and flywheels for 4 s. The beat event carries no position in the bar.

**The engine** announces each beat about 250 ms ahead (`vj.py:126`, `AHEAD_S`).

### Gaps and findings

**The VJ engine does not look up the song database per track.** `seed_bpm` is only a command-line value (`vj.py:1602, 2026`). Only the `beat` command does the lookup through `now_playing()` and `tempo.lookup` (`beatsync.py:395-439`). Taps (`beathand.Hand`) are also wired only into `beat` (`beatsync.py:524-551`).

**The Tap button reaches the engine only as a generic control.**
- The engine publishes every CC as `ctl` (`vj.py:1932-1947`), so CC 23 arrives as `cc23` and nothing acts on it.
- Our FL script maps the CC 23 press to FL's tap tempo (`fl/device_AuroraKeyLab.py:78, 187-188`).
- That script lights only LEDs 5, 6, 8 and 11 (`fl/device_AuroraKeyLab.py:100-112`). The Tap LED is id 4 (`protocol.py:51`), so it is free for the beat blink.

**The off-beat warning is thrown away twice.**
- The referee's `on_beat` runs from −1 to 1, and a negative value means locked on the off-beat (`beatref.py:12`).
- The engine clamps it to 0..1 (`vj.py:891`), and the page clamps it again (`vj-core.js:111`).

**Taps must own the phase.** beat_a, the VJ default, keeps the tempo but loses the beat position under a loud off-beat bass. On the registered half-time drift cases it scores F .218 and CMLt .012, with 152 ms prediction error (`research/reviewed/keylab-liberation-2026-10-22/grid-tracker-scoring-2026-10-22.md:62`). In hardstyle the reverse bass sits on that off-beat.

**Three pieces do not exist yet:** a variety engine, a section detector and a final-frame limiter. I searched `arsenal/web` and `arsenal/keylab`.

### Corrections to the colour lane

I re-checked the colour researcher's JSON with `verify_themes.py`. These four are fixed in the library at the end:
1. **22 LED stand-ins were greys** such as #c2c2c2. The repo test exempts only pure white and otherwise demands HLS saturation above 0.5 (`tests/test_keylab_w0.py:207-213`), so they would fail. They are now `#ffffff` plus a `led_level`.
2. **Molten and Pink Pyro listed a held (saturated red) colour in `burst`.** Held colours are now scene-only.
3. **Pink Pyro's laser colour #db1b64 was saturated red** on linear values (0.84). It is now #ff5c9a.
4. **There are six distinct saturated reds, not seven.** #db0001 appears in three themes.

## 1. Lasers v2

### 1.1 The model: one hit is five choices

| Axis | What it decides | Catalogue |
|---|---|---|
| Pattern | What the beams look like and how they aim | 14 |
| Gate | When they blink, counted in beats | 13 |
| Order | Which heads fire, and in what sequence | 11 |
| Colour mode | How the theme's colours split across beams, heads and pulses | 9 |
| Start | Which head or pair begins | dealt from a head deck |

That gives 14 × 13 × 11 × 9 = 18,018 combinations before the section filters apply, across 21 themes. Small catalogues on independent axes are how laser desks get variety: BEYOND separates cues, beat-based effects and Q-Shift offsets; ChamSys separates chases, FX spread and speed masters.

### 1.2 The heads

**Head map.** Up to 12 heads, plus one hero head at the hero point.
- Coordinates are centred units, frame height = 1, +y up. The hero sits at (0, 0.05), which is 45% from the top, as in the Rose Window plan.
- The default map for scenes without their own heads:
  - 4 floor heads at y −0.46, x ±0.21 and ±0.62;
  - 4 truss heads at y +0.46, same x;
  - 2 per side tower at x ±0.80, y −0.12 and +0.18.

**Head sets are computed from positions, never hard-coded:**
- left and right by the sign of x;
- mirror pairs by |x| and y;
- rings by distance from the hero;
- rows by y (floor, towers, truss);
- rotor order by angle around the hero;
- chase order by x.

So the Rose Window rebuild can move heads freely.

**Scenes with their own heads** declare the header tag `laser-heads`; Play ignores tags it does not know. In v1 only the Cathedral is tagged, and its heads are its pad grid. For a tagged scene the page writes the head bus into the strip (1.7), and the beam layer draws only the hero head.

### 1.3 Pattern catalogue (14 to implement first)

| # | Pattern | What it looks like | Motion | Sections | Beams when gated |
|---|---|---|---|---|---|
| 1 | Fan Burst (today's look) | A fan opens from one head toward the hero. Velocity sets count and spread as today. The hit seed picks the sweep direction. | Aim drifts ±(0.25+0.35·vel) rad over the pulse | all | ≤ 12 per head |
| 2 | Hot Beam | One tight beam with a fixed aim through the hero region, from a deck of 6 aims | none; it cuts black | intro, anti-climax, screech, piano | 1 |
| 3 | Scissors | Mirrored pairs aim at mirrored foci that step on each kick (the Cathedral's grammar as a pattern) | Eases over the first 45% of the beat, then holds | groove, anti-climax | 2 per pair |
| 4 | X Through the Hero | The two outer floor heads cross at the hero | Holds 2–4 beats | drop entry | 2 |
| 5 | Crown | 12–24 even, mirrored beams rise from behind the hero (hero head) | Opens on the ONE over ⅛ beat, holds 4–8 beats | drop, climax | 12 (24 only ungated) |
| 6 | Starburst | Beams all round the hero, full count for a moment, then thinning | Once, on the drop's ONE | drop ONE | ungated only |
| 7 | Converge → Bloom | Every head aims at the hero and the spread narrows each bar; on the ONE they snap outward | 1 step per bar; the bloom takes ⅛ beat | build, then drop ONE | 1 per head |
| 8 | Scanner Sweep | A fan sweeps side to side and eases to a stop on each kick | 1 sweep per beat (½ beat in the last climax bars) | drop | 6 per head |
| 9 | Zigzag | A beam jumps between two angles on every gate step | step = gate step | screech | 1–2 |
| 10 | Tunnel | Beams from a ring of heads meet at the hero, and the ring spins | 1 turn per bar, then per ½ bar, then per beat as the build rolls | build | 1 per head |
| 11 | Phase Wave | Every head runs the same sweep, each offset by 1/N of the cycle (BEYOND's Q-Shift) | 4-beat cycle | melodic drop, break | 1 per head |
| 12 | Rain | Vertical beams from the truss heads, a dealt head on each step, soft fall | every ½ beat | break, outro | 1 |
| 13 | Cage | Two families of parallel beams (left heads, right heads) cross; the cage rotates at bar lines | 1 step per bar | anti-climax | 4 per family |
| 14 | Ladder | Horizontal rungs from the tower heads stack one per step and clear on the bar | 1 beat, then ½ beat in the last bars | build | 1 per rung, ≤ 8 rungs |

The "sheet" forms (False Ceiling, Liquid Sky) are left out of v1 on purpose. A dense fan reads as a filled surface, which is too much area to gate safely.

### 1.4 Gate catalogue (13)

A pulse turns the beam core on, then off. The tail is how the last pulse fades into the theme colour. "b" means one beat.

| # | Gate | Pulses (offset → length, in b) | At 150 BPM | At 180 BPM | Where |
|---|---|---|---|---|---|
| G1 | Single (Kick Hit) | 0 → ⅛; tail ¼ | 50 ms on, 100 ms tail | 50 ms on (3-frame floor), 83 ms tail | kicks in the groove; piano chord hits |
| G2 | One-Two Flicker | 0 and ¼, each → ⅛; tail ¼ on the second | 0 and 100 ms | 0 and 83 ms | drop kicks. Variant: the 2nd blink on the next head, in the other colour |
| G3 | Triple Strobe | 0, ¼, ½, each → ⅛; tail ½ on the third | 0/100/200 ms, 250 ms span | 0/83/167 ms, 217 ms span | fill on beat 4 of every 4th bar; screech hits |
| G4 | Triplet Triple | 0, ⅓, ⅔, each → ⅙ | 0/133/267 ms | 0/111/222 ms | 1 in 4 instead of G3; climax |
| G5 | Push-Pull (1 b loop) | side A 0 → ¼, side B ½ → ¼; 35 ms release | | | main drop groove (kick against reverse bass) |
| G6 | Reverse-Bass Gate (1 b loop) | ½ → ⅜, cut before the kick. Raw: hard cut. Euphoric: 35 ms release | on at 200 ms, off at 350 ms | | drop, under the kicks |
| G7 | Eighth Roll (½ b loop) | every ½ b → ¼ | 5 per s | 6 per s | build, stage 2 |
| G8 | Sixteenth Roll (¼ b loop) | every ¼ b → ⅛ | 10 per s | 12 per s | last 2–4 bars of a build |
| G9 | Doubling Roll | 1 b steps, then ½, then ¼; dark on the last beat (see note) | | | the whole build |
| G10 | Stop-Short | A 16th roll that cuts at beat 2½ of the last bar, dark until the ONE | | | surprise drop entry |
| G11 | Military Roll (1 bar loop) | 16-step masks from a seeded set (see note) | | | anti-climax screech |
| G12 | Inhale (1 b loop) | Ramps 0→1 through the beat (x²), hard cut on the beat | | | pre-drop; euphoric bass |
| G13 | Bar Marker | ONE only → ⅛; tail 1 b | | | breaks, worship piano, rests in long drops |

Notes on the table:
- **G9 timing.** The steps change on the phrase line: 8 + 4 + 4 bars of a 16-bar build. Without a known phrase, each step lasts one bar of holding the pad.
- **G11 masks.** `x.xx x.x. xx.x x...` (the laser-craft lane), plus three of mine: `xx.x .xx. x.xx ..x.`, `x..x x.x. x..x xxx.`, `x.x. xx.. x.xx x.x.`.
- **Roll shapes.** The doubling roll, the stop-short and the roll with rests come from Attack Magazine's snare-roll techniques.
- **Frame rules.** They are stated in ms so other refresh rates follow: a pulse stays on at least 40 ms (3 frames at 60 Hz), the gap stays off at least 30 ms (2 frames), and a step lasts at least 83 ms (5 frames). A faster step runs at half speed, so a 16th roll above 180 BPM becomes an 8th roll.
- **Anchoring.** Short gates (G1–G4 and G13, spanning at most 1 beat) anchor on the hit. Loops (G5–G12) anchor on the grid (3.3).

### 1.5 Orders (11): "alternate which lasers fire"

- **O1 One head:** dealt from the head deck.
- **O2 Alternate L/R:** left, then right.
- **O3 Mirror pair:** a symmetric pair fires together.
- **O4 Centre-out:** rings outward from the hero, so beams radiate from the hero.
- **O5 Outside-in.**
- **O6 Chase L→R or R→L:** by x.
- **O7 Odd/Even:** odd heads on even pulses.
- **O8 Rows:** floor, then towers, then truss.
- **O9 Rotor:** around the hero by angle.
- **O10 Seeded shuffle:** a deck of heads; the same seed gives the same order, like a grandMA3 shuffle value.
- **O11 All:** single pulses only, within the beam caps.

Pulse k of a hit uses step k of its order, and a loop carries the order on across its steps. Mirrors, outside-in and inside-out offsets, and DIV/MOD grouping are BEYOND Q-Shift's and ChamSys's spread tools.

### 1.6 Colour modes (9): "multi colour bursts"

The roles: L1 = the theme's `lasers[0]`, L2 = `lasers[1]` (or W when there is only one), W = white. A laser never uses a held (red) colour.

**Per beam, inside a fan (done in the shader):**
- **M1 Mono:** one colour with a white core.
- **M2 Split Pair:** beams alternate L1 and L2.
- **M3 Gradient Fan:** L1 to L2 along the OKLCH short arc, only when the hue gap is 80° or less.
- **M4 Hot Core:** a white centre beam with coloured sides.

**Per head or per pulse (done by the engine):**
- **M5 Mirror Halves:** left heads L1, right heads L2.
- **M6 Colour Chase:** L2 walks one head or beam per step.
- **M7 One-Two Flip:** pulse k takes `strobe.flicker[k]`.
- **M8 Trinity Triple:** pulses take `strobe.triple`, usually two coloured and a white third as the payoff.
- **M9 Bar Swap:** the sides swap colours on each bar line.

Rules:
- **Split-only themes** (Acid Screech, Magenta Classics, Sanctuary Gold) never get M2 or M3, because their colours grey out where they blend.
- **A multi-colour burst** is M2, M3, M5 or M8, dealt on the hit.
- **The bright head of a burst lasts at most one beat.** Its tail settles into L1 within 200 ms.

### 1.7 Drawing: a beam layer with no feedback

**A new pass.** It is called `BEAM_FS`, lives in `vj.js`, renders at the overlay's resolution, and is added in the composite the way the overlay is. It is never fed back, so a gate's dark gap is really dark. Tails come from each pulse's envelope, not from trails.

**Uniforms.** These belong to a page shader, not a Play preset, so new ones are allowed:
- `u_head[13]`: origin xy, aim, level;
- `u_headB[13]`: beams, spread, core width in px, colour mode;
- `u_headCol[13]` and `u_headCol2[13]`;
- `u_haloHold`.

The fan math is today's overlay math (nearest beam of a fan, `aaWire` core, `hotCore` whitening, Lorentzian halo), so Fan Burst looks like today's burst.

**Halo hold (load-bearing for safety).** While a gate runs faster than 3 pulses per second, halo = level × (0.75 + 0.25·pulse). The haze glow breathes and only the hot cores strobe. My raster check (4.4) shows why it matters: with a flashing halo, a 12-beam fan covers 34% of a one-third-frame window; with cores alone it covers 11.6%.

**Envelope.** Each pulse is on at full level for its length, then off with τ = 8 ms (hard cut) or the gate's release. The last pulse's tail uses τ = tail/3.

**Solo.** While a pad-2 gate runs, the scene's idle beams dip to 30%, like a laser desk's Flash-Solo cue.

**The strip head bus for tagged scenes.** STRIP.VERSION goes from 1 to 2; the layout comment in `vj-core.js` must be updated too.

| Texel | x | y | z | w |
|---|---|---|---|---|
| (9,2) | star count (unchanged) | pattern id 0–14 | step phase 0..1 | solo level |
| (10,2), (11,2), (12,2) | 12 head levels, each = colour slot + level (slot 0 = L1, 1 = L2, 2 = white; level in [0, 0.999]) | | | |
| (13,2) | L1, linear rgb | | | beams per fan |
| (14,2) | L2, linear rgb | | | fan spread (rad) |

**The Cathedral in v1:**
- A head's fan level = max(row 0 pad level, head bus level).
- The page zeroes row 0's pad-2 level for tagged scenes, so head 2 never fires twice.
- Idle beams are multiplied by the solo level.
- Converge aims at the centre and Rain aims down, natively. Other patterns keep the Cathedral's scissor aim and take the bus's fan size.

**Classic mode.** A "Lasers: classic" setting restores today's pad-2 overlay burst exactly. The old path stays in the code; nothing is deleted.

### 1.8 How it is played

| Gesture | What happens |
|---|---|
| **Pad 2 tap** | One hit. Pattern, order, colour mode and start are dealt. In AUTO, velocity picks the gate: below 0.45 Single, 0.45–0.8 One-Two, above 0.8 Triple (1 in 4 Triplet Triple). Velocity still sets beam count, spread and brightness. |
| **Pad 2 again within the same bar** (the second press is a question) | One tier up. **Tier 2:** the order widens (adds the mirror twin or the next ring), a two-colour mode, and the gate steps up (Single → One-Two → Triple → Triplet Triple). **Tier 3 (hero):** Crown, Starburst or Bloom from the hero head with Trinity Triple, if at least 6 hits have passed since the last hero; otherwise tier 2 with a fresh deal. It falls back one tier per bar without a press. The pad's light shows the tier at 60, 80 or 100%. |
| **Pad 2 held** ≥ ½ beat (≥ 200 ms with no clock) | After the short gate, the section's loop runs until release. Build → Doubling Roll. Drop → Push-Pull (a hard press gives the Sixteenth Roll). Anti-climax → Military. Break or piano → Phase Wave in ½-beat steps (no fast gate). On release, the current step finishes, then the loop stops. Idle beams dip to 30%. |
| **Dial** (CC 116) | Picks a fixed gate, G1 to G13, instead of AUTO. The HUD shows its name (the LCD too, once that path is confirmed). Dial click (CC 117) returns to AUTO. |
| **Combo** (a second pad within 50 ms) | Pad 2 fires at once and the partner upgrades it in place, so no latency is added. **1+2 Drop ONE:** Bloom on the next ONE if it is within ⅛ beat, otherwise now, then Crown for 4 beats. **2+3 Hot Core:** white centre beams; the flash still goes through the gate. **2+5 Laser Strobe:** while both are held, a Sixteenth Roll on thin beams with shuffled heads (at most 4) replaces the full-frame strobe pulses. **2+7 Wings:** mirror pairs, outside-in. **2+6 Rain Sparkle:** Rain with shuffled heads on 8ths. |
| **Pads 9–11** (Dampen, Choke, Kill) | Dampen ends loops now and shortens tails ×0.15. Choke cuts every beam. Kill fades the beams with everything else. |
| **Autopilot** (learnable toggle, default off) | The lasers play themselves from the music (1.9), within the solo budget. Meant for when both hands are on the piano. |
| **Pin** (page key P, learnable) | Repeats the last hit exactly, from its seed, until unpinned. |
| **Variety** (learnable, default 1) | 0 makes every hit identical, for rehearsing; 1 is the full deal. |

### 1.9 Which gate on which musical event

**Section sense v1 (new, on the page, heuristic).** It reads kick hits (`hit` events, band kick or full), the energy bands at 40 Hz, the beat grid and the chord source. It is tested by receipt A7.
- **kickRate** = the share of the last 8 beats with a kick within ±70 ms of the beat.
- **BREAK:** kickRate below 0.25 for at least 2 bars.
- **BUILD:** inside a break, either the high band rises over the last 4 bars (slope of at least +0.04 per bar), or hats and snares fall on at least half the 8th positions of the last bar.
- **DROP ONE:** kicks return on 2 consecutive beats after a break or build. The first of those beats is the ONE of bar 1, phrase 1 (`bar_src: drop`).
- **ANTI-CLIMAX:** the first kick section of a track, and any drop with no build before it. **CLIMAX:** a drop after a build. A track change resets the count.
- **SCREECH** (inside kick sections): the high and mid bands both at 0.75 or more for at least ½ beat.
- **PIANO:** the chord source is the keys, meaning keys played in the last 10 s (the engine already makes this call).

| Musical event or section | AUTO choice for a pad-2 hit | Autopilot's own move |
|---|---|---|
| Kick (groove) | G1 or G2 by velocity | none: the idle beams step on the kick (the scene's grammar) |
| Off-beat / reverse bass | hold gives G5 side B, or G6 | G6 on 2 heads, 1 bar in 4 |
| Screech | Zigzag or Hot Beam with G11 or G8, order O10, colours L1 and white | same, ≤ 2 bars |
| Build (snare roll) | Converge, Tunnel or Ladder with G9 on the phrase. Colour drains toward white in the last bar. The last beat is black (all gates stop). | same |
| Drop ONE | Bloom or Starburst with M8 from the hero, then Crown or X | same |
| Climax groove | Crown, X, Fan Burst, Scanner Sweep or Scissors with G5 or G2. Fills: G3 on beat 4 of every 4th bar. Orders O2, O3, O4, O7. | fills only |
| Anti-climax | 1–2 heads; Hot Beam, Cage or Scissors with G1, G2 or G11; one hue, mostly black | G1 on 1 head, every other bar |
| Break / piano | Hot Beam, slow Crown, Phase Wave or Rain with G13, or G1 on chord changes; no step faster than ½ beat | G13 on the ONE |

**Solo budget.** Q-dance's show creator Jonas Schmidt calls the light operator the drummer who keeps time and the laser operator a saxophonist who solos now and then. So the autopilot's gated solos fill at most 2 bars in every 8. Daniel's own presses are never budgeted; only the hero is limited, to 1 in 6–8 hits.

### 1.10 The variety engine

It lives in a pure module, so other pads can use it later.

**Two seeds:**
- The **section seed** changes with each section, or every 8 bars. It shuffles the decks.
- The **hit seed** changes with each press: hash(section seed, hit counter), through splitmix32 into mulberry32.

**Decks.** Each axis is a deck of the cards allowed in this section and theme, shuffled with the section seed. Each hit deals the next card. An empty deck reshuffles, and never starts with the card it ended on.

**Start head.** Dealt from a head deck, preferring the head farthest from the last 4 starts.

**Anti-repeat.** A hit's signature is (pattern, gate, order, colour mode, start head).
- A signature never repeats within 8 hits.
- Consecutive hits differ in at least 2 of the 5 axes.
- A hit that breaks either rule is redealt, up to 8 times, deterministically.

**Small variations from the hit seed:** sweep direction, aim ±0.1 rad, beam count ±1, spread ±15%.

**Variety fader:**
- At 0, every deck plays card 0 with a fixed seed.
- At values in between, each axis redeals with probability equal to the fader value; otherwise it repeats the last hit's card.

**Reproducible.** The same seed and the same inputs give the same hits, bit for bit (receipt A1).

## 2. Colour themes

### 2.1 The library

21 themes in 8 families (the JSON is at the end):

| Family | Themes |
|---|---|
| ritual | Void Ritual, RED Tribe, Red Wall Blue Blades |
| fire | Molten, Golden Wings, Fire & Ice |
| celestial | Celestial Violet, Violet & Rose, UV Euphoria |
| night | Night Sea, Temple of Light, BLUE Raw, Limbo |
| green | Laser Green, Acid Screech |
| pyro | Pink Pyro, Magenta Classics |
| worship | Cathedral Jewel, Brass Break, Sanctuary Gold |
| line | Bone & Gold Line |

Each theme carries:
- A, B and W screen colours;
- `beam` variants, whose halos sit between OKLab L 0.58 and 0.80, so blue beams do not vanish and green does not swamp;
- LED stand-ins with levels;
- the laser roles, the strobe roles (`triple`, `flicker`) and the burst roles;
- the held roles: saturated red, used on the scene only;
- the sections it suits and its hero burst;
- three flags: `split_only`, `one_family` and `crossfade_needs_dip`.

The palettes come from the earlier Q-dance brief (P1–P9, measured from 40 references). The worship themes draw on Palmer et al. 2013 (fast, major music reads lighter, more saturated and yellower).

### 2.2 How a theme drives everything

| Target | Taken from the theme |
|---|---|
| Scene palette (strip row 2, stops 0–3) | Stop 0 = A, stop 1 = B, stop 2 = the OKLab midpoint of A and B, stop 3 = W. Split-only and dip themes use A lifted by 0.1 L as stop 2 instead, so it is never a grey midpoint. `ground` tints the room where a scene has one. |
| Kick glow (composite bloom) | W. Today it is Hue A's complement, which adds a third colour family (`vj.js:1354`). |
| Chord colour | Piano (keys): free, up to the Chord colour knob. Hardstyle (audio): a hue nudge of at most ±15°. Today's default of 0.7 blends four chord colours, up to four families (`vj.js:849-857, 1073-1074`). |
| Lasers | The `lasers` roles through `beam`; `strobe.triple` and `strobe.flicker` for G3 and G2; `burst` for the multi-colour modes. |
| Effects | `fx.shockwave`, `fx.particles`, `fx.flash`. The flash stays white or the W tint, and still goes through the gate. |
| KeyLab pads | The page posts LED stand-ins, never screen colours (today it posts screen colours, `vj.js:1403`). Effect pads use the stand-ins on today's diagonal. Pad 2 takes the laser role's LED colour, with brightness showing the tier. Control pads keep their colours, except Choke: it moves from #ff9a1f (hue 36°, which washes to white on the pads) to #ff3c00 (hue 14°). |

### 2.3 Live controls

**Theme fader** (fader 1, CC 105; today Hue A):
- It has 21 detents in colour-wheel order, with Custom at the top.
- A theme lands after the fader rests for 150 ms, on the next bar.
- Inside a theme, fader 2 becomes Hue drift: ±15°, with the centre detent meaning "as designed".
- In Custom, fader 2 turns the last theme's colour pair round the wheel. This gives back today's free palette.

**Family tabs (the theme pads).** These are the 8 buttons under the screen, learned on first touch; their CCs are inferred, not confirmed.
- The first press picks that family's theme for the current section.
- A second press within a bar moves to the next theme in the family.
- Each button lights in its family's LED colour.
- Page keys F1–F8 do the same, for testing.

**Key auto** (on by default once a key is known). The song's key gives a Camelot number, the number gives a family, and the family's playbook gives the theme.
- The key comes first from the song database at track start. GetSongBPM's song record or AcousticBrainz's low-level tonal key should carry it, but neither field is confirmed yet, and `tempo.py` reads only the tempo today.
- After that, chordsense's key takes over (confidence of at least 0.6, stable for 8 bars).
- Major keys get +0.05 lightness, chroma ×1.1 and +10° toward yellow; minor keys the opposite. The cap is ±15°.
- A manual pick wins until the next track.

**Section rotation:**
- The family playbook picks a theme per section: anti, climax, drop2 and break; for worship, quiet, verse, chorus, bridge and break.
- A returning section returns to its theme.
- Automatic changes happen only on phrase lines, and an automatic theme holds at least 8 bars. Manual picks land on the next bar.
- In a long drop, the laser role swaps every 16 bars.
- A jump of more than 100°, or a flagged theme, cuts through black on the beat.
- When no section is known, nothing rotates.

**Theme Lock** (learnable toggle). Holds the theme, and makes any change wait for the next phrase line.

## 3. Timing

### 3.1 One clock, owned by the engine

It lives in a new pure module, `arsenal/keylab/beatgrid.py`. `BeatGrid` holds an anchor time, an anchor beat number, the period, a bar offset, the source, a confidence and a version number. Four sources feed it, in rising authority:

1. **Database tempo (`src: db`).**
   - A side thread polls Windows now-playing every 2 s (`now_playing()`, `beatsync.py:72`).
   - On a track change it runs `tempo.lookup` and `fuse_bpm`, caches the answer per track, and re-seeds the tracker with the fused BPM, as `beat` does.
   - It never runs on the audio thread, and it fails soft.
   - It gives the tempo only, from the first beat of the track.
2. **Tracker (`src: track`).** Gives the beat position and refines the tempo (beat_a by default).
3. **Referee correction** (behind a flag until benched).
   - When the referee's consistency is at least 0.7 and |offset_ms| is at least ⅛ beat for 2 verdicts running, the phase shifts by the offset. This anchors the beat on the kick.
   - It must pass the bright-bass bench cases before it becomes the default.
4. **The hand (`src: tap`).** Overrides both (3.5).

**Beat event, additive fields** (the contract version stays 1):
- `"bar"`: 1–4, or 0 when unknown;
- `"bar_src"`: `"tap"`, `"drop"` or `"guess"`;
- `"src"`: `"db"`, `"track"`, `"tap"` or `"fly"`;
- `"ver"`: bumps on every hard re-anchor;
- `"wall_ms"`: the send time (time.time()×1000), so the page can measure transport delay;
- `"on_beat"`: −1..1, no longer clamped, plus `"offset_ms"` from the referee.

This is the CDJ beat-packet idea: a beat within the bar plus times to the next beats.

**New events:**
- `tap`: `{"t":"tap","count":k,"mode":"resync|run|lock|release","bpm":x|null}`;
- `track`: `{"t":"track","bpm_db":x|null,"key_db":"F minor"|null}`.

Artist and title stay on the engine's own state route.

`parseEvent` (`vj-core.js`) accepts all of these and widens `on_beat` to −1..1.

### 3.2 The page grid (extends BeatClock)

- **pos(t) = anchorBeat + (t − anchorMs)/period.** This continuous beat position drives every gate.
- **When beat n fires at t_n:**
  - If `ver` changed: hard re-anchor (anchor = t_n, n). It happens at that beat, never mid-pulse.
  - Otherwise, take the error e = n − pos(t_n), to the nearest integer.
    - If |e| ≤ 0.25 beat, slew by stretching the next beat by up to ±10%. pos never jumps backward.
    - If |e| > 0.25 beat, hard re-anchor.
- **A new `ver` flushes queued beats of the old one.** The 4 s flywheel stays as it is.

### 3.3 Scheduling sub-beat gates from the predicted beats

- **Evaluate light at the presentation time:** tEval = rafNow + presentLagMs (default one frame, 16.7 ms; tunable). A pulse lights in the frame whose presentation time is nearest its scheduled time, at most half a frame early or late.
- **No timers per effect.** Every pulse's state is computed from pos(tEval) each frame. A tempo change stretches the gates automatically, and a re-anchor realigns every gate at once (BEYOND's Hard Beat Sync idea: every beat effect reads one metronome).
- **Exactly once.** Each gate remembers the index of its last fired pulse. A forward jump drops skipped pulses, firing only the newest if it is within ¼ step. A backward jump never re-fires.
- **Short gates anchor on the hit.**
  - If a grid point of the gate's step is 60 ms or less ahead, the first pulse waits for it, so a slightly early hand lands on the beat.
  - Otherwise pulse 1 fires now, and the rest land on the following grid points of the step.
  - A pulse never starts less than 83 ms after the previous one; if it would, it moves to the next grid point.
- **Loops anchor on the grid.** The first step starts on the next grid point of its step (a wait of at most ½ step), or immediately if a grid point passed within the last 30 ms.

### 3.4 Tempo change, bad lock, and the confidence ladder

| Level | When | What is allowed |
|---|---|---|
| L3 | confidence ≥ 0.6, or tap-locked | everything |
| L2 | confidence 0.3–0.6 | loop steps of at least ½ beat; no quantize wait (fire on the hit) |
| L1 | flywheel (no predictions, up to 4 s) | loops only at 1 beat (G1 on the beat); short gates as normal |
| L0 | no clock | loops off; short gates use the last known period, else 100 ms steps |

**Why short gates are robust.** They span at most one beat and use the period only for spacing. A 3% tempo error moves the triple's third pulse by about 6 ms. So they stay right even when the beat position is unsure, and the database tempo makes them right from the first second of a track.

**Suspect lock.** If `on_beat` is below 0 for 2 verdicts (4 s), or consistency drops below 0.35, the HUD shows "beat? tap a kick" and the ladder drops one level.

**Drift.** At 150 BPM, a tempo 1 BPM off drifts 2.7 ms per beat. Light becomes noticeably late (45 ms) after about 17 beats. The per-beat slew keeps the error down to the tracker's own.

### 3.5 Tap: how it reaches the engine while FL uses it

**The path.**
- The Tap button sends CC 23 on the DAW port.
- That port is shared under the Windows MIDI Service (probe P1), so FL and our engine both receive the press.
- The engine counts a rising edge of `daw:*:cc23` (value ≥ 0.5, 80 ms debounce) as a tap, timed when it arrives on the MIDI thread (`feed_midi`, perf_counter, the same clock as the audio loop).
- The tap control is learnable (an engine `--tap` id, default `cc23`), in case "the tempo button" turns out to be a different button.

**The math.** `TapLog` is pulled out of `beathand` with no port attached (tap_tempo, tap_grid, versus). `Hand` keeps its own ports for the `beat` command.

**One isolated tap (no tap in the previous 2 s) resyncs the beat**, like BEYOND's Backspace or ChamSys's tap-to-time phase sync. The tapped moment becomes a beat: δ = its phase, wrapped to (−½, ½] beat.
- If |δ| < 0.06 beat, the tap is ignored. That is tap noise, about 25 ms at 150 BPM.
- If |δ| is 0.06–0.125 beat, slew by half of δ.
- If |δ| > 0.125 beat, hard re-anchor at the next beat (`ver`+1).
- One tap on a kick therefore fixes an off-beat lock, where δ is about ½.
- If Daniel confirms he starts tapping on beat 1, the tapped beat becomes the ONE (`bar_src: tap`).

**Four or more taps put the lights on the taps (tap-lock).** Tempo and phase come from a least-squares line through the taps, as `tap_grid` does. The tempo snaps:
1. to the database BPM, if it is within 4% (octave-folded);
2. otherwise to the tracker's BPM, if within 4% and its confidence is at least 0.5;
3. otherwise the tapped tempo stands. By my estimate for 25 ms of tap jitter, 4 taps are good to about ±4 BPM and 8 taps to about ±1.5 BPM.

**When the taps stop** (2 periods with no tap):
- The grid keeps the tapped tempo and phase.
- The hand owns the phase until the tracker agrees within ⅛ beat for 8 beats running. Until then, the tracker refines the tempo only.
- The re-seed rule is unchanged: 8 steady taps, more than 4% apart (octave-folded), at most one per 15 s.

**The Tap LED** (id 4). The engine lights it on each predicted beat, brighter on the ONE: 2 packets per beat through its BurstGovernor. FL's script never touches LED 4.

**FL coupling.** Our FL script also sends every Tap press to FL's tap tempo (`device_AuroraKeyLab.py:187`). With an FL project playing, tapping would retime the project.
- Proposed default: forward to FL only while FL's transport is stopped (`TAP_TO_FL = "stopped"`).
- This is Daniel's call. The engine never depends on FL.

**Pad taps** (beathand's mode) stay in the `beat` command. In the VJ rig the pads fire effects.

### 3.6 The latency budget

| Stage | Size | Status |
|---|---|---|
| Beat announced ahead | about 250 ms (`AHEAD_S`) | today |
| Audio block | 10.7 ms (512 samples at 48 kHz) | today |
| Engine to page (Server-Sent Events, localhost) | about 1 ms expected | to measure with `wall_ms`; p95 must be ≤ 5 ms |
| Animation frame to photon | 1–2 frames | compensated by presentLagMs |
| Frame rounding | ±8.3 ms at 60 Hz | the nearest-frame rule |
| Loopback to speaker | output buffer, likely 10–20 ms (estimate) | puts the light early, which is the safe side |
| Trim | the engine's `offset_ms` (exists) plus the `versus` tap measurement | tune by ear |
| Target | light 0–20 ms before the sound | ITU-R BT.1359: picture-late is detectable from about 45 ms, picture-early only from about 125 ms (a broadcast lip-sync standard, applied here by inference) |

## 4. Safety

### 4.1 Rules (enforced in the laser module before anything is drawn)

1. **Thin beams only.** Cores are at most 3.6 px at 1080p (scaled with resolution), with the halo hold (1.7) on any gate faster than 3 pulses per second.
2. **Caps for gates faster than 3 per second.** At most 4 heads lit, 16 beams in total and 12 per head. The 24-beam Crown and Starburst run only as single onsets.
3. **The area estimator (4.2).**
   - Gated pulses: at most 15% of any one-third × one-third window, and at most 8% of the frame.
   - Single onsets: at most 22% of a window, and at most 10% of the frame.
   - A pulse over budget loses its outer beams for that pulse.
4. **No full-frame forms.** There are no sheet forms; sweeps move thin beams only; gated beams get no feedback trails and no motion blur.
5. **Red.** Lasers never emit a held (saturated red) colour. The library validator proves it: R/(R+G+B) is below 0.8 on both encoded and linear values for every colour a laser can emit.
6. **Fast rolls** (steps of ¼ beat or less): at most 4 bars in a build and 2 bars elsewhere, then at least 1 bar of rest, during which the gate drops to ½ beat.
7. **Lasers never ask the FlashGate.** The 2+3 combo's flash still goes through the gate, as today.
8. **The final-frame limiter is the backstop** (4.3).

### 4.2 The area estimator (pre-limiter)

For each pulse:
1. Sample 16 points along each beam, each with its counted width (the core plus 2 px).
2. Bin the points into a 6 × 6 grid of half-window cells.
3. Evaluate the 25 windows made of 2 × 2 cells.

The cost is O(beams) per frame. The window matches WCAG 2.3.1's reference field, 341 × 256 px at 1024 × 768, which is one-third of each side.

### 4.3 What the lasers expect from the final-frame limiter (being built)

- It measures each frame for relative-luminance changes of 0.1 or more where the darker state is below 0.8, plus red transitions, in one-third-frame windows. These are WCAG's general and red flash definitions.
- It keeps a one-second history of flashes that exceed the area threshold. If a frame would make a 4th, it holds that window's luminance.
- The lasers expect zero interventions in receipt A5. Any intervention during laser play is a laser bug and appears on the HUD.

### 4.4 Worst-case numbers (60 Hz, from `safety_numbers.py`)

| Gate | 150 BPM: pulse on / gap off / most onsets in any 1 s | 180 BPM: pulse on / gap off / most onsets in any 1 s |
|---|---|---|
| Triple, held (every beat) | 3 frames (50 ms) / 3 frames / 8 | 3 frames (50 ms) / 2 frames (33 ms) / 9 |
| Triple, once a bar (fill) | 3 / 3 / 3 | 3 / 2 / 3 |
| One-Two, every beat | 3 / 3 / 6 | 3 / 2 / 6 |
| Sixteenth roll | 3 / 3 / 10 | 3 / 2 / 12 |
| Triplet Triple, every beat | 4 / 4 / 8 | 4 / 2 / 9 |

| Beam shape (1080p, cores 3.6 px plus 1 px each side) | Share of frame | Worst one-third window |
|---|---|---|
| 1 head, 12 beams, 1.7 rad (pad 2 at full velocity) | 3.76% | 11.6% |
| 1 head, 6 beams, 0.9 rad | 1.74% | 5.5% |
| 4 floor heads × 4 beams (the roll cap of 16) | 5.72% | 14.4% |
| Starburst, 24 beams round the hero | 5.01% | 14.6% |
| Crown, 24 beams, upper half | 4.56% | 21.1% (single onsets only) |
| 12 beams if the halo flashed too (+6 px) | 11.46% | 34.3% (fails: why the halo hold exists) |

**Reading the numbers.** A held triple strobe blinks 8 times a second at 150 BPM and 9 at 180, and a 16th roll 10 or 12. That is far above 3 flashes per second. It is safe only because the area stays below WCAG's threshold of 25% of a 10° field: at most 14.6% of the worst window for gated shapes, and under 6% of the frame. The halo hold is what keeps it there. The area figures come from a raster model of the cores, not a render; receipt A5 measures the real thing.

## 5. Acceptance receipts (all headless)

**A1. Variety over 32 hits** (Node, `tests/vj_lasers.test.mjs`).
- Fixture: 32 pad-2 presses on a 150 BPM virtual clock: 8 in an anti-climax, 8 in a build, 16 in a climax. Velocities come from a fixed list covering all three tiers, with repeats; the fixture includes 6 second presses and 2 holds.
- Pass:
  - no signature repeats within 8 hits;
  - consecutive hits differ in at least 2 of the 5 axes;
  - at least 8 patterns, 6 gates, 6 orders and 5 colour modes appear;
  - every hit is legal for its section and theme (split-only rules, beam caps, no held colour);
  - heroes are at most 1 in 6;
  - the same seed gives byte-identical JSON for the 32 hits;
  - Variety 0 gives 32 identical signatures.

**A2. Gate timing against the beat clock** (Node, virtual 60 fps clock).
- Streams: steady 150 and 180 BPM; ±8 ms jitter on the predictions; a ramp from 150 to 156 BPM over 16 beats; a `ver` bump with a ½-beat jump; a 2 s dropout (flywheel).
- Measure each pulse's onset frame against its ideal time.
- Pass:
  - steady streams: max |error| ≤ 8.4 ms, mean ≤ 4.5 ms;
  - with jitter: max ≤ 17 ms;
  - on the ramp: max ≤ 12 ms;
  - no missing and no doubled pulses;
  - after the jump, no pulse fires twice, and the next one lands on the new grid within ±8.4 ms;
  - the frame rules hold: on ≥ 3 frames, off ≥ 2, step ≥ 5.

**A3. Tap and grid** (pytest, `tests/test_keylab_beatgrid.py`, with synthetic tap times and a fake tracker).
- One tap at phase 0.5 on an off-beat-locked grid shifts it by ½ beat, bumps `ver` and sets bar 1.
- One tap at phase 0.03 changes nothing.
- Four taps at 150.4 BPM with a database value of 150 give exactly 150.0, with the phase within 15 ms.
- After the taps stop, the grid holds for 32 beats while a fake tracker keeps reporting the off-beat phase; the tracker never takes over.
- A tracker that agrees within ⅛ beat for 8 beats takes over with no jump larger than 10% of a beat.
- A database seed on a track change makes the first beat event `src: db`.
- An `on_beat` of −0.8 reaches the page as −0.8.

**A4. Colour library** (Node and pytest, porting the checks in `build_themes_v2.py`).
- 21 themes.
- Every LED stand-in is `#ffffff`, or has HLS saturation above 0.5 and a hue outside 15–100°.
- No colour a laser can emit is saturated red, on encoded or linear values.
- No held role appears in any laser list.
- `fader_order` covers every theme once, plus Custom.
- Every playbook entry and every Camelot entry resolves.
- The v2 library below passes today with 0 errors.

**A5. Flash safety.** Part (a) is analytic, in Node on the virtual clock. Part (b) is rendered by `arsenal/lanes/vj_verify.mjs` on SwiftShader.
- Scripts: a triple held for 8 bars at 150 and at 180 BPM; One-Two every beat; a Sixteenth roll for 4 bars; the 2+5 Laser Strobe; Starburst plus Crown. Each runs in three themes: Laser Green (the brightest beams), Night Sea and Golden Wings.
- (a) Rasterise each frame's beams at 960 × 540 (widths scaled) and count pixels whose luminance changes by 0.1 or more.
- (b) Read back full frames at sampled points and compare consecutive frames pixel by pixel.
- Pass:
  - every one-third window stays below 25% (target ≤ 15%), and the frame stays at or below 8%;
  - flashes that exceed the area threshold number at most 3 in any second (0 expected);
  - red transitions: 0;
  - the FlashGate log is unchanged by laser-only scripts;
  - limiter interventions: 0;
  - the raw onset counts are reported as well.

**A6. Colour discipline in a render.** For each theme, render a 12-beam Fan Burst with M3 and M5 over black.
- Pass: at most 2 hue families make up 10% or more of the saturated lit pixels, plus white (rule 5 of the headline brief).
- White-hot cores cover 0.2–6% of the frame on the hit.

**A7. Section sense.**
- Fixtures: a synthetic arrangement event stream at 150 BPM (intro 8 bars, anti-climax 16, break 16, build 16, climax 16), plus the engine's demo replay.
- Pass: at least 85% of bars labelled correctly; the drop's ONE found within 1 beat; the build start found within 2 bars.

**A8. Pad lights.** Every colour posted to `/api/pads` during a theme run is a stand-in that passes the wash rule, and posts stay at 10 per second or fewer (the existing limit).

## 6. Build order, files and Daniel's calls

**Slices:**

| Slice | Work | Receipts |
|---|---|---|
| S1. Engine clock | `beatgrid.py` (with `TapLog` from `beathand.py`); wiring in `vj.py`: the now-playing thread, the database re-seed, Tap on CC 23, the new beat fields, `on_beat` unclamped, the Tap LED | A3 |
| S2. Page clock | `vj-core.js`: `parseEvent` and the grid, extending BeatClock | A2 |
| S3. Laser module | `arsenal/web/vj-lasers.js`, pure: patterns, gates, orders, colour modes, the variety engine, the area estimator | A1, A5a |
| S4. Drawing | `vj.js`: the beam layer, strip bus v2, the Cathedral's `laser-heads` tag; classic mode kept | A5b in `vj_verify.mjs` |
| S5. Themes | `arsenal/web/vj-themes.json` and `vj-themes.js`; the palette, LED, kick-glow and chord-cap changes; the theme fader, family tabs (learned) and key auto | A4, A6, A8 |
| S6. Sections | section sense, AUTO, autopilot | A7 |

**Daniel's calls:**
1. **Tap and FL.** Should a Tap press keep changing FL's tempo? My proposal: only while FL is stopped.
2. **The ONE.** Do you start tapping on beat 1 of a bar? If yes, the first tap of a run marks the ONE.
3. **Controls.** Fader 1 becomes Theme (Hue A and B move into Custom), and the dial becomes the laser gate picker.
4. **Velocity tiers.** Soft = single, medium = one-two, hard = triple, or the other way round (hard = one heavy hit)?

**Gaps:**
- CC 23 as Tap is read from our FL script and Arturia's map. It has not been seen yet at the engine from the hardware. The context-button CCs are inferred.
- The GetSongBPM key field is unconfirmed (their API page refused the fetch). AcousticBrainz's tonal key is to be confirmed on the first live call.
- Section sense is a heuristic, untested on Q-dance tracks.
- ITU-R BT.1359 is a broadcast lip-sync standard; using it for light on music is an inference.
- The one-third-frame window equals WCAG's 10° field only at a typical viewing distance. On a large screen viewed up close, the field is a smaller share of the screen; the 15% target is the margin for that.
- The LED stand-ins remain rules of thumb until the W0 LED probe runs with Daniel at the keyboard.
- The area numbers in 4.4 come from a raster model, not a render.

## Sources

Fetched and checked today:
- Pangolin wiki, BEYOND music and beats (tap-tempo averaging; Backspace re-aligns the beat without changing tempo): https://wiki.pangolin.com/doku.php?id=beyond:music_and_beats_overview
- Pangolin wiki, Q-Shift (period shift per item and per selection, DIV and MOD grouping, outside-in order): https://wiki.pangolin.com/doku.php?id=beyond:qshift
- ChamSys MagicQ busking (tap-to-time on a speed master phase-syncs every chase and FX it controls): https://secure.chamsys.co.uk/docs/magicq/manual/busking.html and https://www.manualslib.com/manual/855941/Chamsys-Magicq.html?page=122
- WCAG 2.1 Understanding 2.3.1 (general and red flash definitions; the 0.006 sr area, 25% of a 10° field, 341 × 256 px at 1024 × 768; area applies to both): https://www.w3.org/WAI/WCAG21/Understanding/three-flashes-or-below-threshold.html
- ITU-R BT.1359-1 (detectability +45 / −125 ms; acceptability +90 / −185 ms): https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1359-1-199811-I!!PDF-E.pdf
- Deep Symmetry, DJ Link beat packets (beat within the bar, plus next beat and next bar in ms): https://djl-analysis.deepsymmetry.org/djl-analysis/beats.html
- Ableton Link (the quantum keeps bar lines aligned): https://ableton.github.io/link/
- Attack Magazine, 10 snare rolls (doubling, stop-short, rests, velocity ramps): https://www.attackmagazine.com/technique/tutorials/10-snare-rolls-for-the-drop/
- Festileaks, Jonas Schmidt (the light operator as drummer, the laser operator as saxophonist who solos): https://festileaks.com/2022/01/jonas-schmidt-is-show-creator-bij-q-dance-in-essentie-speel-ik-met-de-emotie-van-80-000-man/

From the research lanes, not re-fetched by me: grandMA3 MAtricks shuffle, the rekordbox lighting guide, Laserface and Laser Monkey interviews, Palmer et al. 2013 (https://pmc.ncbi.nlm.nih.gov/articles/PMC3670360/), the Camelot wheel, and the GetSongBPM API.

House files:
- `research/reviewed/keylab-liberation-2026-10-22/vj-festival-lessons-2026-10-24.md`
- `research/reviewed/keylab-liberation-2026-10-22/vj-headline-qdance-brief-2026-10-24.md` (palettes P1–P9, the Rose Window, the colour discipline rule)
- `research/reviewed/keylab-liberation-2026-10-22/grid-tracker-scoring-2026-10-22.md:26-28, 55-72, 177-181`
- `research/reviewed/keylab-liberation-2026-10-22/keylab-lit-vision-v2-2026-10-22.md:107` (Daniel's saved looks)
- Code as cited in section 0.

## The theme library (v2, validated: 0 errors)

```json
{"version":2,"roles":{"A": "primary", "B": "secondary", "W": "accent / white-hot"},"laser_colour":"beam[role] if present, else the role's own hex","themes":[
{"id":"void-ritual","name":"Void Ritual","family":"ritual","A":"#ab0a1c","B":"#bfae9f","W":"#fff3d6","ground":"#351015","beam":{"A":"#e01c2c","B":"#bfae9f"},"led":{"A":"#ff001d","B":"#ffffff","W":"#ffffff"},"led_level":{"B":0.76,"W":0.96},"sections":["anti-climax","intro","mid-outro"],"scene":"A","lasers":["B","W"],"fx":{"shockwave":"B","particles":"B","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["B","W"]},"burst":["B","W"],"hero":"none (anti-climax stays one family)","held":["A"],"split_only":false,"one_family":true,"crossfade_needs_dip":false},
{"id":"red-tribe","name":"RED Tribe","family":"ritual","A":"#db0001","B":"#e89029","W":"#fbfcfc","ground":"#520a1e","beam":{"A":"#e11c14","B":"#e89029"},"led":{"A":"#ff0001","B":"#ffffff","W":"#ffffff"},"led_level":{"B":0.78,"W":0.99},"sections":["climax","drop"],"scene":"A","lasers":["B","W"],"fx":{"shockwave":"B","particles":"B","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["B","W"]},"burst":["B","W"],"hero":"gold-to-white gradient fan","held":["A"],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"red-blades","name":"Red Wall, Blue Blades","family":"ritual","A":"#db0001","B":"#4b3cff","W":"#ffffff","beam":{"A":"#e11c14","B":"#5b63f9"},"led":{"A":"#ff0001","B":"#1400ff","W":"#ffffff"},"sections":["climax","second drop","raw anti-climax"],"scene":"A","lasers":["B"],"fx":{"shockwave":"B","particles":"W","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["B","W"]},"burst":["B","W"],"hero":"blue-violet to violet gradient (never red beams in the burst)","held":["A"],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"molten","name":"Molten","family":"fire","A":"#d63b09","B":"#fec141","W":"#fff3d6","ground":"#510a05","beam":{"A":"#d43f13","B":"#f0b225"},"led":{"A":"#ff2000","B":"#ffffff","W":"#ffffff"},"led_level":{"B":0.82,"W":0.96},"sections":["finale","climax","endshow"],"scene":"A>B ramp","lasers":["B","W"],"fx":{"shockwave":"B","particles":"A","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["B","W"]},"burst":["B","W"],"hero":"gold to white gradient fan (the ember stays on the scene)","held":["A"],"split_only":false,"one_family":true,"crossfade_needs_dip":false},
{"id":"golden-wings","name":"Golden Wings","family":"fire","A":"#e89029","B":"#5435d9","W":"#f9e5c5","beam":{"A":"#e89029","B":"#6d5bf9"},"led":{"A":"#ff2a00","B":"#3000ff","W":"#ffffff"},"led_level":{"W":0.93},"sections":["build","euphoric climax","finale"],"scene":"B ground, A light","lasers":["A"],"fx":{"shockwave":"A","particles":"A","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","W"]},"burst":["A","W"],"hero":"gold fan plus a violet mirrored pair, separated, white crossings","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"fire-and-ice","name":"Fire & Ice","family":"fire","A":"#ea7720","B":"#2f6bff","W":"#ffffff","beam":{"A":"#ea7720","B":"#336df9"},"led":{"A":"#ff2800","B":"#004aff","W":"#ffffff"},"sections":["climax","second drop"],"scene":"A","lasers":["B"],"fx":{"shockwave":"W","particles":"A","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["B","W"]},"burst":["B","W"],"hero":"mirror split: left orange, right cobalt, white where they cross","held":["A"],"split_only":false,"one_family":false,"crossfade_needs_dip":true},
{"id":"celestial-violet","name":"Celestial Violet","family":"celestial","A":"#5435d9","B":"#860b5e","W":"#d2d1e5","beam":{"A":"#6d5bf9","B":"#d11a95"},"led":{"A":"#3000ff","B":"#ff00ac","W":"#ffffff"},"led_level":{"W":0.87},"sections":["opener","intro reveal","first groove"],"scene":"A","lasers":["A","W"],"fx":{"shockwave":"B","particles":"W","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"violet to magenta gradient fan","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"violet-rose","name":"Violet & Rose","family":"celestial","A":"#7a3cff","B":"#ff3d8b","W":"#fff0f6","beam":{"A":"#7e51f9","B":"#fb468c"},"led":{"A":"#5100ff","B":"#ff0067","W":"#ffffff"},"led_level":{"W":0.97},"sections":["euphoric climax","melodic drop","signature"],"scene":"A, B rims","lasers":["B","A"],"fx":{"shockwave":"B","particles":"A","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"violet to rose gradient fan (the short way round, through magenta)","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"uv-euphoria","name":"UV Euphoria","family":"celestial","A":"#6a00ff","B":"#00e5ff","W":"#ffffff","beam":{"A":"#7855f9","B":"#2ad4eb"},"led":{"A":"#6a00ff","B":"#00e5ff","W":"#ffffff"},"sections":["euphoric climax","uptempo"],"scene":"A","lasers":["B"],"fx":{"shockwave":"B","particles":"W","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"alternate beams UV/cyan","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"night-sea","name":"Night Sea","family":"night","A":"#0155bc","B":"#1cbde6","W":"#e8f8ff","ground":"#051083","beam":{"A":"#1373f1","B":"#25bde5"},"led":{"A":"#0030ff","B":"#00e5ff","W":"#ffffff"},"led_level":{"W":0.97},"sections":["build","dusk","melodic","laser sea"],"scene":"A","lasers":["B"],"fx":{"shockwave":"B","particles":"W","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"blue to cyan gradient fan","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"temple-light","name":"Temple of Light","family":"night","A":"#696fc2","B":"#172580","W":"#f4f3ff","beam":{"A":"#645ff9","B":"#4769f9"},"led":{"A":"#8080ff","B":"#0022ff","W":"#ffffff"},"led_level":{"W":0.97},"sections":["euphoric break","big white peak","worship chorus"],"scene":"A on B","lasers":["W"],"fx":{"shockwave":"A","particles":"W","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["A","W"]},"burst":["A","W"],"hero":"white fan with periwinkle halos","held":[],"split_only":false,"one_family":true,"crossfade_needs_dip":false},
{"id":"blue-raw","name":"BLUE Raw","family":"night","A":"#0adbef","B":"#1a2cff","W":"#ffffff","beam":{"A":"#2bd5e7","B":"#3d6bf9"},"led":{"A":"#00e9ff","B":"#0014ff","W":"#ffffff"},"sections":["raw anti-climax","screech","rawstyle drop"],"scene":"A","lasers":["A","B"],"fx":{"shockwave":"A","particles":"W","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"alternate beams cyan/blue","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"limbo","name":"Limbo","family":"night","A":"#eef4ff","B":"#4fa8ff","W":"#ff1a3c","beam":{"A":"#eef4ff","B":"#55a8fb"},"led":{"A":"#ffffff","B":"#0081ff","W":"#ff0026"},"led_level":{"A":0.96},"sections":["break","anti-climax (melodic)","worship into hardstyle"],"scene":"A (W pin)","lasers":["A"],"fx":{"shockwave":"B","particles":"A","flash":"white"},"strobe":{"triple":["A","A","A"],"flicker":["A","B"]},"burst":["A","B"],"hero":"none (break register)","held":["W"],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"laser-green","name":"Laser Green","family":"green","A":"#05d987","B":"#72ba4f","W":"#c33661","ground":"#054343","beam":{"A":"#29d889","B":"#72ba4f"},"led":{"A":"#00ff9c","B":"#20ff20","W":"#ff004e"},"sections":["groove","climax","beam section"],"scene":"ground (W pin)","lasers":["A","B"],"fx":{"shockwave":"A","particles":"A","flash":"white"},"strobe":{"triple":["A","A","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"green fan plus the magenta pin as one centre beam","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"acid-screech","name":"Acid Screech","family":"green","A":"#a8ff24","B":"#4a00e0","W":"#ffffff","beam":{"A":"#8ed726","B":"#685df9"},"led":{"A":"#22ff00","B":"#5400ff","W":"#ffffff"},"sections":["anti-climax screech","raw drop"],"scene":"B","lasers":["A","B"],"fx":{"shockwave":"B","particles":"A","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","B"]},"burst":["A","W"],"hero":"acid scans plus violet mirrored pair, separated","held":[],"split_only":true,"one_family":false,"crossfade_needs_dip":true},
{"id":"pink-pyro","name":"Pink Pyro","family":"pyro","A":"#c33661","B":"#85063f","W":"#ffe1e6","beam":{"A":"#ff5c9a","B":"#da1a6d"},"led":{"A":"#ff004e","B":"#ff0072","W":"#ffffff"},"led_level":{"W":0.94},"sections":["endshow climax","finale variant"],"scene":"B ground, A","lasers":["A"],"fx":{"shockwave":"A","particles":"A","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","W"]},"burst":["A","W"],"hero":"bright pink to white gradient fan","held":["B"],"split_only":false,"one_family":true,"crossfade_needs_dip":false},
{"id":"magenta-classics","name":"Magenta Classics","family":"pyro","A":"#ff1fb4","B":"#19e3ff","W":"#ffffff","beam":{"A":"#fb30b3","B":"#2ad4ed"},"led":{"A":"#ff00aa","B":"#00e0ff","W":"#ffffff"},"sections":["classics","euphoric climax"],"scene":"A","lasers":["B","A"],"fx":{"shockwave":"B","particles":"A","flash":"W"},"strobe":{"triple":["A","B","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"mirror split: magenta left, cyan right (they grey where dim halos overlap)","held":[],"split_only":true,"one_family":false,"crossfade_needs_dip":false},
{"id":"cathedral-jewel","name":"Cathedral Jewel","family":"worship","A":"#860b5e","B":"#41397b","W":"#f9e5c5","line":"#8e7165","beam":{"A":"#d11a95","B":"#7656f9"},"led":{"A":"#ff00ac","B":"#1f00ff","W":"#ffffff"},"led_level":{"W":0.93},"sections":["worship verse","melodic break","Rose Window"],"scene":"A+B glass, line","lasers":["W"],"fx":{"shockwave":"W","particles":"line","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["A","W"]},"burst":["W"],"hero":"none in worship; in hardstyle: warm-white crown","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"brass-break","name":"Brass Break","family":"worship","A":"#8e7165","B":"#543a28","W":"#f9e5c5","beam":{"A":"#8e7165","B":"#543a28"},"led":{"A":"#ffffff","B":"#ffffff","W":"#ffffff"},"led_level":{"A":0.57,"B":0.37,"W":0.93},"sections":["melodic break","quiet state","piano"],"scene":"A+B metal","lasers":["W"],"fx":{"shockwave":"W","particles":"W","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["W","W"]},"burst":["W"],"hero":"none","held":[],"split_only":false,"one_family":true,"crossfade_needs_dip":true},
{"id":"sanctuary-gold","name":"Sanctuary Gold","family":"worship","A":"#f2b84b","B":"#3346c8","W":"#fff6e0","beam":{"A":"#f2b125","B":"#4c67f9"},"led":{"A":"#ffffff","B":"#0021ff","W":"#ffffff"},"led_level":{"A":0.85,"W":0.97},"sections":["worship chorus (major key)","uplift"],"scene":"B ground, A light","lasers":["A"],"fx":{"shockwave":"W","particles":"A","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","W"]},"burst":["A","W"],"hero":"gold crown","held":[],"split_only":true,"one_family":false,"crossfade_needs_dip":true},
{"id":"bone-line","name":"Bone & Gold Line","family":"line","A":"#dbcab5","B":"#bfae9f","W":"#f9e5c5","beam":{"A":"#dbcab5","B":"#bfae9f"},"led":{"A":"#ffffff","B":"#ffffff","W":"#ffffff"},"led_level":{"A":0.85,"B":0.76,"W":0.93},"sections":["intro","anti-climax piano","Sigil"],"scene":"A+B line","lasers":["W"],"fx":{"shockwave":"W","particles":"W","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["A","W"]},"burst":["W"],"hero":"none","held":[],"split_only":false,"one_family":true,"crossfade_needs_dip":true}
],
"fader_order":["bone-line","void-ritual","red-tribe","red-blades","molten","fire-and-ice","golden-wings","sanctuary-gold","acid-screech","laser-green","blue-raw","night-sea","temple-light","celestial-violet","uv-euphoria","violet-rose","magenta-classics","pink-pyro","cathedral-jewel","brass-break","limbo","custom"],
"families":{"ritual":{"anti":"void-ritual","climax":"red-tribe","drop2":"red-blades","break":"brass-break"},"fire":{"anti":"void-ritual","climax":"molten","drop2":"fire-and-ice","break":"golden-wings","finale":"molten"},"celestial":{"anti":"celestial-violet","climax":"violet-rose","drop2":"uv-euphoria","break":"temple-light"},"night":{"anti":"blue-raw","climax":"night-sea","drop2":"uv-euphoria","break":"limbo"},"green":{"anti":"acid-screech","climax":"laser-green","drop2":"laser-green","break":"night-sea"},"pyro":{"anti":"void-ritual","climax":"pink-pyro","drop2":"magenta-classics","break":"violet-rose"},"worship":{"quiet":"bone-line","verse":"cathedral-jewel","chorus":"sanctuary-gold","bridge":"temple-light","break":"brass-break"},"line":{"intro":"bone-line","break":"limbo"}},
"camelot":{"8":{"keys":"C / Am","house_hue":200,"family":"night"},"9":{"keys":"G / Em","house_hue":230,"family":"night"},"10":{"keys":"D / Bm","house_hue":260,"family":"night"},"11":{"keys":"A / F#m","house_hue":290,"family":"celestial"},"12":{"keys":"E / C#m","house_hue":320,"family":"celestial"},"1":{"keys":"B / G#m","house_hue":350,"family":"pyro"},"2":{"keys":"F# / D#m","house_hue":20,"family":"ritual"},"3":{"keys":"Db / Bbm","house_hue":50,"family":"ritual"},"4":{"keys":"Ab / Fm","house_hue":80,"family":"fire"},"5":{"keys":"Eb / Cm","house_hue":110,"family":"fire"},"6":{"keys":"Bb / Gm","house_hue":140,"family":"green"},"7":{"keys":"F / Dm","house_hue":170,"family":"green"}},
"mode":{"major":{"dL":0.05,"chroma":1.1,"hue_nudge_deg":10,"toward":"yellow"},"minor":{"dL":-0.05,"chroma":0.9,"hue_nudge_deg":10,"toward":"blue"},"cap_deg":15},
"rules":{"burst":{"max_families":2,"plus":"white-hot cores","patterns":["mono A+W","alternate A/B in one fan (not split_only)","mirror split A|B","gradient A->B along the OKLCH short arc (hue gap <= 80)","white centre beam, coloured sides","sequence by hit: A, B, W"],"deal":"hit seed from the variety engine; never the same colour mode 3 hits running","hero":"1 in 6-8, or the second press inside a bar, or the drop one; adds only colours on the A->B arc","secret":"one full-spectrum fan per set, at the biggest drop, thin beams, <= 2 beats","bright_max_beats":1,"tail_settles_to":"the theme laser colour (lasers[0]) within 200 ms","beam_halo_L":[0.58,0.8],"held_colours":"never in any laser pulse: held roles are scene-only (steady light)"},"white":{"cores_groove_pct":[0.05,1.5],"cores_kick_pct":[0.2,6],"flood":"drop one or first kick of a phrase, through FlashGate, at most 1 per 8-bar phrase","build":"saturation drains toward white over the last bar; last beat black","white_content_themes":["temple-light","limbo","bone-line","cathedral-jewel","brass-break"],"in_white_content_themes":"the rationed peak is the first saturated colour, not more white"},"picking":{"hold_min":"1 phrase (8 bars)","commit":"next bar (next phrase line while Theme Lock is on)","fader_rest_ms":150,"key_auto":"song DB key at track start, confirmed by chordsense key (conf >= 0.6, stable 8 bars); manual always wins until the next track","section":"the family playbook picks the theme per section; a returning section returns to its theme","long_drop":"every 16 bars swap which role the lasers use (A<->B) unless the role it would swap to is held; never change theme inside a drop","dip":"a change between themes whose primaries are > 100 deg apart, or flagged crossfade_needs_dip, cuts through black on the beat"},"safety":{"saturated_red":"R/(R+G+B) >= 0.8 on encoded OR linear values (conservative); such colours are held","red_area_change":"< 10% of the frame per 333 ms outside the gate","strobes":"thin beams only; full-frame flashes through the gate","laser_colours":"no colour a laser gate can emit (lasers, strobe, burst roles) is saturated red on encoded or linear values"},"led":"pads get led[role]; '#ffffff' with led_level[role] is white at that level; every non-white stand-in has HLS saturation > 0.5 and hue outside 15-100 degrees"}
}
```

Files are in <session scratchpad>\lasers:
- themes_library_v2.json
- themes_library_v2.compact.json
- build_themes_v2.py
- verify_themes.py
- safety_numbers.py

---

## Research: laser-craft (verbatim)

# Real laser-show craft for the KeyLab VJ rig (research lane, 2026-10-24)

## 0. Bottom line

1. **Pro laser software does what Daniel asked for.** BEYOND keeps one beat counter running all the time. Tap tempo uses the space bar or the BPM label. Backspace re-aligns the beat ("phase") without changing the tempo. "Quantize Clicks" moves late clicks onto the beat. "Hard Beat Sync" makes every beat-based effect read from one metronome, so they cannot drift apart. Effects are timed in beats. There is a step sequencer that turns beams on and off per beat. Alternation across projectors is built in: mirrors, 1-, 4- and 8-beat shifts between projectors, and Q-Shift offsets (DIV/MOD grouping, outside-in or inside-out order). [S1–S6]
2. **The big shows tap.** Pangolin's own detector, PangoBeats, uses aubio, the same library family as our `tempo.py`. Pangolin's docs still say audio detection is not guaranteed and that tapping is the reliable method. [S8, S9]
3. **Tempo and phase are separate problems.** A BPM from the database gives the tempo only. MIDI clock also gives tempo only. Ableton Link and Pioneer's CDJ link also give the beat position: Link through a "quantum" (a cycle length in beats, so bar lines agree), the CDJs by announcing beat 1–4 of the bar plus when the next beat and next bar land. A tap gives both tempo and phase. On ChamSys desks, tapping re-aligns every running effect at once. [S14, S15, S17]
4. **Hardstyle's off-beat bass is the failure to plan for.** Our own receipts show beat_g and beat_w keeping the tempo but locking on the off-beat with a bright bass (F .055 and .044). beat_a pulls toward the strongest nearby onset, so a loud off-beat bass drags it too. In hardstyle the reverse bass sits on that off-beat, so the lasers would fire on the bass instead of the kick. Four taps on the kick fix it, because taps carry phase. [H3]
5. **Late is noticed sooner than early.** The broadcast standard (ITU-R BT.1359) says viewers notice picture-late from about 45 ms, but picture-early only from about 125 ms. So the gates should sit a little early, never late. [S34]
6. **Q-dance's own words: the light operator is the drummer, the laser operator is the saxophonist** who takes occasional solos. [S19] ILDA judges score "quality and variety of laser effects" and "visuals following music" separately [S28]. So variety must never cost sync, and the laser burst stays special because it is a solo, not wallpaper.

## 1. What the rig does today (read-only check)

- **Laser burst** (`vj.js` ~1258–1265): at most 4 at once in the accent overlay (`u_laser[4]`). Each hit takes the next of four origins in turn (bottom-centre, left, right, top).
  - Its envelope is a fixed one-shot: attack 0.012 s, decay 0.9 s (`vj-core.js` EFFECTS.laser). It has no gate.
  - At 150 BPM a 0.9 s decay spans 2.25 beats, so any gate built on it would smear.
- **Overlay trails** (`vj.js` ~1284): keep = exp(−dt/(0.03+0.17·trails)). At trails 0.5, light fades over about 115 ms, which is longer than a 16th-note step at 150 BPM (100 ms).
  - A 16th roll would read as flicker riding on a glow, not a clean strobe. Gates need a short trail while they run.
- **Strobe bars** run free at 2–12 Hz from `strobeRate` (`vj.js` 1302–1304). They are not locked to the beat.
- **BeatClock** (`vj-core.js` 652+) has `phase()`, `nextBeatAt()`, `count`, and a 4 s flywheel with confidence fading.
  - The strip's bar phase is `((beat.count%4)+ph)/4` (`vj.js` 1109). That counts beats the page has fired, not a real downbeat.
  - The engine's `beat` event carries `n`, bpm and conf, but no position in the bar.
- **Pad envelopes** go into strip row 0 (`vj.js` 1107). Multiplying a gate in there gates every scene's laser heads at once (the Cathedral reads it).
- **Laser Cathedral**: 12 heads on the pad grid (3×4), odd and even heads aimed at mirrored foci (scissors), and the foci step on each predicted beat. This is already the best beat grammar in the rig [H2].
- **Taps**: `beathand.py` is complete (median tempo; `tap_grid` locks the lights to 4+ taps; re-seeds after 8; `versus` measures the offset by ear). It is only wired into the `beat` command, not the VJ engine.
  - The Tap button (CC 23) reaches the engine only as a generic `ctl` event.
  - Our FL script maps CC 23 to FL's tap tempo (`fl/device_AuroraKeyLab.py:78,187`), so with FL open every tap also changes FL's tempo. That is a hazard and Daniel's call.

## 2. Techniques from the pros, with sources

**T1. One always-running beat counter, taps averaged.** BEYOND's BPM counter never stops. Tapping sets the average BPM. Backspace re-aligns the beat when the show is slightly ahead or behind. [S1, S2] An option rounds a tapped BPM to a whole number [S12]. Hardstyle tracks are whole-number BPMs, and so are the database values.

**T2. Snap late hits; share one clock.** "Quantize Clicks" holds a slightly mistimed click and runs it on the beat. "Hard Beat Sync" gives every beat-based effect the same value, so effects built over different beat counts cannot shift against each other. "Loop Mode" counts 1-2-3-4 instead of counting forever. [S2, S3]

**T3. Cue trigger modes as gestures.** Toggle; Flash (plays only while held); Flash-Solo (while held, turns off the other cues); Restart. [S2] Hold-to-gate and "solo" (dim the idle beams while the burst plays) come straight from here.

**T4. Effects timed in beats, with these waveforms:** Linear, Accelerate, Decelerate, Ping-Pong, Discrete steps, Random, Custom. A "beat-based On/Off sequence" is a step chase of checkboxes, one per step. "Multi Zone Time Shift" adds a clock or BPM offset per zone. "Zone Chase" moves content through N zones in M steps. [S4]

**T5. Q-Shift, the offset engine for many lasers.**
- A pad's Y axis sets the effect amount; its X axis sets the offset (−100 to +100).
- "Period shift per item": for example 25% per laser makes a 4-beat effect travel across 4 lasers.
- "Per selection" sets how much of the cycle is visible across all lasers at once.
- DIV = pairs or quads act as one laser; MOD = every-other grouping.
- The order of the lasers matters: outside-in or inside-out gives symmetrical delays.
- Tempo ratios: 4/1 (over 4 beats), 4/4 (1 beat), 1/4 (a quarter beat). [S5, S7]

**T6. One-button stagger and mirror.**
- Mirrors: a left/right split, and alternating L-R-L-R.
- Shifts: 1-beat (asymmetric, gives a wave), or symmetric 4- and 8-beat.
- A double-speed button; hard and soft pause; "Lower Fifty" brings the beams down. [S6]

**T7. Lighting desks use the same ideas.**
- grandMA3: Learn (tap) speed masters; a speed scale that multiplies or divides without moving the fader; a BPM master driven by the audio input. [S16]
- grandMA3 MAtricks: Blocks, Groups, Wings (fold the rig into a mirror), Width, Phase from/to, and Shuffle. A shuffle value repeats the same "random" order every time it is reused. [S16]
- ChamSys speed-master sources: Tap, Audio BPM, Audio Beat, DJM BPM, DJ Beat, and Resync beat. Tapping phase-syncs every chase and effect it controls. [S17]
- ChamSys effects: spread across heads, odd/even, forward/reverse/bounce/inside-out, and Rnd. [S17]

**T8. A strobe on a real laser is blanking.** The beam is switched off and on (TTL or analog modulation) [S31]. QuickShow's effects include pulse/flash/strobe, chop, trace, ripple, mirror, double and bounce [S11]. In BEYOND the strobe is the FLASH effect in QuickFX, which has 4 layers [S10].

**T9. Colour is applied per beam or per position.** BEYOND colour effects can follow By Points, X/Y/Z, Radius, Time or Angle, as a gradient or in discrete steps [S4]. That is how multi-colour fans and colour chases are made.

**T10. Variety is chosen, not random.**
- Virtual Laser Jockey changes cues every N beats, in order or random [S9].
- rekordbox lighting crosses banks (COOL, NATURAL, HOT, SUBTLE, WARM, VIVID, CLUB 1, CLUB 2) with moods (HIGH, MID, LOW, classified from tempo, rhythm, kick and density). Strobe is FAST, MIDDLE, SLOW or OFF. [S18]
- Anthony Garcia (Laserface) chooses per section: one colour or several, and whether to change every beat, every half-beat or every four beats. His working question: "What is the best cue that I can put for this part of the song?" [S24]
- Laser Monkey: melodic music gets long, undulating looks that last minutes; bass music gets tight rhythmic layering on snares and bass changes. He reuses trusted cues but avoids one signature style. [S27]
- Laserium laserists improvised live, within a fixed structure [S29].

**T11. Rigs are layered by role.** Laserface San Francisco ran 122 lasers on BEYOND with timecode from the CDJs (through TC Supply), with fast movement and instant colour changes [S25]. At Dreamstate there were 58: 18 audience, 22 aerial, 14 burst [S26].

**T12. What Q-dance has published.**
- Jeroen Winnubst (LaserImage/Sync) was laser designer for Qlimax 2023 and has run Defqon.1 [S22, S23].
- Defqon.1 stage shows are timecoded in Depence, with about 3 h of on-site programming covering lasers, SFX and pyro [S21].
- End shows are built over a week. Schmidt deliberately started hard and early instead of the expected slow build [S20].
- Gap: no Q-dance laser cue list or interview about busking exists in public. The palettes come from the earlier 40-reference brief [H2].

**T13. Sync protocols compared.**
- MIDI clock: tempo only, and BEYOND follows it less precisely than through PangoTalk [S13].
- Link: tempo, beat and phase (bar lines agree through the "quantum") [S14]; BEYOND supports it since 5.5 [S7].
- Pioneer's CDJ link: beat 1–4 of the bar, plus nextBeat, 2ndBeat and nextBar in ms [S15]. This is the closest model to our 250 ms-ahead beat event.
- A vendor guide (low weight) gives the field symptom: the same BPM but still off the beat means the phase needs re-aligning, not the tempo [S36].

**T14. Snare rolls in builds.** The note values halve as the build goes on: quarters, then eighths, then sixteenths. Variants: a roll that stops short at beat 2.4 of the bar; a "military" roll with rests; a roll with a velocity ramp. [S33] DJ mixers' TRANS effect is a gate on beat fractions from 1/16 to 16 beats [S32]. The DJ world already uses tempo-synced gates.

**T15. The flash rules (WCAG 2.3.1).**
- A "general flash" counts only above an area threshold: a quarter of a 10° field (the 341×256 px reference at 1024×768).
- Changes to or from saturated red count as a flash in their own right.
- Thin beams pass, but their haze halo adds area. [S35]

**T16. The timing tolerance (ITU-R BT.1359).** Detectable from +45 ms (sound first) to −125 ms (sound late); acceptable from +90 to −185 ms. [S34] Applied to light on music, this is my inference: keep the lasers slightly early.

## 3. Timing, translated to the rig

**How fast drift ruins a gate.** At 150 BPM a beat is 400 ms.
- 1 BPM wrong (0.67%) drifts 2.7 ms per beat. It is visibly late (45 ms) after about 17 beats, around 4 bars.
- 3 BPM wrong drifts 8 ms per beat and is late after about 6 beats.
- 16th rolls die first: half a step is 50 ms.
- An octave error (75 instead of 150) drops every other kick.
- An off-beat lock is the worst. The lights look rhythmic, but they ride the reverse bass, so nothing corrects them.

**Proposals** (my design, from the techniques above):
1. **Tempo from the database, phase from the tracker, the hand overrides both.**
   - An isolated Tap (none in the last 2 s) re-aligns the beat to the nearest beat and keeps the tempo. This is BEYOND's Backspace or ChamSys's "Resync beat": one press.
   - 4 or more steady taps put the lights on the taps for tempo and phase (`beathand.tap_grid`, LOCK_TAPS=4). If the tapped tempo is within 0.5 BPM of a whole number, or within 1% of the database BPM, it snaps to that value.
   - 8 taps at a different octave re-seed the tracker (this already exists).
2. **The beat event learns the bar.** Add `bar` (1–4) and `src` (db, track or tap) to the beat event, like the CDJs. Proposal: the first tap of a run is "the ONE". Daniel should confirm he naturally starts tapping on beat 1.
3. **A half-beat flip** for the off-beat lock, on a screen button or Metronome, not a double-tap. A double-tap would read as 240 BPM in FL.
4. **Show the beat on the hardware.** Blink the Tap LED (id 4) on each predicted beat, brighter on the ONE, the way a console's tap key or BEYOND's metronome icon does.
5. **One clock for every gate.** Compute every gate from `BeatClock.phase()` each frame, with no timers per effect. When the clock re-aligns, every gate re-aligns with it.
6. **Snap hits to the grid.** The first pulse fires on the hit; the rest land on the grid. A hit up to about 60 ms before a predicted beat waits for the beat (my numbers).
7. **A confidence ladder.**
   - conf ≥ 0.6: all gates.
   - 0.3–0.6: nothing faster than ½ beat.
   - Flywheel: beat hits and free shapes only.
   - No clock: shapes timed in seconds at the last tapped tempo.
   - This is what a laserist does: stop subdividing when unsure.
8. **Lean early.** Keep the lasers 0–20 ms early. Tune `offset_ms` by ear using `beathand.versus`.
9. **Frame floor.** No pulse shorter than 3 frames. At 60 Hz the fastest usable division is ⅛ beat (50 ms at 150 BPM) up to about 180 BPM; above that, ¼ beat.
10. **Gates bring their own envelopes.** Each pulse decays over ⅛–¼ beat (not the fixed 0.9 s), and the overlay trail drops below about ⅛ of the pulse period while a gate runs.

## 4. Pattern catalogue (26)

Notation: b = one beat. Divisions: ½b = 8th note (200 ms at 150 BPM); ¼b = 16th (100 ms); ⅛b = 32nd (50 ms); ⅓b = 8th triplet; ⅙b = 16th triplet.
Head sets: the overlay has 4 origins today; the Cathedral has 12 (3 rows × 4); the Rose Window plan has 4 floor, 4 truss and 2 per tower.

| # | Pattern | What it looks like | Timing | Where in hardstyle |
|---|---|---|---|---|
| 1 | Hot Beam | One tight beam from one head, fixed aim, cutting black | Hold 1–4 b or gated | Intro, anti-climax, screech |
| 2 | Fan Burst (pad 2 today) | 3–12 beams open from one head; velocity sets count and spread | Opens in ⅛b, decays over 1–2 b (tie to tempo) | Drop accents |
| 3 | Breathing Fan | The fan's spread opens and closes back and forth | 1 cycle per 2 b (groove) or per bar (break) | Groove drop, melodic |
| 4 | Scanner Sweep | A fan or beam sweeps side to side, easing out at each kick | 1 sweep per b, ½b in the climax | Drop |
| 5 | False Ceiling | A dense fan reads as a flat sheet above the crowd line; drops a step each bar | Step per bar | Melodic break into the build [S30] |
| 6 | Liquid Sky | A sheet with a slow travelling ripple through the haze, no gates | 1 ripple per bar | Break, worship piano [S30] |
| 7 | Tunnel | Beams on a circle meeting at a vanishing point at the hero; spin doubles with the roll | Spin per bar, then ½ bar, then 1 b | Build |
| 8 | Crown | 12–24 even, mirrored beams rise from behind the hero | Opens on the ONE, holds 4–8 b | Drop, climax [H2] |
| 9 | Starburst | Beams all the way round the hero, full count for a moment, then thinning | Once, on the drop's ONE | Drop ONE only |
| 10 | Scissors | Mirrored pairs cross and uncross; the aim points step on each kick (existing grammar) | 1 step per b | Groove, anti-climax |
| 11 | X Through the Hero | Two beams from opposite floor corners cross at the hero | Hold 2–4 b | Drop entry [H2] |
| 12 | Converge | Every head aims at the hero; the spread narrows each bar | 1 step per bar | Build |
| 13 | Bloom | The converged beams snap outward | On the ONE, ⅛b snap | Drop ONE |
| 14 | Cage | Two crossing families of parallel beams, angular; rotates at bar lines | Steps per bar | Anti-climax (the dark ritual) |
| 15 | Zigzag | A beam jumps between two angles on discrete steps | ½b or ¼b | Screech |
| 16 | Ladder | Horizontal rungs stack one per step, then clear | 1 b, then ½b in the last bars | Build |
| 17 | Rain | Vertical beams from the top heads, a random head each step, soft fall | ½b | Melodic break, outro |
| 18 | Ping-Pong L/R | Left heads, then right heads, alternately | 1 b or ½b | Drop groove [S6] |
| 19 | Domino Wave | A left-to-right ripple across every head within one beat (the 1-beat shift) | N steps across 1 b | Drop, fills [S6] |
| 20 | Wings | Mirror pairs fire together, outside-in then inside-out (DIV 2) | ¼b per pair | Climax [S5, S16] |
| 21 | Centre-Out | The centre pair first, then outward: beams radiate from the hero | ¼b per ring | Drop ONE, climax [H2] |
| 22 | Odd/Even Swap | Odd heads on the beat, even heads on the off-beat | ½b alternation | Drop groove (kick against reverse bass) [S17] |
| 23 | Row Climb | Cathedral rows bottom, middle, top, then all three | 1 b per row | Last bars of the build |
| 24 | Rotor | The firing head walks round a ring centred on the hero | 1 head per ¼b, one turn per bar | Euphoric melody, climax |
| 25 | Phase Wave | Every head runs the same sweep, each offset by 1/N of the cycle (Q-Shift 25% for 4 heads) | Cycle 4 b, offset per head | Melodic drop [S5] |
| 26 | Seeded Sparkle | A random head each step, from a shuffle that repeats per phrase | ¼b | Screech, top of the climax [S16] |

## 5. Rhythmic gates (12)

Pulse = beam on, then a fast decay. ms values are at 150 BPM.

| # | Gate | What it looks like | Timing | Where |
|---|---|---|---|---|
| G1 | Kick Hit | One sharp pulse on every beat with a short tail | On at 0, pulse ⅛b (50 ms), tail 150–300 ms | Groove drop, on the kick |
| G2 | One-Two Flicker | Two quick blinks, then dark. Variant: a different head or colour on each blink | On ⅛b, off ⅛b, on ⅛b (150 ms total) | On the kick in the drop, every beat or every other beat |
| G3 | Triple Strobe | Three blinks. Variant "Triplet Triple": blinks at 0, ⅓b, ⅔b | Pulses at 0, ¼b, ½b, each ⅛b long (250 ms total) | Fill on beat 4 of every 4th bar; screech hits |
| G4 | Reverse-Bass Gate | Lights on the "and", cut before the next kick: a hard cut for raw, a 30–40 ms release for euphoric | On ½b → ⅞b | Drop, under the kicks [H2] |
| G5 | Push-Pull | Side A on the kick, side B on the bass: the galloping two-sided pulse | Sides alternate every ½b | Main drop groove (pairs with patterns 18 and 22) |
| G6 | Eighth Roll | Steady blinking | Pulse every ½b, 50% duty | Build stage 2 |
| G7 | Sixteenth Roll | Fast blinking, thin beams only | Pulse every ¼b (10 per s) | Last 2–4 bars of the build |
| G8 | Doubling Roll | Accelerates with the snare, then one beat of black | 1 b, then ½b, then ¼b over 8+4+4 bars; dark on the last beat | The whole build [S33] |
| G9 | Stop-Short | A 16th roll that dies early, leaving dark until the drop | Cuts at beat 2.4 of the last bar | Surprise drop entry [S33] |
| G10 | Military Roll | A 16th grid with rests, e.g. `x.xx x.x. xx.x x...`, seeded variants | ¼b grid | Anti-climax screech patterns [S33] |
| G11 | Bar Marker | Fires only on the ONE (or every 4 bars) with a long tail | Bar or 4-bar | Breaks, worship piano, rests in long drops |
| G12 | Inhale | Ramps up through the beat (Accelerate waveform), cut at the next beat | Ramp 0 → 1 b, hard cut | Pre-drop; euphoric bass [S4] |

## 6. Strong colour themes and multi-colour bursts

**Themes** use the measured Q-dance palettes [H2]. Beams use only the bright key, accent and flash columns, never the ground colours.
1. **Void Ritual (P1):** held beams in red #ab0a1c, never gated; gates in bone #bfae9f; ember #d9534d.
2. **Celestial (P2):** #5435d9, magenta #860b5e, periwinkle #696fc2; peak in cool white #d2d1e5.
3. **Molten (P3):** #d63b09 → #ea7720, gold #fec141, warm white #fff3d6. Finale.
4. **Cathedral Jewel (P4):** beams in warm white #f9e5c5 over #860b5e and #41397b glass.
5. **Laser Green (P5):** #05d987 and #72ba4f, with one magenta pin #c33661.
6. **RED Tribe (P6):** held red #db0001, gold #e89029/#efbc62 bursts, white #fbfcfc, cyan #0adbef as the counter colour.
7. **Night Sea (P7):** #0155bc, #1592d9, #1cbde6.
8. **Pink Pyro (P8):** #85063f, #c33661, #d3797e.
9. **Brass Break (P9):** #8e7165, glint #f9e5c5. Piano.
10. **Ice Crown:** cool white plus #1cbde6. White beams bursting from the rose [H2]. This combination is my own, not measured.

**Multi-colour burst modes** (BEYOND colour by points or by angle [S4]):
- Split Pair: beams alternate A and B.
- Mirror Halves: left side A, right side B.
- Gradient Fan: A to B across the fan; a full rainbow only as a rare treat.
- Hot Core: white in the centre, theme colour at the edges.
- Colour Chase: the colour moves one beam per ¼b or ½b.
- One-Two Flip: blink 1 in A, blink 2 in B.
- Trinity Triple: the three blinks in A, B, then white.
- Bar Swap: the sides swap colours on each bar line.

**Rules:**
- Two colour families per section; white is the peak.
- Red is held, never flashed (WCAG treats red transitions as flashes) [S35, H1].
- Themes change on phrase lines (8 or 16 bars), never mid-bar.

## 7. Variety without chaos, through simple combos

**Choosing:**
- Combinations: 26 patterns × 12 gates × 8 colour modes × 10 themes × head orders (L→R, ping-pong, wings, centre-out, odd/even, rows, rotor, seeded).
- Change one of these per bar line; change all of them together only on the drop's ONE.
- No pattern+gate pair repeats within its last 4 uses; seeded shuffles make the "random" repeatable [S16, H1].

**Sections:**
- Anti-climax: 1–2 heads, Hot Beam, Cage or Zigzag, Military Roll, one hue, mostly black.
- Build: Converge, Tunnel or Ladder; Doubling Roll; colour drains toward white; dark on the last beat.
- Drop: Bloom or Starburst on the ONE, then Crown or X with Push-Pull, two hues plus a white peak.
- Break: Ceiling or Liquid Sky with Bar Markers only. [H2, S27]

**Saxophonist budget** [S19]: gated laser solos fill at most about 2 bars of every 8 in a drop. The rest of the time the idle beams step on the kick, which is the Cathedral's grammar today.

**Interface proposal** (Daniel's call):
- **Tap pad 2:** a burst in the current pattern, gate and colour. Velocity keeps its meaning (beam count and spread).
- **Hold pad 2:** the gate runs while held, like BEYOND's Flash mode, and stops at the next step boundary. The idle beams dip to about 30% while it plays, like Flash-Solo [S2].
- **Default is AUTO:** gate and order follow the detected section, so a plain tap still varies.
- **Two detented knobs:** Gate (12 plus AUTO) and Order (8 plus AUTO).
- **Theme:** one knob or the bank buttons.
- **Combos:** pad 2 with pad 1 = the drop-ONE combo (Starburst then Crown). Pad 2 with pad 5 = the laser strobe (thin gated beams instead of a full-frame strobe).

## 8. Safety for gated lasers

- Only thin beams. While a gate is faster than 3 per second, gate the beam core fully but let the haze halo move by no more than 30%.
- At most 4 heads lit at once during rolls.
- Never gate red.
- Rolls of ¼b or faster: up to 4 bars, in builds only; elsewhere up to 2 bars, then rest.
- No sweeps across the whole frame.
- The final-frame limiter stays the backstop [S35, H1].

## 9. Gaps

- No published Q-dance laser cue list or busking interview (Winnubst's pages are profiles only).
- BEYOND's QuickFX and Live Control pages do not list their effect names.
- Our chosen PDF fetches of the QuickShow manual and the Qlimax lasershow page failed.
- "Laser Monkey" and the Laserface articles describe programmed shows, not busking.
- Hardstyle mapping rows (G4 hard cut against soft release, G5) rest on the house brief and are not confirmed by a laserist.
- CC 23 as Tap is inferred from Arturia's map and our FL script. It has not been confirmed on the hardware.

## Sources

- S1 Pangolin wiki, BEYOND Music and Beats overview: https://wiki.pangolin.com/doku.php?id=beyond:music_and_beats_overview
- S2 Pangolin wiki, Grid Toolbar: https://wiki.pangolin.com/doku.php?id=beyond%3Agrid_toolbar
- S3 Pangolin forum, BPM sync options (developer ENOT): https://forums.pangolin.com/threads/bpm-sync-options.1775/
- S4 Pangolin wiki, Using Effects in BEYOND: https://wiki.pangolin.com/doku.php?id=beyond%3Aeffects
- S5 Pangolin wiki, Q-Shift: https://wiki.pangolin.com/doku.php?id=beyond:qshift
- S6 Laserworld, Learning BEYOND ch. 4: https://www.laserworld.com/en/product-related-faq/pangolin-beyond/2044-learning-pangolin-beyond-universe-chapter-4-controls-tools.html
- S7 Pangolin, BEYOND & QuickShow 5.5: https://pangolin.com/blogs/news/beyond-and-quickshow-5-5-release
- S8 PangoBeats docs: https://wiki.pangolin.com/doku.php?id=pangobeat%3Amanual
- S9 Pangolin wiki, Virtual Laser Jockey: https://wiki.pangolin.com/doku.php?id=beyond%3Avirtual_laser_jockey
- S10 Pangolin QuickFX: https://wiki.pangolin.com/beyond:quickfx and https://forums.pangolin.com/threads/help-to-effect-to-flash-laser-like-a-strobe.22258/
- S11 Pangolin QuickShow: https://pangolin.com/pages/quickshow
- S12 Pangolin wiki, Configuration: https://wiki.pangolin.com/doku.php?id=beyond%3Aconfiguration_dialog_box
- S13 Beat Link Trigger, BEYOND Essentials: https://blt-guide.deepsymmetry.org/beat-link-trigger/7.3.0/Integration_BeyondEssentials.html
- S14 Ableton Link: https://ableton.github.io/link/
- S15 Deep Symmetry, DJ Link beats: https://djl-analysis.deepsymmetry.org/djl-analysis/beats.html
- S16 grandMA3 Speed Masters and MAtricks: https://help.malighting.com/grandMA3/2.5/HTML/masters_speed.html and https://help.malighting.com/grandMA3/2.3/HTML/matricks.html
- S17 ChamSys busking, speed masters and FX engine: https://docs.chamsys.co.uk/magicq/1.9.9.x/manual/busking.html , https://www.manualslib.com/manual/855941/Chamsys-Magicq.html?page=122 , https://docs.chamsys.co.uk/magicq/1.9.9.x/manual/FX_engine.html
- S18 rekordbox 7.0.7 Lighting guide: https://cdn.rekordbox.com/files/20241216130922/rekordbox7.0.7_lighting_operation_guide_EN.pdf
- S19 Festileaks, Jonas Schmidt: https://festileaks.com/2022/01/jonas-schmidt-is-show-creator-bij-q-dance-in-essentie-speel-ik-met-de-emotie-van-80-000-man/
- S20 Hard News, end shows: https://hardnews.nl/en/the-bosses-of-q-dance-and-sensation-about-end-shows/
- S21 Syncronorm, Defqon.1 Depence: https://www.syncronorm.com/newsitem/defqon1-depence
- S22 Syncronorm, Qlimax 2023: https://www.syncronorm.com/newsitem/qlimax-2023-interview
- S23 Grand Finale, Jeroen Winnubst: https://grandfinale.nl/jeroen-winnubst
- S24 Festival Squad, Anthony Garcia: https://festivalsquad.com/2019/10/behind-the-scenes-of-laserface-with-creator-and-mastermind-anthony-garcia-exclusive-interview/
- S25 PLSN, Laserface San Francisco: https://plsn.com/articles/features/gareth-emery-brings-laserface-to-san-francisco/
- S26 Pangolin, Laserface Dreamstate: https://pangolin.com/blogs/news/gareth-emerys-laserface-at-dreamstate-socal
- S27 The Daily Frequency, Laser Monkey: https://thedailyfrequency.com/interviews/laser-monkey-on-laser-design/
- S28 ILDA judging: https://www.ilda.com/awards_judging.htm
- S29 ILDA, the Laserium laserist: https://www.ilda.com/thomas.htm
- S30 Pangolin, types of laser shows: https://pangolin.com/blogs/news/types-of-laser-shows
- S31 Laserworld glossary: https://www.laserworld.com/en/glossary.html
- S32 Pioneer DJM-V10 Beat FX: https://www.manualslib.com/manual/2442166/Pioneer-Dj-Djm-V10-Lf.html?page=60
- S33 Attack Magazine, 10 snare rolls: https://www.attackmagazine.com/technique/tutorials/10-snare-rolls-for-the-drop/
- S34 ITU-R BT.1359-1: https://www.itu.int/dms_pubrec/itu-r/rec/bt/R-REC-BT.1359-1-199811-I!!PDF-E.pdf
- S35 WCAG 2.1, SC 2.3.1: https://www.w3.org/WAI/WCAG21/Understanding/three-flashes-or-below-threshold.html
- S36 Starshine Lights sync guide (vendor, low weight): https://www.starshinelights.com/blogs/news/laser-show-synchronization-guide
- H1 E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\vj-festival-lessons-2026-10-24.md
- H2 E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\vj-headline-qdance-brief-2026-10-24.md (palettes P1–P9, Rose Window, hardstyle anatomy)
- H3 E:\AI-Setup\research\reviewed\keylab-liberation-2026-10-22\grid-tracker-scoring-2026-10-22.md (lines 28, 179) and grid-research-deepseek-lenses-2026-10-22.md (line 522): off-beat lock
- Code read: E:\AI-Setup\arsenal\web\vj.js (95–151, 1107–1109, 1258–1304), vj-core.js (EFFECTS, BeatClock 652+), vj-fx.js, presets\vj-laser-cathedral.frag, arsenal\keylab\vj.py (beat contract, lines 20 and 116), beathand.py, tempo.py, fl\device_AuroraKeyLab.py (CC 23 → FL tap tempo)

No files written. The scratch folder holds only an extracted copy of the rekordbox PDF: <session scratchpad>\lasers\rb-lighting.pdf and rb.txt.

---

## Research: colour-themes (verbatim)

I've built a library of 21 colour themes in 8 families. Every theme has screen colours, stand-in colours for the KeyLab pads, how the scene, lasers and effects use it, and its colours for the triple strobe and the one-two flicker. There are also rules for picking themes live and for multi-colour bursts.

I checked every colour three ways: against the repo's own test for colours that wash out on the pads (`tests/test_keylab_w0.py`), against the saturated-red flash rule, and for muddy greys on screen. 22 of the 63 screen colours would wash out or turn grey on the pads, and every stand-in passes that test. Seven colours count as saturated red, so they are "held": shown steadily, never strobed. Three pairs turn grey when blended. Nothing in the repo, the KeyLab or the 8793/8794 servers was touched.

## What the big shows do with colour

- **Two colours per section, held for a whole phrase.**
  - Q-dance holds one or two hue families per section for 8–17 s at a time, about one 8-bar phrase at 150 BPM. Most reference frames show 1–2 families (house Q-dance study, measured).
  - Ed Warren uses two colours at once at most [H, house lessons file]. Steve Lieberman's lighting follows the DJ's video colours: "If they're in blue, we'll stay in the blue shades" [H, Harman].
  - Knife Party run almost the whole set in red, and Carnage allows at most four colours [H, VICE].
- **The anti-climax and the drop look like different worlds.**
  - Q-dance's anti-climax is one hue in near-black, mostly red; the climax is a pair plus a short white peak; the night ends in orange and warm white (study).
  - Rick Jacobs keeps breaks desaturated or black and white, and drops neon [H, Resolume blog].
- **How screen and lasers pair** (Q-dance references):
  - red screen with blue-violet lasers;
  - green screen with green lasers;
  - orange flames with blue beams;
  - when the beams carry the frame, the screen goes dark or matches them (Q24: green lasers, screen almost off, one magenta pin).
- **White is rationed.** Red is held and white or gold carries the flash. A full-frame white flood comes only on the peak hit.
- **Colour that follows the music.** Palmer et al. 2013 (PNAS, PMC3670360) [H]: fast, major-key music gets lighter, more saturated, yellower colours; slow, minor-key music gets darker, greyer, bluer ones (correlations 0.89–0.99). DJs mix in key on the Camelot wheel, where neighbouring keys share 6 of 7 notes [M, Mixed In Key]. If the key picks the colour, a harmonically mixed set walks the colour wheel in small steps.
- **Laser colour.** Pangolin's manual says white is the most important laser colour and orange is a common problem colour [H]. Green looks about 5–7× brighter than red or blue at the same power [M, vendor pages]. On screen the same problem shows up: next to cyan or green, blue beams vanish.
- **Thin evidence:** Excision, Prydz, Anyma and Afterlife. Their pages I could fetch say nothing about colour.
  - Afterlife's identity words are "limbo / twilight" (Sentimente Studio).
  - Tomorrowland 2026 names one emotion per province but no colours [M].

## Checks against the gamut and safety rules

- **KeyLab pads.** A colour washes to near-white when its HLS hue is 15–100° or its HLS saturation is 0.5 or less (the repo's test rule). 22 of 63 colours do: every gold, orange, bone, brass and warm white, plus the lime, the periwinkle and the indigo glass.
  - Each gets a stand-in: gold and orange become red-orange (7–10°) or soft white, bone and brass become white at their own lightness, and lime becomes pure green.
  - All stand-ins pass the test rule. They are provisional until the measured LED gamut table (probe W0 d) exists.
- **Muddy greys on screen.**
  - A straight 50/50 blend of display values (what the page's set crossfade does) turns three pairs grey: Acid Screech (chroma 0.009, #798082), Sanctuary Gold (0.028) and Fire & Ice (0.056).
  - Dim, overlapping beam halos lose colour in Acid Screech (31% kept), Sanctuary Gold (47%) and Magenta Classics (52%). These are marked `split_only`: their two colours never share a laser fan.
  - Bone and brass are only allowed as thin lines or metal, never as fills.
- **Beam brightness.** The primary and secondary colours range from OKLab lightness 0.33 to 0.97. The JSON `beam` values hold beam halos between 0.58 and 0.80, so blue beams are not lost and cyan, green and acid beams do not swamp the others.
- **Saturated red, R/(R+G+B) ≥ 0.8.** The WCAG 2.2 text doesn't say whether to use encoded or linear values, so I flag a colour if either test catches it.
  - Encoded values catch #ab0a1c and #db0001.
  - Linear values also catch #d63b09, #ea7720, #ff1a3c and #85063f.
  - All seven are held: they never join a strobe, a flicker or a fast colour swap, and red area changes stay under 10% of the frame per 333 ms.
  - I excluded the red-against-green pairing (D14), because red–green is the most common colour-vision deficiency [L].

## The theme library

Roles: A = primary, B = secondary, W = accent or white-hot. "held" = a saturated-red colour; *held* = caught by the linear test only. Pads = the LED stand-ins.

| # | Theme (family) | A / B / W (screen) | Pads A / B / W | Where it fits | Echoes | Scene · lasers · effects |
|---|---|---|---|---|---|---|
| 1 | Void Ritual (ritual) | #ab0a1c held / #bfae9f / #fff3d6 | #ff001d / #c2c2c2 / #f6f6f6 | anti-climax, intro, mid-outro | P1; Q13, Q19 | one thin red symbol, ≥85% black · 1–2 bone or warm-white beams · bone ring, warm-white flash |
| 2 | RED Tribe (ritual) | #db0001 held / #e89029 / #fbfcfc | #ff0001 / #c8c8c8 / #fdfdfd | climax, drop | P6; D05, D06 | red held on hero and panels · gold and white mirrored pairs · gold embers, white strobe |
| 3 | Red Wall, Blue Blades (ritual) | #db0001 held / #4b3cff / #ffffff | #ff0001 / #1400ff / #ffffff | climax, 2nd drop, raw | Q-dance red screen + blue-violet lasers | red scene · blue-violet beams only · white flash |
| 4 | Molten (fire) | #d63b09 *held* / #fec141 / #fff3d6 | #ff2000 / #d0d0d0 / #f6f6f6 | finale, endshow | P3; Q07, Q09, D05 | fire ramp with no brown, black between flames · gold crown, white cores · embers |
| 5 | Golden Wings (fire) | #e89029 / #5435d9 / #f9e5c5 | #ff2a00 / #3000ff / #ededed | build, euphoric climax | your saved warm look "Golden wings" + the brief's gold-with-violet pairing | violet ground, gold light · gold beams, violet never in the same fan |
| 6 | Fire & Ice (fire) | #ea7720 *held* / #2f6bff / #ffffff | #ff2800 / #004aff / #ffffff | climax, 2nd drop | D07, Q02 | orange scene · cobalt beams · hero burst is a mirror split; crossfades dip to black |
| 7 | Celestial Violet (celestial) | #5435d9 / #860b5e / #d2d1e5 | #3000ff / #ff00ac / #dddddd | opener, reveal | P2; Q01, Q11, Q20 | violet hero · violet or cool-white beams · magenta ring |
| 8 | Violet & Rose (celestial) | #7a3cff / #ff3d8b / #fff0f6 | #5100ff / #ff0067 / #f7f7f7 | euphoric climax, signature | your "purple and beautiful!" save; Q08, Q10 | violet with rose rims · rose beams, violet pairs on the second press |
| 9 | UV Euphoria (celestial) | #6a00ff / #00e5ff / #ffffff | #6a00ff / #00e5ff / #ffffff | euphoric, uptempo | Defqon.1 UV stage = euphoric | UV body · thin cyan beams |
| 10 | Night Sea (night) | #0155bc / #1cbde6 / #e8f8ff | #0030ff / #00e5ff / #f7f7f7 | build, dusk, laser sea | P7; D13 | deep-blue sheet · cyan beams and sheets |
| 11 | Temple of Light (night) | #696fc2 / #172580 / #f4f3ff | #8080ff / #0022ff / #f7f7f7 | euphoric break, worship chorus | Q05 (Qlimax 2017 white temple) | periwinkle on deep blue · white beams in mirrored diagonals |
| 12 | BLUE Raw (night) | #0adbef / #1a2cff / #ffffff | #00e9ff / #0014ff / #ffffff | raw anti-climax, screech | Defqon.1 BLUE = raw; #0adbef | cyan lines · fast cyan scans, blue fans on the drop |
| 13 | Limbo (night) | #eef4ff / #4fa8ff / #ff1a3c *held* pin | #f6f6f6 / #0081ff / #ff0026 | break, worship into hardstyle | Afterlife "limbo" [M]; Jacobs | white linework, red pin under 2% · thin white beams with ice halos |
| 14 | Laser Green (green) | #05d987 / #72ba4f / #c33661 | #00ff9c / #20ff20 / #ff004e | groove, beam section | P5; Q24, Q06, D02 | screen nearly off (teal haze), one magenta pin · green beams |
| 15 | Acid Screech (green) | #a8ff24 / #4a00e0 / #ffffff | #22ff00 / #5400ff / #ffffff | screech anti-climax, raw drop | study: screeches in acid green | violet glow, acid under 5% of the frame · acid scans, violet fans; split-only |
| 16 | Pink Pyro (pyro) | #c33661 / #85063f *held* / #ffe1e6 | #ff004e / #ff0072 / #efefef | endshow climax | P8; D08, D12 | pink bursts · bright pink beams · comet particles |
| 17 | Magenta Classics (pyro) | #ff1fb4 / #19e3ff / #ffffff | #ff00aa / #00e0ff / #ffffff | classics, euphoric | Defqon.1 MAGENTA = classics | magenta scene · cyan beams; split-only, so the two colours are mirrored |
| 18 | Cathedral Jewel (worship) | #860b5e / #41397b / #f9e5c5, bronze line #8e7165 | #ff00ac / #1f00ff / #ededed | worship verse, melodic break | P4; Q16, Q17, Q21 | jewel glass with bronze lead lines · warm-white beams from behind the hero · no strobe |
| 19 | Brass Break (worship) | #8e7165 / #543a28 / #f9e5c5 | #929292 / #5f5f5f / #ededed | melodic break, quiet, piano | P9; Q25 | still metal under one travelling light · white on the pads by design |
| 20 | Sanctuary Gold (worship) | #f2b84b / #3346c8 / #fff6e0 | #d8d8d8 / #0021ff / #f8f8f8 | worship chorus in major keys | Palmer 2013; "finales go warm" | blue ground, gold light · gold beams; split-only |
| 21 | Bone & Gold Line (line) | #dbcab5 / #bfae9f / #f9e5c5 | #d8d8d8 / #c2c2c2 / #ededed | intro, piano anti-climax, Sigil scene | Qlimax bone linework; Q14 | 2–3 px linework only · one warm-white beam at most |

## Picking themes live

1. **Theme fader.** One fader walks all 21 themes in colour-wheel order (`fader_order`), with a detent for each.
   - A theme is chosen once the fader rests for 150 ms, and it lands on the next bar (next phrase if Quantize is lit).
   - Proposal: fader 1 (today Hue A, CC 105) becomes Theme and fader 2 becomes Hue drift (±15°, centre detent). Today's free Hue A/B pair stays available as "Custom".
2. **Family tabs.** The 8 screen buttons (CC 45–52 and LED ids 21–28, both inferred), each lit in its family's pad colour.
   - First press: the family's theme for the current section.
   - Second press inside a bar: the next theme in that family (your "the second press is a question" idea).
   - Caveat: FL's stock script uses these CCs, so our own FL script must not pass them on.
3. **Dial.** Scrolls the whole library, with name, swatches and a pad preview on the LCD. Long-press Save locks the theme.
4. **Key auto.**
   - The Camelot number (shared key signature) picks the family, using the house pitch hue of the relative major's tonic. Relative major and minor therefore share a family.
   - The mode nudges the colours: major +0.05 lightness, chroma ×1.1, hue +10° toward yellow; minor the opposite. Cap ±15°.
   - Key source order: the song database key at track start, then chordsense's key event (confidence ≥ 0.6, stable for 8 bars). Your manual pick wins until the next track.
   - GetSongBPM returns `key_of` and `open_key` [M, API docs via search]; AcousticBrainz has a tonal key [L, not checked]. `tempo.py` reads only tempo today, so this needs a small addition.
5. **Sections.**
   - Each family has a playbook: anti-climax, climax, second drop and break themes. When a section comes back, its theme comes back (Schiller).
   - A theme holds at least one phrase.
   - In a long drop, swap which colour the lasers use every 16 bars (unless that colour is held). Never change the theme inside a drop.
   - Changes between themes more than 100° apart, or flagged `crossfade_needs_dip`, cut through black on the beat.

## Multi-colour bursts, strobe colours and white

- **At most two hue families per burst, plus white-hot cores.** Only colours in the theme's `burst` list may join, and held colours never join a strobe, flicker or fast colour swap.
- **Patterns, dealt by the per-hit random seed:**
  - one colour plus white cores;
  - A and B alternating within one fan (not for split-only themes);
  - mirror split, A left and B right;
  - a gradient fan from A to B (only when they are within 80°);
  - a white centre beam with coloured sides;
  - a sequence by hit: A, then B, then white.
- **Hero burst.** One hit in 6–8, the second press inside a bar, or the first beat of the drop. It may add only colours between A and B on the colour wheel.
- **The set's secret.** One full-spectrum fan per set, saved for the biggest drop (Warren held his rainbow lasers for the drop cut). Thin beams, at most 2 beats.
- **Timing.** The bright part lasts at most one beat (400 ms at 150 BPM). Tails fade back to the theme's laser colour within 200 ms: the head is multi-colour, the tail is the theme.
- **Strobe colours.**
  - Your triple strobe uses `strobe.triple`, usually two coloured flashes and a white third one as the payoff.
  - The one-two flicker uses `strobe.flicker`.
  - When lasers alternate, the heads swap sides on each flick.
  - All of it stays as thin beams.
- **White budget.**
  - Cores 0.05–1.5% of the frame in the groove, 0.2–6% on a kick.
  - A full-frame flood only on the drop one, through the flash gate, at most once per 8-bar phrase.
  - Builds drain toward white in the last bar, then one beat of black.
  - In white-content themes (Temple, Limbo, Bone, Cathedral, Brass) the rationed peak is the first saturated colour instead.

## What I found in the code (read-only, not changed)

1. **The kick glow adds a third colour.** It uses the complement of Hue A (`vj.js` ~1354, palette stop 4), so every hit adds another family. In theme mode it should use A or W.
2. **Chord colour breaks the two-colour rule.** At its default of 0.7, chord colour blends four chord-tone colours into the palette (`vj.js` 849–857, 1073–1074). That can put up to four families on screen in hardstyle. Cap it to a ±15° nudge there and leave it free for piano.
3. **The laser has only one colour per burst.** Laser colour is the pad's own colour (`putCol`), so pad 2 always fires stop 1 (Hue B), and the overlay has one colour per burst (`u_laserCol`). Alternating and mirrored bursts need a second colour per burst.
4. **Pads are sent screen colours.** The pads are posted the screen colours (`padCol`), so gold themes would wash out. The LED stand-ins should go only to `/api/pads`.
5. **The Choke pad shows near-white.** Its colour #ff9a1f (hue 36°) is in the wash zone (`vj-core.js` 375).
6. **Set crossfades turn some pairs grey.** They blend display values, which greys out complementary pairs. Palette changes already turn through OKLCH (`oklabMix`) and stay colourful (chroma 0.13–0.20 for the same pairs).

## Gaps

- The LED stand-ins are rule-of-thumb until probe W0 d is run with you at the keyboard.
- WCAG doesn't say whether the red test uses linear or encoded values.
- No primary source on colour for Excision, Prydz, Anyma or Afterlife.
- Tomorrowland is trade press only [M].
- I fetched Warren's interview today and got a 403, so it rests on the earlier house verification.
- Nothing is rendered in the real scenes yet. The swatch sheet is a flat mock-up on black.

## Sources

- Earlier research in the repo: `research/reviewed/keylab-liberation-2026-10-22/vj-headline-qdance-brief-2026-10-24.md` (palettes P1–P9, the measured pairs) and `vj-festival-lessons-2026-10-24.md` (Warren, Schiller, the safety standards).
- Palmer et al. 2013: https://pmc.ncbi.nlm.nih.gov/articles/PMC3670360/
- Steve Lieberman: https://pro.harman.com/insights/entertainment/touring/electrifying-the-edm-environment-with-lighting-and-stage-designer-steve-lieberman/ and https://www.vice.com/en/article/steve-lieberman-ultra-music-festival-lighting-interview/
- Rick Jacobs: https://resolume.com/blog/14343
- Pangolin colour settings: https://wiki.pangolin.com/doku.php?id=beyond:advanced_color_settings
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
- Camelot wheel: https://mixedinkey.com/camelot-wheel/
- GetSongBPM API: https://getsongbpm.com/api
- Afterlife identity: https://www.sentimentestudio.com/work/afterlife/
- Tomorrowland 2026: https://www.creativeboom.com/news/tomorrowland-2026s-stunning-designs-highlight-what-creativity-can-add-in-a-sea-of-samey-festivals/
- Green laser brightness: https://pointerclicker.com/green-red-laser/

## JSON

```json
{"version":1,"roles":{"A":"primary","B":"secondary","W":"accent/white-hot"},"themes":[
{"id":"void-ritual","name":"Void Ritual","family":"ritual","A":"#ab0a1c","B":"#bfae9f","W":"#fff3d6","ground":"#351015","led":{"A":"#ff001d","B":"#c2c2c2","W":"#f6f6f6"},"beam":{"A":"#e01c2c","B":"#bfae9f"},"sections":["anti-climax","intro","mid-outro"],"use":{"scene":"A","lasers":"B,W","shockwave":"B","particles":"B","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["B","W"]},"burst":["B","W"],"hero":"none (anti-climax stays one family)","held":["A"],"split_only":false,"one_family":true,"crossfade_needs_dip":false},
{"id":"red-tribe","name":"RED Tribe","family":"ritual","A":"#db0001","B":"#e89029","W":"#fbfcfc","ground":"#520a1e","led":{"A":"#ff0001","B":"#c8c8c8","W":"#fdfdfd"},"beam":{"A":"#e11c14","B":"#e89029"},"sections":["climax","drop"],"use":{"scene":"A","lasers":"B,W","shockwave":"B","particles":"B","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["B","W"]},"burst":["B","W"],"hero":"gold-to-white gradient fan","held":["A"],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"red-blades","name":"Red Wall, Blue Blades","family":"ritual","A":"#db0001","B":"#4b3cff","W":"#ffffff","led":{"A":"#ff0001","B":"#1400ff","W":"#ffffff"},"beam":{"A":"#e11c14","B":"#5b63f9"},"sections":["climax","second drop","raw anti-climax"],"use":{"scene":"A","lasers":"B","shockwave":"B","particles":"W","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["B","W"]},"burst":["B","W"],"hero":"blue-violet to violet gradient (never red beams in the burst)","held":["A"],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"molten","name":"Molten","family":"fire","A":"#d63b09","B":"#fec141","W":"#fff3d6","ground":"#510a05","led":{"A":"#ff2000","B":"#d0d0d0","W":"#f6f6f6"},"beam":{"A":"#d43f13","B":"#f0b225"},"sections":["finale","climax","endshow"],"use":{"scene":"A>B ramp","lasers":"B,W","shockwave":"B","particles":"A","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["B","W"]},"burst":["A","B","W"],"hero":"ember to gold to white gradient","held":["A"],"split_only":false,"one_family":true,"crossfade_needs_dip":false},
{"id":"golden-wings","name":"Golden Wings","family":"fire","A":"#e89029","B":"#5435d9","W":"#f9e5c5","led":{"A":"#ff2a00","B":"#3000ff","W":"#ededed"},"beam":{"A":"#e89029","B":"#6d5bf9"},"sections":["build","euphoric climax","finale"],"use":{"scene":"B ground, A light","lasers":"A","shockwave":"A","particles":"A","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","W"]},"burst":["A","W"],"hero":"gold fan plus a violet mirrored pair, separated, white crossings","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"fire-and-ice","name":"Fire & Ice","family":"fire","A":"#ea7720","B":"#2f6bff","W":"#ffffff","led":{"A":"#ff2800","B":"#004aff","W":"#ffffff"},"beam":{"A":"#ea7720","B":"#336df9"},"sections":["climax","second drop"],"use":{"scene":"A","lasers":"B","shockwave":"W","particles":"A","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["B","W"]},"burst":["B","W"],"hero":"mirror split: left orange, right cobalt, white where they cross","held":["A"],"split_only":false,"one_family":false,"crossfade_needs_dip":true},
{"id":"celestial-violet","name":"Celestial Violet","family":"celestial","A":"#5435d9","B":"#860b5e","W":"#d2d1e5","led":{"A":"#3000ff","B":"#ff00ac","W":"#dddddd"},"beam":{"A":"#6d5bf9","B":"#d11a95"},"sections":["opener","intro reveal","first groove"],"use":{"scene":"A","lasers":"A,W","shockwave":"B","particles":"W","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"violet to magenta gradient fan","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"violet-rose","name":"Violet & Rose","family":"celestial","A":"#7a3cff","B":"#ff3d8b","W":"#fff0f6","led":{"A":"#5100ff","B":"#ff0067","W":"#f7f7f7"},"beam":{"A":"#7e51f9","B":"#fb468c"},"sections":["euphoric climax","melodic drop","signature"],"use":{"scene":"A, B rims","lasers":"B (A pairs)","shockwave":"B","particles":"A","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"violet to rose gradient fan (the short way round, through magenta)","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"uv-euphoria","name":"UV Euphoria","family":"celestial","A":"#6a00ff","B":"#00e5ff","W":"#ffffff","led":{"A":"#6a00ff","B":"#00e5ff","W":"#ffffff"},"beam":{"A":"#7855f9","B":"#2ad4eb"},"sections":["euphoric climax","uptempo"],"use":{"scene":"A","lasers":"B","shockwave":"B","particles":"W","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"alternate beams UV/cyan","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"night-sea","name":"Night Sea","family":"night","A":"#0155bc","B":"#1cbde6","W":"#e8f8ff","ground":"#051083","led":{"A":"#0030ff","B":"#00e5ff","W":"#f7f7f7"},"beam":{"A":"#1373f1","B":"#25bde5"},"sections":["build","dusk","melodic","laser sea"],"use":{"scene":"A","lasers":"B","shockwave":"B","particles":"W","flash":"W"},"strobe":{"triple":["B","B","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"blue to cyan gradient fan","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"temple-light","name":"Temple of Light","family":"night","A":"#696fc2","B":"#172580","W":"#f4f3ff","led":{"A":"#8080ff","B":"#0022ff","W":"#f7f7f7"},"beam":{"A":"#645ff9","B":"#4769f9"},"sections":["euphoric break","big white peak","worship chorus"],"use":{"scene":"A on B","lasers":"W","shockwave":"A","particles":"W","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["A","W"]},"burst":["A","W"],"hero":"white fan with periwinkle halos","held":[],"split_only":false,"one_family":true,"crossfade_needs_dip":false},
{"id":"blue-raw","name":"BLUE Raw","family":"night","A":"#0adbef","B":"#1a2cff","W":"#ffffff","led":{"A":"#00e9ff","B":"#0014ff","W":"#ffffff"},"beam":{"A":"#2bd5e7","B":"#3d6bf9"},"sections":["raw anti-climax","screech","rawstyle drop"],"use":{"scene":"A","lasers":"A (B fans)","shockwave":"A","particles":"W","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"alternate beams cyan/blue","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"limbo","name":"Limbo","family":"night","A":"#eef4ff","B":"#4fa8ff","W":"#ff1a3c","led":{"A":"#f6f6f6","B":"#0081ff","W":"#ff0026"},"beam":{"A":"#eef4ff","B":"#55a8fb"},"sections":["break","anti-climax (melodic)","worship into hardstyle"],"use":{"scene":"A (W pin)","lasers":"A","shockwave":"B","particles":"A","flash":"white"},"strobe":{"triple":["A","A","A"],"flicker":["A","B"]},"burst":["A","B"],"hero":"none (break register)","held":["W"],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"laser-green","name":"Laser Green","family":"green","A":"#05d987","B":"#72ba4f","W":"#c33661","ground":"#054343","led":{"A":"#00ff9c","B":"#20ff20","W":"#ff004e"},"beam":{"A":"#29d889","B":"#72ba4f"},"sections":["groove","climax","beam section"],"use":{"scene":"ground (W pin)","lasers":"A (B)","shockwave":"A","particles":"A","flash":"white"},"strobe":{"triple":["A","A","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"green fan plus the magenta pin as one centre beam","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"acid-screech","name":"Acid Screech","family":"green","A":"#a8ff24","B":"#4a00e0","W":"#ffffff","led":{"A":"#22ff00","B":"#5400ff","W":"#ffffff"},"beam":{"A":"#8ed726","B":"#685df9"},"sections":["anti-climax screech","raw drop"],"use":{"scene":"B","lasers":"A scans, B fans","shockwave":"B","particles":"A","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","B"]},"burst":["A","W"],"hero":"acid scans plus violet mirrored pair, separated","held":[],"split_only":true,"one_family":false,"crossfade_needs_dip":true},
{"id":"pink-pyro","name":"Pink Pyro","family":"pyro","A":"#c33661","B":"#85063f","W":"#ffe1e6","led":{"A":"#ff004e","B":"#ff0072","W":"#efefef"},"beam":{"A":"#db1b64","B":"#da1a6d"},"sections":["endshow climax","finale variant"],"use":{"scene":"B ground, A","lasers":"A","shockwave":"A","particles":"A","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","W"]},"burst":["A","B","W"],"hero":"deep to bright pink gradient","held":["B"],"split_only":false,"one_family":true,"crossfade_needs_dip":false},
{"id":"magenta-classics","name":"Magenta Classics","family":"pyro","A":"#ff1fb4","B":"#19e3ff","W":"#ffffff","led":{"A":"#ff00aa","B":"#00e0ff","W":"#ffffff"},"beam":{"A":"#fb30b3","B":"#2ad4ed"},"sections":["classics","euphoric climax"],"use":{"scene":"A","lasers":"B (A pairs)","shockwave":"B","particles":"A","flash":"W"},"strobe":{"triple":["A","B","W"],"flicker":["A","B"]},"burst":["A","B","W"],"hero":"mirror split: magenta left, cyan right (they grey where dim halos overlap)","held":[],"split_only":true,"one_family":false,"crossfade_needs_dip":false},
{"id":"cathedral-jewel","name":"Cathedral Jewel","family":"worship","A":"#860b5e","B":"#41397b","W":"#f9e5c5","line":"#8e7165","led":{"A":"#ff00ac","B":"#1f00ff","W":"#ededed"},"beam":{"A":"#d11a95","B":"#7656f9"},"sections":["worship verse","melodic break","Rose Window"],"use":{"scene":"A+B glass, line","lasers":"W","shockwave":"W","particles":"line","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["A","W"]},"burst":["W"],"hero":"none in worship; in hardstyle: warm-white crown","held":[],"split_only":false,"one_family":false,"crossfade_needs_dip":false},
{"id":"brass-break","name":"Brass Break","family":"worship","A":"#8e7165","B":"#543a28","W":"#f9e5c5","led":{"A":"#929292","B":"#5f5f5f","W":"#ededed"},"beam":{"A":"#8e7165","B":"#543a28"},"sections":["melodic break","quiet state","piano"],"use":{"scene":"A+B metal","lasers":"W (one)","shockwave":"W","particles":"W","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["W","W"]},"burst":["W"],"hero":"none","held":[],"split_only":false,"one_family":true,"crossfade_needs_dip":true},
{"id":"sanctuary-gold","name":"Sanctuary Gold","family":"worship","A":"#f2b84b","B":"#3346c8","W":"#fff6e0","led":{"A":"#d8d8d8","B":"#0021ff","W":"#f8f8f8"},"beam":{"A":"#f2b125","B":"#4c67f9"},"sections":["worship chorus (major key)","uplift"],"use":{"scene":"B ground, A light","lasers":"A","shockwave":"W","particles":"A","flash":"W"},"strobe":{"triple":["A","A","W"],"flicker":["A","W"]},"burst":["A","W"],"hero":"gold crown","held":[],"split_only":true,"one_family":false,"crossfade_needs_dip":true},
{"id":"bone-line","name":"Bone & Gold Line","family":"line","A":"#dbcab5","B":"#bfae9f","W":"#f9e5c5","led":{"A":"#d8d8d8","B":"#c2c2c2","W":"#ededed"},"beam":{"A":"#dbcab5","B":"#bfae9f"},"sections":["intro","anti-climax piano","Sigil"],"use":{"scene":"A+B line","lasers":"W","shockwave":"W","particles":"W","flash":"W"},"strobe":{"triple":["W","W","W"],"flicker":["A","W"]},"burst":["W"],"hero":"none","held":[],"split_only":false,"one_family":true,"crossfade_needs_dip":true}
],
"fader_order":["bone-line","void-ritual","red-tribe","red-blades","molten","fire-and-ice","golden-wings","sanctuary-gold","acid-screech","laser-green","blue-raw","night-sea","temple-light","celestial-violet","uv-euphoria","violet-rose","magenta-classics","pink-pyro","cathedral-jewel","brass-break","limbo"],
"families":{"ritual":{"anti":"void-ritual","climax":"red-tribe","drop2":"red-blades","break":"brass-break"},"fire":{"anti":"void-ritual","climax":"molten","drop2":"fire-and-ice","break":"golden-wings","finale":"molten"},"celestial":{"anti":"celestial-violet","climax":"violet-rose","drop2":"uv-euphoria","break":"temple-light"},"night":{"anti":"blue-raw","climax":"night-sea","drop2":"uv-euphoria","break":"limbo"},"green":{"anti":"acid-screech","climax":"laser-green","drop2":"laser-green","break":"night-sea"},"pyro":{"anti":"void-ritual","climax":"pink-pyro","drop2":"magenta-classics","break":"violet-rose"},"worship":{"quiet":"bone-line","verse":"cathedral-jewel","chorus":"sanctuary-gold","bridge":"temple-light","break":"brass-break"},"line":{"intro":"bone-line","break":"limbo"}},
"camelot":{"8":{"keys":"C / Am","house_hue":200,"family":"night"},"9":{"keys":"G / Em","house_hue":230,"family":"night"},"10":{"keys":"D / Bm","house_hue":260,"family":"night"},"11":{"keys":"A / F#m","house_hue":290,"family":"celestial"},"12":{"keys":"E / C#m","house_hue":320,"family":"celestial"},"1":{"keys":"B / G#m","house_hue":350,"family":"pyro"},"2":{"keys":"F# / D#m","house_hue":20,"family":"ritual"},"3":{"keys":"Db / Bbm","house_hue":50,"family":"ritual"},"4":{"keys":"Ab / Fm","house_hue":80,"family":"fire"},"5":{"keys":"Eb / Cm","house_hue":110,"family":"fire"},"6":{"keys":"Bb / Gm","house_hue":140,"family":"green"},"7":{"keys":"F / Dm","house_hue":170,"family":"green"}},
"mode":{"major":{"dL":0.05,"chroma":1.1,"hue_nudge_deg":10,"toward":"yellow"},"minor":{"dL":-0.05,"chroma":0.9,"hue_nudge_deg":10,"toward":"blue"},"cap_deg":15},
"rules":{"burst":{"max_families":2,"plus":"white-hot cores","patterns":["mono A+W","alternate A/B in one fan (not split_only)","mirror split A|B","gradient A->B along the OKLCH short arc (hue gap <= 80)","white centre beam, coloured sides","sequence by hit: A, B, W"],"deal":"hit seed from the variety engine; never the same pattern 3 times running","hero":"1 in 6-8, or the second press inside a bar, or the drop one; adds only colours on the A->B arc","secret":"one full-spectrum fan per set, at the biggest drop, thin beams, <= 2 beats","bright_max_beats":1,"tail_settles_to":"the theme laser colour (use.lasers) within 200 ms","beam_halo_L":[0.58,0.8],"held_colours":"never in a strobe, flicker or fast alternation"},"white":{"cores_groove_pct":[0.05,1.5],"cores_kick_pct":[0.2,6],"flood":"drop one or first kick of a phrase, through FlashGate, at most 1 per 8-bar phrase","build":"saturation drains toward white over the last bar; last beat black","white_content_themes":["temple-light","limbo","bone-line","cathedral-jewel","brass-break"],"in_white_content_themes":"the rationed peak is the first saturated colour, not more white"},"picking":{"hold_min":"1 phrase (8 bars)","commit":"next bar (next phrase with Quantize lit)","fader_rest_ms":150,"key_auto":"song DB key at track start, confirmed by chordsense key (conf >= 0.6, stable 8 bars); manual always wins until the next track","section":"the family playbook picks the theme per section; a returning section returns to its theme","long_drop":"every 16 bars swap which role the lasers use (A<->B) unless the role it would swap to is held; never change theme inside a drop","dip":"a change between themes whose primaries are > 100 deg apart, or flagged crossfade_needs_dip, cuts through black on the beat"},"safety":{"saturated_red":"R/(R+G+B) >= 0.8 on encoded OR linear values (conservative); such colours are held","red_area_change":"< 10% of the frame per 333 ms outside the gate","strobes":"thin beams only; full-frame flashes through the gate"}}}
```

Files are in <session scratchpad>\lasers:
- themes_library.json
- themes_library.compact.json
- themes_checked.json
- themes_swatches.png
- themes_data.py
- themes_calc.py
- themes_build.py
