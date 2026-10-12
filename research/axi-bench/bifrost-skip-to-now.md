# AXI bench: `bifrost-skip-to-now`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/25 (100%) | 25/25 (100%) | +0 pp |
| Output tokens, as the reader counts them (median) | 90 | 143 | +53 (+59%) |
| Stdout characters (all runs) | 322 | 657 | +335 (+104%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Whose cursors were advanced? | `deepseek` | 5/5 | 5/5 |
| Who authorized the skip? | `claude` | 5/5 | 5/5 |
| Was an audit record written? Answer yes or no. | `yes` | 5/5 | 5/5 |
| Did the skip happen? Answer yes or no. | `no` | 5/5 | 5/5 |
| What command must be run before the skip can succeed? Give the command only. | `['bifrost-pause']` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora bifrost-skip-to-now deepseek --by claude --reason echo storm` (exit 0)

```
[skip-to-now] deepseek: shared=OK lane=OK (audited event recorded; by claude: echo storm)
  shared: inbox 0->1791819467334-0
  lane: inbox 0->1791819467332-0, shadow_inbox 0->1791819467334-0
```

`aurora bifrost-resume` (exit 0)

```
[bifrost] RESUMED
```

`aurora bifrost-skip-to-now deepseek --by claude --reason echo storm` (exit 2)

```
[skip-to-now] REFUSED: fleet not paused -- a skip under a live consumer races its drain; run bifrost-pause first
```


## After: output

`aurora bifrost-skip-to-now deepseek --by claude --reason echo storm` (exit 0)

```
agent: deepseek
status: skipped to now
shared: OK
lane: OK
audited: true
by: claude
reason: echo storm
moved[3]{cursor,from,to}:
  shared.inbox,"0",1791819502147-0
  lane.inbox,"0",1791819502145-0
  lane.shadow_inbox,"0",1791819502147-0
help[1]:
  uv run agent_cli.py bifrost-resume
```

`aurora bifrost-resume` (exit 0)

```
status: resumed
was_paused: true
pause_was: hard
paused_by: user
pause_reason: skip ceremony
auto_responders: free to take new work
```

`aurora bifrost-skip-to-now deepseek --by claude --reason echo storm` (exit 2)

```
error: "skip refused: fleet not paused -- a skip under a live consumer races its drain; run bifrost-pause first"
code: REFUSED
skipped: false
agent: deepseek
help[1]:
  uv run agent_cli.py bifrost-pause --reason "<why>" --ttl 600 --by claude
```
