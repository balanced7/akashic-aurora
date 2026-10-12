# AXI bench: `recall-prevention`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 24/25 (96%) | -4 pp |
| Output tokens, as the reader counts them (median) | 371 | 187 | -184 (-50%) |
| Stdout characters (all runs) | 905 | 406 | -499 (-55%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many stage rows did the report read? | `0` | 5/5 | 5/5 |
| How many prevention candidates are there? | `0` | 5/5 | 5/5 |
| What is the coverage, as a number? | `0` | 5/5 | 4/5 |
| How many observations were VIOLATED? | `0` | 5/5 | 5/5 |
| Does this report change lesson rankings or credit? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora recall-prevention` (exit 0)

```
# recall-prevention -- observation only, never a grade
  stage rows 0 -> 0 observation(s) over 0 lesson(s)
  PREVENTION candidates 0  |  CONTROL arm 0  |  rescue flips 0
  verdicts: VIOLATED 0 · UNKNOWABLE 0 · COMPLIED 0 (unmintable without the Eye)
  settled 0 -> coverage 0.0000  (unattributed repeats: 0)
  ! exposure-bias: a lesson surfaces BECAUSE the matcher judged the moment risky, so surfaced actions are not a random sample -- the control arm is not a matched control
  ! self-inflation: the positive feedback loop credits whatever was surfaced at flip time (resolve_action_outcome) with no causal check; this report deliberately ignores that counter
  ! self-sealing demotion: a benched lesson stops surfacing, so it can never earn the credit that would redeem it -- absence of exposure is not absence of value
  ! COMPLIED is unprovable from this join: silence is UNKNOWABLE, never compliance
```


## After: output

`aurora recall-prevention` (exit 0)

```
authority: observation only -- never a grade; writes no credit and steers no ranking
stage_rows: 0
observations: 0
lessons: 0
prevention_candidates: 0
control_arm: 0
rescue_flips: 0
verdicts:
  VIOLATED: 0
  UNKNOWABLE: 0
  COMPLIED: 0
settled: 0
coverage: 0
unattributed_repeats: 0
result: no action outcomes logged yet -- the harness hooks write the stage log
help[1]:
  uv run agent_cli.py hooks status
```
