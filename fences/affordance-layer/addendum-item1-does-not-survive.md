# affordance-layer — ADDENDUM: item 1 of my own build spec does not survive contact

Written 2026-10-06 by claude (Vandor#428ba6c4), hours after sealing
`fences/affordance-layer/reconciliation.md`. The reconciliation is sealed and stays as written;
this is the correction that belongs beside it rather than inside it.

## What item 1 said

> **Fix the placeholder-for-a-value-the-emitter-already-holds sites.** One line each, no new
> abstraction, no checker, no ratchet. Heimdall verified three live with zero search effort […]
> My census claims eleven; eight are unaudited and that is stated, not assumed.

I went to do the eight. **The class barely exists.** Of the sites that actually matter, almost none
are "the emitter holds the value and prints a placeholder." My census — and Heimdall's reading of
it, and my own ratification of both — collapsed **four different things** into one defect.

## The four classes

Census method: every emitted string in `core/`, `scripts/`, `agent/` and `agent_cli.py` containing
`agent_cli.py` and a `<placeholder>`; 54 hits. The high-signal subset is the 8 that substitute
*some* fields with real values while leaving others as placeholders — demonstrating the emitter was
templating and chose a placeholder for one field.

**(a) The emitter holds it → substitute. The real defect.**
After inspection this class has **one** member, and it is conditional:
`core/comm/triage_park.py:112` and `agent_cli.py` (defer) each print a list of records carrying ids,
then one generic trailer — `unpark <parked_id>`, `--done <id>`. For N>1 the placeholder is *correct*:
the reader must choose which. For **N==1 there is nothing to choose**, and the placeholder is pure
friction — the reader copies the line, gets a literal, and goes back to read the id off the row
above. One item is also the common case. **Fixed** in this commit, both sites, with the N>1 form
also now carrying a concrete example.

**(b) The emitter cannot know it, because it depends on the READER.**
`core/comm/doctor.py:467` and `:753` print `--by <you>`; `agent_cli.py:6361` prints `--by <you>`;
`:6457` prints `--by <operator>`. Note that `doctor.py:467` already substitutes a real `--reason`,
so the *only* unfilled field is the reader's own identity — which the emitter genuinely does not
have, because it does not know whether Daniel or a seat will run the line. **These are not
substitution defects.** They are Heimdall's V2 finding wearing item 1's clothes: "runnable" depends
on the reader's execution surface, and the remedy is **per-reader rendering at emit time**, which is
item **3** of the same spec. A seat running `doctor` could be handed `--by claude`; the same text
rendered into Discord should say `--by daniil`. Substituting one guess at emit time would be wrong
half the time, silently.

**(c) The emitter deliberately does NOT hold it, for a measured reason, and substituting would be a
regression.**
This is the important one, because it is the citation the fence leaned on hardest.
`agent/harness/context.py:266` prints `mailbox {agent_id} --state <sha> | --open <sha>`.
Heimdall's V4 reads: *"the emitter is iterating mailbox entries and holds the sha per entry; it
prints `<sha>`."* **It is not iterating.** The code immediately above it says so, in a comment
written by whoever optimized it:

> *"Three Redis calls, size-independent. The first two cuts of this line cost 3.8s and 3.2s per
> boot […] An orientation surface that taxes every boot stops being orientation."*
> *"Body availability is deliberately NOT counted here: it needs a read per entry, which is the
> cost this rewrite removed."*

The emitter holds **counts**, by design, because holding the shas cost 3.8 seconds on every boot.
Filling that placeholder would re-introduce a per-entry read that was deliberately removed. The
citation is accurate and the premise attached to it is false — and acting on item 1 as ratified
would have undone a measured performance fix that explains itself in a comment four lines up.

**(d) Genuinely generic instruction text.** `scripts/generators/gen_doors.py:64` writes
`py agent_cli.py <verb>` into generated documentation. Correct as-is; nothing to fix.

## The reorder

Item 1 is **retired as written**. What was assigned to it redistributes:

- the one real member → **done in this commit** (N==1 concretization, two sites);
- class (b), the `<you>`/`<operator>` family → **item 3**, per-reader rendering. It was always
  item 3's work; I double-counted it as a cheap substitution win;
- class (c) → **not a defect**. `context.py:266` is correct and its placeholder should stay, with
  this addendum as the reason the next reader does not "fix" it;
- class (d) → not a defect.

So the spec's cheapest-first ordering was wrong in a specific, instructive way: **I counted the
same finding twice** — once as a trivial substitution (item 1) and once as an architectural change
(item 3) — which made item 1 look like the cheap win and inflated the apparent size of the problem.
Eleven sites was never eleven defects.

## What this says about the round

The fence worked exactly as intended and still shipped a wrong item, because **both reviewers and
I were reasoning about the same census, and the census was the thing that was wrong.** Heimdall
explicitly bounded himself on this — *"Every census number in the brief is unverified by me… I
confirmed three placeholder sites exist by direct read"* — and he was right about all three
existing. "A placeholder is here" and "the emitter holds the value" are different claims, and the
census asserted the second while only ever measuring the first.

Navi, independently, is the one who saw this coming in a different guise: her V4 showed the 29/97
ratio was *"a static classification, not a paste-test"* and errs in both directions. Same disease,
different number. **A reading that looks like a measurement will survive two blind reviewers if
both of them are handed it as given** — the blind halves decorrelate the *reasoning*, not the
*evidence*, and nothing in the method catches a bad census except someone going to do the work.

Practical rule I am taking from this: **when a brief hands reviewers a count, the count itself needs
a named derivation and a sample, or it must be labelled as a reading.** Mine said "eleven places"
with no sample and no derivation, and three of us built an ordering on it.
