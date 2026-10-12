# AXI bench: `college`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 28/30 (93%) | 28/30 (93%) | +0 pp |
| Output tokens, as the reader counts them (median) | 115 | 224 | +109 (+95%) |
| Stdout characters (all runs) | 640 | 1,111 | +471 (+74%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Who is the designated auditor of the course? | `kimi` | 5/5 | 5/5 |
| How many source records does the course have? | `2` | 5/5 | 5/5 |
| Is the lecture sealed? Answer yes or no. | `yes` | 5/5 | 5/5 |
| How many gaps does the course still have? | `2` | 5/5 | 5/5 |
| Is the lecture of this course sealed? Answer yes or no. | `no` | 4/5 | 3/5 |
| Why was the start refused? | `already exists` | 4/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora college show bus-ordering` (exit 0)

```
# college bus-ordering -- How the bus orders messages
roles lecturer=claude  auditor=kimi
stages sources=2  lecture=sealed  audit=1  teachback=0  errata=0
integrity events=OK  lecture=OK
gaps audit coverage is not explicitly closed by the designated auditor | no teach-back recorded
effects none
```

`aurora college show fresh-course` (exit 0)

```
# college fresh-course -- Wake seats
roles lecturer=sol  auditor=deepseek
stages sources=0  lecture=0  audit=0  teachback=0  errata=0
integrity events=OK  lecture=UNSEALED
gaps no verified primary source | lecture is not sealed | no claim audit recorded | no teach-back recorded
effects none
```

`aurora college start bus-ordering --title x --topic y --lecturer a --auditor b --actor a` (exit 2)

```
ERROR: college course 'bus-ordering' already exists
```


## After: output

`aurora college show bus-ordering` (exit 0)

```
course: bus-ordering
title: How the bus orders messages
lecturer: claude
auditor: kimi
sources: 2
verified_primary: 1
lecture: sealed
audit_claims: 1
teachbacks: 0
errata: 0
integrity: ok
gaps[2]: audit coverage is not explicitly closed by the designated auditor,no teach-back recorded
help[1]:
  uv run agent_cli.py college audit bus-ordering --claim-id <id> --claim <claim> --anchor <excerpt> --species <s> --verdict <v> --receipt <r> --source <source-id> --coverage-complete --coverage-receipt <r> --actor kimi
```

`aurora college show fresh-course` (exit 0)

```
course: fresh-course
title: Wake seats
lecturer: sol
auditor: deepseek
sources: 0
verified_primary: 0
lecture: unsealed
audit_claims: 0
teachbacks: 0
errata: 0
integrity: ok
gaps[4]: no verified primary source,lecture is not sealed,no claim audit recorded,no teach-back recorded
help[1]:
  uv run agent_cli.py college source fresh-course --id <id> --title <title> --locator <locator> --kind primary --status verified --receipt <r> --retrieved-at <iso-time> --actor deepseek
```

`aurora college start bus-ordering --title x --topic y --lecturer a --auditor b --actor a` (exit 2)

```
error: college course 'bus-ordering' already exists
code: REFUSED
help[1]:
  uv run agent_cli.py college show bus-ordering
```
