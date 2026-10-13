# The teardown card (v2, finalised 2026-10-13 after the house calibration)

Daniel, 2026-10-13: "how do we expand reverse engineer into 'deconstruct and break down into first
principles, required steps and capibilities and verification' I want us to be able to reverse engineer and
deconstruct anything, from websites and api's to financial models to principles in the world." Then: "I
love your deconstruct the house, yes!" He saw Rimuru's Great Sage in it ("raphael deconstructing skills and
upgrading them"), so the card closes in Great Sage's report voice. The voice is play, and the substance
under it is strict. (The quotes are verbatim, his spelling included; checked against his message.)

v1 (`research/in-flight/deconstruct-the-house-2026-10-13/teardown-card.md`) was calibrated on our own house:
eight subsystem cards and a whole-house report. This is v2, which carries what that run taught (see the
changelog at the end). The skill that uses this card is `../SKILL.md`.

---

## 0. Header (fill it in before you start)

| field | entry |
|---|---|
| Target | Name it exactly. If the request did not name it, ask; never pick a target on Daniel's behalf. |
| Why (the route) | Understanding an artifact / improving our own system / a failure / building it ourselves / claiming it works / something with nothing to open (see the router in `../SKILL.md`) |
| Opened | Date and time, with the time zone |
| Seat | Who is writing this card |
| Scope and permission | Ours, open source, public sources only, or licensed to examine. Write down what is out of scope. |
| Will not touch | Private planes (described by role only: no sizes, counts or dates), running servers, port 8793, the GPU, and any write. Check in code that every "read" verb really is a read before running it; the house's look-alike writers (doctor, eye reads, recall-at, recall, knowledge-map and lookback without their kill switches, the wish-curate listing) are listed under Hard lines in `../SKILL.md`. |
| Expected footprint | Which hooks will fire and which counters your reads will bump |
| Question checklist | Each question, next to the evidence that would answer it. Revisit the list at the end and mark each one answered, partial or open. |

## 1. The eight rows (every teardown fills all eight; "unknown" is a valid, honest entry)

| row | question | example from a chip teardown |
|---|---|---|
| 1 Purpose | What is it for, and for whom? What outcome would make it worth keeping? Write the outcome as a test that someone could fail. For a law of nature, write the question you are asking and why it matters. | The market and workload it targets |
| 2 Observables | What can we see and measure from outside, without trusting its own description of itself? **Stamp every reading with its time.** | The die shot, benchmarks |
| 3 Mechanism | How does it turn inputs into what we observe? Explain every Row 2 observable, or list it as unexplained. | The microarchitecture |
| 4 First principles | The irreducible truths and constraints it rests on: laws, identities, protocols, incentives, the operator's values. **Each one gets two fields, a verdict, a "last measured" date and a falsifier (section 4).** If you cannot name the law or the measurement, it is an assumption dressed as an axiom. | Physics, the process node, Amdahl's law |
| 5 Capabilities | What would we need to HAVE to build or run it: skills, tools, data, access, money, time, people? **List what is missing.** | The fab, the IP, the talent |
| 6 Required steps | In what order would we build it from nothing, and what blocks what (the critical path)? **Also write the order they actually took, where you can see it, and what the difference cost.** | Tape-out order |
| 7 Invariants and failure modes | What must always hold? Mark each held, broken or unknown, with evidence. How does it break, and what does a break look like from outside? Check the seven signatures (section 7). | Thermals, yield |
| 8 Verification | Predictions that COULD FAIL, each with the cheapest test that would show it, **registered before the test** and read by direction (section 5). Run the cheap ones: at least three per subsystem. | Validation silicon |

## 2. The loop table (required whenever the target has a value chain)

Name every link and ask whether the signal flows back (`docs/pillar-analysis-method.md`, step 6). Use only
these codes:

