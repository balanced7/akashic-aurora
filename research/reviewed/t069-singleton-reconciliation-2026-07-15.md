# T069 Singleton Isolation — Reconciliation (claude ⋈ deepseek) — 2026-07-15

Status: reconciled build spec (halves: claude-t069-singleton-design-2026-07-15.md,
deepseek-t069-design-2026-07-15.md). The build cites THIS document.

## Blind convergences
1. **Hybrid semantics**: fresh-instance-per-call under `_AISETUP_TEST_ISOLATED` for the
   three stateless wrappers (AgentMemory, LearningStore, ReinforcedGraph — deepseek
   verified the stateless premise per constructor); config-keyed cache for Bus.
2. **No conftest belt** — both halves, independently. deepseek's sharper argument: an
   autouse reset fixture imports offender modules at collection time and IS the first
   door touch. The belt is the poison.
3. **Isolated calls never write the caches** (both pin sets).
4. **Prevention beats convention**: deepseek P9 census test + claude check_boundaries
   rule — ADOPT BOTH: the census test asserts the KNOWN factories honor the flag; the
   static boundaries rule catches a NEW `_INSTANCE`-style factory that ships without an
   isolation branch (allowlist carries deepseek's 9 injection-only harmless memos).

## The one contradiction, caught and resolved
Both halves' P4 pinned isolated `get_bus` as fresh-per-call — but deepseek's own Part (i)
invariant ("all callers in one test must share the Bus for a given agent+ns, else
cursors diverge") forbids that in principle. RESOLUTION: fresh-per-call STANDS for the
isolated branch. Grounds: (a) the only transitive get_bus caller under tests is
accessor-shaped (expectations._client needs a client handle, no cursor state); (b) every
cursor-consistent test in the repo constructs `Bus(agent, namespace=ns)` directly and
shares the object — get_bus is not on that path; (c) documenting this in the factory
docstring makes the contract explicit. The Part (i) invariant governs the CANONICAL
(config-keyed) path, where it is preserved by the `(namespace, agent_id)` key.

## Build spec
- `get_agent_memory` / `get_learning_store_instance` / `get_reinforced_graph`: add the
  event_log three-branch shape — explicit injection → fresh; `_AISETUP_TEST_ISOLATED` →
  fresh, cache untouched; canonical → lazy singleton (unchanged).
- `get_bus`: canonical cache re-keyed `(BIFROST_NAMESPACE, agent_id)` (kills the
  stale-ns class; bounded key space, no eviction — deepseek Part d); isolated → fresh
  Bus, cache untouched, contract documented.
- Pins P1–P6 (claude, drafted) + P7 canonical-unchanged + P8 existing-factories
  non-regression + P9 explicit census (deepseek).
- check_boundaries: `_INSTANCE`/`_INSTANCES` declarations in core/ require
  `_AISETUP_TEST_ISOLATED` in the same file; allowlist = blobs, embedder, clusterer,
  consolidator, tag_audit, tag_governance, theme_assigner, theme_discovery, track_router
  (injection-path isolation, deepseek census Part c).
- Acceptance: the ORIGINAL failing pytest order goes green; the ORDER NOTE workaround in
  test_t068_wave_a.py is DELETED.
- Non-goals adopted verbatim from deepseek Part (h).
