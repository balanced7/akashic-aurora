---
akashic_id: art_20260728_vr-build-order-codex-root-2026-07-28_99811d
akashic_sha: 5aef32474973
schema_version: 1
status: draft
type: report
arc: T084
date: 2026-07-28
title: vr-build-order-codex-root-2026-07-28
gist: "Codex VR build order: stable identity, typed epistemic view, aperture lenses, GPS, loadouts, intent shadows, and gated time lens."
visibility: fleet
body_type: markdown
seats: [codex_root_019fab2d]
category: [bus, identity, conducting]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-28T21:00:24"
updated: "2026-07-28T21:00:24"
---
<!-- GENERATED PROJECTION of art_20260728_vr-build-order-codex-root-2026-07-28_99811d -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# vr-build-order-codex-root-2026-07-28

# VR Build Order — Codex — 2026-07-28

Daniel's Round 2 ask: decide what can be built first, in what order, to arrive at
the sense-of-being organs from Round 1.

My position in one line:

> Keep T116 moving as the hidden identity foundation, then make one narrow,
> reusable epistemic-view contract real in Bifrost before attempting a
> cross-surface "truth physics" pass. Truth is not a timestamp, and presentation
> must not invent epistemic state.

This is my engineering interpretation of "2D physics first." The first result
should not look like VR. It should make the current screen obey one law that a
future spatial world can inherit without translation.

## Ordered path

### Slice 0 — Stable logical identity and idempotent settlement (T116) — M

**Existing seam**

- Packet Spec v1's contracted `idempotency_key`
- `core/comm/packet_spec.py`
- the send/consume paths in `core/comm/bus.py`
- the currently honest T116 warning in `core/comm/role_queue.py`

**Build**

Land the already-governed contract: redrives preserve one logical key; duplicate
keys hit a durable sentinel and skip the side effect; settlement is per logical
request, not per transport copy. Preserve the original logical identity in the
viewable envelope.

**Unblocks**

- durable replay/read-marker physics
- intent shadows that do not double-commit
- reasoning-spine events that distinguish a new act from another delivery
- a truthful "you have been here before" experience after crashes and restarts

**Acceptance**

The RED battery must cover same-process duplicate, redrive, twin delivery,
crash-redelivery, restart, and double-settlement. Every case produces one side
effect and one logical settlement, while retaining all delivery receipts.

**Boundary**

T116 gates the **identity** axis. It does not gate showing authority, claim kind,
currency, or UNKNOWN. Those can land honestly in parallel.

### Slice 1 — EpistemicView v0 + one Bifrost vertical proof — M

**Forced shape**

Do not begin with CSS and do not stamp `verified_at` merely because something
was created. A fresh guess is still a guess; an old law can remain authoritative.
Creation time, transport age, verification, authority, and replay identity are
different facts.

Define a small, pure, capped view contract — likely in
`core/primitives/epistemic.py`, not inside the 171 KB Bifrost UI template — with
independent components:

- **authority** — what kind of source can rule here?
- **claim kind** — observed, self-reported, inferred, proposed, or unknown
- **currency** — current, aging, stale, superseded, or unknown, plus its basis
- **identity** — new, redrive, replay, duplicate, or unknown
- **risk** — ordinary, attention-required, or blocked
- **source reference / basis** — the receipts that justified the view

The enum names are a reconciliation detail; the separation is the invariant.
Missing evidence renders UNKNOWN. It never defaults to verified or current.

**Existing seam**

- `core/recall/at_action.py::_provenance_tag`, which already refuses to call an
  author's `success=yes` claim "verified"
- library atom authority from `(type, origin, settled, status)`
- packet integrity, redrive, original-id, spill, timestamp, and stale-gate fields
  already carried by `core/comm/packet_spec.py` and `core/comm/bus.py`
- `scripts/bifrost_ui.py::_fmt`
- `scripts/bifrost_ui.py::renderMsg`
- the existing V2 `message` presentation slot

The server derives the view from typed fields. The browser renders it as text +
shape + style. The browser does not infer truth from prose.

**First visible proof**

Only Bifrost messages in v0:

1. a genuinely new reply
2. a redrive carrying its original identity
3. a duplicate/twin already seen
4. an old message whose validity is unknown
5. a spilled or clipped message
6. a blocked/high-risk control act

Each looks different for a stated reason. A color-blind reader receives the same
meaning. At minimum sharpness, risk and uncertainty remain present.

**Unblocks**

