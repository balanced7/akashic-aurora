# Virtual Stage v1.1: the Headhunterz Show 8:51 animation modes, measured (2026-10-25)

Workflow run wf_410244fc-7e7 (task wqib4zg41). Daniel sent a frame of the Qlimax 2014 Headhunterz Show at 8:51 and wrote, verbatim: "This looks sick, can we add these animation modes too?" One study lane measured that span (8:28-9:27) against the soundtrack and wrote a build-ready spec in the stage's own data format (arsenal.arena/v1). The footage and frames are other people's footage and stay private (state/arsenal/refs/qlimax2014/, scratch); nothing here embeds them. Verbatim; local paths shortened to <scratch>.

Vandor's read: the study corrected three of my readings of the frame -- the "warm fan" is a crown of amber heads aimed down and inward at the DJ (a converging tent the eye reads as an upward fan); the white sparkles spin slowly clockwise (about 3.7 degrees a beat); and 8:51 sits in a break, so the rain snaps in on the ONE after a pickup rather than pulsing with a kick. The spec is queued as Stage v1.1, built after Stage v1 (workflow stage-v1-phrases) lands.

---

## The study and spec (verbatim)

I've measured all four modes Daniel's frame shows, and three of my readings differ from Vandor's notes. The warm fan is a ring of amber heads aimed down and inward at the DJ, not beams bursting upward. The white sparkles slowly spin clockwise around the ring. The 8:51 moment sits in a break with no kick, so the rain, sparkles, fan and lanterns do not lock to the beat. The spec for the five modes follows. No repo edits or commits. I didn't touch the KeyLab, MIDI, the three ports or the GPU, and opened no browser. Every grab stays in scratch.

Grades: [H] = measured by me in this lane, [M] = from the earlier study or press, [L] = my inference or a starting value.

## Method
- **Footage:** native 23.976 fps grabs (`py -m arsenal.media grab`):
  - 508–568 s at 480 px wide;
  - 528.5–541.5 s at 960 px;
  - a full-resolution crop of the 8:51 shot (530.7–533.2 s);
  - full-resolution stills at 528.9, 529.8, 530.3, 530.55, 531.0, 538.3, 538.7 and 539.1 s.
- **Beat grid:** librosa beats from the earlier study's demuxed soundtrack, 143.6 BPM (0.418 s per beat) [H].
  - Bars are anchored on the drop: beat 113 at 542.674 s is a downbeat, so downbeats are the beats numbered 1 (mod 4).
  - Two pickup-plus-hit pairs at beats 80/81 and 96/97 confirm it [H].
  - Daniel's frame (531.0 s) sits 0.09 s before downbeat 85 [H].
- **Beam detection:** thin coloured beams lose saturation in this compressed video, so a hue mask found nothing.
  - I detected them on the opponent channel 2G−B−R, top-hat filtered, then fitted line segments (Hough).
  - I tested whether the beams are parallel with a least-squares vanishing-point fit.
- **Small-point motion:** I removed camera motion using a median-blurred base layer (slats and speakers), then matched points frame to frame.

## The span, 8:28–9:27 [H audio and picture]

| Time | Beats | What happens |
|---|---|---|
| 8:24–8:30 | 21–35 | Dip, near silence |
| 8:30.6–8:36 | 36–49 | One hit, about 3 bars of kick, stage fountains |
| 8:36.6–8:49.0 | 50–80 | Break with no kick, held red: ring with sparkles, red lanterns, wide fanned pale beams ("ember fan"). Shots of the stage truss in amber at 8:46–8:48 |
| 8:49.0 / 8:49.4 | 80 / 81 | Pickup, then a hit on the ONE: colour steps to violet and the strand beams snap to a thin parallel rain |
| 8:49.4–8:55.6 | 81–95 | Violet rain break; Daniel's 8:51 frame is here |
| 8:55.6 / 8:56.1 | 96 / 97 | Pickup and hit; a crowd shot covers beats 97–100 |
| 8:57.7–8:59.4 | 101–104 | Pink walks to red at 6.4° of hue per beat |
| 8:59.2–9:00.9 | 105–108 | Lime 16th-note stutter |
| 9:01.0–9:02.6 | 109–112 | Gold/white flood |
| 9:02.67 | 113 | Drop: kick on every beat to 9:27 (one dropped kick at beat 160); white flashes on the off-beat |

