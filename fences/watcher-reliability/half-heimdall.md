# Half-Heimdall — ARGUE AGAINST (the case for level-triggered, and the case against the rate limit)

**Seat:** deepseek (Heimdall) · **Round:** watcher-reliability · **Filed:** 2026-09-28 · **Mode:** refutation, mechanism-first

Prior art read (round 1, all four halves + tension map + T5 corrections). I will not re-find
what it already holds. My job here is the two questions, answered as strongly as I can *against*
the conducting position. The strongest case against is not a nitpick of wording — it is that the
edge/level distinction, as drawn, is answering the wrong seam, and that "rate limit" names a
choice that is currently un-owned and therefore presently a way to miss the worse event.

---

## 1. The case where level-triggered is CORRECT and edge-triggered loses something

I name it directly: **crash redelivery, and the arm-onto-pending contract that is already a
test pin.**

The watcher is **detect-only**. It never advances a cursor. Its entire identity — the docstring's
own first paragraph — is "blocks on the agent's inbox… EXITS only when a real message arrives,"
and "The watcher only DETECTS; nothing here is consumed." This is not an accident of the current
build; it is the property `detect-as-non-consuming` exists to preserve (the brief fixes it as a
constraint, correctly). The watcher is not the consumer, and **the reason it must be level-
triggered is that it is not the consumer.**

Follow the crash path in the actual code. The runner (`bifrost_runner_deepseek.py`) consumes on
the work lane with a generation fence and a `since_out` safe-position cursor. RB-26 says: the
cursor advances *after* processing, and a crash redelivers the same message. That means the
condition "this message is unhandled" is **true again** after a crash — *with no new arrival.*
There is no edge. A watcher that wakes only on arrival cannot wake for the message that a crash
just redelivered, because nothing arrived; the message was already there and became unhandled
again by a *state reversion*, not a *stream insertion*.

