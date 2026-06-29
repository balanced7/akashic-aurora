# Cross-Agent Auto-Logger — design + slice plan

> Companion to `docs/narrative-spine-plan.md` / `-test-plan.md`. Same discipline:
> **a slice ships only when its acceptance bar is met on a fixture AND its robustness
> battery is green.** Below bar → iterate the slice, don't advance.

## The one-sentence seam

Capture every agent's **raw activity** into an append-only **Ledger** firehose, and let
an agent **drill from a Beat/Chapter on the narrative timeline down into the raw events
in that span** — to see *what actually happened, and how*.

This is not a new invention. The foundation already names this exact layer:

- `core/foundation/ledger.py` docstring: *"this ledger is the RAW firehose — every event
  every agent emits. A chronicle is a distilled view DERIVED FROM this ledger."*
- `docs/LEXICON.md` (knowledge layers): *"Raw / archival — `session_logs/learnings.jsonl`
  **+ Ledger streams**. The deepest, richest record. Append-only; never mutated or deleted."*
- `docs/LEXICON.md` (narrative): *"**Beat** — points to its raw atom (a learning / commit /
  **ledger event**)."*

The narrative spine already promises Beats that point at raw atoms. The auto-logger is the
**missing raw-atom substrate** those pointers were designed to resolve into.

## Why now (the gap this closes)

Today there is **no searchable raw record** of cross-agent activity:

