# Instrument layout spec: KeyLab 88 mk3 + five procedural pianos

Research only, 2026-09-15. No models, textures, photos, fonts or logos were downloaded.

How the confidence tags work:
- **[M]** measured: a number published by the manufacturer or a retailer spec sheet, with its source cited.
- **[R]** reported: a reviewer's statement or measurement.
- **[D]** derived: arithmetic on [M] or [R] values, with the working shown.
- **[U]** uncertain: an estimate, a single weak source, or sources that disagree. Never treat a [U] value as measured.

Everything is given in mm. It is also given in **span units (su)**, where 1 su is the width of the host's 88-key row. The TP/110 octave is 165 mm [R, SOS], so one white key is 165/7 = 23.57 mm and 52 white keys = **1225.7 mm = 1 su** [D]. An instrument that is handed `framing` and the key span from `keyX(21)..keyX(108)` can scale every number below by `span / 1225.7`.

---

## 1. Arturia KeyLab 88 mk3 (Daniel's instrument)

### 1.1 Envelope, mass, action

| Item | Value | Tag / source |
|---|---|---|
| Width | 1295 mm (1.0565 su) | [M] Arturia product page, store page, Thomann |
| Depth | 323 mm (0.2635 su) | [M] same |
| Height | 113 mm (0.0922 su). Whether this includes the feet or the knob tops is unknown | [M] value; [U] reference points |
| Weight | 15.7 kg (34.61 lb) | [M] Arturia. Reviews say "about 16 kg" (Perfect Circuit snippet) and "approximately 15 kg" (MusicTech) |
| Keys | 88, fully weighted, Fatar TP/110 graded hammer action; velocity plus **channel** aftertouch (no polyphonic aftertouch) | [M] Arturia; [R] SOS, synthanatomy |
| White key length | 150 mm front to back (0.1224 su) | [R] SOS measured |
| Octave span | 165 mm | [R] SOS |
| Key dip | about 9 mm | [R] SOS |
| Width left for both end cheeks and margins | 1295 − 1225.7 = **69 mm, about 35 mm per side** | [D] |
| Depth left for the panel behind the keys | 323 − 150 = 173 mm, minus the front rail and the gap behind the keys (neither published): **about 150–160 mm of control panel** | [D] + [U] |
| Height of the key tops above the desk | not published; **80–95 mm estimate** | [U] |

### 1.2 Control inventory (counts are firm)

| Control | Count and spec | Tag / source |
|---|---|---|
| Pitch and mod **wheels** (real wheels, not touch strips) | 2 | [M] Arturia, Thomann. On the 61 and 88 they sit on the top panel. Only the 49 moves them to the left of the keys ([M] KeyLab mk3 manual p.11; [R] synthanatomy) |
| Display | 3.5 in full colour, 480×320 px. At 3:2 that is about **74.0 × 49.3 mm** active area | [M] Arturia, Thomann; size [D] |
| Contextual buttons around the display | 8 | [M] Arturia; manual |
| Main encoder | 1, clickable and notched, **aluminium knob** | [M] Arturia ("1 clickable encoder"); [R] synthanatomy (aluminium), gearnews (notched) |
| Back button | 1 | [M] manual (49/61 manual; same family) |
| Pads | 12, velocity and pressure sensitive, RGB, 4 banks (A–D) | [M] Arturia |
| Pad size | **29 mm square, with translucent edges** | [R] SOS measured |
| Pad arrangement | **2 rows of 6**, from one review ("two rows of pads, one row fewer than mk2"). The 49/61 review may not carry over to the 88 | [U] KVR |
| Encoders | 9 × 360°, touch sensitive; touching one shows its value on screen | [M] Arturia; [R] MusicTech, gearnews |
| Faders | 9, touch sensitive, **50 mm** travel | [M] Arturia (single source for the length) |
| Transport and DAW buttons | **8 transport + 4 command = 12**. Named in reviews: Save, Undo, Redo, Loop, Quantize, Metronome, plus Play/Stop/Record | [M] count, Arturia; names [R] internettattoo, MusicRadar-61, soundgale. Exact full list and order [U] |
| Chord / Scale / Arp / Hold | 4 dedicated buttons | [M] manual (49/61); [R] MusicTech (88: "left panel") |
| Octave +/−, Transpose +/− | 4 | [M] manual |
| Settings, Program (Prog), Bank +/− | 4 | [M] manual; [R] SOS places Prog and Settings "way out west" |
| Part buttons | The manual says the right-side encoders and faders address **Part 1 or Part 2** of a Multi. **No review confirms dedicated physical Part buttons** | [U] |
| Rear panel | USB-C (bus powered), 12 V DC in, 5-pin MIDI In/Out, **4 pedal inputs** (Sustain, Expression, Aux 1, Aux 2), Kensington slot | [M] Arturia; [R] SOS (four inputs), gearnews (Kensington, seen on the 61) |
| Accessories | Slot-in music desk in **metal and perspex**; **metal laptop shelf** with a non-slip rubber top (takes a laptop up to 380 × 250 mm); optional beech wooden legs | [M] Arturia store; [R] SOS |

