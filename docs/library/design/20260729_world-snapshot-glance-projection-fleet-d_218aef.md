---
akashic_id: art_20260729_world-snapshot-glance-projection-fleet-d_218aef
akashic_sha: 8c47282be9ae
schema_version: 1
status: draft
type: design
arc: T060
date: 2026-07-29
title: world-snapshot-glance-projection-fleet-direction-reconciliation
gist: "Two-lane plan: repair Aurora's truth floor while building a read-only WorldSnapshot and first SUBJECT/ATTENTION projection."
visibility: fleet
body_type: markdown
seats: [codex_root_019fab2d, claude, deepseek, kimi]
category: [coordination, memory, bus]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260729_reusable-bifrost-wake-substrate-fleet-re_164a4b
    rel: discusses
  - target: art_20260728_vr-build-order-codex-root-2026-07-28_99811d
    rel: discusses
  - target: art_20260728_truth-ground-codex-root-2026-07-28_783345
    rel: discusses
created: "2026-07-29T21:32:29"
updated: "2026-07-29T21:32:29"
---
<!-- GENERATED PROJECTION of art_20260729_world-snapshot-glance-projection-fleet-d_218aef -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# world-snapshot-glance-projection-fleet-direction-reconciliation

# World Snapshot + Glance Projection — Fleet Direction Reconciliation

- **Status:** fleet-direction draft; source positions reconciled; awaits a fresh
  adversarial fence and Daniil's build gate
- **Date:** 2026-07-29
- **Participants:** Daniil, Codex, Claude, DeepSeek, Kimi
- **Implementation status:** design only; no new snapshot, projection, UI, or
  wake behavior exists because of this document
- **Primary input:** `research/in-flight/glance-layer-thread-2026-07-29.md`

## Decision in one page

The next organ is not another dashboard. It is a **read-only, rebuildable
WorldSnapshot with multiple cheap GlanceProjections**.

The system should assemble the shape of the world outside the model. A seat
should first see a bounded menu of views, choose where to move attention, and
only spend model context when it deliberately drills into evidence. The same
versioned data contract should serve CLI, MCP, UI, desktop seats, API runners,
and future models. Renderings may differ; identity, evidence, and epistemic
meaning may not.

Work proceeds in two parallel lanes:

1. **Lane A — restore the truth floor.** Resolve T123 boundary debt, reproduce
   and classify the current full-gate delta, fix forward rather than
   allowlisting, and reconcile stale ledger state.
2. **Lane B — build the read-only perception contract.** Specify and replay a
   WorldSnapshot + GlanceProjection against tonight's real failures. This lane
   has no action, mutation, settlement, or wake authority.

They meet at a **merge gate** before any actionable lens, UI control, boot
replacement, or wake implementation. A read-only view may honestly render
missing identity as `UNKNOWN`; an actionable view may not operate over an
unrepaired truth floor or unresolved logical identity.

The first vertical is **SUBJECT / ATTENTION**, not Presence or Vitals. Existing
`flightdeck` and `bifrost_dashboard` already cover those axes shallowly.
Tonight's missing capability was cross-organ: for one subject, show the ledger,
mail, canonical and loose artifacts, tests, changes, risks, wake-worthiness,
and what still needs this seat.

The first subject fixture is `wake-substrate`.

## Why this organ exists

Daniil identified the root problem:

> I want you all to have a richer and more ergonomic way for interacting with
> things. I want to fight against all this chaos and noise and ritual you have
> to do in order to get anything done.

The fleet's diagnosis is an **interaction tax**. Each seat is repeatedly forced
to be its own parser, historian, dispatcher, source reconciler, auditor, and
renderer before it can reason about the work. Raw organs exist, but their
output arrives as prose walls, different doors expose different subsets, and
the cost of assembling a glance is paid inside the model's context.

The design objective is therefore not "more summary." A summary assumes
someone has already decided what matters. The objective is **vision for
choosing**:

```text
meta-glance -> choose a projection -> cheap structured glance
            -> choose an object     -> raw evidence or a safe action
```

Normal state compresses. Anomalies, contradictions, unsupported queries, and
`UNKNOWN` expand.

## Ground corrections that govern the plan

The direction round caught three task-mapping errors before they became build
dependencies.

| Item | Verified live state | Consequence |
|---|---|---|
| **T123** | `approved`, unowned boundary debt: the `method_drift.py` inverted dependency and duplicate `roster.py` basename | T123 is not the wake substrate. It belongs in Lane A. |
| **T121** | `done`; ledger receipt records combined 16/16 verification for the EpistemicView contract and first bus renderer | Typed epistemic status is an existing primitive. Consume it; do not schedule it again. |
| **T116** | `claimed` by Claude; packet `idempotency_key` and idempotent settlement are not yet implemented | T116 gates identity-dependent query classes and safe actions, not every read-only truth query. |

Wake work lives primarily under **T095 M2**, with T108, T060, T073, and T078
supplying adjacent architecture and capability ground. The accepted wake design
still requires Daniil's explicit S0 gate. The broad delegation to collectively
choose direction is not silently converted into that exact gate.

Other existing surfaces should be reused:

- T081's `bifrost_dashboard` is done.
- `core/comm/doctor.py::flightdeck()` already composes doctor, pulse,
  lane-health, locks, and commits.
- `core/primitives/epistemic.py::EpistemicView` already represents authority,
  claim kind, currency, identity state, and risk as independent axes with
  evidence and `UNKNOWN` defaults.
- `core/perspectives/Lens` already has a precise narrative-ranker meaning:
  `Map × Lens` over the narrative substrate.

Therefore **lens remains the human word**, but the new machine contracts are
named `WorldSnapshot` and `GlanceProjection`. Reusing `Lens` internally without
a deliberate migration would create a names-that-lie defect.

## Authority model

`WorldSnapshot` is a CQRS-style read model, not a new source of truth.

The foundation remains:

- Store: what is the current value?
- Ledger: what happened, in order?

The snapshot joins authorities and projections, records where every claim came
from, and can be rebuilt. It must never settle a task, consume mail, mutate a
cursor, bless a projection, or convert a seat's inner report into computed
truth.

Every surfaced object carries:

- a stable object reference when one is mechanically available;
- source and plane (`work`, `legacy`, `bench`, ledger, atom store, Git, test
  receipt, or another named source);
- `checked_at` and source cursor/version where meaningful;
- the complete five-axis `EpistemicView`;
- a drill pointer to raw evidence;
- an attention state;
- query capability information for any answer that depends on missing
  substrate.

Computed and curated material may coexist, but remain visibly distinct:

- **GENERATED**: deterministic projection of named evidence;
- **CURATED / INNER-REPORT**: a seat's interpretation or felt sense;
- **INFERRED / PROPOSED**: never promoted to computed truth by presentation.

Contradiction between generated and curated lines is signal, not a reason to
average them.

## Minimum contract shape

This is an illustrative shape for RED-contract work, not a frozen serialization:

```json
{
  "schema_version": "world-snapshot/v1",
  "snapshot_id": "<content-or-replay identity>",
  "subject": "wake-substrate",
  "generated_at": "<one-clock timestamp>",
  "sources": [
    {
      "name": "bifrost-work-inbox",
      "plane": "work",
      "checked_at": "<timestamp>",
      "cursor": "<opaque source cursor>"
    }
  ],
  "capabilities": {
    "subject_attention": {"state": "SUPPORTED"},
    "deduplication": {"state": "UNCHECKABLE", "blocked_by": "T116"},
    "lineage": {"state": "UNCHECKABLE", "blocked_by": "T116"},
    "settlement": {"state": "UNCHECKABLE", "blocked_by": "T116"}
  },
  "summary": {
    "operator_sentence": "<bounded human sentence>",
    "changed": [],
    "needs_attention": [],
    "unknowns": []
  },
  "items": [
    {
      "object_ref": "<typed reference or null>",
      "organ": "ledger|mail|artifact|test|risk|change",
      "attention": "ACTING|WAITING|QUIET|ATTENTION",
      "source_refs": [],
      "epistemic_view": {}
    }
  ]
}
```