Daniel's frame by the earlier study's metrics [H]:
- 3.7% lit, 22% true black, 88% at luma ≤ 25.
- Saturated lit pixels: violet 53%, magenta 41%.
- Haze #2c005e (OKLCh 0.257 / 0.141 / 295). The thin lime and amber are too desaturated to register as colour families.

## Measurements

### 1. Strand rake (the "rain")
- **Parallel in 3D [H].** In both close shots, all strand beams converge on one vanishing point, median residual 4.7–5.1° over 29 and 35 frames.
  - That point sits above the frame, toward the stage. So the beams point down and toward the back of the hall, out over the crowd.
  - The wide side shot (8:51) shows two angle families, about 105–110° and 141–146° in the image (90° = straight down), residual 8–13°.
  - I read those two families as perspective of one parallel set across rungs at different heights and depths [L].
  - 3D tilt is not calibrated. Use the earlier study's 55–70° below horizontal for the head rows [M].
- **Count [H, 2 frames].** About 4 beams under the nearest rung, in two pairs, roots under the rails between the lanterns (8:51 and 530.3).
  - That fits the earlier study's 4 heads per rung [M].
  - In the wide shots, 54–85 beam segments are visible per frame.
- **No sweep in the break [H].**
  - Median angle 63–65° for 1.2 s.
  - Vanishing point IQR 11–19 px at 960 px wide.
  - In the side shot, each angle family holds within ±2° over 2.4 s.
- **Snap on the ONE [H].** At 529.334 → 529.376 → 529.418 s (beat 81 is 529.415 s), the segment count goes 13 → 42 → 54 and the lime share 0.46 → 2.4%.
  - Beam width at half maximum narrows from 5–8 px to 3 px (at 960 px wide).
  - The angle spread collapses from 26–114° (wide fan) to 46–84° (parallel).
  - The rain lands on the kick's attack, about 1/10 beat before librosa's beat.
- **No beat lock in the break [H].** Lime share by eighth of a beat varies only 1.04–1.27× (max/min) across four shots. The drop's lime rows at 7:00 were 4.6× [M].
- **Build stutter [H].** From beat 104.7 to 108.9:
  - 1-frame flashes, contrast up to about 90× (4.69% vs 0.05%);
  - 2–3 frames apart, mean 117 ms, which is consistent with 16ths (104 ms). At 24 fps it could alias a faster rate.
- **Colour [H].** On camera, the median beam pixel is #aba879 (OKLCh 0.72 / 0.064 / 105) and cores are #eae2aa (0.91 / 0.073 / 101).
  - The washed-out reading is probably colour subsampling of 1–2 px lines [L].
  - The light itself is lime per ref-18 [M].
- **Reach [H, 6 beams].** The beams run to the crowd; brightness at the crowd end is 0.52–0.82 of the root (median about 0.74).
- **One unexplained change [H].** In the side shot the diagonal family's total length rose about 5× over beats 84–87 with no angle change. It could be a staggered fade-in or the camera; I couldn't tell.

### 2. Ring sparkle
- **Count [H].** 186 sparkles at 8:51 on the visible ring at full resolution; side-shot median 199 (IQR 194–209).
  - Point-like: median area 6 px, 90th percentile 17 px.
  - Peak colour #efb5ff (0.85 / 0.118 / 319); 68% clip a channel.
