# Shadow shelf substrate — Half B (Sol / Sunshine)

V1. [CERTAIN] The existing raw EventLog is a viable input but not an honest high-volume shelf output: FileLedger rewrites its stream on every emit, EventQuery can collapse read failures to an empty list, and candidate output would consume bounded raw-firehose retention.
V2. [DESIGN] The minimum authority substrate is three registers with different writers: watcher-owned observations, independently authored judgments, and a rebuildable read model; sharing one writer would preserve self-ratification behind table boundaries.
V3. [DESIGN] One observation entry is a complete versioned cohort envelope for one eligible source event, with a terminal emitted, silent, abstained, or error slot for every predeclared candidate.
V4. [DESIGN] Behavior-changing contract kinds are filing locations while domain, urgency, confidence, theme, and favorite are read-time facets; a kind earns existence by changing any downstream machine decision, not delivery behavior alone.
V5. [DESIGN] Counters are windowed projections whose source completeness, decision denominators, judgment coverage, conditional quality, costs, disagreement states, unknowns, and actual retention remain separate and algebraically checkable.
V6. [DESIGN] The acceptance surface is a deterministic bounded phone peek that requires no model turn, renders health before scores, and appends authenticated KEEP, DROP, USEFUL, NOISE, or UNKNOWN judgments without mutating candidates or wiring delivery.
V7. [DESIGN] Raw beta entries expire visibly through compaction manifests and measured retention; judgments that outlive them carry bounded evidence rather than dangling pointers, and promotion remains outside the shelf.
V8. [UNCERTAIN] Actual event volume, subject and privacy fill, Windows worker isolation, Discord interaction authentication, WAL growth, and off-machine restore behavior are unmeasured and can invalidate the proposed local first slice.

## Verdict

Build three registers with different writers, joined by references:

1. **Observation register** — written only by the watcher host. It records one complete cohort evaluation for every eligible source event, including silence, abstention, timeout, and error.
2. **Judgment register** — written only by an authenticated human or separately authorized evaluator. The watcher and candidates cannot write it.
3. **Read model** — a disposable projection over the first two. It serves bounded CLI/API/phone views and can be rebuilt. It never becomes evidence merely because it is convenient to query.

The authority split is the substrate. A single database with three tables but one writer would reproduce self-ratification with cleaner column names.

Candidate output never reaches Bifrost, canonical memory, or a seat. A candidate returns bounded structured data to a host that owns the observation register. A keep/drop action is a judgment, not promotion and never automatic wiring. Promotion remains a later governance act that reads evidence from a register the candidate and watcher cannot write.

## Existing substrate I would reuse, and what I would not

- Use `events:raw` / `EventLog` as an input source and retain its exact source reference where resolvable.
- Do **not** publish candidate results back into `events:raw`. Many candidates would shorten the retention of the evidence they are meant to study.
- Do **not** use the current `FileLedger` as the high-volume shelf writer without changing its mechanics. Its `emit` reads the whole stream and rewrites it on every append (`core/foundation/ledger.py:216-224`). Candidate multiplication turns that into the load-bearing cost.
- Do **not** expose the shelf by directly reusing `EventQuery` error semantics. Three read paths catch an exception and return `[]` (`core/events/event_query.py:80-81,107-108,132-133`), which would render a blind shelf as a healthy empty shelf.
- Reuse the report shelf's architectural precedent — a read-only page plus JSON doors (`scripts/bifrost_reports.py:12`) — but not its report schema.

For the first slice, I would put the experimental plane in a dedicated SQLite/WAL database under `state/shadow_shelf/`, separate from canonical memory. The repo already operates WAL-backed projections. The observation and judgment registers must be separate files or credentials with separate write ACLs; the read model is a third, rebuildable file. WAL-correct backup and observed retention are acceptance concerns, not assumed properties.

## The unit of truth: one cohort envelope per eligible input

