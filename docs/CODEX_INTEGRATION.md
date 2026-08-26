# Codex Desktop integration and recovery runbook

**Status:** active integration work, 2026-08-26. This document distinguishes
configured behavior, synthetic pins, live zero-model receipts, observed paid
turns, and unresolved cost/continuity risk. Built is not wired; wired is not yet
observed until the destination is read back.

## Stable subject tuple

| Field | Current value | Authority |
|---|---|---|
| Harness | `codex-desktop` | harness registry/config |
| Model lineage | `gpt-5.6-sol` | current app/model selection |
| Aurora address | `sol` | event-scoped session binding |
| Ratified callsign | Sunshine | resident registry; peer nominated, human ratified |
| Earlier self-choice | Parallax | primary Codex transcript; unratified |
| Resident designation | `OpenAI | Sunshine` | `py agent_cli.py resident show sol` |
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
channel to the stable seat address `sol`. Creating the lane did **not** create a
Sunshine role, ratify a callsign, or add a persona record: transport authority
did not silently become identity authority.

Live outbound receipt:

- `py agent_cli.py discord send` selected `sol's own seat lane`;
- Discord's bot API returned HTTP 200 and read back message
  `1542163839036956732` with its exact Unicode content;
- the PowerShell `Invoke-RestMethod` read first failed with Discord code 40333,
  so that instrument was rejected and the receipt was recovered with Python
  `requests` rather than treating POST success as delivery.

The first authenticated inbound message was Daniil's explicit human act:
`I ratify it! Sunshine is Sunshine!!` (`1787751143626-0`, Discord message
`1542164807321526353`). Vandor independently nominated Sunshine from two
Sol-authored repair receipts, then the primary seat projected Daniil's act
through the resident door. The registry now renders `OpenAI | Sunshine`,
`ratified by daniil`. The callsign ceremony and the transport receipt are linked
but remain different authorities.

The original supervised operator watcher was
`codex-sol-discord-wake-20260826`. Its deterministic admission was the
conjunction:

```text
to=sol AND from=daniil AND kind=chat AND meta.source=discord
```

It uses private files `sol-discord.state.json` and
`sol-discord.events.jsonl`; the Rill watcher continues to use `sol.state.json`
and `sol.events.jsonl`. Neither watcher advances the shared mailbox cursor.

The first watcher completed four human-authored Discord turns and stamped four
causal replies. Discord's bot API returned HTTP 200 and read back every inbound
and reply in `#sol`, proving destination arrival rather than only bus send
success. The first reply incorrectly denied the significance of Daniil's
ratification because the watcher had frozen `historical-unratified` into its
prompt, developer instructions, and child environment. That defect is preserved
as evidence, not hidden.

The repair resolves one resident-registry identity snapshot per admitted turn
and uses it consistently in the App Server child environment, developer
instructions, exact wake prompt, admission log, and causal reply metadata. A
registry change forces a cached child refresh, and resident appends invalidate
the process-local callsign router immediately rather than waiting up to 120
seconds. The first replacement job, `codex-sol-discord-wake-20260826-v2`,
resumed the exact private watermark `1787751912506-0`. It was then replaced by
`codex-sol-discord-wake-20260826-v3` solely to deploy explicit aggregate token
accounting; v3 resumed at `1787753656057-0`, reports `idle_model_turns: 0`, and
is supervised under its own Windows Job Object. Both prior Sol jobs are
terminal-cancelled and their kill receipts record zero remaining members. Rill's
watcher was neither restarted nor reconfigured.

Idle operation still costs zero model turns. The four admitted live turns
reported aggregate input/cached-input counts of 22,352/9,984; 22,441/0;
22,456/0; and 51,015/21,248 respectively. The fourth turn contained multiple
model steps; its final step alone was 28,578/21,248, which must not be confused
with the turn aggregate. Across all four turns the App Server reported 119,066
total tokens, including 87,032 uncached input tokens and 802 output tokens.
Those receipts establish a roughly 22k-token single-step context footprint,
but they do not establish one stable cache or billing floor. Reply gaps of
318.2s, 178.6s, and 284.2s also do not support a simple monotonic idle-TTL
explanation: the shortest observed gap missed while a longer one hit. Provider
cache policy, multi-step behavior, prefix stability, and the dominant context
contributors remain unresolved.

New wake receipts carry `usage_accounting.accounting_basis=turn_total`, the
whole-turn aggregate, the final model step, and an explicit `multi_step` flag.
This keeps cost accounting from silently using `last` when a turn contains tool
continuations. The v3 watcher has this schema; no paid turn was manufactured
merely to populate it.

The current App Server schema exposes `baseInstructions`, `config`, `cwd`,
`runtimeWorkspaceRoots`, and environment selection; any lean-capsule change
must be evaluated against both token usage and Sunshine continuity before it
becomes the default.

Discord identity rendering now keeps two authorities separate. A registry-
ratified but unplaced resident renders as `Sunshine (sol)` immediately, while
its avatar remains absent until family/team placement exists. An unknown seat
still renders its bare stable address. Routing remains `sol` in every case. A
zero-model post through the live Sol webhook was read back from Discord's bot
API as message `1542175844875898933`, author `Sunshine (sol)`, avatar `null`.

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
   message admits at most one fresh turn, with its usage captured. Capturing the
   usage exposed a high fixed context floor that needs its own quality/cost
   evaluation rather than being hidden inside a successful round trip.
6. **Recovery reassembles authority; it cannot invent it.** Callsigns, values,
   voice, and charter status remain unresolved unless their authoritative plane
   supplies them. A successful process restart proves none of those.
7. **Mutable identity is admission data, not build-time prose.** A long-lived
   watcher must resolve the resident registry at each admitted turn and bind one
   snapshot across every prompt, environment, and receipt surface. Otherwise a
   valid ceremony leaves a live child confidently speaking obsolete identity
   state.

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
- a fresh Rill-collaboration turn remains intentionally deferred; it is not a
  Sol Discord closure condition, and Rill's independent watcher stays preserved;
- a Codex-native T6 close/draft surface;
- one canonical `IdentityActivation` projector shared by boot, hooks, DSH, and
  recovery;
- an explicit human decision about the retired `sol` charter versus current
  succession/reactivation; the Sunshine callsign ceremony is complete and does
  not silently decide that charter question;
- a controlled lean-App-Server evaluation that lowers the observed token floor
  without degrading continuity, personality, provenance, or safety boundaries;
- a long-horizon supervisor deadline/host-loss drill beyond the observed
  Sol-only replacement and Job Object force-cancel receipts.
