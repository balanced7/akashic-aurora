# AXI bench: `kata`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 27/30 (90%) | 30/30 (100%) | +10 pp |
| Output tokens, as the reader counts them (median) | 57 | 90 | +33 (+58%) |
| Stdout characters (all runs) | 767 | 1,199 | +432 (+56%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What evidence level does the alias have now? | `VERIFIED` | 4/5 | 5/5 |
| What version number is the alias now? | `2` | 5/5 | 5/5 |
| Which step failed the grammar check? Give the step's command only. | `['--nope']` | 5/5 | 5/5 |
| What evidence level does the alias have after this check? | `GUESS` | 4/5 | 5/5 |
| Did this check change the alias's evidence level? Answer yes or no. | `no` | 5/5 | 5/5 |
| Does bench have an alias called ghost? Answer yes or no. | `no` | 4/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora alias bench mint good --step locks --step alias bench list` (exit 0)

```
[alias] minted good v1 [GUESS] (UNSORTED) (2 step(s)) -- run: uv run agent_cli.py run bench good
```

`aurora alias bench mint bad --step locks --step alias bench list --nope` (exit 0)

```
[alias] minted bad v1 [GUESS] (UNSORTED) (2 step(s)) -- run: uv run agent_cli.py run bench bad
```

`aurora alias bench mint done --step locks --evidence VERIFIED --tested-against pin-1` (exit 0)

```
[alias] minted done v1 [VERIFIED] (UNSORTED) (1 step(s)) -- run: uv run agent_cli.py run bench done
```

`aurora kata bench good` (exit 0)

```
  OK  locks
  OK  alias bench list
[kata] good LEVELED UP: GUESS -> VERIFIED v2 (tested_against=kata-20261012-162402)
```

`aurora kata bench bad` (exit 1)

```
  OK  locks
  FAIL alias bench list --nope   <- agent_cli.py: error: unrecognized arguments: --nope
[kata] bad: a step failed the door's grammar -- evidence stays GUESS. Fix the alias (re-mint) and kata again.
```

`aurora kata bench done` (exit 0)

```
  OK  locks
[kata] done: already VERIFIED -- steps re-confirmed clean.
```

`aurora kata bench ghost` (exit 1)

```
[kata] "no active toolbelt entry 'ghost' for bench (have: bad, done, good)"
```


## After: output

`aurora alias bench mint good --step locks --step alias bench list` (exit 0)

```
alias: good
result: minted
version: 1
evidence: GUESS
family: UNSORTED
steps: 2
help[2]:
  uv run agent_cli.py run bench good
  uv run agent_cli.py kata bench good
```

`aurora alias bench mint bad --step locks --step alias bench list --nope` (exit 0)

```
alias: bad
result: minted
version: 1
evidence: GUESS
family: UNSORTED
steps: 2
help[2]:
  uv run agent_cli.py run bench bad
  uv run agent_cli.py kata bench bad
```

`aurora alias bench mint done --step locks --evidence VERIFIED --tested-against pin-1` (exit 0)

```
alias: done
result: minted
version: 1
evidence: VERIFIED
family: UNSORTED
steps: 1
help[1]:
  uv run agent_cli.py run bench done
```

`aurora kata bench good` (exit 0)

```
alias: good
verdict: leveled up
evidence: VERIFIED
evidence_change: GUESS -> VERIFIED
version: 2
tested_against: kata-20261012-162450
steps_checked: 2
help[1]:
  uv run agent_cli.py run bench good
```

`aurora kata bench bad` (exit 1)

```
alias: bad
verdict: failed
evidence: GUESS
evidence_change: none
version: 1
failed: 1
steps[2]{status,step,error}:
  ok,locks,null
  fail,alias bench list --nope,"unrecognized arguments: --nope"
help[2]:
  uv run agent_cli.py alias --help
  uv run agent_cli.py alias bench mint bad --step '<fixed step>'
```

`aurora kata bench done` (exit 0)

```
alias: done
verdict: already verified
evidence: VERIFIED
evidence_change: none
version: 1
steps_checked: 1
```

`aurora kata bench ghost` (exit 1)

```
error: bench has no active alias named 'ghost'
code: NOT_FOUND
aliases[3]: bad,done,good
help[1]:
  uv run agent_cli.py alias bench list
```
