# Codex Desktop integration and recovery runbook

**Status:** current. Active integration work, updated 2026-09-02. This document
distinguishes configured behavior, synthetic pins, live zero-model receipts,
observed paid turns, and unresolved cost/continuity risk. Built is not wired;
wired is not yet observed until the destination is read back.

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

Starting the host and calling `thread/start`, `thread/fork`, or `thread/resume`
create no model turn. The live
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
- resumes one durably bound, persistent Codex task with
  approval-never/read-only/network-off policy;
- creates and binds one persistent task only when no explicit binding exists;
  it never substitutes a fresh task when a recorded thread cannot be resumed;
- defers without advancing its private watermark when another host owns the
  thread writer, preserving serialization without losing or double-spending a
  Discord message;
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
and the multi-step turn makes the attribution unusually clear: subtracting its
final step from the aggregate leaves 22,437 input tokens, within four tokens of
the 22,441-token single-step turn. Its 21,248 cached tokens belong to the final
continuation reusing that same turn's prefix; they are not evidence that a later
Discord message reused an earlier message's context. Turns two and three showed
zero cached input. Turn one's 9,984 cached tokens have no established source and
did not recur reliably. The observed operator-message floor is therefore a real
approximately 22.4k first-step input cost, while provider cache policy, prefix
composition, and the dominant context contributors remain unresolved.

New wake receipts carry `usage_accounting.accounting_basis=turn_total`, the
whole-turn aggregate, the final model step, and an explicit `multi_step` flag.
This keeps cost accounting from silently using `last` when a turn contains tool
continuations. The v3 watcher has this schema; no paid turn was manufactured
merely to populate it.

The current App Server schema exposes `baseInstructions`, `config`, `cwd`,
`runtimeWorkspaceRoots`, and environment selection; any lean-capsule change
must be evaluated against both token usage and Sunshine continuity before it
becomes the default.

### Current persistent Sunshine binding (2026-09-02)

The 2026-08-26 operator watcher was an informative live experiment, not a
durable service: its supervised job had a 24-hour lifetime, and each Discord
message created a different ephemeral Codex task. It expired on 2026-08-28.
The per-message task design guaranteed conversational amnesia and repeatedly
paid the cold-start context floor documented above.

The replacement uses one persistent history-bearing branch. The source is the
direct Daniel/Sunshine Desktop conversation, bounded through its last completed
turn. The branch was created by an independently owned App Server
`thread/fork`, not by the Desktop fork UI: a Desktop-created child remained
leased by Desktop and correctly refused an external `thread/resume`. Closing
the integration-owned forking host released its lease; two separate fresh App
Server processes then resumed the same branch ID successfully without starting
a model turn. The exact local lineage is recorded in
`%LOCALAPPDATA%/AkashicAurora/codex-wake/sol-discord-continuity.state.json`, not
hard-coded into the public repository.

The private state is schema 2 and bind-once. It records the continuity thread,
the source thread, `binding_kind=completed-history-fork`, bound time, private
watermark, and per-message outcomes. A mismatched launch argument is a refusal,
not a migration. Missing-thread and active-writer errors do not create a
replacement conversation and do not advance the watermark.

Two persistent Windows tasks now separate responsibilities:

- `AkashicAurora-SunshineFleet` runs `bifrost_daemon.py` with Sunshine's own
  `bifrost_runner_sol.py` as its managed child. The child is agentic, write- and
  exec-enabled subject to the existing ACL/ToolBox walls, and carries
  `--ignore-source discord`. Its environment explicitly pins
  `BIFROST_CONSUME_LANE=work`; it cannot silently fall back to the legacy
  cursor merely because a scheduled-task parent lacks the launcher overlay.
  The daemon, rather than a bare runner, owns the Discord outbound feed pump.
- `AkashicAurora-SunshineDiscord` owns only authenticated Discord ingress from
  `daniil` with `kind=chat` and `meta.source=discord`, and resumes the bound
  history-bearing Codex task. Idle operation performs no App Server or model
  work.

