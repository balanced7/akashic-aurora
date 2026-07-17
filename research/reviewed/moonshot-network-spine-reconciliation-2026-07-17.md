# T060 Moonshot + Network Spine — Three-Frontier Reconciliation

Status: **RECONCILED FOR N0 SHADOW OBSERVATION ONLY** (2026-07-17). T047
cutover, routing enforcement, hard-interrupt expansion, daemon supervision, and
autonomous work allocation remain gated.

Coordinator: `codex_root`
Panel: Fable/Claude · DeepSeek Review · Sol/Codex
Method: three blind/read-separated halves, disclosed M1-CC counters, RED/BLUE/Jester
adversarial fold-in, live MCP/control dogfood, M1-PV citation pass.

## 0. Verification header and integrity variance

The M1-PV pass is at
`research/reviewed/moonshot-network-spine-m1pv-2026-07-17.md`.
Against the current artifacts it found:

- 0 section invalidations;
- 1 reclassification: the native MCP `note`/`notes` Namespace-default defect was
  true when Sol observed it and is now fixed by commit `8b09aae`;
- 3 harmless line drifts with live symbols and claims intact.

**Procedural variance, disclosed:** the citation pass completed before this
reconciliation was written, but after the coordinator had read the conclusions to
run the live cross-critique. That does not meet M1-PV's strongest “evidence before
conclusions” ordering. The pass still verifies the evidence, but this record does not
pretend the ordering was perfect.

### The blind-half version split

One untracked DeepSeek blind-half path was overwritten between readers. The original
v0 (~24KB, title `ADVERSARIAL RUNNER LENS`) is no longer recoverable; current v1
(18,005 bytes, title `BLIND HALF`) has an unknown writer. The corrected durable
timeline is:

| Cross writer | DeepSeek version actually critiqued | Durable evidence |
|---|---|---|
| Sol/Codex | v0: T047-first, rollback pin, interactive MCP migration, R1–R4 | Sol cross §1B attacks v0-only rollback text |
| Fable/Claude | v1: daemon-as-consumer + health verdict | Fable cross §1A/§1B attacks v1-only supervision text |
| DeepSeek Review | v1 | DeepSeek cross names v1 S1 as “my half” |

The full incident report and appended correction are at
`research/reviewed/moonshot-network-spine-deepseek-version-race-2026-07-17.md`.
The split means there were effectively **four** proposals, not one clean three-half
fence. It does not authorize a destructive build. It does improve N0: v0 contributed
the interactive-consumer and rollback attacks; v1 contributed the health/supervision
separation; both are disposed below.

Current read hashes, frozen into this reconciliation so another silent overwrite is
detectable:

| Artifact | SHA-256 |
|---|---|
| Fable blind | `a4f13394f8753d5b9ae93039d74071116db6171e1c513e495e3ec54e24fad653` |
| DeepSeek v1 blind | `458dcf1d1858e2b333d700ccbf883176897fb9c503709d6cde76abb36afd1fc1` |
| Sol blind | `258f14cface8ce63890546d6eb10b889d04ea6a9c076387f1629e867e73c3236` |
| Fable cross | `efb01840409a26d1ad55360ef0d19d3b09d5811fc3292e879358c3ca62e92928` |
| DeepSeek cross | `51b18fce393a35c79cbe2a4b07c2ee873ca91ef3f36fcad813c88bcdc42e5fa0` |
| Sol cross | `ff79a0293145328f47ebf2f64b0f559681029c84b651f1a4214aadec45031b83` |

From now on, a blind artifact is not cross-readable until its writer supplies a
versioned path plus content hash. Advisory locks prevent simultaneous edits; an
immediate exact-path mirror makes the version durable.

## 1. The reconciled ruling

The panel converges on the destination:

```text
N0 shadow truth → T047 governed legacy retirement → intent/route enforcement
                → T046 latches → T038 work-token build → M1/M6/M7 expansion
```

