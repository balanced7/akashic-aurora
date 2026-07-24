---
akashic_id: art_20260711_w3-rb-8-dictstore-differential-deepseek_1d516f
akashic_sha: c248fee872bb
status: draft
type: report
date: 2026-07-11
title: W3 RB-8 + DictStore Differential — DeepSeek VERIFY review (complete)
gist: "# W3 RB-8 + DictStore Differential — DeepSeek VERIFY review (complete) Date: 2026-07-11. Author: deepseek, verify gate (read-only). Spec und"
tenant: solo
visibility: fleet
seats: []
category: [substrate, bus, security]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260711_wave-3-reconciled-build-spec-rb-8-12-dic_4f427b
    rel: cites
created: "2026-07-11T05:47:47"
updated: "2026-07-23T21:42:18"
---
<!-- GENERATED PROJECTION of art_20260711_w3-rb-8-dictstore-differential-deepseek_1d516f -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# W3 RB-8 + DictStore Differential — DeepSeek VERIFY review (complete)

# W3 RB-8 + DictStore Differential — DeepSeek VERIFY review (complete)

Date: 2026-07-11. Author: deepseek, verify gate (read-only).
Spec under review: docs/w3-build-spec-2026-07-11.md sections RB-8 + DictStore differential.
Impl under review: commit b044d6b (frozen, push held for this verdict).
Delivered: bus (chunked across two cursors — this file is the authoritative durable copy per
the contested-bus doctrine; parts herein are the union of bus fragments + DictStore-lane
findings intended for the builder).

## PART 1 — RB-8 SENTINEL SEMANTICS (delivered to Claude seat via bus)

### 1. The explicit --supersedes split: AFFIRMED

The split in `cmd_note` (agent_cli.py ~1138-1146) is correct:
- Explicit `--supersedes` → `decide()` single attempt. Retrying would silently supersede
  the WRONG record (the caller named a specific prior; if retry switches to the current
  head, that contradicts the explicit intent).
- Title re-note → `decide_with_retry()`. The helper owns the pointer resolution; retrying
  with a corrected head IS the correct behavior here.

### 2. Misleading error message for stale explicit targets: FINDING

When explicit `--supersedes ADR_OLD` fails CAS because sentinel=ADR_CURRENT, the current
error message (agent_memory.py:203-204) is:

> "lost the title race for '{title}': current head is {result}; re-read and retry against
> it (decide_with_retry does this)"

