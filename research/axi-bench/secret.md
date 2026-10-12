# AXI bench: `secret`

Before: `50c2ee6f (50c2ee6f)`. After: this change. Reader: `claude-haiku-5-5`, 5 runs per question, graded mechanically against seeded answers.

| Measure | Before | After | Change |
|---|---|---|---|
| Reader accuracy | 25/30 (83%) | 29/30 (97%) | +13 pp |
| Output tokens, as the reader counts them (median) | 897 | 465 | -432 (-48%) |
| Stdout characters (all runs) | 2,470 | 1,103 | -1,367 (-55%) |
| AXI checks passed | 3/5 | 5/5 |  |

## Questions

| Question | Expected | Before | After |
|---|---|---|---|
| How many credentials are present in the vault? | `2` | 5/5 | 5/5 |
| How many bytes does openai.key hold? | `51` | 5/5 | 5/5 |
| Is deepseek.key present in the vault? Answer yes or no. | `no` | 5/5 | 5/5 |
| How many credential names does the vault accept in total? | `22` | 5/5 | 5/5 |
| What command captures kimi.key into the vault? Give the command only. | `['secret kimi.key']` | 5/5 | 4/5 |
| Did the command succeed? Answer yes or no. | `no` | 0/5 | 5/5 |

## AXI checks

| Check | Before | After |
|---|---|---|
| unknown flag exit 2 | pass | pass |
| unknown flag on stdout | fail | pass |
| unknown flag lists valid flags | fail | pass |
| help exit 0 | pass | pass |
| no ansi in agent stdout | pass | pass |

## Before: output

`aurora secret` (exit 0)

```
# the vault (sizes only -- contents are never printed)
  chronos_inbound.key          absent           HMAC secret CHRONOS uses to push into our relay -- its own key so its mail resolves to remote:chronos instead of collapsing into another peer's identity
  chronos_outbound.key         absent           HMAC secret we use to push INTO Chronos's relay
  claude_oauth.token           absent           long-lived Claude Code OAuth token (claude setup-token) — the credential !spawn hands a fresh seat, so resuscitation stops dying with the interactive session
  cursor.key                   absent           Cursor API key
  deepseek.key                 absent           DeepSeek API key
  discord_bot.token            absent           Discord bot token (Developer Portal -> Bot -> Reset Token)
  discord_channel_heimdall.url absent           the #heimdall seat-channel webhook (his lane with deepseek)
  discord_channel_navi.url     absent           the #navi seat-channel webhook (his lane with kimi)
  discord_channel_rill.url     absent           the #rill seat-channel webhook (his lane with dsh_agent)
  discord_channel_sol.url      absent           the #sol seat-channel webhook (Daniil's lane with sol)
  discord_channel_vandor.url   absent           the #vandor seat-channel webhook (his lane with claude)
  discord_forum_webhook.url    absent           the #aurora-rooms forum webhook
  discord_operator_id          absent           Daniil's numeric Discord user id — the R1 allowlist
  discord_webhook.url          absent           the #aurora global-feed webhook (pipe 1 of the pool)
  discord_webhook_2.url        absent           an ADDITIONAL webhook on the SAME #aurora channel -- a second independent rate-limit bucket, pooled with pipe 1
  discord_webhook_3.url        absent           pool pipe 3 -- same channel, its own bucket
  discord_webhook_4.url        absent           pool pipe 4 -- same channel, its own bucket
  gemini.key                   present, 39B     Gemini API key
  kimi.key                     absent           Kimi/Moonshot API key
  openai.key                   present, 51B     OpenAI API key
  remote_bridge_inbound.key    absent           HMAC secret a remote peer uses to push into OUR relay (inbound direction; remote-bridge v1 only)
  remote_bridge_outbound.key   absent           HMAC secret we use to push INTO a remote peer's relay (outbound direction; remote-bridge v0)
# capture one:  uv run agent_cli.py secret <name>
```

`aurora secret nope.key` (exit 2)

```

```


## After: output

`aurora secret` (exit 0)

```
vault: /tmp/axi-secret-2lvab8ad
total: 22
present: 2
note: "sizes only: contents are never printed"
credentials[22]{name,state,bytes}:
  chronos_inbound.key,absent,0
  chronos_outbound.key,absent,0
  claude_oauth.token,absent,0
  cursor.key,absent,0
  deepseek.key,absent,0
  discord_bot.token,absent,0
  discord_channel_heimdall.url,absent,0
  discord_channel_navi.url,absent,0
  discord_channel_rill.url,absent,0
  discord_channel_sol.url,absent,0
  discord_channel_vandor.url,absent,0
  discord_forum_webhook.url,absent,0
  discord_operator_id,absent,0
  discord_webhook.url,absent,0
  discord_webhook_2.url,absent,0
  discord_webhook_3.url,absent,0
  discord_webhook_4.url,absent,0
  gemini.key,present,39
  kimi.key,absent,0
  openai.key,present,51
  remote_bridge_inbound.key,absent,0
  remote_bridge_outbound.key,absent,0
help[3]:
  uv run agent_cli.py secret <name>
  uv run agent_cli.py secret <name> --stdin
  uv run agent_cli.py secret --fields what
```

`aurora secret nope.key` (exit 2)

```
error: "unknown target 'nope.key': the vault takes allowlisted names, never paths"
code: UNKNOWN_TARGET
help[1]:
  uv run agent_cli.py secret
```