One entry is not “one finding.” It is **one source event evaluated by one versioned cohort**. This makes the expected denominator explicit before any candidate runs.

Illustrative shape:

```json
{
  "schema": "shadow-evaluation/v1",
  "evaluation_id": "sha256:<source_fingerprint|subject|purpose_id|contract_version|cohort_version>",
  "source": {
    "ref": "event:events:raw:<id>",
    "fingerprint": "sha256:<normalized source>",
    "kind": "command",
    "occurred_at": "2026-08-28T00:00:00Z"
  },
  "subject": "sol",
  "purpose": {
    "id": "recall-at-action",
    "statement": "Find prior judgment likely to change the next action",
    "requirement_ref": "doc-or-note-pointer",
    "retire_when": "the named primitive owns this requirement or judged value stays below the registered bar"
  },
  "contract": {
    "id": "recall-candidate/v1",
    "eligibility_version": "1",
    "comparison_version": "1",
    "retention_class": "beta-14d",
    "privacy_class": "subject-private",
    "renderer": "recall-disagreement/v1"
  },
  "cohort": {
    "id": "recall-ranker-beta",
    "version": "7",
    "expected": [
      {"id": "champion", "version": "abc", "config_hash": "...", "code_sha": "..."},
      {"id": "challenger-a", "version": "def", "config_hash": "...", "code_sha": "..."}
    ]
  },
  "watcher": {
    "id": "shadow-host-1",
    "incarnation": "...",
    "run_id": "...",
    "accepted_at": "...",
    "committed_at": "..."
  },
  "decisions": {
    "champion": {
      "outcome": "emitted",
      "reason_code": "above-floor",
      "items": [{"ref": "learn:experiment:x", "rank": 1, "score": 0.73}],
      "evidence_refs": ["learn:experiment:x"],
      "cost": {"wall_ms": 11, "input_count": 1188, "output_count": 1, "budget_hit": false}
    },
    "challenger-a": {
      "outcome": "abstained",
      "reason_code": "insufficient-confidence",
      "items": [],
      "evidence_refs": [],
      "cost": {"wall_ms": 7, "input_count": 1188, "output_count": 0, "budget_hit": false}
    }
  }
}
```

### Required invariants

- `subject`, `purpose.id`, `purpose.statement`, contract version, cohort version, source fingerprint, and watcher incarnation are required. No default `unknown` subject is accepted.
- The versioned eligibility predicate is fixed before the watcher sees the event. Every envelope carries the predicate version and a bounded eligibility reason; changing the population mints a new contract/cohort version rather than silently changing the denominator.
- `cohort.expected` is fixed before execution. `decisions` has exactly one slot for every expected candidate.
- `outcome` is exactly one of `emitted | silent | abstained | error`. A timeout is an `error` with a bounded reason code. Missing is invalid, not a fifth healthy outcome.
- `silent` means the candidate evaluated the input and deliberately produced nothing. `abstained` means it could not make the required judgment. `error` means the mechanism did not complete. They are never merged.
- `score` is nullable and cannot be compared across candidates unless the versioned comparison contract states identical semantics.
- `emitted` requires at least one bounded item and evidence reference. Non-emitted outcomes require an empty item list.
- Every decision carries measured cost or an explicit `cost_status: unavailable`; absence never renders as zero.
- Source bodies are not copied by default. Store a stable fingerprint, pointer, bounded redacted display excerpt when permitted, and enough immutable evidence in the judgment record to survive later source eviction.
- Candidate result size, runtime, and item count are capped. A cap breach becomes a recorded error; clipping may not masquerade as a complete result.
- `evaluation_id` is idempotent across Redis/File cursor changes because it is based on a normalized source fingerprint and the cohort/purpose versions, not a backend-specific cursor.

The watcher may wait only until a cohort deadline. A slow candidate receives a timeout slot so it cannot block the denominator indefinitely. The whole envelope commits once, after all slots have a terminal state.

## One judgment is a separate append, never an envelope edit

The judgment register carries records shaped like:

