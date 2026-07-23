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

### Data polling

The card polls `/api/now?agent=X` every 2s (when WORKING) or 10s (when IDLE). The
endpoint returns a single JSON blob with all five zones populated. The UI's SSE
stream already delivers trace events live — the card subscribes to the agent's trace
feed and appends in real time between polls.

The `/api/now` endpoint (NEW, ~30 lines in bifrost_ui.py) aggregates:
1. `presence` → bus.presence() filtered to agent
2. `task` → conductor task list filtered by owner
3. `progress` → turn_metrics.progress_view(agent)
4. `locks` → bus.locks() filtered to agent
5. `daemon` → daemon_state.daemon_is_live() + runtimes
6. `card` → incarnation.read_cards(agent) — the plan (claims field)

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

## 6. BUILD PLAN (whole-arc, R001 Part A)

### Slice N1 — `/api/now` endpoint
`scripts/bifrost_ui.py`: new GET handler aggregating presence + task + progress +
locks + daemon + card into one JSON per agent. Pure read, no Redis writes, ~30 lines.

### Slice N2 — NOW-card rendering
`scripts/bifrost_ui.py`: extend the glass-card renderer to include task/progress/
substep fields. Reuse the existing SSE trace-consumer for live narration. ~80 lines
JS in the existing `<script>` block. CSS: ~20 lines (progress bar animation, state
dot pulse, muted-unseated variant).

### Slice N3 — Unseated state
The card already exists for every known agent (from presence roster + handoff
registry). The "unseated" variant is a muted card with the brief-waiting subtitle.
~15 lines JS.

### Fence pins (pre-registered)
| Pin | What | Verdict |
|-----|------|---------|
| N-P1 | Runner card shows task + progress + live tool calls | GREEN → |
| N-P2 | Harness seat card shows task + locks (trace coverage = claude's lane) | GREEN (with hook-narration) |
| N-P3 | Unseated agent renders distinct from idle (kimi receipt) | GREEN → |
| N-P4 | Fidelity off hides narration; key shows tools; full shows all | GREEN → |
| N-P5 | Card survives Redis restart (decays gracefully to IDLE → UNSEATED) | GREEN → |
| N-P6 | No new Redis keys, no new state — projection only | GREEN → |

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

This one-pager answers: data sources (6 event feeds → 5 card zones), the state
machine (5 states across 4 seat classes), what substep means per seat class (4
definitions), and the build plan (3 slices, 6 pins). The chassis is T002's
glass-card — additive, not displacive. The data is already flowing — the card
just renders it.

Daniel's gate: approve the design → build N1/N2/N3 → fence evidence self-presented
per R001 → ship.
