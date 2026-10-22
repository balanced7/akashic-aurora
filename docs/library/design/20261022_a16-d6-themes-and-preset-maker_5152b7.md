---
akashic_id: art_20261022_a16-d6-themes-and-preset-maker_5152b7
akashic_sha: 0fab61cc50f3
schema_version: 1
status: draft
type: design
arc: A16
date: 2026-10-22
title: a16-d6-themes-and-preset-maker
gist: "A16 D6: themes with screen+LED colours, Aurora Void, a preset maker driven by faders and pads"
visibility: fleet
body_type: markdown
seats: [claude]
category: [memory, ui]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:29:21"
updated: "2026-10-22T14:29:21"
---
<!-- GENERATED PROJECTION of art_20261022_a16-d6-themes-and-preset-maker_5152b7 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# a16-d6-themes-and-preset-maker

# A16 D6: themes, and a preset maker you drive with faders and pads

Status: draft for Daniel's "that's right" · Arc A16 · Track K, T3 · Q8 · Builds on D0 (theme layer), D2 (colour pickup), D4 (menus).

## The ask
- "Both so we can have more themes and visual presets. Lets make a ui for making presets so I can try making
  some too, perhaps we can make colors pickable via fades and save or move to next element via pads?" (Q8,
  answering "the piano's note colours, the patch-bay look, or Aurora Void?")
- "adaptive beautiful coloring"

## What exists today (evidence)
- **The piano's note colours are computed in OKLCH** (`noteColor()` / `noteLch()`, arsenal/web/piano.js:380-398),
  with a mode stored in `arsenal.piano.colour`.
- **The patch-bay look is a set of CSS tokens** (arsenal/web/piano.css:7-21): `--accent #F0A443`,
  `--audio #4CC2BA`, `--control #E47FA7`, `--rec #FF4D5E`, and others. Note that the amber accent is exactly
  the kind of colour that washes to white on the pads.
- **The piano's environments:** moon, ember, nebula ("Velvet nebula"), winter, rain, city
  (arsenal/web/piano/looks/registry.js:123-127).
- **"Aurora Void" exists only as a name in the KeyLab vision draft**, not in code
  (research/.../evidence-pages-server-themes-2026-10-22.md §4). This doc designs it.
- **Saved looks:** revisioned JSON, at most 100 presets, written atomically (arsenal/pianolooks.py).
- **The device:** warm low-saturation colours wash to white. Saturated blues, purples, magentas, pinks and reds
  read well (arsenal/keylab/README.md). The measured gamut table is W0 (d), still owed.

## Design

**A theme** is one JSON document that names a colour for every role on every surface. Each colour carries:
- a screen value, full gamut, for the pages and the LCD;
- an LED value, the nearest LED-safe colour, computed from the gamut table and stored, so the device never
  guesses.

The roles:
- pads per mode: root/third/fifth/seventh for chords, kit pieces for drums, scenes, looks;
- button LEDs: transport, tabs;
- LCD lines;
- the page accent.

**Built-in themes**, in the repo under `arsenal/keylab/themes/`:
- **Piano Light:** taken from the piano's OKLCH note colours, so the pads match the screen.
- **Patch-bay:** from the CSS tokens. The amber accent becomes rose on the LEDs, and its screen value is kept.
- **Aurora Void:** new. Near-black ground, with violet, rose and cyan aurora bands. It suits Daniel's
  "violet-and-rose favourite" and is entirely LED-safe by construction.
- **One theme per piano environment:** Moonlit lake, Ember sanctuary, Velvet nebula, Winter mountains,
  Rainforest at midnight, City of light.

**Your own themes** live in state/arsenal/keylab/themes.json: revisioned, written atomically, the same
contract as piano looks.

**The preset maker (EDIT mode, D1).** It works on the device and on the Control Center page at once, both
editing the same draft live.
- **Pick an element:**
  - Tap a pad to select that pad's role, for example "DRUMS · snare". The selected pad blinks.
  - A screen-button tab switches between element groups: Pads, Buttons, LCD, Page.
  - The dial walks through elements in order. That is the "move to next element" you asked for, and a pad press
    does the same.
- **Pick its colour with faders:**
  - faders 1, 2 and 3 are lightness, chroma and hue (perceptual, OKLCH);
  - touching any of them shows its bar on the LCD;
  - the selected pad shows the live colour as you move;
  - the LCD line shows the full-screen colour next to the LED value.

  When the two differ a lot (a warm colour that will wash), the LCD warns "washes on pads", and the pad
  shows what you will actually get.
- **Quick picks:** pads 9-12 hold the four most recent colours, so you can paint several elements fast. On
  the page, a swatch row and the colour wheel do the same.
- **Save, step, name:**
  - Save: a screen button.
  - Next and Prev element: pads or the dial.
  - Cancel: Back.
  - Name: on the page, or on the device by turning the dial through letters on the LCD.

  A saved theme appears at once in D4's theme menu, and its pads preview it.
- **Visual presets** beyond colour: the same maker saves a **look preset**, meaning a theme plus the current
  page's look settings (intensity, motion, environment) through the page's own preset store. "Theme" and
  "look" stay separate, so a colour scheme can be reused across looks.

## Requirements
- R6.1 MUST: every theme colour stores both a screen value and an LED value. The LED value comes from the
  measured gamut table (W0 d) and is never computed on the device.
- R6.2 MUST: the built-in themes ship as JSON files in the repo; user themes are revisioned and atomic, like
  piano looks.
- R6.3 MUST: in EDIT mode, faders 1-3 edit L, C and H of the selected element, with pickup (D2), and the
  selected pad shows the LED result live.
- R6.4 MUST: element selection works by pad tap, by dial and by Next/Prev, and Save, Cancel and Name work from
  the device alone.
- R6.5 MUST: the device and the page edit the same draft live (one source of truth in the hub).
- R6.6 MUST: a colour that will wash is flagged before you save it.
- R6.7 SHOULD: applying a theme repaints the device in one governor window.

## Deliverables
- D6.1 the theme model, the built-in themes and the LED snap. Accepted when pins (round-trip, snap uses the
  table, revision conflicts) are green in a clean worktree.
- D6.2 EDIT mode on the device. Accepted on video: you make a theme from scratch with faders and pads only and
  save it.
- D6.3 the page editor in the Control Center. Accepted when an edit on the page shows on the pads and an edit
  on the pads shows on the page.
- D6.4 Aurora Void. Accepted when you say it's beautiful, with a photo of the device and the page side by side.

## Probes it depends on
- P4: the LED-safe gamut, which is W0 (d) and needs you at the device.
- P26: the native colour-picker screen 39, if it renders, as an alternative LCD view.

## Open questions for Daniel
- Faders for lightness, chroma and hue, or would you rather think in hue, saturation and brightness? (OKLCH
  keeps "the same brightness" honest across hues; HSB is more familiar.)
- Should themes also recolour the pages (the piano, First Light), or only the KeyLab and the Control Center?

## Out of scope
New page environments (media-suite) and VFX looks themselves (the bench).