### 1.3 Top panel, left to right

The **order** of the zones is [R] evidence. The manual's "left side" page lists wheels, Oct/Trans, Bank, Settings/Prog, pads, then MIDI FX and transport. Its "right side" page lists the display, contextual buttons, main encoder, Back, encoders and faders. MusicTech puts the wheels and the Chord/Scale/Arp/Hold buttons on the left panel. MusicTech, gearnews and soundgale all call the screen central. Gearnews has "pads on one side, nine faders with nine pots on the other."

The **x-ranges are [U] estimates** that fit those facts inside the 1295 mm chassis. They are measured from the left outer edge, with the panel depth taken as the 150–160 mm behind the keys.

| Zone | x-range (mm) | Contents | Confidence |
|---|---|---|---|
| Left cheek | 0–35 | Beech end cheek (see 1.4) | width [D]; profile [U] |
| A. Wheels | ~40–120 | Pitch and mod wheels side by side, in a recessed well on the top panel | order [R]; x [U]; wheel diameter **unpublished** |
| B. Global buttons | ~120–240 | Oct −/+, Trans −/+, Prog, Settings, Bank −/+ (small backlit rectangles) | order [R]; x [U] |
| C. Pads + MIDI FX | ~240–500 | 12 pads at 29 mm with ~4 mm gaps (6 × 33 mm = ~198 mm wide, 2 × 33 mm = ~66 mm deep), with Chord/Scale/Arp/Hold beside or above them | pad size [R]; grid [U] |
| D. Transport + command | ~500–600 | 12 buttons, likely 2 rows (soundgale: "arranged in two rows; larger Play/Record/Stop") | [U] placement; the "two rows / larger Play-Rec-Stop" claim is one source |
| E. Display block | ~600–820 | 74 × 49 mm glossy screen near the chassis centre (647 mm); 8 contextual buttons (split around or below the screen), aluminium main encoder and Back to the right. KVR: the **glossy** display section is a "fingerprint magnet" | screen size [D]; position [R] "central"; button split [U] |
| F. Channel strips | ~830–1255 | 9 encoders + 9 × 50 mm faders. About 425 mm / 9 = **~47 mm pitch** if each strip is a knob above a fader. **Unverified** whether it is a knob row behind a fader row or another arrangement | [U] |
| Right cheek | 1260–1295 | Beech end cheek | [D]/[U] |

### 1.4 Materials, colours, finish

- **Chassis material is disputed.** Arturia's own mk3 pages say "high-density plastic, ruggedised knobs and real-wood panelling". Thomann says "robust aluminium housing with wooden side panels". KVR (49/61) says "all-aluminium body". AudioTechnology and MusicRadar (88) say "slick metal case". [U]. At scene scale a **satin-anodised metal-look top panel** (MeshPhysicalMaterial, metalness ~0.6, roughness ~0.45) is indistinguishable from either.
- **End cheeks**: real **beech** wood [R] MusicRadar-61, gearnews ("beech wood end cheeks with sculpted cutouts", PolyBrute-like). They carry an inlaid or embossed brand logo [R]. **Leave it out**: plain wood, with at most a blank shallow recess.
- **Black edition**: matte black body, black controls, **dark-stained wood** cheeks [R] synthanatomy (49/61). For the 88, [U].
- **White edition**: white body with **white controls** [R] soundgale, and **light (natural) wood** cheeks [R] synthanatomy (49/61). For the 88, [U].
- **Orange ("Ultra")** editions exist for the 49/61 with black wooden cheeks [R] gearnews. **None reported for the 88.**
- Keys: standard white and black on both editions [U] (not stated anywhere, but no source mentions otherwise).
- Fader and knob caps: redesigned "non-sticky" caps [R] synthanatomy. Shape and colour are **unpublished** [U].

