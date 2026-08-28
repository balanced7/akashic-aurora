# T370 shadow-shelf pilot — Slice 0 build specification

**Status:** pre-registered, implementation not started
**Lead:** Sunshine (`sol`)
**Independent reconciler:** Vandor (`claude`)
**Parent work:** T370, with T369 supplying the later evaluator; T084 is Sunshine's current coordination umbrella.
**Fence:** `fences/shadow-shelf-substrate/` (formally closed; correction commit `6e42d6d9`).

## Decision

Build the smallest offline proof of the experimental plane before wiring any live watcher.
The proof has one behavior-changing category, one current champion, one deterministic
challenger, one complete cohort envelope per source event, separate observation and judgment
authority, a bounded disagreements-first reader, and measured SQLite/WAL cost.

The fence found two genuinely independent convergences after subtracting requirements already
present in the brief: category identity is a machine contract rather than a label, and death
must remain visible. The original claim of seven independent convergences was corrected by
Vandor; the other five were mostly compliance with the brief and do not count as independent
evidence.

## Why this slice is smaller than the reconciled composite

The largest unresolved risk is write amplification. DeepSeek's read-only census found a prior
reading of 538 recall-at-action injections, while a fresh `agent_cli.py stats` read on 2026-08-28
reported only 42 injections and approximately 5,925 injected tokens under a nominal 24-hour
window. Neither is a daily rate: `recent_injections` is explicitly TEMP-directory-lifetime
observability, so tempdir rotation can shorten the represented window while the renderer still
says 24 hours. The true floor-clearing cohort denominator is unknown, and a durable eligible-event
source must be identified before M9 can be measured. Approximately 400–500 eligible events/day
and approximately 0.8 MB/day are historical hypotheses, not current measurements. Therefore
Slice 0 has:

- no live hook or resident watcher;
- no embedding/model invocation;
- no Bifrost, Discord, EventLog, canonical-memory, or task-ledger write;
- no candidate credential or communication surface;
- only an isolated SQLite/WAL database and deterministic fixture replay.

Live shadowing remains gated on measured rows/day, bytes/envelope, WAL growth, runtime, and a
kill/restart receipt from this slice.

## One category: `recall.at_action.rank.v1`

This is a category because its contract changes a machine decision: which recall candidates are
selected and ordered for an action. It is not the existing free-form `category` metadata field.
`domain`, `urgency`, `theme`, `confidence`, and `favorite` remain read-time facets and cannot
change category identity.

The canonical contract tuple is hashed from:

1. input schema and indexed-over event kind;
2. candidate terminal-outcome schema;
3. comparison semantics;
4. retention and visible-death policy;
5. observation and judgment writer authorities;
6. reader/query semantics and renderer;
7. delivery eligibility (none in Slice 0).

Two names with the same tuple are aliases and the registry refuses the second name. One name
with two tuples is a contract-version conflict and is also refused.

## Observation envelope

One transaction persists one complete cohort for one source event. It carries source identity
and fingerprint, subject, purpose, category contract id/hash, cohort version, watcher incarnation,
and exactly two versioned candidate slots (`champion`, `challenger`). Each slot terminates as one
of `emitted`, `silent`, `abstained`, or `error`, with bounded items, runtime, cost, and an explicit
error reason where applicable. Duplicate source/cohort writes are idempotent.

The envelope is capped at 8 KiB. Oversize candidate output becomes a terminal `error` slot; it
must not disappear and must not prevent the complete envelope from committing. SQLite WAL is the
store; the whole-stream-rewriting `FileLedger` and exception-to-empty `EventQuery` are refused.

### Champion authority in Slice 0

The deterministic Slice 0 champion is a fixture/recording, not proof that the current production
ranker was exercised. A copied champion is allowed only for this offline substrate proof and its
result must carry the detector version/fingerprint. Live integration may not reimplement the
champion inside the shelf: a later adapter must ask the production detector through its real seam
and inject the resulting terminal slot into this substrate. Keeping that adapter outside
`core.recall.shadow_shelf` preserves the Slice 0 no-hot-path/no-writer boundary without turning a
second ranker definition into authority. Fidelity between fixture and detector remains a separate
acceptance gate, not an inference from shared naming.

## Comparison states

