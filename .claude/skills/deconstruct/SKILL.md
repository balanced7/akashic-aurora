---
name: deconstruct
description: Use when asked to deconstruct, break down, take apart, tear down or understand from first principles anything (a website, an API, a financial model, a game economy, a law of nature, a process, a product, or our own house and its subsystems), and when asked "how does this really work?", "what are its first principles?", "what would it take to build this?", "what are the steps and capabilities?" or "how would we verify that?". Use BEFORE claiming you understand a system, before rebuilding one, and before proposing changes to one you have not taken apart. It sends artifact reverse engineering, our own pillars, failures and claims that something works to their own skills.
---

# Deconstruct

Daniel, 2026-10-13: "I want us to be able to reverse engineer and deconstruct anything, from websites and
api's to financial models to principles in the world." This skill is the umbrella for that. It takes any
target apart into **purpose, observables, mechanism, first principles, capabilities, required steps,
invariants and verification**, and closes with a Great Sage report. The report borrows the voice of
Rimuru's Great Sage, who deconstructs a skill and proposes the upgrade; Daniel picked that voice. The voice
is play. Everything under it is strict.

**Iron Law: no claim without its label and its evidence, and no understanding claimed without a
prediction that could fail.** Every claim carries one label (observed, inferred or unknown) and a pointer
that someone else could follow tomorrow. You have not understood a thing until you have written down a
prediction about it that could have come out wrong, and run the cheapest test of it.

## Route first: what are you taking apart, and why?

| What you are taking apart, and why | Go to | What this skill still adds |
|---|---|---|
| **Understanding an artifact:** a binary, an app, a game client, a file format, a shader, a frame, a sound, a device, a protocol, a capture | `.claude/skills/reverse-engineering/SKILL.md`. Its scope list, legal map and "never on the host" rules apply before any tool is opened. | Rows 1, 4, 5 and 6 and the loop table, when you want the whole picture and not only the mechanism |
| **Improving our own system:** a pillar, a subsystem, the whole house | `docs/pillar-analysis-method.md` (triangulate, diagnose at loop altitude, fix with evidence) | Its triangulation is written into the eight rows. The house run is the calibration case. |
| **A failure:** a bug, a red test, a hook that misbehaves, output you did not expect | `.claude/skills/root-cause-before-fixes/SKILL.md` | Row 7's failure signatures: once the cause is found, sweep for the same class elsewhere |
| **Building it ourselves** | All eight rows here, then a clean room: `.claude/skills/reverse-engineering/references/method-legal-cleanroom.md` | Rows 5 and 6 become the build plan, and Row 8's predictions become the conformance tests |
| **Claiming it works** | `.claude/skills/verified-done/SKILL.md` | Nothing. That skill decides. |
| A shader or a look | `.claude/skills/shader-craft/SKILL.md`, "Dissecting a shader" | Nothing extra |
| **Understanding something with nothing to open:** a model, an economy, a law of nature, an institution, an argument | Stay here and fill the eight rows | Everything |

If you cannot tell which row applies, ask what the outcome is meant to be. Knowledge means route 1 or the
last row. A better house means route 2. A fix means route 3. Something we will own means route 4. A claim
means route 5.

**The router depends on sibling skills.** The reverse-engineering skill and the shader-craft "Dissecting a
shader" section ship from other workflows. `tests/test_deconstruct_skill_router.py` checks that every repo path
this skill names exists and is tracked by git, and skips (with the reason) while one is still uncommitted. Commit
this skill together with, or after, those siblings.

**Hard lines (no exceptions):**
- Whatever the reverse-engineering skill puts out of scope stays out of scope here: DRM, cheats, other
  people's systems, other people's assets. A teardown of someone else's product uses public sources and
  our own legitimate use of it.
- Never pick the target on Daniel's behalf. If he says "the app" or "the game", ask which one.
- A financial teardown explains how a model is built. It is not investment advice, and no seat gives
  personal financial advice.
- Private planes (`private/`, personal memory, Daniel's playing data, the story oracle, the private shader
  corpus, spend and wallet figures) are described by their role only: no sizes, counts or dates, because
  "existence metadata is a leak" (`core/trust/private_plane.py:17-19`). A teardown that needs them is filed in
  the private tree, because this repo is public.
