---
akashic_id: art_20260709_codex-pressure-test-inventory-placement_364aad
akashic_sha: b7d4be298979
status: fossil
type: design
date: 2026-07-09
title: "Codex pressure-test — inventory, placement, and simplification"
gist: "**Date:** 2026-06-28 **Purpose:** before building Wave 2, take honest inventory of what already exists, decide *where each Codex slice lands"
tenant: solo
visibility: fleet
seats: []
category: [bus, testing]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations:
  - target: art_20260709_the-codex-a-self-curating-knowledge-laye_302fc9
    rel: cites
  - target: art_20260627_lessons-auto-generated-from-the-learning_6dd9bf
    rel: cites
created: "2026-07-09T23:27:59"
updated: "2026-07-23T21:42:04"
---
<!-- GENERATED PROJECTION of art_20260709_codex-pressure-test-inventory-placement_364aad -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# Codex pressure-test — inventory, placement, and simplification

**Date:** 2026-06-28
**Purpose:** before building Wave 2, take honest inventory of what already exists, decide *where each Codex
slice lands* (component + layer), and find where we can **simplify routing and connections** instead of adding
parts. Companion to `docs/codex-plan.md`.

**Headline:** the Codex needs far fewer *new* components than the plan implied. The system already contains
three-quarters of the machinery — but in **parallel copies** that should be unified. Built right, Wave 2
*reduces* conceptual surface area. Net new primitives: **2** (Embedder, Clusterer) + 1 critic that plugs into
an existing seam. Everything else is **generalize-and-reuse**.

---

## 1. Inventory — what exists, by layer

| Layer | Component | Does | Codex reuse |
|---|---|---|---|
| **S0 foundation** | `store`, `ledger` | persistence (KV/zset/hash; append-only streams) | substrate + index home |
| | `timeutil.to_epoch` (new) | tz-safe epoch | the **one** time fn (collapse the 6 `_epoch` copies) |
| | `relationship_types` | the 66-type edge vocabulary | Resource/edge types |
| | `redis_connection`, `fast_cache` | connectors | — |
| **primitives** (cross-cut) | `ranker` | relevance×importance×recency×relationship, supersession-aware; **`relevance_fn` seam** | the **single** embedding seam |
| | `distiller` | budgeted skeleton, lossless pointers, **`writer`/`critic` seams** | re-distill; critic seam = the faithfulness gate |
| | `supersession` | field-based active/retire | read-filter half of lifecycle |
| **S1-3 domain** | `learning/learning_store` | experiment lessons | an **atom** source |
| | `learning/agent_memory` | episodic memory | an **atom** source |
| | `learning/consolidation` | learnings → `chronicles/lessons.md` via Ranker+Distiller | **a Curator already, on the learning axis** |
| | `events/event_log·query·index` | raw firehose + time-indexed reads | an **atom** source + the C0 index pattern |
| | `signals/*`, `state/*` | coordination, session | atom sources (events) |
| **S4 projections** | `narrative/*` (spine) | Beat→Chapter→Atlas, **Chronicler** (group→rank→distill→persist) | **the Curator's twin**; reuse wholesale |
| | `narrative/chapter_lifecycle` | bi-temporal supersession, regenerate-in-place stable id | the Resource lifecycle (generalize) |
| | `narrative/tagging·tag_governance·tag_audit` | confidence CRDT + flag-only auditor | Resource **confidence** + the C5/C6 discipline |
| | `narrative/theme_assigner` | keyword → theme (crude clustering) | **subsumed by the Clusterer** |
| | `narrative/health` | best-effort counters | Curator observability |
| | `perspectives/schema` (Lens, Map) | value-set + structural projection over substrate | **the C7 read surface** |
| | `perspectives/reinforce` (ReinforcedGraph) | Hebbian co-use strength + half-life decay | **scent/usage** signal for MDL + co-use clustering |
| **S5 interface** | `agent_cli`, bootstrap | the agent door | new `codex`/`curate` verbs |

---

## 2. The eight simplification findings (the actual point of this pass)