- The signal firehose (`agent:events`) is **replay-only** — no filter by type/agent/**time**,
  no full-text. `briefing_loader` brute-scans up to 10k events; that is the whole "search".
- The narrative timeline answers *"what was salient and when"* (Beats/Chapters) but has **no
  drill-down** into the un-distilled detail beneath a Beat.
- The historical raw loggers are dead or fragmented (`session_logger`, `auto_logger`,
  `agent_logger`, `session_canonical`); none auto-hook, none build on the Ledger primitive.
  (Inventory: `docs/` + the logging-inventory exploration.)

So an agent navigating the story can see *"Chapter 3: reworked Slice 7 bi-temporal"* but
cannot ask *"show me what was actually tried in that window."* The auto-logger makes that
question answerable.

## Layered architecture (respecting the strict dependency rule)

`System 0 (foundation)` ← `1–3 (domain)` ← `4 (context/narrative)` ← `5 (interface)`.
Lower layers never import higher ones; agents touch only System 5.

| Concern | Layer | Module (new) | Builds on |
|---|---|---|---|
| **Capture** raw events | Domain (1–3) | `core/events/event_log.py` | `Ledger` (`create_ledger`) |
| **Query / search** | Domain (1–3) | `core/events/event_query.py` | shared **Ranker**, **TrackRouter** |
| **Auto-hooks** (best-effort) | Domain seams | in `mirror.py`, `agent_cli.py`, `core/narrative/session.py` | `event_log.capture()` |
| **Timeline bridge** (Beat/Chapter span → raw) | System 4 | `core/narrative/*` + query | `Chapter.span_start/.span_end`, `Beat.at/.source` |
| **Agent surface** (verbs) | System 5 | `agent_cli.py` `events` verb | query layer |

Rationale: capture and query are reusable **domain primitives** (other tooling can read the
raw stream); the timeline bridge is narrative (System 4); only the thin `events` verb is
agent-facing — consistent with the ACI rule that `Store`/`Ledger` internals are never tools.

## Data model — the "raw event" (lexicon-compliant)

Genus is **event** (→ a `Ledger`); the specific use is **raw event** (full-fidelity,
cross-agent, open-vocabulary). Stored as append-only Ledger records:

```
streams:  events:raw            canonical firehose      (maxlen ~100_000)
          events:{agent}:raw    per-agent history       (maxlen ~10_000)

record (the event dict the Ledger carries):
  {
    "id":         "<opaque ledger cursor>",      # assigned by the Ledger
    "at":         "2026-06-27T18:40:00",         # ISO8601 UTC
    "agent_id":   "opencode",
    "session_id": "7dd4bbea",
    "kind":       "tool_call",                   # OPEN vocab (see below)
    "summary":    "ran pytest tests/ -q",        # one-line, human-readable (the "what")
    "detail":     { ... },                       # full payload: args, diff, stdout (the "how")
    "track":      "ai-setup",                    # routed via TrackRouter (best-effort)
    "refs":       ["beat_...","git:...","file:core/x.py"]  # optional cross-links
  }
```

Followable id: a raw event is addressable as **`event:<stream>:<id>`**. That string is a
valid `Beat.source`, so a Beat can point straight at the raw event it summarizes, and the
bridge can walk Beat → raw event → neighbors.

**`kind` is an OPEN vocabulary** — deliberately unlike the closed 6-species signal set
(`action/decision/blocker/handoff/completion/learning`). Starter kinds:
`tool_call`, `file_edit`, `command`, `observation`, `message`, `note`. New kinds need no
schema change (they're just strings). This is *why* raw events get their own stream rather
than polluting `agent:events`, which `CoordinatorService` switches on by `signal_type`.

### Three views, one source of truth (unchanged contract)

This slots cleanly under the existing harmonized knowledge model:

1. **Raw / archival** — the `events:raw` Ledger (+ `learnings.jsonl`). Sacred, append-only.
2. **Canonical state** — the `Store` (`narr:*` etc.): a Beat = lossy summary **+** `source`
   pointer back into the raw event.
3. **Derived / curated** — `chronicles/` (regenerated Chapters/Atlas).

The auto-logger only adds depth to layer 1; layers 2–3 are untouched except that Beats now
have richer atoms to point at.

## Capture — hooks-first (the chosen scope)

`event_log.capture(kind, summary, *, detail=None, agent_id=None, refs=None, hint=None)`
appends one raw event to `events:raw` + `events:{agent}:raw`. **Best-effort and never
raises** (same contract as `BeatLog.emit` and `mirror._emit_commit_beat`) so wiring it into
hot paths can never break them.

Auto-wire it at the seams we already control — exactly mirroring the proven
`_emit_commit_beat` pattern:

- `mirror.py` commit → already emits a `commit` Beat; also `capture("command", "git commit …")`.
- `agent_cli.py` `learn` / `log` / `boot` → capture the verb invocation + result.
- `core/narrative/session.py` `start_session` / `end_session` → capture session boundaries.

For **external runtimes** (Cursor / OpenCode / Claude), provide the door + adapter, opt-in:

- `agent_cli.py events --capture --kind tool_call --summary "…" [--detail-json '{…}']`
  so a separate process can stream its tool-calls/file-edits in (it already shells to
  `agent_cli.py`; this is one more verb).
- A documented hook recipe (Cursor `hooks.json` post-tool / OpenCode hook) that calls the
  above. **Honest scope:** full conversation capture depends on runtime hooks we don't fully
  own — we ship the capture API + adapter + recipe and document what is auto vs. hook-wired,
  rather than over-promise turnkey total capture.

## Query + the timeline bridge (the payoff)

`event_query` reads the raw stream and answers three questions an agent navigating the
timeline actually asks:

1. **"What happened in this span?"** — `events_in_window(start_iso, end_iso, …)` →
   `Ledger.consume` + time filter. This is the bridge: a `Chapter` has `span_start/span_end`;
   a `Beat` has `at` ± a window. Drill = "give me the raw events under this Chapter/Beat."
2. **"Find where X happened."** — `search(query, *, kind=, agent=, track=, since=, until=)`
   → filter, then rank with the shared **Ranker** (`keyword_relevance` now; the embedding
   `relevance_fn` seam later, same as TrackRouter Slice 6). Returns budgeted summaries +
   `event:` pointers for drill-down (progressive disclosure, per the ACI doc).
3. **"Show me this exact event."** — `get(event_ref)` → resolve `event:<stream>:<id>`.

Agent-facing verbs (System 5, ASCII-safe, fail-soft, front-loaded — house style):

```
py agent_cli.py events --around <beat|chapter|ISO> [--window 30m]   # timeline drill-down
py agent_cli.py events --search "query" [--kind K --agent A --track T --since … --until …]
py agent_cli.py events --capture --kind K --summary "…" [--detail-json '{…}']  # external write
py agent_cli.py story --beat <id> --raw                              # Beat's atom + neighbors
```

## Reuse vs. avoid

- **Reuse:** `Ledger` (capture/replay), `Ranker` (search ordering), `TrackRouter` (per-event
  track), the narrative span model (bridge), `Distiller` (optional digest of a noisy window),
  `tests/isolate_canonical.py` + `redis_test_helpers.py` (isolation).
- **Avoid / do not revive:** `session_logger`, `auto_logger`, `agent_logger`,
  `session_summarizer`, `session_canonical` — dead/fragmented, bypass the Ledger. Their
  cleanup is out of scope here (any agent can pick it up — no fixed per-agent split).

## Slice plan (each with its acceptance bar)

### Slice 1 — capture primitive (`event_log`)
- **Build:** `core/events/event_log.py`: `EventLog` on `create_ledger()`; `capture()` →
  `events:raw` + `events:{agent}:raw` with maxlen retention; module singleton with the
  `_AISETUP_TEST_ISOLATED` escape (mirrors `beat_log.get_beat_log`); `recent()` / `count()`.
- **Bar:** every captured event round-trips File **and** Redis identically; **survives
  Redis-down** (File durable, no hang); `capture()` never raises on bad/huge/None input.
- **Tests:** shape (capture/recent/count); fuzz N captures → `count == len(stream)`,
  time-ordered, every event has `at`+`kind`; cross-backend equality (File vs Redis);
  corruption-skip on read; **isolation** (canonical db 0 untouched).

### Slice 2 — auto-hooks (capture happens by itself)
- **Build:** wire `capture()` into `mirror.py`, `agent_cli` `learn`/`log`/`boot`,
  `session.start/end_session` (best-effort).
- **Bar:** a normal boot→learn→commit→session-end sequence yields the expected raw events
  with **zero manual capture calls**, and **each hook is still green if capture throws**
  (fault injection: capture raises → host command still succeeds).

### Slice 3 — query + search (`event_query`)
- **Build:** `events_in_window`, `search` (Ranker-backed, filters), `get(event_ref)`.
- **Bar (the metric gate):** on a labeled fixture (`tests/fixtures/events_fixture.py`,
  ~40–60 raw events tagged with gold answers), **window recall = 100%** (every event in a
  span is returned) and **search precision@5 ≥ 0.8** vs gold for the QA queries. Filters are
  exact. Honest baseline: keyword ranking; embeddings must beat this later or don't ship.
- **Tests:** empty store; bad/again ids; huge window (budgeted); time-zone/ISO edge cases;
  isolation.

### Slice 4 — timeline bridge + ACI verbs
- **Build:** `events --around` (resolve Beat/Chapter span → window), `story --beat … --raw`,
  Beat↔event linkage (a Beat may carry `source="event:…"`; `--raw` resolves it + neighbors).
- **Bar (navigation):** from each fixture QA pair, the right raw event is reachable from its
  Beat/Chapter in **≤1 drill**; output within token budget; ASCII-safe; errors teach on
  empty/bad input.

### Slice 5 — salience promotion  ✅ DONE
- **Built:** `core/narrative/event_promoter.py` — `salience(event) -> 0..5` (Tier-0 importance:
  kind prior + content boosts) and `promote_salient()`, which scans recent raw events and
  promotes the salient, not-yet-beat'd ones into Beats (provenance preserved: the Beat's
  `source` points AT the raw atom; routed via `RouteHint` so the Track registers). Wired as
  `events --promote [--threshold T] [--max N]` and auto-runs on `boot` (a session boundary).
  The `log` hook now stamps `beat:<id>` into the raw event's refs so it's never re-promoted.
- **Rate-limiter (3 ways):** a salience **threshold** (default 3), a per-run **cap**, and a
  persistent **dedup set** (`narr:promoted:refs`) so a re-run never re-promotes. Events that
  already have a Beat (`beat:` / `git:` / `learn:experiment:` ref) are skipped.
- **Bar — MET:** `tests/test_event_promoter.py` (8 tests): coverage of high-salience events
  = 100% (≥95%), no flood (mundane + already-beat excluded, cap respected), dedup across
  runs, provenance (promoted Beat → `raw_for_beat` resolves the atom). Full suite 212 green;
  narrative faithfulness/coverage harness unchanged; boundaries clean. Dogfooded live: an
  external `error: ZLUDA build failed` event promoted → routed to a new `stemroller` track →
  chronicled into a chapter.

#### Prior art (this is the reflection / episodic→semantic *consolidation* layer)
- **Generative Agents (Park et al. 2023):** per-observation importance/poignancy; *reflection*
  fires when accumulated importance crosses a **threshold** (not a schedule) and is written
  back into the stream → our `salience()` + threshold-gated promotion; ablating reflection
  collapsed emergent behavior (atlan survey), i.e. consolidation is the high-value stage.
- **GAM / SEEM (ACL 2026):** a write-isolation episodic buffer consolidated on boundaries with
  a **provenance pointer** → raw stays append-only/sacred; the Beat points at the atom.
- **RecMem (arXiv 2026):** "not all interactions warrant consolidation" → threshold + cap.
- **"What Deserves Memory"/Nemori (ACL 2026):** predefined importance heuristics encode
  *designer intuition*, not data → ours is an honest **Tier-0 baseline**; an embedding/LLM
  poignancy scorer is a drop-in seam at `salience()` that must **beat** this on a fixture
  (same ablation gate as TrackRouter Tier-1) before it ships.

## Self-tests (the system checks itself — no LLM needed)
- **Source-resolution:** every `event:` pointer a Beat/search result emits resolves to a
  real raw event (the lossless-pointer invariant, one level deeper).
- **Round-trip / cross-backend:** rebuild the stream from File and from Redis → equal.
- **Determinism:** same inputs → identical query results (regenerate twice, diff).
- **Isolation invariant:** a full test run leaves canonical (db 0 / real `AI_SETUP`) unchanged.

## Risks / open questions
- **Volume.** Raw capture is chattier than signals. Mitigation: per-stream `maxlen`, keep
  `detail` opt-in/clippable, and keep salience promotion rate-limited.
- **PII / secrets in `detail`.** Capture may pick up command output. Mitigation: a small
  redaction pass on `detail` (clip + drop obvious token/key patterns) before persist; document it.
- **External-runtime coverage.** We can guarantee the in-process hooks; external total
  capture is best-effort via the adapter/recipe. Stated honestly above.
- **Naming of `kind`s.** Open vocab risks drift; we seed a starter set and let the fixture
  pin the common ones as regression anchors.

## Decisions taken (2026-06-27)
- **Scope:** hooks-first (seams we control) + opt-in external adapter — *not* turnkey total
  capture (honest about runtime limits).
- **Naming:** "raw event"; `EventLog.capture()`; streams `events:raw` / `events:{agent}:raw`;
  agent verb `events`. (Alternatives "atom"/"trace" considered and declined.)
- **Home:** the `Ledger` primitive (System 0), in a new `core/events/` domain package —
  *not* the dead legacy loggers.
