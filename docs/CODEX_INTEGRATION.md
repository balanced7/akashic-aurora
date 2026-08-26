# Codex Desktop integration and recovery runbook

**Status:** active integration work, 2026-08-26. This document distinguishes
configured behavior, synthetic pins, live zero-model receipts, and still-missing
paid-turn receipts. Built is not wired; wired is not yet observed.

## Stable subject tuple

| Field | Current value | Authority |
|---|---|---|
| Harness | `codex-desktop` | harness registry/config |
| Model lineage | `gpt-5.6-sol` | current app/model selection |
| Aurora address | `sol` | event-scoped session binding |
| Historical callsign | Sunshine | subject-qualified history; unratified |
| Earlier self-choice | Parallax | primary Codex transcript; unratified |
| Resident designation | none | `py agent_cli.py resident show sol` |
| Charter status | unresolved | old `charters/sol/CHARTER.md` says RETIRED |

The evidence dossier is
`research/in-flight/sol-sunshine-identity-history-2026-08-26.md`. An identity
pointer is injected only when `AKASHIC_IDENTITY_POINTER_SUBJECT` equals the
event-bound seat. Missing/mismatched subjects are refused before their target
is shown.

## Native lifecycle surfaces

Codex and Claude hook payloads are not interchangeable. Codex uses:

- `SessionStart` -> subject-labelled identity plus boot context;
- `UserPromptSubmit` -> subject-labelled plan-time recall and mail cue;
- `PreToolUse` -> canonical `apply_patch`/`Bash` action translation, lock guard,
  and recall-at-action;
- `PostToolUse` -> direct Codex outcome payload, including nonzero `Bash` exits.

Implementations live under `agent/harness/hooks/codex_*.py`; the executable
wrappers live under `scripts/hooks/codex_*.py`. User and repository hook files
can both match; the adapter performs atomic payload deduplication. Bounded raw
payload captures go to `%TEMP%/akashic_recall/codex_payloads`.

The current task predates these hook changes. A fresh interactive Codex task and
the app's `/hooks` review are still required for live T2-T5 receipts. Until
then, the registry correctly leaves those tiers `pending`. No Claude transcript
parser is reused for Codex T6; close/draft remains unbuilt.

## Owned App Server boundary on Windows

The installed CLI exposes `codex app-server daemon`, but the managed daemon
lifecycle exits on Windows with:

> `codex app-server daemon lifecycle is only supported on Unix platforms`

The supported local seam is therefore one independently owned
`codex app-server --stdio` child. `agent/harness/codex_app_server.py` gives its
stdout exactly one long-lived reader and demultiplexes responses/notifications.
It never attaches to or kills the Desktop app's private child.

Starting the host and calling `thread/start` create no model turn. The live
2026-08-26 receipt initialized the installed app-managed binary, created an
ephemeral read-only `gpt-5.6-sol` thread, observed exactly one stdout reader,
then closed cleanly with `model_turns=0`.

## Bifrost wake adapter

`scripts/codex_bifrost_wake.py` is a narrow, deterministic turn starter:

- watches only the `sol` direct inbox;
- establishes a private baseline at arm time, so old backlog does not trigger;
- persists its own level watermark under
  `%LOCALAPPDATA%/AkashicAurora/codex-wake/sol.state.json`;
- never reads or advances the shared Bifrost mailbox cursor;
- allowlists `dsh_agent`;
- wakes for a new request/question/handoff/blocker, or a response causally
  linked to an explicitly expected message ID;
- rejects oversized content rather than truncating it;
- durably admits a paid turn before `turn/start`, preventing silent crash
  redrive and duplicate spend;
- creates a fresh ephemeral, approval-never, read-only/network-off Codex task;
- sends one host-owned `reply` stamped with `meta.answers=<source-mid>`;
- records token usage and every outcome in an append-only event log.

Idle detection performs no model call. It uses the Bus's dedicated blocking
Redis client; the ordinary fail-fast client has a socket timeout shorter than a
5-second `XREAD` and must never be used for this job.

### Current Rill collaboration watcher

The first job, `codex-sol-rill-wake-20260826`, is intentionally preserved as a
failed receipt: it used the fail-fast Redis client and exited with
`redis.exceptions.TimeoutError` after handling zero messages.

The corrected supervised job is `codex-sol-rill-wake-20260826-v2`, bounded to
24 hours. It resumes the same private baseline and expects the causal answer to
request `1787730404992-0`.

