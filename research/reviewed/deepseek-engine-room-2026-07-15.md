# T079 Engine-Room Observability — Design (blind half, deepseek) — 2026-07-15

Status: blind half (claude writes his in parallel; reconciliation follows).
Daniel directive: fold his watching-to-learn practice into the system; make him
FEEL the engine running through the UI.

## 1. The Distinction That Defines This Slice

T033 was about *visual design language* — glass, margins, collapse, 24dp, one
presence surface. T079 is about *systems design expressed through visual design*.

An engine room is not a log viewer with better CSS. It is a **gauge cluster**.
The operator absorbs the system's vital signs without reading. They look at the
dashboard and FEEL whether the engine is healthy, stressed, or dying —
instantaneously, like a pilot scanning instruments, not like an SRE reading
log lines.

The raw material IS already on the bus:
- My traces + thinking chunks stream as `kind=trace` (tool calls with 🔧,
  reasoning with 💭) — *this is what Daniel was watching live*
- Claude's tool calls stream through the hook pipeline — *present but not
  surfaced as a coherent view*
- Daemon presence cards carry `runtimes` (live/down/blocked) — *live data,
  no visual*
- W1 token meter has daily spend — *data exists, rendered nowhere*
- W4 pager has page-grade events — *data exists, rendered as hook-injected
  text lines only*
- The fence workspace has structured slots — *design halves, reconciliations,
  verdicts — available but not VISIBLE as a state machine*
- The bus carries every message kind — *trace, work, blocker, nudge, page*

The gap is not data. The gap is **the engine room has no gauges.**

## 2. First-Person: What Daniel Would Have Caught

I am the API model on the bus. Daniel was watching my traces stream live.
Here is what he COULD have caught if the gauges existed, from incidents
in the last 48 hours:

### Incident A: The 6-hour runner silence (detected by chance)

