---
akashic_id: art_20260708_deepseek-fenced-design-cross-check-lesso_5f216f
akashic_sha: 69bfd4a157f6
status: draft
type: report
date: 2026-07-08
title: DeepSeek FENCED design cross-check — lesson-content optimization (Forge)
gist: "# DeepSeek FENCED design cross-check — lesson-content optimization (Forge) **Provenance**: DeepSeek (deepseek-v4-pro, think+agentic, read-on"
tenant: solo
visibility: fleet
seats: []
category: [memory, bus, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260701_lesson-forge-evidence-gated-content-opti_fd3204
    rel: cites
created: "2026-07-08T23:54:11"
updated: "2026-07-23T21:42:14"
---
<!-- GENERATED PROJECTION of art_20260708_deepseek-fenced-design-cross-check-lesso_5f216f -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# DeepSeek FENCED design cross-check — lesson-content optimization (Forge)

# DeepSeek FENCED design cross-check — lesson-content optimization (Forge)

**Provenance**: DeepSeek (deepseek-v4-pro, think+agentic, read-only) via bifrost runner,
2026-07-08, answering the raw problem + codebase pointers ONLY — explicitly fenced from
claude's parallel draft (docs/lesson-forge-design-2026-07.md) and all 'forge' bus traffic
until after replying (blind-crosscheck discipline; the fence held: its transcript shows it
re-checking the exclusion before reading context). Request id 1783568591087-0. Captured
from the runner console verbatim; the bus send of this reply hung (T014 evidence).
Reconciliation: claude's design doc sec.12.

---

## (1) Held-out eval / validation gate for a text edit

Options considered: (A) in-vivo champion/challenger — statistically honest but glacially
slow at ~2-5 credits/week corpus-wide, and alternation doubles injection cost; (B)
synthetic eval via the trigger-clause matcher — "the historical credit events ARE the
held-out set": replay the edited lesson through the recall matcher against credit-history
targets; (C) the curator as validator over a trial period; (D) human gate backed by
funnel stats.

**Recommendation: hybrid B + D.** Synthetic replay against historical credit events as a
PRE-FILTER (reject edits that would break credit-carrying retrievals), then human approval
with funnel statistics for survivors. "The synthetic replay is the evidence floor; the
human is the gate. This is honest about the data poverty."

## (2) Safe merging of near-duplicates

1. Candidate discovery: find_related over the whole corpus -> undirected near-dup
   clusters (4-5 dims).
2. Credit fold-in: counters SUM; merged lesson takes the HIGHER surfaced count for
   bench-threshold purposes (don't let a merge look overexposed).
3. Text merge rule: HIGHER-value-rate lesson's text is the BASE; fold only the other's
   DISTINCT details (trigger terms, root_cause) into it.
4. Supersession edge: merged-from lesson gets superseded_by -> redirect, not delete.
5. Safety valve: never auto-merge; propose -> synthetic replay -> human gate.
6. Anti-pattern exclusion: lessons tagged known-bad are NEVER merged — they are
   disconfirmers, and merging dilutes the warning.

## (3) Taxonomy source

Priority: (1) existing category field distribution as seed; (2) TRIGGER-CLAUSE CLUSTERING
as the primary source ("more grounded than category labels and naturally aligned with how
recall matching works"); (3) the recall system's own behavioral classification (what the
agent is DOING). "Don't: import an external taxonomy — the corpus is too small and
domain-specific. The taxonomy is LIVING; a static taxonomy would rot."

## (4) Top failure modes (of its own design)

- FM1 overfitting to 26 credit events: the optimizer must NEVER see raw credit events —
  only lesson text + aggregate counters; the replay gate runs blind AFTER generation as
  coarse pass/fail, never a score to optimize against.
- FM2 edit churn drowning sparse signal: edit SPARINGLY — three narrow triggers only
  (surfaced>=20 & credit 0; near-dup cluster; credit REGRESSION: earned before, silent
  last 15+ surfacings — trigger terms drifted with the repo, e.g. renamed files).
- FM3 merge destroys critical detail: preserve the lower-credit lesson's distinct trigger
  terms as an "also applies when" clause; replay must retrieve on BOTH lessons' credit
  events.
- FM4 human gate becomes a bottleneck: rank by expected impact (credit deficit x
  surfaced), propose <= 2-3 per cycle, unreviewed proposals expire ("the textual learning
  rate applied at the process level").
- FM5 optimizer hallucination: the gate tests RETRIEVAL, not factual accuracy — so the
  optimizer may only do bounded ops (rephrase trigger clause <=1 sentence; fold distinct
  details <=2 sentences; TRIM = delete-only; refresh stale file/path refs) and may NOT
  introduce new factual claims; diff output, never full rewrite; <=40% char delta.
- FM6 taxonomy fighting the trigger system: category is DERIVED from the trigger clause
  and recomputed when an edit changes it.

## Architecture sketch (verbatim structure)

Candidate Discovery (deterministic, after each curator cycle; 3 triggers, <=3 ranked
candidates) -> Optimizer (LLM, bounded ops, aggregate-counters-only input, diff output)
-> Gate (Pass 1 synthetic replay: must retrieve >= incumbent on credited targets, merges
on the union, must not increase injection volume on 24h ledger targets; Pass 2 human:
forge-apply / forge-reject verbs with diff + stats) -> Apply (learn re-record same
experiment_name; stamps forged_at/forged_from/forged_by/forge_gate; category recomputed;
recall cache invalidated; forge event on the firehose).

Explicit non-goals: no automated application (human gate always); no full-content
regeneration; no external taxonomy; no external-repo harvesting (separate feature); no
edits for lessons with < 10 surfaced impressions. Rejected-edit buffer judged "overkill
at our scale" (discard failed edits instead).

---

## Reconciliation summary (full table in design doc sec.12)

CONVERGED independently (locked): replay-against-credit-history as the gate; bounded ops
+ 40% budget; merge via supersession edges + counter folding + union-replay; emergent
trigger-clause taxonomy; offline-only, <=2-3 candidates/cycle; fail-soft.

GRAFTED from DeepSeek into the design: optimizer blinding (FM1), credit-regression
trigger (FM2), base-text merge rule + anti-pattern exclusion (2), no-new-claims edit
constraint (FM5), proposal expiry (FM4).

DIVERGED (now sec.10 decisions): human-gate-always vs auto-provisional-with-rollback
(claude proposes a trust ladder: human gate first, autonomy earned); rejected-edit buffer
keep (claude) vs drop (deepseek).
