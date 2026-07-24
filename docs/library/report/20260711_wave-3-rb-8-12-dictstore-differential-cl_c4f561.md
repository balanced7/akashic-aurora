---
akashic_id: art_20260711_wave-3-rb-8-12-dictstore-differential-cl_c4f561
akashic_sha: b3d80209c3dc
status: draft
type: report
date: 2026-07-11
title: Wave 3 (RB-8..12 + DictStore differential) -- claude design half (FENCED)
gist: "# Wave 3 (RB-8..12 + DictStore differential) -- claude design half (FENCED) Date: 2026-07-11. Author: claude, blind half of the fenced dual "
tenant: solo
visibility: fleet
seats: []
category: [security, method, conducting]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_wave-3-deepseek-blind-half-rb-8-12-dicts_dc03b7
    rel: cites
  - target: art_20260701_resilience-battery-sliced-execution-plan_8d660c
    rel: cites
  - target: art_20260723_project-memory-auto-generated-from-notes_f7b52b
    rel: cites
created: "2026-07-11T05:15:36"
updated: "2026-07-23T21:42:13"
---
<!-- GENERATED PROJECTION of art_20260711_wave-3-rb-8-12-dictstore-differential-cl_c4f561 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Wave 3 (RB-8..12 + DictStore differential) -- claude design half (FENCED)

# Wave 3 (RB-8..12 + DictStore differential) -- claude design half (FENCED)

Date: 2026-07-11. Author: claude, blind half of the fenced dual design.
DeepSeek half: research/reviewed/deepseek-w3-design-2026-07-11.md (unread at authoring).
Slice texts: docs/resilience-battery-slices-2026-07.md lines 136-188. Build order
(claude-ruled, Daniel delegated): RB-8 first -- it hardens the one write door RB-9/10/11
touch; the differential harness is born with it. Design-then-build per slice; acceptance
tests pre-register before each impl (M3).

## RB-8 -- CAS on the note-supersession write

### The races, named (agent_memory.py :122-157 + cmd_note :1065+)

- **R-a lost-retire fork.** Two sessions supersede the same title concurrently. Both
  resolve the same prior id, both hset their new record, both retire the same old id.
  Result: TWO active records for one title -- the forked where-we-are the P1 gate forbids.
  Tonight's twin session is the live generator of exactly this shape.
- **R-b retire clobber.** `_retire_record` is hget -> mutate -> hset. Any concurrent
  mutation of that record json (a second retire, a future field write) can be silently
  lost -- classic read-modify-write.
- **R-c id collision.** `_gen_id` = second-resolution timestamp + randint(1000,9999).
  Two writers in the same second collide with p~1e-4 PER PAIR; hset silently overwrites
  the loser's record. Rare is not never; the slice bar is "no fork under concurrency".
- **R-d visibility gap.** New record becomes readable (hset+zadd) BEFORE the old retires;
  a reader in the gap sees two actives. Transient, but boot/notes can render it.
