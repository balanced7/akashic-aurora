# Perspectives & Maps over a stable substrate — design note (idea, not yet built)

Status: historical  (2026-07-09, P4: Future idea; not yet built)

> Status: IDEA / future capability. Captured 2026-06-27. Build only when there's a real
> need AND the narrative graph has accreted real edges (rule of three). This is the
> *telos* of the knowledge architecture, not a current slice.

## The principle (the user's idea, sharpened)

**Keep the raw substrate sacred and immutable; make interpretation a swappable,
upgradeable layer.** As we upgrade the interpretation, the *same* stored information
yields more value — the data stays safe, the general shape remains, but what we *get*
from it compounds. This is **schema-on-read + "lenses"** applied to an agent's living memory.

## Three layers

| Layer | What it is | Swappable? | Prior-art name |
|---|---|---|---|
| **Substrate** | raw beats / edges / Ledger — never mutated, append-only, lossless | no (sacred) | data lake / source |
| **Map** | a *structural* projection: which relations form the graph you traverse (causal map, dependency map, learning-path map, narrative map) | yes, versioned | view / lens `get` / read-schema |
| **Perspective** | a *value-set* tuning emphasis within a map (factor weights, personalization seed, which relationship-types matter) | yes, tuneable | conceptual-space weights / PageRank personalization |

A **Map** says *how the territory is wired*; a **Perspective** says *what matters on it*.
Swap either independently over the immutable Substrate → a new output. Plus a dynamic:

- **Reinforcement** — edges/nodes carry strength + activation that grow with co-use and
  **decay** without it (ACT-R base-level + Hebbian). Maps shaped by *experience*.
- **Spreading-activation recall** — given a focus + a perspective, light up associated
  knowledge along the strongest paths (associative, beyond keyword/embedding similarity).

## Why it compounds (grounded — and honestly bounded)

1. **Data appreciates** (data-centric AI): re-embedding / re-indexing with a better model
   extracts more from the *same* data; a new Map applies **retroactively to all history**.
2. **Combinatorial leverage**: N maps × M perspectives over one substrate = many derived
   views, each potentially valuable.
3. **Reconstructive memory** (Bartlett 1932): humans reconstruct memories at recall through
   their *current* schemas, drawing new meaning from old experience — we'd mimic this by
   re-projecting old beats through new maps.

**Honest bound:** superlinear *leverage*, not literal exponential magic. The substrate's
information content caps the ceiling; diminishing returns apply; and reconstruction can
**distort** (Bartlett: assimilation / leveling / sharpening). A perspective is a lens *and*
a bias. Substrate quality is the real foundation; perspectives multiply value, never
manufacture it.

## Safety guarantees (so "the data stays safe, the shape remains")

- **Lens laws** (Foster et al. — bidirectional transformations): a well-behaved view
  satisfies round-tripping (`GetPut`, `PutGet`) so a view can **never silently corrupt the
  source**. → Maps/Perspectives are read-projections; edits to a view propagate back only
  through a checked `put`, or not at all.
- **Faithfulness** = our existing source-pointer rule: every projected claim resolves to a
  substrate source. No fabrication. (Lens law, restated in our terms.)
- **Immutable substrate** = our Ledger (append-only, raw never deleted) — already enforced.
- **Reinforcement needs decay + novelty** or it ossifies (rich-get-richer / echo chamber);
  ACT-R power-law forgetting + occasional exploration are the guards. The fan effect warns
  against over-linking (too many associations dilute).

## Has it been built? Pieces yes; the synthesis no

- **Built & at scale:** data lakes / lakehouses (schema-on-read), **semantic/metrics layers**
  (dbt, Cube, LookML), materialized views, lens libraries (Haskell `lens`, Boomerang),
  GraphRAG (re-runnable multi-resolution maps), data-centric re-embedding pipelines.
- **2026 agent frontier reaching toward it:** GAAMA / HeLa-Mem (reinforced graph memory),
  HippoRAG (PageRank recall), multi-view KGs, Amory / AriGraph (narrative memory).
- **Our niche (novel synthesis):** schema-on-read + safe lenses + a *reinforced narrative
  graph* + first-class *swappable Maps/Perspectives*, serving an agent's living memory.
  The planks are proven; assembling them for agent knowledge is new.

## How it fits what we already have

- **Substrate = the Ledger** (append-only, lossless). ✓ already
- **First Map = the narrative graph** (relationship-typed edges) being built in the slices.
- **Perspective seam = the Ranker** (already parameterizable: relevance × importance ×
  recency × relationship-type). A Perspective = a Ranker config + a PageRank seed.
- **Themes / Tracks = built-in maps/perspectives** (thematic facet, domain facet).
- **Lens laws = our faithfulness gate.**

## Minimal first version (when earned, rule of three)

Once the narrative graph has real edges and a concrete need:
1. add **edge strength + node activation** with decay (reinforcement) to the schema;
2. define **2–3 concrete Maps** (causal, dependency/learning-path, thematic) + **a couple of
   Perspectives** (Ranker configs) — not a config sea;
3. add a **`relate(focus, perspective)`** spreading-activation / Personalized-PageRank call;
4. keep every projection faithful (source-pointer) and the substrate untouched.

## Prior-art sources

Conceptual Spaces (Gärdenfors); Faceted classification (Ranganathan PMEST); Spreading
activation + ACT-R (Anderson); Hebbian / HeLa-Mem; GAAMA; Personalized PageRank / HippoRAG;
Schema-on-read (data lakes); Bidirectional transformations / lenses (Foster et al.);
Data-centric AI; Reconstructive memory (Bartlett). (URLs in the session research learnings:
`py agent_cli.py recall perspectives` / `recall analogues`.)
