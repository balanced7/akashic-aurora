---
akashic_id: art_20260714_t060-m1-continuous-presence-fence-brief_4f1905
akashic_sha: 2be1606da659
status: fossil
type: brief
arc: T060
date: 2026-07-14
title: T060-M1 continuous-presence fence brief
gist: "# FENCE BRIEF — t060-m1-design (M1 Continuous Presence) Tier: full (blind halves; reconciliation follows). This brief is shared input and co"
tenant: solo
visibility: fleet
seats: [claude, deepseek]
category: [method, agent-lifecycle]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-23T22:03:08"
updated: "2026-07-23T22:03:08"
---
<!-- GENERATED PROJECTION of art_20260714_t060-m1-continuous-presence-fence-brief_4f1905 -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# T060-M1 continuous-presence fence brief

# FENCE BRIEF — t060-m1-design (M1 Continuous Presence)

Tier: full (blind halves; reconciliation follows). This brief is shared input and contains NO design.

## Question

Design "continuous presence": formalize the runner + wake-listener architecture into **daemon peers**, so every agent is ALWAYS reachable (a directed message never waits for a human to arm anything) and ALWAYS resumable (a dead component comes back without losing thread state) — instead of presence that is session-bound and dies with each seat.

## Why now (raw evidence only — no diagnosis offered)

- Tonight a cleanly-ended predecessor session left claude unreachable-but-seat-holding for a 30-min TTL window (receipt in note `tonight-plan`).
- T073 shipped Phases 1+2 (wake_worthy gate, --to-incarnation addressing) and parked the resident-dispatcher question for "Phase 5 / M1" — M1 is NOW.
- The stop-hook still demands MANUAL re-arming of bifrost_wake per session; hook-spawned processes are not harness-tracked (T073 evidence).
- The runner + UI died with the previous session and were relaunched by hand tonight (fleet-relaunch ritual in `where-we-are`).

## Inputs (read yourself; cite file:line)

- scripts/bifrost_runner_deepseek.py (your own consume loop, runner_lock, hop guard)
- scripts/bifrost_wake.py + scripts/hooks/claude_stop.py (the session wake path)
- core/comm/dispatcher.py (parked resident dispatcher; T073 ruled it out for that arc — its designated review point is M1)
- core/comm/runner_lock.py (seats / tenure / generations)
- docs/library/report/20260715_t073-wake-communicate-reconciliation-cla_a6fc12.md
- docs/library/report/20260714_wishlist-synthesis-both-seats-one-map-20_90759f.md (the M1 seed line)
- docs/LIVE_CONSTRAINTS.md (RB rules that bound any design)
- docs/ROADMAP.md System-0 framing, if useful

## Output shape (design DOC only — T060 is a design wave; NO code changes)

Write `docs/library/report/20260715_t060-m1-continuous-presence-design-blind_ebd800.md` containing:

1. **Ground truth**: components that exist + their lifecycles (who spawns each, who watches it, who restarts it) — file:line grounded
2. **The design**: daemon-peer architecture — lifecycles, supervision, restart policy, failure modes, identity/seat interaction, and how it varies per harness tier (claude-code session vs your runner vs cursor)
3. **Exists-vs-missing table**
4. **Pins-style acceptance list** (M1-prefixed)
5. **Who-builds-what + migration path** (strangler — no big-bang cutover)
6. **Non-goals**
7. **Confidence + grounding_quality per major section** (T049 structured uncertainty)

## Rules

- **BLIND half**: no claude M1 sketch exists in the repo; do not seek one. Design from code + docs + your own lived runner experience.
- Cite file:line for every claim about existing code (M1-PV checks citations at seal time).
- When done: write the file, then send `[t060-m1] DESIGN HALF FILED <path>` (kind=handoff, to claude).
- **YIELD RULE**: if a handoff arrives mid-work whose text starts with `[verify]`, PAUSE this design, do the verify first (a verify gates a mirror), then resume this.
- Budget: think=on tonight — go deep. If the hop loop-guard bites, file what you have and note the cut point.
