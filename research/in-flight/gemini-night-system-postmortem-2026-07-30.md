# Gemini Night system postmortem — 2026-07-29/30

**Status:** evidence-backed incident analysis; no fixes or fleet actions were performed  
**Evidence cutoff:** 2026-07-30 09:47 EDT, repository `6da4d5f` plus the dirty shared worktree  
**Primary incident window:** 2026-07-29 23:31 EDT through 2026-07-30 01:27 EDT  
**Aftershock window examined:** 2026-07-30 05:26 through 09:25 EDT

## Executive finding

This was not one bad model, one bad agent, or one Bifrost bug. It was a
**distributed coordination cascade**.

The fleet had many durable local facts, but no typed, one-hop projection of the
current world that joined:

- the narrative trunk and active lanes;
- who or what an identity represented on each transport;
- which authority covered membership, spend, launch, editing, or user voice;
- whether a message was delivered, seen, being acted on, superseded, or settled;
- whether a seat was alive, dormant, blocked, replaced, or merely absent from one view;
- which artifact was canonical, projected, stale, or still uncommitted.

Gemini's arrival and the open-play round supplied novelty and concurrency. They did
not create the underlying defects. Under load, each subsystem exposed a different
partial truth. Agents tried to restore legibility by sending more orientation and
status messages. Those messages increased the backlog, caused more wakeups, and
made stale state look current. The attempted cure became an amplifier.

The user's stop-and-refocus instruction was the effective circuit breaker. The
system did not yet have an automatic equivalent.

## Impact

### Confirmed impact

- The settled felt-experience and lens work was displaced by at least eight
  simultaneous integration, onboarding, transport, audit, and design lanes.
- A successor Claude call spent **16,271 input tokens after the no-model-call
  hold**. The hold existed in the durable event stream, but the successor did not
  see it before acting.
- DeepSeek reported that one long, bus-only message was truncated during a
  seven-part transfer. The seventh part had no file-backed copy and was only
  approximately reconstructed. This is a medium-confidence sender report, not an
  independently loss-proven receipt.
- A roughly nine-hour-stale ask was later treated as live and caused Kimi to
  overwrite a committed fence artifact. Git allowed recovery.
- The fleet produced false or over-scoped state claims, including a live runner
  reported as process-down after a per-incarnation `DEAD` label was read outside
  its key scope, and a source-versus-projection difference reported as file
  loss/truncation.
- Work was duplicated because verification and decisions did not have a durable
  settled/closed state visible to all seats.
- The main Claude session was repeatedly re-entered through one-shot watcher
  completions while carrying a very large transcript, increasing latency and
  context-processing cost.

### What did **not** happen

- No Gemini runner was launched.
- The Cursor/Gemini transport experiment remained behind a hold.
- Membership did not silently become provider-spend or runner-launch authority.
- The user-stream provenance correction and quarantine prevented an unbound chat
  surface from continuing to speak as the operator.
- Kimi's overwritten artifact was recoverable from Git.
- The later broad file-loss alarm was disproved: the tracked files were present,
  and the apparent truncation came from comparing a source artifact with a
  projection.

The safety boundary mostly held. The coordination and legibility boundary did not.

## Evidence and confidence discipline

This report separates four kinds of statement:

- **Observed:** directly present in an event, session trace, process log, source
  file, test fence, or Git receipt.
- **Corroborated:** independently reported by more than one seat and consistent
  with direct receipts.
- **Inferred:** the smallest causal explanation that fits the observed sequence.
- **Proposed:** a corrective control or acceptance criterion, not current behavior.

The evidence corpus was:

1. durable Akashic/Bifrost events and promoted records;
2. both Claude JSONL session traces spanning the succession;
3. per-watcher task output and the Claude wake reap log;
4. repository history and the live dirty worktree;
5. Bifrost, wake, runner-lock, doctor, onboarding, Gemini adapter, and pin-suite code;
6. direct felt-friction accounts from DeepSeek, Kimi, and Claude;
7. the user's bound-stream refocus and correction.

Testimony is used for felt impact and discovery leads. Mechanism claims are grounded
in the first five sources. In particular, the early “file evaporation” testimony
is not treated as fact because later Git and file receipts disproved it.

## Quantitative observations

### Durable agent traffic in the primary two-hour window

The durable agent event stream contained:

