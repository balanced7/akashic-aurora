# S2 — the consolidation pass that sharpens the corpus (scoping + design)

Written 2026-07-03 (Opus). SCOPING artifact, not a built slice: it decomposes S2 into gated slices and
surfaces the design questions for adjudication. Grounded in the machinery that already exists
(Consolidator, Distiller, FAITH-1, Clusterer) and in the field research (ADR_0702233250: deletion
improves accuracy, but faithfulness-only gates reward over-deletion — coverage must be scored separately).
The S1 triage (`agent_cli.py triage`) already PROPOSES clusters; S2 is the gated machinery that DISPOSES.

## The thesis (one paragraph)

The corpus should get *sharper*, not just *bigger*: value per 1000 injected tokens rises while corpus
tokens hold or fall. The credible mid-2026 recipe (field-verified) is **append-only evidence + a
utility-scored projection that merges near-duplicates by RE-DISTILLING FROM THE ORIGINAL ATOMS** (never
from a prior summary — that's structurally immune to the "photocopy drift" that drove repeated-LLM-
consolidation *below* a no-memory baseline). We already have the append-only Ledger, the utility funnel,
and the FAITH-1 faithfulness gate. S2 adds the two missing pieces — a **coverage** gate and a first-class
**Tests** field — and the orchestration that turns an S1 cluster into one superseding lesson.

## What exists (build on, don't reinvent)

- **Consolidator** (`core/primitives/consolidator.py`) — `items → Ranker.rank → Distiller.distill`, one
  seam, FAITH-1 wired at the Distiller. S2's re-distill IS a `consolidate()` call over a cluster's atoms.
- **FAITH-1** (`core/primitives/faithfulness.py`) — deterministic, no-LLM. HARD gate: every distilled line
  carries a source pointer resolving to a real input atom AND introduces no number/identifier absent from
  that source. This is the **faithfulness half** of the two-sided gate, already built and green.
- **Clusterer** (`core/primitives/clusterer.py`) — embedding clusters of near-duplicate atoms (the merge
  candidates S1 already flags: the `recall_at_action_*` cluster, the `codex_*` cluster, etc.).
- **S2a counter work** (shipped today) — `merge_use_counters` + `prune_ghost_counters`. The credited
  ghosts it deliberately KEEPS are exactly the credit that S2 supersession must fold into the successor.
- **Fleet dispatch** (shipped today) — `core/fleet.call(tag, prompt)`. If the coverage judge needs a
  model, it runs LOCALLY on the fleet at zero marginal cost (a faithful mini, e.g. granite-4.0), not the frontier.

## What's missing (what S2 builds)

1. **A Tests field on the lesson** — each lesson carries its own benchmark questions permanently
   (user idea ADR_0703000542). Storing the questions WITH the knowledge makes every future compaction
   **self-oracled**: coverage is measured against the union of the merged lessons' own tests. The lesson
   schema (`core/learning/learning_store.py`: experiment_name / what_tried / recommendation / root_cause /
   …) has NO such field today.
2. **A coverage scorer** — does the merged lesson still answer what the originals answered? Field lesson:
   a faithfulness-only gate rewards deletion (drop everything → perfectly faithful, useless). Coverage is
   the brake that makes the gate two-sided.
3. **The consolidate-cluster orchestration** — cluster → gather ORIGINAL atoms → `Consolidator.consolidate`
   → two-sided gate → rate-limited, human-confirmed supersession that carries Tests + credit forward.

## The two-sided gate (the heart)

```
merged_lesson = Consolidator.consolidate(cluster_atoms)      # re-distill FROM ATOMS, not prior summaries
    PASS iff:
      FAITHFULNESS (FAITH-1, exists) : merged invents nothing — every claim traces to a source atom, no fabricated numbers
      AND
      COVERAGE (new)                 : merged answers ≥ THRESHOLD of the union of the originals' Tests
    else: keep originals, log the near-miss (never silently drop)
```