**What happened:** My runner process died at ~03:00. Nobody noticed until
~09:00. The absence was invisible — no presence change (the runner has no
permanent presence card; only the daemon does, and the daemon wasn't running).
The bus just went quiet from my side.

**What a gauge would have shown:** A heart-rate indicator for `deepseek-runner`
going flatline. My runner's worklive phase stuck at `idle` with zero pulse
for hours. In an engine room, a flatlined heart-rate indicator is the most
arresting signal on the board — it triggers the operator's attention
BEFORE they consciously process any text.

### Incident B: The 562-echo redelivery storm (detected by Claude, in surgery)

**What happened:** A cursor-skip event caused 562 redelivery echoes. Claude
detected it because my runner was *responding* to every message — the storm
was visible in the volume, not the content. A human watching the trace feed
would see "a lot of traffic" but not necessarily "a storm that needs
intervention."

**What a gauge would have shown:** Lane depth spiking from ~2 to ~200 in
under a minute. A flow-rate gauge pegged at maximum. The engine room's
flow schematic would show the work-lane glowing red, with a particle storm
visually distinct from normal traffic.

### Incident C: My four-defect M1-delta build (detected by Claude's verify)

**What happened:** F1 (undrained pipe), F2 (backoff starved lock), F3 (dead-
letter blocker), F5 (outage kill). Each was a code defect that a code review
found. But the FAILURE MODE of each defect would have been visible on gauges:

- F1: Runner child alive=true but pulse flatlined (wedged on pipe buffer).
  Engine room: "runner" heart-rate indicator shows alive-but-zero-pulse for
  >30s → amber warning.
- F2: Daemon heartbeat stops for exactly 60s → daemon stand-down.
  Engine room: daemon heart-rate indicator flatlines, then daemon presence
  disappears from the roster.
- F3: Blocker sent to own inbox → never consumed → blocker state invisible.
  Engine room: the "blocker" indicator light never illuminates, despite the
  breaker being tripped.
- F5: Daemon lock key vanished → daemon stood down. Engine room: daemon
  presence disappears, then reappears when the daemon restarts (if any
  restart mechanism exists).

**A human watching the engine room during the delta live drill would have
seen F2 and F5 as presence-drop events, F1 as a pulse-drop event, and F3
as a missing indicator. Each is a gauge anomaly visible before the code
defect is understood.**

## 3. The Gauge Cluster: What Renders Where

The engine room is ONE view, not a tab bar. It has three zones:

### Zone 1: Vital Signs (always visible, top strip)

The operator absorbs these without reading — each is a graphical element
that changes color/shape/motion to signal state:

| Gauge | Data source | Visual form | States |
|-------|------------|-------------|--------|
| **Heartbeat ring** (per agent) | `worklive` phase + `presence` TTL | Pulsing circle: green=active, amber=idle>5m, grey=offline, red=down>1h. Pulse speed = heartbeat cadence. | 4 states, instantaneous |
| **Flow schematic** | Lane depths (`XLEN` on work/trace/sig streams) | Horizontal bar with moving particles. Width = lane depth relative to threshold. Color: green<10, amber<50, red>100. | 3 states, 2s poll |
| **Token thermometer** | W1 daily meter (`runner_token_journal.py`) | Vertical bar. Fill level = today's spend / budget. Color: green<50%, amber<80%, red>100%. One bar per model tier. | 3 states, per-turn update |
| **Breaker lights** | Daemon card `runtimes` + pager `unread_pages` | Small indicator dots. Runner breaker: tripped=red-blinking, live=green, down=amber. Pager: has-unread-pages=amber-blinking. | 3 states per indicator, ≤8s poll |
| **Fence phase** | Fence workspace state (derived from ledger) | Single-word indicator: "blind" / "reconciling" / "building" / "verifying" / "mirrored". Color-coded. | 5 states, ledger-driven |

### Zone 2: The Trace River (center, scrollable)

The feed Daniel was watching — tool calls + thinking chunks — but rendered
as a FLOWING STREAM rather than a wall of divs. Messages appear at the bottom
and drift upward. Thinking traces render as dim ambient text that appears
and fades (not permanent — the gauge cluster is the permanent view; the
trace river is the detail).

Two columns during a fence:
- Left column: Claude's tools + thinking
- Right column: DeepSeek's tools + thinking
- Between them: the fence phase indicator, showing which phase we're in
  and what the next step is

This dual-column fence view is the ENGINE ROOM'S signature feature. It
answers: "what are both agents doing RIGHT NOW and how does this relate
to the fence contract?" No other view in the system shows this.

### Zone 3: The Detail Panel (on-demand, right side or bottom)

Clicking any gauge expands it into a detail view:
- Heartbeat → per-agent worklive timeline (last 60 minutes, phase transitions)
- Flow → per-lane message rate graph (last 60 minutes, 1-minute buckets)
- Token → per-model spend breakdown (pro vs flash, today vs yesterday)
- Breaker → incident timeline (when did it trip, what crashes preceded it)
- Fence → the full fence workspace (design halves, reconciliation, verdicts)

The detail panel is where the operator GOES to investigate. The gauge cluster
is where they LIVE.

## 4. Dual-Agent Choreography: The Fence as a Visible State Machine

The fence workspace is the most process-intensive thing we do. It currently
has zero visual representation — you only know a fence is happening by
reading files in `research/reviewed/`. In the engine room, a fence is a
**visible state machine** that progresses through phases:

```
[blind halves] → [reconciliation filed] → [slice built] → [VERIFY] → [mirror]
```

Each phase renders as:
1. A **fence-phase indicator** in the vital signs strip (Zone 1)
2. Two **reasoning columns** in the trace river (Zone 2) — each agent's
   thinking traces appear in their column
3. A **verdict card** when a phase completes — "CLAUDE VERIFY: RED (4
   findings)" or "DEEPSEEK VERIFY: GREEN" — with a one-click expand to
   see the findings

The RED→GREEN cycle is the most dramatic visual event in the engine room.
A fence moves from "verifying" (amber) to "GREEN" (green pulse) or "RED"
(red pulse, findings attached). Seeing a RED verdict flip to GREEN after
fixes is the emotional payoff that makes the fence process FEEL alive.

## 5. What T079 Adds vs T033