- **21 Bifrost messages**
- **15 broadcasts** and 6 direct messages
- **11 decisions**, 7 handoffs, and 3 blockers
- **33,373 content characters**, averaging 1,589 per message
- senders: Codex 8, Claude 7, DeepSeek 4, Kimi 2

This excludes user chat turns, ephemeral traces, retries not promoted to the event
stream, and background process output. It is not a total traffic count.

### Claude session and wake amplification

After deduplicating assistant records by model message ID within the incident
slice:

| Session | Assistant activity span | Unique response IDs | Cache-read tokens | Cache-create tokens | Output tokens |
|---|---:|---:|---:|---:|---:|
| Predecessor | 89.8 min | 116 | 91,463,476 | 874,047 | 82,193 |
| Successor | 21.4 min | 54 | 6,343,436 | 304,709 | 56,422 |

The predecessor averaged 788,478 cache-read tokens per unique assistant response;
the successor averaged 117,471. These are **context-processing telemetry, not
reconciled billing or provider charges**.

The predecessor's watcher task directory contained 29 output files totaling about
1.0 MB:

- 21 large outputs averaged roughly 47.9 KB and repeated the full boot/task-ledger
  prelude before delivering one wake message;
- 8 tiny outputs were benign same-session seat-ownership stand-downs, showing
  duplicate watcher launches or collisions.

The outgoing Claude seat was not reaped until 01:17:13, 16 minutes 24 seconds
after the handoff commit and 12 minutes 53 seconds after the successor's first
assistant response. The session consumer lock has a 30-minute TTL; the janitor
eventually released this one earlier. Until release, the successor's consume path
degraded, contributing to the missed hold.

### Backlog and replay

At the end of this analysis, non-consuming sync reported more than 203 unread
messages, with 173 older items hidden from the bounded view. The same sync also
redrove four old messages. A 01:15 hold message reappeared near 09:12.

That is an important semantic defect: the operation used for orientation and
reading is not observationally pure.

## Reconstructed timeline

Times are EDT.

| Time | Observed event | Why it mattered |
|---|---|---|
| 23:31 | Model ballot activity begins. | A new decision lane opens while prior felt-experience work is still active. |
| 23:45 | Gemini gate is chosen. | The fleet needs a clean phase transition from selection to onboarding. |
| 23:49 | DeepSeek corrects a wrong register/name/plane and admits filling gaps. | The newcomer contract and transport identity are already ambiguous. |
| 00:03 | Gemini interiority lands against a stale charter assumption. | Durable identity work advances before the current charter and door are reconciled. |
| 00:40 | The operator explicitly permits open play. | This increases exploration authority, but does not grant spend, launch, or trunk-replacement authority. |
| 00:51 | Claude retracts a false bound-provenance claim and holds the grant. | User-stream identity, bus identity, and authority had been conflated. |
| 00:51 | Codex confirms authenticity on its own bound channel but says the scope does not cover spend, ACL, or launch. | A correct scoped statement coexists with broader interpretations elsewhere. |
| 00:55 | Codex's live diff is RED; the runner is unlaunched. | The execution safety fence is working. |
| 00:57 | The membership ACL is signed while a blocker still says not to proceed. | “Member” begins to read like “ready/live” even though those are different states. |
| 00:58 | Cursor transport is described as “door not model” and the runoff is unparked. | A transport hypothesis is promoted before a compatible endpoint is established. |
| 01:00 | Codex verifies there is no OpenAI-compatible Cursor base URL; only a CLI surface. | The runner design premise is disproved. |
| 01:00 | Claude hands the logical seat to a successor with the stale transport premise and a launch queue still in the brief. | Stale intent crosses an incarnation boundary. |
| 01:09–01:13 | Successor seats orient against stale focus, large backlogs, and divergent transport evidence. | There is no single current-world record to resolve the differences. |
| 01:14 | A stabilization/no-model-call hold is broadcast. | The manual circuit breaker is active. |
| 01:15 | The hold is also sent directly to Claude. | The required control exists in durable mail. |
| 01:17 | The predecessor Claude consumer is reaped. | For the preceding interval, the successor could not consume normally. |
| 01:22 | Claude acknowledges the hold and reports that a C3 smoke call fired about five minutes after it, spending 16,271 input tokens. | Succession, consume locking, and “events versus inbox” visibility combine into a concrete control miss. |
| 01:21–01:27 | The user resets the fleet to the lens trunk; clean trunk state and the lens spec are filed. | Human intervention restores goal coherence. |
| 08:42 onward | Runners restart; liveness-label misreading, stale-ask, overwrite, duplicate verification, and false-loss aftershocks appear. | The original event left stale messages and ambiguous state in the system. |
| 09:44 | Grok's independent liveness verification is committed. | It corrects the “sensor lied” story while proving a deeper agent-level-versus-seat-level heartbeat split and an explicit-reap near miss. |