- **Placement [H].** Sparkles sit on the ring's bands, tracing the spiral arcs. The band bodies are otherwise dark, and the radial slats behind carry the theme colour.
- **Twinkle [H, 3 shots].**
  - On-run median 3 frames (125 ms, about 0.3 beat); 90th percentile 6–8 frames.
  - Autocorrelation 0.71–0.78 at a lag of 1 frame and 0.01–0.22 at 4 frames.
  - Each point is lit 18–20% of the time.
- **Random, not a chase [H].** Count by eighth of a beat stays within ±5%; count varies only 4–8% within a shot.
- **Spin, a new finding [H].** The whole sparkle field turns clockwise as seen from the audience.
  - Median 8.8°/s (IQR 4.4–13.3), about 3.7° per beat. 94% of 9,529 matched point pairs agree.
  - The ring's structure moves 1.5°/s or less, which is camera motion.
  - The pink close shot, 7 s later, shows the same clockwise flow.
  - An outward drift of 0.12 radii/s may be an artefact of my ellipse fit [L].
- **Where it runs [H].** Present in the red, violet, pink and gold sections and in the drop.

### 3. Warm fan (the "crown")
- **Geometry [H].** Amber heads sit on an arc around the ring's eye. The arc's radius is about 0.32–0.35 of the outer ring's radius (two frames).
  - 14 lenses are visible on about 210° of arc (some hidden behind the speakers), roughly 11° apart.
  - I estimate 20–24 in total, on an arc of about 240° that is open at the bottom [L].
- **Direction [H].** The hot ends (lenses) are at the top and the beams point down and inward.
  - Left-side beams run at 62–74° in the image, right-side ones at 102–110°.
  - They converge about 0.6 arc radius below the arc's centre, toward the DJ.
  - The eye reads this converging tent as a fan bursting upward.
- **Colour [H].** Lens cores #ffe1bc (0.93 / 0.059 / 73), beam bodies #ffcc70 (0.87 / 0.124 / 81). The fan stays amber in the red, violet and pink sections.
- **Motion [H].** Held: one lens holds 68±2° over 1.7 s, and by-eighth variation is 1.08–1.16×.
  - It swells about 70% (0.48 → 0.83% of the frame) over beats 101.6–105.5 in the build.

### 4. Hex lanterns
- **Shape [H].** A polygon fit gives 6–7 vertices.
  - Width/height is 1.63–1.93 from the side (8:51) and 1.1–1.25 from three-quarter views.
  - The 2014 hardware was frosted cubes [M], so these hexagons are probably cubes seen corner-on [L].
- **Colour [H].**
  - Cores at 8:51: #e9aaff, #e59dff, #db95ff (OKLCh L 0.78–0.83, C 0.13–0.16, h 313–317); the brightest is #ffebff.
  - They follow the section's colour: pink cores #ff4d9f / #ff3caf, then red.
  - In their dim phase they read grey-khaki (C 0.07–0.11).
- **Breathing [H, 9 lanterns in 2 shots].**
  - A smooth sine with a 4.0-beat period (min to min 1.67 s); minimum 0.37–0.6 of maximum.
  - Neighbouring lanterns are about 1 beat apart. The rungs nearest the audience peak first, so the wave runs toward the ring [L, 5 lanterns].
  - Change between frames is ≤ about 6%: they never flash.
- **Dot strips [H, by eye only].** Amber dots along the bars, steady.

### 5. Other animations in the span
1. **The ONE snap [H].** The colour step lands between the pickup (beat 80) and the ONE; a cut at 529.21 hides the exact frame. The rain arrives on the ONE.
2. **Phrase colour plan [H].**
   - red held 8 bars → violet held 4+ bars (hue steady within 2°);
   - the pink→red walk in the build's second bar;
   - red stutter bar;
   - gold flood bar (54–71% lit);
   - drop.
3. **Build stutter [H].** As measured under 1.
4. **Drop off-beat white blasts [H, 480 px frames].** 32 events, mostly 1–2 frames.
   - Median phase 0.42 beat after the beat; they come in runs one beat apart.
   - Each covers 13–38% of the frame. This confirms the earlier study's ¼–⅜ beat [M].
