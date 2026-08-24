# T277 — the four-way comparison, with receipts (2026-08-16)

Status: decision-input · Type: analysis · Arc: vision / L0
Author: claude. **This document proposes nothing on its own — it structures a choice
that is Daniil's** (T277: "DANIIL DECIDES... picking it for him would be the T227
defect at the largest possible scale"). Every quote carries an eye address; drill any
of them with `py agent_cli.py eye get <addr>`.

## The finding that reframes the task

T277 credits the question to an external critique (CONTACT-1, 2026-08-10). The corpus
says otherwise:

> "lets integrate the improvements ... and come up with an onboarding test v2 to
> compare how well we did. **how can we measurabely tell if what we are building is
> working / effective?**"
> — Daniil, **2026-06-16**, eye `83ddd20f-1a5b-4504-a926-f55ece37adba:321`

The sharpest external critique this project has received is a question Daniil asked
himself on day ~2 of the recorded corpus, which no durable plane ever answered. Two
independent arrivals at the same question, eight weeks apart. It has seniority, and it
has been open the whole time.

## How to read the table

Each candidate gets: what it optimizes, the metric WITH a target (proposed — argue
with the numbers, they exist to be moved), **what we would STOP doing** (T277: "a
definition that forbids nothing is a slogan"), what today's numbers re-express as, and
his own words on the record for it. The candidates are not compatible as PRIMARY;
any of them can survive as a guard-rail under another.

---

## (a) COLD-START COST — "a fresh seat reaches correct work with zero re-explanation"

**Optimizes:** the boot fold, the primer, handoff quality. The store is good when a
stranger is productive fast.

**His words:**
- the 06-16 founding question above — its first clause is literally "onboarding test v2"
- "initialize yourself with akashic aurora and pay attention to any friction points in
  the initial onboarding. We just spent time making that process better, I want to see
  if we have addressed all the gaps." — 07-16, `69d664e5-...:1` (he ran the cold-start
  test personally)

**Metric + target:** minutes from fresh boot to first *correct, ledger-cited* action;
fraction of an incoming brief that re-carries standing premises. Target: boot→first
correct action **< 5 min**, re-carry fraction **trending to 0** (measured per handoff).

**We would STOP:** growing new retrieval verbs (the Eye keeps what it has); bespoke
per-session context essays; any organ whose value requires its author present.

**Today's numbers, re-expressed:** the 4.8% funnel value rate becomes "premises
re-carried anyway despite recall firing" — measurable against every boot; this
morning's session is a datapoint (the handoff worked: zero re-explanation needed to
resume, but it took a ~920k-context session to write).

## (b) DEFECT YIELD PER DOLLAR — "the fleet finds what a solo agent misses, at stated cost"

**Optimizes:** fences, blind halves, adversarial verification, kill-drills. The store
is good when it causes catches.

**His words:**
- "if we have multiple (i dont know if adversarial is the right word) perspectives with
  differing design roles they can help cover the blind spots of the others" — 07-25,
  `cf1ebd7e-...:1440`
- "Adversarial review it is! I am off to work, continue working with everyone" — 07-28,
  `7d0ede0e-...:5253`

**Metric + target:** CONFIRMED defects found by a fence/blind-half that the primary
lane missed, per gated slice and per dollar. The n=5 kill-drill (T274) is this metric's
instrument, currently missing its bar. Target: **≥1 primary-lane-missed confirmed
defect per gated slice**, fleet spend per catch stated and trending down.

**We would STOP:** unfenced solo shipping on load-bearing slices; fan-out that cannot
name the defect class it hunts (fan-out must show yield, not activity).

**Today's numbers, re-expressed:** the 99.7% quote-honesty rate becomes extractor
calibration for the judge lanes; this morning scores 2-for-2 — an instrument defect
found by drilling its own output, and a stranded review-ready fix recovered.

## (c) DECISION REPRODUCIBILITY — "replay any decision against what was knowable then"

**Optimizes:** append-only planes, supersession records, known_at stamps, the replay
bench. The store is good when the past is queryable as it was, not as it ended up.

**His words:**
- "I want to make sure our communications infrastructure and messaging system are no
  longer a fragile mess where new agents spawn and are confused on what is current or
  not" — 07-09, `79650336-...:31` (currency-vs-history is the reproducibility gap in
  operational clothing)
- "lookback" and "provenance categories" are his vocabulary (glance-directive note);
  the Arc Replay Arc (07-21) is his time-travel→replay-bench directive.

**Metric + target:** fraction of gated transitions whose inputs are point-in-time
reconstructible; a replay drill (given decision D at time τ, recover exactly what was
knowable) passes. Target: **100% of gated transitions from the adoption date forward**;
the drill runs at every gate.

**We would STOP:** in-place doc mutation without supersession records; any new plane
shipping without a known_at column. (The Eye just grew `indexed_at` with exactly these
semantics — the first brick exists as of T313.)

**Today's numbers, re-expressed:** T277's own text concedes "our supersession model
currently CANNOT do this" — the honest current reading is **0%**, which is why this
candidate is the most expensive to pick and the only one priori.sh already proves out.

## (d) PORTFOLIO LEGIBILITY — "an outside reader sees engineering judgment"

**Optimizes:** narrative artifacts, the README, demos, glanceable surfaces. The store
is good when it makes the builder legible.

**His words:**
- "I want to learn from the best in this field, they get paid big money because of
  their skills and a lot of them publish material and have githubs" — 07-02,
  `5804071d-...:696` (the career end-goal, stated plainly)
- "at a glanceable and also TRUE or at least true in one sense" — 08-08, the standing
  acceptance criterion (glance-directive note, ~15 statements since 07-09)

**Metric + target:** the outside-reader test — a cold reader locates what-it-is /
why-it-is-hard / the-evidence-discipline within N minutes, unprompted. Measured by
real outside readers (the CONTACT-1 call was the first live run of this metric).
Target: **3 external readers** reach "this demonstrates engineering judgment" without
being led there.

**We would STOP:** building internal capability that never surfaces in a legible
artifact — the BUILT≠WIRED class, elevated from recurring finding to *defined failure*.

**Today's numbers, re-expressed:** ~12 BUILT≠WIRED findings from the 08-16 session
become the primary defect backlog; T276 (competitive positioning) unblocks.

---

## The tensions, stated honestly

- **(a) and (d) share the glance directive; (b) and (c) are indifferent to it.**
- **(c) is the only candidate that demands something unbuilt** (point-in-time query);
  the others re-aim existing machinery. Picking (c) is picking a construction project.
- **(b) is the only one with a cost denominator** — the only definition under which
  the token-frugality directive is a first-class term rather than hygiene.
- **"Agents prefer the store"** (the standing success bar in memory) is not a fifth
  candidate: it is (a)+(b) measured from the agent's side. It survives any choice.
- A primary does not delete the others — they demote to guard-rails. But T277's
  acceptance asks for ONE definition, and it is right to: the 08-10 call showed what a
  one-sentence definition does for a feature list (priori: "return only evidence that
  was knowable at a pinned instant").

## What happens next (mechanics, no pressure)

Daniil picks a primary (possibly with named guard-rails). Then: the definition lands
in his words in a durable L0 note + ROADMAP.md sheds its HISTORICAL banner; the chosen
metric gets its instrument named (most exist); the STOP list becomes a checker or a
standing review question; the funnel/drill numbers get re-based against the target.
T276 unblocks. Estimated wiring cost for (a), (b) or (d): small — the instruments
exist. For (c): a real arc.
