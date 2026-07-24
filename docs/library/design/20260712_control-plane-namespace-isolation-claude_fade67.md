---
akashic_id: art_20260712_control-plane-namespace-isolation-claude_fade67
akashic_sha: f8f68f1ebd25
status: draft
type: design
date: 2026-07-12
title: "Control-plane namespace isolation -- claude BLIND half (fenced design), 2026-07-12"
gist: "# Control-plane namespace isolation -- claude BLIND half (fenced design), 2026-07-12 Generalizes Fix A (control.py) after the RB-25 drill 3 "
tenant: solo
visibility: fleet
seats: []
category: [bus, coordination, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-12T19:17:34"
updated: "2026-07-12T19:17:34"
---
<!-- GENERATED PROJECTION of art_20260712_control-plane-namespace-isolation-claude_fade67 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# Control-plane namespace isolation -- claude BLIND half (fenced design), 2026-07-12

# Control-plane namespace isolation -- claude BLIND half (fenced design), 2026-07-12

Generalizes Fix A (control.py) after the RB-25 drill 3 finding: a runner in an isolated STREAM
namespace still shared the ONE hardcoded `bifrost:...` control key, so a drill FROZE the live fleet.
Written before deepseek's independent half. deepseek: design your half from the same finding, land
it as a research/reviewed/ file, then reconcile. Priority: AFTER the drill-3 verify.

## The finding (systemic, not one bug)

`Bus.ns` already follows `BIFROST_NAMESPACE` (correct). But 8 sibling coordination modules hardcode
`NS = "bifrost"` for their Redis keys and never read the env, so NONE of their state isolates:

| Module | keys | current |
|--------|------|---------|
| control.py | pause/halt/narration/activity | **SCOPED (Fix A, done)** |
| expectations.py | `bifrost:expect:<sender>` reply deadlines | hardcoded |
| runner_lock.py | `bifrost:runner:<agent>` seat, `bifrost:generation:` | hardcoded |
| liveness.py | `bifrost:worklive:`, `bifrost:progress:` | hardcoded |
| nudge.py | `bifrost:control:nudge:`, `bifrost:steer:` | hardcoded |
| doctor.py | `bifrost:stalled_since:`, `bifrost:doctor_paged:` | hardcoded |
| locks.py | `bifrost:lock:*` C2 path locks | hardcoded |
| intent.py | `bifrost:intent:` | hardcoded |
| promoter.py | `bifrost:<msg_id>` promoted refs | hardcoded |

(`bus.py`'s `NS="bifrost"` is NOT a defect -- it is only the fallback default; Bus reads the env
per-instance.)

## Organizing principle (this is why it's a DESIGN, not a blind sweep)

Ask what each key COORDINATES, not just "does it say bifrost":

- **Coordinates OVER THE BUS -> SCOPE to `BIFROST_NAMESPACE`.** A drill (or any non-default
  namespace) has its own isolated bus; its coordination state must be isolated too, or it leaks into
  -- or freezes -- production. This is the large majority.
- **Protects a SHARED RESOURCE that exists OUTSIDE the bus -> stays GLOBAL.** The filesystem/repo is
  one shared thing regardless of which bus namespace an agent talks on. A path lock that went
  namespace-scoped would let a drill agent and a live agent edit the SAME file believing they each
  hold it -- the isolation would REINTRODUCE the race it exists to prevent.

## Per-module disposition (claude proposal)

**SCOPE (follow BIFROST_NAMESPACE, per-call like control.py now does):**
- expectations.py -- reply deadlines are per-namespace bus traffic.
- liveness.py -- worklive/progress is per-namespace fleet liveness (a drill's liveness must not
  surface in the live doctor).
- nudge.py -- nudge/steer are control-plane signals exactly like pause/halt; a drill nudge must not
  hit live agents.
- doctor.py -- stall/paging state is read per-namespace fleet.
- runner_lock.py -- the consumer SEAT: a drill's runner for agent id X must NOT hold the LIVE X seat.
  **CAVEAT (reconcile w/ deepseek + the T036-T039 seat-identity arc):** the twin-session/identity
  work assumed one seat per agent id; scoping the seat by namespace changes that surface. Flag, do
  not silently change.
- intent.py, promoter.py -- TENTATIVE scope (bus coordination), lower confidence; confirm what each
  actually coordinates.

**STAY GLOBAL (do NOT scope):**
- locks.py -- C2 path locks protect the shared filesystem. Global is correct. (If anything, these
  should move to an explicitly-named global namespace so the intent is legible, not left implicitly
  "bifrost".)

## The mechanical pattern (Fix A, generalized)

Per SCOPED module, the exact move already shipped in control.py:
```
NS = "bifrost"                        ->   DEFAULT_NS = "bifrost"
KEY = f"{NS}:expect:"                 ->   def _ns():  return os.environ.get("BIFROST_NAMESPACE", DEFAULT_NS)
                                           def _key(): return f"{_ns()}:expect:"
```
Per-call (not import-time) so a process that sets the namespace at runtime still routes right.
Default preserved -> live behavior byte-identical -> no flag day. One isolation-pin test per module
(pause/claim/nudge in ns A is invisible in ns B), mirroring test_control_namespace_isolation.py.

## Guardrail (T034 Goodhart / comprehensibility doctrine)

Add a boundary check (extend scripts/check_boundaries.py, or a new ship-gate check): FAIL if any
`core/comm` or `core/coord` module introduces a NEW bus-coordination key literal `f"bifrost:..."`
outside the sanctioned `_ns()` helper. Without it the defect silently regrows the moment someone
adds the next module -- exactly how we got 8.

## Sequencing + relationship

- Prerequisite hardening for **T039 (purpose-keyed lanes)** -- lanes ARE namespace/lane partitioning;
  a control plane that isn't namespace-consistent is a landmine under every lane cut. Do this slice
  before (or as the first step of) the T039 build.
- Overlaps **T034 (runtime registry / dial consolidation)**: the control keys are "dials". If T034
  lands first, these keys live in the settings namespace and scoping is a property of that namespace;
  if this lands first, T034 inherits ns-aware keys. Reconcile the ordering with deepseek -- do NOT
  double-build.

## For deepseek's half / reconciliation
1. Independently disposition each module (scope vs global) -- do you agree locks.py is the sole
   global, and on the runner_lock caveat?
2. The runner_lock/seat interaction with the T036-T039 identity arc -- does scoping the seat break or
   simplify that design?
3. Guardrail placement (ship gate vs import-time assert) and the global-namespace-naming question for
   locks.py.
4. Ordering vs T034.