Both must hold. Faithfulness without coverage over-deletes; coverage without faithfulness lets a fluent
merge invent. The gate PROPOSES; a human/frontier CONFIRMS before supersession (F2 Goodhart guard —
value metrics never feed the gate as an optimizer input, and nothing auto-prunes).

## Slices (build-in-slices, each gated by a yardstick)

- **S2-0 — the Tests keel (cheap, capture-first).** Add an optional `tests` field (list of `{q, a?}`) to
  the lesson schema + the `learn`/`note` write doors; surface it in `recall --full`. Yardstick: a lesson
  can carry QA questions and they round-trip. No gate yet — "capture first, gate later" (rule of three).
- **S2-1 — the coverage scorer + its eval harness (yardstick BEFORE mechanism).** Build a labeled dataset
  (merged-vs-originals pairs; does the merge answer each original test?) and a scorer, measured against it,
  BEFORE wiring it into anything (the eval-harness-before-fix discipline; mirrors the semantic-eval
  yardsticks shipped today). Start deterministic (keyword/embedding answerability); escalate to a LOCAL
  fleet judge (`fleet call` a faithful mini) only if the deterministic scorer can't clear the bar — and
  grade the judge against the same dataset first.
- **S2-2 — the two-sided gate.** Compose FAITH-1 (have) AND the coverage scorer (S2-1) into a
  `consolidate_cluster(cluster)` over the Consolidator. Yardstick: a merge that drops a covered test FAILS;
  a faithful, coverage-preserving merge PASSES (the metric must be able to fail — narrative_metric_pinned_at_100).
- **S2-3 — supersession mechanics.** Merge → carry the union of Tests forward → **fold the originals'
  credit counters into the successor** (sum surfaced/useful/helped/noise; this is where S2a's KEPT credited
  ghosts land) → mark originals superseded (append-only: originals stay in the Ledger, the projection points
  to the successor) → rate-limited → human-confirm. Yardstick: credit and Tests are conserved across a merge.
- **S2-4 — first gated pass, adjudicated.** Run S2-2/S2-3 on ONE real S1 cluster (candidate:
  `recall_at_action_{bootstrap_flow,usefulness,global_hook,polish,ergonomics}` — 5 overlapping recall-arc
  lessons → one principle + provenance). Human/frontier confirms before supersede. Measure the funnel:
  value-per-1000-tokens should rise while corpus tokens fall.

## Open questions (for adjudication)
- **Coverage metric:** deterministic answerability (keyword/embedding overlap of merged-text vs each test) vs
  a local-fleet LLM judge. Start deterministic (cheap, no drift); the fleet judge is the escalation. Which
  clears the yardstick?
- **Who authors the Tests?** author-at-learn-time (best, but friction) vs mined from what_tried/recommendation
  vs generated by a local model at consolidation time (cheap, but the oracle is then model-derived). Likely:
  optional at learn-time + a fleet-generated backfill for legacy lessons, both marked by provenance.
- **Coverage threshold:** what fraction of union-tests must survive to pass? Tune on the S2-1 dataset; do
  NOT hardcode a guess.
- **Credit carry-forward:** sum the counters (per the `merge_use_counters` precedent) — confirm sum, not max,
  so a merged lesson's proven value reflects all its parents.
- **Cadence:** S2 as an on-demand verb (`agent_cli.py consolidate <cluster>`) first; a scheduled nightly
  "dreaming" pass (the Letta/Rika convergent instinct) only after the on-demand path is proven and measured.

## Sequencing note
S2-0 (the Tests keel) is the cheapest, most independent slice and unblocks S2-1's oracle — it is the right
next build. S2-1 through S2-4 are frontier-design-heavy (the gate is high-stakes: it decides what leaves the
corpus) and should each be adjudicated with the user, per the doctrine that S2 is deliberate foundation work,
not an alpha rush.
