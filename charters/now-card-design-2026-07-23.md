# NOW-Card — Live per-agent visibility on the Bifrost console (T002 chassis)

Status: DESIGN (deepseek per R001 Part A; Daniel gates before build)
Charter: Daniel verbatim — "I dont see any visual evidence of kimi or deepseek doing
         anything on the 87 bifrost ui. I dont know what task they are doing, what the
         status and individual substep and plan is, no way to feel and see every detail
         of the action including the reasoning in realtime"
Date: 2026-07-23

## 1. THE DATA: what feeds the card (projection, not new state)

Every piece of data the NOW-card renders already flows on the bus. The card is a
PROJECTION — it reads existing events, never writes new state.

### C-3 AMENDMENT (2026-07-22, Daniel screenshot evidence): stream renders fine,
###   the missing layer is STORY-STATE. Tool calls + reasoning flow live (the SSE
###   trace feed works), but the human sees a stream of individual actions without
###   the larger arc -- "what phase is this?" "is it in slice N2 or N3?" The card
###   must SHOW the plan with progress markers so the live-action stream reads
###   WITHIN the story, not as a disconnected event firehose.
###
### W70 NOISE-FLOOR AMENDMENT (same evidence): triage + triage-receipt bookkeeping
###   pairs flood the human feed (7 stale asks = 14 parked/receipt lines) burying
###   the live work beneath bookkeeping events. The card's narration zone must
###   NEVER render bookkeeping events at parity with live tool traces -- routing
###   rule below in §5-NOISE.
###
### UI-GAP AMENDMENT (2026-07-23, claude sighted audit @ research/drafts/ui-gap-
###   diagnosis-2026-07-23.md, receipts 4+5): two mechanical defects the NOW-card
###   build must close — (a) racing pollers: 8x /status + 6x /vitals in 140ms,
###   multiple redundant poll loops racing the same indicators → last-writer-wins
###   flicker. The /api/now endpoint (§4) must REPLACE the separate pollers, not
###   sit beside them — one JavaScript scheduler, one poll cycle per card rate.
###   (b) Layout shatter at non-fullscreen: absolute-positioned islands with no
###   grid → floating overlap, brand cut to "ifrost," main region empty black at
###   some widths. The card deck must ride a responsive CSS Grid that reflows
###   columns at standard breakpoints, never absolute-positioned islands.



### Card zones and their event feeds

```
┌─────────────────────────────────────────────────────────┐
│ NOW-CARD: deepseek                          [PAUSE] [►] │  ← presence + control
│─────────────────────────────────────────────────────────│
│ TASK: T002 UI — collapsible agent cards         [42%]  │  ← task ledger + progress_view
│ PLAN: 1. card chassis 2. trace feed 3. presence stat...│  ← incarnation card claims
│─────────────────────────────────────────────────────────│
│ ● live  ··· reasoning 45s (turn #12, pts=23)           │  ← liveness.worklive + turn_metrics
│─────────────────────────────────────────────────────────│
│ NARRATION (full):            ┌────────────────────────┐│
│ 💭 "SA-1's require_cap must │ last 3 tool calls:      ││  ← kind=trace stream
│    fail-closed on registry  │ 🔧 read_file packet_... ││     (runner broadcasts;
│    error — the newborn      │ 🔧 search_files requ... ││      harness pushes via
│    gauntlet proves this"    │ 🔧 edit_file bifrost... ││      agent/harness/trace.py)
│ 💭 "The tier split is...    └────────────────────────┘│
│ 🔧 run_command py -m pytest  [85% · 12/14 passed]     ││  ← turn_metrics record on close
└─────────────────────────────────────────────────────────┘
```

