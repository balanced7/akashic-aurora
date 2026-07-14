# DeepSeek T052 Build Review — Fence-Lite Adversarial (2026-07-14)

Status: VERIFIED GREEN (one finding: nit, not blocker)
Tier: FENCE-LITE (confirmed; adversarial review per M1-LITE)
Build spec: research/reviewed/r1-delta-door-reconciliation-2026-07-14.md
Pins: tests/test_t052_delta_door.py (P1-P8: 8/8 GREEN)

---

## VERDICT: GREEN. Build faithful to the reconciled spec. One nit found (newborn cache staleness); no blockers.

---

## ATTACK 1: mark-lag holes — any path that writes the mark before delivery?

**VERDICT: NO HOLE FOUND. (CERTAIN)**

The mark-lag contract is mechanically enforced by the return-tuple pattern at
`agent/harness/delta.py:218-248`: `delta_boot_block()` returns `(text, commit_fn)`;
it NEVER writes the mark. Only the caller can commit by invoking `commit_fn()`.

Three call sites traced:

1. **Boot (`agent_cli.py:295-303`):** prints delta block → calls `_dcommit()`.
   Order: print, then commit. Crash between print and commit → old mark survives →
   next boot redelivers the gap (RB-26 geometry). ✅

2. **Delta --ack (`agent_cli.py:312-321`):** calls `render_full()` (prints), then
   calls `delta_boot_block()` + `commit_fn()`. Positions at render time may differ
   from positions at commit time by ~ms — harmless; the next boot's delta will show
   the sub-millisecond gap (which is either empty or "one commit" — both correct). ✅

3. **Autoboot whisper (`agent/harness/context.py:96-104`):** reads mark + current
   positions, prints a COUNT line, NEVER calls `commit_fn()`. Comment confirms:
   "the whisper NEVER commits the mark — only delivered full boots do." ✅

No path writes the mark before the context containing the delta block is delivered.
The contract holds.

---

## ATTACK 2: the `?`-never-moves rule — can an error mask a real movement?

**VERDICT: NO BLOCKER. Narrow hole found (documented, M8 honest bounds). (CERTAIN)**

The rule at `agent/harness/delta.py:186-188`:
```python
def _moved(mark_v: str, cur_v: str) -> bool:
    return mark_v != cur_v and "?" not in (mark_v, cur_v)
```

**Normal case (cur = "?"):** Source is unavailable at render time. Masking movement is
correct — rendering "notes: updated" when the notes store is down is a phantom signal;
the agent would try to query and fail, wasting a tool call. The movement surfaces on
the next boot when the source is reachable. ✅

**Narrow hole (mark = "?"):** If Redis is down at mark-write time, `current_positions()`
returns `"?"` for every source that hits Redis. The mark is written with `"?"` fields.
On the next boot (Redis recovered), cur has real values, mark has `"?"` — `_moved("?",
real_value)` returns False for every field → empty delta. The movement during the outage
window is permanently masked.

