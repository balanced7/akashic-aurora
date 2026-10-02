# doors-design — RECONCILIATION — Vandor / claude

[CERTAIN] on the convergences and the two rulings, which rest on quoted text from both
sealed halves and on the substrate both halves cite. [DESIGN] on §5, which is mine and was
found by neither half — flagged as such so Daniil can weigh it differently.

Read after both halves sealed. I withheld my own position from the brief deliberately so I
could not anchor a fence I was going to grade; §5 is that withheld material, and §5.3 is the
part where a half beat me to it.

---

## VERDICT ON THE QUESTION

**Yes — with one condition each half found independently, and one neither did.**

Every corpus object can carry a uniform door-list, and the forest can propose derived routes
that seats promote, WITHOUT multiplying confusion, provided:

1. the door-list is a **derived view**, never a new authorable record type (both halves, V1);
2. every door **resolves or declares its degradation** — never silence (both halves, V2);
3. the derived route lives in the **tracked journal** wearing a derivation stamp that survives
   rebuild (both halves, V3/V4);
4. promotion is **append-only supersession retaining provenance**, never a fork or a mutation
   (both halves, V5/V4 — but see §3, where their wording diverges dangerously); and
5. **adoption costs a traversal** (§5.1 — neither half required this, and without it the
   ceremony is theatre).

"Uniform" survives because it means *one grammar, one evidence scale, one degradation
contract* — not one enumerable list. Both halves reached that independently and it is the
load-bearing insight of the fence.

---

## 1. CONVERGENCE, and why it is strong

Blind halves on different seats agreeing is the highest-value signal a fence produces. These
agreed without contact:

| claim | half_a (substrate) | half_b (interaction) |
|---|---|---|
| door-list is derived, not authored | V1 | V1 |
| reuse the connectome's three evidence grades verbatim | V2 | V2 |
| a dead door renders as dead; silence is forbidden | V2 | V2 |
| derived routes live in the TRACKED journal, not the projection | V3/V4 | V3 |
| inference is never laundered as record | V3 | V3 |
| provenance is retained through promotion | V5 | V4 |
| the forest proposes, a seat ratifies, no self-ratification | V5 | V4 |

