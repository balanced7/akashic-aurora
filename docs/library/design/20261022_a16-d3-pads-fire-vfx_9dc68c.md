---
akashic_id: art_20261022_a16-d3-pads-fire-vfx_9dc68c
akashic_sha: 62e47b70fc69
schema_version: 1
status: draft
type: design
arc: A16
date: 2026-10-22
title: a16-d3-pads-fire-vfx
gist: "A16 D3: pads fire VFX looks (latch/hold/one-shot), 48 virtual pads, velocity = intensity, SSE to pages"
visibility: fleet
body_type: markdown
seats: [claude]
category: [performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:29:19"
updated: "2026-10-22T14:29:19"
---
<!-- GENERATED PROJECTION of art_20261022_a16-d3-pads-fire-vfx_9dc68c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# a16-d3-pads-fire-vfx

# A16 D3: pads fire VFX

Status: draft for Daniel's "that's right" · Arc A16 · Track K, T3 · Wish W295 · Builds on D0 (layers, events), D1 (VFX mode).

## The ask
- "Im thinking we can use the pads for vfx"
- "then we can use the keylab as a vfx device with all the faders and buttons"

## What exists today (evidence)
- **The VFX Bench has named looks.** A "name this look" field plus `savePreset/loadPreset` go over HTTP to
  `/vfx/presets`, backed by design/vfx-presets.json (scripts/vfx.html:342-346, 566-603;
  scripts/bifrost_ui.py:819, 1348). A preset bundles style, state, identity, params, tint and dials
  (research/.../evidence-shader-params-vfx-2026-10-22.md §2). The bench is A12's page, served by the Bifrost UI
  on :8790.
- **The house GLSL groups are named recipes:** aurora-band, aurora-sheets, glow-xray, neon-line,
  studio-object, hex-neon. Each recipe's params generate controls (arsenal/web/glsl/index.json:100-123; §5).
- **Piano looks** are saved presets in state/arsenal/looks/presets.json (arsenal/pianolooks.py). First Light
  has `u_hue` and `u_intensity` (first-light.js:58, 144).
- **No page has a push channel for "fire this now"** today. The bench polls `/vfx/presets` and has no
  WebSocket or SSE (§6).

## Design

**In VFX mode (D1), each pad holds one look.** The hub keeps virtual banks, because only the DAW bank shows
live colour: four banks of 12 give 48 looks, and the bank switch is a screen-button tab or the P2-confirmed
bank buttons. A pad's colour is its look's dominant colour, LED-safe snapped (D6), so you can see the palette of
the show before you play it.

**Three ways a pad can fire, set per pad:**
- **Latch:** the look becomes the page's current look and stays. The pad stays bright, the previous one dims.
- **Hold:** the effect lives while the pad is held and fades out on release.
- **One-shot:** a burst whose amount is the hit velocity. It decays with the pad's colour ADSR (shared with D7,
  so a hit's light on the pad and on the screen fall off together).

**Velocity is intensity:** the page receives `velocity` in 0..1 through the descriptor's `curve`, and the
default curve is shared with D7's velocity curves.

**Firing reaches the pages as one event.** The hub sends SSE
`{type: "vfx.fire", look: {source, id}, how: latch|hold|oneshot, velocity, t}` plus `vfx.release`. Each page
subscribes through the same client helper as D2 (`keylab-client.js`) and applies the look with its own loader.
Sources a pad can hold:
- `vfxbench:<preset>`
- `glsl:<group>`
- `piano:<look>`
- `firstlight:<state>`

**Filling the pads:**
- the page's "send to pad" button (the Control Center page lists every look from every source, drag one onto a
  pad);
- or on the device: in VFX mode, long-press an empty pad, turn the dial through the looks, and click.

**Latency:** "as fast as we can go". A pad hit is a note on the input port, and the event goes out on SSE
immediately with no governor in that path (the governor only guards writes to the device). The target is
under 10 ms from the host's receipt to the page's handler, at p95.

## Requirements
- R3.1 MUST: 48 virtual pads (4 banks × 12) in VFX mode, with the bank shown on the LCD and the tab LEDs.
- R3.2 MUST: each pad shows its look's colour, LED-safe snapped.
- R3.3 MUST: the latch, hold and one-shot behaviours, per pad, are pinned with synthetic hits.
- R3.4 MUST: velocity maps through a curve to the look's intensity.
- R3.5 MUST: a page applies a look only through its own loader. The hub never reaches into page internals.
- R3.6 MUST: changes to scripts/vfx.html or scripts/bifrost_ui.py are A12's (DeepSeek's file). A16 delivers
  the client helper and a mount snippet, not edits to those files.
- R3.7 SHOULD: pad-hit to page-handler latency stays under 10 ms p95 on the host leg.

## Deliverables
- D3.1 the VFX mode in the hub (banks, fire events, the three behaviours). Accepted when its pins are green in a
  clean worktree.
- D3.2 VFX Bench subscription, as a snippet for A12. Accepted on video: a pad fires a saved bench look and
  velocity sets its strength.
- D3.3 First Light and piano looks as pad sources. Accepted when one pad per source fires on its page.
- D3.4 assigning a look from the page and from the device. Accepted when you put a look on a pad both ways.

## Probes it depends on
- P2: which bank buttons reach the host in DAW mode.
- P17: pad notes per selector position.
- P21: latency.

## Open questions for Daniel
- One-shots: should a pad's hit also flash the whole pad grid briefly (a "strobe" option), or stay on its own
  pad?
- Should the same pad map fire on every page that is open at once, or only on the page that holds the lease?

## Out of scope
Making new looks (that is the bench and the preset maker, D6) and audio-reactive VFX (the beat lane feeds that
later).