5. **Crown swell [H].** As measured under 3.

## Build spec for v1.1 (in `arsenal.arena/v1` terms, against v0 `sets/source-v0.json`)

### New code this needs
Each item is flagged in the data below.
1. **Selector.** Group selectors only match `<object>.*/<type>`, so either use the new type ids below or add a tag filter to the selector.
2. **Aim.** A look value `"Aim": "<focus>"` that works out pan and tilt toward a focus point.
3. **Twinkle.** A waveform `twinkle` with per-cell random onsets, `life` and `duty`, plus a `drift` that rotates the cell lookup around the ring.
4. **Band cells.** A pixel layout `annulus` (`band-mesh`).
5. **Lantern mesh.** A renderer mesh for `hex-lantern`.
6. **Section cues.** Section cues counted back from the section's end, `{"bar": -2, …}`.

```json
"types": {
  "hex-lantern": {"class":"pixel","layout":"hex-prism","cells":6,"size":[1.6,0.9,0.9],"cell_kind":"face","nits":160,
                  "note":"ours: an elongated hexagonal prism, points along the rung (x); reads hex from every angle (measured width/height 1.6-1.9 side-on)"},
  "rake-7r":  {"extends":"beam-7r"},
  "crown-7r": {"extends":"beam-7r"},
  "band-mesh":{"class":"pixel","layout":"annulus","pitch":0.3,"rows":2,"row_gap":0.35,"cell_kind":"dot","cell_size":0.06,"nits":60000}
},
"objects (additions)": [
  {"on":"rung", "children+": [
     {"type":"rake-7r","at":[[-2.9,-0.55,0],[-1.4,-0.55,0],[1.4,-0.55,0],[2.9,-0.55,0]],"rot":[180,0,0]},
     {"type":"hex-lantern","at":[[-4.5,0,0],[4.5,0,0]],"tags":["backbone"],"replaces":"cube-6"}]},
  {"on":"ring", "children+": [{"type":"band-mesh","ring":{"radius":"outer"},"rows_by_ring":[2,2,1,1]}]},
  {"id":"crown","kind":"structure","at":[0,14,-10],"mesh":"procedural:crown-arc-v1",
   "children":[{"type":"crown-7r","repeat":{"count":22,"polar":{"radius":4.6,"step_deg":11.2,"from_deg":-28}}}]}
],
"groups+": {
  "strand.rake":     {"select":"rung.*/rake-7r"},
  "strand.lanterns": {"select":"rung.*/hex-lantern"},
  "rings.band":      {"select":"ring.*/band-mesh"},
  "crown.heads":     {"select":"crown/crown-7r"}
},
"effects+": {
  "lantern-breath": {"attrs":["Dimmer"],"form":"sine","size":0.6,"measure":4,"phase":{"order":"z","from":360,"to":0,"cyclic":true}},
  "ring-sparkle":   {"attrs":["Dimmer"],"form":"twinkle","life":0.3,"duty":0.19,"seed":2014,"size":1,"measure":1,
                     "phase":{"order":"random","from":0,"to":360,"cyclic":true},"drift":{"order":"angle","deg_per_beat":-3.7},"flashRisk":"none"},
  "ember-fan":      {"attrs":["Tilt"],"form":"const","measure":4,"fan":{"order":"x","from":-35,"to":35}},
  "ember-spread":   {"attrs":["Pan"],"form":"const","measure":4,"fan":{"order":"z","from":-20,"to":20}},
  "rain-stutter":   {"attrs":["Dimmer"],"form":"square","width":0.4,"size":1,"measure":0.25,"phase":{"order":"index","from":0,"to":0},"flashRisk":"local"}
},
"looks+": {
  "ember": {"fade":2,"lines":[
    {"group":"strand.rake","values":{"Dimmer":0.75,"Pan":0,"Tilt":15,"Zoom":3.0,"Color":"beamA"},"effects":["ember-fan","ember-spread"]},
    {"group":"strand.heads","values":{"Dimmer":0}},
    {"group":"strand.lanterns","values":{"Dimmer":1,"Color":"A"},"effects":["lantern-breath"]},
    {"group":"strand.dots","values":{"Dimmer":0.8,"Color":"warm"}},
    {"group":"rings.band","values":{"Dimmer":1,"Color":"W"},"effects":["ring-sparkle"]},
    {"group":"rings.slats","values":{"Dimmer":0.8,"Color":"A"}},
    {"group":"rings.rims","values":{"Dimmer":0}},
    {"group":"crown.heads","values":{"Dimmer":0.55,"Aim":"dj","Zoom":4,"Color":"warm"}}]},
  "rain": {"fade":0.1,"lines":[
    {"group":"strand.rake","values":{"Dimmer":1,"Pan":0,"Tilt":28,"Zoom":0.8,"Color":"beamA","mib":"early"}},
    "... every other line as in ember"]},
  "rain-build": {"fade":8,"from":"rain","lines+":[{"group":"crown.heads","values":{"Dimmer":1,"Aim":"dj","Zoom":4,"Color":"warm"}}]},
  "gold-flood": {"fade":0.25,"lines":[{"group":"strand.rake","values":{"Dimmer":1,"Tilt":28,"Zoom":2.5,"Color":"W"}},
                                      {"group":"strand.lanterns","values":{"Dimmer":1,"Color":"W"}},
                                      {"group":"rings.slats","values":{"Dimmer":1,"Color":"A"}}]}
},
"themes+": {
  "rain-red":    {"A":"#cc2c1c","B":"#ff5058","W":"#ffe6e0","beamA":"#b6f22a","beamB":"#ffd0a0","warm":"#ffc46a","ambient":"#690102"},
  "rain-violet": {"A":"#8a48c6","B":"#923895","W":"#f3e6ff","beamA":"#b6f22a","beamB":"#9a66ff","warm":"#ffc46a","ambient":"#2c005e"},
  "rain-rose":   {"A":"#ee2776","B":"#b72938","W":"#ffe0ec","beamA":"#b6f22a","beamB":"#ff9ec4","warm":"#ffc46a","ambient":"#4f001b"},
  "rain-gold":   {"A":"#f0b040","B":"#ffd27a","W":"#fff1c8","beamA":"#fff1c8","beamB":"#ffd27a","warm":"#ffc46a","ambient":"#5a3000"}
},
"cameras.shots+": {
  "RAIN_SIDE":   {"kind":"path","pos_path":[[25,28,66],[22,28,66]],"look_path":[[-2,13,-8],[-3,13,-8]],"hfov":56,"ev":0.2,"source":"footage (Daniel's ref-25): house right, high, along the strand into the ring"},
  "RAIN_CLOSE":  {"kind":"static","pos":[-12,9,40],"look":[-2,15,-8],"hfov":60,"ev":0.3,"source":"footage 8:49-8:50 and 8:58: near rungs upper right, ring left"},
  "RAIN_ACROSS": {"kind":"static","pos":[-34,16,24],"look":[8,17,24],"hfov":50,"ev":0.3,"source":"footage 8:53-8:56: the lantern chain across the hall"}
},
"cameras.sequences+": {"rain":[{"shot":"RAIN_CLOSE","bars":1},{"shot":"RAIN_SIDE","bars":2},{"shot":"RAIN_ACROSS","bars":1},{"shot":"RAIN_CLOSE","bars":2}]},
"show.sections+": {
  "break": {"deck":[{"look":"ember","bars":8,"theme":"rain-red"},{"look":"rain","land":"phrase","theme":"rain-violet"}],"camera":"rain","speed_by_bar":[1]},
  "build": {"look":"rain-build","theme_walk":{"to":"rain-red","from":"rain-rose","deg_per_beat":6.4},
            "cues":[{"bar":-2,"group":"strand.rake","effects":["rain-stutter"]},{"bar":-1,"look":"gold-flood","theme":"rain-gold"}],"camera":"rain"}
}
```

