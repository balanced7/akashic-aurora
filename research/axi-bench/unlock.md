# AXI bench: `unlock`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 6/25 (24%) | 25/25 (100%) | +76 pp |
| Output tokens, as the reader counts them (median) | 13 | 47 | +34 (+262%) |
| Stdout characters (all runs) | 111 | 314 | +203 (+183%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Was the lock on core/a.py released? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Which agent holds the lock on docs/x.md? | `bob` | 0/5 | 5/5 |
| Is core/a.py locked by anyone right now? Answer yes or no. | `no` | 1/5 | 5/5 |
| Did the command fail because nobody holds docs/x.md, or because another agent holds it? Answer nobody or another. | `another` | 0/5 | 5/5 |
| What command shows who holds which locks? Give the command only. | `['locks']` | 0/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora unlock alice core/a.py` (exit 0)

```
[unlock] released: core/a.py
```

`aurora unlock alice docs/x.md` (exit 1)

```
[unlock] not yours / not held: docs/x.md
```

`aurora unlock alice core/a.py` (exit 1)

```
[unlock] not yours / not held: core/a.py
```


## After: output

`aurora unlock alice core/a.py` (exit 0)

```
unlock: released
path: core/a.py
agent: alice
help[1]:
  uv run agent_cli.py locks alice
```

`aurora unlock alice docs/x.md` (exit 1)

```
error: docs/x.md is held by bob
code: NOT_YOURS
path: docs/x.md
held_by: bob
help[1]:
  uv run agent_cli.py locks alice
```

`aurora unlock alice core/a.py` (exit 1)

```
error: core/a.py is not locked
code: NOT_HELD
path: core/a.py
help[1]:
  uv run agent_cli.py locks alice
```