### S1 — One consolidation engine, not three  ⭐ biggest
`chronicler._build_chapter`, `learning/consolidation`, and the planned **Curator** are the *same pipeline*:
`items → group/cluster → Ranker.rank → Distiller.distill → persist with provenance + supersession`. Two copies
exist today; the Curator would be a third. `consolidation.py` literally calls itself "the episodic→semantic
loop," and `chronicler.py` claims to "generalize consolidation (rule of three)" — but they're still separate
implementations.
**Fix:** extract a shared **`Consolidator`/`Projector`** (a primitive: takes items + a group_fn + a distill
config → summaries-with-provenance). Chronicler configures it by *time*, the Curator by *topic*, consolidation
by *source*. The rule of three already fired — make it real. The Curator becomes ~50 lines of config, not a
new engine.

### S2 — One embedding seam, one Embedder
`relevance_fn` lives only on the **Ranker**; routing, themes, event search, and the tag-audit scorer all rank
through it. `Track.centroid` is already a reserved field for a routing embedding.
**Fix:** the `Embedder` (C0) is a single primitive; **everything consumes embeddings via `Ranker(relevance_fn=embedder)`** — do *not* bolt embeddings onto the router/themes/clusterer separately. One seam, many consumers.

### S3 — The Clusterer subsumes the ThemeAssigner
Clustering exists in exactly one place today: `theme_assigner` (keyword match). Themes are "embryonic
Resources."
**Fix:** build `Clusterer` (C1) as the real engine; re-express ThemeAssigner as a thin Tier-0 caller (or retire
it once embeddings beat it on the fixture). No parallel clusterers.

