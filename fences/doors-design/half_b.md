# doors-design — HALF B (Navi/kimi, the INTERACTION half)

[CERTAIN] — this tag is CERTAIN where it restates existing receipts (routes.py, connectome.py,
the routes journal, T335), and DESIGN where it proposes. I have read the sealed brief; I
have NOT read half_a (Heimdall's mechanism half). Filed blind.

Fence: doors-design. Slot: half_b. By: kimi. Scope of this half: the door-list contract a
seat actually READS; the play laws as mechanics (trail = safety net, crumbs = memory); the
noise floor — how many doors before a room feels like a hallway, and what collapses first
when it does.

I do not repeat half_a's mechanism ground. I take, as given and already true in the tree:
routes journal is authored/TRACKED (core/eye/routes.py:63), eye.db+edges are rebuildable
(core/eye/connectome.py:56-57 "never committed, reconstructible from source"), the three
edge evidence grades recorded/derived/inferred already exist at connectome.py:23-28, and a
walk that crosses an inferred edge already sets `degraded` and names it (connectome.py:372,
routes.py `_resolve` returns current|dangling at :236-262). Those are my building blocks,
not my claims.

## VERDICTS (the six load-bearing lines, expanded in §1–§5)

V1. A door is a promise, not a link: one typed pathway + one evidence grade + one imperative verb, rendered for the READ, never the store. [CERTAIN]
V2. The door-list is RANKED by evidence grade (recorded → derived → inferred), rendered as ≤3 always-visible groups with counts, never a hidden "more doors" menu; every door resolves or reads IS-NOT (absence = never-was, dangling = formed-then-broke). [CERTAIN]
V3. A derived route lives in the TRACKED journal (`state/coord/routes.jsonl`) wearing its `derivation` stamp as part of the content hash, `status:"proposed"` — never a separate store, never the rebuildable projection alone; it may ride recorded+derived edges freely but only DRAFT over inferred edges, and the draft wears `inferred` on every guessed leg. [CERTAIN]
V4. Promotion is ONE verb — `adopt` — append-only supersession that RETAINS the derivation field (no origin laundering) and leaves the proposed record alive; the content hash includes the stamp so adoption is a supersession, never a fork. [DESIGN]
V5. Trail = append-only, content-hash-idempotent, rebuild-proof return paths (safety net); crumbs = receipted, re-walkable steps (memory) — a crumb that cannot resolve is a rumor, not memory. [CERTAIN]
V6. The noise floor is three ungrouped doors to a room; beyond it, collapse to ranked groups with counts. When crossed, the evidence-grade trust collapses FIRST, the imperative mood second, and the IS-NOT distinction drowns last. [DESIGN]

## 0. The interaction truth in one sentence

**A door is a promise, not a link.** The mechanism can propose a thousand edges; what the
seat actually reads is a LIST, and a list is a sentence in the imperative mood: "from here
you can go *thus*." The entire confusion risk Daniil named is not in whether doors resolve —
it is in whether a door *asserts* (this is how OUT) or *offers* (this is how out, if you
want it), and whether the offer survives the thing that produced it being rebuilt away.
The contract's whole job is to keep the imperative mood honest, and the noise floor is the
point where honesty becomes volume and the room becomes a hallway.

## 1. The door-list contract (what a seat reads)

### 1.1 What a door is

A door is **one typed, direction-bearing pathway leaving an object, plus the evidence grade
of the edge it rides, plus an imperative verb.** It is rendered for a seat, so its truth is
in the READ, not the store. Draft shape (DESIGN):

```
<verb> <target>  [via <edge_kind>:<evidence>]
  recall  → the lessons this object's text matches        [via related_to:recorded]
  trace   → where this came from / what followed          [via follows:recorded]
  look    → the position holding this object              [via position:recorded]
  map     → the neighborhood walk around this object      [via related_to:derived]
  route   → the authored string through here              [via routes.jsonl:recorded]
```

Every door carries exactly two things a seat must be able to trust without thinking:
(a) **which edge kind it rides**, and (b) **that edge's evidence grade**. The grade is not
decoration — it is the door's honesty. `recorded` means the harness wrote it down;
`derived` means computed from content and exact; `inferred` means a positional guess
(connectome.py:23-28). A door that rides an `inferred` edge and does NOT say so is a lie in
the imperative mood, and it is exactly the class THE EYE's own docstring refuses
("An inference laundered as a record is precisely the class THE EYE exists to refuse,"
connectome.py:37-38).

### 1.2 How a room lists its doors

A room (any corpus object rendered for walking) lists its doors in a **fixed order that is
also a rank**, and the rank is honest about the evidence:

1. recorded edges first (the floor — won't change under rebuild),
2. derived edges next (computed, exact, reproducible),
3. inferred edges last, and **visually de-emphasized** (dimmed / suffixed / second screen).

This order is not aesthetic. It is the rebuild-survival law made legible: the top of the
list is what survives any rebuild; the bottom is what is cheapest to regenerate and most
likely to silently change. A seat that has learned that order no longer has to wonder
whether a door is load-bearing.

### 1.3 What a dead door must render as

A door that cannot resolve its target must render as **IS-NOT, named, not hidden** —
this is already the house's law one plane over (routes.py `_resolve` returns
`current|dangling`, and the policy sentence "an unclear route is still a route" from
ed728d23:2173 is enforced literally). The dead door is a FIRST-CLASS render state:

```
trace → (no parent chain resolves here)        [IS-NOT: dangling]
```

Not an absence, not a silent skip, not a greyed-out nothing. **Absence must keep meaning
exactly one thing** — connectome.py:59-61 says this about edges; I extend it to doors: a
door missing from the list means *no such pathway was ever formed*, never *the pathway broke
and we hid it*. Distinguishing "never was" from "is now dangling" is the single cheapest
confusion-killer in the whole design, and it is free — the resolution check already runs.

### 1.4 The door-list is the ONLY door surface; there is no "more doors" menu

This is the interaction core of the anti-hallway answer: **the full list is the list.**
There is no "show me more doors" state, because the moment a room has a *hidden* door-set
behind a visible door-set, the seat can no longer trust that the list it is reading is the
list of what leaves this place. A room lists ALL its doors, ranked and categorized, or it
lists none. The rank order does the collapsing, not a fold. (If a room truly has dozens, the
render groups by type — recall-like / trace-like / route-like / standpoint-like — but the
groups are all visible at the top level; grouping is layout, never occlusion.)

## 2. The derived-route record (survives a rebuild without looking like a route)

### 2.1 Schema and the derivation stamp (DESIGN)

A derived route is a route whose provenance says "a machine proposed this and nobody has
promoted it yet." The route journal already carries `by` (seat id) and content-hash id
(routes.py:175-182, `_route_id`). A derived route adds ONE field that carries everything:

```
derivation: {
  "from": "edge-batch 2026-08-26",          # the build/ingest stamp
  "seeds": [<the objects whose doors it connects>],
  "edges": [{"kind": "follows", "evidence": "recorded"}, ...],
  "engine": "trace"                          # which door proposed it
}
```

The derivation stamp is **part of the content hash** (it must be — same steps, two different
derivations, are two different claims about the past), so a derived route survives a rebuild
*only because the route journal is TRACKED and the projection is rebuilt by replaying it*
(routes.py:236-262, `rebuild()`). The key interaction fact: **a derived route lives in the
same journal as an authored route, distinguished only by its `derivation` field and a
`status: "proposed"`** — never by a separate table, never by "we'll remember it was derived
separately." The moment there are two stores, the seat must remember which store it is
reading, and that memory is exactly the confusion the contract exists to kill.

### 2.2 Which edges a derived route may trust

This is the sharpest interaction constraint, and it is CERTAIN because the evidence grades
already exist:

- **recorded** edges (follows: transcript, fence, supersession, manual): MAY be trusted to
  propose a route. The harness or a mind formed them.
- **derived** edges (same_utterance: text-identity): MAY be trusted, but the route must carry
  the "derived" grade on every leg that rides one, because "exact text identity" can still
  produce a route that reads as insight and is only bookkeeping.
- **inferred** edges (adjacent: position): **MAY NOT be trusted to propose a route
  automatically.** An inferred edge is a GUESS, and a route proposed over guesses is a
  machine telling a story it cannot receipt. A derived route MAY include an inferred leg,
  but it must (a) be `degraded`-stamped the whole way (connectome.py:372 already does this
  for walks), and (b) render the guessed leg with the same IS-NOT-truthfulness as a dead
  door. The floor rule: **the forest may propose over recorded+derived freely; over inferred
  it may only DRAFT, and the draft wears "inferred" on every guessed step.**

### 2.3 Rebuild survival = the journal is the only truth-bearing store

This is the one place the interaction half must state a mechanism truth as a constraint on
the contract, because a seat's trust depends on it: **a derived route survives an eye.db
rebuild EXACTLY as well as an authored one, because both live in
`state/coord/routes.jsonl` (TRACKED, append-only) and the projection is replayed.** If
half_a places derived routes in the rebuildable eye.db instead of the journal, that is a
VETO from the interaction side: the seat would learn "sometimes my trail evaporates and
sometimes it doesn't," and a trail that is a safety net only until the next rebuild is not a
safety net. The derivation *stamp* must also journal — never only project.

## 3. The promotion ceremony (derived → authored without laundering the origin)

### 3.1 The verb

Promotion is ONE verb, and its name matters to the interaction. I propose **`adopt`** (the
seat adopts the proposed route), not `save`/`promote`/`accept`, because "adopt" preserves
the truth that the route was *found*, not authored — a foundling, not a native. The prior
art is the house's own propose/ratify ceremony (presets propose, verdicts file
unadjudicated, routes are authored by seats — brief.md:31-34), and this generalizes it to
machine-tied strings.

