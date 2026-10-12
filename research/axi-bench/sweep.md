# AXI bench: `sweep`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 20/25 (80%) | 25/25 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 143 | 244 | +101 (+71%) |
| Stdout characters (all runs) | 292 | 506 | +214 (+73%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many bus messages are pending for the seat? | `3` | 5/5 | 5/5 |
| How many of the pending messages need attention? | `1` | 5/5 | 5/5 |
| Is the observed seat attended by a live session right now? Answer yes or no. | `no` | 5/5 | 5/5 |
| Is it known whether anything moved since the seat's last mark? Answer yes or no. | `no` | 5/5 | 5/5 |
| What is the full command to read the pending messages? Give the command only. | `['bifrost-sync bench']` | 0/5 | 5/5 |

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

`aurora sweep bench` (exit 0)

```
# sweep subject=bench as_of=2026-10-12T14:17:31.090677+00:00 effects=none
  bus: OK 3 pending; 3 shown; order=oldest; truncated=no; attention_shown=1; unrendered=0
  bench: OK 0 parked
  route: UNATTENDED UNATTENDED: no beat, pulse, or worklive
  moved: UNKNOWN mark absent; movement unknown
```


## After: output

`aurora sweep bench` (exit 0)

```
subject: bench
as_of: "2026-10-12T14:18:10.119673+00:00"
pending: 3
need_attention: 1
parked: 0
effects: none
observations[4]{name,status,summary,drill}:
  bus,OK,3 pending; 3 shown; 1 need attention; online=none,bifrost-sync bench --digest
  bench,OK,0 parked,bench bench
  route,UNATTENDED,"UNATTENDED: no beat, pulse, or worklive",roster --agent bench
  moved,UNKNOWN,mark absent; movement unknown,delta bench
help[2]:
  uv run agent_cli.py bifrost-sync bench --digest
  uv run agent_cli.py delta bench
```