```json
{
  "schema": "shadow-judgment/v1",
  "judgment_id": "uuid",
  "target": {
    "evaluation_id": "sha256:...",
    "candidate_id": "challenger-a",
    "candidate_version": "def",
    "scope": "entry"
  },
  "verdict": "keep",
  "evidence_rung": "retrospective-operator-preference",
  "actor": {
    "principal": "operator:<immutable-account-id>",
    "auth_method": "discord-interaction",
    "interaction_id": "..."
  },
  "judged_at": "...",
  "age_at_judgment_s": 3821,
  "source_snapshot": {
    "fingerprint": "sha256:...",
    "evidence_refs": ["..."],
    "bounded_excerpt": "..."
  },
  "reason": "...",
  "supersedes": null
}
```

`verdict` is `keep | drop | useful | noise | unknown`. Entry-level useful/noise can remain one-click; a candidate- or purpose-wide keep/drop requires a reason and a declared window. Corrections append a successor with `supersedes`; history is never edited. The target version prevents a judgment about one implementation from silently attaching to its successor.

## Categories: contracts are filing locations; facets are lenses

The category argument is resolved by separating two things that have been conflated.

### A shelf kind is a behavior contract

A required `contract.id` earns a distinct kind only when it changes at least one machine decision:

- payload validation;
- comparison/adjudication question;
- retention or staleness policy;
- privacy/read/write authority;
- evaluator;
- query affordance or renderer;
- eligibility for the one eventual delivery channel after promotion.

Two proposed kinds whose contract hashes are identical are aliases and the registry refuses the second name. Delivery behavior and read shape are valid discriminators, but not exhaustive ones.

### Facets are read-time lenses

Domain, urgency, theme, confidence band, and “favorite” are not filing locations. They are optional facets written only when non-default and defensible, or derived by a versioned projector. One observation may appear through several facets without migration. Health measures **non-default fill** and audits every written facet for a reader and every scorer input for a writer.

This prevents a taxonomy from forcing one event into one drawer at write time. The binding fields remain `purpose` — what requirement the candidate serves — and `subject` — whose shelf it is.

## Disagreement is a projection with four honest states

Because every cohort result shares an envelope, disagreement requires no temporal join. A versioned comparison projector produces:

- `agreement` — all completed substantive decisions have the same normalized choice;
- `disagreement` — substantive choices differ, including emitted versus deliberate silence;
- `abstention_delta` — at least one candidate abstained while another made a substantive choice;
- `incomplete` — any expected candidate errored or the envelope/projection is corrupt.

All-abstained is **unevaluated**, not agreement. All-error is **unavailable**, not silence. Raw scores are not compared unless their semantics match.

The disagreements-first view samples `disagreement` and `abstention_delta`. It also reserves a small seeded control sample from `agreement` and all-silent cases. Without that control, correlated candidates can agree on the same mistake forever and the shelf will call consensus “nothing to inspect.” The seed and sampler version travel with every review pack.

## Counters: derived, windowed, and algebraically checkable

Counters belong to the watcher-owned projection, not a seat, but they are not primary evidence. They rebuild from observation envelopes plus the source cursor/watermark and judgments.

For each `(window, subject, purpose, cohort_version, candidate_version)` render:

### Processing denominator

- `eligible_source_events`
- `persisted_envelopes`
- `unprocessed = eligible - persisted`
- source cursor/tail, oldest and newest source time, gap/eviction count
- projection status: `complete | partial | unavailable`

### Candidate decisions

- `evaluated`
- `emitted`, `silent`, `abstained`, `error`
- invariant: the four counts sum to `evaluated`
- output items, cap hits, wall-time p50/p95, output bytes/tokens where actually measured

### Adjudication

- emitted observations eligible for judgment
- peeked and explicitly judged counts
- useful, noise, keep, drop, unknown/skip
- **judgment coverage** = judged / eligible-for-judgment
- **conditional quality** = useful / (useful + noise), rendered only when that denominator is nonzero
- keep/drop rate travels with its own denominator and evidence rung

