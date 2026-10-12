# AXI bench: `events`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 35/35 (100%) | 35/35 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 306 | 329 | +23 (+8%) |
| Stdout characters (all runs) | 1,873 | 2,218 | +345 (+18%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many raw events does this output list? | `4` | 5/5 | 5/5 |
| Which agent recorded the deploy event? | `alice` | 5/5 | 5/5 |
| Which track is the migration event on? | `data` | 5/5 | 5/5 |
| Is the summary of the migration event shown in full? Answer yes or no. | `no` | 5/5 | 5/5 |
| What exact command would show the full record of the top-ranked event? Give the command only. | `['events', '--get', 'event:events:raw:']` | 5/5 | 5/5 |
| How many events by agent dave are listed? | `0` | 5/5 | 5/5 |
| Does this output show every stored raw event, with none left out? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora events` (exit 0)

```
# 4 recent raw event(s)
  [note] 2026-10-12T16:08:48 CEST  paused the release until the auth fix lands
      event:events:raw:1791814128710-0   by=alice
  [migration] 2026-10-12T16:08:48 CEST  migrated the lessons table to the v3 schema: renamed four columns, backfilled the scope ...[truncated]
      event:events:raw:1791814128226-0   track=data   by=carol
  [test_run] 2026-10-12T16:08:47 CEST  ran suite: 3 failures in auth
      event:events:raw:1791814127717-0   by=bob
  [deploy] 2026-10-12T16:08:47 CEST  deployed api v2 to staging
      event:events:raw:1791814127182-0   track=ops   by=alice

Drill into one:
  uv run agent_cli.py events --get event:events:raw:1791814128710-0
```

`aurora events --search auth failures` (exit 0)

```
# 4 event(s) matching 'auth failures'
  [test_run] 2026-10-12T16:08:47 CEST  ran suite: 3 failures in auth
      event:events:raw:1791814127717-0   by=bob
  [note] 2026-10-12T16:08:48 CEST  paused the release until the auth fix lands
      event:events:raw:1791814128710-0   by=alice
  [migration] 2026-10-12T16:08:48 CEST  migrated the lessons table to the v3 schema: renamed four columns, backfilled the scope ...[truncated]
      event:events:raw:1791814128226-0   track=data   by=carol
  [deploy] 2026-10-12T16:08:47 CEST  deployed api v2 to staging
      event:events:raw:1791814127182-0   track=ops   by=alice

Drill into one:
  uv run agent_cli.py events --get event:events:raw:1791814127717-0
```

`aurora events --agent dave` (exit 0)

```
# 0 recent raw event(s) by dave
  (none)
```

`aurora events --limit 2` (exit 0)

```
# 2 recent raw event(s)
  [note] 2026-10-12T16:08:48 CEST  paused the release until the auth fix lands
      event:events:raw:1791814128710-0   by=alice
  [migration] 2026-10-12T16:08:48 CEST  migrated the lessons table to the v3 schema: renamed four columns, backfilled the scope ...[truncated]
      event:events:raw:1791814128226-0   track=data   by=carol

Drill into one:
  uv run agent_cli.py events --get event:events:raw:1791814128710-0
```


## After: output

`aurora events` (exit 0)

```
count: 4
events[4]{kind,at,agent,track,summary,ref}:
  note,"2026-10-12T16:09:36 CEST",alice,null,paused the release until the auth fix lands,"event:events:raw:1791814176071-0"
  migration,"2026-10-12T16:09:35 CEST",carol,data,"migrated the lessons table to the v3 schema: renamed four columns, backfilled the scope field for every row, rebuilt the... (truncated, 437 chars total)","event:events:raw:1791814175601-0"
  test_run,"2026-10-12T16:09:35 CEST",bob,null,"ran suite: 3 failures in auth","event:events:raw:1791814175170-0"
  deploy,"2026-10-12T16:09:34 CEST",alice,ops,deployed api v2 to staging,"event:events:raw:1791814174795-0"
help[1]:
  uv run agent_cli.py events --get event:events:raw:1791814176071-0
```

`aurora events --search auth failures` (exit 0)

```
query: auth failures
order: "best match first (ranked, not filtered)"
count: 4
events[4]{kind,at,agent,track,summary,ref}:
  test_run,"2026-10-12T16:09:35 CEST",bob,null,"ran suite: 3 failures in auth","event:events:raw:1791814175170-0"
  note,"2026-10-12T16:09:36 CEST",alice,null,paused the release until the auth fix lands,"event:events:raw:1791814176071-0"
  migration,"2026-10-12T16:09:35 CEST",carol,data,"migrated the lessons table to the v3 schema: renamed four columns, backfilled the scope field for every row, rebuilt the... (truncated, 437 chars total)","event:events:raw:1791814175601-0"
  deploy,"2026-10-12T16:09:34 CEST",alice,ops,deployed api v2 to staging,"event:events:raw:1791814174795-0"
help[1]:
  uv run agent_cli.py events --get event:events:raw:1791814175170-0
```

`aurora events --agent dave` (exit 0)

```
agent: dave
count: 0
events: []
help[2]:
  uv run agent_cli.py events
  uv run agent_cli.py events --capture --kind note --summary "..." --agent dave
```

`aurora events --limit 2` (exit 0)

```
count: 2
more: may exist beyond --limit 2
events[2]{kind,at,agent,track,summary,ref}:
  note,"2026-10-12T16:09:36 CEST",alice,null,paused the release until the auth fix lands,"event:events:raw:1791814176071-0"
  migration,"2026-10-12T16:09:35 CEST",carol,data,"migrated the lessons table to the v3 schema: renamed four columns, backfilled the scope field for every row, rebuilt the... (truncated, 437 chars total)","event:events:raw:1791814175601-0"
help[2]:
  uv run agent_cli.py events --get event:events:raw:1791814176071-0
  uv run agent_cli.py events --limit 4
```
