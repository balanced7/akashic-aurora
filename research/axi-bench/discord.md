# AXI bench: `discord`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 24/25 (96%) | 24/25 (96%) | +0 pp |
| Output tokens, as the reader counts them (median) | 117 | 165 | +48 (+41%) |
| Stdout characters (all runs) | 421 | 625 | +204 (+48%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| Is the Discord bridge configured? Answer yes or no. | `no` | 5/5 | 5/5 |
| What is the file name the webhook URL should be saved to? Give the file name only, not the path. | `discord_webhook.url` | 5/5 | 4/5 |
| What exact command posts a test line once the bridge is set up? Give the command only. | `['discord test']` | 4/5 | 5/5 |
| Was the message sent? Answer yes or no. | `no` | 5/5 | 5/5 |
| Did the command fail, or succeed? Answer failed or succeeded. | `failed` | 5/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora discord status` (exit 0)

```
# discord bridge: NOT CONFIGURED (this is a state, not a failure)
#   1. private Discord channel -> Integrations -> Webhooks -> New -> Copy URL
#   2. save it to /tmp/axi-bench-cdf6476n/before/.secrets/discord_webhook.url
#   3. uv run agent_cli.py discord test
```

`aurora discord send --text hello from the bench` (exit 1)

```
[discord] discord is not configured -- no seat lane and no global webhook. Nothing was sent, and this is a configuration state rather than a delivery failure.
```


## After: output

`aurora discord status` (exit 0)

```
configured: false
webhook_file: /mnt/lnx-storage/projects/akashic-labs/aurora/.claude/worktrees/agent-a36921c04653397c1/.secrets/discord_webhook.url
setup: "private Discord channel -> Integrations -> Webhooks -> New -> Copy URL; save it to webhook_file, then run the test below"
direction: outbound only (inbound needs the R1-R3 identity gate)
help[1]:
  uv run agent_cli.py discord test
```

`aurora discord send --text hello from the bench` (exit 1)

```
error: "discord is not configured -- no seat lane and no global webhook. Nothing was sent, and this is a configuration state rather than a delivery failure."
code: NOT_CONFIGURED
seat: bench
help[1]:
  uv run agent_cli.py discord status
```
