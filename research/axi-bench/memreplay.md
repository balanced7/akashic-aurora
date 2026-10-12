# AXI bench: `memreplay`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 19/25 (76%) | 24/25 (96%) | +20 pp |
| Output tokens, as the reader counts them (median) | 74 | 79 | +5 (+7%) |
| Stdout characters (all runs) | 390 | 800 | +410 (+105%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many lessons are queued for a memory replay? | `3` | 4/5 | 5/5 |
| Why was the lesson stage_paths queued? Give the reason only. | `new` | 0/5 | 4/5 |
| Was a snapshot written? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Which flag is missing from this memreplay run command? Give the flag only. | `--base` | 5/5 | 5/5 |
| Which flag is missing from this memreplay drain command? Give the flag only. | `--daily-usd` | 5/5 | 5/5 |

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

`aurora memreplay queue` (exit 0)

```
  port_clash: new at 2026-10-12T15:45:06+00:00
  stage_paths: new at 2026-10-12T15:45:07+00:00
  keep_me: new at 2026-10-12T15:45:07+00:00
```

`aurora memreplay snapshot --label bench` (exit 0)

```
[OK] snapshot /tmp/axi-bench-52jbxqed/data/metaharness/memsnap/20261012T154509-bench-4422ffb8c377.json
```

`aurora memreplay run --lesson port_clash` (exit 2)

```
ERROR: `memreplay run` needs --lesson and --base (the candidate whose harness the arms share)
```

`aurora memreplay drain --base baseline` (exit 2)

```
ERROR: `memreplay drain` needs --base and --daily-usd
```


## After: output

`aurora memreplay queue` (exit 0)

```
queued: 3
lessons[3]{lesson,why,at}:
  port_clash,new,"2026-10-12T15:45:41+00:00"
  stage_paths,new,"2026-10-12T15:45:41+00:00"
  keep_me,new,"2026-10-12T15:45:42+00:00"
help[2]:
  uv run agent_cli.py memreplay run --lesson port_clash --base baseline --daily-usd 5
  uv run agent_cli.py memreplay drain --base baseline --daily-usd 5
```

`aurora memreplay snapshot --label bench` (exit 0)

```
snapshot: /tmp/axi-bench-52jbxqed/data/metaharness/memsnap/20261012T154543-bench-0a818036d758.json
lessons: 3
excluded: []
```

`aurora memreplay run --lesson port_clash` (exit 2)

```
error: `memreplay run` needs --lesson and --base (the candidate whose harness the arms share)
code: USAGE
help[1]:
  uv run agent_cli.py memreplay run --lesson port_clash --base baseline --daily-usd 5
```

`aurora memreplay drain --base baseline` (exit 2)

```
error: `memreplay drain` needs --base and --daily-usd
code: USAGE
help[1]:
  uv run agent_cli.py memreplay drain --base baseline --daily-usd 5
```