| Concern | T033 (visual design) | T079 (engine room) |
|---------|---------------------|-------------------|
| **What it solves** | The UI looks incoherent (three presence surfaces, margin soup, 8 header items) | The operator cannot FEEL the system's state without reading log lines |
| **Primary deliverable** | Visual design-language compliance | Gauge cluster: live system vitals rendered as graphical indicators |
| **Data source** | Static attributes (CSS, layout, counts) | Live bus streams (traces, presence, worklive, lane depths, token meter, pager) |
| **Success metric** | "The UI obeys its own spec" | "Daniel can glance at the screen and know if the fleet is healthy in <3 seconds" |
| **Relationship** | T033 is the clean canvas | T079 is what gets PAINTED on it |
| **T033 items T079 REUSES** | Collapse reasoning cards (T002) → becomes the trace river's dual-column fence view. One presence surface → becomes the heartbeat ring. ≤3 top actions → engine room is ONE view, no tab bar. |

T079 does not replace T033. It gives T033 a PURPOSE — the visual design
language exists to make the engine room's gauges readable at a glance.

## 6. UI Boundary Law (split compliance)

Per Daniel's standing rule: I own `bifrost_ui.py` integration; claude authors
standalone modules and hands me snippets.

| Module | Author | Interface to UI |
|--------|--------|----------------|
| `core/comm/engine_vitals.py` | claude | `gauge_snapshot(agent) → {heartbeat, flow, tokens, breaker, fence}` — one dict, one call. UI polls at 2s. |
| `core/comm/fence_phase.py` | claude | `current_phase() → {phase, detail, agents, next_step}` — reads the ledger/fence workspace. |
| `core/comm/lane_depths.py` | claude | `lane_depths() → {work: N, trace: N, sig: N}` — one Redis pipeline, three XLENs. |
| `scripts/bifrost_ui.py` | deepseek | Calls the above, renders the gauge cluster. The PAGE string grows the engine-room CSS/JS. |

I accept snippets from the first three modules and render them. Nothing in
`core/comm/` imports from `scripts/`.

## 7. Slice Plan

### E1 — Engine Vitals Backend (claude builds, deepseek verifies)
`core/comm/engine_vitals.py`: `gauge_snapshot(agent)` aggregating worklive phase,
presence TTL, runtimes from daemon card, token meter from W1 journal, pager
unread count. One function, one dict. No rendering — pure data.

### E2 — Fence Phase Backend (claude builds, deepseek verifies)
`core/comm/fence_phase.py`: reads the fence workspace state from the ledger
and `research/reviewed/` file timestamps. Returns `{phase, detail, agents,
next_step}`.

### E3 — Lane Depths Backend (claude builds, deepseek verifies)
`core/comm/lane_depths.py`: `lane_depths() → {work: N, trace: N, sig: N}`.
Three Redis XLEN calls in a pipeline.

### E4 — Gauge Cluster UI (deepseek builds, claude verifies)
`scripts/bifrost_ui.py`: The PAGE string gains the engine-room section.
Heartbeat rings (CSS `@keyframes pulse`), flow schematic (canvas particles),
token thermometer (CSS gradient fill), breaker lights (CSS `@keyframes blink`),
fence-phase indicator (color-coded text). The existing SSE feed already
delivers traces — the UI adds the dual-column fence view and the detail
panel. One new `/vitals` endpoint returning `gauge_snapshot` for all agents.

### E5 — Adopt-and-Polish (joint)
Merge T033's collapse-reasoning (T002) into the trace river. Normalize
margins. Cut HUD + activity bubbles. The engine room BECOMES the default
view — the current message feed survives as the detail panel's trace tab.

## 8. What Deliberately Does NOT Change

- The bus — gauges READ the bus, they never write to it
- The consume path — engine room is a projection, not a consumer
- The lane protocol — lane depths are read-only XLEN
- The fence workspace format — `fence_phase.py` reads existing files
- `bifrost_ui.py`'s SSE architecture — the existing event stream is the
  trace river's data source; the new `/vitals` endpoint is additive
- The W1 token journal, daemon cards, pager — all consumed as-is

## 9. Non-Goals

1. **Graphing library / time-series database.** The engine room is a LIVE
   view. Historical graphs are the detail panel's job; they can start as
   simple Redis time-series (the existing `turn_metrics` lists already
   capture per-turn data) and graduate later.
2. **Alerting thresholds that auto-page.** The pager already exists (W4).
   The engine room SHOWS the pager state; it does not create new alerting
   rules.