### 3.2 The ceremony as mechanics

When a seat adopts a derived route, the journal writes a new record — **it does NOT mutate
the derived route's status in place** (append-only, routes.py's own law). The adopted record:

1. carries the same content-hash payload BUT with a new `by` (the adopting seat) and a new
   `status: "active"`;
2. **retains the `derivation` field from the proposed route** — this is the anti-laundering
   clause. The origin is not erased; it is carried forward. An adopted route is a promoted
   string whose history says "a machine proposed this, a seat blessed it";
3. does NOT delete or rewrite the proposed record. The proposed route stays as a record of
   what the forest offered. (Its status may later read `superseded`, mirroring routes.py's
   `superseded_by` step field, but that is a *later* slice — s1 keeps both records alive and
   distinct.)

### 3.3 What breaks it (interaction view)

Three failure modes, all visible only from the seat's side:

- **Silent promotion** (a derived route that flips to authored with no ceremony record) = the
  seat can no longer tell "a human stood here" from "a machine stood here," and that
  distinction is half the reason the door-list carries evidence grades at all.
- **Origin laundering** (promotion that drops the `derivation` field) = the same lie that
  connectome.py:37-38 already refuses, one plane up: an inference dressed as a record.
- **Double-entry** (adoption that writes a *new* content-hash because the derivation stamp is
  now "active" — if the stamp isn't part of the hash, adoption forks the route instead of
  promoting it). This is why §2.1 makes the stamp part of the hash: promotion is a
  supersession, not a sibling.

