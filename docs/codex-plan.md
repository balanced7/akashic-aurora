# The Codex — a self-curating knowledge layer

**Date:** 2026-06-28
**Status:** plan / design (no code yet) — the Wave-2 direction, reframed around documentation self-management.
**Pressure-tested by:** `docs/codex-inventory.md` (2026-06-28) — inventory + slice placement + 8 simplifications.
That pass found the Codex needs only **2 net-new primitives** (Embedder, Clusterer) + reuse, and reorders the
build to do three unifications first (time fn, shared Consolidator, node-lifecycle). Read it alongside this.
**Companions:** `docs/spine-v2-plan.md` (Wave-1 hardening, done), `docs/tag-governance-plan.md` (the governance pattern this reuses), `docs/perspectives-maps-plan.md` (lenses), `ROADMAP.md`.

---

## 1. The premise (why a Codex, not a folder of articles)

The "400 low-quality articles" death spiral happens because a document is treated as a **precious,
hand-edited artifact**. Once precious, nobody dares merge it, nobody can regenerate it, and every new
insight becomes article #401 instead of improving an existing one. Entropy only goes up.

The escape is the move this system already made twice and didn't fully name:

- **Tags** aren't precious — they're *re-derivable opinions* over immutable facts (the tag-governance CRDT).
- **Chapters** aren't precious — they're *regenerated from their atoms* (Beats), with stable ids and supersession-not-deletion.

> **A knowledge Resource should be a derived, regenerable projection over a cluster of atoms — not a
> thing you edit, a thing the system distills.** The atoms (learnings, beats, events, claims) are the
> sacred, append-only substrate. Merge = re-cluster + re-distill. Split = a cluster went bimodal, fork it.
> The worst case of any curation run is a no-op, because — exactly like the tag CRDT — you never touch the
> substrate and you supersede rather than delete.

That last sentence **is** the property the user asked for ("don't lose data by successive cleanup runs"):
it's the same governance discipline, one layer up.

**Key realization — the spine already does this on the time axis.** Beat → Chapter → Atlas is a
regenerate-from-atoms, bi-temporal, supersession-aware multi-resolution tree. The Codex is the *identical
mechanism rotated onto the topic axis*. We are not inventing; we are reusing.

---

## 2. Layer model — one substrate, two projections

```
                      ┌──────────────── ATOMS (sacred, append-only) ─────────────────┐
                      │  learnings · beats · raw events · claims   (the Ledger/Store) │
                      └───────────────┬───────────────────────────┬──────────────────┘
                                      │                           │
              project by TIME  ◄──────┘                           └──────►  project by TOPIC
                                                                          
        ┌──── the SPINE (built) ────┐                       ┌──── the CODEX (this plan) ────┐
        │  Beat → Chapter → Atlas    │                       │  Atom → Resource → … → Codex   │
        │  (Chronicler, time windows)│                       │  (Clusterer + Curator, topics) │
        └────────────────────────────┘                       └────────────────────────────────┘
                 shared organs:  Embedder · Ranker · Distiller · Supersession · chapter_lifecycle ·
                                 tag-governance (confidence/CRDT) · health counters
```

**Lexicon (the knowledge axis).** `Atom` (substrate) → `Resource` (a distilled note over an atom cluster) →
parent `Resource`s (merged, higher abstraction) → the `Codex` (the whole tree). A `Theme` (already in the
spine) is the **embryo of a leaf Resource** — it already gathers beats across tracks; it just doesn't yet
distill, score, or split. Themes graduate into Resources.

**Why two projections over one substrate (not two substrates):** the spine answers *"what happened, when"*;
the Codex answers *"what do we know about X"*. Same atoms, different index. They share the Embedder, Ranker,
Distiller, Supersession, lifecycle, and health primitives — so the Codex is mostly **orchestration of parts
we already built**, plus one genuinely new primitive (the Clusterer) and a new schema (Resource).

---

## 3. The curator loop (and the primitives each step reuses)

