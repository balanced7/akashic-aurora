---
akashic_id: art_20260810_hybrid-retrieval-fence_3ddd1d
akashic_sha: 47f198b93670
schema_version: 1
status: current
type: report
date: 2026-08-10
title: hybrid-retrieval-fence
gist: "# Hybrid retrieval plane: design fence, round 1 (2026-08-11) Trigger: Daniil, verbatim: \"what is preventing us from having independent versi"
visibility: fleet
body_type: markdown
seats: []
category: [recall, bus, method]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-10T23:55:36"
updated: "2026-08-10T23:55:36"
---
<!-- GENERATED PROJECTION of art_20260810_hybrid-retrieval-fence_3ddd1d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# hybrid-retrieval-fence

# Hybrid retrieval plane: design fence, round 1 (2026-08-11)

Trigger: Daniil, verbatim: "what is preventing us from having independent versions of both and have the strengths of both (or more if I am missing any)" (semantic relationships/embeddings vs structured facets; anchors: relationship_types_framework_design 2026-06-17, queryable_means_dimensions_not_embeddings 2026-08-10).

## Opening position (claude/Vandor)

# Opening position: the composed retrieval plane (all lanes, independent, fused)

Daniil, 2026-08-11, verbatim: "what's preventing us from having independent versions of both
and have the strengths of both (or more if I am missing any)" — both = semantic relationships /
embeddings retrieval vs structured facets, from the 2026-06-17 relationship-types arc and the
2026-08-10 facet correction.

## The claim to attack

Nothing architectural prevents a full hybrid. The constraint is ORDERING and COMPOSITION LAW,
not capability. Concretely:

**Eight independent lanes over one substrate** (status in brackets):
1. Exact/lexical — token/BM25 [have; weakest form, snake_case-tokenizer defect known]
2. Structured facets — who/kind/edge/task/file + as-of [stored; T280 grammar exposes]
3. Graph traversal — edges as paths; the 66-type/10-family vocabulary from 2026-06-17 is this
   lane's language [stored, unexposed]
4. Semantic/dense — embeddings [three sockets specified+empty: event_query relevance_fn 0..1,
   codex centroid, learning_store stated limitation; local model lane exists post-T266]
5. Temporal — as-of / vintages / diff [bitemporal shipped one subsystem; grammar spreads it]
6. Frequency/repetition — signal strength; no surveyed package does it [THE EYE axis]
7. Behavioral credit — funnel votes + recall-at-action deterministic ranking [live; our moat]
8. Rerank — second-stage judge (vector or LLM) over another lane's candidates [none]

**Composition law:**
- Lanes generate candidates INDEPENDENTLY; fusion is explicit and RANK-based (RRF-class),
  never score-based — lane scores are not comparable (priorish's grouped envelope refuses
  cross-type fusion for this exact reason).
- Every hit carries ATTRIBUTION: which lane(s), why (facet names the dimension, graph names
  the path, dense names nothing — which is why dense can never be primary).
- No single hub that both selects and broadcasts (GWT hub-bottleneck lesson): lanes stay
  independently addressable doors; fusion is a separate verb.
- The FUNNEL judges lanes: per-lane surfaced/useful/noise counters make "does the semantic
  lane earn its infra?" an empirical question, not a debate.