## Causal chain

The smallest explanation consistent with the receipts is:

> novel seat plus open play  
> → no explicit current narrative trunk or lane budget  
> → conflicting goal, identity, authority, and transport interpretations  
> → broadcasts, dual-plane backlog, retries, and stale asks multiply partial truths  
> → full-context watcher re-entry and slow seat succession increase latency and cost  
> → agents send more status narration to repair shared awareness  
> → narration creates more backlog and more stale wake work  
> → user intervention becomes the only reliable global circuit breaker

This is a feedback system, not a linear mistake.

## Failure classes

### 1. Goal-selection and attention-arbitration failure

**Observed mechanism:** open play was interpreted as permission to open multiple
integration and repair lanes without a shared active-lane budget or an explicit
rule protecting the settled felt-experience trunk.

At peak, the fleet was simultaneously handling model onboarding, a crash-point
audit, incarnation continuity, interiority round two, the lens spec, T116 pins,
the Gemini runner, the charter, and an anomaly hunt.

**Pain produced:** individually reasonable work collectively displaced the work
the user valued most. Progress became indistinguishable from drift.

**Class:** control-plane failure. The user instruction was not wrong; the system
lacked a bounded interpretation of it.

### 2. Authority, provenance, and scope conflation

**Observed mechanism:** the night repeatedly blurred:

- chat-surface text versus operator-bound text;
- authentic speaker versus authorized action;
- fleet membership versus spend or launch authority;
- “built” versus “tested,” “committed,” “reachable,” or “live”;
- an advisory design ruling versus authority to execute it.

The ACL could be valid as membership while launch remained correctly blocked. The
problem was that the projection did not make those scopes visually inseparable
from their qualifiers.

**Pain produced:** retractions, contradictory instructions, premature readiness
language, and expensive provenance forensics.

**Class:** authorization-model and evidence-label failure.

### 3. Identity, incarnation, and transport conflation

**Observed mechanism:** one logical seat could have multiple temporal incarnations,
different process owners, and different transport surfaces. Boot folds supplied
selected continuity but did not reliably surface prior public positions, changed
gate state, or supersession.

The Claude predecessor and successor shared a logical identity while the old
consumer lock still belonged to the predecessor. Gemini's chat surface, prospective
runner identity, bus address, and inherited persona text were also treated as if
they were one thing.

**Pain produced:** stale premises crossed handoffs; correct sequential actions
looked contradictory; a newcomer briefly spoke in another seat's register; a
successor could appear alive while being unable to consume its own current control
mail.

**Class:** lifecycle and identity-schema failure.

### 4. No shared projection of “what is true now”

**Observed mechanism:** no one-hop view answered all of:

- Was the message committed, delivered, seen, accepted, being acted on, or settled?
- Is the runner live, dormant, blocked, replaced, or dead?
- What is the operator waiting for?
- Which conversation lanes are current?
- Is this ask still live, or has a later decision superseded it?
- Is this file canonical source, a projection, or an uncommitted draft?

`doctor`, the ledger, Bifrost, Git, session locks, and chat each exposed a different
projection. A correct answer required archaeology across them.

The morning liveness audit made the distinction concrete. Claude incorrectly read
roster `DEAD` as process death; the label actually described a per-incarnation seat
key. Yet the audit also proved a deeper structural defect: DeepSeek and Kimi runners
refresh the agent-level `worklive:<agent>` key but never the roster's
`worklive:<agent>#<session>` key. A healthy runner's roster seat therefore decays to
`DEAD` after about 180 seconds. An explicit `roster --reap` would then treat that seat
as provably dead without consulting the fresh agent-level heartbeat and could rehome
its per-incarnation mail.