The first safe implementation is **N0 — Shadow Delivery Truth + Route Explain**.
It measures the substrate that exists and exposes a queryable decision; it does not
change a packet's destination, wake behavior, priority, deadline, consumer, or owner.

Why N0 wins:

1. Sol and Fable independently rule that `meta.wake` is a scheduling change, so the
   reopened design's “zero-risk Phase 0” label is false unless enforcement is removed.
2. DeepSeek still prefers T047, but its final counter requires a 48-hour lane-vs-
   legacy shadow window first. That observation window is N0 even if it is named a
   T047 precondition.
3. DeepSeek v0's rollback pin is impossible as written: turning dual-write back on
   changes future writes; it cannot retroactively recreate legacy copies omitted
   while off.
4. The version split and native-door asymmetries make a destructive cutover while
   Daniel sleeps an unjustified authority expansion. Daniel's “continue as far as
   possible” directive safely authorizes reversible observation, not mail-loss risk.

The strongest disconfirmation is real: T047, not N0, is the structural gate on M1's
lane-native consumer and on trustworthy M7 trace projection. Therefore N0 is bounded:
one implementation slice, one live three-seat drill, one 48-hour soak. It must then
produce the T047 gate evidence or be removed; it cannot become a permanent parallel
router.

## 2. Divergence triage

### D1 — First slice

- Fable blind: additive seven verbs + T047; cross: **amends to Sol shadow first**.
- Sol blind/cross: shadow composer/decision first.
- DeepSeek v0: T047 first; cross: T047 only after a 48-hour shadow comparison.
- DeepSeek v1: daemon/health first.

**RULING:** N0 shadow observation first. A read-only fleet-health verdict is a separate
O0 candidate; daemon-managed child processes are excluded and remain owned by T086.

### D2 — Intent verbs

Seven intents are the target roster: ASK, TELL, HAND, REVIEW, STREAM, SIGNAL, REPLY.
REPLY is mandatory and wraps `Bus.send_reply()`; this is unanimous. But sending via a
new intent surface is deferred because:

- the MCP door has no authenticated actor binding and accepts caller-supplied
  `from_agent` strings;
- the interactive MCP, runner reply, and ToolBox send surfaces differ;
- a flag-day migration would recreate a two-class fleet.

N0 exposes read-only route explanation and statistics. Intent send wrappers enter a
later strangler only after the actor and surface contracts are named.

### D3 — T047 rollback and interactive consumers

T047 remains required, but its rollback claim becomes precise:

- `BIFROST_LANES_DUAL_WRITE=1` restores **future** dual writes;
- trimmed or never-written legacy history is not restored unless an explicit,
  idempotent replay tool is designed and audited;
- interactive MCP mail must move from legacy peek to a lane-native read contract
  before legacy freezes.

A simple “latest 50, no advance” peek is insufficient for a newborn seat. Registration
must choose an audited cursor epoch: bounded replay, or start-now for ephemeral mail
while boot separately surfaces durable promoted handoffs/decisions.

### D4 — Per-agent trace

Per-agent trace is **partitioned retention inside the existing `trace` family**, not a
new lane. Discovery comes from the governed roster/presence, never unbounded Redis
SCAN. Deletion ritual: tombstone seat → stop writes → retain for a bounded diagnostic
window → delete its partition → durable deletion receipt. This precedes using trace as
M7's cognition feed.

### D5 — M1 supervision and health

The read-only one-line fleet verdict is valuable and may be fenced as O0. Process
supervision is not part of T060. C4-2 already records a cleanup/supervision failure
that killed load-bearing work, and T086 owns the lifecycle reconciliation. T060 may
consume that contract; it may not invent a second supervisor.

### D6 — M6 authority

The current T038 hand pilot continues now: OFFER → ACCEPT → HELD with progress →
RELEASED, one durable note per transition. A later allocator may use cost/capability
evidence to **propose** ownership; it may not silently retarget transport. T038 build
still follows T046 and must retain its CAS/generation fence. Auto-claim is additionally
gated on the C9 ground-truth layer so a poisoned high-precedence note cannot actuate a
fleet-wide work split.

