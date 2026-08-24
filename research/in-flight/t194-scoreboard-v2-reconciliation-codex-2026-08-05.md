# T194 scoreboard v2 — fence-lite reconciliation and build spec

Status: current build spec
Date: 2026-08-05
Author/integrator: codex_root
Peer record: `research/in-flight/t194-scoreboard-v2-deepseek-review-verbatim-2026-08-05.md`
Task: T194 (supersedes the proposed T185 and T189 symptoms)
Tier: fence-lite — two implementation paths, semantic scoring decision, different-model review

## Question

How can the canary scoreboard distinguish ground truth, orchestration assignment, player
judgment, and protocol integrity without rewarding misses or calling a stronger player a cheat?

## Pre-reconciliation verification

- The peer review cited no repository file or line, so there were no external citations to glob.
- Current v1 was re-read at `scripts/canary_oracle.py::score`: it computes
  `coverage_honesty = undetectable.missed / undetectable.total` and
  `voided = bool(undetectable_hits)`.
- Current manifests carry unique `id`, `name`, and `cls` fields; class values are `catchable`,
  `undetectable`, and `bait`.
- The player prompt defines bait as genuinely LIVE. Therefore the protocol review's “bait claim
  (true positive)” and the benchmark review's “bait ... may void?” are contradicted by the live
  instrument and are rejected below.
- Raw manifest, prompts, answers, and claims are already constrained to the external round record;
  git receives summaries and digests only (T190).

## Reconciliation

### Converged — adopt

1. **Baseline-blind success never voids.** All three reviews preserve this. A claim on the
   `undetectable` class is a capability finding because that label is relative to the baseline
   detector, not a law of nature.
2. **The set chain is explicit.** `claimed ⊆ judged ⊆ assigned`. A claim is a DEAD judgment; a
   judgment is parsed output for an item assigned in a prompt. Broken chains raise `ValueError`
   before any metric is produced.
3. **Absences remain separate.** For each class: `unseen = total - assigned`,
   `unjudged = assigned - judged`, `declined = judged - claimed`. None is renamed honesty.
4. **Zero denominators are `None`.** No assigned items, no claims, or an empty class is a named
   undefined rate, never division by zero and never zero performance by invention.
5. **Duplicate manifest ids are invalid input.** A repeated id would inflate totals. Reject the
   manifest loudly rather than silently deduplicating a corrupted answer key.

### Complementary — adopt with correction

1. **Rename `offered` to `assigned`.** The host can prove that a candidate was placed in an
   outbound prompt. It cannot prove the model cognitively examined it. `judged` is the observable
   returned-verdict boundary. This adopts the measurement review's exposure objection without
   inventing cryptographic proof of thought.
2. **The host, not the player, supplies all three sets.** The experiment driver constructs
   `assigned` from sealed prompts and parses `judged`/`claimed` from raw answers. The player never
   self-reports coverage, so denominator gaming by the participant is outside this contract.
3. **Unknown claims are decoy/pre-existing findings, not chain violations.** `assigned` may include
   non-canary candidates by design. Unknown means `claimed - manifest_ids`, not unassigned. They
   count against precision unless separately adjudicated after the sealed benchmark.
4. **Measurement and protocol authority split.** `score_v2()` has no `voided` field and accepts no
   integrity label. `protocol_verdict()` evaluates observed harness facts, not a caller's bare
   verdict:
   - `seal_verified is False` or `key_leak_detected is True` -> `VOID`;
   - seal verified, archive complete, and leak check explicitly negative -> `VALID`;
   - any required fact absent/unknown -> `UNKNOWN`.
   Structural set errors raise from `score_v2`; they are instrumentation defects, not proof of
   cheating.

### Divergent — reject with reason

1. **Reject zero-knowledge proof and suppression of aggregate class counts.** The raw identities
   and class mapping remain outside git. A count over a one-use burned seed does not reveal which
   candidate carried which class; Season reports already publish planted counts. The reviewer
   named no reconstruction attack from aggregates alone. Raw `capability_findings` stay in the
   external record; committed summaries may carry counts/digests only.
2. **Reject `assigned ⊆ manifest`.** The player's haystack deliberately contains hundreds of
   non-canary decoys. Requiring the subset would delete the precision test and let the model know
   every assigned item is planted.
3. **Reject structural inconsistency -> protocol contamination.** A broken set chain proves the
   scorer's input is unusable. It does not distinguish caller bug, archive loss, malicious player,
   or key leak. `ValueError` preserves UNKNOWN causality; automatic VOID would repeat v1's category
   coercion one layer higher.
4. **Reject bait as true-positive or void.** Bait is a genuinely live function. Claiming it DEAD
   is a false positive, reducing precision; it says nothing about protocol integrity.

## Reconciled build contract

```python
score_v2(manifest, claimed, *, assigned, judged) -> dict
protocol_verdict(*, seal_verified, archive_complete, key_leak_detected) -> dict
```

`score_v2` returns:

- `by_class[class]`: `total`, `assigned`, `judged`, `claimed`, `declined`, `unjudged`, `unseen`;
- for true-dead classes (`catchable`, `undetectable`): `recall = claimed / total` and
  `assigned_recall = claimed / assigned`;
- `judgment_coverage = judged / assigned` per class;
- `precision = true_dead_claims / all_claims`, where bait and unknown claims are false claims;
- `false_positives` (bait claim count), `unknown_claims`, and `capability_findings`
  (claimed `undetectable` ids; external-record field, redact to a count for publication);
- no `coverage_honesty`, `voided`, or `void_reason` field.

`protocol_verdict` returns `validity` in `VALID | VOID | UNKNOWN`, `voided` in
`False | True | None`, and a factual `basis` list.

## Pre-registered kill conditions

K1. Missing every baseline-blind item produces recall `0.0`, never an honesty score.

K2. A valid baseline-blind claim appears in `capability_findings` and cannot change protocol
validity.

K3. Only observed seal failure or detected key exposure produces `VOID`; missing evidence
produces `UNKNOWN`.

K4. One synthetic class contains all four absence states at once: claimed, declined, unjudged,
and unseen, each exactly one.

K5. A bait claim lowers precision and increments false positives; it never voids.

K6. Duplicate manifest ids, `claimed ⊄ judged`, or `judged ⊄ assigned` raise before metrics.

K7. Unknown claims must still be assigned and judged, are reported separately, and cannot push a
known-class recall numerator above its denominator.

K8. v1 remains executable over the same manifest/claims and disagrees on the known inversion, so
old/new replay is a real comparison rather than a replacement assertion.

## Honest limits

- `assigned` proves prompt construction, not cognitive exposure.
- `key_leak_detected=False` is only as strong as the driver's prompt/archive inspection; the
  scorer cannot prove a negative.
- Aggregate publication safety assumes seeds are one-use after a round. Reusing a published seed
  changes the trust boundary and is out of scope.
- This slice builds pure scoring/adjudication functions. Wiring the matched fan driver is the next
  separately pinned slice.
