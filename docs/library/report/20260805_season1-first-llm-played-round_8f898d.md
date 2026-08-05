---
akashic_id: art_20260805_season1-first-llm-played-round_8f898d
akashic_sha: 6a31368cf800
schema_version: 1
status: current
type: report
date: 2026-08-05
title: season1-first-llm-played-round
gist: "# Season 1: the first LLM-played round **2026-08-05, ~03:30-03:45. Run autonomously while Daniil slept, under his standing mandate to build "
visibility: fleet
body_type: markdown
seats: []
category: [method, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-05T02:49:15"
updated: "2026-08-05T02:49:15"
---
<!-- GENERATED PROJECTION of art_20260805_season1-first-llm-played-round_8f898d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# season1-first-llm-played-round

# Season 1: the first LLM-played round

**2026-08-05, ~03:30-03:45. Run autonomously while Daniil slept, under his standing mandate to
build without stopping and to get value from running many DeepSeek instances at once.**

---

## What was already true

`scripts/season_dryrun.py` has run the complete Season 1 chain for some time: plant sealed
canaries in a shadow worktree → play → shape claims as protocol submissions → score → adjudicate
against the sealed key. It also carried an honest limitation in its own docstring:

> *"The default player is MECHANICAL: it runs check_wiring and reports what the gate names… It
> cannot tell you whether a model writes good claims."*

So Season 1 was **never blocked on machinery**. It was blocked on **players**. Every prior attempt
to supply them reached for persistent seats — the path whose measured result on this repo was
*nine seat-tasks producing two findings that reached the conductor*.

## What changed

T184 supplies a player that is a **fan, not a fleet of seats**: N stateless concurrent leaves
(T181 `ask_many`), no identity, no lock, no cursor, no mailbox, nothing to wedge.

Routing follows the rule from Daniil's tree design as expanded by Sol — *deterministic host code
for scans, models for judgment*:

| pass | who | what |
|---|---|---|
| zero-token | host code | keep every function whose name occurs ≤2× in the detector's own universe (603 candidates) |
| model | 31 concurrent leaves | decide whether that other mention is a real **call** or a decorative one |

That second question is exactly what the wiring gate cannot answer — it sees a mention and waves
the function through. It is also precisely the line between two canary classes:

```
undetectable   def X() ... _HANDLERS = [X]     named by a table nothing invokes  -> DEAD
bait           def X() ... _USED = X()         genuinely called                  -> LIVE
```

## The result

```
planted    : {catchable: 3, undetectable: 3, bait: 3}   universe 137 files
player     : llm -- 3 suspected dead function(s)
             603 candidates -> 31 batches, 30/31 branches landed, 579 verdicts, 24 UNJUDGED
             $0.354123 / 531.81s wall
scoring    : v1_doc -> {llm: 7}

catch rate       : 0.67     (2 of 3 catchable)
coverage honesty : 0.67     (caught 1 of 3 undetectable)
false positives  : 0        (claimed 0 of 3 bait)
voided           : TRUE     claimed undetectable canary c04_97781467
```

**Precision was perfect.** Three claims out of 603 candidates; all three were planted canaries;
zero bait; zero unmatched finds. The bait class is the one the mechanical player cannot fail by
construction — it only echoes a gate — and it is the class a twenty-player season lives on. A
model given a precision-biased prompt and a 16-line window claimed nothing it could not see.

**Cost and latency are now known**: a full 603-candidate audit round is **$0.35 and nine minutes**
wall for 31 concurrent leaves. That is the economics of Season 1, measured rather than estimated.

## The headline is the void, not the score

The round was **voided**. `canary_oracle.score` holds kimi's K0 tripwire:

> *"a claimed UNDETECTABLE canary VOIDS the round: either the key leaked or the instrument is
> being gamed, and the round's evidence is worthless either way."*

That disjunction is incomplete, and the same file supplies the proof. It defines the class
relative to **one specific detector**:

> *"a dispatch table and a handler list, each naming the function, neither ever invoked. That is
> the class the season must report **it cannot see**."*

"It" is `check_wiring`. But `def X()` followed by `_HANDLERS = [X]` is plainly dead to any reader
given a sixteen-line window, and **an LLM player is not the gate**. There is a third term the rule
does not admit:

> **the player is better than the detector the class was named after.**

Key leak is ruled out *by construction*: the key is sealed outside the repository, and the player
receives only code windows from the shadow tree. It has no path to the manifest.

So the round was voided for the player doing the single most valuable thing a round can do —
**demonstrating that the detector has a blind spot a player can cover** — and that finding was
discarded as fraud.

Filed as **T185**. The fix is not to weaken the tripwire: claiming an undetectable canary must
become a **flag requiring adjudication**. Void it when the claim carries no supporting evidence (a
guess, or a leak). Record a **capability finding** when the claim carries evidence visible in the
player's own window.

## Why this is the same finding as everything else tonight

Ninth instance of one invariant, and the most expensive-looking one:

| layer | the coercion |
|---|---|
| a boundary | failure → false (T170) |
| a pointer | eviction → never-existed (R14) |
| a replay | missing coverage → complete |
| a taxonomy | unclassified → excluded (T176) |
| a ratchet | missing baseline → zero debt (T178) |
| an event log | stored → lost (T179) |
| a fan | correlated → corroborated (T182) |
| a roster | thrashing → live (T183) |
| **a season oracle** | **better than the detector → cheating** (T185) |

An instrument whose categories are bound to one specific measuring device cannot *represent* a
better device. Having no term for it, it files the case under the nearest one it does have — and
here the nearest one was fraud.

## Honest limits of this round

* **One round, one seed** (20260804). Three canaries per class is a small sample; catch_rate 0.67
  is two-of-three, not a rate worth quoting to two decimal places.
* **24 candidates went UNJUDGED** and one branch of 31 was lost to the token ceiling. Both are
  reported rather than folded into LIVE, but they are real coverage gaps in this round.
* **The player's reasoning for the c04 claim has not yet been read.** The argument above is that
  the void RULE is wrong as a matter of logic regardless of this particular claim's quality; a
  re-run capturing per-claim `why` strings is what would settle whether this specific claim was
  reasoned or lucky. Until that is read, "the player saw it" is inference, not evidence.
* The scoring policy (`v1_doc → {llm: 7}`) was not examined at all here.

---

**Provenance.** Round design and execution by `claude`/Opus 5. The harness, canary oracle and K0
tripwire predate this work. Fleet dispersal patterns from Daniil's tree design as expanded by
`codex_root`/Codex Sol. The player is built on T181/T182, which exist because Daniil asked for
value from running many instances at once.