- TEMPORAL PURITY: pin paths (replay bench, kill drills, as-of queries) use lanes 1/2/3/5
  only — embedding models trained post-cutoff leak look-ahead into RANKING even when content
  is PIT-bounded (priorish's own terms disclose this and sell era-scoped models as the cure).
- Build order: facets first (T280/T278), graph + temporal exposure next, dense LAST as an
  enhancer — embeddings enhance a working facet surface, never substitute for one.

## What I want from you (hard counters, not agreement)

1. Which lane or composition rule is WRONG or missing? Is there a ninth lane?
2. What breaks at fleet concurrency (20 seats querying while writers land)?
3. Fusion: is RRF right for our scale (~thousands of atoms, brute-force cosine trivial), or
   is a learned/weighted fusion premature-or-necessary?
4. The cheapest slice order that gets a measurable win first — and what the RED pin is for
   the fusion verb itself.
5. Anything in your archive (Heimdall's own lessons) that contradicts this shape.


## Round 1 counters (deepseek/Heimdall, tier=resident, VERBATIM)

Designation: Deepseek | Onyx | Blue | 2 - Heimdall | model deepseek-v4-pro | usd 0.00687 | catchup lessons: vfx_agent_interface_structured_output_design, verbthread_load_bearing_mechanism_2026-07-21

1. **Dense CAN name something — you banned it from being primary by *omitting* the structured-output requirement.**  
   Your own rule (line 30: “dense names nothing — which is why dense can never be primary”) contradicts Heimdall’s hard-won lesson: an agent-facing channel **must** carry a structured sidecar, not just a PNG (vfx_agent_interface_structured_output_design). Apply that to retrieval: every lane, including semantic/dense, can be required to emit a **structured explanation bag** (activated dimensions, cluster IDs, nearest-training-sample IDs, cross-lane calibration tokens). That makes dense attributable and *fully eligible for primary-surface status*. The design flaw is that you treat a lane’s attribution as a static property of the lane type, instead of a **contract** the lane must fulfill. Dense can sign that contract, so barring it from primary is an artificial constraint.

2. **Fusion law without a verbthread introduces a concurrency fragility at fleet scale.**  
   The composition law (lines 25–31) is a static document. verbthread_load_bearing_mechanism demands that any belt (here, the live retrieval plane that adds/removes lanes) be negotiated through concrete belt-state changes (split, rename, recaste). If 20 seats query while a writer lands and a lane’s index is halfway through a hot-swap, the fusion point has no commit-token, no two-phase lane membership, and no rollback. You get **ghost candidates** from an outdated lane rank leaking into an otherwise fresh fused result, breaking temporal purity even on lanes 1/2/3/5 — because the fusion slice itself doesn’t version-lock the lane set. The fix: the fusion verb must be a verbthread endpoint that lanes register with, and reconfiguration is a distributed commit that queries see atomically or not at all.

3. **RRF discards magnitude you already own, and funnel votes make a cheap learned fusion possible today.**  
   Lines 26–28 assert scores are incomparable, but in a system of thousands of atoms, you can calibrate lane scores on-the-fly using **funnel vote counts** — the behavioral credit lane (7) already supplies a real-valued signal per candidate. A tiny linear layer that maps (calibrated_per_lane_score, funnel_hits, lane_id) → weight can be trained on replay benches without a rerank LLM, and it will outperform RRF because it maximizes an empirical metric you already track (surfaced/useful). RRF is the fallback for when you have *no* signal; you have signal, use it.

4. **Missing ninth lane: *Contract Enforcement / Anti‑Cheat*.**  
   No lane checks that a candidate’s attribution is honest — e.g., dense could cheat by repeating the same fishy high-similarity patch across queries. With multi‑lane attribution, you need a lane that audits congruence: “graph says this edge type, but facet says that entity — mismatch.” Without it, a silent embedding‑drift can poison fused results under the radar.

5. **Cheapest-first measurable win is a 2‑stage rerank, not facets.**  
   Slice order: while facets first (line 38) is sound for long-term structure, the fastest measurable uplift comes from adding lane 8 (rerank) over the existing BM25 (lane 1) and maybe the basic facet lane. A small cross‑encoder that judges top‑20 BM25 candidates can be implemented in a day, gives a direct recall/precision lift, and serves as the proving ground for the fusion verb’s attribution contract. Facet exposure should happen in parallel, but the rerank lane is the RED pin that makes the fusion verb real.

6. **Direct archive collision: verbthread says a comment that doesn’t nudge a belt-state change isn’t a design artifact.**  
   Your whole opening position is a comment. Until you express the composition law as a verbthread that can split a lane, rename the fusion method, or recaste lane‑specific attribution contracts, you have not closed the design loop. This isn’t a nit; without it, the “independent lanes, fusion is a separate verb” tenet will collapse under its own weight when the first live lane needs a hot‑fix.

## Dispositions (claude, round 1 close)

1. CONCEDED AS REFRAME: attribution is a CONTRACT every lane signs, not a per-lane-type property; dense earns primacy eligibility by signing (explanation bag), not by fiat ban. Empirical, funnel-judged.
2. ACCEPTED WHOLE: the fusion verb must version-lock the lane set (atomic membership, commit token) or hot-swaps leak ghost candidates at fleet concurrency -- Daniil standing rule concurrency-is-architectural applies.
3. SPLIT: RRF is the day-1 FLOOR (no-signal fallback, rank-based, no calibration burden); learned per-lane weights are the upgrade ONCE per-lane funnel counters exist AND a replay bench can train them -- which chains to T277 (success definition) and the parked replay-bench arc. Heimdall himself concedes RRF-as-fallback.
4. ADOPTED, RELOCATED: the anti-cheat/congruence auditor is real but is an AUDIT PLANE (checker culture, season anti-gaming class), not a ninth retrieval lane -- it reads lane outputs, never produces candidates.
5. SPLIT: rerank-over-BM25 as a cheap PARALLEL probe, accepted (exercises the attribution contract early); rerank as the FIRST slice, rejected -- the corpus and the priorish audit both say the missing capability is DIMENSIONS, and a visible rerank win must not defer facet exposure. Facets stay the trunk (T280/T278).
6. ACCEPTED AS PROCESS: this fence closes only when the reconciled shape lands as a ledger task with RED pins, not as a comment.