### D7 — M7 projection

M7 reuses T054 flow tracing and event/trace projection. Dashboard observers never
consume work mail. An interactive agent reading its own addressed mail is a mail
consumer, not a dashboard observer, and may use its governed work-lane read path.

## 3. U1–U5 final disposition

| Item | Final ruling | Slice |
|---|---|---|
| U1 missing REPLY | **ADOPT, blocking for any intent-send surface.** REPLY wraps `send_reply`; preserve reply_id, lane-first retry/fallback, dedup, and expectation settlement. | Intent strangler after N0 |
| U2 wrap, do not replace | **ADOPT.** Name runner reply, ToolBox send, interactive MCP/CLI, and infrastructure callers. No raw-send retirement in N0. | Four-phase strangler |
| U3 queryable route | **ADOPT now.** Pure dry-run route is N0's operator/MCP seam. | N0 |
| U4 per-rule counters | **ADOPT now, bounded.** Static kind/rule fields plus collapsed `_unknown`; no agent/content/flow labels. Counters are evidence, not success. | N0 |
| U5a mid-turn blind spot | **Out of router.** Runner round-boundary injection / T058-T083 seam. | Fidelity/lifecycle |
| U5b ghost reply | **Split.** Linkage stays in REPLY; liveness belongs to supervision/lease evidence. | Intent + T086 |
| U5c cost-ignorant router | **Reframe.** Cost/capability informs a governed T038 ownership proposal, never covert transport authority. | T038 after gates |

## 4. Control-fidelity contract learned from Codex + Jester

OpenAI's current Codex manual makes the essential product distinction simple:
**Steer** appends input to the current run; **Queue** waits for the next run. The
app-server lifecycle separately describes `turn/steer` and `turn/interrupt`.
Aurora should preserve that understandable model and add distributed receipts, not
replace it with protocol jargon.

Source: <https://learn.chatgpt.com/docs/prompting.md>

### Required semantics

| Mode | Scheduling contract | Required receipt |
|---|---|---|
| `inform` / queue | Next turn; never displace current work | delivered/pending or expired |
| `steer` | Same active task at next safe tool-round boundary; no restart | adopted/deferred/conflict + task/span + apply time |
| `interrupt` | Finish current tool call, checkpoint, suspend, service, then restore/replan/abort | checkpoint id + disposition + resume_of |
| `halt` / barrier | Stop dispatch/consume at safe boundaries until governed release | per-target barrier ACK |

Every signal gets a server-derived `signal_id`, bound actor, target, mode, task/span,
sent/expiry times, expected action, required capability, and supersession link. The
receiver records received/applied times and disposition. The same signal applies at
most once even if a carrier and Redis queue/flag both arrive.

### Seat-class result from the live dogfood

- DeepSeek Review (runner seat) adopted steer `1784270053028-0` inside T060 without a
  task restart; its cross records plan/tool history preserved and no observed duplicate.
- Fable/Claude (session seat) did **not** receive steer `1784270039666-0` in the active
  cross. It sat unconsumed in `bifrost:steer:claude` because session seats have no
  `steer_drain` loop. The miss was found only by direct inspection after filing.
  Failure C1-7 and lesson `session_seat_no_steer_drain` now preserve the receipt.

Therefore `steer` is not one transport. The control door must resolve the target's
seat class/capability and choose a path that can produce a receipt. A registered seat
that cannot drain current-turn steers must refuse/downgrade loudly or receive a
harness-level current-turn injection; silent queueing is forbidden.

### Security ruling from RED/BLUE/Jester

Fidelity governs **when**, not **truth**. An urgent payload never outranks the task
ledger or mechanical evidence. The Jester has no nudge, steer, halt, blocker, or
decision authority. Current native MCP nudge is not ready for expansion because its
caller supplies `from_agent` and the wrapper writes the flag/queue without a bound
transport identity or capability check.

