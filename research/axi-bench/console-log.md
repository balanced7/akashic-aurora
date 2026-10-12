# AXI bench: `console-log`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 23/25 (92%) | 25/25 (100%) | +8 pp |
| Output tokens, as the reader counts them (median) | 254 | 185 | -69 (-27%) |
| Stdout characters (all runs) | 892 | 696 | -196 (-22%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many console events are listed? | `4` | 5/5 | 5/5 |
| Which agent was the interjection addressed to? | `claude` | 5/5 | 5/5 |
| Why was the collaboration paused? | `['auth']` | 5/5 | 5/5 |
| How many bytes was the shared file docs/spec.md? | `2048` | 5/5 | 5/5 |
| Does this output show every console event there is? Answer yes or no. | `no` | 3/5 | 5/5 |

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

`aurora console-log` (exit 0)

```
# 4 durable console event(s) (live cockpit -> Ledger)
  [control] user resume  2026-10-12T15:40:07
    (no reason)
    ref: event:events:raw:1791819607503-0
  [file_drop] user shared  2026-10-12T15:40:07
    docs/spec.md (2048 bytes)
    ref: event:events:raw:1791819607078-0
  [control] user pause  2026-10-12T15:40:06
    reviewing the auth change
    ref: event:events:raw:1791819606586-0
  [interjection:steer] user -> claude  2026-10-12T15:40:06
    also cover the null case
    ref: event:events:raw:1791819606133-0

Drill: uv run agent_cli.py events --get <ref>
```

`aurora console-log --limit 2` (exit 0)

```
# 2 durable console event(s) (live cockpit -> Ledger)
  [control] user resume  2026-10-12T15:40:07
    (no reason)
    ref: event:events:raw:1791819607503-0
  [file_drop] user shared  2026-10-12T15:40:07
    docs/spec.md (2048 bytes)
    ref: event:events:raw:1791819607078-0

Drill: uv run agent_cli.py events --get <ref>
```


## After: output

`aurora console-log` (exit 0)

```
count: 4
events[4]{ref,kind,by,to,text}:
  "event:events:raw:1791819649173-0",resume,user,null,(no reason)
  "event:events:raw:1791819648717-0",file_drop,user,null,docs/spec.md (2048 bytes)
  "event:events:raw:1791819648265-0",pause,user,null,reviewing the auth change
  "event:events:raw:1791819647789-0","interjection:steer",user,claude,also cover the null case
help[1]:
  uv run agent_cli.py events --get <ref>
```

`aurora console-log --limit 2` (exit 0)

```
count: 2
more: true
events[2]{ref,kind,by,text}:
  "event:events:raw:1791819649173-0",resume,user,(no reason)
  "event:events:raw:1791819648717-0",file_drop,user,docs/spec.md (2048 bytes)
help[2]:
  uv run agent_cli.py events --get <ref>
  uv run agent_cli.py console-log --limit 4
```
