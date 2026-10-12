# AXI bench: `wrap`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 25/25 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 1,094 | 1,502 | +408 (+37%) |
| Stdout characters (all runs) | 3,136 | 3,772 | +636 (+20%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Has this draft already been recorded as a note? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many lessons from this session does the draft draw on? | `1` | 5/5 | 5/5 |
| What exact command records this draft as the where-we-are note? Give the command only. | `['wrap --commit']` | 5/5 | 5/5 |
| Was a note written by this command? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which flag makes wrap overwrite the hand-written note anyway? Give the flag only. | `['--force']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora wrap` (exit 0)

```
[wrap] no routing set for the next window -- the night shift cannot pre-chew without targets.
       Set them with: uv run agent_cli.py wrap --route T123,T124 --commit
# DRAFT where-we-are (review it; record with: uv run agent_cli.py wrap --commit -- the default title supersedes the prior where-we-are)

Learned:
  - port_clash: Use when tests hang at start: check that port 16379 is free first.  (learn:experiment:port_clash)
Decided / noted:
  - where-we-are: Wave 3 done; next: the ledger table.  (mem:decision:ADR_1012180304_33cc9d67)
Recall activation by family (3 injection(s) this session): conductor 0/3 · door 1/3 · preregistered 1/3 · seat 1/3
Recall review (3 lesson(s) surfaced this session -- vote the hits/misses):
  - 1x preregistered-checker-threat-model
    useful: uv run agent_cli.py recall-feedback --source learn:experiment:preregistered-checker-threat-model   |   noise: uv run agent_cli.py recall-feedback --source learn:experiment:preregistered-checker-threat-model --noise
  - 1x seat_commit_identity_conflict
    useful: uv run agent_cli.py recall-feedback --source learn:experiment:seat_commit_identity_conflict   |   noise: uv run agent_cli.py recall-feedback --source learn:experiment:seat_commit_identity_conflict --noise
  - 1x door_gate_cold_start_after_uv_sync
    useful: uv run agent_cli.py recall-feedback --source learn:experiment:door_gate_cold_start_after_uv_sync   |   noise: uv run agent_cli.py recall-feedback --source learn:experiment:door_gate_cold_start_after_uv_sync --noise

# from 0 commit(s), 1 lesson(s), 1 note(s) this session

## ARC SCORECARD (last 0.5d: 0 commit(s)) -- method-baseline reads (T031 hook 3)
  M1   fenced dual pass             UNRECORDED -- nobody wrote it down; this is NOT evidence of absence (self-reported: no detector exists) [self-report]
  M3   pre-registered acceptance    (no signal -- annotate fired/skipped-with-reason in the wrap note)
  M4   drills as acceptance         UNRECORDED -- nobody wrote it down; this is NOT evidence of absence (self-reported: no detector exists) [self-report]
  M5   live-exercise after ship     UNRECORDED -- nobody wrote it down; this is NOT evidence of absence (self-reported: no detector exists) [self-report]
  M6   verbatim preservation        (no signal -- annotate fired/skipped-with-reason in the wrap note)
  M10  guards for new law           (no signal -- annotate fired/skipped-with-reason in the wrap note)
  M11  slice discipline            0 slice(s), 0 revert(s); no substrate ships in window -- gate did not apply
  (M0/M2/M7/M8/M9: judgment practices -- annotate in the wrap note where they fired or were deliberately skipped)
```

`aurora wrap --commit` (exit 1)

```
[wrap] no routing set for the next window -- the night shift cannot pre-chew without targets.
       Set them with: uv run agent_cli.py wrap --route T123,T124 --commit
WARNING: the current 'where-we-are' note is CURATED (hand-written). This wrap draft is MECHANICAL and would overwrite it.
  To supersede deliberately: re-run with --force (review the draft first).
  To record alongside:      uv run agent_cli.py wrap --commit --title "where-we-are-2026-10-12"
(nothing written)
```


## After: output

`aurora wrap` (exit 0)

```
state: draft -- not recorded
record_with: "uv run agent_cli.py wrap --commit (records it as where-we-are, superseding the prior one)"
sources:
  commits: 12
  lessons: 1
  notes: 1
draft[21]{line}:
  "Shipped:"
  "  - wip wrap  (git:1a7b9eff)"
  "  - wip log  (git:54c03914)"
  "  - wip stats  (git:38afca31)"
  "  - wip status  (git:c8175fd0)"
  "  - wip handoff  (git:854bc58b)"
  "  - wip notes  (git:663f3d95)"
  "  - wip note  (git:04f7805b)"
  "  - wip learn  (git:41e41adf)"
  "Learned:"
  "  - port_clash: Use when tests hang at start: check that port 16379 is free first.  (learn:experiment:port_clash)"
  "Decided / noted:"
  "  - where-we-are: Wave 3 done; next: the ledger table.  (mem:decision:ADR_1012180338_828f3603)"
  "Recall activation by family (3 injection(s) this session): conductor 0/3 · door 1/3 · preregistered 1/3 · seat 1/3"
  "Recall review (3 lesson(s) surfaced this session -- vote the hits/misses):"
  "  - 1x preregistered-checker-threat-model"
  "    useful: uv run agent_cli.py recall-feedback --source learn:experiment:preregistered-checker-threat-model   |   noise: uv run agent_cli.py recall-feedback --source learn:experiment:preregistered-checker-threat-model --noise"
  "  - 1x seat_commit_identity_conflict"
  "    useful: uv run agent_cli.py recall-feedback --source learn:experiment:seat_commit_identity_conflict   |   noise: uv run agent_cli.py recall-feedback --source learn:experiment:seat_commit_identity_conflict --noise"
  "  - 1x door_gate_cold_start_after_uv_sync"
  "    useful: uv run agent_cli.py recall-feedback --source learn:experiment:door_gate_cold_start_after_uv_sync   |   noise: uv run agent_cli.py recall-feedback --source learn:experiment:door_gate_cold_start_after_uv_sync --noise"
scorecard[12]{line}:
  "## ARC SCORECARD (last 0.5d: 19 commit(s)) -- method-baseline reads (T031 hook 3)"
  "  M1   fenced dual pass             UNRECORDED -- nobody wrote it down; this is NOT evidence of absence (self-reported: no detector exists) [self-report]"
  "  M3   pre-registered acceptance  MEASURED 0/15 test-adding commit(s) clean (0%)  <-- pins are landing WITH their implementation"
  "  M4   drills as acceptance         UNRECORDED -- nobody wrote it down; this is NOT evidence of absence (self-reported: no detector exists) [self-report]"
  "  M5   live-exercise after ship     UNRECORDED -- nobody wrote it down; this is NOT evidence of absence (self-reported: no detector exists) [self-report]"
  "  M6   verbatim preservation        (no signal -- annotate fired/skipped-with-reason in the wrap note)"
  "  M10  guards for new law           (no signal -- annotate fired/skipped-with-reason in the wrap note)"
  "  M11  slice discipline            19 slice(s), 0 revert(s); MEASURED 0/3 SUBSTRATE ship(s) gated (0%)"
  "       ungated substrate: 1cb8d9e5 wip boot"
  "       ungated substrate: 7595a078 feat(authorship): keep the commit ledger local, with the ses"
  "       ungated substrate: 9dd0446e fix(identity): let each machine name the operator on agent c"
  "  (M0/M2/M7/M8/M9: judgment practices -- annotate in the wrap note where they fired or were deliberately skipped)"
notices[1]{kind,message}:
  routing,no routing set for the next window -- the night shift cannot pre-chew without targets.
help[2]:
  uv run agent_cli.py wrap --commit
  uv run agent_cli.py wrap --route T123,T124 --commit
```

`aurora wrap --commit` (exit 1)

```
error: the current 'where-we-are' note is CURATED (hand-written); this wrap draft is MECHANICAL and would overwrite it (nothing written)
code: CURATED_HEAD
notices[1]{kind,message}:
  routing,no routing set for the next window -- the night shift cannot pre-chew without targets.
help[2]:
  uv run agent_cli.py wrap --commit --force
  uv run agent_cli.py wrap --commit --title "where-we-are-2026-10-12"
```
