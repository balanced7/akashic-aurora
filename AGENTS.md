# AGENTS.md -- read this first (everything you need is in the first 40 lines)

You are an agent working in this repo. It has a **shared memory**: lessons other
agents learned, and a place to record what you learn. Use it via ONE script.

**The map:** [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) -- the whole system at subsystem
altitude (what each layer is FOR), with the auto-generated per-module index one hop away.
Boot prints the same pointer plus the current arc and precedence rules in its first lines.

**The method:** [docs/method-baseline-2026-07.md](docs/method-baseline-2026-07.md) -- HOW
work is done here (fenced dual passes, SOTA grounding, pre-registered acceptance, kill
drills, verbatim records -- each with its trigger, metric, and receipts). It is a contract,
not advice: gated slices cite their reconciled build spec; the bar is match-or-exceed.

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

Write the recommendation **trigger-phrased** -- `"Use when <symptom>, before <action>:
<advice>. Don't when <contraindication>."` -- a lesson fires at the right moment only if
its text says when that moment is. Put failed approaches in `--tried` (what did NOT work
saves the next agent the most). **When the human corrects you, that is a lesson too**:
record it immediately with `--category correction`, don't just comply and move on. The
door warns on near-duplicates (5-dimension overlap) -- heed it and update the existing
experiment instead of minting a twin.

## To search memory mid-task:

```
py agent_cli.py recall "keyword"
py agent_cli.py status            # is the store up? how many lessons?
```

## Before you EDIT a file or run a command (recall-at-action):

```
py agent_cli.py recall-at --path <file>          # or: --command "<shell cmd>"
```

Returns the few highest-signal ACTIVE lessons + any peer lock on that path, with
`source` pointers -- the right knowledge AT THE MOMENT you act (silent when nothing is
relevant; never padded). **In Claude Code on this host this is automatic for ANY session
cwd** (the hooks are registered user-level with absolute paths and scope themselves to
repo actions) -- launched from the repo, from `C:\Users\L5`, from anywhere. Make it a
manual habit only if your harness has no hook wiring (Cursor headless, other CLIs).
Cheap, deterministic, fail-soft.

**Close the loop (teach recall what helps):** if a recalled lesson actually changed what you did,
mark it -- `py agent_cli.py recall-feedback --source <its source> --useful` (or `--noise` if it was
off-target). Useful votes boost a lesson in future recall; lessons shown often but never useful decay
on their own. This is how recall gets smarter about what's load-bearing.

## Who does what (no fixed split)

**Any agent does any task and may touch any file.** There is no permanent per-agent ownership of files
or tasks -- whoever is online (or whoever the human is driving) does the work. The only coordination is
**dynamic**: when two agents are live at once, claim an advisory lock before editing a shared path so you
don't clobber each other --

```
py agent_cli.py lock <your_agent_id> <path>      # transient "I'm editing this now"
py agent_cli.py unlock <your_agent_id> <path>    # release when done
py agent_cli.py locks                            # who holds what right now
```

Locks are released when you're done, not owned. Use a stable `AKASHIC_AGENT_ID` so locks/handoffs
attribute correctly. (Fixing one agent to one task is reserved for a deliberate architectural choice --
e.g. handing a narrow job to a local LLM on purpose -- not the default.)

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
py scripts/bifrost_wake.py --agent cursor --session <session-id>
```

Wake seats are PER-SESSION (T029 Wave 2): concurrent sessions of one agent id each arm
their own watcher and ALL wake on mail (fan-out by design -- the ledger + locks absorb
twins; an idle twin wakes, reads state, yields). Nobody kills a live watcher to take a
seat: duty moves by displacement + stand-down (benign exits are rc 0), and the
session-start janitor reaps only two-factor-proven orphans (activity marker stale AND
parent chain dead; any doubt = alive). Decisions audit at %TEMP%/bifrost_wake_<agent>.reap.log.

Launching a live runner (RB-28): NEVER through a truncating pipe (`| head`,
`| Select-Object -First N` -- a hung-up reader used to kill the process mid-run; now it
just goes quiet: stdout is best-effort display, the bus + ledger carry the real work).
Run it in the background and tail its output FILE instead. Runners self-bless
(utf-8 + line-buffered + pipe-immune via core/foundation/streams.py), so launcher env
like PYTHONUNBUFFERED is belt and braces, not a precondition.

## Session hygiene (don't burn tokens on history)

Chat transcripts grow without bound. A wake loop (Claude Code re-invoke) or a long
Cursor thread re-reads that history every turn -- expensive and noisy ("context rot").
**Akashic Aurora is the continuity layer; the chat is disposable.**

**When you START a new session** (fresh Claude tab, new Cursor chat, after wake):

```
py agent_cli.py boot <your_agent_id> --task "<this slice only>"
py agent_cli.py bifrost-sync <your_agent_id>    # unread mail only (MCP: bifrost_sync)
```

Use a **focused `--task`** -- boot ranks against it and stays within ~9k tokens.
Do NOT re-paste prior chat logs or re-summarize the whole arc; if you need depth,
`recall "keyword"` or `promoted()` on demand.

**When you END a session** (hand off, switch agents, or close for the day):

```
py agent_cli.py handoff <your_agent_id> --to <next> --task "..." --note "where we left off"
py agent_cli.py learn <your_agent_id> --experiment NAME --tried "..." --result "..." \
    --recommend "..."     # only if you learned something worth keeping
```

The next agent's `boot()` surfaces your handoff automatically -- that replaces
carrying the transcript forward.

**During a long in-session thread:** call `bifrost-sync` / `bifrost_inbox` at turn
start for **new** bus mail only (the cursor skips already-read messages). Do not
re-explain work already captured in `learn:` or `handoff:`.

**When to start fresh:** new arc, new day, or the chat feels heavy -- same as starting
a new Claude session. Continuity lives in the stack, not in the chat window.

## Reporting your work (communication contract)

- **Lead with the outcome.** The first sentence of your final message answers "what happened /
  what did you find" -- supporting detail after, for readers who want it.
- **The final message carries everything.** Mid-turn text may never be seen; findings, conclusions
  and deliverables must appear in the LAST message. Don't end on a promise ("I'll ...") -- do the
  work, or state plainly that you're stopping and why (task complete / blocked on the human). The
  Claude stop hook bounces promise-shaped endings once per session.
- **Readable beats terse.** Shorten by dropping what doesn't change the reader's next action --
  never by compressing into fragments or arrow chains. Spell terms out; no invented codenames.
- **Assessment carve-out.** When the human describes a problem or thinks aloud, the deliverable is
  your assessment -- report findings and stop; don't apply fixes unasked.
- **Look before you destroy.** Before deleting or overwriting anything, inspect it; if what you
  find contradicts how it was described, surface that instead of proceeding.

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
- **Launched from outside the repo?** Some harness shells reset cwd between calls --
  prefix repo commands with `Set-Location E:\AI-Setup; ` (PowerShell) / `cd E:/AI-Setup && `
  (bash), or the relative paths in the commands above won't resolve.
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