### 1.5 What lights up (for the reactive layer)

| Element | Behaviour | Tag / source |
|---|---|---|
| 12 pads | **RGB backlit through translucent edges** (29 mm pads, "translucent edges"). Colour per bank or per DAW clip state | [R] SOS; [M] Arturia "RGB pads". One review says the tops are black-painted with only the sides lit, but it may describe the Essential mk3 [U] |
| Transport buttons | "classic, backlit" | [R] synthanatomy |
| Contextual and menu buttons | "a little stripe of LED lighting in the middle", backlit plastic | [U] (review snippet; may be the Essential mk3) |
| Display | Emissive colour LCD (glossy) | [M] |
| Encoders, faders, wheels | **Not lit.** Touch gives on-screen feedback only | [R] MusicTech, gearnews |

**Renderer mapping (proposal, not research).** Pads glow with `noteColor` on strikes (emissive only while reacting, scaled by vel). The display shows our own chord-name canvas texture. Transport buttons stay dim white and brighten only on pedal. The cheeks and panel never glow.

### 1.6 Ask Daniel: ten tape-measure numbers that turn [U] into [M]

He owns the unit, so a two-minute measurement beats any web source.

1. Cheek thickness, and the cheek profile height at the front and at the back.
2. Chassis front edge to the front of the white keys.
3. Desk to white key top; desk to panel surface at the rear edge. Is the panel flat or sloped?
4. x-centre, from the left edge, of: the wheels, the pad block, the screen, the main encoder, the first and last fader.
5. Knob row behind the fader row, or interleaved?
6. Pad grid (6×2?) and the location of the Chord/Scale/Arp/Hold and transport clusters.
7. Wheel diameter and how far the wheels protrude.
8. Do dedicated Part buttons exist?
9. Idle colours of the pads and buttons when nothing is pressed.
10. Height of the fader caps and knobs above the panel.

---

## 2. Five other instruments (compact proportion specs)

All of these are **generic**: no brand names, logos or wordmarks. Real models are cited only for dimensions.

### 2.1 Concert grand (~2.74 m)

| Item | mm | su | Tag / source |
|---|---|---|---|
| Length (keyboard front to tail) | 2740 | 2.235 | [M] 9 ft concert grand reference: Wikipedia D-274, dimensions.com |
| Width (across the keyboard) | 1560 | 1.273 | [M] same (156 cm) |
| Top of white keys above floor | 715 | 0.583 | [M] dimensions.com |
| Height, lid closed | ~990–1040 | ~0.83 | [U] generic grand "39–41 in" (itemfits, designingidea). Not specific to this model |
| "Height 196 cm" | 1960 | — | [M] dimensions.com; almost certainly **lid fully open** [U] |
| Rim (case side) depth | ~380 | 0.31 | [U] generic "around 15 in" (search snippet) |
| Weight | 480 kg | — | [M] |
| Rim | Laminated maple, bent continuously (long bentside curve, straight spine on the bass side, rounded tail) | [R] Wikipedia |
| Finish | Satin ebony or high-gloss ebony | [R] Wikipedia |
| Lid prop angle | **long stick ~38°** (some sources say "45° common"); short stick ~10°. Prop stick about 787 mm (31 in), **perpendicular to the lid** where they meet | [R] pianoworld forum quoting SOS; 45° from the same thread search |
| Brief | **35°** is within reported practice. Use 35–38° | — |
| Legs | 3: two under the keyboard cheek blocks, one under the tail-bass region. Height puts the key tops at 715 | [U] common knowledge, not sourced |
| Pedal lyre | 3 pedals (damper, sostenuto, soft) on a lyre between the front legs | [M] pedal set from the Kawai CR-40A spec |
| Music desk | Rectangular rail on the plate, set back ~250–300 from the fallboard; ~900 × 300 | [U] no published dimensions found |

**Geometry notes.** Build the plan outline as an ExtrudeGeometry `Shape`: straight spine, bentside as a cubic Bezier, tail arc. The lid is the same shape at ~20 mm thickness [U], hinged on the spine side and split at the front flap. Cheek blocks sit either side of the 1 su key span: (1.273 − 1) / 2 = **0.137 su each** [D].

### 2.2 Upright (~1.25 m tall, warm wood)