- On our own house, stay read-only unless Daniel says otherwise. **Check in code that a "read" verb really
  is a read before you run it.** These look like reads and write:
  - every `doctor` round, with or without `--page`: it can push page-grade findings to the human pager, retract
    standing pages, delete their escalation keys and set stall keys (`core/comm/doctor.py:138-155`,
    `:1604-1608`, `:1640-1642`, `:1653-1720`);
  - every eye read (`eye find`, `freq`, `standing`, `stats`): opening the index rewrites a meta row
    (`core/eye/index.py:456-530`);
  - every `recall-at` call, including the CLI verb: it appends a silence row;
  - `recall`: it may bump counters;
  - `knowledge-map` and `lookback`: they bump counters unless `AKASHIC_KMAP_NO_COUNT=1` or
    `AKASHIC_LOOKBACK_NO_COUNT=1` is set;
  - the `wish-curate` listing: it takes a file lock whose sidecar lives in `docs/`.

  If you ran a writer by mistake, say so in the side-effects block, with what it did, what it may have done, and
  "effect unknown" where you cannot tell.

## The eight rows

Every teardown fills all eight rows. "Unknown" is a valid, honest entry.

| row | the question | done when | chip-teardown analogy |
|---|---|---|---|
| **1 Purpose** | What is it for, and for whom? What outcome would make it worth keeping? For a law of nature, write the question you are asking and why it matters. | The outcome is written as a test that someone could fail | The market and workload it targets |
| **2 Observables** | What can we see and measure from outside, without trusting its own description of itself? Stamp each reading with its time. | At least one observable comes from outside the target's self-report | The die shot, benchmarks |
| **3 Mechanism** | How does it turn inputs into what we observe? | Every Row 2 observable is explained or listed as unexplained | The microarchitecture |
| **4 First principles** | The irreducible truths and constraints it rests on: laws, identities, protocols, incentives, the operator's values. Each principle gets two fields and a verdict (below). | Every principle names its law or its measurement, and the date it was last measured | Physics, the process node, Amdahl's law |
| **5 Capabilities** | What would we need to HAVE to build or run it: skills, tools, data, access, money, time, people? | What is missing is listed explicitly | The fab, the IP, the talent |
| **6 Required steps** | In what order would we build it from nothing, and what blocks what (the critical path)? Where you can see it, also write the order they actually took and what the difference cost. | The critical path is named | Tape-out order |
| **7 Invariants and failure modes** | What must always hold? How does it break, and what does a break look like from outside? | Each invariant is marked held, broken or unknown, with its evidence | Thermals, yield |
| **8 Verification** | Predictions that could fail, each with the cheapest test that would show it. Run the cheap ones. | At least three run per subsystem, with their results | Validation silicon |

**Add the loop table whenever the target has a value chain**, which is nearly always. Name every link and
ask whether the signal flows back (`docs/pillar-analysis-method.md`, step 6). On the house this was the
most productive lens on all eight cards, so it gets a fixed vocabulary (below), not prose.

## The labels

- **observed**: you saw it in code, data, telemetry, a run or a source, and you give the pointer: file:line,
  a command with its output and the time, a receipt path, a commit, or a URL with the date read.
- **inferred**: you reasoned it from observations. Name which ones.
- **unknown**: you did not look, could not look, or the evidence conflicts. Say which, and where the search
  stopped. **A bounded negative stays bounded.** "Not found in X" never becomes "absent".

Strict rules:
- One label per claim. A sentence that carries two claims gets two labels.
- **Observing that a thing is written is not observing that it is true.** A docstring, a README, a wiki, a
  status line or a textbook is observed as a document. Whether its claim is true is Row 4's verdict, or a
  Row 8 test. Quote it exactly: a principle is only refuted if the refutation answers what the text says.
- Stamp observables with their time, and re-run the cheapest ones when you synthesise. A live system
  moves: on the house, the arsenal was measured as fully decoupled and gained its first core import about
  20 minutes later.

## Row 4: two fields and a verdict for every first principle

Each principle is written as: **the claim with its pointer · the evidence or law it rests on · a verdict ·
when it was last measured · its falsifier** (what result would prove it wrong).

