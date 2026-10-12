# AXI bench: `loop`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 23/25 (92%) | 23/25 (92%) | +0 pp |
| Output tokens, as the reader counts them (median) | 38 | 75 | +37 (+97%) |
| Stdout characters (all runs) | 529 | 672 | +143 (+27%) |
| AXI checks passed | 3/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many candidates are in the archive? | `3` | 5/5 | 5/5 |
| Which candidate is the parent of v2? | `v1` | 4/5 | 5/5 |
| Which candidate is the root ancestor of v2? | `baseline` | 5/5 | 4/5 |
| How much money, in USD, has the loop spent today? | `0` | 5/5 | 5/5 |
| Which flag must be added for `loop run` to start? Give the flag only. | `--daily-usd` | 4/5 | 4/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | fail | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora loop status` (exit 0)

```
{
 "candidates": 3,
 "front": [],
 "spent_today": 0.0,
 "proposers": {}
}
```

`aurora loop archive` (exit 0)

```
  baseline                       parent=-                        pass=None tokens=None  
  v1                             parent=baseline                 pass=None tokens=None  a test-first skill raises the pass rate
  v2                             parent=v1                       pass=None tokens=None  a shorter CLAUDE.md costs fewer tokens
```

`aurora loop lineage --candidate v2` (exit 0)

```
v2 <- v1 <- baseline
```

`aurora loop run` (exit 2)

```
ERROR: `loop run` needs --daily-usd: the loop spends real money and has no default budget
```


## After: output

`aurora loop status` (exit 0)

```
candidates: 3
front: []
spent_today_usd: 0
proposers: []
help[2]:
  uv run agent_cli.py loop archive
  uv run agent_cli.py loop run --candidate baseline --daily-usd 5
```

`aurora loop archive` (exit 0)

```
total: 3
candidates[3]{name,parent,pass_rate,tokens,hypothesis}:
  baseline,null,null,null,null
  v1,baseline,null,null,a test-first skill raises the pass rate
  v2,v1,null,null,a shorter CLAUDE.md costs fewer tokens
help[1]:
  uv run agent_cli.py loop lineage --candidate v2
```

`aurora loop lineage --candidate v2` (exit 0)

```
candidate: v2
depth: 3
lineage[3]: v2,v1,baseline
```

`aurora loop run` (exit 2)

```
error: "`loop run` needs --daily-usd: the loop spends real money and has no default budget"
code: USAGE
help[1]:
  uv run agent_cli.py loop run --candidate baseline --daily-usd 5
```
