[CERTAIN]

V1. [CERTAIN] Substrate: the house already lives the authored/derived split in TWO organs with different split-points -- routes are AUTHORED (tracked journal state/coord/routes.jsonl = truth, eye.db = rebuildable projection, content-hash id), while connectome edges are DERIVED (wholesale-rebuilt edges table in eye.db, three evidence grades recorded/derived/inferred). The door-list must be a derived VIEW over both, not a new authorable record type.

V2. [CERTAIN] Door-list contract: a door is a typed EXIT (what I can do from here), not a destination; four fields -- kind (one closed verb vocabulary), target, evidence (recorded|derived|inferred, the connectome's scale reused verbatim), degraded (bool + reason). A dead door renders as the door marked dead, never as silence (routes._resolve returns dangling and preserves the address; trace sets degraded and names the guess).

V3. [CERTAIN] Derived-route record: same schema as authored (content-hash id, receipt-REQUIRED canon steps) plus provenance + per-leg evidence + derived:true. It MAY trust recorded (follows) and derived (same_utterance) edges; it MAY cross an inferred (adjacent) edge ONLY by stamping that leg inferred and rendering the route degraded -- never laundering inference as record.

V4. [CERTAIN] Derivation-stamp honesty across rebuild: the stamp is written INTO the tracked journal at derivation time, so rebuild() replays it byte-for-byte and NEVER re-derives it -- a re-derived stamp drifts with a friendlier corpus, which is the backfill-as-measurement defect this house already refuses for walk depth.

V5. [CERTAIN] Promotion ceremony: promotion is a status transition (a route_promoted journal line on the SAME content-hash route_id), not a delete-and-resave -- the id survives, the derived flag flips, provenance is retained not erased. The forest PROPOSES, a seat PROMOTES, never self-ratifies.

V6. [DESIGN] Play laws + noise floor: trail = re-walkable derived route whose drill depth counts bodies obtained (T335); crumbs = journal-recorded legs, so receipt-required is non-negotiable. The floor is a KIND count (roughly the existing exit verbs, ~6-12), not a door count; within a kind, collapse to nearest/freshest with an expand door -- uniform means one grammar/evidence/degrade contract, NOT enumerable doors.

V7. [CERTAIN] Red pins: P1 survives IFF the stamp is journal-durable (V4); P2 already true by content-hash + append-only, residual risk is a promotion that re-writes steps (forbid -- promotion cites route_id, carries no steps); P3 true IFF provenance is append-only and read-forward; P4 true IFF every door renders resolving-or-degraded (V2/V3); P5 already the substrate's law on two planes, inherit it as a FIELD on the door, and refuse to HIDE a degraded door to reduce noise.

---

# doors-design — half_a (substrate) — Heimdall / deepseek

Blind to half_b. Grounded in the live substrate as it exists 2026-08-26:
`core/eye/routes.py`, `core/eye/connectome.py`, `core/eye/index.py`,
`core/eye/pyramid.py`, `core/foundation/relationship_types.py`. Where I claim
a fact I name the file; where I design I say so. I answer the QUESTION from
the substrate seat: the QUESTION asks *can every corpus object carry a uniform
door-list, and can the forest propose derived routes seats promote, without the
added doors multiplying confusion* — and my half's job is the ground that door
must be built on, or the reason it cannot be.

---

## 0. The one fact the whole fence turns on

The house already lives the authored/derived split in **two** organs, and the
split is not in the same place in both. This is not incidental; it is the
clue to the correct door contract.

* `core/eye/routes.py` — a **route** is AUTHORED. Its truth lives in a
  TRACKED append-only journal (`state/coord/routes.jsonl`); `eye.db` holds only
  a rebuildable projection. `save()` journals first, projects second; the route
  id is a SHA-256 **content hash** of `{name, steps}` (line ~91 `_route_id`),
  so a crash-redelivered or double-pasted save is *the same line, the same row*
  (pin P2). T335 added `route_walked` journal records so even *walks* (the
  usage history) survive a rebuild — the exact sentence "wiping the projection
  loses nothing authored" now holds *including* the evidence anyone walked it.

* `core/eye/connectome.py` — an **edge** is DERIVED (mostly). The `edges` table
  is *plainly and deliberately* a rebuildable projection ("never committed,
  reconstructible from source at any time" — docstring). `build()` drops and
  rewrites it wholesale. Three edge kinds, three **evidence grades**:

        follows          parent→child from parentUuid    evidence: RECORDED
        same_utterance   one utterance, N records, text  evidence: DERIVED (exact)
        adjacent         orphan pinned to nearest chained
                         event by position               evidence: INFERRED (a guess)

  And `trace()` already enforces the honesty law: a walk that crosses an
  inferred edge sets `degraded=True` and *names it* in `degraded_reason`
  ("this ancestry is a positional guess"). Pre-contract edges (no formation
  metadata) are **counted and declared, never silently dropped, never
  backfilled with a sentinel**.

So the substrate verdict, stated once and leaned on throughout: **the door-list
is the first object that is *neither* authorable-as-journal *nor* purely a
derived projection — it is a derived view *over* the authored-and-derived
objects, and its mortality class is therefore "projection, but one whose
renderer must know both planes."** Everything below is consequences of that.

---

## 1. The door-list contract

**What a door is.** A door is a *typed traversal* leaving a corpus object —
not the destination, the *kind of exit*. A door answers "what can I DO from
here?" not "what is here?" The house already has these exits, working, under
one roof:

* from an **event** (eye) — `recall` (keyword), `knowledge-map` (neighborhood
  walk over `related_to`), `lookback` (why/whence), `eye find/freq/trace/zoom/
  overview` (transcript terrain), `position` (standpoint);
* from a **lesson** (learning store) — `related_to` edges (SKOS:related walk),
  recall, note-supersession chains;
* from a **route** — `walk` (resolve/drill), `list`, supersession via
  `superseded_by` on a step.

So a uniform door-list is not *inventing* exits; it is *listing* the exits
that already exist, per object, with one type grammar. That is the only way
the "uniform" in the QUESTION is safe: **the door-list is a view, not a new
writable record type.** As a view it can be rebuilt and thus can afford to be
derived; as a new authorable record it could not, and would be a fourth organ
to reconcile with the three that already disagree on where authored truth
lives.

**How a room lists its doors.** The minimal door schema — carried on every
corpus object — is four fields and nothing more:

        door.kind        : the exit verb, from ONE closed vocabulary
        door.target      : the address the exit leads toward (may be empty for
                           "navigate the forest from here")
        door.evidence    : recorded | derived | inferred   (the connectome's
                           grades, reused verbatim — do NOT mint a third scale)
        door.degraded    : true iff the pathway currently cannot be fully
                           honored, plus the reason string

The kind vocabulary must be closed and small — the route step-types lesson
applies one plane over (`routes.py` docstring: "a vocabulary that accepts
anything means nothing", enforced by refusing unknown types at save). Borrow
the existing step vocabulary where it overlaps but do not reuse `follows`/
`same_utterance`/`adjacent` as *door kinds*: those are *edge kinds* (how two
nodes connect); doors are *verbs a seat takes*. A door of kind `trace` exits
an event *via* edges; the door and the edge are different layers and must not
share one vocabulary or the exclusion trap (`connectome.py` docstring, "the
exclusion trap is precisely the class the eye exists to refuse") gets harder
to test.

**What a dead door renders as.** A door whose target no longer resolves (a
route step whose `target` address finds no event) is NOT absent — it is a door
with `degraded: true` and a reason naming the break ("target dangles at
session:line"). This is already the law in two places and I make it the list's
law verbatim: `routes._resolve` returns `dangling` and preserves the last-known
address rather than erasing the door; `trace` marks `degraded` and names the
guess. **A dead door must render as the door, marked dead — never as silence.**
Silence is the defect this whole house keeps re-finding (`stale_plugin_...`,
`a_heartbeat_proves_presence...`): absence must keep meaning exactly one
thing, and a room whose door vanished indistinguishable-from-never-had is a
room that lies.

---

## 2. The derived-route record

The QUESTION's second clause — "the forest proposes derived routes" — has a
live receipt already: the naming-arc play session's `trace` returned a
machine-generated walk that was rendered and then thrown away, "a derived
route nobody saved." That is precisely the gap: a traversal *was computed*
(the connectome walked it), *was shown*, and then died, because there was no
slot to hold it. The derived-route record is that slot.

**Schema.** A derived route is the same record as an authored route, plus a
derivation field, *minus* the right to be the truth:

        route_id      : content hash of {name, steps}   (SAME hash as authored —
                        a derived route later promoted keeps its id, see §3)
        name          : machine-suggested handle (flagged, never confused with
                        a seat's title)
        steps         : same canon steps as routes.py _canon_steps (receipts
                        REQUIRED — a derived route with unreceipted legs is an
                        unfalsifiable claim and is refused)
        provenance    : how it was born — the closed vocabulary
                        (see derivation stamp below)
        derived       : true (the mortality-class flag; §3 promotion flips it)

Critically: **a derived route does NOT get a free pass on receipts.** The
substrate already refuses an authored step with no receipt ("a claim about the
past must be checkable"). A derived route is *exactly* where the temptation is
to let the machine fill gaps with inference — and this is the one place the
contract must be *stricter* than authored, not looser.

**Derivation stamp — which edge kinds a derived route may trust.** The
connectome already grades evidence; the derived-route record must carry that
grade through every leg and refuse to launder it. The rule, stated as law:

  * a derived route MAY be built from `recorded` edges (follows — the harness
    wrote the link) and `derived` edges (same_utterance — exact text identity
    in one session). These are faithful to the record.
  * a derived route MAY cross an `inferred` edge (adjacent — a positional
    guess) ONLY if the resulting route stamps that leg `inferred` and the
    route as a whole renders `degraded`, naming the guess — exact `trace()`'s
    law, generalized to the route level. A derived route that crosses an
    inferred edge and reports it as if recorded is *the* thing this fence must
    refuse, and the substrate already has the vocabulary and the precedence to
    refuse it: "an inference laundered as a record is precisely the class THE
    EYE exists to refuse" (connectome.py docstring).

**How the stamp stays honest and survives an eye.db rebuild.** This is the
substrate's *hardest* honest point and I answer it directly.

The derived route's truth does NOT live in `eye.db` alone. It follows the exact
split `routes.py` established, *extended by one field*:

        state/coord/routes.jsonl   append-only, TRACKED — holds ALL routes, and
                                    each record now carries provenance so a
                                    derived route is distinguishable from an
                                    authored one IN THE JOURNAL (the truth plane)
        eye.db routes/route_steps  projection — rebuildable, INSERT OR IGNORE,
                                    replay idempotent by content-hash id

Why this matters for the honesty of the stamp: if the derivation stamp lived
only in `eye.db`, then `rebuild()` (which reconstructs the projection from the
journal) would have to *re-derive* the stamp — i.e. re-run the inference — or
lose it. Re-deriving on every rebuild would make the stamp *drift* (a derived
route rebuilt against a changed corpus could silently gain or lose inferred
legs), and *losing* it would flip a derived route into looking authored.
Neither is acceptable. So:

  * the stamp is written INTO the journal at derivation time — once, by the
    proposer, as `provenance` + per-leg `evidence` — so `rebuild()` replays it
    *byte-for-byte* and the stamp is exactly as honest after a wipe as before;
  * a derived route therefore survives an eye.db rebuild *identically*, not
    *approximately*, because it is journal-replayed like every authored route.
    Its derived-ness is a journal fact, not a projection inference.

This is the single most important substrate contribution to the fence: **the
derivation stamp's honesty is guaranteed by putting the stamp in the durable
plane (journal) and forbidding `rebuild()` from ever re-computing it.** A
stamp that is re-derived is a stamp that can be silently upgraded by a
friendlier corpus — the same class as backfilling a walk depth as `listed`
(routes.py docstring: "a guess wearing a measurement's clothes").

---

## 3. The promotion ceremony

The QUESTION asks how a derived string becomes authored "without laundering its
machine origin." The substrate's `fields are the answer`: promotion is a
**status transition, not a deletion and re-save.**

  * A derived route is proposed by the forest (a seat-triggered trace, a
    recall-driven walk), journaled with `derived: true`, `provenance` filled,
    and a machine-suggested `name`.
  * A seat promotes it by writing a `route_promoted` journal record listing
    the same `route_id`. The id is a **content hash**, so promotion does not
    change the id — the promoted route *is the same object*, its `derived`
    flag flips to false, and its `provenance` is NOT erased (it carries the
    full derivation history forward). **The machine origin is kept in the
    record and marked, never laundered and never silently retained as if it
    were a seat's title.**
  * The record that enforces this is the journal's append-only shape: a
    promotion is a NEW line, and the history (derived→promoted) is readable as
    a sequence. No overwrite, so pin P2 (no silent overwrite) and pin P3
    (promotion carries derivation history) are the SAME mechanical guarantee —
    the content-hash id plus append-only journal makes both true for free.

This is the promotion-ladder precedent (presets *propose*, verdicts file
*unadjudicated*, seats *author*) generalized: **the forest may PROPOSE and
ROUTE, but may never SELF-RATIFY** — the house's own law
(`instrument_proposes_never_self_ratifies`). A derived route that promoted
itself, or that a promotion silently re-authored the content of, would be the
one thing this ceremony exists to prevent.

---

## 4. The play laws as mechanics, and the noise floor

**Trail = safety net.** The QUESTION's own framing names it: a derived route is
a *trail* a seat may later walk by hand rather than re-discover. Mechanically
that means a derived route must be re-walkable exactly like an authored one
(`walk()` with resolve/drill), and its `drill` depth must report `legs_drilled`
= *bodies obtained*, never legs attempted — the T335 law — so a seat knows
whether the trail was actually re-traversed or merely listed. A trail that
reports "drilled" when it only listed is a trail that lies, and a seat
following it into the dark does so believing a light that isn't there.

**Crumbs = memory.** The derived route is the crumb; the journal is the memory.
Crumbs only preserve what the journal actually recorded, which is why the
receipt-required rule (§2) is non-negotiable: a crumb with no receipt is a
pointer to nothing, and a trail of pointers-to-nothing is worse than no trail
because it *looks* walkable.

**The noise floor: how many doors before a room feels like a hallway.** This
is a DESIGN verdict, so I flag it and hand the number to reconciliation, not
assert it as substrate fact. The substrate says this much with certainty: the
door-list is a *view over existing exits*, so it does not *add* doors — it
*names* the ones already present. The confusion risk is therefore not "too
many doors" (the doors exist whether listed or not) but "too many *kinds*," and
the floor is a *kind* count, not a door count. My substrate recommendation: a
room renders at most a small closed set of door *kinds* (on the order of the
existing exit verbs — recall, map, lookback, trace, freq, zoom, walk, position
— roughly a half-dozen to a dozen), and *within* a kind the list collapses to
the nearest/freshest target, with "…and N more" as a door of kind `expand`, not
N identical doors. A door-list that cannot collapse within a kind *is* a
hallway. This is the one place the word "uniform" must NOT mean "enumerable" —
uniform means one grammar, one evidence scale, one degrade contract; it does
not mean every exit gets a door on the face of the room.

---

## 5. The five pre-registered RED pins — substrate verdicts

**P1 — derived-route rebuild survival.** SURVIVES IFF the derivation stamp is
journal-durable (§2) and `rebuild()` replays it verbatim, never re-derives. If
the stamp lives only in `eye.db`, P1 FAILS the first rebuild — a derived route
either loses its derived-ness (laundered into authored) or re-runs inference
and drifts. Make the stamp a journal field and P1 is mechanically true, not an
invitation to be careful.

**P2 — authored-route no-silent-overwrite.** Already true by content-hash id +
append-only journal (`routes.py` `_route_id` + `save`). The pin's residual risk
is promotion (§3): a promotion that re-writes steps would be a silent
overwrite *in disguise*. Enforcement: promotion references `route_id`; it does
not carry steps. The steps arrived from the derived record; editing them is a
new authoring act with its own new id.

**P3 — promotion carries derivation history.** True iff `provenance` + per-leg
`evidence` are journal fields that survive the flag flip (§3). If promotion
erases provenance, P3 fails loudly. Keep provenance append-only and read it
forward; never drop it.

**P4 — door-list renders with every door resolving or IS-NOT.** True iff the
degrade contract (§1) is enforced at render: every listed door carries either a
resolving target or an explicit `degraded` + reason. The substrate already has
both halves — `_resolve`'s `dangling` and `trace`'s `degraded_reason` — ready
to be the door-list's resolution contract. A door that renders as nothing is a
P4 failure by definition.

**P5 — degraded pathways name their degradation in the list itself.** Already
the substrate's law on two planes (`routes._resolve` names `dangling` and
preserves the address; `trace` names the inferred-edge guess). The list must
inherit it: `degraded` is a *field on the door*, not a footnote elsewhere. The
one trap to refuse: a degraded door must not be *hidden* to reduce confusion —
hiding a broken trail is how a seat walks it anyway. Name it, show it, let the
seat choose.

---

## Standing defects this fence must not re-introduce

Three, named for reconciliation, all receipts in `routes.py`/`connectome.py`:

1. **Backfilling a guess as a measurement** — refusing this is why walks have
   `unknown` depth and why a pre-contract edge is never sentineled. The door
   contract must refuse the same: no "default door," no "assume current."
2. **A vocabulary that accepts anything means nothing** — the step-types and
   formed_via vocabularies are closed and refusable for a reason. The door-kind
   vocabulary must be closed and refuse unknown kinds at render, or P4 has no
   teeth.
3. **The machine that shows a thing is not the machine that grades it** — the
   derived route is *proposed* by the forest and *promoted* by a seat; the
   trace that generated it must not also auto-promote it. `instrument_proposes_
   never_self_ratifies` is the governing law and the derived-route ceremony is
   its clearest instance yet.

---

*substrate receipt: connectome.py (edge kinds + evidence grades + trace's
degrade law), routes.py (journal/projection split, content-hash id, T335 walk
records, step receipt law), index.py + pyramid.py (the eye exit verbs). Half_a
submits no half_b assumptions; everything above that needs a second opinion is
flagged DESIGN and handed to Vandor's reconciliation.*
