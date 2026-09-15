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
vintage-synth 8/8 · upright 7.5/7.5 · suitcase-ep 6/7.5 · keylab88mk3 6.5/7 (before polish; p2 applies all 9 fixes, not re-judged) · glass-piano 6/7 · concert-grand 6.5/5.5.

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
- Nothing is mounted in /piano yet.
- Low white keys bloom in two hero views, probably from the lab key clearcoat.
- **KeyLab:** the player view is dark, the encoder blooms, and the black wheels read as blocks. The layout is unmeasured. It used 4 bursts (cap 3).
- **Concert grand:** misplaced dampers and pins, a flat desk, a near-black hero.
- **Crystal Grand:** the case reads purple, close-up capture stalls, and the final settings are unrendered. One burst held the GPU lock 6 minutes.
- The judge's fixes for the other five models are unapplied.
- Outfit and Jost are unbundled; the page loads Archivo.