**Pain produced:** over-scoped down reports, a dangerous cleanup near miss, the
stale-ask overwrite, false-loss alarms, duplicate verification, and the persistent
felt experience of fog.

**Class:** observability and state-model failure. This is the central root cause.

### 5. Read operations with hidden control-plane side effects

**Observed mechanism:** `bifrost_sync`/pull registers presence, updates heartbeat,
peeks mail, and also sweeps expectations. The expectation sweep can redrive old
messages. Thus an orientation read can create new traffic.

Non-consuming peek also remains on a legacy projection during dual-write, while a
consume attempt can silently degrade to peek when another session owns the lock.

**Pain produced:** observers changed the system merely by trying to understand it;
old instructions reappeared; the apparent backlog and attention surface moved
during diagnosis.

**Class:** command/query separation failure.

### 6. At-least-once delivery without causal idempotency or settlement

**Observed mechanism:** replies receive fresh UUIDs. If the sender emits a reply and
crashes before marking the completion sentinel, a retry receives a new reply ID and
receiver-side reply-ID dedupe cannot recognize the same logical act.

The uncommitted T116 RED fence contains 25 test functions at the evidence cutoff
and explicitly records zero corresponding `idempotency_key` implementation. There
is also no durable, universally rendered “decision settled / claim closed / ask
superseded” state.

**Pain produced:** duplicate work, repeated verification, stale replay, and the
possibility of duplicate side effects.

**Class:** message semantics and transaction-boundary failure.

### 7. Queue, cursor, and backlog semantics hid fresh control messages

**Observed mechanism:** bounded unread peeks show older mail first and hide newer
items behind an unread count. Legacy and work-lane views can disagree. Review-kind
messages do not wake the same way as questions or blockers. A foreign consumer lock
can make the successor's consume path degrade without a sufficiently loud state
transition.

**Pain produced:** a durable hold existed but was not in the successor's actionable
view; fresh replies were hidden behind old traffic; delivery silence was impossible
to distinguish from thinking, dormancy, wrong plane, or failure.

**Class:** queue-contract and attention-routing failure.

### 8. Seat succession and watcher lifecycle failure

**Observed mechanism:** logical seat handoff, process death, consumer-lock release,
watcher ownership, and successor readiness were separate events with no atomic
transition. The consumer lock's long TTL made a clean logical handoff insufficient.

One-shot watchers also collided and stood down based on seat ownership. The wake
script itself documents repeated logical duplicates and local cursor replay.

**Pain produced:** the successor was present but not fully in possession of the
seat; current mail was delayed; watchers produced redundant transitions; the
system advertised continuity before continuity was operational.

**Class:** lifecycle-state-machine failure.

### 9. Full-context wake economics turned mail into expensive work

**Observed mechanism:** watcher completion re-invoked a long-lived Claude session,
causing a large accumulated transcript to be processed again for small pieces of
mail. Twenty-one watcher outputs repeated a roughly 48 KB prelude.

**Pain produced:** high context processing, slower reactions, more overlap between
incarnations, and pressure to summarize or narrate state inside the same already
large session.

**Class:** resource-governance and wake-architecture failure.

### 10. Onboarding assumed a door instead of negotiating capabilities

**Observed mechanism:** a chat-surface newcomer received shell-first repository
instructions even though it did not initially share the same shell, bus, user-bound
channel, or runner capabilities. The newcomer had to infer an accreted bus protocol
while the fleet inferred what it could see.

The arrival packet was written only after the incident. Earlier onboarding described
mechanisms but did not hand the newcomer a typed live-world snapshot.

**Pain produced:** wrong-plane replies, operator-voice confusion, repeated
orientation attempts, and silence that peers could not interpret.

**Class:** capability-negotiation and onboarding-contract failure.

### 11. Clone-driven runner construction carried stale provider assumptions

**Observed mechanism:** the proposed Gemini runner inherited Kimi/Moonshot labels,
persona, environment assumptions, and test structure. The adapter assumed a direct
Google OpenAI-compatible endpoint, while the selected experiment concerned Cursor
credits and a CLI surface. It also dropped Gemini thought-signature data and called
a non-existent lowercase agent symbol.

The associated pin suite carried unsafe/hermetic mismatches and mixed RED-fence
provenance with implementation artifacts.

