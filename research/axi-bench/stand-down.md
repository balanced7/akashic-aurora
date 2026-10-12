# AXI bench: `stand-down`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 11/15 (73%) | 14/15 (93%) | +20 pp |
| Output tokens, as the reader counts them (median) | 43 | 67 | +24 (+56%) |
| Stdout characters (all runs) | 120 | 173 | +53 (+44%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the seat yielded? Answer yes or no. | `no` | 5/5 | 4/5 |
| Which environment variable must be set for this command to work? Give its name only. | `CLAUDE_CODE_SESSION_ID` | 5/5 | 5/5 |
| Which agent's seat was this command about? | `claude` | 1/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora stand-down claude` (exit 1)

```
no session id in the environment -- nothing to yield (CLAUDE_CODE_SESSION_ID unset; this door is for interactive seats)
```


## After: output

`aurora stand-down claude` (exit 1)

```
error: no session id in the environment -- nothing to yield (CLAUDE_CODE_SESSION_ID unset; this door is for interactive seats)
code: NO_SESSION
yielded: false
agent: claude
```
