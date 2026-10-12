# AXI bench: `corpus`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 25/25 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 26 | 61 | +35 (+135%) |
| Stdout characters (all runs) | 225 | 390 | +165 (+73%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many scenarios does the corpus hold? | `0` | 5/5 | 5/5 |
| What command should be run next to put scenarios into the corpus? Give the command only. | `['corpus mine']` | 5/5 | 5/5 |
| Does the scenario T999-deadbeef exist? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many transcripts were archived by this run? | `0` | 5/5 | 5/5 |
| What is the archive's size cap, in MB? | `2048` | 5/5 | 5/5 |

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

`aurora corpus status` (exit 0)

```
0 scenario(s): {}
accepted 0 (holdout 0, validated 0), oracles {}
areas: {}
candidates run: none yet
```

`aurora corpus list` (exit 0)

```
(empty corpus -- run `corpus mine`)
```

`aurora corpus show T999-deadbeef` (exit 1)

```
ERROR: no scenario 'T999-deadbeef'
```

`aurora corpus archive` (exit 0)

```
archived 0, unchanged 0, refused 0 (0 MB of 2048 MB)
```


## After: output

`aurora corpus status` (exit 0)

```
total: 0
accepted: 0
holdout: 0
validated: 0
candidates_run: none yet
help[1]:
  uv run agent_cli.py corpus mine
```

`aurora corpus list` (exit 0)

```
total: 0
scenarios: []
help[1]:
  uv run agent_cli.py corpus mine
```

`aurora corpus show T999-deadbeef` (exit 1)

```
error: no scenario 'T999-deadbeef'
code: NOT_FOUND
help[1]:
  uv run agent_cli.py corpus list
```

`aurora corpus archive` (exit 0)

```
archived: 0
unchanged: 0
refused: 0
size_mb: 0
cap_mb: 2048
capped: false
help[1]:
  uv run agent_cli.py corpus mine
```
