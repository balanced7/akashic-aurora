# AXI bench: `hooks`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 35/35 (100%) | 35/35 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 190 | 194 | +4 (+2%) |
| Stdout characters (all runs) | 791 | 838 | +47 (+6%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many Aurora hooks are installed in the claude project settings file? | `10` | 5/5 | 5/5 |
| Which harness has its Aurora hooks switched off (disabled)? Give the harness name only. | `codex` | 5/5 | 5/5 |
| How many codex hooks are disabled? | `5` | 5/5 | 5/5 |
| What command turns the disabled hooks back on? Give the command only. | `['hooks enable', '--harness codex', '--scope project']` | 5/5 | 5/5 |
| How many projects are enrolled (where the hooks speak up)? | `1` | 5/5 | 5/5 |
| How many cursor hooks would this install add? | `6` | 5/5 | 5/5 |
| Did this command write anything to disk? Answer yes or no. | `no` | 5/5 | 5/5 |

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

`aurora hooks status --project /tmp/axi-hooks-74yk0w6h` (exit 0)

```
# Aurora harness hooks  (change with: hooks install|uninstall|enable|disable|enroll|unenroll)
claude  project          /tmp/axi-hooks-74yk0w6h/.claude/settings.local.json
    10 installed
codex   project          /tmp/axi-hooks-74yk0w6h/.codex/hooks.json
    0 installed, 5 disabled
    turn back on: agent_cli.py hooks enable --harness codex --scope project
enrolled (the hooks speak up here):
  /tmp/axi-hooks-74yk0w6h
```

`aurora hooks install --harness cursor --scope project --project /tmp/axi-hooks-74yk0w6h --dry-run` (exit 0)

```
DRY RUN -- install cursor hooks (project): /tmp/axi-hooks-74yk0w6h/.cursor/hooks.json
  added    sessionStart:cursor_sessionstart.py
  added    beforeShellExecution:cursor_beforeshell.py
  added    preToolUse:cursor_pretooluse.py
  added    postToolUse:cursor_posttooluse.py
  added    postToolUseFailure:cursor_posttooluse.py
  added    sessionEnd:cursor_sessionend.py
```


## After: output

`aurora hooks status --project /tmp/axi-hooks-74yk0w6h` (exit 0)

```
hooked_files: 2
files[2]{harness,scope,state,installed,disabled,path}:
  claude,project,on,10,0,/tmp/axi-hooks-74yk0w6h/.claude/settings.local.json
  codex,project,off,0,5,/tmp/axi-hooks-74yk0w6h/.codex/hooks.json
enrolled[1]: /tmp/axi-hooks-74yk0w6h
help[1]:
  uv run agent_cli.py hooks enable --harness codex --scope project --project /tmp/axi-hooks-74yk0w6h
```

`aurora hooks install --harness cursor --scope project --project /tmp/axi-hooks-74yk0w6h --dry-run` (exit 0)

```
action: install
harness: cursor
scope: project
path: /tmp/axi-hooks-74yk0w6h/.cursor/hooks.json
dry_run: true
written: false
added[6]: "sessionStart:cursor_sessionstart.py","beforeShellExecution:cursor_beforeshell.py","preToolUse:cursor_pretooluse.py","postToolUse:cursor_posttooluse.py","postToolUseFailure:cursor_posttooluse.py","sessionEnd:cursor_sessionend.py"
help[1]:
  uv run agent_cli.py hooks install --harness cursor --scope project --project /tmp/axi-hooks-74yk0w6h
```
