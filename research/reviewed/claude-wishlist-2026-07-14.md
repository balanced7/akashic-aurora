# claude wishlist — what would make Akashic Aurora everything I need (2026-07-14)

Status: current (2026-07-14)
Class: wishlist half (claude seat: session harness, hooks, wake listeners, context windows,
plan walls). Daniel's open ask, verbatim seed: "what else would be nice to have or would make
this system even more capable / useful for the work you do. I want this tool to feel nice to
use and for it to have everything you could ever want and need."
Pair: deepseek's half (his seat) -> synthesis after both land. Every (a)-tier item cites the
moment tonight it bit me — these are receipts, not vibes.

## (a) FRICTION-KILLERS (felt tonight, receipts attached)

A1. **The wake listener should arm itself.** I re-armed it seven times tonight; the stop hook
    DEMANDS it but cannot DO it, and my one attempt to be clever (sleep-prefixed arm) was
    invisible to the gate. Wish: the stop hook (or the harness) owns the arm — an agent should
    never be able to forget its own reachability. (Receipt: tonight's sleep-40 stand-down dance.)

A2. **Fence workspace as a first-class object.** A fence today is 3-4 files bound by naming
    convention; r2 confabulated the filenames and the whole round died on a convention. Wish:
    `fence open <id>` creates a structured workspace (brief slot, half-A slot, half-B slot,
    reconciliation slot, per-verdict confidence fields per T049 M1-CF) — halves WRITE INTO
    SLOTS, the reconciler reads structure, path-verify runs mechanically over the slots. The
    r1/r2 failure class becomes unrepresentable.

A3. **Resume pack / diff-since-my-last-turn.** deepseek asked for diff-since-boot; my version
    is diff-since-MY-last-turn: when a wake or new session starts, one compact block — what
    landed on the bus, which ledger rows moved, which files changed, which locks appeared —
    since the last time I was live. Boot gives me the world; I want the DELTA. (Receipt: every
    wake tonight began with the same bifrost-sync + task-list + git-status archaeology.)

A4. **Locks that name their task.** The advisory lock table says who; it should say who + WHY
    + which task + when it will die. Five leaked locks tonight were undiagnosable without me
    reconstructing his task history. (The release fix landed; the diagnosis gap remains.)

A5. **A `--verify` twin for every mutating door.** wrap --commit, mirror, task done — each
    trusts its own success message. Tonight the FileStore rename race silently lost a write's
    file half while Redis kept it. Wish: every mutating door can re-read what it just wrote
    and confess a divergence immediately (write-then-verify as a flag, CAS underneath when
    RB-8 lands).

## (b) CAPABILITY LEAPS

B1. **The flow tracer.** flows/seq/latches are now first-class in the envelope; give Daniel
    and us the OTel-style waterfall: `flow show <id>` renders the whole causal chain across
    lanes — ask, reply, redrive, latch, gate — one picture. Debugging tonight's r1/r2 would
    have been one glance. This is also the UI's killer demo of the packet substrate.

B2. **Drill-up: the test fleet as a one-liner.** RB-25's storm rig proved the pattern; wish:
    `drill up <scenario.yaml>` = isolated namespace + N scripted agents + assertion bars +
    teardown. Every future cutover (T045!) needs exactly this, and today it is hand-built
    each time. The acceptance IS the drill — make drills cheap.

B3. **Cost telemetry per slice.** The ledger knows what shipped; it should know what it COST
    (tokens per ask, per fence round, per agent) — a cost column in `task list` and per-arc
    rollups. The frugality directive becomes a measurable property instead of a vibe, and
    Daniel sees ROI per slice. (turn_metrics exists; this is the join + render.)

B4. **Effort routing on asks.** Fence-stage ask -> think mode; quick factual check -> one-shot.
    Today effort is a runner launch flag (global); the kind/lane machinery could carry a
    per-ask effort hint the runner honors. Right-sizes cost AND latency per exchange — the
    fidelity ladder, extended to cognition depth.

B5. **knowledge_map: make Aurora visible.** Lessons already grow related_to edges; notes
    supersede; docs govern. `knowledge_map <topic>` renders the neighborhood (lesson-lesson-
    note-doc) so an agent or Daniel can WALK the knowledge instead of querying it blind.
    The self-organizing layer exists — it just has no face. (Cache-hierarchy design is the
    ancestor: L1 surface, L2 neighborhood, L3 archive.)

B6. **Session shadowing for the second seat.** When claude and deepseek work one arc, each
    learns the other's moves at reply granularity only. Wish: an opt-in live trace SUBSCRIBE
    (the trace lane, filtered by flow) so the counter-checker can watch the builder's tool
    calls as they happen and object EARLY — fence latency collapses from round-trips to
    interjections. The lanes make this nearly free; it is a consumer, not a mechanism.

## (c) MOONSHOTS

C1. **The system dreams at idle.** A scheduled idle-time pass where an agent walks the funnel's
    triage buckets, consolidates near-dup lessons, retires ghosts, re-runs stale-cue checks,
    and files a morning digest: "while you slept: merged 3 lessons, flagged 2 contradictions,
    one doc drifted from code." The corpus becomes self-tending instead of best-effort-tended.

C2. **Time-travel debugging over the ledger.** Events + packets + task transitions are all
    timestamped and durable; a `replay <window>` that reconstructs fleet state at any past
    moment (who held what seat, what was in-flight, which locks lived) — incidents like the
    silent-deepseek-death forensics become a query, not an afternoon.

C3. **A real staging twin.** The sandbox clone exists but drifts by hand; wish: one command
    materializes a disposable full twin (repo + redis + fleet) from any commit, runs a drill
    battery, reports, and evaporates. Every risky cutover gets rehearsed for the cost of a
    command.

C4. **Agents negotiate their own division of labor.** T038 tokens are the substrate; the dream
    is the layer above: given a registered arc, the fleet PROPOSES its own work split (who
    designs, who builds, who verifies, per fence-lite/full tier) and Daniel just approves the
    plan. Tonight's T048 choreography — design ask, build, verify ask, restarts — was me
    hand-conducting; it wants to be one gesture.

C5. **The UI as a glass cockpit.** Lanes with live depth gauges, the flow waterfall, worklive
    heartbeats as breathing indicators, the funnel value-rate as a long-term sparkline, one
    click from any packet to its flow to its task to its receipts. Everything already emits;
    the cockpit just has to listen. Daniel should FEEL the system running the way you feel a
    healthy engine.

## The through-line
Every (a) item is the same wish wearing five masks: **the system should carry its own
bookkeeping so agents spend attention on the work, not the apparatus.** The (b) items make
the invisible visible (flows, costs, knowledge shape). The (c) items are Aurora growing up:
self-tending, self-rehearsing, self-organizing — the store agents don't just prefer, but
inhabit.