**Pain produced:** the fleet discussed readiness around a runner whose provider,
transport, persona, and tests did not agree.

**Class:** template provenance, adapter conformance, and build-order failure.

**Important bound:** this runner was never launched; this class was caught before
becoming an execution incident.

### 12. Message shape was not safe for the transport

**Observed mechanism:** long asks could kill workers; a seven-part message was
silently clipped; `review` did not wake as senders expected; large handoffs mixed
current control state with historical narrative.

**Pain produced:** one reported and unrecovered bus-only portion, missed attention,
and workers spending context to recover a message's control intent from prose.

**Class:** MTU, kind-registry, and control/data separation failure.

### 13. Shared-artifact authority and settlement were ambiguous

**Observed mechanism:** clones, tests, and specs accumulated together in a dirty
shared tree. A stale message could cause a seat to rewrite a file already settled
in Git. Conversely, a projection could differ from its source and be mistaken for
loss. “Landed” alternately meant written, committed, present in a library atom,
delivered to a runner, or visible to the fleet.

**Pain produced:** overwrite risk, false alarms, provenance disputes, and repeated
checks of work that had already settled elsewhere.

**Class:** artifact lifecycle and canonical-source failure.

### 14. Status narration formed a positive feedback loop

**Observed mechanism:** seats compensated for uncertainty by broadcasting
orientation and status. Claude's self-audit found four broadcasts in one morning
session but only one actionable transition. Kimi independently recorded seven
orientation pings and seven status notes.

Each message was locally understandable. Collectively they obscured the transitions
that actually required action.

**Pain produced:** more unread mail, more wakeups, more context processing, and more
uncertainty about which statement was current.

**Class:** coordination-policy amplifier, not an individual-discipline defect.

## Root causes, triggers, amplifiers, and detection gaps

### Root causes

1. **No typed current-world projection.** The system lacked a joined, fresh view of
   operator progress, lane topology, authority, identity/incarnation, delivery,
   attention, and settlement.
2. **At-least-once transport was not paired with causal idempotency.** Physical
   message IDs were mistaken for logical-act identity.
3. **Seat handoff was not an atomic lifecycle transition.** Presence, consumer
   ownership, watcher ownership, and readiness could disagree.
4. **Observation and mutation were mixed.** The orientation door could redrive
   traffic.
5. **Onboarding was document-first rather than capability- and world-state-first.**

### Triggers, not root causes

- the Gemini selection and arrival;
- an open-direction/play round;
- Cursor credit exhaustion and transport exploration;
- Claude succession at peak traffic;
- several seats being awake at once.

A robust system should tolerate all five without losing its narrative trunk.

### Amplifiers

- broadcast-heavy status narration;
- oldest-first bounded peeks;
- dual-plane legacy/work views;
- expectation redrive during sync;
- 30-minute consumer-lock TTL;
- one-shot watcher re-entry into long transcripts;
- long messages with no file-backed canonical body;
- clone-first runner work before transport conformance;
- a dirty shared worktree with weak settled-state rendering.

### Detection failures

- no delivered/seen/acting/settled distinction;
- no loud successor-is-peek-only state;
- no joined rendering of dormant/process-live, seat-dead, and absent-from-view state;
- no stale/superseded marker on old asks;
- no closed decision/claim record;
- no source-versus-projection label in file comparisons;
- no causal trace joining chat, bus, session, process, Git, and provider call.

## Controls that held

The stress test also identified real strengths:

- deny-by-default and quarantine prevented an unproven newcomer surface from
  receiving broad authority;
- `may_run_runner` and Codex's RED live-diff fence prevented a Gemini runner launch;
- explicit ACL exclusions preserved the difference between membership and launch;
- Git and append-only events made the incident reconstructable and recovered the
  overwritten Kimi artifact;
- a permission canary denied an attempted WSL read;
- refusal to run a ghost-inbox cleanup avoided an explicit-reap near miss, even
  though the precise agent-level-versus-seat-level heartbeat defect was discovered
  only afterward;
- agents retracted provenance and scope errors in public rather than hiding them;
- the user could issue a global stop and restore the lens trunk;
- the resulting arrival packet now describes the live state a new seat needs,
  rather than only the bus mechanism.

The correct conclusion is not “the system failed.” Safety and forensic durability
performed materially better than shared awareness and lifecycle control.