Required defense is two-sided:

1. send door binds the actual actor and checks `bus.steer` / `bus.nudge`;
2. receiver checks the server-derived grant again before apply;
3. spoofed or uncapped control traffic is recorded and refused;
4. a task-status claim inside a steer is rendered against the live ledger, not treated
   as ground truth because it arrived at high fidelity.

Hard interrupt remains unavailable for active work until C1-3's
checkpoint/suspend/restore pin passes. It is not the default nudge mode.

## 5. N0 build specification — Shadow Delivery Truth + Route Explain

### Purpose

Measure whether the current lane mirror is trustworthy enough to retire legacy, and
let any operator/MCP seat ask what the static router would do, without changing live
delivery.

### Included behavior

1. `core/comm/router.py` defines a pure `RoutingDecision` and `route(kind)` over the
   existing `packet_spec.lane_for()` table. Fields are bounded and inspectable:
   `kind`, `lane`, `known`, `rule_id`, `policy_version`, `mode="shadow"`.
2. The send door records one logical route-decision count and the existing lane-write
   path records physical mirror outcomes: success, failure, unmapped, or disabled.
   REPLY records its existing lane-primary success/fallback separately.
3. Metrics live in one bounded Redis hash per namespace. Known kind names come only
   from `KIND_LANE`; all unknown strings collapse to `_unknown`. Metrics are
   fail-silent and can never fail a send.
4. CLI `packet-trace` and native MCP `packet_route` expose the same dry-run result;
   `packet-stats` / `packet_route_stats` expose the bounded counters.
5. Existing loud diagnostics remain. A total Redis outage cannot persist a failure
   counter, so stderr plus the existing outage health signal remain the evidence for
   that class; N0 does not claim otherwise.

### Explicit exclusions

- no intent send wrappers;
- no `meta.wake` honoring or wake-policy change;
- no lane selection by the new router;
- no priority, deadline, ECN/AIMD, target/model/cost selection, refusal, or reordering;
- no raw-send deprecation;
- no legacy read/write removal, cursor migration, interactive lane peek, trace
  repartition, latch, daemon, or UI code;
- no content-based routing and no model on the hot path;
- no unbounded per-agent, payload, or flow-id metric labels.

### Pre-registered pins (must be RED before implementation where applicable)

1. `test_route_matches_lane_for_every_live_kind`
2. `test_unknown_kind_is_shadow_unmapped_not_refused`
3. `test_lane_failure_preserves_legacy_delivery_and_counts_failure`
4. `test_route_and_outcome_cardinality_is_static`
5. `test_reply_lane_first_dedup_and_expectation_semantics_unchanged`
6. `test_cli_and_mcp_route_json_are_identical`
7. `test_shadow_metrics_failure_never_fails_send`
8. `test_shadow_observation_adds_under_5ms_p50_on_local_redis`

### Kill drill K0 — mirror failure stays observational

Inject an xadd failure only on the lane mirror while legacy remains live. The recipient
must receive exactly one logical message via current semantics; route explanation must
remain unchanged; failure diagnostics/counter must identify the static rule; no wake,
cursor, priority, deadline, or ownership state may change. Any delivery difference or
unbounded metric field kills N0.

### Live panel drill L0

After a fresh MCP-server restart loads the tools, Fable, DeepSeek Review, and Sol each
query one distinct decision (HAND-equivalent kind, REPLY, and STREAM/trace). They send
using existing doors only. One REPLY settles its expectation. Route stats name the
three static rules; the cockpit input is the observation record, never agent-authored
UI state.

### T047 promotion gate

N0 may propose T047 only when all are true:

- at least 48 continuous hours of dual-write observation;
- lane-copy success ratio > 0.999 overall **and by load-bearing work/reply kind**;
- zero unexplained unmapped kinds;
- 100% of the bounded three-seat directed handoff/reply drill arrives and settles;
- interactive MCP lane-native read + audited cursor epoch has passing pins;
- T066 lane-only reply/failure/redrive drill passes;
- rollback text states future-only restoration or includes a tested replay ritual;
- per-agent trace retention is ready before M7 treats trace as cognition history.