The 2026 literature converges on a three-tier consolidation loop ([survey: Memory for Autonomous LLM
Agents](https://arxiv.org/html/2603.07670v1)): **local** (new item finds top-K similar, decide merge),
**cluster-level fusion** (align + generalize/refine clusters), **global integration** (holistic coherence).
Mapped onto our parts:

| Curator step | What it does | Reuses (built) |
|---|---|---|
| **Embed** | atoms → vectors (the substrate for everything) | `Embedder` (new, C0) + `Ranker.relevance_fn` seam |
| **Cluster** | hierarchical, attributed clustering → merge/split *proposals* | `Clusterer` (new, C1) |
| **Distill** | regenerate the affected Resource's summary from its atoms | **Distiller** (writer→critic) |
| **Score** | confidence (evidence+agreement), scent (usage), staleness (superseded-atom %) | **Ranker** + ReinforcedGraph + bi-temporal |
| **Gate** | apply only if the MDL objective improves AND the summary stays faithful | `MDL scorer` (C3) + faithfulness gate (C4) |
| **Supersede** | new version replaces old; `replaces`/`is_version_of` edges; old stays queryable | **chapter_lifecycle** (verbatim) |
| **Flag, don't destroy** | auto-apply only safe high-confidence ops; flag the rest for a cheap confirm | **G2 auditor** pattern + active learning |
| **Observe** | count merges/splits/rejects/staleness so the curator can't silently rot | **health counters** (W-c) |

---

## 4. The objective — what makes "merge or split as needs demand" precise

Vague curation thrashes. The principled objective is **Minimum Description Length under a faithfulness
floor**, usage-weighted ([MDL principle](https://arxiv.org/pdf/2007.14009); [Krimp / VoG: MDL for clustering,
text & graph summarization](https://arxiv.org/pdf/1406.3411)):

> The best knowledge structure **minimizes total description length** — `L(resources) + L(atoms | resources) +
> L(index)` — **subject to**: every Resource summary stays faithful to its atoms (C4 gate), and no atom is
> lost (lossless pointers), weighted by the actual query/usage distribution.

- **Merge** when collapsing two Resources *shortens* the description (high redundancy/overlap).
- **Split** when forking *shortens* it (one Resource answers two distinct query intents — measurable from
  which atoms get retrieved together).
- **Rule of three** (existing project principle): no Resource below 3 atoms; don't split until a sub-cluster
  has ≥3 atoms with *distinct usage*.
- **Hysteresis** (anti-thrash): act only when ΔDL crosses a margin; regenerate-in-place with **stable ids**;
  ReinforcedGraph decay damps churn. (We already hit chapter-id thrash — this is the designed cure.)

This objective is **testable**, which is the real anti-entropy guarantee: "doesn't become useless" stops
being a hope and becomes a standing benchmark (C7) — *can an agent find the right Resource and answer in ≤N
hops?* — exactly as the ARI bar guards routing.

---

## 5. Prior art per organ (what the best approaches do)

- **Multi-resolution structure:** [RAPTOR](https://www.frontiersin.org/journals/computer-science/articles/10.3389/fcomp.2025.1710121/full)
  (recursive cluster+summarize tree; query at any level), [GraphRAG](https://arxiv.org/pdf/2404.16130)
  (hierarchical Leiden communities + summaries), [ArchRAG](https://arxiv.org/pdf/2502.09891) (*attributed*
  communities — densely linked AND thematically similar = a better merge criterion than either alone).
- **Clustering / merge-split mechanics:** BERTopic (hierarchical agglomerative merge; `partial_fit`/`merge_models`
  for streams), [BERTrend](https://arxiv.org/html/2411.05930v1) (online emerging-trend detection),
  [Online topic modeling via Optimal Transport](https://arxiv.org/html/2504.07711v1), [ANTM](https://arxiv.org/pdf/2302.01501)
  (aligned evolving topics). **Caveat from the field:** uncontrolled splitting causes "unnecessary
  proliferation" → our hysteresis + rule-of-three are not optional.
- **Self-evolving agent memory:** [A-Mem](https://arxiv.org/pdf/2502.06975) (Zettelkasten notes that evolve),
  Mem0 (consolidate salient facts, reduce redundancy at source), [three consolidation levels](https://arxiv.org/html/2603.07670v1),
  and crucially [SSGM — Stability & Safety Governed Memory](https://arxiv.org/html/2603.11768v1) (names exactly
  the risks of evolving memory — our invariants answer these).
- **Faithfulness gate:** MiniCheck / **Bespoke-MiniCheck-7B** (SOTA entailment-based faithfulness, small enough
  to run locally), FactCC2, [HaRiM+](https://arxiv.org/pdf/2211.12118), Q-S-E (QA-generate→sort→evaluate),
  [PrefixNLI](https://arxiv.org/pdf/2511.01359) (catch inconsistency early).
- **Temporal / staleness:** [Zep/Graphiti bi-temporal](https://arxiv.org/html/2501.13956v1) — four timestamps
  (`t_valid`/`t_invalid` world-time, `t_created`/`t_expired` system-time), **invalidate-not-discard**, conflict
  detection via semantic+keyword+graph search. (Our Chapter is already bi-temporal; this validates the model.)
- **Embedding substrate (local-first):** for CPU/offline — [EmbeddingGemma-300M](https://innovativeais.com/blog/best-embedding-models-for-rag-in-2026)
  (on-device, Gemma family), E5-Small (~33M), all-MiniLM-L6-v2 (ultra-light), nomic-embed-text (8k ctx). FAISS
  for the vector index if scale demands. Pick by benchmarking 2–3 on our own labeled fixture (C0).
- **Canonicalization / dedup / human budget:** [active-learning entity resolution](https://arxiv.org/pdf/1906.08042)
  (uncertainty sampling — label only the *informative* pairs), embeddings-as-blocking + FAISS, in-context LLM
  clustering ER. → auto-dedup the obvious, **flag only the ambiguous ~5%** for confirmation.

---

## 6. Safety invariants (inherited from tag-governance, extended)

The Codex reuses I1–I6 verbatim and adds two:
- **I1 Immutability** — never edit/delete an atom. **I2 Monotonicity** — a Resource's confidence/maturity only
  rises except on explicit human downgrade. **I3 Append-only** versions. **I4 Reversibility** — every merge/split
  is undoable. **I5 No hard-destroy** — supersede/quarantine, never delete. **I6 Read-only detect** — proposal
  scans never mutate.
- **I7 Lossless** — every Resource keeps pointers to all its atoms; no atom is ever orphaned by a merge/split.
- **I8 Faithful** — no Resource ships a summary that fails the entailment gate (quality floor; stops decay).

These make the formal promise: **successive curator runs converge and can only improve or no-op** — the
document-layer version of the 1000-record CRDT fuzz we already proved for tags.

---

## 7. Slices — each with research-to-do, an acceptance bar, and worst-case tests

Same cadence as Wave 1 / the G-slices: build small, gate on an executable bar, prove robustness with
worst-case tests, mirror. Flag-only before any write power. Each Tier-1 (ML) piece must **beat its Tier-0
baseline on a fixture or it doesn't ship** (the ablation gate).

### C0 — Embedding substrate  *(was V7; now the floor everything stands on)*
**Goal:** an `Embedder` primitive (local model, offline) + an embedding cache on the Store (keyed by
atom-id + content-hash) + wire into the `Ranker.relevance_fn` seam. First consumer: the TrackRouter Tier-1.
**Research-to-do:** benchmark EmbeddingGemma-300M vs E5-small vs bge-small on a labeled routing/recall fixture
(CPU latency + quality); decide FAISS vs in-Store brute force at our N.
**Bar:** embedding relevance **beats the keyword baseline** on the fixture (ablation gate); CPU latency bounded;
a content change invalidates the cache; model-absent → graceful keyword fallback.
**Worst cases:** model missing/offline, empty text, oversize text truncation, cache staleness, identical-text dedup.

### C1 — Clusterer primitive  *(was V6; now the merge/split engine)*
**Goal:** hierarchical, *attributed* (links + similarity, ArchRAG-style) embedding clustering over atoms →
cluster assignments + **merge/split proposals** with cohesion scores. Deterministic, flag-only.
**Research-to-do:** HDBSCAN vs agglomerative vs Leiden-on-kNN-graph; cohesion metric (silhouette / intra-vs-inter);
hysteresis/stability strategy.
**Bar:** on a labeled fixture, recovers the real domains (voice/vision) as clusters, proposes one correct merge
and one correct split; **re-run stability** (same input → same clusters; small perturbation → no thrash).
**Worst cases:** singletons (rule-of-three: no cluster <3), one-giant-cluster, all-distinct, re-run churn.

### C2 — Resource schema + lifecycle
**Goal:** the knowledge-axis node — `Resource(id, title, summary, atom_ids, centroid, confidence, maturity,
valid_from/valid_to, recorded_at, relates[supersession/parent/child])`. Reuse `chapter_lifecycle`
(regenerate-in-place stable id, `correct_*` supersede, bi-temporal).
**Research-to-do:** maturity ladder (seedling→budding→evergreen, digital-garden style) mapped to confidence.
**Bar:** regenerate-from-atoms is idempotent (stable id); merge unions provenance + supersedes olds; split
partitions atoms into two + supersedes old; **no atom lost** (I7); every op reversible (I4).
**Worst cases:** merge, split, round-trip, backward-compat with pre-Codex data, empty cluster.

### C3 — MDL scorer + merge/split decision
**Goal:** the objective function — a description-length estimate + usage weighting + rule-of-three + hysteresis
margin → a **ranked, gated** list of merge/split ops (proposals, not actions).
**Research-to-do:** a tractable DL proxy (token-length + overlap, or a Krimp-style code table); the margin/threshold
calibration; contradiction handling (don't merge away disagreement).
**Bar:** a redundant pair scores *merge*, a bimodal Resource scores *split*, a healthy one scores *no-op*; a tiny
perturbation produces **no** action (thrash guard); a contradicting pair is flagged `contradicts`, never merged.
**Worst cases:** over-merge guard, hysteresis/margin, contradiction, zero-usage resources.

### C4 — Faithfulness gate  *(was V9; now the quality floor / invariant I8)*
**Goal:** an entailment critic on every re-distillation (Tier-0 = the existing source-pointer check; Tier-1 =
a MiniCheck-style NLI model) wired into the Distiller writer→critic seam and the Curator.
**Research-to-do:** local MiniCheck/NLI feasibility vs a strong heuristic; the pass threshold.
**Bar:** catches a planted hallucinated claim (probe-F, made permanent); passes a faithful summary; the Curator
**rejects** an unfaithful merge. Tier-1 must beat Tier-0 on a faithfulness fixture or it doesn't ship.
**Worst cases:** empty summary, all-faithful, adversarial fabricated pointer, partial support.

### C5 — Curator loop (FLAG-ONLY)
**Goal:** orchestrate C0–C4: scan atoms → cluster → MDL-gated proposals → dry-run distill + faithfulness check →
emit a **proposal report**, applying **nothing** (the G2-auditor discipline). Health counters throughout.
**Bar:** on real canonical data, produces sensible merge/split proposals and **mutates nothing** (I6,
byte-for-byte read-only, asserted like the G2 test).
**Worst cases:** empty corpus, no-proposals, corrupt atom skipped, read-only proof.

### C6 — Curator apply (confidence-gated, supersede-not-delete) + active-learning confirm
**Goal:** auto-apply only high-confidence safe ops (near-duplicate dedup); **flag the rest via uncertainty
sampling** for a cheap human/agent confirm; all ops append-only + reversible.
**Research-to-do:** the auto-apply confidence threshold; uncertainty-sampling query strategy for which pairs to ask about.
**Bar:** a confirmed merge applies + is reversible; a low-confidence op is flagged not applied; **successive runs
converge** (CRDT-style no-degrade fuzz, like the tag-governance 1000-record test). No atom lost under a storm.
**Worst cases:** re-run idempotence, rollback restores prior, hostile/low-confidence storm can't degrade.

### C7 — Multi-resolution read surface + standing anti-entropy benchmark
**Goal:** query the Codex at the right level and drill via pointers; ship the standing benchmark (retrieval
quality + faithfulness + hops-to-answer) as a **gate that must not regress across curator runs**.
**Research-to-do:** the eval set (representative questions → expected Resource/atom); the hop budget.
**Bar:** an agent finds the right Resource in ≤N hops; the benchmark score **does not regress** after a curate
cycle (the testable "doesn't become useless" guarantee).
**Worst cases:** ambiguous query, empty Codex, deep tree, stale-resource avoidance.

### Cross-cutting (rides the followup) — staleness via bi-temporal
The spine-v2 followup (unify the 6 `_epoch` copies / timestamp handling) is now a **prerequisite**: staleness
detection ("which Resources rest on superseded atoms") needs correct valid-time vs system-time. With it, a
Resource built on invalidated atoms is flagged stale (Graphiti *invalidate-not-discard*) and re-distilled.

---

## 8. Sequencing & first move

**C0 → C1 → C2 → C3 → C4 → C5 → C6 → C7.** Rationale:
- **C0 first** — the embedding substrate is the floor for clustering, dedup, recall, and merge-overlap; and it
  independently improves routing, so it ships value before the Codex exists.
- **C1–C4** build the organs (engine, schema, objective, quality floor) — each independently testable.
- **C5 (flag-only) before C6 (apply)** — we watch the Curator's proposals on real data and earn trust before
  granting any write power, exactly as G2 (detect) preceded any cleanup op.
- **C7 last** — the standing benchmark that keeps the whole thing honest forever.

**First slice to build: C0 (embedding substrate),** beginning with the research-to-do — benchmark 2–3 local
embedding models on a labeled fixture and pick one — then the `Embedder` primitive + cache + the ablation-gated
routing win. Same test-first, ablation-gated, mirror-per-slice cadence as Wave 1.