| Item | mm | su | Tag / source |
|---|---|---|---|
| Height | 1210 (48 in class) to 1310 (52 in class). **Use ~1250** | ~1.02 | [M] Yamaha U1 = 121 cm (pianopricepoint); pro-upright range 121–135 cm (pianopricepoint) |
| Width | 1500–1530 | 1.22–1.25 | [M] U1: 150 cm (pianopricepoint); 152 cm Yamaha range (search) |
| Depth | 600–610 | 0.49 | [M] same |
| Top of white keys above floor | 710–760 (typical ~750) | 0.61 | [R] generic (ezmusicbox, Yamaha FAQ) |
| Weight | ~228 kg (502 lb) | — | [M] U1 |
| Finishes | American walnut, mahogany, polished or satin ebony, white | [M] pianopricepoint (U1 options) |

**Parts, top to bottom** (proportions [U]):
- Lid / top board: full width, hinged near the back, ~25 thick.
- Upper front panel: ~500 tall, with the music desk as a ledge ~ 80 below the fallboard hinge.
- Fallboard: a hinged, rounded-front cover ~100 deep over the keys (soft-close on the U1 [M]).
- Key slip: a strip below the white key fronts, ~40 tall.
- Cheek arms either side of the keys: 0.11–0.12 su wide [D] from (width − span) / 2.
- Lower front (kneeboard): ~550 tall.
- Toe blocks / legs forward of the base.
- 2–3 pedals at the centre bottom.

Warm wood = MeshPhysicalMaterial, colour ~#6b3f22 walnut, roughness ~0.35, clearcoat ~0.6. Use a canvas-texture grain stripe (procedural) if wanted.

### 2.3 1970s suitcase-style electric piano (73 keys, tolex, no brands)

| Item | mm | su | Tag / source |
|---|---|---|---|
| Keys | 73, **E to E** (MIDI 28–100); 43 white keys → **1013.6 mm** span | 0.827 | count [M] (Rhodes 73 family); E–E range [U] common knowledge; span [D] at 23.57 mm |
| Keyboard top unit (w × d × h) | ~1245 × 660 × 330 (49 × 26 × 13 in) | 1.016 × 0.54 × 0.27 | [U] single forum post (ep-forum, "dnarkosis"). The depth looks high |
| Speaker/amp base (w × d × h) | ~1220 × 686 × 356 (48 × 27 × 14 in) | 0.995 × 0.56 × 0.29 | [U] same post |
| Overall (h × w × d) | 660 × 1245 × 254 (26 × 49 × 10 in), 60 kg | — | [U] search snippet (equipboard/reverb aggregation). The dimension order is garbled; treat as "keys at ~660 above floor" |
| Covering | **Black tolex**, **silver grille cloth** on the speaker base | [R] chicagoelectricpiano |
| Harp cover (the flat top over the tines) | **Black** molded cover; flat top | [R] fenderrhodes.com |
| Name rail | Silver/brushed-metal strip behind the keys (per brief). **Leave it blank: no wordmark** | [U] not independently verified in fetched sources |
| Controls | Early (1969–75): 2 knobs (volume, bass boost), later concentric knobs. 1975–79: volume knob, **2 sliders** (treble, bass), 2 knobs (vibrato speed, intensity) on the front panel | [R] fenderrhodes.com mark1b; soundgirls |
| Legs | Stage version: detachable chrome legs. Suitcase: the top unit sits on the amp base | [R] fenderrhodes.com mark1a |

**Geometry notes.** Model it as two RoundedBoxGeometry blocks (top unit plus base) with small metal corner caps. The cabinet is wider than the 73-key span by ~0.19 su, so there is ~0.1 su of cheek per side [D]. The controls sit on the name-rail or front-panel strip to the **left** of the keys [U]. The grille is a slightly recessed panel on the base front. There is an integration question for the host: a 73-key body around an 88-key host row would need `KEY {first:28,last:100}`, or the body centred under keys 28–100.

### 2.4 Vintage analog monosynth (wood end cheeks, tilted panel, generic)

