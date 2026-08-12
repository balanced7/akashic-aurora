# RESULT: the blind draft, and the warning that could not reach me

Run 2026-08-07 against predictions committed at `ed518ea`, before the draft.

## Scorecard

| | prediction | outcome |
|---|---|---|
| **P1** | drafter finds `drained`'s three cursor families | **PARTIALLY REFUTED — but it is a WINDOW miss** |
| **P2** | drafter MISSES the cross-subsystem `confidence` fork | **REFUTED, and CONFOUNDED by my own grounding** |
| **P3** | ≥1 candidate names a mechanism I would not have thought of | **CONFIRMED, richly** |

## P1: the miss was my evidence, not its reasoning

The drafter named `cursor:` and `cursor:seat:` and did **not** name `cursor:lane:`.

Checked before scoring it as a miss:

```
truncated: True
EVIDENCE CLIPPED: bus.py (40000 of 80052 chars)
cursor:lane: reachable in what the drafter actually saw?  False
cursor:seat: reachable?                                    True
```

**`cursor:lane:` is at `bus.py:1201`, outside the 40k window.** The drafter found every
cursor family it could see and missed the one that was literally absent from its evidence.
Scoring that as a reasoning failure would have been inferring absence from a blind
instrument — the exact error this arc is about, and the one my pre-registration promised to
distinguish.

**It also found two mechanisms MY table lacks**: `reply_seen:<reply_id>` and the re-ask
collapse `xrange` check. Both are arguably "has this been consumed", and both are absent
from my binding. P3 fulfilled on a *control* term — the blind drafter improved a table I
wrote.

## THE FINDING: my own fix had no channel to me

I did not see that clip warning during the run.

I built `T218` this morning precisely so a window-caused abstention would stop reading as
absence. claude#42d00626 then **widened** it (his T225) to cover REFUSED, MISSING and SKIPPED
files as well. The notice exists, it is correct, and it fired.

**It goes to stderr. My probe captured stdout only.** So the warning had no channel to the
reader who needed it, and my experiment was silently compromised by the very defect the
warning was built to announce.

That is `a_warning_needs_a_channel_the_reader_actually_has` at third order: I built the
notice, a peer widened it, and it still did not reach me — because of how *I* invoked the
tool. A warning is not "loud" because it was written; it is loud only on a channel the
reader is actually listening to.

**Operational fix, and it is one line per probe:** any harness that captures a tool's output
must capture **stderr too**, or it is running blind to every diagnostic the tool emits.

## P2: refuted, and I confounded it myself

The drafter found both `learning_loader._CONFIDENCE_IMPORTANCE` (categorical) and
`tagging.BASIS_CONFIDENCE` / `TagEntry.confidence` (float) — the cross-subsystem fork.

But **I handed it both files** in the grounding list. My pre-registration claimed the list
"cannot leak it" because it included extra files; for `confidence` it contained exactly my
two table entries plus one. That is a weak fence and I should have caught it while writing.

Honest read: **a drafter can find a cross-subsystem fork when handed both subsystems.**
Whether it would find the second subsystem unprompted is untested, and that was the actual
question.

## P3: three candidate drafts worth ratifying

Not adopted — drafts for a human, per the construction.

- **`attending`** — `liveness.attendance()`, `worklive_beat_age`, `progress_age`,
  `roster()`, `BusLossGuard`, `bus.PRESENCE_TTL`. Six mechanisms for "is this seat actually
  here", which is exactly the T155 four-gauges-disagreeing incident in binding form.
- **`settled`** — `_SETTLE_LUA`, `reply_settled:{sender}:{rid}`,
  `expectation_settled_answered`, `TERMINAL_TO_STATE`, `CLOSED.ANSWERED`, `CLOSED.ECHO`.
- **`stale`** — `STALE_PROPOSED_DAYS`, `premise_settled`, the inbox freshness window, the
  consume-side stale-gate auto-park.

`attending` is the strongest candidate: six differently-named mechanisms answering one
question is the exact shape that cost a seat-hunt at T155.

## What this says about the division of labour

The question behind P2 was: what does human ratification have to add?

This run cannot answer it, because I leaked the files. What it *does* show is narrower and
still useful: **the drafter is good at enumerating mechanisms inside evidence it can see, and
completely bounded by what it was handed.** Every miss traced to the window, not the
reasoning. So the human contribution under test is **choosing the evidence**, and the next
experiment has to withhold the file list rather than hand it over.
