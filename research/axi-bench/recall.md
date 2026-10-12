# AXI bench: `recall`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 3 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 12/15 (80%) | 15/15 (100%) | +20 pp |
| Output tokens, as the reader counts them (median) | 60 | 90 | +30 (+50%) |
| Stdout characters (all runs) | 1,122 | 1,151 | +29 (+3%) |
| AXI checks passed | 4/6 | 6/6 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Which port should be checked when tests hang at start? | `16379` | 3/3 | 3/3 |
| Which category is the port_clash lesson in? | `performance` | 3/3 | 3/3 |
| Is the git_blanket_staging lesson active, or has it been graduated? Answer active or graduated. | `graduated` | 3/3 | 3/3 |
| How many lessons matched the search? | `0` | 3/3 | 3/3 |
| What exact command would show the complete record of the auth_token_refresh lesson? Give the command only. | `['--full', 'learn:experiment:auth_token_refresh']` | 0/3 | 3/3 |

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

`aurora recall port` (exit 0)

```
# 1 lesson(s) matching 'port'
  - [performance] port_clash: Use when tests hang at start: check that port 16379 is free first. (source: learn:experiment:port_clash)
```

`aurora recall git` (exit 0)

```
# 1 lesson(s) matching 'git'
  - [correction] git_blanket_staging [graduated]: Stage explicit paths, never git add -A. (source: learn:experiment:git_blanket_staging)
```

`aurora recall token` (exit 0)

```
# 1 lesson(s) matching 'token'
  - [security] auth_token_refresh: Use when a token refresh fails with 401 after an idle period, before retrying the request: refresh the token once, then retry. The refresh window is 300 seconds and a second failure means the session is revoked. The refresh window is 300 seconds and a second failure means the session is revoked. The refresh window is 300 seconds and a second failure means the session is revoked. The refresh window is 300 seconds and a second failure means the session is revoked. The refresh window is 300 seconds and a second failure means the session is revoked. The refresh window is 300 seconds and a second failure means the session is revoked.  (source: learn:experiment:auth_token_refresh)
```

`aurora recall nonexistent_xyz` (exit 0)

```
# 0 lesson(s) matching 'nonexistent_xyz'
```


## After: output

`aurora recall port` (exit 0)

```
query: port
total: 1
lessons[1]{name,category,status,lesson}:
  port_clash,performance,active,"Use when tests hang at start: check that port 16379 is free first."
help[1]:
  uv run agent_cli.py recall --full learn:experiment:port_clash
```

`aurora recall git` (exit 0)

```
query: git
total: 1
lessons[1]{name,category,status,lesson}:
  git_blanket_staging,correction,graduated,"Stage explicit paths, never git add -A."
help[1]:
  uv run agent_cli.py recall --full learn:experiment:git_blanket_staging
```

`aurora recall token` (exit 0)

```
query: token
total: 1
lessons[1]{name,category,status,lesson}:
  auth_token_refresh,security,active,"Use when a token refresh fails with 401 after an idle period, before retrying the request: refresh the token once, then retry. The refresh window is 300 seconds and a second failure means the session is revoked. The refresh window is 300 seconds and a second failure means the session is revoked. The... (truncated, 636 chars total)"
help[1]:
  uv run agent_cli.py recall --full learn:experiment:auth_token_refresh
```

`aurora recall nonexistent_xyz` (exit 0)

```
query: nonexistent_xyz
total: 0
lessons: []
help[2]:
  uv run agent_cli.py recall "<broader query>"
  uv run agent_cli.py learn <agent_id> --experiment <name> --tried ...
```