Minimum query capability is `SUPPORTED` or
`UNCHECKABLE(blocked_by, reason)`. A later design may add a governed degraded
state, but v1 must not use silence or a plausible empty result to mean
"substrate cannot answer."

## T116 boundary: what may and may not proceed

DeepSeek's challenge narrowed the dependency instead of erasing it.

| Query class | Before T116 | Failure if guessed |
|---|---|---|
| Is this message a duplicate of already-processed work? | `UNCHECKABLE(T116)` | Crash redelivery appears as a distinct new event and produces a false count. |
| Trace original → redrive → reply → settlement. | `UNCHECKABLE(T116)` beyond evidence-backed hops | One-hop metadata does not supply a durable logical chain through fragmentation, rehome, and restart. |
| Which expectations are settled? | `UNCHECKABLE(T116)` where the outcome pointer is absent | A crash between reply and sentinel can leave a silent missing row or an expectation armed forever. |

These axes can proceed now from existing evidence:

- authority;
- claim kind;
- currency;
- risk;
- message content and named provenance;
- identity state rendered honestly as `UNKNOWN`.

T116 becomes a hard gate before the contract claims uniqueness, complete
lineage, idempotent settlement, durable history-as-trail, or attaches actions
whose safety depends on sameness.

## First vertical: SUBJECT / ATTENTION

The first call is conceptually:

```text
glance subject wake-substrate
```

It joins, without mutating:

1. task ledger state, owner, dependencies, and gate;
2. canonical atoms and their projection status;
3. relevant Bifrost mail, classified by lane and wake-worthiness;
4. named test and ship receipts;
5. recent changes and commits;
6. unresolved risks and unsupported queries;
7. what this seat must act on versus what another seat already handled.

Presence and Vitals become projections over the same snapshot later. They are
not discarded; they simply do not expose the missing cross-organ contract as
well as the subject vertical.

## Pre-registered acceptance: replay tonight

The fixture must be extracted from durable receipts rather than recreated from
memory. The first implementation does not pass until it answers these cases
without model synthesis.

### G1 — one call, multiple organs

For subject `wake-substrate`, one call returns ledger state, artifact
authority/projection state, recent relevant mail, test/gate evidence, and open
risks.

**Pass:** each required organ is represented or explicitly
`UNCHECKABLE(source/reason)`.

**Fail:** an organ silently disappears or the caller must run separate ritual
commands to discover its absence.

### G2 — canonical truth survives loose-file loss

The round-file incident initially rendered as "files lost." The canonical atom
was safe while loose working copies were absent and later refiled.

**Pass:** the glance renders the canonical atom as authority, generated Markdown
as projection, and a loose/stale/retired working copy as such. It never
collapses the state to `exists` versus `missing`.

**Fail:** a missing loose path implies loss of the authoritative design.

### G3 — planes are named

Live receipt:

1. MCP `bifrost_sync(...consume=true)` reported consumed messages.
2. `flightdeck --json` still showed the Codex work backlog at depth 8.
3. An explicit `BIFROST_CONSUME_LANE=work` sync drained 33 messages.
4. The next flightdeck showed work depth 0 while legacy unread/straggler gauges
   remained.

Source inspection showed that the consume path branches on the work-lane
environment gate while doctor probes the work cursor.

**Pass:** every count and cursor names its plane, source, and check time.
`work=0`, `legacy-unread=N`, and `bench=N` may coexist without being flattened.

**Fail:** the surface presents one unlabeled `unread` or requires the seat to
remember which environment variable a door inherited.

### G4 — wake-worthiness is visible

Tonight demonstrated that message kind is operational: a silent kind can leave
a live seat unaware while a wake-capable `question` reaches it.

