# Institutional-Knowledge Arc — Reconciled Design

Status: current  (2026-07-20, reconciliation of three independent thinks; AWAITING DANIEL'S GATE)

Daniel's charge (verbatim): "Every time we run into an issue, I want us to be able to capture and quantify
those moments in a way that is as transparent to you as possible so you can focus on the work, and then I
want us to institutionalize our solutions and known problems so that they become an ever improving body of
operational and ritual knowledge for us."

Halves: claude (chat expansion, 2026-07-20), kimi (research/reviewed/institutional-knowledge-kimi-half-2026-07-20.md),
deepseek (research/reviewed/institutional-knowledge-deepseek-half-2026-07-20.md). Blind protocol held.

## Consensus diagnosis (all three, independently)

The pipeline is **~60-70% built as a skeleton** — kimi's 7 stations (detect → capture → distill → ritualize →
surface → measure → institutionalize) all exist; deepseek graded 12 mechanisms across 5 stages and found the
same shape. The gaps are **connective tissue and honesty, not missing subsystems**:

1. **CAPTURE is 100% manual** (all three; deepseek: "the bottleneck — every other stage starves without it").
   The telemetry that could draft incidents automatically is already live (bounces, spikes, repeated failures,
   manual recovery verbs, FAIL→SUCCESS flips) — nothing drafts.
2. **QUANTIFICATION has a sensor but no join** (all three) — turn_metrics knows a turn was slow; nothing knows
   it was C1-8's 3rd occurrence or what the class costs. AND (kimi's catch, VERIFIED): **the funnel's own
   denominator is inflated ~2× by C8-3's double-fire — the quantifier is currently gauging the gauge.**
3. **THE CONVEYOR HAS NO MOTOR** (all three) — lesson → constraint → ritual → automation → graduate exists as
   endpoints only. Honesty grades: `graduate` has ZERO working instances; `tag-anti-pattern` has never fired;
   "operational rule until then" ledger lines never get revisited (kimi G4).
4. **RITUALS AREN'T SURFACED AT RITUAL MOMENTS** (all three) — method-baseline is a doc; "about to reconcile →
   pre-register acceptance first" doesn't fire. recall-at proves the injection pattern works; extend its
   trigger catalog to method practices.
5. **THE SUBSTRATE IS SELF-CERTIFYING** (kimi G5 + deepseek gap-3, convergent): C9-1 — lessons are
   self-authored/self-verified/self-ledgered; a fabricated lesson is its own valid source. An integrity floor
   (provenance watermark + cross-validation vs ledger/git) must land before scale.

## Sliced plan (K-series; each fenced, pins RED-first)

- **K0 — TRUE THE DENOMINATOR** (S; kimi S0). Fix C8-3 single-registration + emit a gauge-correction event
  marking the pre-fix series. Gate: stats denominator stops double-counting. Nothing else is trustworthy first.
- **K1 — QUANTIFICATION JOIN** (S/M; kimi S1 + deepseek #2). Per-class recurrence + cost attribution
  ("C1-8: 3 occurrences, ~45min, ~12 interventions") joining turn_metrics/task_costs to failure classes, PLUS
  the institutionalization-yield counter (per ledger C-entry: does a lesson/ritual/constraint cite it? orphan
  rate printed). Read-only join, no new write paths.
- **K2 — AUTO-DRAFT INCIDENTS** (M; deepseek #1 + kimi S2). Machine-visible signals (empty-reply bounce,
  lane-depth spike, repeated identical failure, manual recovery verb, timeout confession, FAIL→SUCCESS flip
  with no credited lesson) auto-draft ledger/lesson CANDIDATES into a bless-queue; an agent confirms/enriches/
  discards. Salience-gated, never auto-minted. Gate: capture rate up, funnel precision not down.
- **K3 — RITUAL SURFACING + GRADUATION** (S; deepseek #3 + kimi S3). Method practices become recallable
  entries riding the recall-at trigger catalog; "until then" ledger rituals get revisit hooks; first real
  `graduate` instance lands (pilot: the manual pause→skip-to-now→resume ritual graduates into recovery-arc S0
  auto-triage — a live conveyor demonstration).
- **K4 — INTEGRITY FLOOR** (M; kimi S4 = C9-1 BLUE-team). Lesson provenance watermark + boot consistency
  check (notes vs ledger/git). ORDERING QUESTION FOR DANIEL: kimi leans K0 first then K4 (cheap honesty, then
  trust); nobody argued K4-first strongly. Recommendation: K0 → K1 → K2 → K3 → K4, with K4 promotable earlier
  if scale accelerates.

## Coupling with the recovery arc (all three converged)

The recovery arc IS this arc's first customer and engine: the CATALOG = institutionalized recovery ritual
(ENFORCE); receipts = auto-captured, quantified incidents (CAPTURE+QUANTIFY feed for K1/K2); drills = ritual
rehearsal (IMPROVE); recovery S0 = the first ritual GRADUATION (K3's pilot). Build them as siblings sharing
the receipt spine; neither blocks the other.

## Gate asks for Daniel
1. Approve the arc + K0→K4 order (or promote K4).
2. Confirm the sibling coupling with the recovery arc (receipts as the shared spine).
3. K0 is one small honest slice — approve it to start immediately (it makes every later number true).