Both tasks run at logon, start when available, allow battery operation, have no
execution-time limit, reject twin instances, and carry a restart policy for
later process failures. The fleet task passes `--external-supervisor`. Without
that flag,
the daemon's normal stale-code metabolism launched a detached successor and
exited 0; Task Scheduler then reported `Ready` while the orphaned successor
continued running, so a later crash would not have triggered its restart
policy. A second live drill showed that this host did not automatically retry
an immediate singleton refusal even though the task XML contained
`RestartOnFailure`: it remained `Ready` with result 75 for the full 110-second
observation window. Externally supervised daemons therefore wait for a prior
TTL lease inside the same scheduler-owned process; they do not exit during the
handoff. The existing detached self-restart and fail-fast lock refusal remain
the defaults for other callers. An isolated live two-daemon drill then proved
the supervised contract rather than only its unit seam: the successor remained
alive while PID 10532 held the lease, acquired it in the same process after the
first daemon exited, and both processes returned 0. Reinstall or update the
tasks with the local continuity IDs:

```powershell
./scripts/install_sunshine_discord_tasks.ps1 `
  -ThreadId <discord-continuity-thread-id> `
  -SourceThreadId <direct-history-source-thread-id>
```

Inspect without consuming any cursor or disturbing the running tasks:

```powershell
Get-ScheduledTask AkashicAurora-SunshineFleet,AkashicAurora-SunshineDiscord
Get-Content "$env:LOCALAPPDATA\AkashicAurora\codex-wake\sol-discord-continuity.state.json"
Get-Content "$env:LOCALAPPDATA\AkashicAurora\codex-wake\sol-discord-continuity.events.jsonl" -Tail 20
```

The Sol runner now honors `bifrost-drain` at its loop boundary and clears stale
pre-tenure drain requests before onboarding. The one legacy bare runner that
predated this code could not honor a graceful drain; it was proven idle with no
activity and zero backlog, then its exact PID alone was retired. The waiting
daemon replaced it with the managed full-door command line. This exception is
an incident receipt, not the new lifecycle procedure.

The first managed transition also exposed why the work-lane pin is not
decorative. Before the pin, the successor inherited no consume-lane environment
from Task Scheduler and began processing legacy traffic. Its worklive counter
reached seven turns during the transition; the daily Sol journal snapshot read
15 turns and 3.2 million unpriced tokens across all tenures that day. That
journal is not precise enough to attribute all 3.2 million tokens to this one
process, but it is conclusive evidence that an implicit legacy lane is not an
acceptable launch posture. The process was allowed to finish its in-flight
turns, held at a targeted loop boundary, then replaced with the explicit work
lane.

Current observed gates are: 55 focused tests green; persistent branch lineage
read back as `forkedFromId=<direct-history-thread>` and `status=notLoaded`;
two fresh-process resumes green; both Windows tasks running; daemon parent and
managed Sol child command lines correct; watcher armed with zero idle turns.
The managed outbound feed is also destination-proven: Bifrost message
`1788359047651-0` (`FEED617A`) appeared in `#sol` as Discord message
`1544714561893179444`, and its exact body was read back through Discord's bot
API. After the scheduler-anchor repair, Bifrost message `1788360912798-0`
(`ANCHOR-FFF05B52`) traversed the new daemon and was read back exactly as
Discord message `1544722382768308234`; Task Scheduler still owned daemon PID
64012 and managed runner PID 66768 remained its child after the first
stale-code-check interval. The final human-authored inbound nonce, bound-task
reply, and destination readback are still required before claiming end-to-end
reachability.

## Governed Aurora verb execution

Sunshine's Discord incarnation now has two always-visible client-owned read
tools and one conditional combo executor when launched with governed exec.
`aurora_read_verb` accepts a structured `{verb, args}` object for governed
primitives. `aurora_combo_catalog` accepts no arguments and explains which
active subject-owned aliases the bridge would admit or omit, without executing
anything. `aurora_read_combo` appears only when at least one live, safe,
zero-argument combo exists and accepts one name from that roster. None exposes
a raw command string, working-directory override, write tool, network tool,
generic `run`, macro arguments, peer-owned belt, or approval escape hatch. The
Codex thread itself remains `read-only`, `networkAccess=false`, and
`approvalPolicy=never`.

The dynamic tool is a bridge into Aurora's existing guarded door, not a second
shell. A call succeeds only when all four layers agree:

1. the watcher was explicitly launched with `--allow-exec`;
2. the live ACL record for the subject seat still contains `exec`;
3. Sunshine's bridge-local grammar accepts both the verb and its exact argument
   shape;
4. `ToolBox` accepts the exact `py agent_cli.py <read-verb> ...` family, rejects
   mutation flags and rejects every shell metacharacter before using
   `shell=False`.