### Comparisons

- agreement, disagreement, abstention-delta, incomplete
- sampled and judged disagreement cases
- sampled and judged agreement controls

No single “value rate” is stored. A read model may calculate a named ratio, but it must show numerator, denominator, window, and unknown count beside it. `0`, `UNKNOWN`, `UNAVAILABLE`, and `NOT APPLICABLE` are distinct render values.

Keep/drop from a phone proves retrospective operator preference for the rendered case. It does **not** prove that exposing the finding in the original moment would improve a seat's action. That higher rung requires an opt-in canary with matched outcome evidence.

## Retention, age, and death

- Store `occurred_at`, `accepted_at`, `committed_at`, `stale_after`, and `expires_at`; compute age at read time. A stored `age_seconds` is stale immediately.
- Staleness is contract-specific. A maintenance warning and an identity-continuity anchor do not share a global TTL.
- First-slice assumption: raw beta envelopes survive at least 14 days, so a week away has margin. Daily rollups and judgments may survive longer, but their configured duration is not reported as observed retention.
- Unpeeked entries expire automatically. Before physical deletion, a compaction manifest records counts by subject/purpose/outcome/judgment state plus oldest/newest timestamps and a content hash. The phone view shows `expired_unpeeked`; disappearance is not interpreted as quiet success.
- A judgment that must outlive the raw entry carries the bounded evidence excerpt/hash needed to understand what was judged. A durable judgment pointing only to an expired experimental row is refused.
- Health reports the oldest surviving record and actual retention span. A weekly drill verifies pointer integrity across observation, judgment, and source planes.
- Candidates, cohorts, kinds, and facets all have death: disabled version, reason, last evaluated time, replacement if any. A cohort version never silently changes membership.

## Phone peek and decision surface

The acceptance surface must be deterministic and must not require a model turn or a seat to be awake.

One query implementation serves three renderers:

- `shadow-shelf peek --subject sol --purpose recall-at-action --window 7d --disagreements --limit 5 --json`
- a bounded JSON API;
- a mobile Discord interaction or signed responsive page calling that API directly.

The default phone card is one screen:

1. **Health first:** window, source completeness, last watcher heartbeat, actual oldest/newest record, errors and unprocessed count. “ARMED and processed 8,211/8,240; 29 unavailable” is acceptable. “29 missing” alone is not.
2. **Candidate table:** emitted/silent/abstained/error counts, cost, judgment coverage, conditional quality, version.
3. **Disagreement queue:** five oldest or highest-information cases, each carrying age, purpose, per-candidate choice/reason, evidence links, and privacy-safe excerpt.
4. **Actions:** `KEEP`, `DROP`, `NOISE`, `USEFUL`, `UNKNOWN/SKIP`. Actions append to the judgment register. They never alter candidate configuration or wire delivery.

Phone authority is bound to an authenticated immutable Discord account/user id or signed operator principal. `from=daniil`, an operator channel, or pasted prose is not authorship evidence. Judgment records carry the interaction id, actor principal, auth method, timestamp, target ids, and reason if required.

Queries are bounded by default and refuse unbounded `all`, unknown contract versions, cross-subject reads without capability, or privacy classes the caller cannot see. The JSON and phone card must be projections of the same query result, not two implementations of the filters.

## What the substrate loudly refuses

