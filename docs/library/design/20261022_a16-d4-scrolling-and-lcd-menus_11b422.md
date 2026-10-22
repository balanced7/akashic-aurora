---
akashic_id: art_20261022_a16-d4-scrolling-and-lcd-menus_11b422
akashic_sha: ba80a54db757
schema_version: 1
status: draft
type: design
arc: A16
date: 2026-10-22
title: a16-d4-scrolling-and-lcd-menus
gist: "A16 D4: dial and fader scrolling, declared menus on the LCD, pads preview choices, second-press help"
visibility: fleet
body_type: markdown
seats: [claude]
category: [bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:29:20"
updated: "2026-10-22T14:29:20"
---
<!-- GENERATED PROJECTION of art_20261022_a16-d4-scrolling-and-lcd-menus_11b422 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# a16-d4-scrolling-and-lcd-menus

# A16 D4: scrolling with the dial or a fader, and menus on the LCD

Status: draft for Daniel's "that's right" · Arc A16 · Track K, T3 · Wish W296 · Builds on D0 (LCD lane), D1 (lease), D2 (declarations).

## The ask
- "we can use a fader or perhaps the dial wheel to scroll."
- "for the vfx page and arsenal pages to interact with the keylab display with menus and adaptive beautiful
  coloring."

## What exists today (evidence)
- The main dial: turn CC 116 (relative), click CC 117. Arturia's script collapses the turn to fixed steps with
  "No acceleration with the main encoder". Back is CC 40 (research/.../evidence-control-map-2026-10-22.md §1).
- **LCD screens:**
  - two-line full screen 12 persists (confirmed on the device 2026-10-22);
  - knob/fader/pad graphics 28/29/30 carry a 0-127 bar.
- **The LCD enum also names screens Arturia's script never draws:**
  - list setup/append/prepend (20-22);
  - carousels (18-19);
  - a colour picker (39);
  - a browser (40).

  Whether the firmware renders them is unknown (§4; probe P16).
- **The piano's Studio drawer is already a declarative menu.** Groups (Scene, Atmosphere, Colour & numbers,
  Frame) hold settings, each with a label and values, and all of it comes from `LOOK_SETTINGS`
  (arsenal/web/piano/looks/registry.js:107-177; studio.js:50-73).
- **The Second-Press principle** (memory 2026-10-07): the first press shows the name, the second a whispered
  hint, the third the full picture.

## Design

**Menus are declared, not drawn.** A page declares a menu tree, built from what it already has (the looks
registry groups, the param schema groups): `menu: [{group, items: [{id, label, values|range, current}]}]`.
The hub owns how that tree looks on the LCD. Pages never send screen bytes.

**On the LCD:**
- If P16 shows the native list widget works, menus use it, so they scroll like the KeyLab's own.
- Otherwise the fallback is the two-line full screen:
  - line 1: "Group › Item", in the group's colour;
  - line 2: the value, in the value's own colour (a theme shows its colour, a toggle shows on or off).
- An item with a range shows the fader graphic (screen 29) with its bar.

**Navigation:**
- **Dial turn:** move through items. The hub adds the acceleration Arturia left out: quick turns jump by more,
  measured from the turn rate, so a list of 100 is not 100 clicks.
- **Dial click:** enter a group, or start editing a value. Turning then changes the value, and a second click
  commits it.
- **Back (CC 40):** up one level, or cancel an edit.
- **Fader 9 as a scrub bar** for long lists. Its absolute position maps to the list index, so one sweep
  crosses a list of 300. It uses D2's pickup, so it never jumps the cursor when you first touch it.
- **Screen buttons** stay the mode tabs (D1). Inside a menu, the four nearest the cursor can become shortcuts,
  labelled on the screen.

**Adaptive colour:**
- While you browse a choice, the **pads preview the options**. Browsing themes lights pads 1-N in each theme's
  colour, and the hovered one breathes.
- The tab LEDs and the LCD line colours follow the current theme (D6).
- Colours are LED-safe on pads and buttons, and full-gamut on the LCD (it is a colour screen).

**Second press.** On an item's first focus, the LCD shows its name. Dwelling there 1 s, or clicking twice,
shows the page's help text for it, which the param schema already carries as `help`.

**The menu always belongs to the lease holder (D1).** If the piano page holds the keyboard, its Studio menu is
what you browse. When OBS takes over, the menu becomes OBS's scenes.

## Requirements
- R4.1 MUST: pages declare menus as data; no page sends LCD bytes.
- R4.2 MUST: dial turn, click and Back navigate any declared tree with no page-specific code.
- R4.3 MUST: dial acceleration is pinned with synthetic turn streams (slow turns step by 1, fast turns jump).
- R4.4 MUST: the fader scrub maps position to index with pickup (no jump on first touch).
- R4.5 MUST: the LCD names the group, item and value, coloured from the theme, at 60 ms or more between
  updates.
- R4.6 MUST: browsing a choice previews the options on the pads when their values have colours.
- R4.7 SHOULD: the native list widget is used if P16 proves it; otherwise the two-line fallback, with no loss
  of function.
- R4.8 SHOULD: the help text appears on dwell or a second press.

## Deliverables
- D4.1 the menu model and navigator in the hub. Accepted when pins cover the tree walk, acceleration, scrub and
  commit/cancel in a clean worktree.
- D4.2 the piano's Studio drawer declared through the client helper. Accepted on video: you change the
  piano's theme and intensity from the KeyLab alone.
- D4.3 the LCD renderers (two-line, fader bar, and the list widget if P16 passes). Accepted with a photo of each
  screen.

## Probes it depends on
- P16: the native list widget.
- P26 (new): do screens 39 (colour picker) and 40 (browser) render? Send each once with sample data and
  photograph it.
- P14: LCD spacing.
- P2: Back and the dial on this unit.

## Open questions for Daniel
- Fader 9 as the scrub bar, or a different fader?
- Should a menu change apply live as you turn, or only on the second click? (The proposal: live preview while
  turning, and the second click keeps it, so Back undoes.)

## Out of scope
The preset maker's editing screens (D6) and OBS-specific menus (D5).