The model-visible enum currently contains 17 deliberately read-only verbs:
`discover`, `doctor`, `flightdeck`, `flow`, `harnesses`, `injections`,
`knowledge-map`, `list`, `locks`, `lookback`, `promoted`, `pulse`, `recall`,
`stats`, `status`, `triage`, and `unwedge`. Each has a separate positional and
flag grammar. In particular, the bridge refuses `task`, `fence`, and `notes`
even though the older ToolBox family list names them, refuses the mutating
`doctor --page` form, and refuses the extra paid-model `discover --semantic`
form. The bridge's authority therefore cannot widen merely because ToolBox's
shared historical allowlist changes.

The combo tool is rebuilt at every admitted turn from `data/verb-registry/sol.json`.
The host expands each candidate through the toolbelt organ, admits only authored
combos with zero parameters, and preflights **every** expanded step against the
same 17-verb bridge grammar before executing step one. Each admitted primitive
then re-enters ToolBox independently, so the launch flag and live ACL remain in
force for every step. A later unsafe verb or shell token therefore refuses the
whole combo without partial execution. Combined output is capped at 24,000
characters so composition cannot multiply three individually bounded reads into
an unbounded model injection.

The admission catalog closes the bridge's former silent-omission seam. It lists
each active alias as `ADMITTED` or `OMITTED`, carries evidence and family, and
names the first failing step plus the exact bridge refusal. It accepts no
`agent` argument, so a subject cannot use it to inspect a peer-owned belt. A
registry read failure renders `UNAVAILABLE` and a failed tool result rather than
a falsely clean empty catalog. The result shares the 24,000-character whole-
output cap and never enters `ToolBox.run_command`.

The first live belt session rejected both of its own opening candidates.
`pressure = triage -> doctor -> locks` parsed, kata-verified, and ran
successfully, but cost 6.7 seconds and roughly 13.5k output characters while
the existing higher-rung `flightdeck --agent sol` answered the
operational-pressure question in roughly 2.3k. Kimi's fleet cross-review caught
the duplication; Sunshine retired `pressure` with its history intact.

`dosage = injections --hours 6 -> stats --hours 6` also parsed, verified, and
ran, but a second three-seat review found that its adjacency invited a false
return-on-spend reading across mixed denominators. Direct dogfood then supplied
the cheaper falsifier: `stats --hours 6` already reports same-window injection
cost, flips, and lessons recorded in about 300 characters, while the additional
injection ledger contributed roughly 6k characters without answering another
operational question. Sunshine retired `dosage` too. The belt therefore has
zero active combos after this round; history retains both candidates, and the
bridge omits `aurora_read_combo` on the next admitted turn until a new combo
passes the same admission and cross-review.

Round 6 deliberately produced no replacement. Kimi returned the empty set after
finding every honest candidate already owned by a primitive. DeepSeek's
`runtime-drift` idea required introspecting bridge admissions and therefore
became the catalog diagnostic above rather than a pretend composition. Vandor's
`roster -> doctor -> locks` candidate failed live: `roster` alone rendered about
10.4k characters, the proposed three reads totaled roughly 18.1k, and
`flightdeck` already rendered the relevant lane and lock overview in about
2.6k. More importantly, advisory edit locks do not establish whether a seat can
receive mail. Keeping the active belt empty is the verified garden outcome.

That session also found and repaired an older toolbelt honesty defect: `kata`
upgraded evidence by re-minting without the authored `family`, silently turning
entries such as Rill's `rillsitrep` from `MONITORS` into `UNSORTED`. Kata now
preserves family while changing only verification evidence. The repair is
pre-registered by a RED pin before implementation.

One evidence-lifecycle question remains open rather than being hidden in this
slice. Kimi found a `VERIFIED` DeepSeek combo whose old `bifrost_dashboard`
primitive no longer exists in the live parser. The combo bridge safely omits
that entry because it revalidates the current roster before advertising it,
but the belt still renders the historical `VERIFIED` label. Fleet review
rejected both a blind demotion to `GUESS` and an `EXPIRED` value smuggled into
the confidence axis. Round 6 then corrected the proposed taxonomy: `kata` is a
parse-only instrument and cannot observe a transient execution failure. The
stable candidate split is now static versus dynamic: an absent primitive is
referential death and should retire; a present primitive with rejected argv is
malformed and should demote; a grammar-clean runtime failure belongs to the
runner's execution receipt, never `last_kata`; an unreadable subject is
`UNKNOWN`, not missing. That policy remains under adversarial review; this
slice makes the admission disagreement visible but does not mutate the
peer-owned belt or silently settle its evidence lifecycle.

