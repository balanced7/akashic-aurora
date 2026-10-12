# AXI bench: `graduate`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 28/30 (93%) | 29/30 (97%) | +3 pp |
| Output tokens, as the reader counts them (median) | 57 | 43 | -14 (-25%) |
| Stdout characters (all runs) | 564 | 440 | -124 (-22%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What automation now enforces the graduated lesson? | `pre-commit hook` | 5/5 | 5/5 |
| Will the graduated lesson still take recall slots? Answer yes or no. | `no` | 4/5 | 4/5 |
| Does tab_width compete for recall slots again? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Did the command succeed? Answer yes or no. | `no` | 4/5 | 5/5 |
| What command lists the lesson names to check the spelling? Give the command only. | `['list']` | 5/5 | 5/5 |
| Which flag is missing from the command? | `['--enforced-by']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora graduate bench --experiment blanket_staging --enforced-by pre-commit hook` (exit 0)

```
[OK] graduated 'blanket_staging' -- enforced by: pre-commit hook
     It keeps history (`list` tags it [graduated]) but no longer takes recall slots.
```

`aurora graduate bench --experiment tab_width --undo` (exit 0)

```
[OK] un-graduated 'tab_width' -- it competes for recall surface slots again.
```

`aurora graduate bench --experiment no_such_lesson --enforced-by ci` (exit 1)

```
ERROR: no lesson named 'no_such_lesson' -- check the name with `uv run agent_cli.py list`.
```

`aurora graduate bench --experiment blanket_staging` (exit 2)

```
ERROR: need --experiment NAME and --enforced-by "<the automation that enforces it>" (or --undo to reverse a graduation).
Example: uv run agent_cli.py graduate claude --experiment git_blanket_staging --enforced-by "git-guard PreToolUse hook (C0)"
```


## After: output

`aurora graduate bench --experiment blanket_staging --enforced-by pre-commit hook` (exit 0)

```
experiment: blanket_staging
graduated: true
enforced_by: pre-commit hook
recall_slots: no (history kept)
```

`aurora graduate bench --experiment tab_width --undo` (exit 0)

```
experiment: tab_width
graduated: false
recall_slots: yes
```

`aurora graduate bench --experiment no_such_lesson --enforced-by ci` (exit 1)

```
error: no lesson named 'no_such_lesson'
code: NOT_FOUND
help[1]:
  uv run agent_cli.py list
```

`aurora graduate bench --experiment blanket_staging` (exit 2)

```
error: missing --enforced-by (or pass --undo to reverse a graduation)
code: USAGE
help[1]:
  uv run agent_cli.py graduate bench --experiment blanket_staging --enforced-by "<automation>"
```