| Item | mm | su | Tag / source |
|---|---|---|---|
| Width | 727 | 0.593 | [M] Model D reissue spec (zZounds) |
| Depth (panel lowered) | 435 | 0.355 | [M] same |
| Height (panel lowered) | 146 | 0.119 | [M] same |
| Keys | 44 (F to C), low-note priority. 26 white keys → **~613 mm** span | 0.50 | count [R] Wikipedia, Vintage Synth Explorer; F–C [U]; span [D] assuming full-size keys [U] |
| Wheels | Pitch + mod wheels in a box **left of the keys**. Box ≈ 727 − 613 − 2 cheeks ≈ **~80–90 mm** | — | position [R]; width [D]/[U] |
| End cheeks | Solid wood (walnut on the reissue editions). Top edge slopes from **~128 mm tall at the rear to ~95 mm at the front** above the desk; rubber feet 12 mm | [R] Moog forum measurements; walnut [R] Bill's Music listing |
| Key tops above the underside | White keys ~102 mm, black keys ~112 mm | [R] Moog forum |
| Panel | Hinged at the bottom rear. It rests flat or tilts up on a kickstand against **one of 4 screw heads, each a different angle**. **No angle is published.** One source says it "can be propped up perpendicular to the keyboard" | [M] manual p.8 (4 positions); angles [U]; "perpendicular" [R] Vintage Synth Explorer |
| Suggested tilt stops | 0° (flat), ~35°, ~55°, ~75° from horizontal | [U] pure estimate |
| Panel sections, left to right | Controllers → Oscillator Bank → Mixer → Modifiers (Filter and Loudness Contour) → Output | [M] manual text (search snippet) |
| Switch colours | Rocker switches: **orange** (modulation routing), **blue** (audio on/off), **grey** (performance) | [M] manual text (search snippet) |
| Knob count, style | Not verified. Typical look is black skirted knobs with a silver insert [U]. Use ~24 knobs across the 5 sections [U] |

**Geometry notes.** The case is a shallow wood-trimmed box. The panel is a separate group rotated about its rear-bottom hinge. Cheeks are ExtrudeGeometry from a side-profile Shape with the 128 → 95 slope. The panel face is dark (near-black) with a thin light-grey section legend drawn procedurally on a canvas, with **no brand text**. Rocker switches are small instanced boxes in the three colours. They can pulse emissive on strikes (orange = the mod wheel section when the pedal is down, and so on). The instrument is ~0.59 su wide, so it can sit centred on the host row or be scaled to the span. Decide in the build.

### 2.5 Glass piano (translucent crystal case, visible action)

