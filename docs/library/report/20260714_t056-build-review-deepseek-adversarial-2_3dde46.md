---
akashic_id: art_20260714_t056-build-review-deepseek-adversarial-2_3dde46
akashic_sha: 9fa2453db593
status: draft
type: report
date: 2026-07-14
title: T056 Build Review — deepseek adversarial (2026-07-14)
gist: "# T056 Build Review — deepseek adversarial (2026-07-14) **Verdict: GREEN.** Pins K1-K7 verified one pass; zero findings that block task-done"
tenant: solo
visibility: fleet
seats: []
category: [conducting, governance, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_r5-cost-telemetry-reconciliation-build-s_d7f3a8
    rel: cites
created: "2026-07-14T18:19:53"
updated: "2026-07-23T21:42:17"
---
<!-- GENERATED PROJECTION of art_20260714_t056-build-review-deepseek-adversarial-2_3dde46 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T056 Build Review — deepseek adversarial (2026-07-14)

# T056 Build Review — deepseek adversarial (2026-07-14)

**Verdict: GREEN.** Pins K1-K7 verified one pass; zero findings that block task-done.
Three touch-points verified with exact line citations. Hot-path contract intact.

Build commit: 0bc1ffa (2026-07-14)
Reviewed: core/coord/task_costs.py + core/coord/task_ledger.py diff + core/comm/turn_metrics.py diff

---

## K1 — Attribution Gate: GREEN

- `_active_task_for` (task_costs.py:45-55) does owner match + status filter on
  `(in_progress, verifying)` — exact.
- Defensive `len(hits) == 1` guard (line 54): 0 → None, >1 → None. The >1 case
  is reachable: the serialize gate (task_ledger.py:196) only blocks IN_PROGRESS,
  not VERIFYING, so an agent CAN own A(VERIFYING) + B(IN_PROGRESS) simultaneously
  — attribution correctly refuses (under-report per C5).
- The one-in-progress gate is GLOBAL (task_ledger.py:198: "Phase 1 runs one at a
  time"), making single-owner-scope attribution exact when it fires.
- Test `test_k1_owner_matched_active_task_increments` (line 75-88): owner-own-task
  increments, cross-owner no-op, done-task no-op. All three arms covered.

## K2 — Hot-Path Contract: GREEN

- `turn_metrics.record()` calls `attribute_turn(agent, row)` inside the existing
  fail-open `try` (turn_metrics.py:137-141). The call is AFTER the recording push
  (line 128) and the event capture (line 131-134) — turn measurement completes
  independently.
- `attribute_turn` is itself fail-open internally (task_costs.py:76-77: `except
  Exception: return None`).
- Redis operations: 1 HINCRBY per field (4 max; tokens conditional) — bounded.
- Test `test_k2_redis_down_is_a_noop` (line 90-98): monkeypatches `_client` to
  None, verifies no-op + no-raise. ✅

## K3 — Finalize: GREEN

- `finalize` (task_costs.py:81-105): hgetall → delete → stamp → return. Deletes
  accumulator BEFORE applying stamps — if the process crashes between delete and
  git save, the task reverts to VERIFYING (git is source of truth), next DONE
  transition finds empty accumulator, stamps nothing. Under-report per C5.
- `finalize` is called INSIDE the DONE gate (task_ledger.py:209-211) BEFORE
  status=done is set and BEFORE save(). Stamps + DONE status ride the same atomic
  git write.
- Test `test_k3_finalize_stamps_and_deletes` (line 102-116): verifies stamp values,
  accumulator deletion, missing-accumulator no-op. ✅

## K4 — Bounce / Idempotence: GREEN

- `finalize` guard (task_costs.py:90-91): `if not acc or int(acc.get("turns", 0)
  or 0) <= 0: return {}`. Once the accumulator is deleted by first finalize, every
  subsequent call finds an empty/nonexistent key → returns `{}` → task dict unchanged.
- The DONE status is terminal (TRANSITIONS["done"] = set()), so the gate path
  won't call `finalize` twice — the test calls it directly, which is the right
  adversarial probe.
- Test `test_k4_finalize_is_once` (line 120-130): first stamp, second call on same
  task → cost_turns unchanged. ✅

## K5 — Goodhart Guard (Retro-Only): GREEN

- `cost_line` (task_costs.py:118-143): FIRST check is `str(task.get("status")) !=
  "done"` → returns `""`. Defense in depth: even if called with a live task dict
  carrying cost stamps, it renders nothing.
- Only caller: `format_state` (task_ledger.py:338-339), which iterates
  `v["done"]` (state_view's done-filtered list). No other render path exists.
- `state_view` → `summ()` (task_ledger.py:289-296) passes through `cost_*` keys
  for ALL statuses, BUT consumers (agent_cli.py:1030-1042, 1100-1120;
  conductor.py:139) use only non-cost fields. The render gate is in `cost_line`,
  not in the summary pass-through — correct layering.
- Test `test_k5_no_cost_on_live_tasks` (line 134-141): verifies claimed,
  in_progress, verifying all render `""`. ✅

## K6 — Render Budget + Drop Order: GREEN

- Parts array order: `[turns, duration_s, tools, tokens]` (task_costs.py:127-136).
- Pop loop (line 139-141): `parts.pop()` removes last element → tokens, then tools,
  then duration. Loop stops at `len(parts) > 1` → turns never drop.
- Final `line[:LINE_BUDGET]` (line 142) as last-resort hard truncation.
- `_fmt_tokens` (line 108-115): G/M/k thresholds reasonable.
- Test `test_k6_done_render_budget` (line 144-157): normal case under budget,
  10^12-token case forces drop — both verified. Edge not covered: pathological
  turn count >10^19 chars (absurd; hard truncation is correct fallback). Not a
  finding.

## K7 — Absent Honesty: GREEN

- `cost_line` guard (task_costs.py:125-126): `turns = task.get("cost_turns")` /
  `if not turns: return ""` — falsy turns (None, 0, missing key) → no render.
- `finalize` only stamps `cost_turns` when `int(acc.get("turns", 0) or 0) > 0`
  (task_costs.py:90-91), so stamped tasks always have ≥1 turns.
- Test `test_k7_pre_t056_tasks_render_nothing` (line 160-166): no cost_* keys →
  `""`. ✅

---

## NO FINDINGS

All seven pins pass on source review. No adversarial finding that would block
task-done. The build is faithful to the reconciled spec
(research/reviewed/r5-cost-telemetry-reconciliation-2026-07-14.md). Three
touch-points clean: hot-path call-through is fail-open-isolated, DONE transition
finalize is correctly ordered, format_state renders retro-only with correct drop
order.

**T056 → DONE.**