For an EXPLICIT target, this message SUGGESTS retrying — but retrying is WRONG (it would
supersede a record the user didn't name). The message is correct for genuine
decide_with_retry races but misleading for explicit targets.

**Recommended fix:** In `cmd_note`'s explicit-supersedes branch, pre-read the sentinel key
BEFORE calling `decide()`:

```python
head = mem.store.get(HEAD_KEY_PREFIX + normalize_title(title))
if head and head != supersedes and mem._is_active(head):
    → refuse: "refused: explicit target {supersedes} is not the current head
     (head is {head}). Drop --supersedes to auto-resolve, or use --supersedes {head}."
if not head:
    → refuse: "no existing note for this title; drop --supersedes for a fresh first note."
```

This also serves as the RB-10 pre-write validation (target existence + non-self + active)
called for in the spec, saving the write+CAS+cleanup cycle for invalid targets.

**Severity:** Non-blocking. The stale-target case reaches CAS → loses → gets an error.
The error is technically correct (the race was lost) but the suggested remedy is wrong
("retry against the head" would supersede the wrong record). Can ship as-is and fix in
the RB-10 slice where pre-write validation is spec'd.

### 3. RB-10 validation gap: CONFIRMED (pre-acknowledged)

The spec says "target must exist, must not be self, must be ACTIVE." None of these are
implemented yet in `decide()` or `cmd_note`. Pre-acknowledged — RB-10 is the next slice
pair and explicitly owns these checks. Not a finding against RB-8.

### 4. decide_with_retry vs decide() docstring alignment: OK

`decide_with_retry` docstring says "callers with an EXPLICIT target use decide() and
handle SupersedeRaceError themselves." The `cmd_note` explicit branch does exactly this
— catches SupersedeRaceError at line 1152 and prints an ERROR line. Correct.

## PART 2 — RB-12 TIEBREAKER GAPS (delivered to Claude seat via bus)

### 5. get_decisions() sort: single-key

`get_decisions()` (agent_memory.py:278) still sorts `key=lambda x: x.created_at`
— single key. The spec says `(created_at, title, id)`. `_resolve_head()` already uses
`(created_at, id)` — two keys, deterministic because id is unique — but `get_decisions()`
is the primary surface for notes rendering, boot RECENT NOTES, and the governing-arc
picker. Without the secondary sort, same-timestamp ties have unstable order.

**Severity:** Non-blocking for RB-8. The sentinel eliminates title-level forks; same-title
ties are now impossible within a chain. Cross-title ties (two different titles sharing
a timestamp) are rare and the render instability is cosmetic. Fix in RB-12.

### 6. _orientation_header candidates: no pre-sort

The governing-arc selection (agent_cli.py ~1032: `match = next((c for c in candidates
if c[0]), None)`) picks first-match-wins. Candidates inherit ordering from
`get_decisions()`'s single-key sort. When two governing candidates share a created_at
timestamp, the winner depends on iteration order — unstable.

**Recommended fix:** Pre-sort candidates before selection:
```python
candidates.sort(key=lambda c: (c[0], c[2]))  # governs (True first), then doc path
```

**Severity:** Non-blocking for RB-8. Same-timestamp governing-arc ties have never been
observed in the corpus. The 2026-07-11 incident was caused by stale-arc retention,
not tie instability. Fix in RB-12.

## PART 3 — DICTSTORE + ZSET ORDERING (builder-lane findings)

### 7. DictStore: spec-faithful

`DictStore(FileStore)` in core/foundation/store.py:862-896:
- ✅ Pure in-memory (no-op _load/_flush)
- ✅ TTL ops raise NotImplementedError loudly (cut list #3)
- ✅ RLock atomicity (inherited from FileStore)
- ✅ cas atomic under lock (inherited from FileStore)
- ✅ Decision paths never touch TTL — no regression risk

Minor observation: a `DictStore()` constructor leaves `self._path = None`. The FileStore
`_load()` and `_flush()` are overridden to no-ops, so no disk path is ever accessed.
Clean.

### 8. Zset ordering fix: CORRECT AND SAFE

The fix in `zrange()` and `zrangebyscore()` (store.py:570-611) sorts `(score, member)`
to match Redis's documented lexicographic-by-member tie-breaking. This was caught
LIVE by the differential harness on first run — FileStore used insertion-order, Redis
used lexicographic, the RB-12 cross-backend render instability my half named.

**Impact on existing consumers (full analysis):**

| Consumer | File | What it does with zrange/zrangebyscore | Affected? |
|---|---|---|---|
| agent_memory.get_decisions | agent_memory.py:271 | zrangebyscore → append → sort by created_at | ⚠️ Input order changed, but subsequent `decisions.sort(key=lambda x: x.created_at)` wipes the zset order. If two records share created_at, the sort is unstable on both old AND new code — the old instability was insertion-order vs zset-order vs sort-order. The new instability is ONLY the sort-order tie (which RB-12 fixes). Net: NO regression, RB-12 gap pre-existing. |
| agent_memory.record (experiences) | agent_memory.py:315,338 | zrange(desc=True) → iterate | ⚠️ Same-score experiences could reorder. Experience retrieval is quality-ranked later; same-score ordering has never been a contract. Negligible. |
| agent_memory reflections | agent_memory.py:378 | zrange(desc=True) → iterate | Same as experiences — negligible. |
| beat_log beats | beat_log.py:119,123 | zrange/zrangebyscore → iterate | Beats have sub-millisecond timestamps; same-score ties near-impossible in practice. |
| chronicler | chronicler.py:165 | zrange → iterate | Full scan; order doesn't matter outside rendering. |
| event_index eviction | event_index.py:96 | zrange → delete oldest | Members with same score: deletion order changes by at most the window=1 boundary. Eviction is approximate by design. |
| migrate_time_scores | migrate_time_scores.py:44,65 | zrange → iterate | One-shot migration script, already run. |
| test_robustness cross-store compare | test_robustness.py:99 | zrange(withscores=True) → assert equality | ✅ NOW CONVERGES where it previously diverged silently. This is a FIX, not a break. |

**Verdict:** The zset ordering fix cannot break any existing contract. Consumers that
rely on deterministic same-score ordering were already broken on RedisStore (which
always used lexicographic) — the fix brings FileStore/DictStore INTO LINE with the
backend that has always governed production behavior.

### 9. Differential harness: spec-faithful

tests/test_store_differential.py:
- ✅ 4 sequences: RB-8 protocol, CAS contention schedule, seeded random soup (seed 4242),
  zset tie-order
- ✅ Return-value comparison AFTER EVERY op
- ✅ Typed final-state dump (kv/hash/zset)
- ✅ Redis-absent → pytest.skip
- ✅ Redis namespace isolation (uuid prefix per run)
- ✅ Teardown cleanup (stale key deletion)

## PART 4 — SUITE, PINS, COVERAGE

### 10. Pre-registered pins: all 10 skip→PASS unweakened

tests/test_w3_supersession_cas.py at HEAD correctly guarded with `_W3_BUILT` skip
guard. With RB-8 impl landed, all 10 tests flip skip→PASS. Zero assertion changes —
M3 compliance confirmed.

### 11. Full-suite regression: two transient flakes, both pre-existing

- test_killwindow_drill::test_w3_duplicate_reply_is_the_accepted_tolerance — flake
- test_wake_detect::test_watch_keeps_waiting_through_trace_and_exits_quiet — flake
Both pass in isolation. Live-bus race class, pre-existed before Wave 3. Not RB-8
regression. Full suite otherwise green.

### 12. Door coverage: complete for decisions

All `mem.decide()` call sites:
- ✅ cmd_note explicit --supersedes (line 1140)
- ✅ cmd_note re-note (line 1146, decide_with_retry)
- ✅ wrap --focus (line 1329, decide_with_retry)
- ✅ wrap where-we-are (line 1373, decide_with_retry)
- ⚪ Tests — direct decide() calls, correct for test isolation

No other production `decide()` calls exist. No experiences/reflections doors modified
— those data types don't participate in title supersession chains. Correct scope.

### 13. Interleavings the pins miss (failure-mode audit)

Three gaps, all pre-acknowledged:

| Gap | Cause | Severity | Mitigation |
|---|---|---|---|
| Orphaned sentinel (crash between hset and claim) | Process dies after writing record but before CAS | New record exists, sentinel unchanged → not surfaced as active. Next re-note supersedes the OLD head, missing the orphan. Self-heals on the first re-note that reads the sentinel correctly, BUT the orphan stays active-unheaded. | Doctor scan (cut list #4). Not auto-repaired. |
| Visibility window (crash between claim and retire) | CAS succeeds, process dies before _retire_record | New record is head, old record not yet superseded. Reader sees head → new; scan sees both. | Self-heals on next re-note (new head -> retire old). No fork created. |
| DictStore RLock serialization in threaded smoke | test_threaded_door_smoke uses DictStore → all threads serialized under RLock | True Redis concurrency (interleaved cas cycles) not tested | Known limitation; no latency-injector harness exists. The differential harness tests return-value semantics per op, which IS the contract. |

## FINAL VERDICT

**GATE GREEN.** Impl faithfully follows the reconciled spec. All 10 pre-registered pins
pass unweakened. Differential harness caught a real cross-backend ordering bug on first
run and it was fixed at the source. Two RB-12 tiebreaker gaps are cosmetic at this
slice boundary and explicitly owned by the RB-12 spec. The stale explicit-target error
message is a minor UX finding; the remedy (pre-read sentinel before decide) is an RB-10
pre-write validation concern. Door coverage is complete for decision paths. Zset ordering
fix is safe: it converges FileStore with Redis's documented behavior rather than diverging.

No blockers. Push when ready; RB-9 opens after.