| verdict | meaning |
|---|---|
| **LAW** | An external law, cited: physics, mathematics, an accounting identity, a protocol standard |
| **MEASURED** | An incident or measurement with a receipt |
| **VALUE** | The operator's stated value, quoted with its source |
| **DESIGN CHOICE** | Someone chose it, and it could have been otherwise |
| **CONTINGENT** | True here and now, because of a circumstance that could change |
| **STALE** | True when written, but not true now, or not measured since a date you name |
| **SCOPED** | True at some doors, times or populations, but stated as true everywhere |
| **FALSE** | Tested and wrong |

If you cannot name the law or the measurement, the principle is an assumption dressed as an axiom (trap 1).
A definition is not a law, and a policy built on a real asymmetry is still a DESIGN CHOICE.
In a living system, ask "when was this last measured?" Of the house's 27 false first principles, 18 were
stale, scope-dropped or unwired, and at least 2 were wrong from the day they were written. Do not assume a false
principle decayed; date when it was last true, or say that you cannot.

## The loop table: a fixed vocabulary

| code | meaning |
|---|---|
| **C** | Closed: the signal flows back and something acts on it |
| **P** | Partly closed: name the weak link |
| **I** | Open on purpose: name the gate or guard (Daniel's gate, or a guard against Goodhart) |
| **O** | Open by defect: name the broken link from the list below |

The broken links: **no reader** (something is measured, and nothing acts on it) · **no clock** (a hand
crank that nobody turns) · **off the road** (the guard or join sits where the traffic does not pass) ·
**starved horizon or wrong population** (the reader sees too little, or the wrong things) · **not built or
never exercised** · **twin defect** (fixed in one organ, still alive in its sibling) · **collision** (two
correct rules fight each other).

In hardware terms, an O loop is a gauge with no wire to the hand. A designed-open loop, where something is
measured but nothing acts, is the most common real finding. On the house, 14 of the 26 open loops needed no
new idea: only a reader for a signal the house already produced, or a clock for a crank it already had.

## Row 8: predictions that could fail

Write every prediction as a row: **id · direction · prediction (written before the test) · what a defect
would look like · test · result · verdict**.

| direction | what it tests | how to read it |
|---|---|---|
| **C** | The target's own claim about itself | A FAILED C row is a defect |
| **D** | Our suspicion (the auditor's hypothesis) | A HELD D row is a defect |
| **F** | A proposed fix's effect, by replay | A held F row supports the fix |
| **G** | A claim in our own report (ours or a sibling workflow's) | A failed G row means our report is wrong |

Without the direction, "held" means nothing. On the house, one card scored 13 of 13 held and another 3 of
14 held, and both were reporting the same kind of defect. Count your tally by the stated rule, row by row.

1. **Register first.** Write the prediction down before you run the test, and keep it with the teardown.
   A scratch folder gets cleared (lesson `a_conclusion_outlives_the_evidence_unless_something_moves_it`).
2. **Ask "could this test fail for the right reason?"** An empty query is guaranteed to stay silent, and
   equal totals can hide different members (on the house, equal atom totals in the store and the journal hid a
   swap in both directions). A lookup in the same sources you used for Row 2 cannot fail either; label it weak.
   **Add a negative control when it is cheap:** a string that is not on the page must return 0. The two tests on
   the house that had controls were the cleanest in the run.
3. **Cheapest first:** a read, a header, an arithmetic check, a published value. Escalate only when a cheap
   test cannot answer the question.
4. **Prefer replay against a fake store** for anything that writes. Never test a writer on live state to
   "see what happens".
5. **Run at least three per subsystem.** Report the failures first, and label a weak test as weak (for
   example, a replication of a reading taken hours earlier).

## The procedure

0. **Route** (the table at the top). Name the target. If it was not named, ask.
1. **Open a card** from `references/teardown-card.md`. Fill in its header: the target, the time, the seat,
   the scope and permission, what you will not touch, and the footprint you expect to leave.
2. **Write the question checklist**, each question next to the evidence that would answer it.
3. **Row 2 before Row 3.** Measure from outside before you read the target's own description of itself.
4. **Fill the mechanism, the loop table, the first principles, the capabilities, the steps (both orders)
   and the invariants.**
5. **Row 8:** register the predictions, run them, record the results.
6. **When there are several cards:** each card's summary carries all eight rows. Resolve the unknowns across
   cards before writing the whole report, because one card's unknown is often another card's observation.
   Then re-run the cheapest observables.
7. **Name the traps you saw**, and the row where you saw each one.
8. **Close with the Great Sage report** and the "side effects I caused" block. Proposals wait for Daniel.

## The five traps (name them when you see them)

1. **False first principles: assumptions dressed as axioms.** On the house: the recall-at docstring prices a
   warm file read at about 1 ms, and it measured 9 ms, while the whole call (153 ms) was never priced; "unknown
   agents are quarantined" (282 lessons were written by 52 ids that resolve as quarantined, and the sentence was
   wrong at the shell door from the day it was written). *Test:* name the law or the measurement, and its date.
2. **Chesterton's fence: never propose removing or redefining a part before stating why it exists.** On the house,
   each of the 16 proposals carries the reason its part exists. For example, the archive's refuse-shrinking law
   stays because it caught a real bug on 2026-08-11 (`scripts/ops/archive_transcripts.py:133-138`), and the
   width gauge keeps its definition because it excludes claimed and verifying rows on purpose
   (`core/coord/task_ledger.py:576-577`).
3. **Reductionism: some behaviour lives in the loop, not in the parts.** On the house, every part writes
   well (no torn lines in 116,693), and still 26 of 54 loops are open. The identity bug was one story
   running through three organs, and no single card could see it.
4. **The map is not the territory: only a prediction that could fail closes the gap.** On the house,
   `status` printed four calm lines while 23 lessons lived only in the copy with no journal.
5. **Goodhart: verifying the metric instead of the thing.** On the house, the reconciliation gate passes
   any document that contains the letters "gate", and equal totals hid a membership swap in both directions.

## Seven failure signatures (what a break looks like from outside)

The house run found these, and every one carries over to other systems:
1. **Quiet green** (a fault stuck at 0): the break reads as health. Equal totals, a clean verify, an audit
   that says MATCH. This was the signature seen on the most cards (four of eight) on the house.
2. **Always red** (a fault stuck at 1): an alarm that never clears carries no more information than one
   that never fires.
3. **Twin fix:** the defect is fixed in one organ and still alive in its sibling. After any finding, search
   for the same shape elsewhere (lesson `when_a_fix_primitive_is_born_sweep_the_class_that_birthed_it`).
4. **A reader built before the writer's contract was true.** It produces false alarms, false refusals and
   gates that let everything through.
5. **One name, many tables:** the same entity is spelled differently in places that never join up.
6. **Test residue in production:** fixtures, locks or identities that a test left on the live plane.
7. **The observer is in the territory:** your reads bump counters, beat seat records and push injections.
   Declare that footprint.

## The Great Sage report (the voice)

Each card closes with this report. Its words map one-to-one onto the labels, which keeps the voice close to the
evidence. It is not automatic: on the house, one Notice carried an inferred cause, so check every Notice line for
inferences before you close.

| word | what it carries | its source |
|---|---|---|
| **Notice.** | Observed facts, each with its pointer | observed |
| **Analysis.** | Inferences, each naming the observations it rests on | inferred |
| **Unknown.** | What we did not or could not see, and the search boundary | unknown |
| **Proposal.** | Changes, smallest first. Each one states why the part it touches exists. | trap 2 |
| **Verification.** | The predictions that could have failed, and whether they did | Row 8 |
| **Recommendation.** | The seat's own view of what to do first | the seat |
| **Proceed?** | YES / NO | **Daniel alone** |

**Voice rule:** the play is in the framing, and the strictness is in the content. Great Sage may be smug.
Great Sage may not be wrong. "Notice." and "Analysis complete." are welcome, and so is a dry aside.
Three things are not allowed: an adjective that claims more than the evidence ("clearly broken", "huge"), a
number without its pointer, and a seat answering its own "Proceed?".

> **Notice.** An unauthenticated `GET /repos/balanced7/akashic-aurora` (curl, 2026-10-13 about 10:20 EDT)
> returned `X-RateLimit-Limit: 60`. Over four calls, Remaining fell 59, 58, 57, 56. The third call sent
> `If-None-Match` and got `304 Not Modified`.
>
> **Analysis.** The 304 cost one unit, exactly like a 200 (this rests on the second, third and fourth
> readings). The belief that "a 304 is free" does not hold for a caller without a token.
>
> **Unknown.** Whether a 304 is free with a token: not tested. Search boundary: one endpoint, four calls, one
> network address, one minute.
>
> **Proposal.** Any house tool that polls GitHub without a token counts every call against its budget,
> 304s included. Nothing is removed.
>
> **Verification.** 4 predictions: 3 held and 1 failed (A4, the useful one).
>
> **Recommendation.** Adopt the budgeting rule before any polling tool is built.
>
> **Proceed?** YES / NO. *Analysis complete. Awaiting the master's answer.*

## Worked mini-examples

Five targets, eight rows each, in `references/worked-examples.md`: a website (akashiclabs.io: the repo is a map
that never mentions the cache every reader goes through), an API (GitHub REST: "a 304 is free" fails for a caller
without a token), a financial model (a DCF: identities are the gears and bets are the fuel; three quarters of the
value is a bet on year six onward), a principle in nature (the aurora's red crown: altitude decides which
oxygen line survives), and a game economy (Archero, public sources only: 3:1 fusion compounds, and DPS × EHP hides
one target versus a crowd).

## The calibration case: the house (2026-10-13)

The card was first calibrated on our own house: 8 subsystem cards plus a whole-house report in
`research/in-flight/deconstruct-the-house-2026-10-13/`, summarised in `references/house-calibration.md`. In
short: the data plane is sound and the control plane is where it breaks (26 of 54 loops open by defect). The
doctor rule was a partial catch: **1 card caught it in code, 2 ran it as a read, the house seat declined it.** An
adversarial review then found the evidence sound and the write-up overstated in places; those fixes are listed in
the same reference.

## House words (a short glossary)

- **The house:** Akashic Aurora, this repo plus its live services (Redis on 16379, the bus, the runners).
- **Seat:** one live agent session with an agent id. **Runner:** the process that gives an API model a body, an
  inbox and a lock.
- **Organ:** a subsystem with its own writer, record and reader (boot, recall-at, the doctor, the eye).
- **Twin:** two copies or sibling organs that should agree (two hook copies; boot's ranker and recall-at's). A
  **twin defect** is fixed in one and alive in the other.
- **The road:** the path every commit actually walks (the git hooks), as opposed to an optional door such as
  `ship.py`. A guard **off the road** is one most traffic never meets.
- **Pager:** the human-facing alarm list (`core/comm/pager.py`), rendered into every live seat's prompt.
- **Doctor:** the fleet's liveness reader (`core/comm/doctor.py`). It also writes the pager.
- **T418:** the identity law: boot refuses a session whose identity stamp names someone else.
- **Scribe:** a proposed job that joins commits to their ledger rows.
- **Fence:** a design round with two blind halves and a reconciliation.

## Red-flag phrases (each one means STOP)

- "It obviously works like…" (a mechanism with no observable behind it)
- "That's a first principle" (name the law or the measurement, and its date)
- "We understand it now" (show the prediction that could have failed)
- "Nothing reads that" or "it's absent" (bound it: say what you searched, where, and when)
- "This part is unused, remove it" (trap 2: first say why it exists)
- "All green" or "the totals match" (quiet green: could this check have failed?)
- "Its status page / README / docstring says…" (that is the map; go and measure the territory)
- "It's only a read" (check in code that it writes nothing; see the list under Hard lines)
- "They all decayed" (date when each was last true, or say you cannot)
- "The model says it's worth X" (the bets say so; give the range and the bets that move it)
- "Proceed? YES", written by a seat (that line is Daniel's)

## Files

- `references/teardown-card.md`: the card (v2, finalised after the house calibration). It holds the fill-in
  skeleton, the header, the footprint block, and a changelog from v1 to v2.
- `references/worked-examples.md`: the five worked mini-examples.
- `references/house-calibration.md`: the calibration case and what its review fixed.
- `tests/test_deconstruct_skill_router.py`: pins that every repo path named here exists and is tracked by git.
- The method it extends: `docs/pillar-analysis-method.md`. Its siblings: `.claude/skills/reverse-engineering/`,
  `.claude/skills/root-cause-before-fixes/`, `.claude/skills/verified-done/`, `.claude/skills/shader-craft/`.
- The calibration record: `research/in-flight/deconstruct-the-house-2026-10-13/`. As of 2026-10-13 that folder
  is invisible to knowledge-map and lookback (house checks H1 and H2), which is one reason the card now lives
  here.
- Not mirrored into `.agents/skills/`, where four skills live for non-Claude seats (shader-craft is not mirrored
  either). Whether to mirror it is a choice for Vandor and Daniel, not a broken rule.