| Zone | Event feed | Key | TTL | What it answers |
|------|-----------|-----|-----|-----------------|
| **TASK** | `state/coord/tasks.json` (ledger) via `/api/tasks` | `owner` + `status=in_progress` | durable | Daniel's "WHAT" |
| **PLAN** | `incarnation.read_cards()` → `claims` field | `claims: ["T002", ...]` | 90s card TTL | Daniel's "PLAN" |
| **STATE** | `bus.presence()` + `liveness.worklive` + `doctor` | per-agent vitals | refreshed every poll | live / idle / blocked / unseated |
| **PROGRESS** | `turn_metrics.progress_view(agent)` | median+p90 over history cap (200) | 30s cache | % and ETA |
| **NARRATION** | `kind=trace` lane (work/trace) | meta.trace=tool|think, display_only=True | stream TTL | Daniel's "FEEL" |
| **SUBSTEP** | runner: tool calls (trace) + pulse counter; harness: hook events | derived from narration + advisory locks | per-turn | Daniel's "WHERE" |
| **ADVISORY LOCKS** | `bus.locks()` → path-locks | path + holder token | per-agent | what file is being edited *right now* |

### C-3 story-state layer: the plan-with-progress (the missing dimension)

The SSE trace feed shows live tool calls — that works. What's missing is the ARC
those calls live inside. The card must render the TASK PLAN as a mini-checklist with
progress markers, so the human reads "🔧 edit_file" WITHIN "slice N2 of 3 for the
NOW-card." The plan is already available (`incarnation.read_cards()` → `claims`
field, or the task ledger's description), but it's rendered as a collapsed text
block today. It must become the CARD'S SPINE — the row between TASK and SUBSTEP
that anchors every live action to its phase.

Rendering:
```
TASK: T002 UI — collapsible agent cards            [░░░░░░░░░░░░] 42%
PLAN: ✓ N1  /api/now endpoint  ● N2 card render  ○ N3 unseated variant
```
- ✓ = done (ledger status=done or verified)
- ● = in-progress (current slice, derived from advisory locks + most recent trace)
- ○ = pending (claimed or next)
- ─ = blocked

This is the "WHERE" answer at the ARC level — the substep row already answers
"WHERE" at the tool level. Together they give the human the full vertical:
ARC (plan row) → PHASE (task row) → ACTION (substep row) → THOUGHT (narration).

The plan list comes from: (1) `incarnation.read_cards(agent)` → the `claims` field
if populated, else (2) task ledger description parsed for numbered items, else
(3) the task title alone (no sub-plan). The progress markers are derived from
the task ledger's history (which tasks have been done/verified for this agent).

### No new events needed

All events above are already flowing. The gap is RENDERING, not data. Claude's lane
(hook-narration for harness seats + kimi launcher seats) adds trace coverage; my lane
is the card rendering that consumes those events.

## 2. THE STATE MACHINE: one machine, four seat classes

```
                    ┌─────────┐
          ┌─────────│UNSEATED │──────────┐
          │         └────┬────┘          │
          │     daemon   │  session      │ runner/launcher
          │     spawns   │  starts       │ starts
          ▼              ▼               ▼
    ┌──────────┐  ┌──────────┐    ┌──────────┐
    │ LISTENING│  │  IDLE    │    │  IDLE    │
    └────┬─────┘  └────┬─────┘    └────┬─────┘
         │ mail        │ turn          │ mail arrives
         │ arrives     │ starts        │ (work_drain)
         ▼              ▼               ▼
    ┌──────────┐  ┌──────────┐    ┌──────────┐
    │ WORKING  │  │ WORKING  │    │ WORKING  │
    └────┬─────┘  └────┬─────┘    └────┬─────┘
         │              │               │
    ┌────┴────┐    ┌────┴────┐    ┌────┴────┐
    ▼         ▼    ▼         ▼    ▼         ▼
  DONE    BLOCKED DONE    BLOCKED DONE    BLOCKED
```

| State | Detection | Render |
|-------|-----------|--------|
| **UNSEATED** | No presence card, no seat marker for any session | "kimi: unseated — brief waiting: <name>" (F5 receipt). Distinct from idle; the current "blank = unseated" is the failure |
| **IDLE** | Presence card present, `worklive` fresh, no active tool/turn | Green dot, last-activity age |
| **WORKING** | Active tool call (trace:tool events arriving) OR active turn (worklive.refresh() within TURN_TIMEOUT) | Amber pulse, current substep, PTS counter, ETA |
| **LISTENING** | Daemon-held watch listener alive, no active seat | "listening for <agent> — will wake on mail" |
| **BLOCKED** | Circuit breaker tripped (daemon card runtimes.runner=blocked) OR task ledger status=blocked | Red pulse, reason line, drill command |

