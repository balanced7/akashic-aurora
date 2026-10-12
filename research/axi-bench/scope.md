# AXI bench: `scope`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 29/30 (97%) | 30/30 (100%) | +3 pp |
| Output tokens, as the reader counts them (median) | 27 | 66 | +39 (+144%) |
| Stdout characters (all runs) | 370 | 649 | +279 (+75%) |
| AXI checks passed | 3/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many lessons are there in total, across all scopes? | `5` | 5/5 | 5/5 |
| How many lessons apply universally? | `3` | 5/5 | 5/5 |
| Which lesson is scoped to harness:codex-cli alone? | `codex_only` | 5/5 | 5/5 |
| What is the scope of the lesson gpt_on_codex? | `['harness:codex-cli', 'model:gpt']` | 5/5 | 5/5 |
| How many scope widening proposals are there? | `0` | 4/5 | 5/5 |
| Does a lesson named no_such_lesson exist? Answer yes or no. | `no` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| empty state explicit | fail | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora scope tree` (exit 0)

```
universal  (3 lesson(s))
  universal: uni_3, uni_2, uni_1
harness  (1 lesson(s))
  harness:codex-cli: codex_only
model:family  (1 lesson(s))
  harness:codex-cli model:gpt: gpt_on_codex
```

`aurora scope show --experiment gpt_on_codex` (exit 0)

```
gpt_on_codex: harness:codex-cli model:gpt  (level: model:family)
```

`aurora scope proposals` (exit 0)

```
no widening proposals (a lesson needs credit or repeats under 2+ harnesses or models)
```

`aurora scope show --experiment no_such_lesson` (exit 1)

```
ERROR: no lesson 'no_such_lesson'
```


## After: output

`aurora scope tree` (exit 0)

```
total: 5
scopes[3]{level,scope,count,lessons}:
  universal,universal,3,"uni_3, uni_2, uni_1"
  harness,"harness:codex-cli",1,codex_only
  "model:family","harness:codex-cli model:gpt",1,gpt_on_codex
help[2]:
  uv run agent_cli.py scope show --experiment <name>
  uv run agent_cli.py scope proposals
```

`aurora scope show --experiment gpt_on_codex` (exit 0)

```
experiment: gpt_on_codex
scope: "harness:codex-cli model:gpt"
level: "model:family"
```

`aurora scope proposals` (exit 0)

```
total: 0
proposals: []
needs: credit or a repeat under 2+ harnesses or 2+ model families
help[1]:
  uv run agent_cli.py scope tree
```

`aurora scope show --experiment no_such_lesson` (exit 1)

```
error: no lesson 'no_such_lesson'
code: NOT_FOUND
help[2]:
  uv run agent_cli.py recall no_such_lesson
  uv run agent_cli.py scope tree
```
