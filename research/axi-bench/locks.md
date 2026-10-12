# AXI bench: `locks`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 3 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 14/15 (93%) | 15/15 (100%) | +7 pp |
| Output tokens, as the reader counts them (median) | 101 | 119 | +18 (+18%) |
| Stdout characters (all runs) | 185 | 218 | +33 (+18%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which agent holds the lock on docs/x.md? | `bob` | 3/3 | 3/3 |
| How many locks are held in total? | `3` | 3/3 | 3/3 |
| Which paths does alice hold locks on? List them separated by commas. | `['core/a.py', 'scripts/y.py']` | 3/3 | 3/3 |
| What is the TTL, in seconds, of the lock on docs/x.md? | `120` | 3/3 | 3/3 |
| Does carol hold any lock? Answer yes or no. | `no` | 2/3 | 3/3 |

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

`aurora locks` (exit 0)

```
# 3 advisory path-lock(s) held
  core/a.py  <- alice  token 1  [1s old, ttl 600s]
  docs/x.md  <- bob  token 2  [0s old, ttl 120s]
  scripts/y.py  <- alice  token 3  [0s old, ttl 600s]
```


## After: output

`aurora locks` (exit 0)

```
count: 3
locks[3]{path,agent,ttl_s,age_s}:
  core/a.py,alice,600,1
  docs/x.md,bob,120,0
  scripts/y.py,alice,600,0
help[2]:
  uv run agent_cli.py unlock <agent_id> <path>
  uv run agent_cli.py recall-at --path <path>
```