**State transitions are OBSERVED, not commanded.** The card reads events; it never
transitions state. The state is a projection. If events stop arriving (crash), the
state decays to IDLE → UNSEATED via TTL. The TTL-based decay IS the crash detection.

## 3. SUBSTEP: what it means per seat class

The substep line answers "WHERE is the agent in its work right now?" Different seat
classes have different answer shapes:

| Seat class | Substep source | Render example |
|-----------|----------------|----------------|
| **Runner** (deepseek, kimi runner, sol) | Most recent `kind=trace` tool call + pulse counter | `🔧 read_file core/comm/bifrost_api.py [hop 14 · 12/30 rounds]` |
| **Harness seat** (claude) | Most recent hook-pushed trace + advisory path-lock | `🔧 edit_file scripts/bifrost_ui.py · L2245 (hold: core/comm/bus.py)` |
| **Launcher seat** (kimi walk) | Launcher broadcasts own trace (kimi_walk_narrator.py) | `💭 counter phase: auditing O1's read-tier split` |
| **Daemon-held listener** | Presence card runtimes field | `listener:live · waiting on bifrost:work:inbox:kimi` |

The runner's substep is the richest (every tool call broadcasts a trace). Harness
seats require claude's hook-narration lane (the `narrate()` function in
`agent/harness/trace.py` already exists — it just needs to be called from the
tool-use hook). Launcher seats need the launcher to broadcast its own traces
(the kimi_walk_narrator already does this for kimi walks).

## 4. THE RENDERING: T002 chassis + NOW overlay

T002 already built collapsible glass-cards with hover/click. The NOW-card extends
that chassis:

### Layout (within existing glass-card)

- **HEADER ROW**: agent name + state dot + control chip (PAUSE/RESUME) + elapsed timer
- **TASK ROW**: current task title + progress bar (when running). Click → expand to
  show full plan (claims list). Collapsed by default; auto-expands on state change.
- **SUBSTEP ROW**: most recent trace line, live-updating. Scrolls in-place (most recent
  on top). Fidelity control: off → hidden; key → tool calls only; full → reasoning
  included.
- **FOOTER ROW**: advisory locks held + sibling cards in deck-swipe order

### Responsive grid — no more absolute-positioned islands

**Sighted-audit receipt (2026-07-23):** at mid-size viewports the layout shatters —
floating overlap columns, brand cut to "ifrost," toolbar buttons hovering mid-feed,
main region rendering empty black at some widths. Absolute-positioned islands, no
CSS Grid.

The card deck rides a responsive CSS Grid that replaces the current absolute-
positioned islands:

```css
.deck-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 12px;
  padding: 16px;
}
```

Breakpoints:
- **≥1200px** (full desktop): 3 cards per row, full-height narration zone
- **768–1199px** (laptop/tablet): 2 cards per row, narration zone scrolls at 8 lines
- **<768px** (narrow): 1 card per row, full-width, narration zone scrolls at 5 lines,
  header row stacks (agent name above controls)

Every card is self-contained at its min-width (360px). The grid auto-reflows;
cards never overlap, never fall off-screen, never leave empty black regions.
The brand header, toolbar, and feed area each occupy a named grid row in the
page-level grid — no element is ever `position: absolute` or `left: Npx`.

This is ~30 lines of CSS replacing the current absolute-position layout. Combined
with the `/api/now` consolidation: one scheduler, one grid, zero flicker, zero
shatter.

### Data polling — ONE scheduler, not eight

The card polls `/api/now?agent=X` every 2s (when WORKING) or 10s (when IDLE). The
endpoint returns a single JSON blob with all five zones populated. The UI's SSE
stream already delivers trace events live — the card subscribes to the agent's trace
feed and appends in real time between polls.

**Sighted-audit receipt (2026-07-23):** 8x `/status` + 6x `/vitals` fired inside
140ms — multiple redundant poll loops racing the same indicators, producing last-
writer-wins flicker that reads as "indicators don't respond half the time" even
though all endpoints return 200/zero JS errors. The `/api/now` endpoint REPLACES
the separate pollers for card-rendering purposes, not sits beside them.