The App Server host now distinguishes reverse JSON-RPC requests from ordinary
notifications and answers `item/tool/call` on a worker thread. This preserves
the one-stdout-reader invariant while a verb runs. An unknown request receives
a JSON-RPC method-not-found response instead of hanging the paid turn. Because
dynamic tools are an experimental App Server surface, the host negotiates
`capabilities.experimentalApi=true` only for exec-enabled watcher instances;
it also refuses a local `dynamic_tools` start before that negotiation.

The instance-local `sol` ACL record was reactivated permanently at Daniil's
direct request with only `read`, `exec`, `bus.send`, `bifrost.inbox`,
`git.read`, `kb.recall`, and `kb.learn`. It has no write scope, network,
steering, or grant/approval authority. The canonical grant door records
`granted_by=claude` because that is the effective super-admin profile used by
the consistency guard; the record's reason and `request_ref` state that the
actual authorization was Daniil's direct Codex message and that `--by` is not
authentication.

The live supervised job is `codex-sol-discord-wake-20260826-v8`. It resumed the
private watermark `1787805814662-0` and armed with `allow_exec=true`,
`dynamic_tools=["aurora_read_verb", "aurora_combo_catalog"]`, and
`idle_model_turns=0`. V7 was idle when it was displaced to load the admission
catalog, but its blocking read did not quiesce inside the five-second grace
window; the Windows Job Object force receipt reports `remaining_pids=[]`, and
an independent exact-PID read found every former member gone. V8 is running
with child PID `4560`, supervisor PID `51476`, watchdog PID `53160`, and verified
Job Object membership. No message or model turn was admitted during the
replacement. The independent
`codex-sol-rill-wake-20260826-v2` job was only status-read and remained running
with child PID `18984`, supervisor PID `13284`, watchdog PID `25988`, and no
cancel request.

That ARMED line is a launch-time receipt, not a permanent roster claim. The
host rebuilds `dynamic_tools` when each message is admitted. Because the live
Sunshine belt now has zero active entries, the next admitted turn will expose
`aurora_read_verb` plus the non-executing `aurora_combo_catalog`; the combo door
reappears automatically when a safe zero-argument combo exists.

No paid model turn was manufactured for this deployment. A hermetic App Server
fixture proved the reverse request/response join and capability negotiation. A
live zero-turn `thread/start` then accepted the real 17-verb primitive schema
and the no-argument admission catalog with one stdout reader, no protocol noise,
and zero model turns. A live `sol` bridge receipt ran
`discover` and separately refused `learn`, the positional mutation forms
`task done`, `fence open`, and `notes --project`, the side-effecting
`doctor --page`, the paid `discover --semantic` form, and `discover; whoami`.
The first organic Discord tool use remains the end-to-end model receipt.

Two adjacent shared-surface gaps remain explicit. ToolBox's historical family
allowlist is too coarse to classify positional subactions on its own; Sunshine's
bridge now contains the narrower grammar, but direct callers of that shared
family still require a separate global repair. Also, ACL files contain the
historical token `verb.author`, but `core/trust/capabilities.py` does not
currently define it and
the `alias` door does not consult it. Therefore this change does **not** claim
governed alias authoring. Repairing that global contract would change other
seats' current behavior, including Rill's, and is deliberately not smuggled
into Sunshine's exec activation.

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
py -m pytest tests/test_codex_app_server.py tests/test_codex_hook_contract.py tests/test_t099_v01_kata.py -q
py -m pytest tests/test_codex_discord_wake.py tests/test_sol_discord_integration.py -q
py -m pytest tests/test_t169_budget_exhaustion_still_answers.py -q
py -m pytest tests/test_bifrost_mesh.py tests/test_seat_identity_resolver.py -q
py scripts/checkers/check_wiring.py
py agent_cli.py harnesses
```

The first unbounded global gate attempt in this session reproduced the prior
resource failure: pytest reached roughly 64 GB private memory before manual
termination. A bounded verbose replay localized the discrete jump to
`test_t169_budget_exhaustion_still_answers.py::test_f1_exhaustion_still_returns_an_answer`.
Production had intentionally changed DeepSeek's default tool-round limit to an
unlimited `10**9` sentinel, while the old test materialized
`range(DC.MAX_TOOL_ROUNDS)` into a list. The acceptance test now installs its
own three-round cap and all five T169 pins pass in under one second; production
remains unlimited. A bounded replay of the remaining 1,547 tail outcomes
completed with a 2.13 GB peak. The traversed global tree still contains
unrelated failures, so these receipts are not represented as a globally green
suite.

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
