---
akashic_id: art_20260828_purpose-conditioned-recall-measurement_8b0d81
akashic_sha: fa1ad6b3359c
schema_version: 1
status: current
type: design
date: 2026-08-28
title: purpose-conditioned-recall-measurement
gist: "# Purpose-conditioned recall measurement **Status:** operator-origin research amendment; candidate law, not yet a ratified global law, build"
visibility: fleet
body_type: markdown
seats: [daniil, sunshine]
category: [recall, identity, governance]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-28T00:05:33"
updated: "2026-08-28T00:05:33"
---
<!-- GENERATED PROJECTION of art_20260828_purpose-conditioned-recall-measurement_8b0d81 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# purpose-conditioned-recall-measurement

# Purpose-conditioned recall measurement

**Status:** operator-origin research amendment; candidate law, not yet a ratified global law,
build specification, metric, or capability claim.

**Originator:** Daniil.

**Source:** an analysis supplied by Daniil on 2026-08-28 describes his move from one aggregate
recall percentage to purpose-specific criteria and rates. The attached analyst's identity is not
asserted here. The sentence proposed there as the third law is preserved as that analyst's
formulation, not misquoted as Daniil's exact wording.

**Formalized by:** Sunshine, with one necessary refinement made explicit below.

**Canonical parent:** `art_20260827_adaptive-recall-memory-fabric_298a33`.

## The operator move

The question "how good is recall?" has no honest scalar answer when recall is doing different
jobs with different beneficiaries, failure costs, and success conditions. Purpose supplies the
criterion from outside the scorer:

- enforcement recall succeeds when a governed violation is refused at the decision moment;
- discharge or intent recall succeeds when the wanted commitment becomes actionable at the
  intended moment;
- play recall may succeed when an invited connection is explored rather than ignored;
- identity or continuity recall must first satisfy subject and authority constraints before any
  behavioral judgment is meaningful.

A metric cannot define useful as "whatever this metric scored highly" and then claim to measure
usefulness. Declaring the purpose first breaks that circle.

## Candidate purpose law

> **A recall-rate claim is meaningful only against a declared purpose.**

The stronger operational form is:

> **No recall quality claim is meaningful without a versioned purpose contract, an opportunity
> denominator, a purpose-specific success predicate, and an explicit UNEVALUATED state.**

This sits naturally beside the two existing operator-origin laws:

1. Precision at the gate buys density in the pool.
2. Axes are lenses, not filing locations.
3. A recall rate is meaningful only against a declared purpose.

The third remains a candidate law until Daniil treats this formalization as the right expression
of his idea.

## Vector, not scalar

The current global recall percentage should be retired as a claim about recall quality. It may be
preserved as historical telemetry only with its exact numerator, denominator, scope, and `as_of`.
Replacing it with a vector does not mean producing the same metric twelve times. Each purpose may
have a different success predicate and confidence kind, so the rates are not automatically
comparable and must not be silently averaged.

For example, refusal rate, timely-discharge rate, browse rate, and continuity-safe activation rate
do not share a semantic unit. A mean across them is a category error even when the arithmetic is
correct.

## Necessary refinement: partition opportunities, not atoms

Purpose must not become a new filing taxonomy for the corpus. One atom may serve action,
continuity, intent, and play through different projections. Therefore:

- purpose is declared on the **opportunity or behavior contract**, before candidate selection;
- atoms remain many-purpose and are not assigned to one permanent bucket;
- a single evaluated opportunity has one role-bound `purpose_contract_id`, or explicitly declares
  a multi-purpose composition whose counting law is part of the contract;
- retrospective assignment of purpose from the observed outcome is forbidden because it makes the
  success criterion circular and gameable.

If the proposed purposes overlap, the output is a set-valued vector rather than a mathematical
partition. Calling it a partition is valid only after exclusivity and completeness are proved at
the opportunity level.

## The minimum purpose contract

A purpose-conditioned measurement needs at least:

1. `purpose_id` and version;
2. beneficiary and subject;
3. observable decision moment and opportunity predicate;
4. eligible source and projector/site contract;
5. success predicate and evidence/confidence kind;
6. valid delivery window, including the difference between early, timely, and late;
7. noise cost, blindness cost, and authority to refuse;
8. judgment principal and who may not self-promote;
9. minimum denominator or uncertainty rule;
10. explicit non-success and unavailable states;
11. item, byte, latency, and spend bounds;
12. a hash included in the behavior/evaluation identity.

