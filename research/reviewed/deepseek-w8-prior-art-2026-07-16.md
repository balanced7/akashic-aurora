# W8 Gauge Honesty + Episode Auto-Close — Prior Art (deepseek research, 2026-07-16)

Status: research note for claude's W8 build. Cites night-build-brief-2026-07-16.md §W8.

## Prior Art

### 1. OTel Span context-manager pattern (Python `with` statement)

OpenTelemetry's Python SDK uses context managers: `with tracer.start_as_current_span("name"):`
auto-closes the span on exit (finally block). The pattern: **tie the lifecycle of a
transient object to the scope that owns it**. A session's open episode IS a span —
its lifecycle is the session. When the session exits (SessionEnd hook, or
`end_session()`), the episode closes.

**Synthesis:** Our `end_session()` already does this (`close_episode(store, now=now_iso,
open_next=False)` at `core/narrative/session.py:118`). The auto-close is BUILT. What
W8 adds is the PROMINENCE: the whisper should show when an episode has been open for
a long time so the operator knows to close it. Like OTel's `set_status_on_exception` —
the framework handles cleanup, but the operator should see the status.

### 2. Prometheus counter naming conventions (`_total` suffix, label semantics)

Prometheus mandates that counters end in `_total` and that labels explain WHAT is being
counted — not just the number. A metric `http_requests_total{method="GET"}` tells you
the denominator. A bare `http_requests 8` is meaningless — 8 what? Compared to what?

**Synthesis for W8 gauge drift:** The whisper shows `mail: 8 unread` — 8 what? The
`bifrost-sync` shows 10 pending; a raw peek shows 19 total. Each gauge counts a
DIFFERENT denominator:
- Whisper: `peek_inbox(limit=8)` → first 8 from legacy cursor (all lanes during dual-write)
- Sync consume: `consume_inbox(limit=20)` → work-lane only (if lane-enabled) from work cursor
- Raw peek: `b.inbox(limit=20, advance=False)` → all lanes from legacy cursor

The fix is NOT to make them all agree (they CAN'T — they serve different purposes).
The fix is Prometheus-style: **label the denominator**. Each gauge says what it counts:

```
mail: 8 unread (legacy peek, first 8)
sync: 10 pending (work-lane)
peek: 19 total (all lanes)
```

The operator stops asking "why do they disagree?" and starts understanding that they
measure different things. This is the Prometheus insight: a counter without a label is
a mystery; a counter with a label is a measurement.

### 3. (Implicit) Kubernetes `kubectl get pods` vs `kubectl get pods -A`

Two views of "how many pods" — one namespace-scoped, one cluster-wide. Nobody asks
"why does `kubectl get pods` show 3 but `kubectl get pods -A` shows 47?" because the
scope is IN the command. Our whisper/sync/peek gauges are the same — they just need
their scope made explicit.

## Design implications for Claude's build

### Gauge labels (the explaining denominator)

- Whisper `mail:` line: append scope hint → `mail: 8 unread (legacy peek)`
- `bifrost-sync` pending line: append → `10 pending (work-lane)` or `10 pending (legacy, lane-off)`
- Raw peek: already self-evident (the user just ran the command)

This is ~3 one-line edits in `agent/harness/context.py` (the whisper) and
`agent/bifrost_pull.py` (the sync render). Trivial build, big clarity win.

### Episode auto-close: ALREADY DONE

`core/narrative/session.py:115-119`: `end_session()` force-closes the open episode with
`open_next=False`, and `start_session()` (called by boot) first closes any prior open
session's episode before opening a new one. The 189h-untitled-episode is a UI rendering
concern (the whisper shows a stale open episode) — not a missing auto-close. What W8
might add: an "episode open for N hours" line in the whisper or doctor, so the operator
sees it BEFORE session end.

## Verdict

The core W8 fix is **label semantics** (borrowed from Prometheus): each gauge names what
it counts. Episode auto-close is already built; the gap is visibility. ~5 lines changed
across 2 files. Lite-tier. Claude's lane per the night brief.
