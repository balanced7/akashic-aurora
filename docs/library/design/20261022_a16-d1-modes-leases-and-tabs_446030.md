---
akashic_id: art_20261022_a16-d1-modes-leases-and-tabs_446030
akashic_sha: a21b7b501298
schema_version: 1
status: draft
type: design
arc: A16
date: 2026-10-22
title: a16-d1-modes-leases-and-tabs
gist: "A16 D1: modes follow the last tool (lease stack + pin), mode tabs on the screen buttons, PERFORM/DRUMS swap"
visibility: fleet
body_type: markdown
seats: [claude]
category: [testing, tooling, performance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-10-22T14:29:18"
updated: "2026-10-22T14:29:18"
---
<!-- GENERATED PROJECTION of art_20261022_a16-d1-modes-leases-and-tabs_446030 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# a16-d1-modes-leases-and-tabs

# A16 D1: modes that follow the last tool, a pin, and mode tabs on the screen buttons

Status: draft for Daniel's "that's right" · Arc A16 · Track K, T3 · Wish W294 · Builds on D0 (leases, layers).

## The ask
- "how we can change modes on the keyboard depending on what tool requested it last, we can think of how to
  do that, perhaps a keylab key combo."
- "We could have the pads do different things depending on mode, we could have performance mode for triggering
  patterns we can swap mid performance to drums and back, idk what would be the easiest way to set that up."

## What exists today (evidence)
- There is no lease on the device. Whoever wrote last wins, by accident (chordview.py, beatsync.py).
- The house lock primitives `core/comm/locks.py` (fencing token, TTL, no steal) and `core/comm/runner_lock.py`
  (heartbeat, a consumer lease) exist, but neither does "last claimant wins" or "pin"
  (research/.../evidence-obs-and-leases-2026-10-22.md §6).
- The eight screen buttons under the LCD send CC 45-52. Arturia's FL script never uses Shift. Bank+/-,
  Settings, MIDI, Transpose and Octave are unbound in that script
  (research/.../evidence-control-map-2026-10-22.md §1-2). Whether each of them sends anything to the host in DAW
  mode is the P2 census.

## Design

**Two things are both called "mode", so the doc keeps them apart:**
- **Who** holds the keyboard: the *lease*. A tool owns the surface: the piano page, chordview, beat, OBS, FL,
  an agent.
- **What** the pads do for that holder: the *surface mode*. The modes are:
  - PLAY (chords and light);
  - DRUMS (kits, D7);
  - PERFORM (patterns);
  - VFX (looks, D3);
  - EDIT (presets, D6);
  - MIX (bindings, D2).

**Leases: the last claimant wins, unless pinned.** The lease logic lives inside the hub and is process-local.
1. A client that wants the surface sends `claim{tool, mode}`. It goes on top of a **stack** and becomes the
   foreground. The previous holder drops to the stack, keeps its layer state, and is told by SSE that it lost
   the foreground.
2. When the foreground holder releases, or its SSE connection drops (that is the heartbeat; there is no
   separate timer), the next one down the stack returns, and its scene repaints in one frame.
3. **Pin:** while the surface is pinned, claims queue instead of taking the foreground. The LCD shows
   "Pinned · <holder>", and a queued claimant hears "queued behind a pin". Unpinning hands the foreground to
   the newest queued claim. That keeps "last tool wins" as the rule, deferred rather than lost.
4. Every claim carries a fencing token. An intent from an old token is refused, so a tab that woke up late
   cannot repaint over the current holder.

**The LCD always says who holds it:** one line, "<tool> · <MODE>", in the tool's colour, shown for 1 s on
every change and then folded into the persistent screen.

**Mode tabs, the easiest way to swap mid-performance.** The eight screen buttons sit under the LCD, so the LCD
can label them. Each holder gets a tab row that the hub draws, for example
`PLAY | DRUMS | PERFORM | VFX | EDIT | MIX | … | PIN`. One press swaps the pads' job instantly: the frame diff
repaints at most 12 pads, inside one governor window. Each mode keeps its own state, so swapping to DRUMS and
back to PERFORM lands exactly where you left it, with the same pattern lit and the same bank. A tab's LED is
lit in that mode's colour, and the active tab is bright.

**PERFORM mode:** pads trigger patterns, and what a pattern is depends on the holder.
- In FL: our script (D8) jumps to and queues FL patterns. The pad colour is the pattern's colour in FL,
  LED-safe. A pressed pad is "queued" and blinks to the beat, then "playing" and solid.
- In the Control Center: scenes and looks (D3) or sound-room clips (later, R track).
- Launch quantise: the next beat or the next bar (a setting). The beat comes from the tempo lane (tempo.py)
  or FL's own clock.

**The pin combo.** The combo has to be a control that (a) sends a message to the host in DAW mode and (b) is
not used by FL or by us for anything else. The rule is fixed now; the button is picked after the P2 census.
The proposed first candidate is **holding the 8th screen button**, the PIN tab: a long press of at least
600 ms pins or unpins. A short press does nothing, so it cannot be hit by accident mid-song. A two-button
combo from the free set (for example Bank- + Bank+) is the fallback if the screen button is ever needed for
something else. While pinned, the PIN tab LED breathes.

## Requirements
- R1.1 MUST: the newest unpinned claim takes the foreground; the holder it displaces keeps its state and is
  told over SSE.
- R1.2 MUST: when the holder releases or disconnects, the previous holder returns within one frame.
- R1.3 MUST: while pinned, claims queue. Unpinning hands the foreground to the newest queued claim.
- R1.4 MUST: an intent with a stale fencing token is refused, and the client is told why.
- R1.5 MUST: the LCD names the holder and the mode on every change.
- R1.6 MUST: a mode swap repaints in at most one governor window (12 packets); the target is under 100 ms from
  the button press to the last pad lit.
- R1.7 MUST: each mode keeps its own state across swaps.
- R1.8 MUST: the pin needs a deliberate gesture (a long press or a two-button combo). A single short press
  never pins.
- R1.9 SHOULD: the tab row and the tab LEDs follow the theme (D6).

## Deliverables
- D1.1 the lease stack in hub.py, with pins for stack order, pin/queue, a disconnect returning the previous
  holder, and a stale-token refusal. Accepted when the pins are green in a clean worktree.
- D1.2 the tab row and the pin gesture. Accepted on video: swapping PERFORM → DRUMS → PERFORM mid-loop, plus a
  pin that survives a page trying to claim.
- D1.3 PERFORM mode for FL patterns, through D8. Accepted when a pad queues a pattern and it starts on the next
  bar.

## Probes it depends on
P2 (which buttons reach the host in DAW mode, including long presses on the screen buttons), and P1/P23 for
the FL side.

## Open questions for Daniel
- Is a long press on the 8th screen button a good pin? Or would you rather a two-button combo you can feel
  without looking?
- In PERFORM, should a pattern start on the next beat or the next bar by default?

## Out of scope
What each mode paints (D2, D3, D6, D7) and the FL calls themselves (D8).