Changing the purpose, opportunity set, success predicate, or delivery window changes the behavior
contract. It is not a parameter tweak to the same experimental arm.

## The diagnostic funnel

One per-purpose hit rate still cannot distinguish corpus, trigger, and delivery failure. The
purpose contract must expose the stages that produce the rate:

| Stage | Count | What a loss can diagnose |
|---|---:|---|
| opportunity | `O` | how often the declared decision moment occurred |
| eligible candidate exists | `C` | corpus/projector reach, reported as `C/O` |
| trigger selects or abstains | `T` | gate fit, reported as `T/C` plus abstentions |
| delivered in the valid window | `D` | transport/timing, split early, timely, and late |
| attended or consumed | `A` | delivery-mode salience, reported as `A/D` where observable |
| independently judged | `J` | judgment coverage, never inferred from silence |
| purpose-specific success | `S` | observed criterion fulfillment, reported as `S/J` |

Not every purpose needs every stage. An inapplicable stage is `NOT_APPLICABLE`, never a fabricated
zero. Every reported ratio carries both counts, the contract id, subject, policy/arm identities,
and `as_of`.

This funnel earns the diagnostic claim in the attached analysis: a low outcome can be localized to
candidate reach, trigger selection, delivery timing, attention, or judgment coverage. A lone
per-purpose scalar cannot do that localization by itself.

## Sparsity and UNEVALUATED

Purpose conditioning trades conflation for smaller denominators. That is desirable only if small
samples stay visible:

- zero observations means `UNEVALUATED`, not zero quality;
- a denominator below a preregistered threshold remains `UNEVALUATED` or carries an uncertainty
  interval that is too wide for promotion;
- missing judgment is `UNJUDGED`, not a negative judgment;
- silence, abstention, refusal, unavailability, truncation, early delivery, and late delivery stay
  distinct;
- sparse categories may be pooled only by a declared hierarchical model whose transfer assumptions
  and failure conditions are explicit.

The threshold is contract-specific. It must not be chosen after seeing the result.

## What may and may not aggregate

Cross-purpose operational totals such as bytes, latency, spend, and opportunity counts may be
summed when their units match. Cross-purpose quality may not.

A weighted composite is permissible only as the score of one named decision policy for one named
principal with weights declared before observation. It must not be relabeled "overall recall
quality," and it never replaces the underlying vector.

## Causal boundary

Purpose conditioning makes mechanical failures attributable; it does not solve the counterfactual
problem. The funnel can measure opportunity, reach, selection, timing, attention, judgment, and an
observed purpose criterion. It cannot infer what the same seat would have done on the same evolving
trajectory without the recall intervention.

Long-run causal superiority therefore remains unknown without a representative randomized or
paired intervention, and even such an experiment proves only its exercised purpose contract,
population, and arms.

## Consequences for the fleet program

- Keep Round A's canonical atom fixed so replies remain independently comparable.
- Introduce this amendment in Round B as a load-bearing claim to attack, not as a settled answer.
- Heimdall should attack whether each numerator and confidence kind earns its claim.
- Navi should attack whether proposed purposes correspond to distinct observable decision moments
  and whether the set is actually a partition.
- Vandor should attack duplicated purposes, hidden weighting, and mechanisms imported across
  domains.
- Rill should attack whether purpose conditioning prevents or merely relabels wrong-subject
  evidence in identity and continuity cases.
- Sunshine should attack whether purpose, subject, opportunity, and success identity survive every
  store, projector, truncation, and restart seam without creating a parallel control plane.

Round C should not mint a global purpose enum. It should produce a small register of versioned
purpose contracts for the few types that survive cross-examination, with explicit generator seams
and falsifiers. Round D may exercise one such contract and can prove no more than that bounded case.

## Cheapest falsifier

Choose two genuinely different purposes and replay the same observed opportunities through the
proposed reporting funnel. The amendment fails if any of the following occurs:

1. purpose is assigned only after the result is known;
2. the same opportunity is double-counted without an explicit composition law;
3. a low final rate cannot be localized to a funnel stage;
4. an empty or too-small denominator renders as a quality score;
5. changing the purpose or success predicate leaves the behavior-contract identity unchanged;
6. the reporting surface averages the two purpose-specific quality rates into one fleet quality
   number.

Until that falsifier survives, this is a promising measurement law, not implemented truth.