## 4. The play laws as mechanics + the noise floor

### 4.1 Trail = safety net

The trail (a walkable route through where you have been) is a safety net **because it is
append-only and content-hash-idempotent and rebuild-proof** — all already true. The
interaction law it encodes: **a seat may always return.** The trail's whole value is that
"go back" is a door that never dangles and never lies about depth (routes.py DEPTHS
listed/resolved/drilled, `walk()` at :331-388 derives depth from what actually ran, never
self-declared — "a self-declared fidelity field is exactly as trustworthy as the number it
replaced").

### 4.2 Crumbs = memory

Crumbs (the breadcrumb steps) are memory **because they are receipted** — every step carries
a `receipt` that must be checkable (routes.py:91-101 "a step without a receipt is an
unfalsifiable claim about the past — refused at the door"). The interaction law: **a crumb
that cannot be resolved is not memory, it is a rumor.** Crumbs are only memory if you can
re-walk them. This is why the dead-door IS-NOT render (§1.3) is not a courtesy — it is the
crust that makes crumbs trustworthy: a walker who can see which crumbs resolve and which
don't is holding memory; a walker who sees a list of crumbs with no resolution is holding a
shopping list for the past.

### 4.3 The noise floor (the headline number)

This is the question Daniil actually handed the interaction half, and I will give a number
and a collapse-order, both DESIGN but argued from the receipts.

**The number: three per role, grouped, is a room; seven unranked is a hallway.**

The mechanism is Miller's chunking, but the house already has its own version: the route step
vocabulary is exactly six types (routes.py STEP_TYPES observation/discriminating-test/
decision/dead-end/anchor/handoff) and the walk-depth vocabulary is exactly three (DEPTHS
listed/resolved/drilled). **Three is the house's comfortable read-width** — a seat holds
three doors without effort, seven only by grouping them. So the rule is not "no more than N
doors" but **"no more than three UNGROUPED doors, and any group that exceeds three collapses
to its head with a count."** A room with 12 doors renders as three visible door-groups —
recall-like (5), trace-like (3), route-like (4) — and the group-header carries the count, so
the seat sees "5 recall doors here" and drills only if it wants. That is not occlusion
(hidden doors); it is chunking (ranked groups), and the difference is that the GROUP HEADER
is always visible so the total is never a surprise.

### 4.4 What collapses first when the floor is crossed

In order (this is the interaction half's specific contribution — the failure is NOT
uniform):

1. **The evidence-grade trust collapses first.** The moment a list is long enough to scroll
   or skim, the seat stops reading the `recorded/derived/inferred` suffix on each door. And
   that suffix is the only thing standing between the seat and walking an inferred edge as if
   it were recorded. So the FIRST casualty of too many doors is precisely the honesty the
   whole design exists to add. Volume destroys the reason the doors exist.
2. **The imperative mood collapses second.** Long lists get skimmed as nouns ("trace, map,
   route...") not as offers ("trace → do you want to see where this came from?"). And a door
   read as a noun is not a door, it is a menu item. The seat stops *choosing* and starts
   *consuming*, which is the exact death of "playful exploration" Daniil asked for.
3. **The IS-NOT distinction drowns last but matters most.** In a 12-door list, a single
   "dangling" among 11 "current" is invisible — the seat walks it, hits the dead end, and
   *blames the room* (or the forest) rather than reading the door that already told it. The
   dead-door render is only useful if the list is short enough that the dead door is
   *adjacent* to the live ones it is being compared with. Past the floor, IS-NOT becomes
   noise instead of signal, and the safety net silently stops catching.

The interaction half's verdict on the QUESTION, in one line: **yes — every corpus object can
carry a uniform door-list and the forest can propose routes seats adopt, on one condition:
the door-list must be RANKED by evidence grade into ≤3 visible groups with every door
resolving or reading IS-NOT, and the derived route must live in the tracked journal wearing
its derivation stamp forever — because a door is a promise, and the only thing worse than no
promise is a promise the seat cannot tell was kept.**

## 5. The five pre-registered RED pins (my verdicts, blind to half_a)

- **P1 — derived-route rebuild survival.** Must journal the derivation stamp to
  `state/coord/routes.jsonl` (TRACKED) — NOT to eye.db. Veto-check: if the derived route
  lives only in the rebuildable projection, the trail is a fair-weather safety net. SEAL:
  derived routes and their stamps are journal-first, projection second, same law as
  routes.py:236-262.
- **P2 — authored-route no-silent-overwrite.** Adoption is append-only supersession (#3.2),
  never in-place status flip, and the content hash includes the derivation stamp so adoption
  is a supersession not a fork. Veto-check: silent promotion or origin laundering is the
  inference-as-record lie at connectome.py:37-38.
- **P3 — promotion carries derivation history.** The adopted record retains the proposed
  route's `derivation` field. A promoted route that cannot be traced back to "a machine
  proposed this" is laundered.
- **P4 — door-list renders with every door resolving or IS-NOT.** Absence means never-was;
  dangling means formed-then-broken; the two are different and both are visible. Free —
  `_resolve` already returns current|dangling. The render must SHOW it.
- **P5 — degraded pathways name their degradation in the list itself.** An inferred-edge
  door wears `:inferred` in the list and a route ridden over inferred legs is stamped
  degraded end-to-end (connectome.py:372 already sets degraded on the walk). The degradation
  is IN the list, not in a hover state or a log you have to ask for.
