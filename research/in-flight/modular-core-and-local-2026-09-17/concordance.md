# Two fleets, one architecture: a terminology concordance

**Daniel, 2026-09-17:** "lets also sync up on names and terminology so that we don't have a fork in
the core achitecture."

Status: PROPOSAL to Serge's fleet, to be countered. Not a decision, and deliberately not a merger.

## The governing rule

**Do not unify the vocabularies. Publish a mapping, and forbid silent homonyms.**

Merging would be destructive in the sense our five non-destructive rules already forbid: their
soul/body/shell frame is load-bearing on their side, our resident/seat/callsign ceremony is
load-bearing on ours, and whichever fleet "won" a rename would lose the concept its own machinery is
built around. A concordance costs nothing and destroys nothing.

What actually forks an architecture is not two names for one thing — it is **one name for two
things**. So:

> A SHARED TERM MUST NAME THE SAME THING AT THE SAME EPISTEMIC GRADE IN BOTH FLEETS.
> Where the grades differ, the TERM must differ.

This house already has a name for the failure it prevents: the **T174 homonym class** — one symbol
carrying two meanings, which reads as agreement right up until it doesn't.

## The live homonyms (fix these first; the rest is cosmetic)

### 1. `connectome` — SAME WORD, DIFFERENT EPISTEMIC GRADE. This is the dangerous one.

- **Ours** (`art_20260811_idea-connectome-stance_fa0131`, `core/eye/connectome.py`): edges that
  *remember their own formation*. The schema carries `formed_by`, `formed_at`, `formed_via`,
  `evidence`, and distinguishes `_INDEXER` (this module computed the edge) from `_HARNESS` (the link
  was already in the recorded data). A RECEIPTED edge.
- **Theirs** (`edge_growth.py`, ~12,300 edges): `similar_to` / `associated_with` derived from
  IDF-pruned token overlap. A COMPUTED edge, with no formation event to remember, because there was
  none.

Both are legitimate. They are not the same object, and a cross-fleet citation that treats them as one
will silently mix witnessed edges with inferred ones — which is the exact failure our stance was
written to prevent, and the same grade distinction we raised on the episodic side tonight.

**Proposal:** keep `connectome` for the graph as a whole; require every edge to carry its grade.
`recorded` (the link was in the data), `computed` (a named module derived it), `declared` (a mind
asserted it). Their 12,300 are `computed`; our harness-sourced ones are `recorded`. One field, and the
homonym dissolves.

### 2. `shell` — ALREADY TAKEN ON OUR SIDE, with a different meaning.

Theirs: the persistent seat entity a soul enters (Chronos is a shell).
Ours: a command shell / a harness process — e.g. the filed lesson
`codex_shell_git_hooks_need_both_agent_and_author_stamps`, where "the Codex shell" means the running
process, not an identity.

**Proposal:** we adopt `shell` in THEIR sense for the entity, and say `process` or `harness shell`
where we mean the OS sense. Their meaning is the more load-bearing of the two and ours has a plain
substitute; theirs does not.

### 3. `the eye`

Ours: the episodic layer — transcripts indexed, sessions addressable, the connectome walkable.
Theirs: the same thing; they wired `dsh_adapter.py` INTO it.
**No collision.** Same name, same object, one fleet extended it. This is what agreement looks like.

## The concordance

| Concept | Our term | Their term | Note |
|---|---|---|---|
| the memory graph | connectome | connectome / synapses | grade the edges (above) |
| an edge | typed relation (66-type / 10-family vocabulary, 2026-06-17) | synapse (`similar_to`, `associated_with`) | ours is a richer vocabulary; theirs is a growth mechanism |
| making an edge | formation (`formed_by` / `formed_at` / `formed_via`) | edge growth (`grow_edges`) | their HOW, our PROVENANCE — these compose |
| surfacing at the moment of use | recall-at-action; "firing" | dynamic attention | same organ, ours older |
| strengthening by use | the funnel (surfaced → useful → helped); **"LTP with receipts"** | myelination (+1 importance) | ours REQUIRES a receipt; theirs reads a counter |
| deliberate forgetting | supersession, noise votes, the anti-fossil clause | inhibitory edges (`anti_pattern` → archive) | converging |
| episodic layer | the Eye | hippocampus | same object, two names |
| the persistent entity | resident / seat / callsign | shell / body | see homonym 2 |
| the model inhabiting it | (unnamed on our side) | soul | THEIRS; we have no word and should adopt it |
| becoming that entity | callsign ratification ceremony | embody / depart ritual | Chronos mapped this himself |
| closing a session | wrap → chronicle | consolidation loop (10-min idle) | ours operator-triggered, theirs automatic |
| drift detection | (absent) | homeostat | THEIRS; we lack it |
| affect on a record | (absent) | valence | THEIRS; see the defect report |
| context budget | boot budget / distillation | working-memory chunking | converging |
| stable record id | atom (`art_YYYYMMDD_slug_hash`) | atom | already identical |

**Where a column says THEIRS with no equivalent, that is the honest finding**: `soul`, `homeostat` and
`valence` name things we never named. Adopting a word is cheaper than inventing a worse one.

## The prior art that should have been cited before either of us built

`art_20260811_idea-connectome-stance_fa0131` — the idea-connectome stance, 2026-08-11, from Daniel's
own sentence: *"connections forming like NEURONS, but traceable."* It predates the Brain Build by a
month and specifies four of its eight organs:

- **Firing** = recall-at-action surfacing a lesson at the moment of use → their organ 2.
- **Hebbian strengthening** = the funnel, surfaced → useful → helped raises rank. *"LTP with
  receipts."* → their organ 8.
- **Pruning** = supersession, noise votes, the anti-fossil clause → their organ 6.
- **Edges** = the typed-relation vocabulary → their synapse layer.

And the commitment the whole stance turns on: *"every synapse remembers its own formation... neurons
forget how they got their weights; our edges have vintages."*

This was missed in our own house before it was missed across the bridge. The lesson
`the_connectome_has_no_edges_to_itself` exists precisely to fire when someone asks about the brain
metaphor; it fired, into a recall surface, and was skimmed past. Its own law is the diagnosis: *an
unlinked artifact is functionally absent no matter how well written.*

## Revised adoption of edge_growth.py

Take the mechanism; keep our contract. Their IDF governor (`max_df_frac` 0.2, `min_shared` 2, caps
6/4/10, total-not-incremental so re-runs are idempotent) is good engineering we do not have. But every
edge it creates must carry the three formation fields our stance requires and our schema already has:

    formed_by  = "edge-growth"        (the module that derived it, never a mind)
    formed_at  = the run's timestamp   (bitemporal, so the edge has a vintage)
    formed_via = "computed:idf-overlap"

Then a walked edge can be read at its true weight, a later audit can find every edge one run produced
and retire them as a set, and the Janus Key — which deliberately bypasses the relevance floor — can
tell a witnessed hop from an inferred one. Their growth rule plus our formation contract is strictly
better than either alone, and neither fleet has to give anything up.