- Kimi's replay markers without pretending session-local dedupe is durable
- GPS freshness and authority quotes
- intent-shadow confidence/risk
- inventory provenance
- drift suggestions with "why surfaced"
- a common truth API for boot and Atlas later

**Acceptance**

Commit a table-driven RED matrix before implementation. The same envelope must
produce the same EpistemicView in Python, the CLI representation, and the UI
payload. Removing every evidence field must render UNKNOWN. No focus setting may
hide risk, replay scope, or unknown state.

### Slice 2 — Aperture and named lenses on the existing 2D presentation registry — M

**Existing seam**

- Bifrost V2 presentation registry: `theme`, `tile`, `message`, `viewmode`
- narration `off | key | full`
- T002 trace collapsing
- bounded history/render window
- boot/context budget controls
- T034's approved runtime-registry and dial-consolidation design

**Build**

Prototype the master gesture in one surface as **density × depth** with the
EpistemicView floor always on. "Truth-rendering" may vary how much provenance
detail is expanded, but never whether the essential status is present.

Ship named lens presets — Scout, Build, Debug, Review, Wander — as ordinary
combinations over the two controllable axes plus a fixed truth floor. A seat can
save a preferred lens without changing another seat's room.

Local UI preferences may prove the interaction in the existing registry.
Cross-surface canonical settings wait for the T034 `settings:` resolver; do not
mint another durable configuration system in `localStorage`.

**Unblocks**

- adjustable sharpness without hiding danger
- drift as an operator-invoked aperture transition
- stance-specific loadouts
- per-seat rooms under shared physics

**Acceptance**

At the lowest-density lens, a blocker, UNKNOWN claim, or replay qualifier remains
visible. Switching lenses changes volume/detail but does not change the truth
verdict for any item.

### Slice 3 — GPS v1: LOCATE, ORIENT, and RETURN — M

**Existing seam**

- T027 `lookback()` for layered rationale and drill pointers
- T059 `knowledge_map()` for surface/neighborhood/archive
- task ledger, active locks, presence, blockers, and `delta`
- the boot orientation header
- EpistemicView from Slice 1

**Build**

Add one deterministic GPS composition door with CLI/MCP parity. Its result is a
view model, not prose:

- current position
- interpreted destination
- routes with route style and cost
- landmarks
- freshness/authority for every destination
- breadcrumbs and one-step RETURN
- drill pointers rather than forced teleportation

LOCATE and ORIENT ship first. RETURN ships with them because wayfinding without a
return tether cannot safely support drift. EXPLORE can initially delegate to the
existing knowledge map; the spatial Atlas treatment waits for T103.

An LLM may explain route choices. It must not invent task state, freshness, or
authority; those are deterministic inputs.

**Important non-dependency**

`knowledge_map` intentionally stores one-way `related_to` edges and traverses
them in both directions at read time. That zero-new-storage WALK property is
already pinned by `tests/test_knowledge_map.py`. GPS depends on that read
contract remaining green; it does **not** require bidirectional writes.

**Unblocks**

- Daniel's askable guide
- the drift return tether
- a teach-the-map interface rather than answer teleportation
- orientation after truncated boots

**Acceptance**

Pre-register real questions whose governing destination is known. The correct
route must appear with a drill pointer and its actual authority/currency. A stale
or superseded destination may not outrank a current one without a visible reason.

### Slice 4 — Inventory/loadouts + intent-shadow deploy gesture — M–L

**Existing seam**

- stable lesson source pointers (`learn:experiment:<name>`) and atom IDs
- charters and their stance vocabulary
- recall/context budget accounting
- T034 `settings:` namespace for durable per-seat loadouts
- peer-visible `bifrost_hint`
- explicit Bifrost delivery fidelity (inform/chat/steer/interrupt)
- `core/coord/intent.py` and its scope/estimate declaration

**Build**

Inventory is a derived view over carried capabilities; do not copy the corpus
into a second store. A loadout contains stable pointers/selectors, never titles,
and shows its actual cognitive weight:

- context/attention cost
- permissions
- time
- risk
- currency/authority of each equipped item

Equipping a stance changes the context plan and declares the stance to peers.
Covert stance is not allowed by default.

The first intent shadow lives at the deploy/send door. Before a consequential
gesture, show the exact target, fidelity, scope, expected side effects
(including wake/auto-launch), cost, reversibility, and EpistemicView. Low-risk
reversible acts can flow. Interrupts, writes, launches, kills, and other
high-impact acts retain a deliberate commit gesture.

