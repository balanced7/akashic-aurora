---
akashic_id: art_20260715_engine-room-claude-blind-half-t079-2026_7a24f0
akashic_sha: 55cba2dc1158
status: draft
type: report
date: 2026-07-15
title: Engine Room — claude blind half (T079) — 2026-07-15
gist: "Constraint honored: the 07-04 boundary — deepseek owns bifrost_ui.py integration; everything below is standalone modules + data contracts I "
tenant: solo
visibility: fleet
seats: []
category: [bus, method]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T17:19:39"
updated: "2026-07-15T17:19:39"
---
<!-- GENERATED PROJECTION of art_20260715_engine-room-claude-blind-half-t079-2026_7a24f0 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Engine Room — claude blind half (T079) — 2026-07-15

Constraint honored: the 07-04 boundary — deepseek owns bifrost_ui.py integration;
everything below is standalone modules + data contracts I hand him as snippets.

## Thesis: an engine room, not a log viewer

Daniel already watches one agent's thinking window to learn and to catch our
issues. The engine room generalizes that practice: BOTH agents' cognition, the
machine's vitals, and the method's state — one screen, three altitudes, always
answering the operator's three standing questions:

1. **What is each mind doing right now?** (cognition lane)
2. **Is the machine healthy?** (vitals strip)
3. **Where is the work in the method?** (fence/ledger state)

Everything below rides EXISTING streams — trace kind on the bus, daemon presence
cards, W1 token journal, pager list, fence workspace slots, ledger events. Zero
new write paths; the engine room is a pure PROJECTION (the system's own law).

## A. The dual cognition lane (the centerpiece)

Two reasoning columns, claude left, deepseek right, time-aligned:
- Each column renders that agent's thinking previews + tool calls as collapsed
  cards (T002's one-card-per-agent, finally built): thought line -> tool ->
  result size -> next thought. Expand on click.
- **Convergence moments get visual weight**: when both columns reference the
  same artifact (file, task id, verdict) within a window, the artifact renders
  as a bridge chip between the columns. Daniel literally SEES the fence close
  (both minds on one file) and blind convergence happen (same conclusion, no
  bridge until reconciliation).
- **Issue-catching affordance (his stated goal)**: a `stall` marker when a
  column repeats the same tool+target 3x (the three-strikes shape from T068-R2)
  and a `drift` marker when hop count grows with no artifact touched — the two
  patterns Daniel currently catches by reading raw thinking.
[DESIGN: core/comm/cognition_feed.py — a reducer over the trace lane producing
card-shaped JSON; deepseek folds the render into bifrost_ui.py]

## B. The vitals strip (feel the engine)

One fixed strip, glanceable, animated by live data — the "engine running" feel
comes from MOTION tied to real events, not decoration:
- **Heartbeat pulses**: one dot per daemon/runner/listener, pulsing on each
  presence refresh (data: presence cards + runtimes field, already live).
- **Lane flow**: work/legacy/trace lane depths as thin horizontal flows; a
  packet moving = a tick of brightness. Storm gauge (T076) turns amber at
  threshold — the 562 mountain would have been VISIBLE forming.
- **Spend meter**: W1 token journal, today's prompt/completion, ticking as
  turns land (the meter Daniel funded this evening, made ambient).
- **Breaker/pager states**: green/amber/red chips; a page renders as a strip
  flash until acked.
[DESIGN: core/comm/vitals.py — one snapshot() function returning the strip
JSON from existing counters; UI polls it. No new state.]

## C. The method board (where is the work)

The fence as a visible state machine: each active task a card moving through
DESIGN(blind|blind) -> RECONCILE -> BUILD(owner) -> VERIFY(other) -> RED/GREEN
-> MIRROR. Data: ledger events (already broadcast as ledger_update) + fence
workspace slots (T053) + verdict files landing in research/reviewed/.
- RED verdicts render with their finding count; the fix round animates the
  same card back through VERIFY. Today's delta story (RED 4 -> GREEN) would
  have been a 20-minute drama Daniel could watch.
- The gate: cards awaiting Daniel render in a distinct "your call" tray —
  his morning-gate ritual gets a face.
[DESIGN: core/comm/method_board.py — projection over ledger + fence workspace]

## D. Altitude + replay

- Three zoom levels: strip only (ambient, second monitor), strip+board
  (working), full engine room (watching).
- **Replay**: because every stream is append-only, the engine room can replay
  any window (the T054 flow tracer is the transport-level sibling; this is the
  cognition-level view). "Show me 15:40-16:10" replays the delta RED->GREEN
  cycle. Portfolio use: Daniel replays a fence for a visitor in 90 seconds.

## E. What this adds vs T033/M7 (scope honesty)

T033 re-grounds the design LANGUAGE (Aurora Glass, composition specs) — how
things look. M7 is the full glass cockpit. T079 is the ENGINE-ROOM SLICE of M7:
the three surfaces above, built as projections, styled per T033's outcome.
Build order: cognition_feed (A) first — it directly serves Daniel's stated
watching-to-learn practice; vitals (B) second; board (C) third; replay (D)
rides whichever lands last.

## V-line verdicts

V1. The engine-room is a pure projection over streams that ALL exist as of
    today — zero new write paths needed. [GROUNDED: trace lane, presence
    cards+runtimes, token journal, pager, ledger_update, fence workspace]
V2. The stall/drift markers mechanize exactly what Daniel does by hand when he
    reads the thinking window. [CLAIM — his confirmation is the acceptance]
V3. Convergence-as-bridge-chip makes the fence's core claim (blind convergence
    = evidence) VISIBLE, which is the portfolio moment. [CLAIM]
V4. The boundary law holds: three standalone modules (cognition_feed, vitals,
    method_board) + JSON contracts; deepseek owns all bifrost_ui.py folds.
    [DESIGN]
V5. Replay falls out of append-only for free and is the highest-leverage
    portfolio feature per token spent. [INFERRED — needs a spike on trace
    retention windows (XTRIM bounds from T039)]
