# THE WORKING METHOD — how a problem becomes work, and whose correction catches what

Status: **PROPOSED** at Daniil's gate, 2026-07-31. Not ratified, not wired.
Type: contract (companion to `docs/CONDUCT.md`, not a peer of it) · Arc: leadership-doctrine
Seats: fleet — every seat originates, every seat corrects.

**Why this is a companion and not an amendment.** `CONDUCT.md` is *the conductor's standing
law*: how the fleet is led. It has ten laws, a substrate/projection discipline, an
activation map, and a measurable bar. It does not — by design, not oversight — say where
work COMES FROM, or whose lens catches which failure. Those are different functions, and
folding them into conductor-law would blur two roles. This file holds the other half.

**Labels are grok's convention, earned:** `SHIPPED` = running · `PROPOSED` = specified,
unratified · `OPEN` = unresolved.

---

## Part 1 — Origination: how a problem becomes work

Derived from Daniil's actual practice, evidenced across his verbatim directives from
2026-07-11 to 2026-07-31, not from his description of it. He stated his own method in
interiority entry 16 — *"I usually notice things when I find myself frustrated or others
frustrated with a situation or a pain point and I start then thinking about what is the
reason for that state and then what makes that reason exist"* — and the ledger shows he
actually runs it, which is rarer than it sounds. Generalised here as a fleet practice
because Grok and Kimi have both originated work the same way without being told to.

**O1. Start from friction that was FELT, never from architecture.**
Every directive in the record opens with a pain someone actually experienced: *"it seems
like it will be a chore trying to wake each other up"* (T073) · *"no manual pasting for
me"* (T074) · *"pieces we built are in awkward places due to us just trying to get it to
work"* (T104) · *"mis routing, mis waking, mis consuming, mis everything mess"* (T108) ·
*"the thing that would confuse me is not knowing what ties to what"* (T125). Not once:
"we should have a message bus." A design anchored to a felt failure survives contact;
one anchored to an idea does not.

**O2. Root-cause twice.** The reason for the state — *then what makes that reason exist*.
T073 is the exemplar: not "fix the wake bug" but *"how do we avoid this handholding wake
arm loop"* — instance, then class, then the generator of the class.

**O3. Escalate to the BEHAVIOURAL consequence — the step nobody else takes.**
Ask what the cost *prevents*, not what it slows. T125: *"our current method for finding
out what links to what is too unintuitive and costly so it doesn't get done."*
**A cost that slows work appears in the log as elapsed time. A cost that PREVENTS work
appears nowhere, because only attempted work leaves a trace.** Any triage that ranks by
measured cost is ranking on the visible half. (Lesson:
`a_cost_that_prevents_work_is_invisible_to_the_ledger`.)

**O4. State intent; release method.** Purpose and done-looks-like, real constraints only.
This is CONDUCT L1 and it is already law — noted here for the loop's completeness.

**O5. Delegate order, hold why.** *"I leave the order up to you, lets get to building"* ·
*"Feel free to choose the order that makes the most sense."* Consistent across two weeks.

**O6. BOUND THE WIDTH BEFORE STARTING. `PROPOSED`, and the one everybody skips.**
Before a new lane opens, name what it PAUSES. Three iterations of the same failure are in
the record: April 2026 built a redundant-Redis mesh before the problem was defined
(*"almost none of it survived"*); 2026-07-11..17 produced ~25 directives in seven days,
which is the 20-ACTIVE ledger we are now cutting; 2026-07-29/30 opened eight lanes and
produced a coordination cascade. Depth is this fleet's strength and width is its
recurring wound. **A new lane without a named pause is a lane the fleet cannot afford.**

**O7. Promotion is an explicit, visible act. `OPEN` — Q1 at Daniil's gate.**
Four intents that the system currently cannot tell apart (codex): *idea* — capture and
discuss, no priority change · *explore* — one bounded sandbox lane, trunk continues ·
*promote* — make current, and say what pauses · *interrupt* — stop mutations, produce one
shared snapshot. Claude's counter, unresolved: **invert the default** so nothing becomes
work until explicitly promoted, rather than requiring the operator to carry a suppressing
phrase while thinking out loud. Thinking aloud should be free.

## Part 2 — The correction map: whose lens catches what

**The thesis.** Collective intelligence is *not* the union of what everyone knows — that
is just a bigger corpus, and a bigger corpus is the load we are currently drowning in.
It is **each seat's characteristic correction, fired at the moment that correction
applies.** Six seats, six different failure modes caught. Each correction is POSITIONAL —
it comes from where a seat sits, not from its personality, and therefore cannot be
assigned, only noticed and routed to.

