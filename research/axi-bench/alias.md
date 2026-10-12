# AXI bench: `alias`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 30/30 (100%) | 29/30 (97%) | -3 pp |
| Output tokens, as the reader counts them (median) | 46 | 73 | +27 (+59%) |
| Stdout characters (all runs) | 795 | 1,233 | +438 (+55%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What version number did the alias get? | `1` | 5/5 | 5/5 |
| What exact command runs the alias that was just minted? Give the command only. | `['run bench land']` | 5/5 | 4/5 |
| How many active aliases does bench have? | `2` | 5/5 | 5/5 |
| What evidence level does the scan alias have? | `VERIFIED` | 5/5 | 5/5 |
| Which version of the land alias is active? | `2` | 5/5 | 5/5 |
| Did retiring ghost succeed? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora alias bench mint land --step status --step locks --family RHYTHM --why close the day` (exit 0)

```
[alias] minted land v1 [GUESS] (RHYTHM) (2 step(s)) -- run: uv run agent_cli.py run bench land
```

`aurora alias bench mint scan --step locks --evidence VERIFIED --tested-against pin-42 --family SENTINELS` (exit 0)

```
[alias] minted scan v1 [VERIFIED] (SENTINELS) (1 step(s)) -- run: uv run agent_cli.py run bench scan
```

`aurora alias bench mint peek --step status` (exit 0)

```
[alias] minted peek v1 [GUESS] (UNSORTED) (1 step(s)) -- run: uv run agent_cli.py run bench peek
```

`aurora alias bench mint land --step status --family RHYTHM` (exit 0)

```
[alias] minted land v2 [GUESS] (RHYTHM) (1 step(s)) -- run: uv run agent_cli.py run bench land
```

`aurora alias bench retire peek --reason unused` (exit 0)

```
[alias] retired peek (unused)
```

`aurora alias bench list` (exit 0)

```
# toolbelt: bench -- 2 active (quota 20; evidence confesses: GUESS = never pinned)
  [RHYTHM]
    land                 v2  [GUESS]  1 step(s): status
  [SENTINELS]
    scan                 v1  [VERIFIED :pin-42]  1 step(s): locks
```

`aurora alias bench history land` (exit 0)

```
  v1 superseded 2026-10-12T14:13:28.505029+00:00: status -> locks
```

`aurora alias bench retire ghost` (exit 1)

```
[alias] REFUSED: "no active toolbelt entry 'ghost' for bench (have: land, scan)"
```


## After: output

`aurora alias bench mint land --step status --step locks --family RHYTHM --why close the day` (exit 0)

```
alias: land
result: minted
version: 1
evidence: GUESS
family: RHYTHM
steps: 2
help[2]:
  uv run agent_cli.py run bench land
  uv run agent_cli.py kata bench land
```

`aurora alias bench mint scan --step locks --evidence VERIFIED --tested-against pin-42 --family SENTINELS` (exit 0)

```
alias: scan
result: minted
version: 1
evidence: VERIFIED
family: SENTINELS
steps: 1
help[1]:
  uv run agent_cli.py run bench scan
```

`aurora alias bench mint peek --step status` (exit 0)

```
alias: peek
result: minted
version: 1
evidence: GUESS
family: UNSORTED
steps: 1
help[2]:
  uv run agent_cli.py run bench peek
  uv run agent_cli.py kata bench peek
```

`aurora alias bench mint land --step status --family RHYTHM` (exit 0)

```
alias: land
result: superseded
version: 2
evidence: GUESS
family: RHYTHM
steps: 1
help[2]:
  uv run agent_cli.py run bench land
  uv run agent_cli.py kata bench land
```

`aurora alias bench retire peek --reason unused` (exit 0)

```
retired: peek
reason: unused
active: 2
help[1]:
  uv run agent_cli.py alias bench list
```

`aurora alias bench list` (exit 0)

```
agent: bench
active: 2
quota: 20
aliases[2]{name,family,version,evidence,steps}:
  land,RHYTHM,2,GUESS,status
  scan,SENTINELS,1,VERIFIED,locks
help[2]:
  uv run agent_cli.py run bench <name>
  uv run agent_cli.py kata bench <name>
```

`aurora alias bench history land` (exit 0)

```
alias: land
current_version: 2
superseded: 1
versions[1]{version,superseded_at,evidence,steps}:
  1,"2026-10-12T14:14:06.511081+00:00",GUESS,status -> locks
```

`aurora alias bench retire ghost` (exit 1)

```
error: "no active toolbelt entry 'ghost' for bench (have: land, scan)"
code: NOT_FOUND
help[1]:
  uv run agent_cli.py alias bench list
```
