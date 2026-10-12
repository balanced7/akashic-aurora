# AXI bench: `pulse`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 16/25 (64%) | 19/25 (76%) | +12 pp |
| Output tokens, as the reader counts them (median) | 77 | 138 | +61 (+79%) |
| Stdout characters (all runs) | 167 | 266 | +99 (+59%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which agent has elevated pressure? | `alice` | 5/5 | 5/5 |
| How many messages are in alice's backlog? | `11` | 5/5 | 5/5 |
| Is any agent in the critical zone? Answer yes or no. | `no` | 1/5 | 4/5 |
| Which agents have no work lane? List them separated by commas. | `['bench', 'carol']` | 5/5 | 5/5 |
| What exact command diagnoses the agent under the most pressure? Give the command only. | `['unwedge', 'alice']` | 0/5 | 0/5 |

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

`aurora pulse` (exit 0)

```
pulse: 1 elevated (alice), 1 normal — watch the elevated lanes
  elevated: alice (backlog=11)
  normal: bob (backlog=0)
  absent: bench (backlog=0), carol (backlog=0)
```


## After: output

`aurora pulse` (exit 0)

```
summary: "pulse: 1 elevated (alice), 1 normal — watch the elevated lanes"
agents: 4
elevated: 1
normal: 1
no_lane: 2
readings[4]{agent,zone,backlog}:
  alice,elevated,11
  bob,normal,0
  bench,no lane,0
  carol,no lane,0
help[1]:
  uv run agent_cli.py unwedge alice
```
