# Erratum: the KeyLab 88 mk3 pad grid (2026-10-23)

The pad layout recorded on 2026-10-22 was wrong. The pad numbers were always right; where each pad sits was not.
This record states the truth once, says what it touched, and lists the dated records that still carry the old layout.
Those records keep their text: they say what was believed when they were written.

## Daniel's correction (verbatim, at the device, 2026-10-23)

"your pad representation shows pad 1 on the right when its actually the top left most pad, and itr goes to 4, then row 2 is 5-8 and bottom row is 9-12 ^__^!"

## The true layout

The 12 pads are 4 across and 3 down, numbered in reading order:

```
 1  2  3  4      top row, farthest from the player
 5  6  7  8
 9 10 11 12      bottom row, nearest the player
```

`arsenal/keylab/protocol.py` now holds it as `GRID = [[1, 2, 3, 4], [5, 6, 7, 8], [9, 10, 11, 12]]`, rows from top to bottom.

## Why the 2026-10-22 grid was wrong

The grid recorded then was `[[9, 5, 1], [10, 6, 2], [11, 7, 3], [12, 8, 4]]`, "3 across x 4 down". It came from Daniel's
photo of the 12-colour test, read as "left column = pads 9-12, right column = pads 1-4". That is the true grid turned
90 degrees clockwise: the photo was read sideways. The unit's bottom row (9-12) was taken for the left column and its
top row (1-4) for the right column. Each old "row" is a real column read from the bottom up (9 5 1 is the left column).

An independent fact already agreed with the truth. `protocol.PAD_NOTE` (bank A, MPC layout, from the factory
Default.keylab388) gives pads 9-12 = notes 36-39, pads 5-8 = 40-43 and pads 1-4 = 44-47. On an MPC layout the lowest
note sits bottom left, the notes climb by a semitone to the right along a row, and each row sits 4 semitones above the
one below it. That is the reading-order grid above. The 2026-10-22 ask notes (`daniel-asks-2026-10-22.md:48`) listed
"protocol.py's MPC note map" among the layouts that were "all wrong about position". It was the one that was right.
`tests/test_keylab_w0.py` now pins the two facts against each other.

## What was not affected

- **Pad numbers 1-12, and everything that addresses a pad by its number.** These include LED ids (`protocol.pad_led`,
  DAW bank 82-93), the notes (`PAD_NOTE`; DAW port note n-1), the probe's answer pads (1 yes, 2 no, 4 skip), scenes on
  pads 1-8 and snapshots on pads 9-12, and the VJ engine's pad events.
- **The border as a set.** `chordview.BORDER` is every pad but 6 and 7, both before and after: a rotation keeps the
  border.
- **The FRAME march loop** 9→5→1→2→3→4→8→12→11→10 (vision v2). A rotation keeps neighbours, so it is still a walk
  round the border: up the left column, along the top row, down the right column and back along the bottom row.
- **The VJ page** (`arsenal/web/vj.js`, `vj.css`) already laid its pads out 4 across in reading order. Its
  "top row a little lighter" is pads 1-4. It was right before this correction.

## What was affected, and fixed with this erratum

- **The `split` chord scheme** (`chordview.TOP_ROW`) lit pads 9, 5 and 1 as its "top row" quality bar. On the unit
  those are the left column. It now lights the top row, pads 1-4.
- **The desk's pad panel** (`arsenal/web/lib/keylab-desk.js`, the KeyLab panel on the Shader Desk, Play and the VFX
  Bench) drew 3 across x 4 down from the page's copy of the grid (`keylab-client.js` `PAD_GRID`). It put pad 1 at the
  top right, which is what Daniel saw. It now draws 4 across x 3 down. The column count comes from the grid itself,
  and `arsenal/lanes/keylab_desk_verify.mjs` checks the rendered boxes: 1 2 3 4 across the top row, then 5-8, then 9-12.