### S4 — Unify the two supersession models  ⚠️ latent bug
There are **two** retire mechanisms that don't talk to each other:
`primitives/supersession` (field `superseded: True`) and `chapter_lifecycle` (bi-temporal `valid_to` +
`replaces`/`is_version_of` edges). `Ranker.is_active` checks only the boolean — so a node retired *bi-temporally*
(valid_to set) still ranks as **active**. Harmless today (Ranker doesn't rank Chapters) but it **will** bite the
Codex, which ranks Resources that use the bi-temporal lifecycle.
**Fix:** promote `chapter_lifecycle` to a shared **node-lifecycle** and make `is_active` honor *both* `superseded`
and an open `valid_to`. One lifecycle for Chapter + Resource.

### S5 — Collapse the six `_epoch` copies (the followup, now prerequisite)
`event_index, event_query, beat_log, tag_audit, tag_governance, reinforce` each define their own `_epoch`
(locale-dependent for naive timestamps). `foundation/timeutil.to_epoch` already exists (built in D4).
**Fix:** re-point all six at `timeutil`. Required *before* C-staleness, which needs correct valid-time vs
system-time. Do it as the first cross-cutting cleanup.

### S6 — The faithfulness gate plugs into an existing seam
`Distiller` already exposes a `critic` callback, and `chronicler._compute_metrics` already does Tier-0
faithfulness (every `(source: X)` must resolve to a chapter beat).
**Fix:** C4 = implement a `faithfulness` critic and pass it as `Distiller(critic=…)`. No new plumbing; the
chronicler's source-pointer check is the Tier-0 baseline the Tier-1 NLI critic must beat.

### S7 — The C7 read surface is a Lens + Map, not a new retriever
`perspectives/schema` already models a **Lens** (value-set parameterizing the Ranker) and a **Map** (which
relation-domains form the traversed graph). Multi-resolution Codex retrieval = "traverse the Resource tree
(a Map) with a value-set (a Lens)."
**Fix:** C7 adds a `codex` Lens + Map and a thin retrieve verb — not a new retrieval engine.

### S8 — Resource confidence is a composition, not a 5th table
Confidence/strength notions already exist: `tagging.BASIS_CONFIDENCE`, `Ranker` weights, `ReinforcedGraph`
strength. Don't invent a parallel Resource-confidence model.
**Fix:** Resource confidence = **compose** existing signals — evidence count + agreement (tag-governance) +
scent (ReinforcedGraph). C3's weak-supervision learns the weights; it does not add a new scale.

---

## 3. Where each slice lands (revised placement)

| Slice | Lands in | New / reuse | Layer |
|---|---|---|---|
| **(pre) S5** time unification | `foundation/timeutil` ← 6 callers | reuse | S0 |
| **C0** Embedder | `core/primitives/embedder.py` + cache on Store; wired into `Ranker.relevance_fn` | **NEW primitive** | primitives |
| **C1** Clusterer | `core/primitives/clusterer.py`; subsumes `theme_assigner` | **NEW primitive** | primitives |
| **(refactor) S1** Consolidator | `core/primitives/consolidator.py`; chronicler + consolidation refactor onto it | **EXTRACT** | primitives |
| **C2** Resource + lifecycle | `core/codex/schema.py` + generalize `chapter_lifecycle` → shared node-lifecycle (S4 fix) | NEW schema + **unify** | S4 |
| **C3** MDL scorer/decision | `core/codex/curate.py`; uses ReinforcedGraph + Distiller length + tag-gov confidence | NEW logic, reuse signals | S4 |
| **C4** Faithfulness critic | `core/primitives/faithfulness.py` → `Distiller(critic=…)` (S6) | **NEW critic, existing seam** | primitives |
| **C5** Curator (flag-only) | `core/codex/curator.py` = Consolidator + Clusterer + curate, **applies nothing** | reuse (orchestration) | S4 |
| **C6** Curator apply | same module; reuse tag-governance confidence gate + active-learning confirm | reuse | S4 |
| **C7** Read surface | `perspectives` Lens/Map + a `codex` retrieve verb in `agent_cli` | reuse (S7) | S4/S5 |

**Net new files:** `embedder`, `clusterer`, `consolidator`, `faithfulness` (primitives) + `codex/{schema,
curate,curator}` (S4). Everything else is refactor/reuse. The Codex is a **new sibling of `narrative`** at S4,
sharing the primitive layer — not a new stack.

---

## 4. The two open questions, answered by the inventory

- **One tree or two?** → **Two projections over one substrate, sharing the machinery.** The spine indexes atoms
  by *time*, the Codex by *topic*; both run the same Consolidator, the same node-lifecycle, the same Lens/Map
  read. Separate trees, shared organs. (Unifying the *trees* would conflate "when" with "what about" — keep
  them distinct; unify the *engine*.)
- **Auto-apply vs flag line (C6)?** → reuse the tag-governance confidence gate verbatim: **auto-apply only
  ops at ~human/confirmed confidence** (near-duplicate dedup — embedding cosine above a high threshold);
  **flag everything semantic** (merges/splits that change meaning) via uncertainty sampling. The CRDT
  convergence proof we already have then covers the Curator too.

---

## 5. Routing, before vs after

```
BEFORE (parallel copies):                AFTER (shared seams):
 chronicler  ─┐                           chronicler ─┐
 consolidation┼─ each: group→rank→distill   curator   ─┼─► Consolidator(group_fn, distill, critic)
 (curator)   ─┘   (3 implementations)      consolidation┘        │
 router  ─embeds?─┐                                              ├─ Ranker(relevance_fn = Embedder)  [1 seam]
 themes  ─embeds?─┤  (would be 3 seams)     all rank/cluster ────┤
 clusterer─embeds?┘                                              ├─ node-lifecycle (Chapter + Resource) [1 model]
 supersede: bool  ┐                                              ├─ Distiller(critic = Faithfulness)   [1 gate]
 valid_to: edges  ┘  (2 retire models)      read ────────────────┘─ Lens + Map (Perspectives)         [1 surface]
 _epoch ×6        ───────────────────────►  timeutil.to_epoch                                          [1 time fn]
```

---

## 6. Revised sequencing

1. **S5 time unification** (prerequisite cleanup; tiny; enables staleness) —
2. **C0 Embedder** (the floor; ablation-gated routing win) →
3. **S1 extract Consolidator** (refactor chronicler + consolidation onto it; pure refactor, suite stays green) →
4. **C1 Clusterer** (subsumes themes) →
5. **C2 Resource + unified node-lifecycle** (fixes S4) →
6. **C4 Faithfulness critic** (into the Distiller seam) →
7. **C3 MDL decision** →
8. **C5 Curator flag-only** → **C6 apply** → **C7 read**.

Doing **S5 + S1 + S4** (the three unifications) early means every later slice is built on one engine, one
lifecycle, one time fn, one embedding seam — the connections get *simpler* as we add capability, not more
tangled. That is the optimization this pass was for.