| code | meaning |
|---|---|
| **C** | Closed: the signal flows back and something acts on it |
| **P** | Partly closed: name the weak link |
| **I** | Open on purpose: name the gate or guard (Daniel's gate, or a guard against Goodhart) |
| **O** | Open by defect: name the broken link, using one of the words below |

The broken links: **no reader** · **no clock** · **off the road** (the guard or join is not where the
traffic passes) · **starved horizon** or **wrong population** · **not built** or **never exercised** ·
**twin defect** · **collision** (two correct rules fight each other).

| loop (each link named) | status | broken or weak link | evidence |
|---|---|---|---|
| | | | |

A designed-open loop, where something is measured and nothing acts on it, is the most common real finding.

## 3. Labels (on every claim)

- **observed**: you saw it in code, data, telemetry, a run or a source, and you give the pointer: file:line,
  a command with its output and the time, a receipt path, a commit, or a URL with the date read.
- **inferred**: you reasoned it from observations. Name which ones.
- **unknown**: you did not look, could not look, or the evidence conflicts. Say which, and where you
  stopped (the search boundary). A bounded negative stays bounded: "not found in X" never becomes "absent".

One label per claim. **Observing that a sentence is written is not observing that it is true.** A
docstring, a README, a wiki or a textbook is observed as a document, and whether it is true is a Row 4
verdict or a Row 8 test. Quote it exactly: a refutation counts only if it answers what the text says (on the
house, "a ~1ms file read" was first refuted as if it priced the whole call).

## 4. Row 4 format: two fields and a verdict

| # | the claim, with its pointer | the evidence or law it rests on | verdict | last measured | falsifier | kept or broken today |
|---|---|---|---|---|---|---|
| | | | | | | |

The verdicts (use only these): **LAW** (an external law, cited) · **MEASURED** (an incident or measurement
with a receipt) · **VALUE** (the operator's stated value, quoted) · **DESIGN CHOICE** · **CONTINGENT**
(true here and now, for a reason that could change) · **STALE** (no longer true, or not measured since a
date you name) · **SCOPED** (true at some doors, times or populations, but stated as true everywhere) ·
**FALSE** (tested and wrong).

Ask every principle "when was this last measured?" On the house, 18 of the 27 false first principles were
stale, scope-dropped or unwired, and at least 2 were wrong from the day they were written. In a living system,
trap 1 is often trap 4 with a date on it, but do not assume decay: date when the principle was last true, or say
you cannot. A definition is not a LAW, and a policy built on a real asymmetry is a DESIGN CHOICE.

## 5. Row 8 format: predictions that could fail

| id | dir | prediction (written before the test) | what a defect would look like | test | result | verdict |
|---|---|---|---|---|---|---|
| | | | | | | |

**Direction:** **C** tests the target's own claim, so a FAILED C is a defect. **D** tests our suspicion, so
a HELD D is a defect. **F** tests a proposed fix, by replay. **G** tests a claim in our own report, or in a
sibling workflow's report.

Rules:
1. Register each prediction before its test, and keep the list with the card, not in a scratch folder.
2. Ask "could this test fail for the right reason?" An empty query is guaranteed to stay silent, and equal
   totals can hide different members. **Add a negative control when it is cheap.**
3. Cheapest test first.
4. Check in code that the verb is a read before running it. **Test writers by replaying them against a fake
   store**, never on live state.
5. Label weak tests as weak (for example, a replication of a reading taken hours earlier, or a lookup in the
   same sources Row 2 used). Report the failures first.
6. Count the tally by the direction rule, row by row. If a row's direction makes the tally read wrongly, fix the
   direction or the count, never the rule.

## 6. The traps (name them, and the row where you saw them)

1. **False first principles:** assumptions dressed as axioms.
2. **Chesterton's fence:** never propose removing a part before stating why it exists.
3. **Reductionism:** some behaviour lives in the loop, not the parts.
4. **The map is not the territory:** only a prediction that could fail closes the gap.
5. **Goodhart:** verifying the metric instead of the thing.

## 7. Failure signatures (what a break looks like from outside)

1. **Quiet green** (a fault stuck at 0): the break reads as health.
2. **Always red** (a fault stuck at 1): an alarm that never clears says nothing.
3. **Twin fix:** fixed in one organ, still alive in its sibling. Search for the same shape.
4. **A reader built before the writer's contract was true.**
5. **One name, many tables.**
6. **Test residue in production.**
7. **The observer is in the territory:** declare your footprint (section 8).

## 8. Side effects I caused (a required block)

List every write your "read-only" pass caused, so nobody mistakes it for organic traffic: hooks that fired
(and how many times), counters bumped, injection rows written, seat records beaten, and network calls to
outside services. If you ran a write-capable verb, even one a brief called a read, name it plainly as a writer,
say that you ran it, what it did, and what it may have done; write "effect unknown" where you cannot tell. Never
call it a read. If you caused none that you know of, write "none known", followed by the search boundary.

## 9. Synthesis, when there are several cards

1. Each card's summary carries **all eight rows** plus its loop table. If it does not, budget time to
   re-read the full cards.
2. **Resolve the unknowns across cards** before writing the whole report: one card's unknown is often
   another card's observation.
3. Re-run the cheapest observables at synthesis time and record any that moved. A live system has a
   half-life measured in hours.
4. Normalise every loop and verdict into the fixed vocabularies above. Do not invent new phrasings.

## 10. The Great Sage report (each card closes with it)

The words map one-to-one onto the labels, which keeps the voice close to the evidence. It is not automatic
(on the house, one Notice carried an inferred cause), so check each Notice line for inferences:

> **Notice.** (observed facts, with pointers)
>
> **Analysis.** (inferences, each naming the observations it rests on)
>
> **Unknown.** (what we did not or could not see, and the search boundary)
>
> **Proposal.** (what to change, smallest first; never propose a deletion without the reason the part exists)
>
> **Verification.** (the predictions that could have failed, and whether they did)
>
> **Recommendation.** (the seat's own view: what first, and why)
>
> **Proceed?** YES / NO (the operator's gate: every proposal waits for Daniel, and no seat answers this line)

The play goes in the framing ("Notice.", "Analysis complete.", a dry aside). Strictness goes in the content:
no adjective may claim more than the evidence, and no number appears without its pointer.

---

## Skeleton (copy from here)

```markdown
# Teardown: <target>

| field | entry |
|---|---|
| Target | |
| Why (route) | |
| Opened | YYYY-MM-DD HH:MM TZ |
| Seat | |
| Scope and permission | |
| Will not touch | |
| Expected footprint | |

## Question checklist
| question | evidence that would answer it | state (answered / partial / open) |
|---|---|---|

## Row 1 Purpose
## Row 2 Observables (each stamped with its time)
## Row 3 Mechanism
## Loops
| loop | status (C/P/I/O) | broken or weak link | evidence |
|---|---|---|---|
## Row 4 First principles
| # | claim + pointer | evidence or law | verdict | last measured | falsifier | kept or broken |
|---|---|---|---|---|---|---|
## Row 5 Capabilities (list what is missing)
## Row 6 Required steps (the ideal order, the actual order, what the difference cost)
## Row 7 Invariants and failure modes (check the seven signatures)
## Row 8 Verification
| id | dir | prediction | what a defect looks like | test | result | verdict |
|---|---|---|---|---|---|---|
## Traps seen (trap, row, evidence)
## Side effects I caused
## Great Sage report
> **Notice.**
> **Analysis.**
> **Unknown.**
> **Proposal.**
> **Verification.**
> **Recommendation.**
> **Proceed?** YES / NO (Daniel's)
```

---

## Changelog: v1 to v2 (what the house taught the method), plus the review corrections (row 14)

The source is section 11 of `research/in-flight/deconstruct-the-house-2026-10-13/the-house-deconstructed.md`.

| # | what the house run showed | change in v2 |
|---|---|---|
| 1 | Loop altitude was the most productive lens on all eight cards, but they described loop status in about fifteen different phrasings | Section 2: a required loop table with a fixed vocabulary (C, P, I, O, plus the named broken links) |
| 2 | "Held" is good news for a house claim and bad news for an auditor's hypothesis. One card scored 13 of 13 held and another 3 of 14, and both were reporting the same kind of defect. | Section 5: a direction column (C, D, F, G) and a "what a defect would look like" column |
| 3 | On Row 4, "observed" was used both for "the sentence is written" and for "the sentence is true", and the cards invented eleven verdict phrasings | Section 3's rule, plus section 4: two fields and a fixed verdict list |
| 4 | 18 of the 27 false first principles were stale, scope-dropped or unwired (and at least 2 were wrong from birth) | Section 4: the "last measured" and falsifier columns |
| 5 | Three tests passed without testing anything; the two that had negative controls were the cleanest | Section 5, rule 2: "could this fail for the right reason?" and negative controls |
| 6 | A brief's "read" (doctor) can write the pager. One card caught it in code, two ran it as a read, and the house seat declined it. Eye reads, recall-at and listings write too. | The header's "will not touch" field and section 5, rule 4: check in code that a verb is a read, and replay writers against a fake store. Section 8: a writer you ran is named as one, with "effect unknown" where you cannot tell |
| 7 | A read-only fan-out still beats seat records, pushes injections and bumps counters | Section 8: a required "side effects I caused" block |
| 8 | The summary format dropped four rows, which forced a re-read of about 300 KB | Section 9, item 1 |
| 9 | One card's unknown was often another card's observation | Section 9, item 2 |
| 10 | The territory moved during the run (the arsenal gained a core import about 20 minutes after it was measured) | Row 2's time stamps and section 9, item 3 |
| 11 | "Proceed?" was used both as Daniel's gate and as the seat's recommendation | Section 10: "Recommendation" belongs to the seat; "Proceed?" belongs to Daniel alone |
| 12 | On Row 6, the useful content was the gap between the ideal order and the order actually taken | Row 6 now asks for both orders and for what the gap cost |
| 13 | The Great Sage voice mostly held; it leaked once, when the house report's Notice carried an inferred cause | Kept, with a check on each Notice line (section 10). The failure signatures (section 7) were added from the whole-house report's section 8b. |
| 14 | An adversarial review (2026-10-13) found the evidence sound and the write-up overstated in places: a writer called a read, private numbers copied out, a guess presented as a law, a misquoted docstring, a tally against its own rule | Section 3: quote a refuted claim exactly. Section 4: date decay instead of assuming it. Section 5: count the tally row by row. Section 8: name writers as writers. Header: no sizes, counts or dates for private planes. Details in `house-calibration.md` |
