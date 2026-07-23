# Addendum — the MCP-leverage map (what fleet pain dissolves if the door goes concurrent)

Status: current (round WIDENED by Daniel mid-counter — this rides with the opening)
Type: report (round addendum) · Arc: interface / System-5 door · Seats: claude (author); same counter roster · Date: 2026-07-23
Parent: research/drafts/mcp-concurrency-and-boot-ergonomics-opening-claude-2026-07-23.md

**Daniel's widening steer (verbatim, two levels up):** "how many of our concurrent agents
and wake and all the rest can be solved by us leveraging the multithreaded -ness and
concurrency in the MCP? Have everyone think on what we can improve by improving our setup
and the interface with mcp"

**The question restated:** O1 fixes a defect. Daniel is asking the bigger one: treat the
MCP door as an ARCHITECTURAL RESOURCE — a live, concurrent, session-bound process on every
seat — and ask which standing arcs (wake, seats, coordination, ergonomics) it can carry.

---

## The map: pain-arc × what a concurrent door changes

**L1 · The wedge class (the defect) — DEAD with O1.** Baseline; everything below assumes it.

**L2 · The W63 quoting class — DEAD for any seat that uses the door.** MCP arguments are
typed JSON: no PowerShell apostrophe mangling, no --text-file workarounds, no argv
flag-misparse. Tonight's F5 (seats avoiding `note` because of quoting) is not a missing
flag problem, it is a WRONG DOOR problem: post-O1 + attachment fix (T081-W2), in-session
verbs should ride MCP and the whole quoting genus retires for harness seats. (CLI stays
canonical for shells and humans; one source of truth is unchanged — same cmd_* underneath.)

**L3 · The consumer-seat zombie class (tonight's F1) — DIES if the seat lease binds to the
door's lifetime.** Today the seat holder is a spawned listener pid that can outlive its
session (786s stale claim tonight). A stdio MCP server is a CHILD OF THE SESSION — it dies
when the session dies, mechanically, every time. New slice candidate **O1.5**: when consume
rides the MCP door, the RB-21 seat lease keys to the server instance; session end = process
death = instant seat release. No TTL wait, no zombie, no wind-down protocol. (The CLI door
keeps TTL semantics as fallback.)

**L4 · The wake-arm loop (T073/T086/P1) — TRANSFORMED, not fully solved; the honest cut:**
- New slice candidate **A1 `bifrost_await(lane, timeout)`**: a long-poll tool that blocks
  server-side until work-lane mail arrives (or window expires), then returns the mail.
  Pre-O1 this tool is IMPOSSIBLE — it would starve the loop (the exact wedge). Post-O1 it
  is cheap: the loop stays live, other calls flow, and the harness can CANCEL it (today
  cancellation starves too).
- What it buys over `bifrost_wake.py`: in-protocol (no subprocess, no stop-hook arm ritual,
  no harness-tracking pitfall — the recurring must-be-harness-tracked lesson evaporates),
  session-bound (no orphan), lane-aware, and the mail RETURNS IN the tool result (wake and
  payload in one hop — today's watcher wakes you and then you go fetch).
- What it does NOT buy: true idle-wake. A parked long-poll is a HELD-OPEN TURN, not an idle
  session; the harness tool-timeout governs the window and re-issuing windows costs turns.
  P1's daemon remains the owner of real idle-wake; A1 is the in-session tier of the same
  ladder. VERIFY before design-freeze: harness per-call timeout config, and whether a
  parked call costs anything besides the held turn.

**L5 · Per-session substrate duplication — SOLVED by O3, and O3 is exactly the P1 daemon's
transport.** N sessions today = N server processes, N Redis pools, N heal sweeps, no shared
live state. The singleton streamable-HTTP door (`--http` exists; needs O1 internals for
multi-client) is ONE substrate process every seat, runner, and UI connects to. Presence,
locks, seats, packet routing become ONE process's live state with Redis behind it. P1's
reconciled design already names a ManagedChild daemon; the daemon SERVES the door.
Sequence stands: O1 → O1.5/A1 → O3-with-P1.

**L6 · The fidelity ladder (INFORM/STEER/INTERRUPT/HALT) — SHARPENED.** An armed A1 await
is an interrupt point a peer can resolve INSTANTLY (send → blocked call returns now), vs
today's wake latency. Server→client MCP notifications could someday carry INFORM-tier
ambient state without burning a call — but harness support for surfacing notifications is
UNVERIFIED; design for it, do not depend on it (stated bound).

**L7 · What MCP concurrency does NOT touch (say it before someone sells it):** the model
is still one turn at a time (agent-side parallelism is the fleet's, not the door's); Redis
stream/lane/cursor semantics stay exactly as C6-7 left them (the door is a CALLER of bus
physics, never a second source of truth); sampling (server asks a client's model to think)
is not in our harness today; and none of this replaces the ledger/notes precedence spine.

## Slice candidates out of this addendum (all gated, none building tonight)

- **O1** — the dispatch/capture fix (already on the table; unchanged).
- **O1.5** — consumer-seat lease keyed to door lifetime (kills the zombie class).
- **A1** — `bifrost_await` long-poll wake tier (kills the arm ritual in-session; P1 keeps idle).
- **O3+P1** — singleton HTTP door served by the P1 ManagedChild daemon (one substrate process).
- **D-road** — in-session verb traffic migrates CLI→MCP door for harness seats (retires the
  W63 genus there); CLI remains canonical for shells, humans, and cwd-independent scripting.

## Asks (added to the standing roster)

- **deepseek:** fold this into the counter you are writing — especially L3 (your runner
  holds seats too: should ITS consume lease bind to a door lifetime?), L4 (would your
  runner replace its poll loop with A1?), and the L7 boundary (name anything here that
  quietly makes the door a second source of truth — that is the failure mode to veto).
- **kimi:** the leverage map is optimism-shaped by construction — stranger-test L2–L6 for
  asserted-guards (especially A1's "harness can cancel post-O1" and the L3 lease claim)
  and check each "dies/solved" verb against a receipt or downgrade it to "should".
- **gemini (advisory):** re-asked narrowly on long-poll-tool wake patterns and
  singleton-vs-per-session MCP topology.
- **Daniel:** no new decision tonight — this widens the SAME gate: when the counters land,
  you rule the option set AND the slice order (my rec stays O1 first; O1.5 and A1 are the
  two cheapest structural wins behind it).

---

## CORRECTIONS (append-only; filed by the author against own claims)

- **C-1 (2026-07-23 ~02:15, source: gemini second capture, HIGH engagement):** L3's
  "structurally impossible" was TOO STRONG — pure process-lifetime binding fails on
  SIGKILL/Task-Manager kills (no EOF cleanup runs). Corrected design: stdin-EOF death
  detection for the graceful path PLUS an ephemeral lease with ~2s heartbeat / ~5s TTL
  for the violent path (fleet reclaims via XPENDING/XCLAIM). Net: the zombie window
  shrinks 1800s → ~5s; it does not reach zero. O1.5's spec inherits this shape.
- **C-2 (same source):** A1 must be WINDOWED long-poll, not an unbounded park — MCP
  clients enforce per-tool timeouts (~30–120s) and an over-window block orphans the
  server-side task; block ≤ ~5s per xread with cancellation propagated down. A1's spec
  inherits this shape. Both corrections land in the reconcile; kimi's brief already
  targets these two claims (ask 6).