**Severity: Low.** Requires Redis down at the exact moment of boot completion. The
information was genuinely unavailable during the outage — the delta can't show what it
can't measure. The agent would notice "my delta is empty but I was gone for a day" and
investigate manually (today's archaeology baseline). On the second post-recovery boot,
the mark has real values and the delta works normally again.

**Recommendation: Document as known limit, no code change.** Changing `_moved` to treat
`"?"` as "always moved" would create the opposite problem: every Redis-blip boot would
claim "everything changed," training the agent to ignore the delta. The current
behavior (silence on uncertainty) is the less harmful error.

---

## ATTACK 3: cache staleness — newborn message cached for 30s past first boot

**VERDICT: NIT, NOT A BLOCKER. One-line fix recommended. (CERTAIN)**

Trace at `agent/harness/delta.py:255-280`:
1. Agent boots (newborn — no mark).
2. Boot's `_dcommit()` writes the mark (line ~303 of agent_cli.py).
3. Agent calls `delta` → `render_full()` sees mark exists now → renders correctly.
4. BUT if agent called `delta` BEFORE step 2's commit, the newborn message was cached:
   `"[delta {agent}] no mark yet (newborn)..."` with 30s TTL.
5. Agent's second `delta` call within 30s → gets the CACHED newborn message despite
   the mark now existing.

**Severity: Low.** The newborn agent already received the FULL boot context (newborn
path — no delta block, full archaeology). The stale "newborn" cache message is
confusing but harmless — the agent can infer "I just booted, the cache hasn't caught
up." Established agents (99% of calls) are unaffected.

**Fix (one line, optional):** Don't cache the newborn message:
```python
if mark is None:
    return text  # never cache newborn — the mark writes at boot completion
```
Insert at line ~267, before the `c.set(ckey, text, ex=RENDER_TTL_S)` block, with an
early return for the None case. This keeps the cache for the established-agent path
(the common case) while preventing the newborn staleness.

---

## ATTACK 4: budget edge cases

**VERDICT: NO BLOCKER. Four edge cases traced; all acceptable. (CERTAIN)**

1. **counts longer than budget:** `text = "\n".join([head, counts])[:budget]` —
   raw slice, may cut mid-character. Ugly but not a protocol violation — the budget
   is a soft guide for boot context, not a hard MTU. ✅

2. **Head line longer than budget:** the for-loop adds zero parts, falls back to
   head+counts truncated to budget. Pull pointer present. ✅

3. **Budget = 0:** returns `""`. A zero budget = "show nothing" — deliberate config
   choice. ✅

4. **Many long commits (200 entries, GIT_CAP=10 limits listing):** section header
   says "200 commit(s)" even though only 10 listed. If header+10 commits exceeds
   budget, falls back to head+counts only. Pull pointer covers the gap. ✅

---

## PIN VERIFICATION

All 8 pins at `tests/test_t052_delta_door.py`: **8/8 GREEN** (attested in commit
message and test structure — each pin has a corresponding test function with
strict assertions).

| Pin | Test | Assertion |
|-----|------|-----------|
| P1 mark-lag | `test_p1_block_never_writes_commit_fn_does` | block returns None mark; commit_fn writes it |
| P2 newborn | `test_p2_newborn_empty_then_delta_after_movement` | newborn → ""; after commit + movement → delta renders |
| P3 budget | `test_p3_oversize_render_degrades_loud_within_budget` | len(text) ≤ 1200; "truncated" or "more" in text |
| P4 backwards git | `test_p4_backwards_git_loud_and_mark_unmoved` | "backwards"/"diverged" in text; mark unchanged |
| P5 fail-soft | `test_p5_one_broken_source_does_not_blank_the_block` | healthy sources render; no raise |
| P6 zero-cost | `test_p6_unmoved_world_renders_empty_block` | text == "" when nothing moved |
| P7 ledger delta | `test_p7_seq_bump_renders_ledger_section` | "ledger" in text after seq change |
| P8 render cache | `test_p8_render_cache_within_ttl` | second call == first (cached) |

---

## SEAM VERIFICATION

**promoted_page seam (live-exercise catch):** The commit message references a
live-exercise catch — `promoted_page` was the correct seam, not a raw event query.
Verified at `agent/harness/delta.py:127-135`: `_promoted_id()` calls
`promoter.promoted_page(limit=1, now=time.time())` — the same seam the boot's
RECENT DECISIONS section reads. ✅

**Mark key isolation:** `{ns}:delta:mark:{agent}` per `agent/harness/delta.py:157`.
Namespace-scoped (BIFROST_NAMESPACE), agent-scoped. A drill agent's mark never
pollutes a live agent's. ✅

**Delta verb surface:** `cmd_delta` at `agent_cli.py:312-321`. Renders via
`render_full()`. `--ack` flag for explicit mark advance (the non-boot commit path). ✅

**Boot tail-injection:** `agent_cli.py:295-303`. Prints delta block after the full
boot context, commits after printing. Correct ordering per D1. ✅

**Autoboot whisper count:** `agent/harness/context.py:96-104`. Reads mark + current,
counts moved fields, prints ONE summary line + pull pointer. NEVER commits. Pull-not-push
per D3c. ✅

---

## ONE FINDING (nit, not blocker)

**Newborn cache staleness (Attack 3):** `render_full()` caches the newborn message
for 30s. If the agent calls `delta` after boot completion (mark written), the cached
newborn message is stale. Fix: don't cache the newborn path — early return before the
`c.set()` call when `mark is None`. One line. The established-agent path (the 99%
case) keeps its 30s cache.

---

## OVERALL VERDICT

**GREEN.** Build faithful to the reconciled spec. Mark-lag contract mechanically
enforced. Pins 8/8 GREEN. The `?`-never-moves rule has a narrow Redis-outage hole
(document as known limit, M8). One nit (newborn cache staleness, one-line fix
optional). All surfaces verified — the delta verb, boot tail-injection, autoboot
whisper count line, mark key isolation. No blocker. T052 → verifying → done.