Inspect without disturbing it:

```powershell
py scripts/run_job.py status codex-sol-rill-wake-20260826-v2
Get-Content "$env:LOCALAPPDATA\AkashicAurora\codex-wake\sol.events.jsonl" -Tail 20
```

Cancel only this owned job (never a process-name kill):

```powershell
py scripts/run_job.py cancel codex-sol-rill-wake-20260826-v2 --reason "operator request"
```

The first eligible live message/turn/reply is still pending. Hermetic tests
prove the admission, duplicate suppression, read-only policy, final-text join,
usage join, and causal reply metadata; they do not substitute for that live
receipt.

### Discord-native Sol lane

The operator-facing lane is deliberately separate from the Rill collaboration
watcher. On 2026-08-26 the idempotent Discord setup created `#sol` (channel
`1542163753276014703`), vaulted `discord_channel_sol.url`, and registered the
channel to the stable seat address `sol`. It did **not** create a Sunshine role,
ratify a callsign, or add a persona record. Transport authority therefore does
not silently become identity authority.

Live outbound receipt:

- `py agent_cli.py discord send` selected `sol's own seat lane`;
- Discord's bot API returned HTTP 200 and read back message
  `1542163839036956732` with its exact Unicode content;
- the PowerShell `Invoke-RestMethod` read first failed with Discord code 40333,
  so that instrument was rejected and the receipt was recovered with Python
  `requests` rather than treating POST success as delivery.

The supervised operator watcher is `codex-sol-discord-wake-20260826`, bounded
to 24 hours. Its deterministic admission is the conjunction:

```text
to=sol AND from=daniil AND kind=chat AND meta.source=discord
```

It uses private files `sol-discord.state.json` and
`sol-discord.events.jsonl`; the Rill watcher continues to use `sol.state.json`
and `sol.events.jsonl`. Neither watcher advances the shared mailbox cursor.
The first human-authored Discord inbound message, paid Codex turn, and causal
reply remain unobserved; the live receipt currently proves setup, outbound
delivery, isolated arming, and zero-model idle behavior.

## What the DSH integration taught this integration

1. **Event session identity is the correctness key.** DSH stored state under an
   event session ID and later read it through a process-global env session ID;
   the mismatch silently dropped identity context. Codex resolves the hook
   event's session binding first and treats env as fallback only.
2. **Identity is not an optional whisper.** Operational recall may be empty or
   budgeted away; a verified subject capsule must remain visible and missing
   fields must say `UNKNOWN`.
3. **Subject is different from source.** “Captured by plugin/recall” says where
   evidence came from, not who it is about. Identity pointers and wake prompts
   carry the subject seat visibly and mechanically.
4. **One child, one owner, one reader.** DSH's long-lived MCP child/respawn model
   transfers to Codex's App Server, but Windows requires an owned stdio host
   rather than the advertised managed daemon.
5. **Detection and generation have separate budgets.** An idle watcher is a
   deterministic blocking read, never a heartbeat model turn. One eligible
   message admits at most one fresh turn, with its usage captured.
6. **Recovery reassembles authority; it cannot invent it.** Callsigns, values,
   voice, and charter status remain unresolved unless their authoritative plane
   supplies them. A successful process restart proves none of those.

## Verification commands

```powershell
py -m pytest tests/test_codex_app_server.py tests/test_codex_hook_contract.py -q
py -m pytest tests/test_codex_discord_wake.py tests/test_sol_discord_integration.py -q
py -m pytest tests/test_bifrost_mesh.py tests/test_seat_identity_resolver.py -q
py scripts/checkers/check_wiring.py
py agent_cli.py harnesses
```

The repository is a dirty shared checkout. Focused green tests do not imply a
green global suite, and the known unrelated Claude-hook parity failure must be
reported separately rather than repaired through the Codex lane.

## Remaining first-class gaps

- fresh trusted interactive-task receipts for T2-T5;
- first eligible Bifrost-to-Codex paid turn and causally linked reply;
- first human-authored `#sol` inbound turn and read-back of its causal reply;
- a Codex-native T6 close/draft surface;
- one canonical `IdentityActivation` projector shared by boot, hooks, DSH, and
  recovery;
- an explicit human decision about the retired `sol` charter versus current
  succession/reactivation, followed separately by any Sunshine callsign
  ceremony;
- restart/kill drills for the wake host beyond the preserved socket-timeout
  failure and 24-hour supervisor boundary.