Where each value comes from:
- **Measured [H]:** the 8 + 4 bar deck, the snap on the ONE, the held rain, the ~2× zoom ratio, the 4-beat breath and its 0.4 floor, the twinkle's 0.3-beat life and 0.19 duty, the 3.7°/beat clockwise spin, the crown's arc radius and spacing, its held aim and 8-beat swell, the 16th stutter in the second-to-last bar, the gold last bar, and all the colours.
- **Starting values [L]:** tilt 28° and 15°, zoom 0.8 and 3.0, the fan spreads (±35°, ±20°), and the head x positions.
- **Head count.** The v1.1 strand gets 48 rake heads (4 per rung) plus 22 crown heads, 70 new heads in all.
- **Lantern spread.** One full cycle across 12 rungs puts neighbouring rungs 1/3 beat apart. The `from 360 to 0` order makes the audience end peak first; this direction is [L].
- **Sparkle cells.** About 1,200 band cells at 0.19 duty gives about 230 lit, which matches the 186–250 visible.

**Triggers:**
- The phrase sequencer runs the `break` deck and the `build` cues.
- Pad 7 (NEXT LOOK) advances the deck on the next downbeat, which is the snap.
- Pad 5 (SPARKLE, held) doubles sparkle duty and spin while held and releases over 1 beat [L].
- Pad 9 (BUILD) and pad 10 (DROP NOW) as in the design.
- The drop keeps Source Array's Rose Fans, with the white blast timed at 0.2–0.45 beat after the kick.