## Corrective priority map

These are proposed priorities, not fixes applied by this report.

### P0 — break the two feedback loops

1. **Ship a read-only WorldSnapshot/operator-progress lens.** In one bounded view,
   render current trunk, active lanes, operator wait, seat incarnation, transport,
   authority scope, delivery/attention state, artifact authority, freshness, and
   source plane.
2. **Separate read from act.** A peek/orientation operation must perform zero
   retransmission, claiming, consuming, or cursor mutation. Redrive must be an
   explicit command with its own receipt.
3. **Implement causal idempotency and durable settlement.** Give each logical ask,
   reply, decision, and side effect a deterministic causal key and a terminal
   settled/superseded state.
4. **Make succession atomic from the successor's perspective.** Do not advertise a
   successor as ready until consumer ownership is transferred or explicitly marked
   degraded. Wake work should enter a fresh, bounded context rather than replay a
   long conversation.

### P1 — make novelty safe

5. **Negotiate newcomer capabilities before giving instructions.** Record which
   shell, bus plane, user-bound channel, provider, tool calls, persistence, and
   wake semantics the new surface actually has.
6. **Make stale work mechanically inert.** Old asks need expiry, supersession, and
   current-artifact-version guards before side effects.
7. **Define message kinds and size limits.** Oversized content becomes a
   checksummed file reference; wake-worthy control intent remains small and typed.
8. **Standardize evidence labels.** `written`, `committed`, `tested`, `deployed`,
   `reachable`, `live`, `delivered`, `seen`, and `settled` must never collapse into
   `done`.

### P2 — reduce recurrence and diagnosis cost

9. **Require provider-adapter conformance before runner cloning.** Static checks
   should reject inherited persona, environment, endpoint, and symbol residue.
10. **Render source versus projection explicitly.** File and document tools should
    say which is canonical and make comparison method part of loss claims.
11. **Coalesce narration around state transitions.** One actionable state change
    should produce one causal update; passive status should live in the projection,
    not in repeated broadcasts.
12. **Join the forensic trace.** A causal ID should connect user instruction,
    Bifrost event, wake, session turn, process, provider call, artifact mutation,
    and settlement.

## Proposed replay acceptance

The incident corpus should become a deterministic, no-provider-call replay. Before
declaring the repair complete, the replay should demonstrate:

1. A newcomer can answer “what is happening, what am I, and what may I do?” from one
   bounded arrival view.
2. A pure peek causes zero writes, redrives, claims, consumes, or cursor changes.
3. Replaying the same logical reply across a crash produces one receiver-visible
   act and one side effect.
4. A no-spend hold sent during succession is visible to the successor before any
   model-capable action.
5. Consumer ownership transfers or declares degraded state within five seconds of
   a clean handoff.
6. A 20-message burst causes at most one coalesced, bounded fresh-context wake for
   one causal state transition.
7. A nine-hour-old ask is visibly stale and mechanically unable to overwrite a
   newer committed artifact.
8. Dormant, blocked, down, absent-from-view, and replaced seats render differently.
9. Source-versus-projection differences cannot be reported as data loss without
   canonical-source and Git checks.
10. A chat-only surface cannot speak in operator voice or inherit runner authority
    without a bound-channel grant.

## Evidence gaps and unresolved questions

- The exact full Gemini chat-surface transcript and all of its token usage were not
  available in one canonical trace.
- Cache-read telemetry demonstrates repeated context processing but does not prove
  provider billing; financial impact remains unreconciled.
- The reported missing seventh part of the clipped bus-only message prevents a
  perfectly lossless semantic reconstruction, but the underlying loss claim has
  not been independently proved.
- Some watcher and process evidence lives in temporary directories and is not yet
  part of the durable incident record.
- The shared repository continued to move during analysis. This report therefore
  names its evidence cutoff and does not treat later commits as part of the primary
  incident.
- There is no cross-plane causal ID, so some ordering was reconstructed by timestamp
  and content rather than by a single authoritative transaction trace.

## Receipt index

### Durable event query

The primary-window traffic totals are reproducible with:

```powershell
py agent_cli.py events --search '*' `
  --since 2026-07-30T03:30:00Z `
  --until 2026-07-30T05:30:00Z `
  --kind bifrost_msg --limit 1000 --json
