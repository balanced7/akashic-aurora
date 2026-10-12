# AXI bench: `bifrost-standby`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 13/25 (52%) | 24/25 (96%) | +44 pp |
| Output tokens, as the reader counts them (median) | 57 | 91 | +34 (+60%) |
| Stdout characters (all runs) | 239 | 338 | +99 (+41%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many messages were drained? | `2` | 4/5 | 5/5 |
| Which agent sent the request message? | `deepseek` | 5/5 | 5/5 |
| Is a wake listener now waiting for new mail for this agent? Answer yes or no. | `no` | 4/5 | 5/5 |
| How many messages did this run drain? | `0` | 0/5 | 5/5 |
| What exact command would drain the inbox and then wait for new mail? Give the command only. | `['bifrost-standby', 'claude']` | 0/5 | 4/5 |

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

`aurora bifrost-standby claude --no-listen` (exit 0)

```
drained: 2 message(s)
  [request] from deepseek: please review core/a.py
  [chat] from deepseek: fyi the build is green
standby: report-only (no listener requested)
```

`aurora bifrost-standby claude --no-listen` (exit 0)

```
drained: inbox already clean
standby: report-only (no listener requested)
```


## After: output

`aurora bifrost-standby claude --no-listen` (exit 0)

```
seat: yours
drained: 2
mail[2]: "[request] from deepseek: please review core/a.py","[chat] from deepseek: fyi the build is green"
listener: not armed (--no-listen)
help[1]:
  uv run agent_cli.py bifrost-standby claude
```

`aurora bifrost-standby claude --no-listen` (exit 0)

```
seat: yours
drained: 0
mail: []
listener: not armed (--no-listen)
help[1]:
  uv run agent_cli.py bifrost-standby claude
```