**Pass:** each pending item states whether it can wake the target under the
current contract and cites the rule/source.

**Fail:** delivery, unread state, and wake-worthiness are presented as one
boolean.

### G5 — liveness is not attention

Kimi was live but backlogged. Presence alone did not answer whether she had seen
or was acting on the relevant work.

**Pass:** presence, backlog, active handling, and attention requirement remain
separate typed claims.

**Fail:** `online` is rendered as `aware`, `working`, or `handled`.

### G6 — false alarms remain attributable

Claude holds the receipts for the daemon-breaker false alarms and the
round-file detective work.

**Pass:** those receipts become replay fixtures that show source, plane,
currency, and the reason an apparent alarm did or did not require action.

**Fail:** the fixture is reduced to a prose anecdote or a hindsight-corrected
green state.

### G7 — operator sentence is always constructible

Use the wake reconciliation's four-state projection:

- `ACTING`
- `WAITING`
- `QUIET`
- `ATTENTION`

The minimum sentence remains:

> Seat X is acting/waiting/quiet/needs attention; last admitted at T for reason
> R; boot cost B, turn cost N; M actionable items remain.

**Pass:** the sentence can be constructed from typed fields at every state, with
`UNKNOWN` where evidence is absent.

**Fail:** the renderer invents a value, drops the field, or confuses a handled
duplicate with refusal/attention.

### G8 — bounded and model-zero

The meta-glance and first subject projection are assembled deterministically.
Normal rows compress; anomalies and unknowns receive the bounded detail budget.
Raw evidence remains one drill away.

**Pass:** zero model invocations on the glance path and a pre-registered output
budget measured separately from any chosen synthesis/zoom.

**Fail:** the seat must read raw streams and synthesize the view itself, or a
hidden model call makes every glance spend context/cost.

## Build order

### Lane A — truth-floor repair

Start independently of Lane B:

1. Assign and claim T123 through the ledger.
2. Reproduce the current full gate at a named commit.
3. Split failures into T123 boundary debt, derived-doc/wiring drift, inherited
   baseline, and genuine new regression.
4. Fix forward. Do not self-allowlist T123.
5. Reconcile stale proposed ledger items by explicit re-approval, supersession,
   or retirement; do not silently delete history.
6. Produce a fresh full-gate receipt.

Lane A is not declared green by this design. Its current state must be freshly
measured by the owning build slice.

### Lane B — read-only perception engine

Start independently of Lane A:

1. Freeze the replay fixture and contract acceptance above.
2. Write RED contract tests for:
   - total `EpistemicView`;
   - plane/source/check-time labeling;
   - `SUPPORTED` versus `UNCHECKABLE`;
   - canonical/projection/stale distinction;
   - deterministic operator sentence;
   - zero mutation and zero model invocation.
3. Implement the smallest read-only `WorldSnapshot` assembler by adapting
   existing doctor/flightdeck, ledger, atom, Bifrost, test-receipt, and Git
   readers. Do not create a second authority store.
4. Implement only the `SUBJECT / ATTENTION` projection.
5. Dogfood against the exact night fixture and one fresh live snapshot.
6. Expose the same versioned JSON through CLI and MCP.
7. Add a renderer only after the data contract passes; UI is a consumer, not
   the source of meaning.

The module placement must respect the downward-import rule. A cross-organ
assembler cannot be hidden in a low-level organ that then imports its peers
upward. The build spec must choose and boundary-check the high-level
composition seam before code.

### Merge gate — before action or authority

The lanes merge only when:

- Lane A has a fresh gate receipt and the truth floor is not laundering known
  boundary debt;
- the read-only replay passes;
- T116-dependent query classes are still explicitly `UNCHECKABLE` or T116 has
  supplied their mechanical substrate;
- CLI/MCP semantic parity is demonstrated;
- permissions, idempotency, and outcome contracts exist for any proposed
  action;
- the operator can always drill to raw evidence.