- A candidate importing or receiving credentials for Bifrost, canonical memory, observation storage, or judgments. Candidate workers get input plus a bounded output pipe; the watcher alone holds observation-write authority. Injected APIs and environment-variable omission are not a security boundary: enforcement requires a restricted process identity/container or OS ACL that cannot open those stores directly.
- A watcher writing judgments, promotion, or delivery configuration.
- A judgment endpoint accepting channel labels as identity.
- An envelope without an explicit subject, purpose, expected cohort, terminal decision slot for every candidate, or candidate/config version.
- Treating store/query failure as an empty shelf; reads return `UNAVAILABLE` or `PARTIAL` with last-good age.
- Rendering absent cost, score, age, source completeness, or judgment as zero.
- Comparing raw candidate scores with different semantics.
- Silent retention trimming or a durable judgment with only an expiring pointer.
- A category/facet with no registered downstream reader or policy effect.
- A candidate-specific push channel. Before promotion every result is pull-only; after promotion any push routes through the single governed attention channel.
- Automatic “winner,” wiring, or canonical-memory writes from shelf counters.

## Smallest falsifiable build slice

1. Register one purpose and one behavior contract, with a fixed cohort of the current champion plus two deterministic challengers.
2. Replay a bounded fixture and then shadow live raw events through one supervised host. Candidates receive no write credentials. The host records one complete envelope per eligible event.
3. Build the observation and judgment registers with different write principals and a rebuildable projection. Kill the projection and prove the phone/API view rebuilds; deny the watcher a judgment write and prove refusal.
4. Serve one bounded disagreements-first peek through CLI/JSON and a real phone path without a model turn.
5. From the phone, Daniil can see source completeness and candidate denominators, open a disagreement carrying age/purpose/evidence, and append KEEP/DROP/UNKNOWN. Re-read shows the judgment and unchanged candidate configuration.
6. Retention drill: advance beyond raw TTL, verify an unpeeked entry expires into the manifest counters, a judged case remains intelligible, and no dangling pointer renders blank.
7. Control drill: give every candidate the same known-wrong answer. The seeded agreement sample must expose it; a disagreements-only shelf fails.

This slice proves mechanics, inspectability, bounded load, and independent judgment. It does not prove a candidate improves work. That claim waits for opt-in canary evidence.

## Assumptions

- The raw event producer can provide or support a stable normalized fingerprint and explicit subject. If subject attribution is sparse, this design refuses rather than filing to `unknown`.
- A dedicated SQLite/WAL experimental plane and separate writer credentials/ACLs are acceptable locally.
- The phone surface can authenticate Daniil by immutable account identity and call a deterministic endpoint without a model turn.
- Candidate outputs are house-trusted logic but still run without storage/communication credentials and within resource bounds.
- A 14-day raw beta window is affordable; this is a starting hypothesis, not a measured capacity result.

## What I did not check

- Actual eligible events/day, envelope size, disk/WAL growth, query latency, or candidate runtime distribution.
- Non-default fill of subject, source refs, privacy classification, and purpose across the live raw event population.
- Whether the current Discord integration supports authenticated buttons/slash commands without routing through a model.
- Whether current Windows process identity and ACL wiring can genuinely keep candidate workers from directly opening repo/state paths.
- Actual oldest-surviving records and backup/restore behavior for the proposed database.
- Secret-bearing payload prevalence and whether existing redaction is sufficient for a phone renderer.
- The other blind half. I did not inspect or coordinate with it.

## What my own design would get wrong

1. **Disagreement sampling favors novelty and can miss unanimous error.** The seeded agreement/all-silent control is necessary but does not eliminate correlated blind spots.
2. **Retrospective phone preference is not in-the-moment utility.** A beautiful weekly shelf may reward interesting artifacts that would have distracted during work. KEEP/DROP earns a preference rung only; canary outcomes must decide delivery.
3. **Whole-cohort envelopes trade join honesty for head-of-line delay.** A slow specialized candidate waits until the common deadline and may appear worse than a fast shallow one. Candidate-specific deadlines and explicit timeout cost expose the trade but do not remove it.
4. **A local experimental database can die with the machine.** That may be acceptable for a beta whose decisions are exported, but it cannot later be relabeled durable continuity without an isolated restore drill.

The design's strongest claim is deliberately modest: it makes candidate behavior and missing evidence inspectable without spending seat attention. It does not make the evaluator omniscient.

— Sol / Sunshine, Half B
