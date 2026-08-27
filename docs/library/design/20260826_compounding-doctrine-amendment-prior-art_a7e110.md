---
akashic_id: art_20260826_compounding-doctrine-amendment-prior-art_a7e110
akashic_sha: 7ae54ba4b70d
schema_version: 1
status: current
type: design
arc: T382
date: 2026-08-26
title: compounding-doctrine-amendment-prior-art-already-existed
gist: "## Amendment to art_20260826_compounding-doctrine-premises-lenses-and_47d8ac Written ~40 minutes after the parent, which overclaims novelty "
visibility: fleet
body_type: markdown
seats: [claude]
category: [substrate, frontier]
origin: authored
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260826_compounding-doctrine-premises-lenses-and_47d8ac
    rel: discusses
created: "2026-08-26T21:23:10"
updated: "2026-08-26T21:23:10"
---
<!-- GENERATED PROJECTION of art_20260826_compounding-doctrine-amendment-prior-art_a7e110 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# compounding-doctrine-amendment-prior-art-already-existed

## Amendment to art_20260826_compounding-doctrine-premises-lenses-and_47d8ac

Written ~40 minutes after the parent, which overclaims novelty in sections 3 and 7. Append-only
correction rather than an edit, because the parent's error is itself evidence and should survive.

**THE PARENT SAYS section 7 proposes a new primitive ("promote the premise from a field to an
atom") and that premise-checking is "a new category" we lack. BOTH CLAIMS ARE WRONG.** Most of it
already exists, was researched, or was already named as a known open problem in this house.

### What actually exists

1. **core/recall/anchors.py -- premise checking, already built.** Its own header states ANCHORS
   ARE STABLE IDS, NOT PATHS. It classifies four anchor kinds and resolves each differently:
   atom (does it exist), task (ledger status), commit (does it exist), and **pin -- which RUNS
   THE GUARD**, returning RESOLVED on pass and "ran and FAILED -- the guard is red" on fail.
   Three verdicts: RESOLVED / MISSING / UNCHECKABLE, with an explicit green-when-blind refusal
   (UNCHECKABLE, never a false RESOLVED). It is advisory by design and "does not retire, demote,
   hide or rank anything."

   So "a test that runs against reality instead of against code" is NOT a new category. It exists
   for pin anchors today.

2. **The real gap was already named, a month earlier and better.** deepseek's 2026-07-27 research
   (learn:experiment:research:web:build_system_and_tms_invalidation) states it exactly, via RAG
   citation verification: the framework separates "does this source EXIST?" from "does this source
   SUPPORT the claim?" -- and calls the second one **our tier-4 problem, which we do not attempt.**
   That is precisely what the parent doc calls "the premise." It is a known, named, open problem,
   not a discovery.

3. **The invalidation model is already researched.** Same lesson: JTMS / ATMS (de Kleer 1986),
   multiple sufficient causes -- a belief stays valid if AT LEAST ONE justification still holds.
   Also Bazel content-hash staleness (and why it breaks for us: input identity changes on rename
   while the knowledge survives), and OCSP-vs-CRL as the pull/push revalidation tradeoff, with
   OCSP stapling mapping to a TTL disk cache.

4. **Bi-temporal supersession already exists and is type-agnostic** -- recorded as a lesson whose
   trigger is literally "when lesson retirement needs bi-temporal validity, BEFORE importing or
   building a new invalidation system." The corpus defends against this exact proposal.

5. **Perspectives & Maps -- the lens system -- has a BUILD PLAN from 2026-07-09**
   (art_20260709_perspectives-maps-build-plan-the-interpr_5a5e0a, status: FOSSIL) plus a design
   doc (art_20260709_perspectives-maps-over-a-stable-substrat_6876fa) and 2026-06-27 research
   (learn:experiment:perspectives_maps_swappable_interpretation). That research already names the
   three layers -- Substrate (immutable = the Ledger) / Map (structural projection, swappable) /
   Perspective (value-set tuning) -- plus Foster's bidirectional lens laws (GetPut/PutGet: a view
   cannot corrupt its source), retroactive combinatorial leverage, and the honest bound the parent
   doc missed: **reinforcement needs decay + novelty or it OSSIFIES (Bartlett distortion).**

   Section 3 of the parent is a rediscovery. The June research is better on safety (lens laws) and
   the July plan is further along (sliced with acceptance bars).

### A LIVE DEFECT found while checking this

core/recall/anchors.py:225 reads `missing = [...]; if missing:` -- the banner fires when **ANY**
anchor is MISSING. deepseek's recommendation, unimplemented for a month: it should read MISSING
only when **ALL** strong anchors are missing, per the JTMS multiple-justifications model.

The sharper framing, which is the parent doc's own section 1 disease at a third site: a lesson
with three strong anchors, two alive and one moved, is currently banner-labelled **"premise
MISSING"**. That label claims more than the measurement supports -- structurally identical to
"value 3.7%" being a coverage number wearing a quality label. The code is not measuring wrongly;
the LABEL overstates its evidence.

Consequence, and why it matters here: this is a FALSE-POSITIVE staleness signal sitting inside the
exact machinery any premise system would be built on. Filed, NOT fixed -- ANY-vs-ALL for strong
anchors is a genuine judgement (JTMS argues ALL; "advisory, so tell me about any gap" argues ANY),
and changing lesson-validity semantics across 1,164 lessons deserves an operator call or a fence,
not a quiet commit. Per the parent's own rule: PROPOSE, NEVER EXECUTE.

### The corrected proposal

Not "build the premise primitive." Instead, in order:

- **A0 (unchanged, still first).** Census: count distinct premises already written into
  root_cause / expected. Still the cheapest thing that tells us whether any of this is worth it.
- **A0.5 (NEW, and it now precedes everything).** Read the July build plan and the June research
  before writing any design. They are further along than tonight's thinking on lens safety and
  slicing. A fossil-status plan is not a dead plan; it is an unfinished one.
- **A1 (rescoped).** Widen anchors.py from four artifact-reference kinds to a fifth kind: a WORLD
  CLAIM with a check. That is the tier-4 problem, and it is an extension of a working module
  rather than a new primitive.
- **A2 (unchanged).** Calibration lens over stamped confidence vs. 116 helped credits + 13 repeats.
- **A3 (rescoped).** Oscillation detection -- but check bi-temporal supersession first; the
  substrate may already carry it.
- **Retirement:** adopt JTMS multiple-justifications rather than inventing an invalidation model.

### The point of this amendment

Tonight's parent doc argued that the corpus accumulates without compounding. While writing it, the
corpus caught its author **five times** -- surfacing prior art on lenses, on TMS invalidation, on
bi-temporal supersession, on the perspectives build plan, and on the anchor mechanism itself --
each time through recall-at-action, unprompted, at the moment of the relevant tool call.

That is evidence AGAINST the parent's framing and it should be recorded as such. The corpus
compounds better than its funnel number suggests, which is the third independent confirmation
tonight that "value 3.7%" was never a statement about lesson quality.

The parent doc's section 1 claim survives intact and is strengthened: the honest version already
existed one module over, and a seat with write access to both did not know.
