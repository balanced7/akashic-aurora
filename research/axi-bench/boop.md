# AXI bench: `boop`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 15/20 (75%) | 20/20 (100%) | +25 pp |
| Output tokens, as the reader counts them (median) | 178 | 9 | -169 (-95%) |
| Stdout characters (all runs) | 468 | 605 | +137 (+29%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the boop received? Answer yes or no. | `yes` | 5/5 | 5/5 |
| How was the boop adjudicated? Give one word. | `useful` | 5/5 | 5/5 |
| How many bus messages are pending for the seat? | `1` | 5/5 | 5/5 |
| What is the full command to read the pending messages? Give the command only. | `['bifrost-sync bench']` | 0/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora boop` (exit 0)

```
boop. (received, subject-labeled, adjudicated USEFUL -- the smallest door in the house)
```

`aurora boop --surface` (exit 0)

```
boop. (received, subject-labeled, adjudicated USEFUL -- the smallest door in the house)
# sweep subject=bench as_of=2026-10-12T15:51:17.810748+00:00 effects=none
  bus: OK 1 pending; 1 shown; order=oldest; truncated=no; attention_shown=1; unrendered=0
  bench: OK 0 parked
  route: UNATTENDED UNATTENDED: no beat, pulse, or worklive
  moved: UNKNOWN mark absent; movement unknown
```


## After: output

`aurora boop` (exit 0)

```
boop: received
adjudicated: useful
```

`aurora boop --surface` (exit 0)

```
boop: received
adjudicated: useful
sweep:
  subject: bench
  as_of: "2026-10-12T15:51:42.839974+00:00"
  pending: 1
  need_attention: 1
  parked: 0
  effects: none
  observations[4]{name,status,summary,drill}:
    bus,OK,1 pending; 1 shown; 1 need attention; online=none,bifrost-sync bench --digest
    bench,OK,0 parked,bench bench
    route,UNATTENDED,"UNATTENDED: no beat, pulse, or worklive",roster --agent bench
    moved,UNKNOWN,mark absent; movement unknown,delta bench
help[2]:
  uv run agent_cli.py bifrost-sync bench --digest
  uv run agent_cli.py delta bench
```
