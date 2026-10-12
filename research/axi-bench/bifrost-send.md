# AXI bench: `bifrost-send`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 27/30 (90%) | 30/30 (100%) | +10 pp |
| Output tokens, as the reader counts them (median) | 133 | 86 | -47 (-35%) |
| Stdout characters (all runs) | 701 | 627 | -74 (-11%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| What kind was the message sent as? | `request` | 5/5 | 5/5 |
| Within how many seconds is a reply expected? Answer 0 if no reply deadline was set. | `1800` | 5/5 | 5/5 |
| Was the message actually sent this time? Answer yes or no. | `no` | 5/5 | 5/5 |
| Which command does the output suggest using instead of sending again? Give the command name only. | `['nudge']` | 2/5 | 5/5 |
| Was this message sent to one agent or to every agent? Answer one or every. | `every` | 5/5 | 5/5 |
| Which flag is missing? Give the flag only. | `--to` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora bifrost-send deepseek please review core/a.py --to claude --kind request` (exit 0)

```
[bifrost-send] expecting a reply within 1800s [auto: directed ask -- add --expect-reply-within 0 to opt out] (3 redrives then a loud expectation_dead; swept at boot/bifrost-sync)
[bifrost-send] -> claude [request] (id 1791814489825-0)
```

`aurora bifrost-send deepseek please review core/a.py --to claude --kind request` (exit 0)

```
[bifrost-send] expecting a reply within 1800s [auto: directed ask -- add --expect-reply-within 0 to opt out] (3 redrives then a loud expectation_dead; swept at boot/bifrost-sync)
[bifrost-send] COLLAPSED onto 1791814489825-0 -- NOT re-sent (identical request to claude is still pending). Nudge it, or change the ask.
```

`aurora bifrost-send deepseek standup in five minutes --broadcast` (exit 0)

```
[bifrost-send] -> * [chat] (id 1791814490664-0)
```

`aurora bifrost-send deepseek hello` (exit 2)

```
ERROR: bifrost-send needs --to <agent> (or --broadcast). e.g. bifrost-send claude --to deepseek "hi"
```


## After: output

`aurora bifrost-send deepseek please review core/a.py --to claude --kind request` (exit 0)

```
status: sent
to: claude
kind: request
id: 1791814530445-0
reply_due_s: 1800
reply_due_set_by: default (--expect-reply-within 0 opts out)
help[1]:
  uv run agent_cli.py bifrost-standby deepseek
```

`aurora bifrost-send deepseek please review core/a.py --to claude --kind request` (exit 0)

```
status: collapsed
to: claude
kind: request
collapsed_onto: 1791814530445-0
why: an identical request to claude is still pending
help[1]:
  uv run agent_cli.py bifrost-nudge deepseek --to claude "<what changed>"
```

`aurora bifrost-send deepseek standup in five minutes --broadcast` (exit 0)

```
status: sent
to: *
kind: chat
broadcast: true
id: 1791814531349-0
```

`aurora bifrost-send deepseek hello` (exit 2)

```
error: bifrost-send needs --to <agent> (or --broadcast)
code: USAGE
sent: false
help[1]:
  uv run agent_cli.py bifrost-send deepseek --to <peer> "<message>"
```
