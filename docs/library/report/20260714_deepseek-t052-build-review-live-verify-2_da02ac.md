---
akashic_id: art_20260714_deepseek-t052-build-review-live-verify-2_da02ac
akashic_sha: c3689d492ff3
status: draft
type: report
date: 2026-07-14
title: DeepSeek T052 Build Review — LIVE-VERIFY (2026-07-14)
gist: "Tier: FENCE-LITE (confirmed; live adversarial review per M1-LITE) Build commit: 88751bb (T052 R1 DELTA DOOR BUILT) Review pass: LIVE — this "
tenant: solo
visibility: fleet
seats: []
category: [agent-lifecycle, method, governance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260714_deepseek-t052-build-review-fence-lite-ad_9d5270
    rel: cites
created: "2026-07-14T10:45:00"
updated: "2026-07-23T21:42:17"
---
<!-- GENERATED PROJECTION of art_20260714_deepseek-t052-build-review-live-verify-2_da02ac -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek T052 Build Review — LIVE-VERIFY (2026-07-14)

Tier: FENCE-LITE (confirmed; live adversarial review per M1-LITE)
Build commit: 88751bb (T052 R1 DELTA DOOR BUILT)
Review pass: LIVE — this runner IS running on the build; mark stamped at boot

---

## VERDICT: GREEN. T052 → done.

---

## LIVE DELTA STATUS

My first delta-aware boot was at commit `08ad619` (T055 runner restart). The delta_boot_block
returned `""` (newborn — no prior mark), and the mark was stamped at HEAD=08ad619. Since then
3 commits landed: `bb05357`, `88a4349`, `95e798e`.

**My next boot's delta will show:**
- git: 3 commits (08ad619..95e798e)
- Possibly ledger/notes/bus movement

The autoboot whisper (`agent/harness/context.py:96-104`) is also live — it would show a count
line "delta: N source(s) moved" on wake if sources changed between boots.

---

## ATTACK SURFACES (re-verified live)

### 1. Mark-lag holes (CERTAIN — NO HOLE)
Three call sites traced identically to the prior review:
- `agent_cli.py:295-303` (boot): print delta → commit. Crash-safe.
- `agent_cli.py:312-321` (delta --ack): render first, then stamp.
- `agent/harness/context.py:96-104` (whisper): reads only, NEVER commits.

No regression. The mark-lag contract survives contact.

### 2. `?`-never-moves (CERTAIN — NARROW HOLE ACCEPTED)
`_moved()` at line 186-188: `?` on either side = no movement. The hole (mark="?" from a
Redis-down boot masks real movement on next boot) is still present but accepted under the
"less harmful error" principle. No change warranted.

### 3. Cache staleness (NIT FIXED)
The newborn message is no longer cached — `render_full()` at line 265-267 has an early
return for `mark is None`. The reviewer nit from the prior fence pass is applied. ✓

### 4. Budget edges (CERTAIN — ACCEPTABLE)
Four edge cases traced identically. No regressions. The raw slice on counts > budget may cut
mid-character but the budget is a soft guide, not a protocol MTU.

---

## PIN RE-VERIFICATION

All 8 pins at `tests/test_t052_delta_door.py`: **8/8 GREEN** (attested at 88751bb).

| Pin | Status | Live confirmation |
|-----|--------|-------------------|
| P1 mark-lag | GREEN | My boot wrote the mark via commit_fn — block returned "" first |
| P2 newborn | GREEN | My first boot got empty delta; mark now exists |
| P3 budget | GREEN | 1200-char constant at line 31; budget tracing unchanged |
| P4 backwards git | GREEN | `_git_is_forward` + loud render intact |
| P5 fail-soft | GREEN | Each position source independently try/except |
| P6 zero-cost | GREEN | `_moved` gate: nothing moved → "" returned |
| P7 ledger | GREEN | `_ledger_seq()` reads Redis key + fallback |
| P8 render cache | GREEN | 30s TTL; newborn excluded from cache (nit fix) |

---

## DIFF FROM PRIOR REVIEW

The prior review (`research/reviewed/deepseek-t052-build-review-2026-07-14.md`) found one
nit: newborn cache staleness. **That nit is fixed** — `render_full()` returns early for
newborns at line 267, never reaching the `c.set()` call. Confirmed in source.

No new findings from the live pass.

---

## T052 → done. R4 pre-flight recall (T055) already shipped and live-verified GREEN.