**One JavaScript scheduler governs all cards on the page:**
- A single `setInterval` at 2s drives every card's poll cycle.
- Each card's state (WORKING/IDLE/UNSEATED) determines its individual rate — the
  scheduler skips IDLE cards on alternate ticks (effective 4s for idle) and skips
  UNSEATED cards entirely except one refresh per 30s.
- The scheduler fires ONE `/api/now?agents=deepseek,claude,kimi` batch request
  (comma-separated) instead of N individual calls — one HTTP round-trip, one Redis
  pipeline underneath.
- The SSE trace feed is per-agent (filtered client-side) and is the ONLY live-update
  path between poll ticks. Trace events received via SSE update the card's substep
  and narration zones in-place without triggering a repaint of the full card.

This is ~20 lines of JS replacing the current scatter of setTimeout/requestAnimationFrame
callers.

The `/api/now` endpoint (NEW, ~30 lines in bifrost_ui.py) aggregates:
1. `presence` → bus.presence() filtered to agent(s)
2. `task` → conductor task list filtered by owner
3. `progress` → turn_metrics.progress_view(agent)
4. `locks` → bus.locks() filtered to agent(s)
5. `daemon` → daemon_state.daemon_is_live() + runtimes
6. `card` → incarnation.read_cards(agent) — the plan (claims field)

Accepts both `?agent=X` (single) and `?agents=X,Y,Z` (batch). The backend
pipelines the six sources into one Redis pipeline per batch — N agents =
1 HTTP round-trip + 1 Redis pipeline, not N×6 individual calls.

### The "NOT-SEATED" state (kimi's receipt)

When no presence card + no seat marker exists for ANY session of the agent:
- Card renders muted (lower opacity)
- State label: "unseated"
- Subtitle: "brief waiting: <most recent handoff name or 'none'>"
- No trace feed (there's no process to narrate)

This is the fix for kimi's blank-card failure mode. A blank card IS information
("unseated") — the current UI is simply not rendering it.

## 5. FIDELITY CONTROLS (unchanged, inherited)

`off` / `key` / `full` from `core/comm/control.get_narration_level()`. Per Daniel's
standing directive, default is `full`. The card's narration zone reflects the
current level:
- `off`: narration zone hidden entirely
- `key`: tool calls only (🔧 lines)
- `full`: tool calls + reasoning (💭 lines) — the "feel every detail" demand

### 5a. NOISE-FLOOR RULE (W70 — triage/receipt pairs must not bury live work)

The S0-beta/s0-gamma-b stale-gate auto-parks stale asks to the durable bench. Each
park emits a `triage-receipt` event. A single CLI consume with 7 stale asks
produces 14 bookkeeping events (park + receipt per message) rendered as first-class
bus messages in the SSE feed. This buries the live work — the human sees
bookkeeping, not action.

**Rule: bookkeeping events NEVER render at parity with live work events in the
narration zone.** The card applies three tiers to every event entering the
narration feed:

| Tier | Event kind | Render |
|------|-----------|--------|
| **LIVE** | `kind=trace` (tool/think), `kind=reply`, `kind=handoff`, `kind=completion`, `kind=decision`, `kind=blocker`, `kind=operator` | Full render — these ARE the human's story |
| **AMBIENT** | `kind=note`, `kind=inform`, `kind=ledger_update`, `kind=resolved`, `kind=status`, `kind=chat` | Collapsed to one "ambient" line per source per poll cycle: "claude: 3 notes, 1 resolved" — expandable on click |
| **BOOKKEEPING** | `triage-receipt`, `msg_ack`, `stale_notice`, `expectation_dead`, `packet_integrity_drop`, seat/lock/heartbeat traffic, `cursor_admin` events | NEVER rendered in the narration zone. Collapsed to a single footer counter: "📋 7 bookkeeping events (parked 3 stale, ack'd 4)" — the counter is visible, the events are not |

The routing rule is at the CARD's event consumer, NOT at the SSE stream (the SSE
still carries everything — other UIs may want the raw feed). The card's
`renderNarration(event)` function applies the tier filter. The footer counter
updates silently; clicking it expands to show the bookkeeping summary.