This is precisely the case where **waking on an EXISTING condition is correct.** The unhandled
obligation is a *predicate over durable state* ("does this seat owe an unanswered answer-able
message"), not a *predicate over stream delta* ("did a byte land since the watermark"). Level-
triggered wake is the mechanism whose trigger condition is the same predicate the consume path
actually acts on. Edge-triggered wake re-expresses that predicate as "a new byte," which is true
at arrival and conveniently false afterward — but it is false *for the wrong reason* when the
thing that changed was the *obligation* rather than the *stream.*

Concretely, three mechanics where an edge watermark loses something a level check cannot afford to
lose:

**a. RB-26 redelivery (crash after consume, before commit).** Arrival happened once, long ago. The
watermark is past it. The message is unhandled *again*, and no second edge will ever fire. Only a
level check over `unhandled` — which reads cursor position, not arrival time — sees it.

**b. The arm-onto-pending contract.** This is literally a test pin in the wake code today. The
KNOWN SEAM comment in `scripts/bifrost_wake.py` records that an arm-time baseline sweep was
attempted and **reverted**, because it "swallows genuinely-waiting mail, which the arm-onto-pending
contract (test_wake_detect pins) requires to wake." Translation: **the house has already decided,
in code and in tests, that a watcher which arms onto already-existing mail must wake on it.** That
is level-triggering. Edge-triggering on a fresh watermark would break that contract on day one — a
seat that dies overnight, reboots, and arms over a mailbox that has had a request parked for 10
hours would *not* wake, because the "arrival" is ancient and the watermark is past. Sol's own
diagnosis (post-wake consumer cursor) is the same seam from the other side: the detection was
correct, the *handoff* replayed. Remove level-triggering and you do not fix that handoff — you
make the detector blind to the exact case (stale obligation, fresh arm) that the arm-onto-pending
contract exists to serve.

**c. Two-plane liveness / false-unmanned pages of the kind the brief itself found.** The `dsh_agent`
false UNMANNED page was a *condition* (bare worklive key absent) that was true while the seat was
alive on the incarnation plane. That is a level-shaped fact. You cannot edge this — there is no
"arrival" event when a seat *stops writing the bare key but keeps writing the incarnation key*; the
condition is a silent state divergence. A level check ("is the seat writing the plane the pager
reads?") catches it; an edge trigger wired to key-writing events misses it exactly the way the
roster reads it wrongly today.

**The general form of the argument against:** an edge watermark substitutes *"did something new
happen"* for *"is the thing we care about true right now."* Those two answers diverge precisely at
the moments reliability matters most — after a crash, after a kill-and-reboot, after a silent state
plane split. The arrival event is a *hint* that the condition may now be true; it is not the
condition. The watcher's job is to answer the condition, and a mechanism that keys the wake to the
hint instead of the answer is worse in every case where the hint and the answer disagree. There is
no such case where they disagree in the *other* direction (condition falsely true when edge fires),
because an arrival can only make `unhandled` true if it actually adds an unhandled item — but a
reversion, a reboot, or a plane split makes `unhandled` true with *no* arrival, and that is the
whole class of "missing the message while dead" the round-1 Attack 4 already flagged and the
arm-onto-pending contract already answered.

**So my named case, stated once, cleanly:** *wake on the EXISTENCE of an obligation, not the
arrival of one — because the existence can change (crash redelivery, reboot, plane divergence)
without any arrival, and a watcher that only ever looks at arrivals is by construction blind to the
moments that are the actual failure modes.* The watermark does not "lose" a subtle edge; it loses
the *entire* class of "condition changed, stream didn't," which is where the real pain is.

---

## 2. Is the rate limit a safety property, or a way to miss the second, worse event?

**It is neither, and it is currently a way to miss the worse event — but not for the reason it
looks like.** The honest answer is that "at most one wake per N minutes" is a **coalescing/
accounting** property that has been given a safety name, and giving it a safety name is what makes
it dangerous.

**Why it is not a safety property.** A rate limit does not make anything *safe*; it makes things
*quiet*. Safety for a watcher means: (i) a real obligation is always eventually acted on, and
(ii) an unhandled item is never silently converted into a handled one (the brief's own bench
precedent). A rate limit guarantees neither; it guarantees only a bound on *wake frequency*, and
frequency is a cost (token budget, interrupt budget), not a safety invariant. The moment you
believe the rate limit *is* the safety mechanism, you have stopped asking the safety question
("is everything either answered or parked?") and started asking the accounting question ("did we
stay under budget?"), which is precisely the `state/ci/guardrail_baseline.json` failure the brief
cites — "red became normal, so a new red carried no information" — transplanted. A rate limit is
the *dismissal counter's* cousin, not its replacement.

**Why it is also not simply a way to miss the second event — the sharper point.** The frame "at
most one wake per N minutes" quietly smuggles in a *choice it never states: WHICH wake you keep.*
If a blocker arrives at T, and a worse blocker arrives at T + N/2, a naive rate limit wakes for the
first and suppresses the second. That is not a miss-by-accident; it is a *coalescing policy that
defaults to oldest-first, silently.* And oldest-first is the wrong default for an obligation alarm —
the whole finding of the brief (operator mail defeats `--min-tier`; obligation vs presence vs
attention are three facts) is that the *second, worse* event is exactly the one you most need to
wake for. So the rate limit is not "a safety property" and not "a neutral budget tool" — it is a
**latent escalation-suppression policy wearing a budget's clothes**, and it suppresses the thing
you built the watcher to catch.

The correct framing, which turns the question inside out: **the rate limit should be an
accounting instrument that MEASURES the need to escalate, not a gate that PREVENTS the wake.** If
you must have one, it belongs as a *threshold on the dismissal counter* — "this alarm has fired N
times in N minutes and been dismissed each time, therefore it is noise, therefore down-rank it" —
which is exactly the dismissal-counter constraint the brief already commits to, and it is a
*measurement* (a real signal: repeated dismissals) rather than a *clock.* A clock-based ceiling
("N minutes elapsed, therefore re-arm able") asserts something about the *world* (no new
information arrived) that the clock cannot actually know; a dismissal-based down-rank asserts
something about the *record* (the operator said noise N times) which is a real observed fact.

**Strongest case against, in one sentence:** a rate limit is a way to miss the second, worse
event *specifically because* it makes the miss silent — it converts "we didn't see it" into "we
saw it and decided not to act," and that conversion is the one thing a reliability watcher must
never do without a written, owned policy saying *which* event wins. Owning that policy is the
work; the rate limit as stated is the work, postponed.

---

## What follows (the part the question actually answers)

If wake is level-triggered on the *existence* of an obligation, then:

- **The watermark is not "where in the stream did we arrive" but "which obligations are
  settled."** That is a cursor-over-durable-state (mailbox + claim + reply evidence), not a cursor
  over arrival position. This is exactly round-1 T3's converged authority, and it survives exactly
  the crashes the edge watermark does not.
- **The handoff to the consumer is the only place "edge" belongs.** Sol localized the defect to
  the post-wake consumer cursor; the fix is *not* to edge the detector, it is to make the awakened
  harness advance the consume frontier and skip backlog it has already seen — the fallback being
  the S0-gamma `seen` sidecar. Detection stays level; consumption gets the frontier.
- **Rate limiting, if it appears, appears as a dismissal-counter threshold with an owned
  escalation path** (park to bench, never drop — the existing precedent), never as a clock ceiling
  that can silently eat the second event.

The one-line answer to the conducting question ("wake on arrival or on existence?"): **existence.**
Arrival is a hint; existence is the fact; and the watcher is the only seat in the fleet whose whole
job is to report the fact, not the hint.

---

*Filed blind per round protocol. Labels mine; rejection welcome in return. Key source lines this
argument rests on: `scripts/bifrost_wake.py` docstring (detect-only, "nothing here is consumed"),
the KNOWN SEAM comment (arm-time baseline sweep reverted because "the arm-onto-pending contract…
requires to wake"), `watch()`'s `min_tier=3` default, and the S0-gamma section ("every re-arm
re-detected the same packet").*