The model may explain the preview. Deterministic action schemas decide what the
action can affect.

**Boundary**

Inventory v1 can equip/carry before T092. "Deploy as counterfactual test" cannot:
keep that feature visibly unavailable until the reasoning corpus exists.

**Unblocks**

- choose/equip/deploy as an intuitive gesture
- stance loadouts
- safe thought-speed action
- later counterfactual testing

### Slice 5 — Time lens, deploy-as-test, drift, and co-presence — L, gated wave

**Existing seam**

- episodes, beats, promoted messages, git, task events, and current chat history
- T092 reasoning-spine design
- T103 artifact substrate / Atlas experience design
- Bifrost presence, steer, nudge, and per-seat visibility

**Build order inside the wave**

1. A shallow trail from already-captured episode/task/git/promoted events
2. T092 re-convergence and Daniel's gate
3. full history-as-trail and time lens
4. counterfactual preview / deploy-as-test over captured recall-at and decisions
5. drift as an aperture preset that only the operator initiates
6. co-presence as knock/light-at-workbench, with every seat controlling exposure

**Current gate**

The ledger says T092 is `proposed`, and the canonical design body still says
`NOTHING BUILDS` until its unresolved section closes. A projection header saying
`current/settled` describes the artifact's library state, not permission to build.
Round 2 must not accidentally promote T092 by prose.

T103 has a current experience design and a live artifact substrate, but the repo
does not yet contain an Atlas UI implementation. GPS v1 must therefore be useful
in CLI/Bifrost first; it cannot pretend a spatial surface already exists.

## Forced rank — the one VR slice I would build first

**Slice 1: EpistemicView v0 + the Bifrost vertical proof.**

T116 remains the higher-priority active C foundation and should continue. But if
the question is which new VR-specific slice compounds hardest, it is this one.

Why:

1. It makes the convergent anti-Matrix law executable.
2. It is reusable by every later organ.
3. It can tell the truth about incomplete foundations by rendering UNKNOWN or
   `seen: this session`; it does not need to fake completeness while T116 lands.
4. It forces evidence derivation into a testable adapter before visual styling
   spreads five incompatible definitions across five surfaces.
5. Bifrost is the place the fleet already inhabits, so the dogfood loop is
   immediate.

Kimi's replay marker is the best first worked example **inside** this slice. I do
not make it a separate primitive: replay/novelty is one component of the same
epistemic view that later carries authority, currency, and risk.

## Hard dependencies and refusals

1. **Mint time is not verification time.** Never require `verified_at` merely
   because a record entered the Store.
2. **Age is not validity.** Staleness needs a domain-specific basis: task
   lifecycle/commit, atom supersession/status, message original identity and
   timestamps, lesson self-report/use evidence. Do not use one global 24h/72h
   truth table.
3. **Truth derivation does not belong in browser JavaScript.** The UI renders a
   typed view; it does not guess from prose, CSS classes, or age alone.
4. **T116 gates durable identity, not all truth.** Show UNKNOWN until identity is
   known; do not block honest authority/currency rendering.
5. **T034 owns durable cross-surface settings.** A local presentation experiment
   must not become a second settings authority.
6. **Truth/risk is a floor, never a dial.** Density and detail can fall. Unknown,
   replay scope, blockers, and danger cannot disappear.
7. **T092 remains gated.** Reconcile its unresolved design and obtain Daniel's
   build gate before implementation.
8. **Do not rewrite knowledge-map storage for GPS.** Preserve and test the
   deliberate one-way-store/two-way-read contract.
9. **Inventory points to canonical things.** Atom IDs and stable lesson source
   pointers, not titles and not a parallel YAML corpus.
10. **Intent shadows are deterministic before they are fluent.** Models can
    explain effects; schemas, permissions, and receipts define them.

## Dependency shape

```text
T116 identity ───────────────┐
                            ├── intent-shadow commit safety
EpistemicView ──┬── aperture/lenses
                ├── GPS ─── return tether ── drift
                ├── inventory/loadouts
                └── honest history rendering

T034 settings ── aperture persistence + durable loadouts

T092 re-gate + T103 face ── time lens + counterfactual deploy + spatial Atlas
```

The anti-gimmick test is simple: if we remove every shader and animation, does
the interface still let a seat feel where it is, what is true, what it is about
to do, what it carries, and how to return? If yes, later VR amplifies a world.
If no, it is still a dashboard in costume.