| Item | mm | su | Tag / source |
|---|---|---|---|
| Reference size (6'1" class) | **L 1850 × W 1500 × H 1000**, 425 kg | 1.509 × 1.224 × 0.816 | [M] Kawai CR-40A spec page |
| Size range in the category | 1540 (5 ft) to 2800 (9'2") long | 1.26–2.28 | [M] Blüthner Lucid range (luxury-pianos) |
| Case material | Transparent **acrylic** (cast Plexiglas), not glass. It keeps ~90% light transmission | [R] luxury-pianos, edelweisspianos |
| Transparent parts | Rim, lid, legs, music desk, keyslip/front, so the **action is visible** as keys are played. The plate, soundboard and strings are visible through the rim | [R] edelweisspianos, luxury-pianos |
| Opaque interior | Cast-iron plate (gold, or custom plated), spruce soundboard, hammer action | [R] luxury-pianos |
| Lighting | Optional built-in RGB LED illumination | [R] luxury-pianos (Lucid) |
| Lid props / pedals | 2 lid props; damper, sostenuto, soft | [M] Kawai CR-40A |

**Geometry and budget notes (proposal).**
- Reuse the §2.1 grand outline at L 1850 / W 1500 proportions.
- Case: MeshPhysicalMaterial `transmission: 1, thickness: ~15, ior: 1.49` (acrylic), `roughness: 0.02`, a slight blue-grey `attenuationColor`. Environment-free lighting leaves transmission dark, so give the case a faint rim sheen via `clearcoat` and `sheen`, or an additive fresnel edge.
- Visible action: 88 hammer shanks + heads as **one InstancedMesh** (a single draw call), rotated per `state.pressed` vel.
- Dampers: a second InstancedMesh, lifted while `pedal` is down.
- Plate: a single ExtrudeGeometry in gold metal.
- Strings: one `LineSegments` batch.
- Emissive: hammer heads flash `noteColor` on strike, so the "crystal" glow comes from inside the case.

---

## 3. Sources

- Arturia KeyLab 88 mk3 product page (specs): https://www.arturia.com/products/hybrid-synths/keylab-88-mk3/overview
- Arturia store, KeyLab 88 mk3: https://www.arturia.com/store/keylab-88-mk3
- Arturia KeyLab mk3 (49/61) overview (materials wording): https://www.arturia.com/products/hybrid-synths/keylab-mk3/overview
- Arturia downloads, KeyLab 88 mk3 manuals: https://www.arturia.com/support/downloads-manuals/product/keylab-88-mk3
- KeyLab mk3 manual pp.11–13 (ManualsLib): https://www.manualslib.com/manual/3648617/Arturia-Keylab-Mk3.html
- KeyLab 88 mk3 manual PDF (not readable: over 10 MB): https://dl.arturia.net/products/keylab-88-mk3/manual/keylab-88-mk3_Manual_1_0_0_EN.pdf
- Thomann, KeyLab 88 mk3 White: https://www.thomannmusic.com/arturia_keylab_88_mk3_white.htm
- Sound On Sound review, KeyLab 88 MkIII: https://www.soundonsound.com/reviews/arturia-keylab-88-mkiii
- SOS news, KeyLab 88 Mk3 launch: https://www.soundonsound.com/news/arturia-launch-keylab-88-mk3
- MusicTech review, 88 mk3: https://musictech.com/reviews/controllers/arturia-keylab-88-mk3-review-midi-keyboard/
- MusicRadar review, 88 mk3: https://www.musicradar.com/music-tech/midi-controllers/delivers-streamlined-daw-integration-with-an-excellent-hammer-action-keyboard-arturia-keylab-88-mk3-review
- MusicRadar review, 61 mk3: https://www.musicradar.com/music-tech/midi-controllers/arturia-keylab-61-mk3-review
- Soundgale review, 88 mk3: https://soundgale.com/arturia-keylab-88-mk3-review/
- Synth Anatomy review, KeyLab mk3: https://synthanatomy.com/2024/08/arturia-keylab-mk3-review-hardware-and-software-midi-keyboard-controller.html
- Gearnews review, KeyLab 49/61 mk3: https://www.gearnews.com/arturia-keylab-61-mk-3-review/
- KVR review, KeyLab mk3: https://www.kvraudio.com/arturia-keylab-mk3-review
- Internet Tattoo, KeyLab mk3 88 features: https://www.internettattoo.com/blog/the-4-coolest-features-of-the-arturia-keylab-mk3-88
- Perfect Circuit listing (search snippet only; the page returned 403): https://www.perfectcircuit.com/arturia-keylab-88-mk3.html
- Key size (octave 164–165 mm, white 23.5 mm, black 13.7 mm): https://www.pianoscales.org/the-keyboard.html
- Steinway D-274 (Wikipedia): https://en.wikipedia.org/wiki/Steinway_D-274
- Model D dimensions: https://www.dimensions.com/element/steinway-grand-piano-model-d
- Lid prop angles (forum): https://forum.pianoworld.com/ubbthreads.php/topics/185981.html
- Generic grand heights and rim: https://itemfits.com/furniture/grand-piano , https://designingidea.com/piano-dimensions/
- Yamaha U1: https://pianopricepoint.com/yamaha-u1-upright-piano/
- Pro upright size range: https://pianopricepoint.com/pianos-categorized-by-size/pro-upright/
- Keyboard height from floor: https://ezmusicbox.com/blog/height-of-a-piano-keyboard/
- Rhodes suitcase dimensions (forum): https://ep-forum.com/smf/index.php?topic=420.0
- Rhodes Mark I 1969–74: https://www.fenderrhodes.com/pianos/mark1a.html
- Rhodes Mark I 1975–79: https://www.fenderrhodes.com/pianos/mark1b.html
- Suitcase 73 restoration (tolex, grille): https://chicagoelectricpiano.com/rhodes/custom-shop-1971-fender-rhodes-suitcase-73/
- Suitcase controls history: https://soundgirls.org/the-fender-rhodes/
- Minimoog Model D reissue dimensions: https://www.zzounds.com/item--MOOMINIMOOGD
- Model D measurements (forum): https://forum.moogmusic.com/t/model-d-measurement/22570
- Model D manual p.8 (panel stops): https://www.manualslib.com/manual/1164307/Moog-Minimoog-Model-D.html?page=8
- Minimoog on Vintage Synth Explorer: https://www.vintagesynth.com/moog/minimoog
- Minimoog on Wikipedia: https://en.wikipedia.org/wiki/Minimoog
- Kawai CR-40A spec: https://www.kawai-global.com/product/cr-40a/
- Transparent piano guide: https://www.edelweisspianos.com/complete-guide-to-transparent-pianos/
- Clear grand piano (Lucid) description: https://luxury-pianos.com/model/lucid-idyllic-excellence/
