# Perspectives & Maps — build plan (the interpretation layer over the narrative graph)

> Status: PLAN (plan-first, build-in-slices, each gated by an acceptance bar — same
> discipline as `docs/narrative-spine-plan.md` + `docs/narrative-test-plan.md`).
> Builds on the idea captured in `docs/perspectives-maps-design-note.md`. Now buildable
> because the narrative spine (Slices 0–8) gives us a real substrate of beats + typed
> edges to put lenses over. **The substrate stays sacred; this layer is swappable.**

## 1. What already exists (we build on, never mutate)

- **Substrate** — the **Ledger** (raw events via the autologger) + **beats / chapters /
  tracks / themes** with **relationship-typed edges**. Immutable, append-only, lossless. ✓
- **The Perspective seam** — the **Ranker** is already parameterized (relevance × importance
  × recency × relationship-type). A Perspective is just a *named weighting* of it.
- **Bi-temporal fields** — `last_used`/validity already on the schema → the hook for decay.
- **Faithfulness gate** — every projection must resolve to a substrate source (= lens laws).

So this layer is mostly *parameterization + a little new state*, not a new subsystem.

## 2. The model (three knobs over one substrate)

| Concept | What it is | Mechanism |
|---|---|---|
| **Map** | a *structural* projection: which relations/node-types form the graph you traverse (narrative map, causal map, dependency/learning-path map) | a sub-graph selector over the typed edges |
| **Perspective (Lens)** | a *value-set* tuning emphasis: factor weights + a personalization seed + which relations matter | a Ranker config + a PageRank seed |
| **Reinforcement** | edges/nodes that *strengthen with co-use and decay without it* — the map learns from experience | Hebbian edge strength + ACT-R base-level activation |
| **Spreading-activation recall** | `relate(focus, lens)` lights up associated knowledge along the strongest paths | Personalized-PageRank / weighted walk |

A **Map** says *how the territory is wired*; a **Perspective** says *what matters on it*.
Swap either over the immutable substrate → a different surfaced view. Reinforcement makes
the substrate's edge-weights a living, experience-shaped thing (without changing the facts).

## 3. Schema additions (small, on the existing nodes/edges)

- **Edge** gains `strength: float = 1.0`, `count: int = 0`, `last_used: iso` (reinforcement).
- **Node** (beat/chapter) gains `activation: float` (base-level: frequency + recency, decayed).
- **Lens** (`core/perspectives/lens.py`): `{name, factor_weights, relation_weights, seed,
  goal}` — a pure config; reuses `Ranker`.
- **Map** (`core/perspectives/maps.py`): `{name, relation_domains[], node_kinds[],
  direction}` — selects a sub-graph of the substrate. Named + versioned.
- Storage: `persp:lens:<name>`, `persp:map:<name>`; edge strength lives on the edge record.

## 4. Slices (each independently testable, leaves the suite green)

- **P0 — schema + lexicon.** Lens, Map, reinforced Edge/Node fields; lexicon entries. No
  behavior. **Bar:** round-trip + validation (Lens reuses real relationship-type names).
- **P1 — reinforcement.** Hebbian edge-strength bump on co-activation (bounded, sigmoid) +
  ACT-R **power-law decay**; node base-level activation. Hook: when beats co-surface (same
  chapter, same retrieval), bump their connecting edge. **Bar:** on a fixture, repeated
  co-activation strengthens the *right* edges; decay lowers stale ones; **strength is
  bounded (no runaway)**; deterministic with a fixed clock.
- **P2 — Lens / Perspective.** `view(map, lens, focus=None)` → a re-ranked, faithful
  projection. Ship **2–3 concrete lenses** (causal-why, recency, thematic) — not a config
  sea. **Bar:** different lenses produce **measurably different orderings** (a *lens-
  divergence* metric ≥ threshold) AND every view is **100% faithful** (source-resolved).
- **P3 — Maps.** **2–3 concrete maps** (narrative = current; causal = causal edges only;
  dependency/learning-path). **Bar:** each map is a valid sub-graph of the substrate (every
  edge a real typed edge); traversal works; maps are swappable without touching data.
- **P4 — spreading-activation recall.** `relate(focus, lens)` = Personalized-PageRank /
  weighted walk over the reinforced graph. **Bar:** precision@k vs **gold associations** on
  a fixture, and it **beats a keyword/embedding baseline** (ablation — earns its complexity).
- **P5 — agent verb.** ONE new verb: `py agent_cli.py relate <focus> [--lens X] [--map Y]
  [--json]` (ACI: tiny surface). **Bar:** budgeted output, faithful, errors-that-teach.
- **P6 — anti-ossification guards + eval.** Decay + **novelty/exploration** (occasionally
  surface weak/distant links). **Bar (the important one):** after N reinforcement cycles,
  recall **diversity/entropy stays above a floor** — the map must NOT collapse into a rich-
  get-richer echo chamber. Plus the standing `test_perspectives.py` running all bars.

## 5. Reuse vs. new

| Reuse (built) | New (this plan) |
|---|---|
| Ledger + beats/edges/relationship_types (substrate) | reinforced Edge/Node fields + decay |
| **Ranker** (the Perspective seam) | Lens config + `view()` |
| Distiller (faithful view summaries) | Map selector + 2–3 concrete maps |
| bi-temporal `last_used` (decay hook) | spreading-activation / Personalized-PageRank |
| faithfulness gate (= lens laws) | `relate` verb + `test_perspectives.py` |

## 6. Acceptance metrics (benchmark-grounded, per the test-plan discipline)

| Slice | Metric | Field it comes from |
|---|---|---|
| P1 reinforcement | bounded-strength + correct decay + co-activation precision | ACT-R / Hebbian |
| P2 lenses | lens-divergence (views differ) + 100% faithfulness | conceptual spaces / lens laws |
| P3 maps | sub-graph validity (every edge real) | multi-view KG |
| P4 recall | precision@k vs gold; **beats baseline (ablation)** | Personalized-PageRank / HippoRAG |
| P6 anti-ossification | diversity/entropy floor over N cycles | ACT-R forgetting / exploration |

## 7. The honest bounds (carried from the research)

- **Ossification is the real risk** — Hebbian reinforcement is rich-get-richer. Decay +
  novelty are **mandatory** (their own slice + bar), not optional polish.
- **"Exponential" is leverage, not magic** — the substrate's information content caps the
  ceiling; perspectives multiply value, never manufacture it.
- **Perspectives are value-laden** — a lens is a bias (Bartlett: assimilation/leveling/
  sharpening). Lenses must be **explicit and inspectable**, not hidden defaults.
- **Lens laws** (Foster `GetPut`/`PutGet`) — views are **read-only projections**; the only
  write-back is bounded, decayed reinforcement. A view can **never corrupt the substrate**.
- **Rule of three** — build P1 + *one* lens + *one* map first; expand only with real use.

## 8. Prior art

schema-on-read / data lakes; Foster bidirectional **lenses** (+ laws); **conceptual spaces**
(Gärdenfors, weighted dimensions); **ACT-R** (base-level + decay + spreading activation);
Hebbian / **HeLa-Mem**, **GAAMA**; **Personalized PageRank** / HippoRAG; faceted classification
(Ranganathan); data-centric AI; **reconstructive memory** (Bartlett). (URLs in the research
learnings: `py agent_cli.py recall perspectives`.)

## 9. Suggested first move

**P0 + P1** (schema + reinforcement) — small, no ML, and it's the piece nothing else has:
edges that *learn from co-use* turn our static typed graph into a living map. Everything
else (lenses, maps, recall) is parameterization on top, behind the Ranker seam we already built.