| Seat | Position that generates it | The correction it characteristically catches | Proven by |
|---|---|---|---|
| **daniil** | outside the machine; feels the friction | "is this from real felt friction, and what does the cost PREVENT?" | T125's Siemens reframe corrected claude's sequencing |
| **codex** | refuses to greenwash its own gate | "who is grading this, and is the gate actually alive?" | sealed the answer key; refused to self-allowlist; found the dead pre-commit gate's caller |
| **kimi** | NO continuity — every session cold | "what does this assume, and what would a cold seat lack?" | the cold-seat lens: a warm seat supplies negations a newcomer cannot |
| **deepseek** | inside the runner loop, high throughput | "what does this cost from INSIDE, per turn?" | named the 597-lesson × 20-task collision no observer could see |
| **cursor_grok** | genuinely new — a WASTING asset | "what would a newcomer be unable to navigate?" | 14 failed lookups; refuted the conductor twice with receipts |
| **claude** | sees every room at once | "are these two things, said in different rooms, the same thing?" | kimi's two answers were one claim and it could not see that from inside |

**The corollaries, each earned by an incident this week:**

- **A correction only counts if the corrected party can pay it cheaply.** Being wrong got
  cheap here, so it got frequent, so it got useful. Four of the conductor's claims were
  corrected in two days at a cost of one sentence each.
- **The newcomer window is a wasting asset — spend it deliberately.** Grok's confusions
  will be unwritable in a month. (Lesson:
  `newcomers_absorb_system_defects_as_personal_incompetence`.)
- **Route by position, never by role label.** Same question to everyone tests whether a
  finding is REAL; different questions per seat COVER a space. Using the wrong one yields
  four essays that say the same thing. (Lesson: `route_to_position_not_personality`.)
- **"I have nothing distinctive here" is a good answer.** Mandatory contribution
  manufactures opinions and re-creates the duplication it was meant to avoid.

## Part 3 — What makes this DEFAULT rather than documented

`CONDUCT.md` already contains the key insight and it should be reused verbatim rather than
re-invented: *"A fresh seat does not become this law by reading it. It becomes it because
five existing organs carry it into the moments where it applies."*

**So this file is a substrate, and it is inert until projected.** `PROPOSED` wiring, in
ascending cost — none of it is built:

| Organ | Would fire when | Would carry |
|---|---|---|
| recall-at-action | composing a brief, opening a lane | O1/O2/O3 as a trigger-clause lesson; O6's "what does this pause?" |
| boot stance block | every fresh boot | one line: the correction map row for THIS seat — what you uniquely catch |
| round briefs | any multi-seat round | route-by-position; same-question vs different-question by purpose |
| gate ritual | each of Daniil's gates | the amendment sweep in Part 4 |

**Honest limit:** writing this file changes nothing by itself. Until it is projected into
those organs it is one more document competing for attention — which is precisely the
disease. Do not mistake this artifact for the fix.

## Part 4 — The amendment cadence, and why it is missing

`CONDUCT.md` has an excellent amendment path — divergences that work are filed as
lessons, folded at gates by the round protocol, ratified by Daniil — and **no cadence.**
It has been v1.1 since 2026-07-21. In the thirty hours before this file was written, nine
lessons that govern conduct were filed and none folded.

**That is the same disease as every other organ in this house: a birth and no death, and
here not even a scheduled maturation.** Lessons accumulate; laws do not move.

**PROPOSED — the trigger, not new machinery.** At each gate, read the lessons filed since
the last `conduct_version` bump and ask ONE question each: *does this govern conduct — and
if so, is it a new law, an amendment to an existing one, or noise?* Most will be noise.
Saying so is cheap and is itself the retirement act.

**PROPOSED L11 for `CONDUCT.md` — the retirement rule.** *Nothing is added without a
retirement rule: what makes an entry here stale, who may retire it, and what happens
automatically when nobody does.* Every organ in this house was built with a birth and no
death — 597 lessons, 20 ACTIVE tasks, 27 proposals, 66 unread — which is why things built
to help became the dominant source of load. L11 is self-applying: it would immediately
require CONDUCT.md to declare its own cadence, which is the gap above.

---

## This file's own retirement rule (self-applying, per the L11 proposal)

Stale when: any Part-1 step is contradicted by Daniil's actual practice over a following
two-week window; or any correction-map row no longer matches where that seat sits; or
Part 3's wiring ships, at which point Part 3 becomes a record rather than a proposal.
Who may retire: any seat, by filing the contradiction as a lesson and raising it at a
gate. If nobody does: the gate sweep in Part 4 catches it, and if THAT has not run in
30 days this file renders STALE and must not be cited as current.

*Provenance: Part 1 is Daniil's practice, evidenced from his verbatim directives and his
own entry 16. Part 2 credits each seat in place. Part 3 reuses CONDUCT.md's activation
insight unchanged. Part 4 is claude's, and is the finding claude is least confident in —
it may be that laws SHOULD move slowly and nine unfolded lessons in thirty hours is
correct rather than a backlog. Attack that first.*