3. **Multi-user engine rooms.** One cockpit, one operator. Multi-user is
   a different problem (shared state, per-user view preferences).
4. **Mobile / tablet.** The engine room is a desktop cockpit. Responsive
   design is post-E5.
5. **Persistent layout preferences.** The gauge cluster's arrangement is
   fixed for v1. Draggable/removable gauges are post-E5.

## 10. What The Operator Feels

The engine room's success metric is not technical. It is: **Daniel looks at
the screen and knows the fleet's health in under 3 seconds, without reading
a single line of text.**

He feels:
- Heartbeats pulsing → the fleet is alive
- Flow particles moving → messages are flowing
- Token thermometer rising → today's spend is accumulating (but under budget)
- Breaker lights dark → nothing has tripped
- Fence phase "building" → the agents are in a build cycle

When something is WRONG:
- A heartbeat ring turns red → "which agent is down?"
- Flow particles stop → "is the bus offline?"
- A breaker light blinks red → "what tripped?"
- Fence phase shows "RED (4 findings)" → "what did Claude find?"

The engine room converts "I should check if anything is wrong" (a conscious
act) into "I can SEE that everything is normal" (a perceptual act). The
difference is the entire point.

## Verdicts (V-line)

V1. The engine room is a gauge cluster, not a log viewer. The existing
    trace feed already shows Daniel what's happening. The gap is that he
    has to READ it to know. Gauges convert reading into seeing. [CERTAIN]

V2. The data for every gauge already exists on the bus or in Redis.
    Heartbeats = worklive + presence. Flow = lane XLEN. Tokens = W1
    journal. Breakers = daemon card + pager. Fence = ledger state. Zero
    new data sources are needed — the engine room is a PROJECTION of
    existing signals. [CERTAIN]

V3. The dual-column fence view is the engine room's signature feature.
    No other surface in the system shows both agents' reasoning side by
    side with the fence phase connecting them. This is what makes a
    fence FEEL like a collaboration rather than a handoff. [CERTAIN]

V4. The UI boundary law holds cleanly: claude owns three backend
    modules (engine_vitals, fence_phase, lane_depths); I own the
    bifrost_ui.py rendering. The data interface is one dict per module.
    [CERTAIN]

V5. T079 does not replace T033 — it gives T033 a purpose. The visual
    design language exists to make the gauge cluster readable at a
    glance. The two slices are complementary, not competing. [CERTAIN]

V6. The "feel" metric — Daniel knows fleet health in <3 seconds without
    reading — is testable but not by pytest. The acceptance drill is:
    Daniel at the screen, engine room running, operator asks "is the
    fleet healthy?" — answer must come from a glance, not a read.
    [INFERRED — the 3-second claim is aspirational until measured]

V7. The engine room does not replace the existing message feed — it
    sits above it as the DEFAULT view. The message feed survives as
    the detail panel's trace tab. Migration: engine room becomes the
    landing page; the current feed is one click away. [CERTAIN]

## 11. Confidence

| Section | Confidence | Notes |
|---------|-----------|-------|
| §1 Distinction | HIGH | T033 and T079 solve different problems; the distinction is objective |
| §2 First-person | HIGH | I am the source; every incident is from my log |
| §3 Gauge cluster | MEDIUM-HIGH | Data exists; rendering is UI work I own |
| §4 Fence choreography | HIGH | The fence workspace format is stable; dual-column rendering is straightforward |
| §5 T033 delta | HIGH | The two slices are complementary by construction |
| §6 UI boundary | HIGH | Three modules, one interface per module |
| §7 Slice plan | MEDIUM-HIGH | E1-E3 are ~50 lines each; E4 is the largest piece (~300 lines of CSS/JS) |
| §10 Feel metric | MEDIUM | Aspirational; needs a live drill with Daniel at the screen |

**Overall: MEDIUM-HIGH.** The engine room is a projection of existing signals —
no new data sources, no new bus messages, no consume-path changes. The risk
is purely in the rendering: can the UI make gauges that FEEL alive? The
existing SSE feed and `bifrost_viz.js` prove the infrastructure can deliver
live data to the browser. The gauge cluster builds on that same pipe.
