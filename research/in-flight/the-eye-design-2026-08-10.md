# THE EYE — making the transcript plane queryable

Design for T278. claude (Vandor), 2026-08-10. Everything below is verified rather than
assumed; where something is unverified it says so.

---

## 1. Daniil's specification, verbatim

Recovered from session transcripts on 2026-08-10, after the repo planes returned a false
negative. He said this on **2026-07-31**, and again in restated form on **2026-08-10**.

> "…[you shouldn't] have to seach files, I want you to be able to **search redis and get a
> representation of the items referenced within. a realtime eye that you can quyery and
> understand your position and vision on multiple axees at once with ways of pinging and
> navigating quickly**"

And the constraint, stated in the same conversation, unprompted:

> "**I want the eye to have its own cursor, we can't have lookups breaking core system
> logic**"

Restated 2026-08-10, after seeing priori.sh:

> "I want all of our transcripts to be quereable in useful ways with **frequency, who was
> there, what is ambiant related knowledge**. Make this be useful and useable **for you**."

That last clause is the design constraint and not a pleasantry: **the consumer is the fleet,
not a browsing human.** This is a door returning structured results, not a UI.

---

## 2. Why this is urgent: it has already cost us twice, in one evening

On 2026-08-10 two separate directives were found to have been specified, quoted back later as
standing policy, and never built — because nothing in the repo could find them.

| directive | said | re-quoted as policy | built |
|---|---|---|---|
| Research cadence — "we keep finding gold when we do this but we rarely do it, so I want a full comprehensive suite so we can actually start making informed decisions instead of stepping on every rake as it comes along" | 2026-07-26 | 2026-08-01 | **no** |
| THE EYE — the quote in §1 | 2026-07-31 | 2026-08-01, scored **3×** in a prioritisation pass | **no** |

Recovering them cost **eight guessed substring searches**. Before that, four parallel
searches across the ledger, lesson corpus, notes, chronicles, git history and library atoms
returned a **confident, wrong negative** — I was about to record "this conversation does not
exist."

**The transcript plane is the one input class the fleet cannot read, and it is where the
founder actually speaks.** `check_verbatim_citation` blocks a ship whose *decision* rests on
evidence living only in a chat scroll; there is no equivalent for *directives*. So the
highest-authority input has the weakest durability, which is exactly backwards.

**The Eye is the fix for the precise failure that keeps burying the request for it.**

---

## 3. Feasibility — verified, not assumed

```
~/.claude/projects/<project-slug>/*.jsonl
480 files · 440 MB
```

Record schema, sampled from the largest file (5,108 records):

| field | use |
|---|---|
| `type` | user · assistant · system · **queue-operation** · attachment · last-prompt · custom-title · mode |
| `timestamp` | temporal anchoring; as-of queries |
| `sessionId`, `uuid`, `parentUuid` | threading — "what was around it" is a traversal, not a re-search |
| `cwd`, `gitBranch` | **ambient context, already present** — what he was working on when he said it |
| `message.role` / `message.content` | the utterance |
| `version`, `entrypoint`, `userType` | provenance |

**Everything Daniil asked for is already in the data.** Nothing needs to be inferred.

---

## 4. THE TRAP — his speech hides in `queue-operation` records

This is the finding that separates a working ingest from a silently broken one.

```json
{"type":"queue-operation","operation":"enqueue","timestamp":"2026-08-02T02:32:01.968Z",
 "sessionId":"…","content":"whole claude code crashed again and didn't let me launch it
 without re-installing it"}
```

A `queue-operation` with `operation: "enqueue"` carries a `content` field holding **what
Daniil typed while a turn was already running** — his mid-turn interjections. He makes them
constantly (three times in the session that produced this design).

**These are NOT `type: "user"` records.** An ingest reading only `type: user` silently drops
every interruption he has ever made — and interruptions are disproportionately *corrections*,
which are the highest-value utterances in the corpus.

The corpus already warned about this in
`learn:experiment:operator_speech_hides_in_queue_operation_records`, and I nearly built it
wrong regardless. **Pin this case.**

---

## 5. Reference design: priori.sh

████████████'s shipped product (seen 2026-08-10). Tagline: *"what was knowable, when."*
Point-in-time queries over EDGAR filings, ALFRED vintages and Fed communications; BLAKE3
content hashes; sealed extraction locks; thirteen normalised sources; Live / Replay /
sealed-Pack modes.

**Its query surface is a typed facet dropdown:**

```
Source        data source
Entity        entity name
Type          structural or signal
Relationship  relationship
Exact phrase  exact phrase        <- LAST. The fallback.
```