Notably both rejected the same wrong answer: a door is **not a destination** (a: "a typed
EXIT, not a destination") and **not a link** (b: "a promise, not a link"). Two seats, two
vocabularies, one refusal. That refusal should go in the contract verbatim.

---

## 2. THE TWO HALVES ANSWERED DIFFERENT QUESTIONS ABOUT THE NOISE FLOOR — both correctly

This reads as a conflict and is not:

* **half_a V6:** the floor is a **KIND count** (~6-12, roughly the existing exit verbs).
* **half_b V6:** the floor is **three ungrouped doors** to a room.

a is bounding the **grammar** (how many kinds of door may exist at all). b is bounding the
**render** (how many appear at once before a room reads as a hallway). Both bounds are
needed and they compose: a vocabulary of ~6-12 kinds, rendered at most 3 groups at a time.

Adopt both. State them as separate limits so nobody later "reconciles" them into one number.

---

## 3. RULING ONE: half_a's "the derived flag flips" is a projection, not a mutation — and
##    it must be written that way or someone will implement the mutation

This is the finding I would most want carried into the build, because it is invisible in
both halves read alone and is a bug in waiting.

* **half_a V5:** promotion is "a status transition ... the id survives, **the derived flag
  flips**, provenance is retained not erased."
* **half_b §3.2:** adoption "writes a new record — **it does NOT mutate the derived route's
  status in place** (append-only, routes.py's own law)."

Read literally these contradict. But half_a's OWN V1 establishes the journal is append-only,
and half_a's V7 forbids a promotion that re-writes steps. So half_a cannot mean an in-place
write; it means the flag **reads** false after the appended `route_promoted` record, on a
read-forward projection.

**RULING: half_b's mechanism, half_a's identity.** Promotion appends a record citing the same
`route_id`; nothing is mutated; the flag is a read-forward projection over the journal. The id
survives because `_route_id` hashes `{name, steps}` (half_a, routes.py ~line 91) and neither
changes at promotion.

**And a correction to half_b, from its own goal:** b_V3 puts the derivation stamp *inside* the
content hash. That is safe only while the stamp is byte-identical before and after adoption —
which b_V4 does guarantee ("RETAINS the derivation field"). But it makes the id fragile against
any future stamp enrichment, and b explicitly wants "a supersession, never a fork." Hashing
`{name, steps}` and carrying the stamp as a retained *field* achieves b's goal with less
coupling. Recommend a's hash boundary, b's append-only ceremony.

---

## 4. RULING TWO: no expand door — and half_a's own P5 is why

* **half_a V6:** "within a kind, collapse to nearest/freshest **with an expand door**."
* **half_b V2:** "≤3 always-visible groups with counts, **never a hidden 'more doors' menu**."

An expand door is a hidden-doors menu. And half_a's own **P5** says: "refuse to HIDE a degraded
door to reduce noise." You cannot honour P5 behind an expand affordance without already knowing
which hidden doors are degraded — at which point you are rendering them anyway.

**RULING: half_b.** Collapse to ranked groups **with counts, always visible**. The count is what
makes collapsing honest: it tells the seat the volume it is not being shown, which is the
difference between summarising and hiding. Derived from half_a's principle, so both halves own
the outcome.

---

## 5. WHAT NEITHER HALF FOUND — mine, labelled as mine [DESIGN]

### 5.1 Adoption must cost a traversal, or the ceremony is theatre

Both halves specify **who** ratifies (a seat, never the forest) and **what** it writes. Neither
specifies what ratification **costs**, and that is the gap that empties the ceremony.

The house's propose/ratify precedents — presets, unadjudicated verdicts — all share a property
this one does not: **the proposal is cheap to evaluate.** You read a preset and you know. A
derived route is a *path*; its correctness is not visible on its face. To know whether it is
good you have to walk it.

If adoption is a button, adoption becomes rubber-stamping, and **a rubber-stamped derived route
is worse than an unadopted one** — it now wears authored authority while carrying machine
provenance nobody checked. That is the laundering the QUESTION explicitly set out to prevent,
arriving through the front door instead of the back.

**Proposal:** `adopt` refuses unless a `route_walked` record for that `route_id` exists by the
adopting seat. The substrate already has this — T335 added `route_walked` journal records
(half_a §0). The falsifier is already in the tree; it just is not wired to the gate.

### 5.2 A promoted derived route rots, and neither half can detect it

half_a V4 hardens the stamp against **rebuild** — the stamp must not drift when the corpus is
friendlier. Correct, and it is the opposite concern from mine.

A derived route is a **function of the corpus**. Promoting it freezes a snapshot of something
that was derived from live terrain. When the terrain moves, the promoted route may still
*resolve perfectly* — every leg present, nothing dangling — and no longer describe anything
true. half_b's V5 is closest ("a crumb that cannot resolve is a rumor, not memory") but that is
resolution failure. The dangerous case is the route that resolves and lies.

**Proposal:** the derivation stamp records the corpus state it was derived from (edge-table
generation or a build counter). A promoted route whose stamp predates the current generation
renders **stale** — a third state beside resolving and dangling. Not auto-retired: rendered.
This is the same class as the corpus lesson that a competitive-position claim inherits its own
timestamp, one plane over.

### 5.3 Where a half beat me

I withheld a third position: that the noise floor is about **ranking, not count** — an
unranked list of twelve doors is a hallway; a ranked twelve with three surfaced is a room.
**half_b found this independently** (V2, "RANKED by evidence grade"). I am recording that it
converged rather than quietly claiming it, because a reconciler who only reports what the
halves missed is grading on a curve he set.

---

## 6. THE FIVE PRE-REGISTERED PINS

Both halves addressed all five; I add the conditions the rulings above impose.

* **P1 derived-route rebuild survival** — half_a V4 is correct and sufficient: the stamp is
  journal-durable and replayed, never re-derived.
* **P2 authored-route no-silent-overwrite** — holds by content-hash + append-only. §3's ruling
  strengthens it: promotion carries no steps and mutates nothing.
* **P3 promotion carries derivation history** — holds IFF provenance is append-only and
  read-forward (both halves). Add §5.1: it must also carry the *walk receipt*.
* **P4 door-list renders with every door resolving or IS-NOT** — both halves. §5.2 adds a
  third rendering state: **stale**.
* **P5 degraded pathways name their degradation in the list itself** — both halves, and §4
  turns it into the argument against the expand door.

---

## 7. FOR DANIIL'S GATE

Three decisions, ranked by how much they change the build:

1. **Does adoption require a walk?** (§5.1) This is the biggest one and it is a judgement about
   ceremony, not mechanism. It makes adoption slower and honest. My recommendation: yes — the
   receipt already exists, and the alternative is a ceremony that certifies nothing.
2. **Stale as a third render state?** (§5.2) Costs a generation counter on the stamp. My
   recommendation: yes, and render-only — never auto-retire.
3. **Hash boundary: `{name, steps}` or `{name, steps, stamp}`?** (§3) My recommendation: the
   former, with the stamp retained as a field. It gets half_b's supersession guarantee without
   coupling the identity to the provenance format.

Everything else is agreed by both halves and needs no ruling.

**Both halves were good, and their disagreement was worth more than their agreement.** The
noise-floor "conflict" was two correct answers to two different questions, and the promotion
"conflict" was a wording ambiguity that would have shipped as an in-place mutation of an
append-only journal. Neither is visible reading either half alone. That is the fence working.
