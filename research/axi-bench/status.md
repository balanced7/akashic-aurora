# AXI bench: `status`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 10/20 (50%) | 20/20 (100%) | +50 pp |
| Output tokens, as the reader counts them (median) | 68 | 94 | +26 (+38%) |
| Stdout characters (all runs) | 163 | 192 | +29 (+18%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many lessons are stored in memory? | `3` | 0/5 | 5/5 |
| Is Redis reachable? Answer yes or no. | `yes` | 1/5 | 5/5 |
| Does the narrative spine report any errors? Answer yes or no. | `no` | 4/5 | 5/5 |
| How many agent memory keys are there? | `0` | 5/5 | 5/5 |

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

`aurora status` (exit 0)

```
# system status
  backend     : Redis localhost:16379 (+ File mirror)
  learnings   : 7
  agent memory: 0
  spine health: {'route:unknown': 1, 'route:persist': 2}
```


## After: output

`aurora status` (exit 0)

```
backend: "Redis localhost:16379 (+ File mirror)"
redis: up
lessons: 3
keys:
  learn: 7
  agent_memory: 0
  total: 24
spine_health: ok
spine_counters:
  "route:unknown": 1
  "route:persist": 2
```
