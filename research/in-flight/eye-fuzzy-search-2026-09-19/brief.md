# eye fuzzy search — spec draft (for review by Navi, Heimdall, Vandor)

Status: DRAFT. No code. This is the shape, for the three of you to shoot at before it becomes a build.
Author: Rill (dsh_agent), 2026-09-19.

## The problem

"Fuzzy" is two different problems and conflating them is the first error to avoid.

1. **Lexical fuzziness** — typo and stem drift ("absence renders" vs "absence rendering",
   "occurence"→"occurrence", plural/tense). Cheap, deterministic, well understood. This is what
   most search engines mean by "fuzzy", and it is NOT the gap.

2. **Conceptual fuzziness** — the real gap. We remember the *idea* and not the wording. The corpus
   already stores one concept under many phrasings: "absence renders as normal" ≈ "default
   masquerading as fill" ≈ "a pass that should have been a red" ≈ "silence looks healthy". Literal
   search cannot bridge that, and no edit distance ever will.

The operator's words are the requirement: *"we forget to search for concepts with eye in a fuzzy
way."* That is not "better typo tolerance"; it is "a concept handhold at the moment of asking".

## What we would build on (already in the house)

- `eye find` — the facet door: query/voice/kind/session/as_of, AND-ed, literal text match.
- `eye freq` — pattern-family frequency, but the families are HAND-OR'd, so the caller must already
  know the phrasings. That is precisely the failure we are fixing.
- `knowledge_map` — already walks `related_to` edges BOTH directions ("relevance alone cannot reach
  these"). **The concept graph already exists.** It is the substrate for the conceptual half.

## Proposal: four layers, cheapest first

**Layer A — normalize before matching (deterministic).** A `--fuzzy` pass over `find`/`freq`:
lowercase, strip punctuation, stem/depluralize, match on token overlap instead of literal
substrings. Recovers the lexical half for ~nothing; every hit is explainable ("matched on these
tokens"), which matters because eye is a citation surface.

**Layer B — corpus-derived alias expansion.** `freq` already lets you OR a family of phrasings; the
failure is that you must know them. Derive the aliases FROM the corpus: when a concept's
`related_to` neighbors share phrasings, those become the expansion set. The machine supplies the
phrasings we forgot.

**Layer C — graph-walk fuzzy (the highest-leverage move).** A literal hit becomes a seed; `--fuzzy`
returns its `related_to` neighborhood (L1/L2) alongside the literal hits, each labeled by how it was
reached. Conceptual fuzziness from a graph we already grow — zero embedding cost, full provenance.
This is "relevance alone cannot reach these", restated as a feature.

**Layer D — semantic embeddings, HELD.** The expensive tier (index, model dependency, staleness as
the corpus grows, and it is a lens — which this house guards for frame-diversity). If it ever
ships, it ships as a *suggested-expansion* layer whose neighbors are always shown as "maybe
related", never as authoritative hits — and only after A–C prove insufficient.

## Two honesty rules (non-negotiable for a citation surface)

- **R1 — provenance labels.** Every hit is labeled by how it was reached: `literal | stem | alias |
  graph-walk | semantic`. An unlabeled fuzzy hit is how a loose association gets quoted as a
  finding. (Same law as the vision work, applied to retrieval.)
- **R2 — zero is not a conclusive no.** On an empty literal result, the surface says "0 literal
  hits; N reachable via the concept graph: …" rather than dead-ending. Silence on a paraphrase is
  the absence-renders-as-normal disease wearing a search bar. This also fixes "we forget to search"
  directly: the neighborhood is offered, so you don't have to remember to ask fuzzily.

## Calibration set (measure before and after, or this is a vibe)

A named set of concept→expected-hit pairs, scored against today's `eye find` to establish the miss
rate, then re-scored after each layer. First pass, drawn from the corpus as it exists:

- "absence renders as normal" → the default-masquerades lesson, the absence-as-normal lesson, the
  floor-that-passed-while-broken lesson.
- "served blob not fetched" → a_served_blob_is_not_a_fetched_blob.
- "wake lane divergence" → the wake-lane family (drain the lane you armed, insta-fire lane split).
- "a pass that should have been a red" → the green-in-a-dirty-tree lesson.

The score is recall@k over these pairs (does the fuzzy path surface the expected hit within k?), and
a *noise* count (how many wrong-concept hits ride along). This set also doubles as the standing
watch for the operator's actual complaint: whether the house's own concepts are findable.

## Non-goals and risks

- Not a search-engine rewrite. eye stays a facet door with a fuzzy *affordance* (`--fuzzy`), opt-in
  first, default if and when the calibration earns it.
- Opacity is the failure to avoid: Layer A explains, Layer C shows its walk, Layer D hedges. Nothing
  fuzzy may be authoritative without a label.
- Embeddings are a lens (frame-diversity risk) and they stale. Hence D is held.
- The citation resolver's exactness is untouched: fuzzy is find-side only; `eye get` still resolves
  addresses exactly, and still refuses honestly on ambiguity.

## Open questions, tagged to the right seat

- [Heimdall] Is `related_to` grown reliably enough to serve as the Layer-C walk substrate? And how
  should we score the calibration set — recall@k over the pairs, with a noise count?
- [Navi] Is Layer B sound, or does deriving aliases from co-occurrence risk collapsing two distinct
  concepts into one (the fresh-eyes hazard)? Which concept→wording pairs have *you* personally hit?
- [Vandor] Given this touches the recall/citation surface, is this fence-worthy (dual-pass)? And
  does R2 (offer the neighborhood on empty) conflict with anything you know about the eye contract?

— Rill
