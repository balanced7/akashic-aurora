# Retention Tiers, Safe Flush, and Decompression — opening position

**Status:** OPENING POSITION (not ruled; for house counter)
**Author:** Navi (kimi), from Daniil's 2026-09-23 directive
**Minted:** 2026-09-23/24
**Supersedes:** the heatmap/find/relational thread — this is the frame those three fall out of

## The directive (verbatim)

> "Eventually we will need to think of an architecture that will allow us to retain dense
> and important information and periodically safely flush things... we can have a mechanism
> for archiving things because words are compressable, if we can somehow through clever
> engineering achieve fast recall and decompression that could be useful."

## What this actually asks for

Three coupled things, none of which exist as a single mechanism today:

1. **Retention tiers** — a space where "dense and important" information stays *hot* (fast
   recall) while everything else is allowed to go *cold* (compressed, slower, but never gone).
2. **A safe flush cadence** — periodic, *provable* promotion/demotion between tiers, so the
   hot surface stays bounded (context budgets, lane depths, token cost) without silently
   losing the cold body.
3. **Decompression** — a proven path from cold/compressed back to verbatim on demand. This is
   the acceptance test: can an agent, a month later, recover the *exact* sentence whose
   conversation left no hot trace?

## The house already has the two poles; it lacks the shuttle

This is not greenfield. Two halves exist and are battle-tested:

- **The LOSSY pole = the recall funnel** (walked with Vandor 2026-09-23): silence gate →
  stop-list → relevance floor → anti-repeat → faithfulness gate → **cap-3 skeleton render**
  ("skeleton-first, lossy summary + lossless source pointer", N-of-M legend, pull door).
  This *is* "retain dense, advertise cheap": it keeps the shape and a pointer, not the body.
- **The LOSSLESS pole = blob + pyramid**: `blob:<sha>` for spilled payloads (`bifrost-fetch`),
  and the Eye's L4→L0 descent (era → session → exchange → event). Verbatum is never unreachable;
  it is one resolution away.

**What is missing: the shuttle.** We compress ON READ (the funnel renders lossy by default) but
we never EXPIRE ON WRITE. Consequences, measured live this week:

- trace lanes sit at `trace=5000` on every seat (`bifrost_dashboard`).
- `state/coord/corpus_reads.jsonl` grows unbounded (every find/search logged).
- `state/eye/eye.db` grows with every ingest.
- No tier models "cold archive" as a first-class state — things are hot or absent, never "cooled."

## The load-bearing axiom (the thing to challenge)

> **"Safe flush" must mean COOL THE PROJECTION, never DELETE THE SOURCE.**

The house's founding contract is append-only, never rewrite the substrate, "deleting [a
projection] loses nothing *because it is regenerable.*" A flush that deletes verbatim source is
the ONE operation that breaks that contract. So the architecture is:

- **Keep the append-only source forever** (ledger, transcripts, blobs, event firehose).
- **Make the HOT PROJECTION sparse** — flush/rebuild the *index, cache, ranking surface*, never
  the *ledger*.
- **Compression = the retrieval surface gets lossy (skeleton), not the source.**

Then "fast recall + decompression" is: hot recall serves the skeleton; the pointer resolves the
verbatim body from the (always-retained) source. Flush is *cooling*, and "safe" is proven by the
fact that nothing was ever deleted — only re-indexed.

## The fork for the house (open questions)

1. **Is lossy deletion ever right?** If a compressor *provably* reconstructs the source (a
   mathematical round-trip, not an LLM paraphrase), could we delete the verbatim cold body and
   rely on decompression alone? Navi's position: the proof bar is unreachably high (LLM
   summary/paraphrase is NOT round-trip; only e.g. zstd/gzip over bytes is, and that's just
   storage, not a tier model). But the counter is welcome.
2. **Does the recall funnel already imply the tier model?** Its surface/bench/archive
   distinction may already BE the tiers, unnamed. If so, the work is to *name and instrument*
   them (promotion = credit, demotion = bench), not to invent a new mechanism.
3. **Is "heat" the selection signal?** Daniil's heatmap instinct (recency, tool-call frequency)
   is really asking: *what deserves to stay hot?* Heat = recency-decayed frequency × cost-weight
   is the natural selector for the hot tier — so "heatmap" is not a visualization feature, it is
   the *demotion/promotion criterion*.

## Acceptance (pre-registered, Vandor-style kill-drill)

The mechanism is proven the day this holds:

> An agent, one month after a conversation, can recover the *exact* text of a sentence from it —
> including one whose conversation currently leaves **zero** durable trace (cf. 2026-09-23's
> vanished Discord exchange) — via one resolution, in bounded time, without having kept the whole
> conversation hot for the intervening month.

If the mechanism passes that, flush was cooling and the contract held. If it fails, we flushed the
wrong thing.

## Relationship to the find / heatmap / relational thread

- `find` (Search Everything) = *location* — the band-aid that locates what got lost.
- The **retention architecture** = the *cure* — stop losing it in the first place.
- `find` and this note answer different questions; the bridge between them (path ↔ indexed session)
  is the join that would have made tonight's lost file recoverable *even through the wrong worktree*.

## Next step

Escalate to a design atom with a fence (opening position + counter + sunset) once the house weighs
in on the fork above — OR fold into the recall-funnel cadence work if that is where tiers already
half-live.
