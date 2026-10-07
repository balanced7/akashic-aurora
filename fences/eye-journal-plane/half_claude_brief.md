# Fence brief — how should a transcript's ADDRESS be derived?

**Opened** 2026-10-07 by Vandor (claude seat), overnight, against Daniel's standing instruction:

> "See if you can't continue working on making our best knowledge reach us when we need it or at
> least be easy to find. Perhaps we need to run some kind of index on our transcripts and atoms so
> that we know what we have and where its supposed to live and start making our library more
> organized"

This is a **design fence**, not a census. The mechanical halves (a found-vs-taken counter, a parser
for the journal record shape) I am building regardless; they have no contested choice in them. The
contested choice is below, and the house rule is that it is not mine to settle alone.

---

## The measured situation

`core/eye/index.py:session_id_for(path)` answers "what session does this transcript belong to?". The
answer becomes the event address: `event_id = "<session>:<line>"`.

It resolves a file's **stem**, unless that stem appears in a hand-written set:

```python
_GENERIC_TRANSCRIPT_STEMS = {"session", "transcript", "conversation", "chat"}
```

for which it falls back to the parent directory name. Its own docstring explains why the set exists
(T406): DSH names all 25 of its transcripts `session.jsonl.zstd`, `.stem` is constant for every one,
and — quoting it — *"The damage of getting this wrong is not a missing session, it is LOST EVENTS."*

**What I measured tonight, all [CERTAIN] from my own commands:**

| fact | number |
|---|---|
| workflow journals at `<session>/subagents/workflows/wf_*/journal.jsonl` | **90** |
| distinct ids `session_id_for` gives them | **1** (`"journal"`, ninety times) |
| distinct ids their parent directory names would give | **90** |
| files silently discarded by `_take()`'s `seen` dedup | **89** |
| agent `result` records inside them | **870**, 0 null/empty |
| returned verdict text | **13.12 MB**, spanning 2026-08-01 → 2026-10-07, still growing |
| rows those journals contributed to `events` | **0** |
| what `eye ingest` reports | `1515/1515 files \| 55,470 events \| unparsed 0` |

The one journal that survived dedup is recorded in `ingest_state` with `lines=26` and produced zero
events, because a journal record is `{type, key, agentId, result}` and the parser reads
`user`/`assistant`. It parsed cleanly and meant nothing, which `unparsed 0` cannot express.

So: 870 agent verdicts — the most expensive knowledge this house produces, the record of what each
fanned-out agent *concluded* — are unsearchable, and every instrument involved reports healthy.

## Why I am fencing rather than just patching

The obvious patch is `_GENERIC_TRANSCRIPT_STEMS.add("journal")`. That is the move that produced this
bug: the set is four names someone had already been bitten by, and it cannot know the fifth. The
house has a standing finding against exactly this shape, in `core/trust/private_plane.py`:

> MARKERS ARE DERIVED, NEVER DECLARED ... A hand-maintained denylist rots the moment someone adds a
> file.

So I want genericness **derived**. And the moment I write that down, it collides with something real.

## The collision

Deriving genericness means observing the corpus: *a stem claimed by several files in several
directories is generic.* But the address is a **primary key over 55,470 already-indexed rows**. If a
stem is unique today and a second file with that stem appears tomorrow, the derivation changes that
session's address — and `INSERT OR IGNORE` will not tell anyone. A derived key that can move is a
worse failure than a declared key that rots, because rot is visible in a diff and silent re-keying
is not.

My current inclination, stated so you can attack it rather than guess at it:

> Derive genericness from the corpus, but make it **monotone** — once a stem has ever been observed
> as generic, it stays generic, persisted in the eye's `meta` table. The hand-written four become a
> historical seed rather than the mechanism. Genericness only ever accumulates, so an address can
> change at most once, in the direction of becoming more specific, and that change is recorded.

I am not confident in it. Three things bother me: the first-ever ingest of a colliding plane still
mis-keys one file before the collision is observed; "monotone" means a one-time typo'd filename
poisons a stem forever; and persisting derived schema in `meta` makes the db's interpretation
depend on its own history, which is the kind of thing that is miserable to debug two months later.

## The calibrated question

**Is an address that is derived from the corpus the right primitive here at all — or is the correct
answer that a transcript's address should be derived from its PATH POSITION (structural, knowable
from one file, no corpus and no history), with genericness never needing to be decided?**

If you think it is position, say what the position rule is, precisely enough to implement, and what
it does to the 55,470 rows already keyed the old way. If you think it is corpus-derived, attack the
monotone scheme on its three weak points above. If you think the denylist is actually correct and I
am over-engineering a four-element set, say that plainly — it is a real possibility and I would
rather be told than ship a mechanism nobody needed.

## Constraints any answer has to respect

1. `event_id = "<session>:<line>"`. 55,470 rows exist. Re-keying is not free and must be stated.
2. A UUID-stemmed Claude Code transcript must keep resolving to itself (ratcheted in
   `tests/test_the_eye_does_not_silently_discard_a_plane.py`).
3. DSH's 25 `session.jsonl.zstd` must keep resolving by directory (same file).
4. `is_subagent` provenance is stamped from the path and must survive whatever you propose.
5. Whatever reports coverage must distinguish **found** from **taken**. That half is not in dispute.

## What I have already pinned (RED, commit 0329e32a)

`tests/test_the_eye_does_not_silently_discard_a_plane.py` — 5 RED, 3 ratchets green. The pins assert
the collision, the derivation requirement, the found-vs-taken counter, the "parsed but yielded
nothing" honesty gap, and reachability of all 90 journals. They are deliberately phrased so a
position-based answer and a corpus-based answer can both satisfy them.
