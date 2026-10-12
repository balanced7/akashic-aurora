# AXI bench: `focus`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 29/30 (97%) | +13 pp |
| Output tokens, as the reader counts them (median) | 33 | 77 | +44 (+133%) |
| Stdout characters (all runs) | 242 | 426 | +184 (+76%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which task is this session focused on? | `T001` | 5/5 | 5/5 |
| How many tool calls have been attributed to the focused task? | `0` | 5/5 | 5/5 |
| Does this session have a focus? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which files does the drift check watch for this task? List them separated by commas. | `['core/auth.py', 'core/session.py']` | 5/5 | 5/5 |
| What is the ledger status of the focused task? | `proposed` | 5/5 | 4/5 |
| What exact command checks this session out of its focus? Give the command only. | `['focus', '--clear']` | 0/5 | 5/5 |

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

`aurora focus bench --session s1` (exit 0)

```
# focus T001: 0 call(s) attributed (0 on its files, 0 elsewhere, streak 0)
```

`aurora focus bench --session s2` (exit 0)

```
# no focus. Set one: uv run agent_cli.py focus --set T###
```

`aurora focus bench --session s3 --set T001` (exit 0)

```
# focused T001 (proposed) -- Fix the login redirect
#   drift watched against: core/auth.py, core/session.py
```


## After: output

`aurora focus bench --session s1` (exit 0)

```
focus: T001
calls: 0
on_task_files: 0
elsewhere: 0
miss_streak: 0
help[1]:
  uv run agent_cli.py focus bench --session s1 --clear
```

`aurora focus bench --session s2` (exit 0)

```
focus: none
help[1]:
  uv run agent_cli.py focus bench --session s2 --set T###
```

`aurora focus bench --session s3 --set T001` (exit 0)

```
focus: T001
status: proposed
title: Fix the login redirect
drift_watched[2]: core/auth.py,core/session.py
help[2]:
  uv run agent_cli.py focus bench --session s3
  uv run agent_cli.py focus bench --session s3 --clear
```
