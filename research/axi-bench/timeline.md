# AXI bench: `timeline`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 25/25 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 179 | 185 | +6 (+3%) |
| Stdout characters (all runs) | 639 | 691 | +52 (+8%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which actor recorded the test_run row? | `bob` | 5/5 | 5/5 |
| How many rows came from the events domain? | `3` | 5/5 | 5/5 |
| Of the rows from the events domain, what is the kind of the most recent one? | `rollback` | 5/5 | 5/5 |
| Does this output list every row in the time window? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many rows from the events domain fall in the time window? | `3` | 5/5 | 5/5 |

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

`aurora timeline --hours 0.005` (exit 0)

```
# timeline -- 5 row(s) over the last 0.005h
  read: events=3, files=2, tasks=0
  10-12 16:29:18  files                file:modified      .aurora-world
  10-12 16:29:26  events  alice        deploy             deployed api v2 to staging
  10-12 16:29:27  events  bob          test_run           ran suite: 3 failures in auth
  10-12 16:29:27  events  alice        rollback           rolled api back to v1
  10-12 16:29:28  files                file:modified      state/redis-backend
```

`aurora timeline --hours 0.005 --limit 1` (exit 0)

```
# timeline -- 5 row(s) over the last 0.005h
  read: events=3, files=2, tasks=0
  10-12 16:29:28  files                file:modified      state/redis-backend
```


## After: output

`aurora timeline --hours 0.005` (exit 0)

```
window: last 0.005h
total: 3
read: events=3 files=0 git=0 tasks=0
rows[3]{at,domain,actor,kind,summary}:
  "10-12 16:30:09",events,alice,deploy,deployed api v2 to staging
  "10-12 16:30:09",events,bob,test_run,"ran suite: 3 failures in auth"
  "10-12 16:30:10",events,alice,rollback,rolled api back to v1
help[1]:
  uv run agent_cli.py events --get event:events:raw:1791815410282-0
```

`aurora timeline --hours 0.005 --limit 1` (exit 0)

```
window: last 0.005h
total: 3
shown: 1
read: events=3 files=0 git=0 tasks=0
rows[1]{at,domain,actor,kind,summary}:
  "10-12 16:30:10",events,alice,rollback,rolled api back to v1
help[2]:
  uv run agent_cli.py timeline --hours 0.005 --limit 0
  uv run agent_cli.py events --get event:events:raw:1791815410282-0
```