**Flash safety:**
- **Rain and crown:** held in breaks. The lime and amber are never red, and halos are never strobed.
- **Stutter:** a unison 16th on dimmers. `governEffect` will floor it at 0.6 by default. Matching the footage's full on/off needs an exception for thin beam cores only, where the governor predicts a swing under 0.09 per window. That is Daniel's call.
- **Sparkle:** decorrelated per cell and ≤ 20 px each, so the total varies under 10% and there is no frame flash. The spin never reverses within a section, and the slats are never spun.
- **Lanterns:** 0.6 Hz with a 0.4 floor; red lanterns breathe but never flash.
- **Off-beat white blasts:** 13–38% of the frame at 2.4 per second, so they go through FlashGate (≤ 3/s) and share that budget.

## Acceptance targets
Measure with the same scripts on 24 fps renders at 143.6 BPM; each reference value from the footage is in brackets.

**Rain**
- R1. Rain in RAIN_CLOSE: line-to-vanishing-point median ≤ 6° (4.7–5.1), point above the frame; ≥ 40 segments per frame (54–80); width ≤ 3.5 px at 960 px wide (3.0); ember width ≥ 5 px (5–8).
- R2. Snap: segments rise ≥ 5× within 2 frames of the ONE (7 → 54); angle 10–90% range ≤ 40° after (46–84).
- R3. Break: angle drift ≤ 2° per 2 beats; vanishing-point IQR ≤ 20 px; lime by eighth of a beat ≤ 1.3× max/min (1.04–1.27).
- R4. Stutter: on/off ≥ 10× at 2–3 frame intervals (90×, 117 ms), or the governed version if that's the call.
- R5. Reach: brightness at the beam end ≥ 0.5 of the root (median 0.74).

**Sparkle**
- S1. Count: 180–280 on the full ring at 1080p (186 / 199); area ≤ 20 px (median 6).
- S2. Twinkle: on-run median 2–4 frames (3); autocorrelation 0.6–0.85 at lag 1 and ≤ 0.25 at lag 4; duty 0.12–0.28 (0.18–0.20).
- S3. No beat lock: by eighth of a beat within ±8%, count variation ≤ 10%.
- S4. Spin: ≥ 85% of matched pairs clockwise (94%), 6–13°/s (8.8).
- S5. Colour: ≥ 90% of sparkles on band cells; peak L ≥ 0.8, C ≤ 0.15.

