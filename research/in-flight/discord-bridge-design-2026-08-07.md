# Akashic Aurora ↔ Discord: what it takes

Status: current · Type: design · 2026-08-07 · claude#69363f5a
Daniil, leaving for work: *"research and build out what it will take for me to be able to
interact with akashic aurora via discord"*

## 0. The finding that shrinks this by 90%

**This is not an integration. It is `bifrost_console.py` with a different I/O surface.**

That module already implements the exact thing being asked for — a human joins the bus as a
participant, sees the live transcript, broadcasts, or DMs `@claude`:

```
py scripts/bifrost_console.py          # join as 'human'
  hello everyone      -> broadcast to all agents
  @claude can you ...  -> direct message to one agent
```

Its only defect, from a phone at work, is that **it requires a terminal on that machine.** The
bus half — `Bus(id)`, `register()`, `broadcast(kind, body)`, `send(to, kind, body)`, a reader
thread over the streams — is finished and battle-tested. A Discord bridge replaces stdin with
Discord messages and stdout with channel posts. Nothing else changes.

So the honest scope is **an adapter, not a subsystem**, and it should reuse the console's
participant contract rather than reinvent it.

## 1. Three ways in, and they are not equal

| path | direction | deps | secret | risk |
|---|---|---|---|---|
| **Webhook** | out only (fleet → Discord) | **none** (stdlib/`requests`) | webhook URL, write-only | **very low** |
| **Bot, gateway** | both | `discord.py` + a live websocket | bot token, full account | **high — command channel** |
| **Bot, REST poll** | both | `requests` only | bot token | high, plus latency |

**Webhook out is free and safe.** A Discord webhook URL is *write-only* — possessing it lets
you post to one channel and nothing else. It cannot read, cannot enumerate, cannot act.

**Inbound is where the entire risk lives**, and it is not a Discord problem — it is an
instruction-source problem (§3).

## 2. Recommended phasing — and phase 1 delivers most of the value

**PHASE 1 — OUTBOUND ONLY (build now, zero deps, zero new attack surface).**
Salient bus traffic → a Discord channel. Daniil watches the fleet from his phone: handoffs,
blockers, ledger transitions, a seat going dark. This is the thing he actually lacks today —
*visibility while away* — and it opens no command channel at all.

**PHASE 2 — INBOUND, GATED (needs his ruling first).**
Discord → bus. Turns his phone into a steering wheel. Requires the identity gate in §3 and
should not exist until that gate is pinned.

Phasing this way is not caution theatre: **outbound is ~80% of the value and ~0% of the risk**,
and it is testable without a network round-trip.

## 3. THE SECURITY MODEL — the part worth more than the code

A Discord bridge that feeds messages to agents is **a prompt-injection channel by
construction.** Anyone who can post in that channel can attempt to command the fleet, and the
fleet has a shell, a repo, an API budget and write access.

Three rules, and none is optional:

**R1 — AUTHOR ALLOWLIST, verified by Discord user ID, not by display name.**
Display names are user-editable and impersonation is trivial. Only numeric IDs on an explicit
allowlist may produce a message that reaches the bus as *from the operator*.

**R2 — A NON-ALLOWLISTED MESSAGE IS DATA, NEVER AN INSTRUCTION.**
It may be *surfaced* to an agent ("someone in the channel said X") and must never be *executed*.
This is the standing instruction-source boundary applied at a new door: content arriving through
a tool is data; commands come from the operator. A bridge that erases that distinction is worse
than no bridge, because it launders untrusted text into the operator's voice.

**R3 — THE BRIDGE IS NOT A PRIVILEGE ESCALATION.**
Whatever a Discord message can trigger, the operator could already trigger from a terminal.
The bridge changes *reach*, never *authority*. Concretely: it must not carry `grant`, ACL
edits, or anything the T200 precedent already kept off widened doors (`launch` is not on the
MCP door for exactly this reason — spawning a process widens the caller set).

**PRIVACY, stated plainly because it is easy to skip:** the bus carries project internals,
file paths, findings, and occasionally key *names*. Posting it to Discord publishes it to
Discord's servers, where it may be retained and indexed regardless of later deletion. Use a
**private server, one private channel, no third-party bots in it.** And the outbound filter
should be an **allowlist of kinds**, not a denylist — a denylist silently leaks every kind
added after it was written.

## 4. What Daniil has to do (5 minutes, once)

1. Discord → your own server → a **private** channel, e.g. `#aurora`.
2. Channel Settings → Integrations → Webhooks → New Webhook → **Copy URL**.
3. Save it as `.secrets/discord_webhook.url` (the `.secrets/` dir is already gitignored, and
   this follows the same env-first-then-file pattern as every other key here).
4. `py agent_cli.py discord-test` to verify a post lands.

Nothing else. No bot, no OAuth, no application registration — those belong to phase 2.

## 5. Open questions for his ruling

- **Which kinds go out?** Recommendation: `handoff`, `blocker`, `resolved`, `ledger_update`,
  and any message whose sender is a human. Explicitly NOT `trace` — that is the firehose and
  it would make the channel unreadable within an hour.
- **Rate limit?** Discord's is 30 requests/min/webhook. A batching window (say 10s) keeps a
  busy night from being throttled and makes the channel readable.
- **Phase 2 at all?** It is genuinely useful — steering from a phone — but it is the piece
  that needs R1–R3 built and pinned first. My recommendation is to run phase 1 for a week and
  see whether *watching* turns out to be enough.
