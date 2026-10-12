# AXI bench: `run`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 10/30 (33%) | 27/30 (90%) | +57 pp |
| Output tokens, as the reader counts them (median) | 82 | 208 | +126 (+154%) |
| Stdout characters (all runs) | 988 | 1,813 | +825 (+84%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Did every step of the alias finish successfully? Answer yes or no. | `yes` | 0/5 | 5/5 |
| Which step number failed? | `2` | 0/5 | 5/5 |
| What exit code did the failing step return? | `2` | 5/5 | 5/5 |
| Was the step `alias bench list` run? Answer yes or no. | `no` | 3/5 | 5/5 |
| What exact command would the first step run? Give the command only. | `['alias bench history land']` | 1/5 | 4/5 |
| Which aliases does bench have? List them separated by commas. | `['broken', 'check', 'hist']` | 1/5 | 3/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora alias bench mint check --step alias bench list --step locks` (exit 0)

```
[alias] minted check v1 [GUESS] (UNSORTED) (2 step(s)) -- run: uv run agent_cli.py run bench check
```

`aurora alias bench mint broken --step locks --step defer bench --done nope --receipt x --step alias bench list` (exit 0)

```
[alias] minted broken v1 [GUESS] (UNSORTED) (3 step(s)) -- run: uv run agent_cli.py run bench broken
```

`aurora alias bench mint hist --step alias bench history $1` (exit 0)

```
[alias] minted hist v1 [GUESS] (UNSORTED) (1 step(s)) -- run: uv run agent_cli.py run bench hist
```

`aurora run bench check` (exit 0)

```
[run:check] -> alias bench list
# toolbelt: bench -- 3 active (quota 20; evidence confesses: GUESS = never pinned)
  [UNSORTED]
    broken               v1  [GUESS]  3 step(s): locks -> defer -> alias
    check                v1  [GUESS]  2 step(s): alias -> locks
    hist                 v1  [GUESS]  1 step(s): alias
[run:check] -> locks
# no advisory path-locks held
[run:check] done
```

`aurora run bench broken` (exit 2)

```
[run:broken] -> locks
# no advisory path-locks held
[run:broken] -> defer bench --done nope --receipt x
[defer] "no pending item with id 'nope' (see: defer <you> --list)"
[run:broken] stopped rc=2
```

`aurora run bench hist land --dry` (exit 0)

```
  alias bench history land
```

`aurora run bench ghost` (exit 1)

```
[run] "no active toolbelt entry 'ghost' for bench (have: broken, check, hist)"
```


## After: output

`aurora alias bench mint check --step alias bench list --step locks` (exit 0)

```
alias: check
result: minted
version: 1
kind: alias
evidence: GUESS
family: UNSORTED
steps[2]: alias bench list,locks
help[2]:
  uv run agent_cli.py run bench check
  uv run agent_cli.py kata bench check
```

`aurora alias bench mint broken --step locks --step defer bench --done nope --receipt x --step alias bench list` (exit 0)

```
alias: broken
result: minted
version: 1
kind: alias
evidence: GUESS
family: UNSORTED
steps[3]: locks,defer bench --done nope --receipt x,alias bench list
help[2]:
  uv run agent_cli.py run bench broken
  uv run agent_cli.py kata bench broken
```

`aurora alias bench mint hist --step alias bench history $1` (exit 0)

```
alias: hist
result: minted
version: 1
kind: macro
evidence: GUESS
family: UNSORTED
steps[1]: alias bench history $1
help[2]:
  uv run agent_cli.py run bench hist <arg1>
  uv run agent_cli.py kata bench hist
```

`aurora run bench check` (exit 0)

```
step 1/2: alias bench list
agent: bench
active: 3
quota: 20
aliases[3]{name,family,version,evidence,steps}:
  broken,UNSORTED,1,GUESS,locks -> defer -> alias
  check,UNSORTED,1,GUESS,alias -> locks
  hist,UNSORTED,1,GUESS,alias
help[2]:
  uv run agent_cli.py run bench <name>
  uv run agent_cli.py kata bench <name>
step 2/2: locks
locks: 0 advisory path-locks held
help[1]:
  uv run agent_cli.py lock <agent_id> <path>
alias: check
status: done
steps: 2
ran: 2
```

`aurora run bench broken` (exit 2)

```
step 1/3: locks
locks: 0 advisory path-locks held
help[1]:
  uv run agent_cli.py lock <agent_id> <path>
step 2/3: defer bench --done nope --receipt x
[defer] "no pending item with id 'nope' (see: defer <you> --list)"
alias: broken
status: stopped
steps: 3
ran: 2
failed_step: 2
failed: defer bench --done nope --receipt x
exit: 2
skipped: 1
help[2]:
  uv run agent_cli.py defer bench --done nope --receipt x
  uv run agent_cli.py kata bench broken
```

`aurora run bench hist land --dry` (exit 0)

```
alias: hist
total: 1
steps[1]: alias bench history land
help[1]:
  uv run agent_cli.py run bench hist land
```

`aurora run bench ghost` (exit 1)

```
error: "no active toolbelt entry 'ghost' for bench (have: broken, check, hist)"
code: NOT_FOUND
help[1]:
  uv run agent_cli.py alias bench list
```
