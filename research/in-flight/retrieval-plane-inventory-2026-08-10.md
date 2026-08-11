# The retrieval plane inventory — what we store, what we can actually ask

claude (Vandor), 2026-08-10. Written because a search failed in a way that revealed the shape
of the problem, and the next person to ask "why can't I find X?" should read this instead of
rediscovering it.

---

## The question this answers

**"Our knowledge is grepable but not queryable."** — Daniil, 2026-08-10, calling it "a huge
part of the problem we have."

He is right, and the reason is not that retrieval is bad. It is that **we hold many dimensions
and offer one.**

---

## The planes, and which have doors

| plane | holds | fleet door | searchable by |
|---|---|---|---|
| Lesson corpus | 846 lessons, per-agent attributed | `recall`, `recall-at`, `recall --agent` | token match |
| Notes | durable state, superseded by title | `note --get`, `notes` | title, listing |
| Ledger | 278 tasks, status history, declared files | `task list`, `task get` | id, status |
| Library atoms | typed docs, categories, arcs | `doc`, projections in `docs/library/` | filename, grep |
| Events | append-only event log | `events`, `event_query` | filters |
| Bus | live + captured messages | `bifrost-sync`, `bifrost-fetch` | cursor, id |
| Git | commits, diffs, dates | `git log -S`, pickaxe | string |
| **Session transcripts** | **the founder's own words** | **NONE** | **nothing** |

The last row is the finding. **480 files, 440 MB, and no door.** It is reachable only from the
harness, by substring, one snippet per session.

---

## What that costs, measured

On 2026-08-10, two directives were found to have been specified, re-quoted later as standing
policy, and never built — because nothing in the repo could locate them.

- **Research cadence**, 2026-07-26: *"we keep finding gold when we do this but we rarely do it,
  so I want a full comprehensive suite so we can actually start making informed decisions
  instead of stepping on every rake as it comes along."*
- **THE EYE**, 2026-07-31: *"a realtime eye that you can quyery and understand your position
  and vision on multiple axees at once."* Scored **3×** in a prioritisation pass.

**Four parallel searches across every plane that HAS a door returned a confident, wrong
negative.** Recovery took eight guessed substring searches through the harness tool. A negative
result from the readable planes is **not** a negative about what was said.

---

## The dimensions we hold but do not offer

Benchmarked against priori.sh's shipped facet surface (Source · Entity · Type · Relationship ·
Exact phrase, with as-of beside the search box):

> **AUDIT NOTE 2026-08-10 (live API, Daniil's key):** the facet reading CONFIRMED — plus
> operator syntax (`source:`/`entity:`/`type:`/`rel:`/`-term`) and an "interpreted as" parse
> echo the screenshot didn't show. One correction rides the lesson
> `priorish_live_api_audit_corrects_screenshot_claims`: a Pro-gated vector reranker exists in
> their document plane (second-stage after facets, never on `/search`), so "no semantic at
> all" overstated it; the conclusion of this inventory is unchanged and strengthened.

| dimension | where it already lives | queryable today? |
|---|---|---|
| **Who** | `agent_id` on lessons; `by`/`owner` on tasks; commit author; `frm` on bus | only via `recall --agent`, added 2026-08-10 (T260) |
| **What kind** | atom `type`, message `kind`, lesson `category`, task `status` | no |
| **Related to what** | `replaces`, `related_to`, `enforced_by`, `deps` | no — edges are stored, not searchable |
| **As of when** | bitemporal `valid_from` / `valid_to` / `recorded_at` | no — see below |
| **Where** | declared `files` on tasks, `cwd`/`gitBranch` on transcripts | no |
| **Exact phrase** | token index | **yes — the only one** |

**Six dimensions in the data. One and a half exposed.**

---

## The two things already built and not adopted

### 1 · Bitemporal validity — we are level with the state of the art and did not spread it

`docs/PRIOR_ART.md` records this, and it is the one subsystem where the assessment is
*inverted* in our favour:

> "**INVERTED** — this is the one subsystem where we are level with the state of the art rather
> than behind it. `valid_from` is set once and never moves, `valid_to` closes on supersession,
> `recorded_at` refreshes on regeneration, and `supersede()` persists **BOTH** nodes so the old
> one stays queryable and inbound links forward via `replaces` edges. **The real gap is not in
> this subsystem: it is that the LESSON plane never adopted it.**"

Comparable systems named there: **Zep / Graphiti bi-temporal** ("THE SAME MODEL WE ALREADY
HAVE"), SQL:2011 temporal tables, Datomic as-of queries.

**Verified 2026-07-26 by running it:** a lesson-shaped object carrying those three attributes
works with `lifecycle.stamp()` and `lifecycle.is_active()` today, unmodified. **Three fields buy
the whole mechanism.**

**Gotcha, recorded there and worth repeating:** `isinstance(node, BiTemporal)` returns **False**
even for an object carrying all three attributes, because `runtime_checkable` Protocols validate
*methods*, not *data members*. The lifecycle functions work anyway through `getattr`
duck-typing — **but anyone who adds an isinstance guard for safety silently breaks a mechanism
that otherwise just works.**

**Consequence today:** recall hands back the *current* head. We cannot ask what the fleet knew
on a past date. The n=5 kill-drill therefore ran against today's archive with no way to replay
the decision as it was actually made — the exact failure priori.sh exists to prevent
("historical evals cheat when tools retrieve corrected present-day evidence").

### 2 · The embedding socket — specified three times, never filled

- `core/learning/learning_store.py` — "no embeddings, no LLM judge" *(stated limitation)*
- `core/events/event_query.py` — "embedding relevance_fn is a later swap-in — same 0..1
  contract, must beat the [current]" *(contract already defined)*
- `core/codex/schema.py` — `centroid: List[float]  # embedding handle` *(field exists, unused)*

Three modules anticipated semantic retrieval and left the socket open. **That ordering is
correct.** Embeddings enhance a working facet surface; they do not substitute for a missing
one. Fill the sockets *after* the dimensions are exposed, not before.

---

## The known defect in the one dimension we do offer

`learning_store.py` line ~75: `_TOKEN = [a-z0-9_]+` makes underscore part of a token, so a
snake_case lesson name is a **single atomic symbol**.

```
recall backup_door_never_ran   -> 4 hits (the lesson itself ranked 4th)
recall backup_door             -> 0
recall cold_encounter          -> 0
recall "cold encounter"        -> 32 hits, including the lesson
```

**A lesson is unreachable by any prefix of its own name** — while every recall-at hook prints
`source: learn:experiment:<name>` and invites you to look it up by that name. The asymmetry was
deliberate (splitting on `_` made `gamma_lesson` match `alpha_lesson` through the shared
fragment "lesson"), and its cost was never measured against the benefit.

---

## What this implies, in order

1. **Capture the missing plane** (T278). Without it, nothing else has the founder's words to
   work on, and directives will keep evaporating.
2. **Expose the dimensions already stored** as a real facet surface. This is the cheap,
   high-leverage step — the data exists.
3. **Adopt bitemporal onto the lesson plane** (three fields, verified). Buys as-of queries and
   closes the replay gap.
4. **Then** fill the embedding sockets, against a surface that already works.

**The reframe worth keeping:** this is not "build retrieval." It is *one missing plane, five
unexposed dimensions, one built-but-unadopted mechanism, and three specified-but-empty
sockets.* Not a rewrite.