**Crown**
- W1. 18–24 lenses, 10–13° apart, ≥ 90° open at the bottom.
- W2. Beams meet 0.4–0.8 arc radius below the arc centre (0.6).
- W3. Direction drift ≤ 3° per 4 beats.
- W4. Lens L ≥ 0.9 with hue 60–85; body hue 70–85 with C ≥ 0.1; amber whatever the theme.
- W5. Swell +50–90% over 4 beats (+70%).

**Lanterns**
- L1. Period 4 ± 0.5 beats; min/max 0.35–0.6; neighbours 0.5–1.5 beats apart.
- L2. Side-on width/height 1.6–1.95, 6 ± 1 vertices.
- L3. Core L 0.78–0.96 with C ≤ 0.17 in the theme hue; dim phase C 0.07–0.11.
- L4. ≤ 10% change per frame.

**Colour plan and composition**
- C1. Theme holds per phrase (±3°); steps between the pickup and the ONE; walk 5–8° per beat (6.4); last bar 50–75% lit.
- C2. RAIN_SIDE frame: lit 3–8% (3.7); true black ≥ 20% (22); 80% or more of pixels at luma ≤ 25 (88%); haze OKLCh 0.22–0.30 / ≥ 0.12 / 285–305.

## Daniel's calls
1. **Lantern:** our elongated hex prism, or keep cubes turned 45° (they read as hexagons only from some angles).
2. **Stutter:** true unison 16ths (needs the exception for thin cores), or the governed or chase version.
3. **Sparkle cells:** add the new band cells (about 1,200), or reuse the existing rim strips (no new fixtures, but each ring reads as two thin dotted lines).
4. **Head count:** 70 more heads, 98 in v1.1.
5. **Spin direction:** fixed clockwise as measured, or allowed to change per section (never within one).

## Gaps
- **3D angles:** not calibrated; image angles only.
- **Thin counts:** heads per rung from two frames. The crown's total and its hidden bottom are inferred. The lantern wave direction comes from 5 lanterns.
- **Frame rate:** the stutter rate is subject to 24 fps aliasing.
- **Spin:** measured quantitatively in one shot; the direction is confirmed in two.
- **Hidden bar:** the crowd shot hides bar 97–100.
- **Open question:** the rain's growth over beats 84–87 in the side shot is unexplained.
- **Video colour:** the thin beams' colour on camera is degraded by the video's colour subsampling.

## Files
Everything is in scratch: `<scratch>/stage/v1_1-study/`.
- **Grabs (other people's footage, private):** `gA/`, `gB/`, `gS/`, `full851/`, `full2/`, `sheet2fps/`, about 245 MB.
- **Scripts the judge can reuse:**
  - `beams.py`, `beamstat.py`, `famts.py` (beams);
  - `feat.py`, `phase.py` (per-frame features and beat profiles);
  - `spark.py`, `spark2.py`, `spark3.py`, `spark4.py`, `flowfield.py`, `rot.py` (sparkles);
  - `lant.py`, `lcol.py` (lanterns);
  - `warm.py` (crown);
  - `series.py`, `aud.py`, `mosaic.py`, `overlay.py`, `ov_ang.py`.
- **Data:** `aud_beats.json`, `series_gB.json`, `beams_gA.json`, `beams_gS.json`, `feat_gA.json`, `spark_side.json`.
- **Evidence images:** `ova_side.png`, `ova_close.png`, `ff_side.png`, `ff_pink.png`, `spark_acc_side.png`, `c_fan.png`, `z851_front.png`, `z_warm2.png`, `lens_000538.700.png`.
- **The earlier study's frame metrics** came from `q14spec/measure.py`.

The media toolbox wrote grab receipts under the gitignored `state/arsenal/media/receipts/grab/`. I also recorded a shared lesson, `show-video-thin-beams-and-led-motion`, on how to detect thin beams and remove camera motion before measuring LED points.