…with an **as-of control beside the search box** (not in advanced filters), and stable
per-observation URLs (`#observation/<uuid>`) so any fact is addressable and linkable.

**There is no semantic-search facet at all.**

### The lesson, which corrected my first design

**Queryable means having DIMENSIONS, not having embeddings.** Grep has one dimension: the
string. Queryable means slicing by *who*, *what kind*, *related to what*, *as of when* — and
falling back to phrase only when the structured query fails.

### What we already store vs what we expose

| priori facet | we already hold | exposed as a query dimension? |
|---|---|---|
| Source | `agent_id` on every lesson, note, commit | **no** |
| Entity | task ids, file paths, atom ids | **no** |
| Type | atom types, message kinds, lesson categories | **no** |
| Relationship | `replaces`, `related_to`, `enforced_by` edges | **no** |
| as-of | bitemporal `valid_from` / `valid_to` / `recorded_at` | **no — built, one subsystem only** |
| Exact phrase | token matching | **the only one we have** |

**Five of six dimensions already stored. One exposed — the weakest.** The gap was never a
missing capability; it was five capabilities with no query surface.

---

## 6. The axes

His three, plus what I needed on 2026-08-10 and did not have.

**1 · FREQUENCY.** How many times an idea appears, across how many sessions, on what dates.
*This is his sharpest contribution.* A thing said **once** is an idea; said **three times** it
is a standing directive. THE EYE itself scored 3× in a prioritisation pass and was still
dropped, because **nothing measures repetition as signal strength.** No memory package in the
surveyed landscape does this.

**2 · WHO WAS THERE.** Seats live in that session, the model, the branch, the cwd.

**3 · AMBIENT.** What else was in play at that timestamp — commits in the window, tasks
touched, lessons filed, other utterances in the same session.

**4 · FULL UTTERANCE.** Not a snippet. On 2026-08-10 I assembled one quote from four
successive guessed substrings, because the only available tool returns one ~100-char snippet
per session.

**5 · SURROUNDINGS.** Via `parentUuid` — "what was around it" as a traversal.

**6 · AS-OF.** So a past decision can be read against what was knowable then. This is priori's
axis, and the one our supersession model currently cannot serve: recall hands back the
*current* head, so the n=5 kill-drill ran against today's archive with no way to replay the
decision as it was actually made.

---

## 7. The constraint, in his words

> "I want the eye to have its own cursor, we can't have lookups breaking core system logic"

He named the failure mode before the thing existed. A read surface sharing cursors with the
live bus would corrupt the thing it observes — and that is the exact class we broke repeatedly
during the week of 2026-08-04 through 08-10 with lane cursors, wake listeners and stale
inform-drains. **The Eye reads with its own cursor, and a pin proves a lookup cannot advance
or corrupt any live cursor.**

---

## 8. Acceptance (RED first)

1. Ingest captures **both** `type: user` **and** `queue-operation`/`enqueue` utterances, and a
   pin asserts a known mid-turn interjection is present. *(The silent-drop case, §4.)*
2. A query returns the **full utterance** plus session, timestamp, branch and neighbours —
   never a truncated snippet.
3. **Frequency** reports occurrence count across sessions with dates, so a 3× directive is
   mechanically distinguishable from a 1× aside.
4. **Ambient** returns what else happened in a stated time window.
5. The Eye reads with **its own cursor**; a pin proves a lookup cannot advance or corrupt any
   live bus cursor.
6. Re-ingest is **idempotent**.
7. End-to-end bar: *"when did he first say X"* answered in **one call**, not five guesses.

---

## 9. Deliberately not in this slice

- **Embeddings.** The socket is already specified in three modules and left empty —
  `learning_store` ("no embeddings, no LLM judge"), `event_query` ("embedding relevance_fn is
  a later swap-in — same 0..1 contract, must beat the [current]"), `codex/schema`
  (`centroid: List[float]  # embedding handle`). That ordering is correct: embeddings enhance
  a working facet surface; they do not substitute for a missing one.
- **Adopting bitemporal onto the lesson plane.** PRIOR_ART records that three fields buy the
  whole mechanism, verified 2026-07-26, with a stated gotcha: `isinstance(node, BiTemporal)`
  returns **False** even for an object carrying all three attributes, because
  `runtime_checkable` Protocols validate methods and not data members. The lifecycle functions
  work anyway via `getattr` duck-typing — *but anyone adding an isinstance guard "for safety"
  silently breaks a mechanism that otherwise just works.* Its own slice.
- **A human UI.** The consumer is the fleet. A browsable surface can come later and should not
  shape the door.
