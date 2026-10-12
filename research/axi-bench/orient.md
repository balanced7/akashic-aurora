# AXI bench: `orient`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 5/30 (17%) | 29/30 (97%) | +80 pp |
| Output tokens, as the reader counts them (median) | 28 | 241 | +213 (+761%) |
| Stdout characters (all runs) | 356 | 1,505 | +1,149 (+323%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many landmarks does the scene contain in total? | `4` | 0/5 | 5/5 |
| Which landmark is shown nearby, in focus? | `bus` | 0/5 | 5/5 |
| What is the authority of the focus claim? Give the value only. | `mechanical_source` | 0/5 | 5/5 |
| How many blind spots does the scene report? | `2` | 0/5 | 4/5 |
| What is the full command to return to ambient awareness? Give the command only. | `['sweep', 'bench']` | 0/5 | 5/5 |
| Did the command produce a scene? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora orient` (exit 0)

```
# orient subject=bench target=ambient density=compact depth=surface effects=none
  focus ambient awareness (no destination supplied)
  nearby bus
  periphery 3 contour(s): bench, route, moved
  return {'verb': 'sweep', 'args': {'agent': 'bench'}}
  blind=0 | truth floor=always
```

`aurora orient verb:recall` (exit 0)

```

```

`aurora orient bogus:x` (exit 2)

```
ERROR: unsupported orient destination kind 'bogus'; use verb, seat, or thread
```


## After: output

`aurora orient` (exit 0)

```
subject: bench
target: ambient
density: compact
depth: surface
effects: none
focus: ambient awareness (no destination supplied)
landmarks_total: 4
landmarks[4]{name,place,status,summary}:
  bus,nearby,OK,1 pending; 1 shown; 1 need attention; online=none
  bench,contoured,OK,0 parked
  route,contoured,UNATTENDED,"UNATTENDED: no beat, pulse, or worklive"
  moved,contoured,UNKNOWN,mark absent; movement unknown
blind_total: 0
return: uv run agent_cli.py sweep bench
help[1]:
  uv run agent_cli.py orient verb:<name> --agent bench
```

`aurora orient verb:recall` (exit 0)

```
subject: bench
target: "verb:recall"
density: compact
depth: surface
effects: none
focus:
  summary: declared=observed; reachable=observed; authorized=unknown; wired=observed
  authority: mechanical_source
  claim_kind: observed
  currency: unknown
  identity_state: unknown
  risk: ordinary
  folded_fields: 8
landmarks_total: 4
landmarks[4]{name,place,status,summary}:
  bus,nearby,OK,1 pending; 1 shown; 1 need attention; online=none
  bench,contoured,OK,0 parked
  route,contoured,UNATTENDED,"UNATTENDED: no beat, pulse, or worklive"
  moved,contoured,UNKNOWN,mark absent; movement unknown
blind_total: 2
blind[2]: "fresh runtime proof: no canonical verb-to-receipt resolver",test reference scan was truncated
return: uv run agent_cli.py sweep bench
help[1]:
  uv run scripts/checkers/check_door_parity.py --report
```

`aurora orient bogus:x` (exit 2)

```
error: "unsupported orient destination kind 'bogus'; use verb, seat, or thread"
code: USAGE
help[1]:
  uv run agent_cli.py orient verb:<name> --agent bench
```