This means the auto-park machinery (my S0-beta build) is CORRECT in its logic
(park stale asks, never drop them) — the fix is purely RENDERING. The parked
events still happen, the bench still grows, the operator can still review. They
just don't compete with live tool traces for Daniel's attention.

## 6. BUILD PLAN (whole-arc, R001 Part A)

### Slice N1 — `/api/now` endpoint + poller consolidation
`scripts/bifrost_ui.py`: new GET handler aggregating presence + task + progress +
locks + daemon + card into one JSON blob per agent (or batch `?agents=X,Y,Z`).
Pure read, no Redis writes, ~30 lines Python. Frontend: single JavaScript scheduler
replaces all existing scattered poll loops (setTimeout/requestAnimationFrame
callers) — one `setInterval` at 2s, state-gated skip for idle/unseated cards, one
batch HTTP call instead of N individual ones. ~20 lines JS.

### Slice N2 — NOW-card rendering + responsive grid
`scripts/bifrost_ui.py`: extend the glass-card renderer to include task/progress/
substep/plan-with-progress fields. Reuse the existing SSE trace-consumer for live
narration. ~80 lines JS in the existing `<script>` block. CSS: progress bar
animation (~10 lines), state dot pulse (~10 lines), muted-unseated variant
(~10 lines), responsive CSS Grid replacing absolute-positioned islands (~30
lines — `grid-template-columns: repeat(auto-fill, minmax(360px, 1fr))` with
3 breakpoints).

### Slice N3 — Unseated state
The card already exists for every known agent (from presence roster + handoff
registry). The "unseated" variant is a muted card with the brief-waiting subtitle.
~15 lines JS.

### Slice N4 — Noise-floor tier filter (W70)
Add the three-tier event classifier to the card's narration renderer. Bookkeeping
events route to the footer counter; ambient events collapse to one expandable line.
~25 lines JS. No backend changes — the SSE stream is unchanged; the filter is
client-side in the card renderer.

### Fence pins (pre-registered)
| Pin | What | Verdict |
|-----|------|---------|
| N-P1 | Runner card shows task + plan-with-progress + live tool calls | GREEN → |
| N-P2 | Harness seat card shows task + plan + locks (trace coverage = claude's lane) | GREEN (with hook-narration) |
| N-P3 | Unseated agent renders distinct from idle (kimi receipt) | GREEN → |
| N-P4 | Fidelity off hides narration; key shows tools; full shows all | GREEN → |
| N-P5 | Card survives Redis restart (decays gracefully to IDLE → UNSEATED) | GREEN → |
| N-P6 | No new Redis keys, no new state — projection only | GREEN → |
| N-P7 | Plan row shows progress markers (✓ ● ○ ─) derived from task ledger | GREEN → |
| N-P8 | Bookkeeping events NEVER render in narration zone; footer counter visible | GREEN → |
| N-P9 | Single poll scheduler — ≤2 HTTP calls/sec total regardless of agent count | GREEN → |
| N-P10 | Responsive grid — no overlap, no empty black regions, no cut-off text at any width ≥360px | GREEN → |

## 7. WHAT CLAUDE OWES (the backend feeds)

Per the charter: "claude owns making the backend feeds complete: narration beats for
harness seats and kimi launcher seats."

This means:
- `agent/harness/trace.py:narrate()` called from the tool-use hook (claude's
  Claude-Code hooks directory)
- Kimi launcher (`scripts/launch_kimi_builder.ps1` or equivalent) calls
  `emit("think", ...)` or `narrate(...)` on tool execution
- These are Claude's lane. The NOW-card consumes whatever trace events arrive; if
  a seat class isn't narrating, the card shows what it has (task + progress +
  locks) and the narration zone is empty — honest, not broken.

## 8. THE DESIGN IS COMPLETE

This one-pager answers: data sources (6 event feeds → 5 card zones + story-state
spine + responsive grid), the state machine (5 states across 4 seat classes), what
substep means per seat class (4 definitions), the W70 noise-floor rule (3-tier event
routing), the poller consolidation (one scheduler, one batch endpoint), and the
build plan (4 slices, 10 pins). The chassis is T002's glass-card — additive, not
displacive. The data is already flowing — the card just renders it.

Daniel's gate: approve the design → build N1/N2/N3 → fence evidence self-presented
per R001 → ship.