- **R-e title->id lookup race.** cmd_note resolves title -> current id, then writes.
  Resolve and write are not atomic; two writers resolve the same head. (R-a's front half.)

### Fix: per-title HEAD POINTER, CAS'd -- the chain becomes linear by construction

New plain key per normalized title: `mem:decisions:head:<norm-title>` holding the active
record id. Plain key ON PURPOSE: store.cas (:180) speaks GET/SET keys, not hash fields --
the C3 primitive is used as-built, zero new store surface.

Write protocol (in decide(), when a title chain exists or supersedes is given):
  1. norm = normalize(title)   [RB-9's function -- built together]
  2. expected = store.get(head_key)           (None = first note for this title)
  3. hset new record + zadd index             (record exists but is NOT YET the head)
  4. ok = store.cas(head_key, expected, new_id)
  5a. ok: NOW retire the expected old id (_retire_record) -- only the CAS winner retires,
      which closes R-a AND makes R-b's window single-writer in practice.
  5b. !ok (lost the race): re-read head, retry from step 2 against the NEW head, cap 3
      retries, then FAIL LOUD (return "" + logged error + the caller's teaching message
      names the winning head). Never silent, never forked. The loser's step-3 record is
      superseded-marked before erroring (no orphan actives).
  Readers of "active per title" consult the head; scan readers still work (superseded
  flags unchanged in meaning) -- the head is an ARBITER, not a second source of truth
  (it names which record is current; the record itself still carries the flag).

R-c fix: id becomes ADR_<ts>_<uuid4.hex[:8]> -- collision probability drops ~5 orders,
no coordination, ids remain sortable-by-prefix. (Alternative NX-guard write rejected:
extra round-trip for a problem entropy solves.)
R-d: closed for head-readers by protocol order (head flips before retire, and flips
atomically); scan-readers' residual gap = the retire write itself, microseconds, and
RB-12's render orders deterministically so the gap cannot flip a render.

### Migration + failure modes of the fix

- Lazy head bootstrap: on first write to a title with records but no head key, derive
  head from the scan (newest active for norm-title), CAS from None. A one-shot backfill
  script is optional sugar; lazy alone is sufficient and idempotent (RB-11 pins it).
- Head/record drift (head names a vanished or retired id): RB-10's validator detects,
  heals from scan, logs the heal (which side chose what -- RB-25 store-divergence drill
  language).
- Contention livelock: retry cap 3 + loud failure (see 5b). A cap'd CAS loop cannot wedge.
- Redis-down: create_store falls back; DictStore cas is lock-atomic (:414). Differential
  harness proves both backends agree on every step of this protocol.

### Pins (pre-registered before impl)

  1. Two store handles, interleaved supersede of one title (deterministic schedule):
     exactly ONE active head; loser errored loudly; no record left active-but-unheaded.
  2. Retire-vs-supersede interleaving: no lost flag write.
  3. Same-second id generation x1000: zero collisions.
  4. Lazy bootstrap: pre-head corpus + one write -> correct head; re-run = no-op.
  5. Reader in the write gap sees at most one ACTIVE per title via head reads.

## RB-9 -- title normalization at the single write door

normalize(): NFC -> casefold -> strip -> collapse internal whitespace. Applied to the
HEAD KEY and duplicate/lookup comparisons only; the display title stores verbatim (the
record keeps what the author wrote). Read-side lookups (--retire by title, supersede-by-
title) normalize before compare. Existing corpus is ASCII-clean today -- pin ZERO behavior
change on the current notes set; divergent-only-by-normalization titles (the lexicon.md/
LEXICON.md class) are detected at write + by the RB-11 migration scan and FLAGGED, never
auto-merged (which prior wins is a human/agent ruling).

## RB-10 -- supersede-target validation + all-retired-title detector

Validation at the door: supersedes id must EXIST and be ACTIVE. Superseding a superseded
id = back-door fork -> refused with a teaching error naming the current head (errors that
teach, ACI doctrine). Retire of already-retired = idempotent no-op (returns True).
All-retired detector: a title whose records are all superseded (dangling/absent head with
retired bodies) renders in `notes --all` archaeology and a doctor line -- retired-only
truth stays REACHABLE and LABELED (P7's retired-only case), never resurrected silently.

## RB-11 -- migration idempotency pin + chain-length warning

Pin: the P1/T021 migration verbs and the RB-8 lazy bootstrap re-run as no-ops (same store
state hash before/after second run). Chain-length warning: RENDER-side only (ledger stays
clock-free, T025 precedent) -- a title whose chain exceeds 50 renders "(long chain: N)"
in notes; no write-side limit (where-we-are chains are legitimately long; the warning is
signal, not a gate).

## RB-12 -- deterministic ordering + graceful empty-state at boot

Total order everywhere a list renders: sort key (created_at, id) -- created_at alone ties
at second resolution and then leaks dict/scan order. Applies to get_decisions, notes,
boot RECENT NOTES, chronicles/memory.md projection. Pin: same corpus -> byte-identical
render, twice. Empty-state: fresh clone / empty store -> boot and notes render a calm
"(no notes yet)" line and exit 0; pin on an empty DictStore. (RB-18's cold-clone lookback
is Wave 5's cousin; this slice only covers boot/notes surfaces.)

## DictStore differential (Daniel's briefing item)

tests/test_store_differential.py -- an op-sequence runner: sequences of (op, args) applied
to a fresh DictStore AND a Redis store (redis half auto-skips when Redis is absent; runs
in the local suite + ship gate where Redis lives). After EVERY op, observable state
asserted equal: get/hget/hgetall/zrange/cas-return. Sequences: (1) the exact decide/
supersede/retire/bootstrap protocol steps; (2) CAS contention pairs (two handles,
alternating deterministic schedule); (3) seeded-random op soup (fixed seed, pinned -- no
wall-clock anywhere). Divergence output names the first diverging op + both states.
A pytest file, not a daemon; the ship gate runs it (it IS the standing guard).

## What I would NOT build

- A global write lock around decide() -- kills concurrency for a rare race; CAS suffices.
- CRDTs / vector clocks -- five orders of magnitude past the need.
- Auto-merge of normalization collisions -- correctness rulings belong to agents/Daniel.
- Hash-field CAS in the Store -- head-as-plain-key uses the primitive as built (C3);
  extending the store contract is a separate decision nothing here requires.

## Cost

Supersede write: +1 GET +1 CAS (cold path, human-cadence). Boot title reads: +1 GET per
rendered title, amortized by the existing render batch; no hot-path (turn-loop) touches.

## Open questions for reconciliation

  Q1 Loser semantics on CAS failure: retry-against-new-head (my 5b) vs refuse-outright
     ("re-read and re-decide")? Retry preserves author intent; refuse is stricter.
  Q2 Chain-length threshold (50?) and whether where-we-are is exempt.
  Q3 Differential redis-absent policy: skip (my lean) vs fail (forces redis in CI).
  Q4 Does retire_decision (tombstone, no successor) also route through the head CAS
     (head -> sentinel "retired")? My lean: yes -- one protocol, no special case.
