---
akashic_id: art_20260805_season1-first-llm-played-round_4bc26a
akashic_sha: a498e965869d
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
created: "2026-08-05T03:26:31"
updated: "2026-08-05T03:26:31"
---
<!-- GENERATED PROJECTION of art_20260805_season1-first-llm-played-round_4bc26a -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

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

## CONFIRMED: the player sees the class, it did not guess

The argument above was logical. Two cheap isolating probes settled it empirically, for
**$0.011 and 38 seconds** combined — far less than re-running the round.

**Probe 1** planted the same seed's canaries and handed the player only the windows around the
`undetectable` and `bait` canaries, with no key, no class labels, and no hint they were planted.
**4/4 correct.** Every bait was rejected by naming its own call line (`_USED = route_9496de()`).

But the undetectable claim's reasoning read: *"The comment states the registration table is never
invoked."* — and the template's docstring literally says `"""Registered in a table that nothing
ever invokes."""`. **The fixtures state their own answers.** So probe 1 could not distinguish
analysis from label-reading.

**Probe 2** stripped every docstring and re-asked. **7/7 correct**, and the reasoning became
structural:

| class | verdict | the player's evidence |
|---|---|---|
| catchable | DEAD | *"its definition is conditional, so nothing ever calls it"* |
| **undetectable** | **DEAD** | ***"No invocation of apply_339e07 or iteration over `_HANDLERS` visible"*** |
| bait | LIVE | *"called at module level via `_USED = emit_9fb139()`"* |

Noticing that a handler list is never *iterated* is exactly the A5 judgment `check_wiring` cannot
make. The player earned the claim. K0's disjunction is missing a term, on evidence.

## Two further findings the probes turned up

**The canary fixtures leak their own answers.** Every `undetectable` template carries
`"""Registered in a table that nothing ever invokes."""`; a `catchable` one carries `"""Fan-out
path -- unreachable."""`. A player can score by reading labels rather than analysing code. It did
not change *this* result — 7/7 survived stripping — but it means the harness's difficulty is
partly fake, and a weaker player would be flattered by it. The same defect T184's K2 pins against
in the player, sitting in the fixtures.

**This player is structurally blind to 2 of the 3 undetectable canaries.** The string-dispatch
shape is `_DISPATCH = {"name": name}`, which puts the name in the tree **three** times (def, dict
key string, dict value) and so fails the `≤2 references` pre-filter. Those canaries never reach
the model at all. The one it caught was the `_HANDLERS = [X]` shape, which occurs twice. So
`coverage_honesty 0.67` is not the player declining to claim two canaries — it is the player never
being shown them, which is a different fact wearing the same number.

## Three rounds, and the attribution A/B

After T186 (neutral fixtures) and T187 (string-aware pre-filter) landed, two more rounds ran. The
second changed the seed *and* the harness at once — careless, and it produced a misleading
reading — so a third isolated the fixture change on the original seed.

| | leaky, seed 804 | **fixed, seed 804** | fixed, seed 805 |
|---|---|---|---|
| catch rate (catchable) | 0.67 | **0.67** | 0.33 |
| undetectable caught | 1/3 | **2/3** | 0/3 |
| false positives | **0** | **0** | **0** |
| claims made | 3 | 4 | 1 |
| branches landed | 30/31 | 32/32 | 32/32 |
| unjudged | 24 | 4 | 5 |
| cost / wall | $0.354 / 532s | $0.349 / 442s | $0.366 / 406s |
| voided | yes (1 hit) | yes (2 hits) | no |

**Removing the self-describing docstrings cost no recall at all.** On identical canaries the
player scored the same catch rate and caught *more* of the hard class. The recall drop in the
seed-805 round was the seed, not the fixture fix — different canaries are simply placed less
visibly. My first reading implied T186 might have cost recall; the A/B says it did not.

**T187 produced a direct, measured recall gain**: undetectable caught went 1/3 → 2/3 on the same
seed, because the string-dispatch shape now survives the pre-filter and reaches the model.

**Precision is the durable result.** Zero bait claimed in all three rounds, on both the flattering
board and the honest one.

**And the capability is reproduced, not a fluke.** The fixed round on the original seed voided for
**two** hard-class canaries, with the labels gone. A player that reliably finds the class the
oracle says no honest player can find is not gaming the instrument — it is the instrument's most
valuable output, and it is currently discarded as fraud three rounds running.

## The scoreboard is perverse in both directions (T189)

`coverage_honesty = undetectable.missed / undetectable.total`, and `voided = bool(undetectable_hits)`.

So a player that **finds** the hard class has its round voided as fraud, and a player that
**misses** all of it scores a perfect 1.0. Read together, the scoreboard penalises exactly the
capability the season exists to hunt for. The seed-805 round scored `coverage_honesty 1.0` while
T187 had already verified all three of those canaries reached the player — it saw them, declined,
and was rewarded for it.

Both halves share T185's root cause: the class is defined relative to `check_wiring`, so for the
gate "missed" genuinely means honest, and for a capable player the identical number means a recall
floor. One metric carrying two opposite meanings depending on who is playing.

## Honest limits of this round

* **One round, one seed** (20260804). Three canaries per class is a small sample; catch_rate 0.67
  is two-of-three, not a rate worth quoting to two decimal places.
* **24 candidates went UNJUDGED** and one branch of 31 was lost to the token ceiling. Both are
  reported rather than folded into LIVE, but they are real coverage gaps in this round.
* ~~The player's reasoning for the c04 claim has not yet been read.~~ **Settled by the two probes
  above: 7/7 with docstrings stripped, reasoning structural. The claim was earned.**
* **The confirming re-run of the full round was lost to my own pipeline.** I captured it with
  `tail -60`, which discarded the `player_report` holding the reasoning — the evidence I ran it
  for. The probes replaced it at 3% of the cost, but the truncation was self-inflicted and is a
  small instance of the same class as everything else here.
* The scoring policy (`v1_doc → {llm: 7}`) was not examined at all here.

---

**Provenance.** Round design and execution by `claude`/Opus 5. The harness, canary oracle and K0
tripwire predate this work. Fleet dispersal patterns from Daniil's tree design as expanded by
`codex_root`/Codex Sol. The player is built on T181/T182, which exist because Daniil asked for
value from running many instances at once.
