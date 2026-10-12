# AXI bench: `usage-errors`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 3 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 2/12 (17%) | 12/12 (100%) | +83 pp |
| Output tokens, as the reader counts them (median) | 0 | 73 | n/a |
| Stdout characters (all runs) | 0 | 349 | n/a |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Did the command succeed? Answer yes or no. | `no` | 2/3 | 3/3 |
| Which flags does the locks command accept? List them separated by commas. | `['--json', '--help']` | 0/3 | 3/3 |
| Which argument was not recognized? | `--stat` | 0/3 | 3/3 |
| Which existing command did the user most likely mean? Give the command name only. | `locks` | 0/3 | 3/3 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora locks --stat` (exit 2)

```

```

`aurora lokcs` (exit 2)

```

```


## After: output

`aurora locks --stat` (exit 2)

```
error: "unrecognized arguments: --stat"
code: USAGE
command: uv run agent_cli.py locks
valid_flags[2]: "--help","--json"
help[1]:
  uv run agent_cli.py locks --help
```

`aurora lokcs` (exit 2)

```
error: unknown command 'lokcs'
code: USAGE
command: uv run agent_cli.py
did_you_mean[3]: locks,lock,lookback
help[2]:
  uv run agent_cli.py locks --help
  uv run agent_cli.py discover
```