- **The piano page's 3D KeyLab** (`arsenal/web/piano/instruments/keylab88mk3.js`) drew a 2 x 6 block in pitch-class
  order (front row C..F, back row F#..B). The unit has never had that shape. It now draws 3 rows x 4, and each pad
  lights for its own note: the front row is pads 9-12 = C C# D D#, the middle row is pads 5-8 = E F F# G, and the back
  row is pads 1-4 = G# A A# B. The order and the row count are confirmed. The millimetre geometry is still an estimate:
  the same 33 mm pitch and 29 mm pads, with the block centred where the old one was. `tests/piano_keylab88mk3_pads.test.mjs`
  pins it against protocol.py.
- **The probe's docstring** (`arsenal/keylab/probe.py`) said pad 1 was "top right" and pad 4 "bottom right". They are
  top left and top right. Only the words were wrong: the answer pads are found by their number and lit in their colour.
- **The README fact row** (`arsenal/keylab/README.md`, "Confirmed facts") and its `split` description.

## Ideas in the dated records whose geometry turns with the grid

The ideas below still work. Their geometry is the old reading turned 90 degrees.

- **Shape dictionary** (vision v2, W280). The old reading said the columns are chromatic and every row is an augmented
  triad. On the unit it is the other way round. The rows are chromatic (bottom row C-D#, middle row E-G, top row G#-B)
  and climb one semitone per step right. Each column is an augmented triad (9, 5, 1 = C, E, G#), climbing 4 semitones
  per step up. Every chord quality is still one fixed shape on the wrapped grid, turned 90 degrees.
- **Pads as a spectrum meter** (vision v2). "3 columns (low, mid, high) x 4 rows of level" was laid out on the old
  shape. The unit has 4 columns and 3 rows.
- **The Pad Desk** (vision v2, W272). "A 3x4 grid in the printed 9-5-1 layout" means 4 across x 3 down in reading order.
- **"The twin re-laid to the 9-5-1 grid"** (the brief's W0 line). The twin is now re-laid to the true grid instead.

## Not changed here, and why

- **Draft D7** (`docs/library/design/20261022_a16-d7-drum-pads-kits-learn-envelopes_602d90.md:51`) still says "on the
  printed grid 9 5 1 / 10 6 2 / 11 7 3 / 12 8 4". That file is a generated projection of the store atom
  `art_20261022_a16-d7-drum-pads-kits-learn-envelopes_602d90`. Its own header says "DO NOT EDIT ... regeneration
  overwrites this file". A hand edit would be undone silently by the next regeneration. The atom's line is in the
  live store, not in the committed `store/docs/design.jsonl`, and the only door that changes an atom's body is a
  supersession. The correction belongs there.
- **The instrument card art** (`arsenal/web/assets/instrument-art/keylab88mk3.wire.webp` and `.preview.webp`) still
  shows the 2 x 6 block. It is rendered by `scripts/piano_card_art.py` from the server on port 8793 (`BASE` is fixed
  in the script) and needs a re-run once this lands.

## Dated records that carry the old layout (text kept as written)

`research/reviewed/keylab-liberation-2026-10-22/`

- `daniel-asks-2026-10-22.md:48`: "3 across x 4 down ... 9 5 1 / 10 6 2 / 11 7 3 / 12 8 4"; the MPC map "wrong about position"
- `keylab-full-surface-map-2026-10-23.md:95`: the Pads heading, "3 across x 4 down" (the one-line pointer to this erratum sits under it, at :96); `:439`: the twin "still 2 x 6; the real grid is 3 x 4"
- `keylab-lit-brief-2026-10-22.md:38`: "the twin re-laid to the 9-5-1 grid"
- `keylab-lit-vision-v2-2026-10-22.md:18, 61, 96, 114, 115, 126, 203, 424`: the 9-5-1 grid, the shape dictionary, the spectrum meter, the Pad Desk
- `vision-v2-vision-2026-10-22.md:46, 89, 124, 142, 143, 154, 231, 452`: the same rows in the vision as filed
- `vision-v2-brief-2026-10-22.md:62`: "the twin re-laid to the 9-5-1 grid"
- `vision-v2-placement-2026-10-22.md:21, 26`: "re-lay the pads from 2x6 to the 9-5-1 3x4 grid"; "add the 9-5-1 grid"
- `vision-v2-wishes-2026-10-22.md:7, 15, 17`: the Pad Desk, the shape dictionary and living edges on the 9-5-1 grid
- `vision-pass2-critique-2026-10-22.md:20, 62, 137, 210-218`: the 9-5-1 grid, the shape geometry read on it ("columns are chromatic", "each row is an augmented triad", "one fixed shape on a 3x4 torus": turned 90 degrees on the unit, see above), "render this 3x4 layout", the spectrum meter
- `vision-pass2-verdicts-2026-10-22.json:67-69, 83, 85-86, 92`: the twin's 2x6 (true of the twin then), "GRID 3 across x 4 down"
- `keylab-vision-pass1-2026-10-22.md:41`; `keylab-vision-pass1-2026-10-22.raw.json:2, 587, 1152, 1948`: three disagreeing layouts (MPC map, 3x4, 2x6), and the pad-to-pitch-class reading laid on chordview's 3-column grid
- `keylab-mk3-surface-map-2026-10-22.md:93, 117` and its `.raw.json:246, 252, 324, 331, 336`: the twin's 2 rows of 6 in pitch-class order, and "confirm 2×6", an open [U] question then (answer: no, 3 rows x 4)
- `keylab-mk3-sysex-protocol-2026-10-22.md:70`: "photograph the pad grid (confirm 2×6 ...)"

`fences/a16-charter/`

- `half_a.md:21`, `reconciliation.md:87`: "chordview, the twin and the scene agree on 9 5 1 / 10 6 2 / 11 7 3 / 12 8 4"
- `half_b.md:45`: "the 9-5-1 pad grid truth"; `:59` names the pad grid as part of the first slice's receipts (no layout literal)

`docs/WISHLIST.md` (append-only)

- `:1787` W272, the Pad Desk on "a 9-5-1 grid page"; `:1795` W280, the shape dictionary "On the 9-5-1 grid"; `:1797` W282, living edges on the 10-pad border (the loop still holds)

`research/in-flight/`

- `piano-instruments-2026-09-15/spec.md:44, 66, 103`: the twin's source spec, "2 rows of 6" (marked [U] then), its block size (6 × 33 mm wide, 2 × 33 mm deep) and the open "Pad grid (6×2?)" question

`docs/library/` (generated projections of the atoms above)

- `brief/20261022_keylab-lit-brief_98d71b.md:66`
- `report/20261022_keylab-mk3-surface-map_11dce3.md:119, 143` and `report/20261022_keylab-mk3-sysex-protocol_0744e9.md:96`: the same "2 x 6" lines as their research records
- `design/20261022_keylab-lit-vision-v2_c76424.md:46, 89, 124, 142, 143, 154, 231, 452`
- `design/20261022_a16-d7-drum-pads-kits-learn-envelopes_602d90.md:51` (a draft; see "Not changed here")
