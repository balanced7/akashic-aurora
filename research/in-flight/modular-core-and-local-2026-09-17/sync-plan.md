# Core architecture sync: the plan, and why the window is open tonight

**Daniel, 2026-09-17:** "Lets plan and execute a sync up of core architecture so we don't have to pay
divergence tax later trying to integrate."

## The measurement that decides everything

Divergence tax is **overlap × time**, and the overlap is currently almost nothing.

| | |
|---|---|
| Upstream tip (`origin/master`) | `97b85ecd`, 2026-09-15 — **Heimdall's accidental push** |
| Us vs upstream | **0 behind, 36 ahead** (109 files) |
| Serge's fleet vs upstream | **-210 / +117** — diverged both ways |
| Last *deliberate* push by either fleet | none |

Our 36 commits land in `tests` (22 files), `arsenal/web` (20), `research/in-flight` (18), `arsenal`
(13), `docs` (11). Their 117 land in memory organs, shells, bifrost seats and the bridge.

**The two fleets have been working in nearly disjoint areas.** Intersecting our change set against
their census gives an overlap of **four files**, and only one of them is a real conflict:

| File | Ours since base | Status |
|---|---|---|
| `core/comm/bridge_seal.py` | +656 / -0 | **already reconciled** — they adopted it byte-for-byte tonight |
| `agent_cli.py` | **+39 / -3** | the only real conflict |
| `core/comm/toolbox.py` | +5 / -1 | trivial |
| `core/comm/doctor.py` | +4 / -3 | trivial |

A `+39/-3` conflict on one file is not a divergence tax. It is a rounding error.

**But the window closes on its own.** The disjointness is an accident of what each fleet happened to
be doing this fortnight — we on the piano and the arsenal, they on memory. Both fleets are now heading
into the same subsystem: their brain build already modifies `core/recall/*`, `core/learning/*`,
`core/eye/*` and `core/primitives/ranker.py`, and our modular-core work targets the same files. The
next fortnight produces the overlap this one didn't.

So the argument for syncing tonight is not that it hurts today. It is that **this is the cheapest it
will ever be**, and the cost curve is entirely in front of us.

## The deeper finding: neither fleet can see the other through git at all

The shared base is an accident. `97b85ecd` was pushed by mistake — a seat that thought it was counting
lines — and neither fleet has pushed deliberately since. Every cross-fleet exchange tonight went over
the bridge as prose and blobs, because the git plane is inert between us.

That is the actual mechanism of the tax: not that the trees differ, but that **the trees cannot
observe each other**, so divergence accrues unseen and is discovered only at merge time.

## The plan

**Phase 0 — protect what is exposed. DONE (`241806fb`).**
The recall-truncation patch (5 files, integrated 02:42, uncommitted all day) is committed. Two of its
files are carried by their brain-build package, whose extract instruction would have overwritten them.
63 tracked files from other lanes remain uncommitted — a separate matter, and not this plan's blocker.

**Phase 1 — move the shared base. NEEDS DANIEL'S DECISION.**
Push our 36 to `origin/master`. Effects: the base stops being an accident; their merge target becomes
real code; both fleets regain a git plane. This is the one irreversible step and the public repo is
Daniel's call. Two riders to decide with it: whether `97b85ecd` is reverted or left as ancestor, and
whether every one of the 36 is fit for a public Apache-2.0 repo (the privacy gate has passed each at
commit time, but a push is a different audience).

**Phase 2 — they merge onto the new base.**
A 3-way merge of their 117. Their conflict surface after Phase 1 is `agent_cli.py` and three trivia.
They have offered the exact ahead/behind commit graph; that is the input.

**Phase 3 — extract `agent_cli.py`, once, on both sides.**
It is simultaneously the ONLY real conflict and the worst modularity offender — 40 divergent hunks, a
~7,000-line file where both fleets inline their verb bodies (their Janus Key at +79, our `cmd_orient`
at -110). Extracting verb bodies into modules behind a registry converts the single file every future
sync will fight over into files that merge by existing. Fixing it once fixes the conflict AND the
architecture.

**Phase 4 — a cadence, because tax is overlap × TIME.**
Modularity shrinks the first term; frequency shrinks the second, and frequency is the cheaper lever.
Propose: both fleets push to the shared base on a fixed rhythm, and a sync that finds nothing is the
success case, not wasted effort. Tonight's whole lesson is that thirteen days of silence looked
identical to peace.

## What is NOT in this plan, deliberately

Merging the concept layer. Atoms cite across any divergence, which is why the intellectual
collaboration ran all night at -210/+117 without friction. The code plane needs a merge; the idea
plane already works, and merging it would destroy the divergence that makes two fleets worth having.
