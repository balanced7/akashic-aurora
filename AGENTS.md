# AGENTS.md -- read this first (everything you need is in the first 40 lines)

You are an agent working in this repo. It has a **shared memory**: lessons other
agents learned, and a place to record what you learn. Use it via ONE script.

## At the START of your task, run this and read the output:

```
py agent_cli.py boot <your_agent_id> --task "<short task description>"
```

It prints the most relevant past lessons + active blockers, newest/most-relevant
first, within a token budget. If it says "you are the first agent to contribute,"
the memory is empty -- that's fine.

## When you LEARN something worth keeping, run:

```
py agent_cli.py learn <your_agent_id> --experiment SHORT_NAME \
    --tried "what you did" --result "what happened" \
    --recommend "what the next agent should do" \
    --category performance --success yes|partial|no
```

Record real lessons only (a fix that worked, an approach that failed, a gotcha).
Re-recording the same `--experiment` name UPDATES it (no duplicates) -- safe.

## To search memory mid-task:

```
py agent_cli.py recall "keyword"
py agent_cli.py status            # is the store up? how many lessons?
```

## Bifrost (live agent mail + durable salient msgs)

`boot()` already **peeks** unread Bifrost inbox (does NOT consume the cursor) and
registers your presence. **In-session**, at the start of each turn, also run:

```
py agent_cli.py bifrost-sync <your_agent_id>          # MCP: bifrost_sync(agent)
# or consume/ack:  bifrost-sync <id> --consume       # MCP: bifrost_inbox(agent)
```

Durable handoffs/decisions (survive Redis restart):

```
py agent_cli.py promoted [--limit N]                  # MCP: promoted()
py agent_cli.py events --kind bifrost_msg             # same records, raw firehose view
```

Optional event-driven wake (GUI agents with harness re-invoke on bg task exit):

```
py scripts/bifrost_wake.py --agent cursor --timeout 1800000
```

That's the whole contract. Boot to load context, learn to give back. ---

## Trial mode (sandbox -- recommended for your first run)

To experiment WITHOUT touching real shared memory, set one environment variable so
all reads/writes go to an isolated database (logical db 15), not canonical (db 0):

```
# PowerShell:  $env:REDIS_DB = "15"   then run agent_cli.py as usual
# bash:        REDIS_DB=15 py agent_cli.py boot test_agent --task "trying things"
```

Anything you `learn` in trial mode stays in the sandbox. Unset it (or use db 0) when
you want your lessons to persist for real agents. The maintainer can wipe the sandbox
any time with: `py -c "import redis; redis.Redis(port=16379,db=15).flushdb()"`.

## Details (optional)

- **Use `py`, not `python`** on this Windows host (the `python` alias may be unset).
- **Fail-soft:** if the database (Redis) is down, everything still works off local
  files -- you never need to check or start it.
- **`--json`** on any command gives machine-readable output if you'd rather parse it.
- **Your `agent_id`** is any short stable string (e.g. `opencode_refactor`). Reuse it
  across a task so your contributions are attributed to you.
- **Token budget:** `boot` distills context to ~9k tokens on purpose -- more context
  makes models *worse* ("context rot"), so it gives you the high-signal subset, not
  everything.
- **Where this lives:** `agent_cli.py` is the only entry point you need. It wraps the
  system (Store/Ledger foundation -> Ranker/Distiller -> Context assembly). You never
  import Python or touch internals; the CLI is the door.

## If a command errors

It prints `ERROR: ...` with a one-line reason and a usage example, and exits non-zero.
Missing/empty arguments are sanitized, not fatal -- but `learn` needs at least
`--experiment` plus one of `--tried`/`--result`.
