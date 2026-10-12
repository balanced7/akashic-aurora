# AXI bench: `ask`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 10/30 (33%) | 30/30 (100%) | +67 pp |
| Output tokens, as the reader counts them (median) | 4 | 67 | +63 (+1575%) |
| Stdout characters (all runs) | 224 | 867 | +643 (+287%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many background asks are recorded? | `0` | 5/5 | 5/5 |
| Does an ask with handle deadbeef exist? Answer yes or no. | `no` | 0/5 | 5/5 |
| What exact command lists the recent background asks? Give the command only. | `['ask --list']` | 0/5 | 5/5 |
| Is ask 42 in a terminal state? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Which flag should be run first, --bg or --get? Answer with the flag only. | `--bg` | 0/5 | 5/5 |
| Did the ask succeed? Answer yes or no. | `no` | 0/5 | 5/5 |

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

`aurora ask --list` (exit 0)

```
# no background asks recorded
```

`aurora ask --get deadbeef` (exit 0)

```
# ask deadbeef -- UNKNOWN
```

`aurora ask --status 42` (exit 0)

```
# ask 42 -- UNKNOWN (terminal)
  caller should: re-ask -- treat the old transaction as unresolvable (evidence lost or trimmed: RB-30 flush, or maxlen outlived the ask)
```

`aurora ask --bg --get x` (exit 2)

```

```

`aurora ask --as-resident nobody what is two plus two` (exit 1)

```

```


## After: output

`aurora ask --list` (exit 0)

```
total: 0
asks: no background asks recorded
help[1]:
  uv run agent_cli.py ask --bg "<question>"
```

`aurora ask --get deadbeef` (exit 0)

```
handle: deadbeef
state: UNKNOWN
next: "no ask by that handle -- check the id, or `ask --list` to see recent ones"
help[1]:
  uv run agent_cli.py ask --list
```

`aurora ask --status 42` (exit 0)

```
ask_id: "42"
state: UNKNOWN
terminal: true
caller_should: "re-ask -- treat the old transaction as unresolvable (evidence lost or trimmed: RB-30 flush, or maxlen outlived the ask)"
```

`aurora ask --bg --get x` (exit 2)

```
error: "--bg SPAWNS a new ask; --get/--list READ existing ones. Pick one: run --bg first, then --get the handle it prints."
code: USAGE
help[1]:
  uv run agent_cli.py ask --bg "<question>"
```

`aurora ask --as-resident nobody what is two plus two` (exit 1)

```
error: "'nobody' is not a resident (no ratified designation), so it cannot answer at the resident tier. Run the ceremony first: uv run agent_cli.py resident nominate nobody --callsign <name> --receipt <their lesson> --by <peer>"
code: ASK_FAILED
```