The ratio is evidence, not proof. Any mismatch stops the cutover and becomes the
deliverable.

## 6. MCP status after live dogfood

| Surface | Observed status |
|---|---|
| Core native coordination | Working: boot, status, presence, task list/claim, recall-at, locks, send, nudge, sync, promoted, events |
| MCP Namespace defaults | Fixed in commit `8b09aae`; parity pin 2/2 green. The already-running server must restart to load it. |
| MCP boot single-frame | Working in the attached seat; uncommitted C7-4 stdin isolation + real cold/warm test are 3/3 green, but ownership/commit is still outstanding. |
| MCP `log` single-frame | Root cause repaired in the M1-LITE slice; peer verdict SHIP; real stdio + related regression set green. Running server must restart after mirror. |
| Native actor binding | Not present for `from_agent` control calls; security gate remains open. |

Answer to “is MCP working?”: **yes for the core collaboration path, not yet parity-
complete in the currently running process**. Restart is required to load the two fixed
wrapper/log paths; actor-bound control fidelity remains design work.

## 7. Experiment data

| Receipt | Result | Design consequence |
|---|---|---|
| Virgin `codex_root` cursor | 10,009 historical packets before current replies | Newborn cursor epoch/freshness is a first-class contract |
| Runner soft steer | Adopted in current task, history preserved | Runner path viable; add signal id/disposition |
| Session soft steer | Applied 0×, no receipt, found after filing | Seat-class routing + loud downgrade required |
| Blind-half overwrite | Two versions at one path; v0 unrecoverable | Versioned filenames, hashes, locks, immediate mirror |
| Cross-critique yield | Wake-semantic overclaim, impossible rollback, MCP spoof, C9/M6 gate, supervision boundary | The panel changed the first slice materially |
| Native `note`/`notes` | Failed live, newcomer isolated root cause, peer fixed whole Namespace-default class | Door dogfood should be an acceptance gate |
| Native `log` | Attached call hung; fresh stdio reproduced; stack found eager NumPy import | Default log path now lazy/lightweight |

Cadence verdict: **AMEND and adopt** WORK → CHECKPOINT → SYNC → RULE → RESUME,
with a freshness seed before WORK, a version/hash in every CHECKPOINT, and a receipt
or loud downgrade for every steer. Hard interrupts wait for durable checkpoints.

## 8. Morning decisions for Daniel

1. **T047:** approve the gate definition above, not an immediate cutover. N0 begins the
   48-hour clock; the cutover returns for an explicit decision with receipts.
2. **Control identity:** choose the actor-binding home for native MCP (session-bound
   server identity/capability token is recommended; checking a caller-supplied name is
   insufficient).
3. **Fidelity UX:** approve `inform/queue`, `steer`, `interrupt`, `halt` semantics and
   make hard interrupt explicit rather than the default.
4. **M1:** approve read-only fleet verdict as its own O0 fence; keep process supervision
   under T086.
5. **M6:** keep the T038 hand pilot running; gate auto-claim on T046/CAS and C9
   ground-truth integrity.
6. **M7:** approve per-agent trace as partitioned retention in one trace family, with
   the deletion ritual above.
7. **MCP restart:** restart/reload the Aurora MCP server after the boot/log repairs are
   durably mirrored, then run the native one-frame parity suite from all three seats.

## 9. Immediate execution order

1. Mirror the verified MCP-log repair; finish ownership of the already-green C7-4
   boot repair.
2. Commit N0 failing pins before implementation.
3. Build N0 only, run K0, and obtain a peer countercheck.
4. Run L0 with the three frontier seats and start the 48-hour observation window.
5. Continue design/pilot/projection work, but stop before T047 or any high-fidelity
   control expansion until the named gates are satisfied.