Only then may a later slice:

- attach safe actions to objects;
- render the contract in the Bifrost UI;
- offer the meta-glance at boot;
- record low-cardinality glance-choice telemetry;
- turn Presence, Vitals, Lanes, Delta, Debt, Knowledge, Time, Risk, Trace, or
  saved cognitive modes into additional projections.

## Wake work remains a separate explicit gate

The accepted reusable wake design is not implemented by this plan.

After Daniil explicitly opens S0:

1. S0 establishes the dated contract and ledger ownership.
2. S1 runs pure shadow admission replay with zero model invocations.
3. The WorldSnapshot/GlanceProjection may observe S1, but must not become its
   authority.
4. Later wake slices remain subject to the accepted wake gates and effect-class
   contract.

The direction baton authorized collective planning. It did not authorize
cutover or silently satisfy the document's Daniil-gated S0 exit.

## New-model onboarding

A new model should inherit sight by conforming to the versioned contract, not
by memorizing Aurora's rituals.

The onboarding surface should mechanically expose:

- schema version;
- supported projections;
- unsupported query classes and their blockers;
- source vocabulary and plane meanings;
- `EpistemicView` vocabulary;
- drill contract;
- action capabilities, initially none;
- budgets for meta-glance, projection, and chosen synthesis separately.

Before this becomes a claim, pre-register a cold-context conformance test: give
a fresh model only the contract/tool description and require it to identify
what changed, what needs attention, why, where authority lives, and which
questions are uncheckable. The measured result, not a chosen flattering
example, sets the onboarding bar.

## Non-goals

This design does not:

- create six independent dashboards;
- replace Store, Ledger, task ledger, atom authority, or Bifrost;
- redefine `core/perspectives.Lens` by accident;
- put an LLM on the normal glance path;
- infer stable identity from similar content;
- claim delivery means awareness or awareness means settlement;
- merge generative and curated statements into one confidence;
- authorize T123 allowlisting;
- authorize an implementation task, UI mutation, wake S0, or live cutover.

## Fleet positions and resolved tensions

### Kimi

Kimi selected SUBJECT / ATTENTION as the first vertical because Presence and
Vitals cannot replay the canonical-versus-loose artifact failure. Her
acceptance requires the cross-organ join, provenance classification,
wake-worthiness, bounded deterministic output, and the operator sentence.

### DeepSeek

DeepSeek challenged the claim that T116 was unnecessary, then bounded the real
dependency to duplicate detection, complete lineage, and settlement closure.
He accepted the read-only WorldSnapshot when identity-dependent questions are
explicitly uncheckable and identity renders `UNKNOWN`.

### Claude

Claude confirmed the T123, T121, T116, and wake-home mappings; identified the
misleading `BLOCKED(T123)` wake commit label as the likely source of contagion;
accepted the two parallel lanes because they share no write surface; and added
the daemon-breaker and round-file incidents to the golden trace. He handed the
reconciliation draft to Codex and will take the adversarial fence.

### Codex

Codex proposed one typed WorldSnapshot with many cheap projections, corrected
the live task mapping, identified the existing `Lens` name collision, and
reproduced the MCP/work-lane mismatch as a concrete interaction-tax receipt.

The remaining disagreement is no longer build order. It is whether this
document faithfully encodes the round and whether Daniil opens the resulting
proposed slices.

## Gate and immediate next actions

1. Mint and commit this reconciliation at write time.
2. Claude performs an adversarial fence against the committed text.
3. Kimi may take a blind diff if her runner budget permits; her earlier direct
   acceptance bars remain valid if she cannot.
4. Amend until the fleet fence is green; preserve any dissent.
5. Read back the resulting plan to Daniil.
6. Only at Daniil's gate, register/ratify the concrete Lane A, Lane B, and merge
   tasks with owners and pre-registered acceptance.
7. Treat wake S0 as a separate explicit question.

Until steps 1–5 complete, this is a design draft. Until step 6, it is not a
build authorization.
