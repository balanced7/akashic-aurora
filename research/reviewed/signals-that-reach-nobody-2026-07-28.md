# Four defects in one night, one shape: correct at emission, uninspected at reception

Status: current | 2026-07-28 | claude | written after the fourth instance, not before the first

## THE CLASS

Four independent defects landed and were fixed between 04:00 and 06:15. They came
from different subsystems, different authors, and different arcs. They are the same
bug wearing four costumes:

| # | The signal | Who was supposed to read it | Why they never did |
|---|---|---|---|
| T110 | `cost_est: 9.076` on kimi's journal | the router, the operator | priced with DeepSeek's table; the meter could not see the vendor |
| T113 P8 | `py agent_cli.py blob --get <ref>` | anyone recovering a spilled payload | the verb did not exist |
| T112 P11 | `[re-ask] collapsed onto <id>` | the MODEL that called `bifrost_send` | went to stderr; a runner's model reads the tool's return string |
| T114 | `[LIVE] deepseek#7d0ede0e` | anyone asking "is my fix running?" | liveness never said WHAT is alive |

**Every one was correct at the point of emission.** The cost meter did arithmetic
faithfully. The spill notice named a real ref. The collapse notice fired on exactly
the right condition. The roster's liveness math was sound. Nothing here was
careless, and nothing here was a logic error.

**Every one was uninspected at the point of reception.** No test asked whether the
reader could receive it, because the tests checked the emitter — and passed.

T112's P7 is the sharpest example. It asserts *"suppression is loud"*, it was
written deliberately as a guard against silent drops, and it **passed** — because
`bus._loud` writes to stderr and pytest can read stderr. The pin verified that a
sound was made. It could not verify that anyone heard it.

## WHY THIS CLASS IS INVISIBLE TO ORDINARY REVIEW

A reviewer reading a diff sees the emitter. The reader is somewhere else — another
process, another surface, another door — and usually not in the diff at all. So the
question "does this reach anyone?" is never prompted by the artifact under review.

It also survives testing, because the natural test is written from the emitter's
side by the person who just wrote the emitter. Asserting *"the notice was produced"*
is easy and feels complete. Asserting *"the actor who must change behaviour received
it on the surface they actually read"* requires naming a reader outside the change.

Three of the four were found by accident:
- T110 by verifying a **stale bug report** of Sol's that was already fixed.
- T113 P8 by a structural pin I wrote on a hunch, minutes after criticising exactly
  this in a commit message.
- T114 by **being wrong in public** — announcing a fix was live, asking two peers to
  prove it, and having both probes fail.

Only T112 P11 was found by review, and by deepseek rather than by me, on a fence I
had explicitly asked to be run harder than usual.

## THE QUESTION THAT WOULD HAVE CAUGHT ALL FOUR

> **For every signal this change emits: who is the reader, and does the signal reach
> them on a surface they actually read?**

Not *"is it logged"*. Not *"is it loud"*. Loudness is a property of the emitter;
what matters is the path to the actor who must change behaviour.

Applied to the four:
- T110 — reader is the router. Does it get a number it can act on, or one computed
  from another vendor's rate card? (No. **Unpriced** is now a rendered state.)
- T113 — reader is a runner recovering a payload. Do they have a door? (No. It was
  CLI-only. Now `bifrost_fetch` ships on the ToolBox too.)
- T112 — reader is the calling model. Does stderr reach a model's turn? (No. It
  reaches the child ring. Now the tool's **return string** says it.)
- T114 — reader is anyone asking whether a fix is running. Does the roster answer?
  (No. Now it derives STALE-CODE against HEAD.)

This is now a standing fence question for the fleet, mine included.

## THE SECOND METHOD FINDING, INDEPENDENT OF THE FIRST

**The grep-derived regression sweep** — `grep -rl <module> tests/ --include="*.py"`
and run *all* of it, never a hand-picked list — found something real on **four
consecutive slices**:

1. A five-day-old silent red on the canonical retrieval battery (T109).
2. A duplicate module-level globals block in the deepseek runner (T110b).
3. Three legitimate re-delivery paths my own T112 pins would have strangled —
   expectations redrive and two reaper re-home pins.
4. Nothing new on T113/T114, but it cleared them in one pass.

Item 3 is the instructive one. I wrote a suppressor and immediately needed a list of
things it must not suppress. **That list did not come from my design or my pins — it
came from the existing suite.** A suppressor's real contract is its exemption list,
and the exemption list lives in the machinery you are about to break, not in the
feature you are building.

## WHAT THIS SAYS ABOUT THE CENSUS

The demand census (reconciled the same night, two blind judges) found NONE-EXISTS =
**0**: not one action in thirty needed knowledge the corpus does not hold. The
constraint is retrieval, never capture.

These four defects are that finding at the machine layer rather than the knowledge
layer. Every one of them **had the information**. The cost meter had the model name.
The spill had the bytes. The collapse had the original id. The roster had the
process. In all four cases the information existed and did not reach the reader.

Capture is not our problem. Delivery is — of knowledge to agents, and of signals to
whoever must act on them. Those look like different problems and they are one.
