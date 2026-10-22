---
akashic_id: art_20261022_a16-keylab-control-center-minted_c1aac3
akashic_sha: b2ab4a74d996
schema_version: 1
status: current
type: ruling
arc: A16
date: 2026-10-22
title: a16-keylab-control-center-minted
gist: "A16 KeyLab Control Center minted at Daniel's word: own arc, counts toward A12 (#4), lights first; charter = fences/a16-charter"
visibility: fleet
body_type: markdown
seats: [claude]
category: [library, agent-lifecycle, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:21:30"
updated: "2026-10-22T14:21:30"
---
<!-- GENERATED PROJECTION of art_20261022_a16-keylab-control-center-minted_c1aac3 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# a16-keylab-control-center-minted

# A16 KeyLab Control Center: minted

**Minted 2026-10-22 by Vandor (claude seat), at Daniel's word.** This follows the A15 precedent
(docs/library/design/20260902_the-one-program-reconciliation_e1bbbc.md, section 5):
1. a proposal;
2. Daniel's yes;
3. a fence with blind halves;
4. M1-PV;
5. reconciliation;
6. Daniel ratifies the name and rank.

All six steps are done.

## Daniel's words, verbatim (Discord, 2026-10-22)

- The yes: "Feel free to commit, if it deserves its own arc for proper workflow then lets do another arc."
- The name, answering Q3: "Keylab Control Center"
- The rank, answering Q2 ("count it toward A12 THE FACE, or let it stand on its own?"): "lets fold it in", then, when asked to confirm that reading, "Yes".
- The order, answering Q4: "lights first"

## What that means for the program

- **A16 KeyLab Control Center** is its own arc, with its own number, fence and gate.
- In the appetite ranking (docs/library/ruling/20260903_appetite-ranking-2026-09-03_375c23.md) it **counts toward A12 THE FACE**, which is #4. The order now reads A8 > A1 > A3 > A12 (+A16) > A5. A15 remains provisional and unranked.
- A12 owns the Bifrost UI and /vfx. A16 owns the KeyLab's port and the binding between the device and the pages (see the boundary below).

## The charter, in brief

The full charter is fences/a16-charter/reconciliation.md: sealed, PV 34 verified and 0 missing, halves by claude and deepseek.

**Mandate:** make the KeyLab 88 mk3 a house instrument, the hands and second screen of the pages, not a peripheral demo.

**Boundary:** the port is the seam.

A16 owns:
- the hub, the only writer of the DAW port;
- the intent API, the scene model, leases and the input plane;
- the LED-safe snap table;
- the FL handoff script;
- the sound room's supervision and the pad sampler.

A16 does not own:
- the pages (media-suite);
- /vfx and the Bifrost UI (A12);
- the palette canon, which is a shared module.

**Watches:**
- K "Light" (the build watch), work packages:
  - T1, land and licence;
  - T2, the hub and the port;
  - T3, the light language and controls;
  - T4, beat and BPM, which is Heimdall's lane.
- R "Engine Room" (the design watch, probes only), work package T5, the sound room.
- C "Commons" (gated), work package T6.

T4 and T5 are never both under construction.

**Rulings Daniel gave while the fence was open:**
- **Hub:** its own service, reachable from the piano server's UI.
- **MCP door:** yes.
- **Latency:** "as fast as we can go", inside the freeze ceiling.
- **FL:** our own script, where we drive the pads, screen and lights, FL keeps transport working, and faders are NOT tied to FL's mixer, so they can link to anything.
- **Themes:** the piano colours, the patch-bay look and a proposed Aurora Void all become presets, plus a preset maker.
- **Design docs** with requirements and deliverables, not just wishes.
- **Licence:** aubio stays optional; the house writes its own beat detector before anything is bundled.

## Where it stands at minting

- **W0 is mostly landed:**
  - c37ff191: the toolkit;
  - 332d4711: the tempo lane;
  - ce02387f: the governor, the pins, the colour fix and the README receipts. The pins are verified green in a clean worktree at ce02387f.
- **Still owed in W0** (each needs Daniel at the device): the photo receipt for the colour fix, the LED gamut probe, probes P1/P2/P5/P13/P14/P17, and the kill drill.
- **Open with Daniel:** Q13, the Commons.
