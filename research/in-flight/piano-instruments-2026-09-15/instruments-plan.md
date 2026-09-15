# Piano instruments: plan

Sheet: `instruments-sheet.jpg` (one column per model; rows hero / 9:16 player / close-up; Db6/9 at velocity 124). Modules: `arsenal/web/piano/instruments/<id>.js`. Lab: `piano-lab-instruments.html?id=<id>`.

## 1. Models
- **keylab88mk3** (22 calls, 47k tris): Daniel's controller, black or white, no lettering. Pads glow in each pitch class's note colour; their rims bloom on hard strikes. The screen shows our chord name and Nashville number. LEDs follow the pedal, the chord and the keys.
- **concert-grand** (26 calls, 65k tris): an open grand. Strings ring in note colour, dampers lift, and a lid light tints the plate.
- **upright** (13 calls, 17k tris): a walnut upright. Felt glows behind struck keys, candles flare, and the chord is inked on the book.
- **suitcase-ep** (15 calls, 31k tris): a tine electric piano. Tines glow, dampers lift, and a lamp flashes.
- **vintage-synth** (26 calls, 49k tris): an analog synth with pitch lamps and a velocity ladder.
- **glass-piano** (25 calls, 85k tris): an acrylic grand. Hammers throw and strings take the note colour. The glass pass redraws the scene.

## 2. Judge scores (fidelity / beauty)
After the q pass, judged on the newest `-q` frames (previous score in brackets):
vintage-synth 8.5/8.5 (8/8) · keylab88mk3 7.5/7.5 (6.5/7) · upright 8/7.5 (7.5/7.5) · suitcase-ep 7.5/7 (6/7.5) · concert-grand 7/6.5 (6.5/5.5) · glass-piano 6.5/6.5 (6/7).

Every model gained on at least one axis and none lost fidelity. Beauty dropped for suitcase-ep (dresser silhouette) and glass-piano (the clear case vanishes in the hero). All models are within 60 calls and 150k triangles.

## 3. Integration into /piano
- **Setting:** an "Instrument" select ("Page keys" plus the six), saved in `arsenal.piano.instrument`, loaded with `import()` and error-isolated like the scheme host in `piano-next.js`.
- **Host hook** (about 60 lines in piano.js, after the current edits):
  1. Pass `ctx`: THREE, scene, keyX, isBlack, KEY, noteColor, framing, `span {left, right, keyTop, keyFront, keyBack, floorY}`, `fonts.display`.
  2. Add `group` (already aligned to keyX); call `resize` from `applyFraming`.
  3. Before `composer.render`, fill one reused `state` and call `update`.
  4. Apply hints: keyStyle colours, hide keys outside keySpan, `hideHostBody`, floor at `min(-2.3, floorY)`. Restore on switch.
- **Coexistence:** models sit below the trail plane, so Synthesia bars and schemes draw over them. Spectacle already holds `floor`, `lacquer` and `railLine`, so one owner toggles them. Portrait: lids short or off; non-note glow capped.
- **Budget:** 13–26 calls per model, so a page frame stays at about 100–130. Glass defaults to `'fast'` until measured. The grand's and upright's lights recompile shaders once on switch.

## 4. Open issues
Ordered by what could embarrass us in front of Daniel, most important first.
- Nothing is mounted in /piano yet.
- **KeyLab wheels:** still two black rocker caps in the hero, not round wheels. It is his own instrument, so this matters most. The rear-to-front cheek slope is also hard to see at hero scale.
- **Crystal Grand hero:** with no environment map the clear acrylic has no presence. The rim, legs and lid disappear, so it reads as a dim black grand. It needs stronger fresnel or edge highlights, or a faint environment map. The whole frame still costs about 218 calls, against 100–135 for the others.
- **Concert grand:** in 9:16 the overstrung bass is a translucent orange sheet and the left cheek has grey banding. In the close-up the pins are oversized posts in a sparse grid and the dampers are tall black slabs. The desk grille looks like a vent, and in the hero a long black bar lies across the plate.
- **Suitcase EP:** it looks like a two-drawer chest (empty face under the keys, doubled brackets, side handles). The grille shows the speaker cones through it, and the control plate is under the keys instead of on the left name rail. The 9:16 view is dark.
- **Upright:** the candles are still hot orbs in 9:16. The kneeboard grain is evenly spaced sine contours, and the walnut is orange-red rather than #6b3f22.
- **Vintage synth:** minor only. The face is bronze-brown, not near-black, and the walnut cheeks look slightly plastic.
- **Lab-wide:** host keys look grey and muddy in every 9:16 view. Chord text on instruments (the upright's book, the Crystal Grand's desk) repeats the page header.
- The low-key bloom hot spots from the earlier heroes are gone.
- **Fonts:** the lab page now loads Outfit, Raleway and Jost from Google Fonts. The /piano page still loads Archivo only.
