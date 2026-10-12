# AXI bench: `precompile`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 13/20 (65%) | 20/20 (100%) | +35 pp |
| Output tokens, as the reader counts them (median) | 85 | 135 | +50 (+59%) |
| Stdout characters (all runs) | 390 | 574 | +184 (+47%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many lessons are in the precompile plan? | `2` | 5/5 | 5/5 |
| How many lessons pass every compile gate? | `0` | 3/5 | 5/5 |
| Which gates is short_titles still failing? List the gate names separated by commas. | `['proven', 'stable']` | 0/5 | 5/5 |
| Was a precompiled candidate built? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora precompile plan` (exit 0)

```
  no_force_push                            guard        hold proven=none stable=False premise=True -> claude-code,codex-cli,cursor,runner
  short_titles                             instruction  hold proven=none stable=False premise=True -> claude-code,codex-cli,cursor,runner
```

`aurora precompile build` (exit 1)

```
{
 "built": false,
 "why": "no lesson passed the gates"
}
```

`aurora precompile check` (exit 0)

```
no drift: every generated piece matches its source hash
```


## After: output

`aurora precompile plan` (exit 0)

```
total: 2
passing: 0
lessons[2]{lesson,kind,status,failing_gates,harnesses}:
  no_force_push,guard,held,"proven, stable","claude-code, codex-cli, cursor, runner"
  short_titles,instruction,held,"proven, stable","claude-code, codex-cli, cursor, runner"
help[1]:
  uv run agent_cli.py precompile build --force
```

`aurora precompile build` (exit 1)

```
error: no lesson passed the gates
code: NOTHING_TO_BUILD
help[2]:
  uv run agent_cli.py precompile plan
  uv run agent_cli.py precompile build --force
```

`aurora precompile check` (exit 0)

```
root: /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a7f65ec701d4c3c3d
drift: 0
problems: []
```