- `agreement`: both candidates emitted the same bounded item identities;
- `disagreement`: emitted sets differ, including emitted versus deliberate silence;
- `abstention_delta`: exactly one candidate abstained;
- `incomplete`: at least one candidate errored while the cohort is otherwise inspectable;
- `unevaluated`: all candidates abstained;
- `unavailable`: all candidates errored.

All-silent is agreement only when both terminal silence records are present. A seeded known-wrong
agreement is sampled into a control view so a disagreements-first shelf cannot hide correlated
unanimous error.

## Authority and registers

Observation and judgment are distinct SQLite databases with distinct APIs. Observation writers
cannot write judgments. Judgments are append-only, authenticated with a human/seat principal,
target an exact cohort + candidate id + candidate version, and carry `KEEP` or `DROP` as
retrospective preference only. They never promote a candidate and never claim causal usefulness.
The read model is rebuildable from both registers.

Compaction may remove expired raw envelopes only after appending a manifest containing the cohort
identity, content hash, reason, and timestamps. Judgments survive compaction. The reader renders
the death as `stale`/expired rather than pretending the cohort never existed.

## RED acceptance pins — commit before production code

1. Stable contract hashing; alias and same-name/different-contract refusal.
2. One idempotent, atomic cohort envelope contains both terminal slots, including silence,
   abstention, and error.
3. The comparison-state matrix above, including `unevaluated` and `unavailable`.
4. The 8 KiB cap turns oversize output into a visible error slot while preserving the cohort.
5. Observation and judgment stores/APIs are separate; judgment targets exact candidate version;
   no judgment path can promote.
6. Every numerator renders with its denominator and judgment coverage; no naked win rate.
7. Bounded disagreements-first peek distinguishes `unpeeked`, `partial`, `stale`, `unknown`,
   and `unavailable`; a failed read never becomes `[]`.
8. Seeded known-wrong unanimous output appears in the control sample.
9. Compaction writes a visible manifest before deletion and preserves judgments.
10. Kill between candidate calculation and commit yields either zero cohort or one complete cohort;
    retry is idempotent.
11. Resource health reports rows, bytes/envelope, DB bytes, WAL bytes, and backlog. It auto-pauses
    at configurable limits; pilot defaults are WAL >100 MiB or backlog >2x trailing 24-hour input.
12. The fixture/replay path imports or calls no model, Bifrost, Discord, EventLog writer, or
    canonical Store writer.

## Lane ownership

- DeepSeek: storage/cohort/comparison RED pins only, in a new test file; no production code.
- Kimi: reader/state/control/authority RED pins only, in a separate new test file; no production
  code. Her existing-surface census informs the renderer, but the pilot category remains the
  behavior contract defined above.
- Sunshine: integrate the spec, verify RED failures are causal, then own production integration.
- Vandor: adversarially review the two RED artifacts and the must-not-build boundary before the
  test-only commit; retain reconciliation authority.
- Rill: no new assignment or interruption. A later optional acceptance read is gated on Daniil
  and Rill both wanting it after the substrate is stable.

## Stop / drop rules

Stop before live wiring if the fixture cannot preserve complete denominators, candidate output can
write adjudication, a failed read appears empty/healthy, write amplification is superlinear, the
seeded wrong agreement is hidden, the kill drill produces a partial cohort, or the bounded replay
exceeds the declared resource ceiling. No amount of tuning can promote past one of those failures.

## Post-Slice 0 accepted invariant — preserve the dependency cone

Vandor's read-only acceptance of implementation commit `eca73526` (Bifrost reply
`1787882451422-0`) verified a stronger form of pin 12: `core.recall.shadow_shelf` imports only the
Python standard library. It cannot reach a canonical writer, live detector, model, bus, Discord,
or EventLog through its dependency cone. Isolation is therefore structural in Slice 0, not merely
a behavior that happened not to fire during replay.

Preserve that property. The first live adapter must stay outside this module, ask the production
detector through its real seam, and pass only terminal slots into the substrate. Adding a `core.*`
import to `core.recall.shadow_shelf` is a boundary change that reopens independent review; it is not
an ordinary wiring refactor. This invariant does not claim that the future adapter itself is
isolated — its authority and load require their own pins.
