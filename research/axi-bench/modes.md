# AXI bench: `modes`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 24/25 (96%) | -4 pp |
| Output tokens, as the reader counts them (median) | 30 | 52 | +22 (+73%) |
| Stdout characters (all runs) | 317 | 503 | +186 (+59%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which memory mode is active? | `interpretive` | 5/5 | 5/5 |
| Which environment variable sets the memory mode? Give the name only. | `AKASHIC_MEMORY_MODE` | 5/5 | 4/5 |
| What move is planned for the lesson short_titles? | `keep` | 5/5 | 5/5 |
| How many compiled lessons are stale? | `0` | 5/5 | 5/5 |
| Which flags are missing from this modes compare command? List them separated by commas. | `['--compiled', '--scenario']` | 5/5 | 5/5 |

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

`aurora modes show` (exit 0)

```
memory mode: interpretive (AKASHIC_MEMORY_MODE); active harness: unknown
```

`aurora modes placement` (exit 0)

```
  short_titles                             keep       stays interpretive
  no_force_push                            keep       stays interpretive
```

`aurora modes stale` (exit 0)

```
no compiled lesson has changed
```

`aurora modes compare --base baseline` (exit 2)

```
ERROR: `modes compare` needs --base, --compiled and --scenario ...
```


## After: output

`aurora modes show` (exit 0)

```
mode: interpretive
harness: unknown
set_by: AKASHIC_MEMORY_MODE
modes[3]: interpretive,precompiled,hybrid
```

`aurora modes placement` (exit 0)

```
total: 2
moves:
  keep: 2
lessons[2]{lesson,move,why}:
  short_titles,keep,stays interpretive
  no_force_push,keep,stays interpretive
help[1]:
  uv run agent_cli.py precompile plan
```

`aurora modes stale` (exit 0)

```
stale: 0
lessons: []
```

`aurora modes compare --base baseline` (exit 2)

```
error: "`modes compare` needs --base, --compiled and --scenario ..."
code: USAGE
help[1]:
  uv run agent_cli.py modes compare --base baseline --compiled <candidate> --scenario <id> --daily-usd 5
```