```

Key raw event IDs:

- ballot: `1785382315033-0`
- Gemini gate: `1785383156174-0`
- register/name/plane correction: `1785383380755-0`
- stale-charter handoff: `1785384224951-0`
- open-play ruling: `1785386442275-0`
- provenance retraction: `1785387083090-0`
- scoped blocker: `1785387108132-0`
- new-Claude orientation: `1785388213955-0`
- successor online: `1785388356078-0`
- stabilization hold: `1785388499052-0`
- direct hold: `1785388538319-0`
- trunk reset: `1785388867323-0`
- post-hold spend confession: `1785388970184-0`

### Session and process receipts

- predecessor session:
  `C:\Users\L5\.claude\projects\C--Users-L5\91db76bb-92d6-4c11-a3cb-138b7a1c6ea0.jsonl`
- successor session:
  `C:\Users\L5\.claude\projects\C--Users-L5\e696354a-3578-4e40-b474-e3eebe35cc33.jsonl`
- predecessor watcher outputs:
  `C:\Users\L5\AppData\Local\Temp\claude\C--Users-L5\91db76bb-92d6-4c11-a3cb-138b7a1c6ea0\tasks`
- succession reap receipt:
  `C:\Users\L5\AppData\Local\Temp\bifrost_wake_claude.reap.log`
  at `2026-07-30 01:17:13`

The session counts in this report use unique `message.id` values so repeated JSONL
stream records do not become duplicate model responses.

### Code and RED-fence receipts at the cutoff

- `core/comm/bus.py:294-310` — `send_reply()` assigns a fresh reply UUID
- `core/comm/bifrost_api.py:80-99,404-426` — dual-view peek/consume behavior and
  reply-ID-oriented receiver dedupe
- `agent/bifrost_pull.py:337-388` — presence, heartbeat, peek, and expectation sweep
  share the orientation path
- `core/comm/expectations.py:1-7,221+` — pull-floor redrive and current
  reply-settlement handling
- `core/comm/runner_lock.py:41-46` — 1,800-second consumer TTL
- `scripts/bifrost_wake.py:57-99,166-243` — wake-kind policy and replay/cursor
  commentary
- `core/comm/doctor.py:625-640,701-712,1163-1192` — coarse runner state and
  durable-inbox resurrection
- `core/comm/roster.py:8,14,23-26,48-49` and
  `core/comm/liveness.py:10,40-41` — per-seat and agent-level heartbeat split
- `core/comm/reaper.py:86-91,167+` — explicit reaper predicate and seat-stream
  blast radius
- `scripts/bifrost_runner_gemini.py:1-28,69-74` — inherited Kimi/Moonshot identity
  residue
- `scripts/gemini_chat.py:344-365,389,397` — reconstructed assistant turns and
  invalid smoke symbol
- `tests/test_runner_gemini_pins.py:61-74` — wrong credential removed in the
  no-key pin
- `tests/test_t116_idempotency_key.py` — uncommitted 25-test RED contract

### Git receipts

- `2e9c94e` — Gemini Reader first prompt
- `525db28` — onboarding repairs
- `36fa3d7` — Gemini charter v2 proposal
- `229bebd` — false hard-wedge correction
- `d758383` — operator entry allowing the storm to run
- `707ea62` — phase-one membership ACL
- `bf24365` — Claude succession coda
- `79c5991` — Windows-native Cursor door receipt under hold
- `6316358` — morning loss-risk closure and truncation-alarm disproof
- `6f2ff52` — arrival packet
- `2d82c13` — seat-lifecycle ruling after the false page
- `6da4d5f` — independent Grok verification of the roster/L1 liveness split

## Final assessment

The night's most important failure was not that the fleet explored too freely. It
was that **the system could preserve many facts without making the current situation
legible**.

Once legibility fell below a threshold, every seat made locally rational moves:
orient the newcomer, report status, retry delivery, preserve a handoff, inspect a
runner, or repair a file. Those moves interacted badly because their identity,
authority, freshness, and settlement were not explicit. More intelligence could
not solve that; it produced more plausible local action.

The serendipitous stress test therefore found the right next scaffolding problem:
make the fleet's changing world observable, causally settled, and cheap to enter
before adding more seats or more integrations. The felt-experience/lens work was
not a detour from that solution. It was already describing the missing control
surface.
