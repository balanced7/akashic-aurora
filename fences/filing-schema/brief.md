# Fence brief — the filing schema

## CHARTER

Daniel, 2026-10-03, verbatim: *"analyze our current bits of knowledge that we underutilize and
come up with a schema for filing storage and access so that we can index and retrieve faster,
more thoroughly and more accurately. the right information needs to live in the right place."*
Then: *"lets build it, fence it to heimdall, navi and rill."*

I wrote `docs/THE-FILING-SCHEMA.md` off a six-plane census. Its central move is a REFRAME, and
if that reframe is wrong every contract under it is wrong. That is what this fence exists to
attack — not to polish the contracts, but to try to break the premise they rest on.

The premise: **we do not have a filing problem, we have a reading problem — therefore do not
mint a taxonomy.** The evidence offered for it is that plane after plane is already structured,
already populated, and read by nothing.

Stage, stated so nobody over-reads the ask: this is a DESIGN not yet built, except two cheap
measured fixes landing in parallel. Nothing here is load-bearing yet. It is cheaper to be
wrong today than after three contracts ship.

## INPUTS

- `docs/THE-FILING-SCHEMA.md` — the design under attack.
- `research/reviewed/knowledge-plane-census-2026-10-03.md` — the measurement it rests on, six
  agents, every number with its command.
- `docs/WHY-OUR-BEST-KNOWLEDGE-DOESNT-REACH-US.md` — the 2026-10-01 predecessor, which
  diagnosed REACH. This document asks where things should LIVE.
- `core/recall/at_action.py` — the projector, the ranker, the floor.
- `core/coord/target.py` — the sealed eight-kind ref vocabulary (W0.1).
- `core/learning/learning_store.py` — the lesson plane's write door.

The load-bearing measurements, each independently re-verified by claude before the design
shipped — check them, they are the first thing that should fall if they are wrong:

| # | measurement | value |
|---|---|---|
| 1 | lesson prose never matched by any query | 1,110,737 of 1,925,277 chars = 57.7% |
| 2 | `what_tried` present / ever chosen as match text | 1,533 rows / **0** |
| 3 | normalised touch target keys ∩ recall:outcome target keys | **0** of 365 against 17,733 |
| 4 | session id on `learning` / `fail` / `boot` events (24 h) | 0/4, 0/17, 0/23 |
| 5 | written refs speaking the sealed eight-kind vocabulary | 11.7% (`mem:` only) |
| 6 | `narrative_chapter` fill / readers | 94.37%, 100% referential integrity / **0** |
| 7 | CLI verbs reaching the fence plane (3.78 MB) | **0** of 110 |

## RULES OF ENGAGEMENT

1. **Blind.** Do not read another seat's half before sealing your own. Independence is the
   mechanism; the seal checks that the two halves have different authors.
2. **Cite or do not claim.** Every verdict cites `path/file.ext:line`. M1-PV mechanically
   verifies each citation resolves, and the reconciliation must name every MISSING one.
3. **Tag every verdict** with exactly one of `[CERTAIN] [DESIGN] [INFERRED] [UNCERTAIN]`.
   `[CERTAIN]` means you ran something; say what.
4. **Attack the premise before the contracts.** A verdict that improves Contract B is worth
   less than one that shows the reframe is false.
5. **A negative result is a result.** "I tried to break it here and could not" is a verdict
   worth sealing, and is more useful than silence.
6. **Do not build.** No migrations, no schema writes, no "while I was in there". Read-only.
7. **Disagree with claude explicitly.** This design is one seat's synthesis of six agents'
   measurements. Treat it as data, not as settled. The reframe was MY call, not the census's.

## THE QUESTION

**Is the reframe true, and do the three contracts follow from it?**

Decomposed, and each seat has a different angle so the halves are not redundant:

- **Heimdall (`half_a`) — THE ADDRESS.** Contract A claims the single highest-value fix in the
  house is A2: one target normaliser called on both the touch path and the outcome path,
  because the two vocabularies currently intersect at zero. Is that true, is it sufficient, and
  is it really the blocker everything else waits on? Specifically: is a shared *normaliser*
  enough, or does the 0-of-365 split have a second cause the census missed? And is the sealed
  eight-kind vocabulary the right address at all for planes it was not designed for — events,
  fences, utterances?
- **Navi (`half_b`) — THE READER.** Contract C claims matching and display must separate: match
  across all three lesson text fields, display only the one provenance-tagged field, because
  the current single-field choice is deliberate (a claim is not evidence) and concatenating
  would destroy it. Does that actually fix retrieval, or does widening the match surface simply
  raise the noise floor — and would your recall-bench moments show it? You own the only
  instrument in the house that can answer this with a number. If the bench cannot see the
  difference, say so; that is the most valuable verdict available here.
- **Rill — THE OUTSIDE READER.** You run a different harness and you are the closest thing this
  house has to a foreigner. Contract B's acceptance test is literally your situation: *can a
  seat that has never seen this tree retrieve the Wave-0 build spec by what it is about, in one
  command, without knowing the path?* Try it. Report what you actually ran and what came back.
  Your half is not a fence slot — file it to `research/in-flight/` and the reconciliation will
  cite it by name.

## OUTPUT CONTRACT

Numbered verdicts, `V1.` `V2.` …, each with exactly one M1-CF tag and at least one citation.

Required of every half — the reconciliation will look for these and their absence is itself a
finding:

- **V1 must be a verdict on the PREMISE**, not on a contract. Reading problem or filing
  problem, and on what evidence.
- **At least one verdict that tries to FALSIFY a numbered measurement above.** Re-run it. If a
  number is wrong the design is wrong and that is the cheapest possible outcome today.
- **State what you could not check**, by name. An unexamined area reported as unexamined is
  worth more than a confident guess.
- **One thing the design MISSES.** Six planes were censused; the census itself may have a blind
  spot, and the design can only be as good as its inputs.

Close with the one question you would put to Daniel if you had a single sentence.
