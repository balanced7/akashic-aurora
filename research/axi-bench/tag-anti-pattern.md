# AXI bench: `tag-anti-pattern`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 19/20 (95%) | 20/20 (100%) | +5 pp |
| Output tokens, as the reader counts them (median) | 36 | 33 | -3 (-8%) |
| Stdout characters (all runs) | 157 | 241 | +84 (+54%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the lesson tagged? Answer yes or no. | `yes` | 5/5 | 5/5 |
| What anti-pattern name was given to the lesson? | `retry-loop` | 4/5 | 5/5 |
| Did the command succeed? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which command must be run first to create the lesson? Give the verb only. | `['learn']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora tag-anti-pattern bench --experiment blind_retry --name retry-loop --reason locks the account` (exit 0)

```
[OK] tagged 'blind_retry' as anti-pattern 'retry-loop' -- recall will now warn on it
```

`aurora tag-anti-pattern bench --experiment no_such_lesson --name x` (exit 1)

```
[FAIL] no lesson 'no_such_lesson' to tag (record it first with `learn`)
```


## After: output

`aurora tag-anti-pattern bench --experiment blind_retry --name retry-loop --reason locks the account` (exit 0)

```
tagged: true
experiment: blind_retry
anti_pattern: retry-loop
recall: warns on it now
```

`aurora tag-anti-pattern bench --experiment no_such_lesson --name x` (exit 1)

```
error: no lesson 'no_such_lesson' -- record it first with learn
code: NOT_FOUND
help[1]:
  uv run agent_cli.py learn bench --experiment no_such_lesson ...
```
