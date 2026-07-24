---
akashic_id: art_20260715_t069-singleton-isolation-claude-half-bli_f884b1
akashic_sha: c0333db5dc3a
status: draft
type: report
date: 2026-07-15
title: T069 Singleton Isolation — Claude Half (BLIND) — 2026-07-15
gist: "subsystem, I want our best effort on it\"). deepseek's half: deepseek-t069-design-2026-07-15.md. Build follows the RECONCILED spec only. ## T"
tenant: solo
visibility: fleet
seats: []
category: [method, testing, tooling]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-15T00:08:36"
updated: "2026-07-15T00:08:36"
---
<!-- GENERATED PROJECTION of art_20260715_t069-singleton-isolation-claude-half-bli_f884b1 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

> **DRAFT** -- unpromoted; the wrap sweep + library lint curate drafts.

# T069 Singleton Isolation — Claude Half (BLIND) — 2026-07-15

subsystem, I want our best effort on it"). deepseek's half:
deepseek-t069-design-2026-07-15.md. Build follows the RECONCILED spec only.

## The defect, precisely

A door touch under live env pins module singletons for every later consumer expecting
isolation. Reproduced: pytest order [t068_wave_a → boot_orientation → agent_interface]
fails 3 tests; reversed passes 19/19. The repo PATTERN exists (event_log/event_query:
`_AISETUP_TEST_ISOLATED` → fresh instance, never cache; tests/isolate_canonical.py) —
four factories never adopted it: get_agent_memory, get_learning_store_instance,
get_bus, get_reinforced_graph. get_bus has a second, RUNTIME defect: its cache keys on
agent_id only while Bus bakes BIFROST_NAMESPACE at construction — a namespace flip
serves a stale-ns bus (the class expectations Fix A fixed per-call on 2026-07-12).

## My position on the semantics fork

**Fresh-instance-per-call under the flag (event_log precedent), NOT config-keyed test
caches.** Premise that makes it safe — verified per factory: these are stateless
wrappers over external state (AgentMemory(store), LearningStore(store), Bus(client),
ReinforcedGraph(store)); durable state lives in the Store/Redis/files, so two fresh
wrappers over the same isolated paths see the same state. Fresh-per-call also matches
the existing isolate_canonical.py contract, so no test-harness migration.

**Config-keyed caching IS right for one surface: the non-isolated get_bus cache.** Key
it `(namespace, agent_id)` so runtime ns flips (drills) get correct buses. Bounded
growth: namespaces are few (live + test-*); an eviction story is not needed at current
scale — flag it for the reconciliation if deepseek's census disagrees.

**Isolated calls must never WRITE the caches** (my pins assert this) — matching
event_log, and preventing an isolated run from donating instances to a later live run.

## Census (my initial sweep — deepseek's half owns the exhaustive pass)

Offenders: the four factories above. Inheriting the fix: expectations._client (routes
through get_bus("expect")). Suspects I did NOT clear: turn_metrics._est_cache
(time-keyed memo — likely harmless, ns-blind?), promoter/at_action module caches,
core/signals coordinator caches. The reconciliation should dispose of each explicitly.

## Belt question

A conftest autouse reset of known caches is REDUNDANT debt once factories honor the
flag — my vote is NO belt. The durable guard instead: a check_boundaries rule (T031
energy) — any module-level `_INSTANCE`/`_instances` factory in core/ must contain an
`_AISETUP_TEST_ISOLATED` branch, enforced mechanically so the NEXT factory can't
reintroduce the class.

## My pins (drafted, uncommitted — tests/test_t069_singleton_isolation.py)

P1/P2 agent_memory + learning_store: flag-on → fresh per call, cache unwritten.
P3 get_bus: ns flip serves correct-ns bus (RED today). P4 get_bus flag-on: fresh, cache
unwritten. P5 the original coupling in-process: door touch then isolated consumer →
fresh instance (regression for tonight's failure). P6 reinforce: flag-on fresh.
Acceptance beyond pins: the ORIGINAL failing pytest order goes green, and the
workaround ORDER NOTE in test_t068_wave_a.py is DELETED (the fix makes it false).
