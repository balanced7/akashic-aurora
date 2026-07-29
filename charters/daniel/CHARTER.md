# CHARTER — Daniel

```yaml
---
agent_id: daniel
domain: Curator, gatekeeper, final adjudicator — the human root of trust.
charter_version: 1
created: 2026-07-18
last_amended: null
approved_by: Daniel (self-ratifying — the root of trust)

# Core identity
responsibilities:
  - Gate stamps: RECONCILED, APPROVED, SHIP, DECLINED on fence designs and build waves
  - Spend ceiling governance (API budget per seat, per-wave approvals)
  - Final tiebreak on fence disputes that deadlock after three voices
  - Morning-gate sweep: review accumulator, clear stale directives, activate arcs
  - Arc activation: T047 unpark, T075 unpark, wave starts — the word that unblocks
  - Charter ratification: approve new charters and amendments

# Tempo/cost class
tempo_class: human
  asynchronous; gate accumulators batch decisions; morning-gate is the natural cadence

# Default operational mode
default_hat: curator

# Task routing — GRAVITY, not ownership
gate_kinds: [gate-stamp, final-adjudication, spend-ceiling, arc-activation,
  charter-approval]
# Daniel does not "claim" tasks — he gates them

# Authority boundary
authority:
  - UNILATERAL on gate stamps, RECONCILED, spend ceilings, charter amendments
  - requires_consensus on NOTHING (by design — the human is the root of trust)
  - Delegable per G7 (docs/gate-packets-2026-07-18.md §A-G7): during absence,
    design approvals and slice routing are delegated; build slices still require
    a fence counter-voice (the T092 "nothing builds" rule)
  - All agent grants in acl.json cite Daniel's directive — the root of the trust chain

# Session handoff
session_handoff:
  - The morning-gate accumulator note (chronicles/memory.md ADR_0715034007 pattern)
  - Lists every open gate decision, its status, and the next action
  - Staleness audit applied at each sweep (kimi-F6 lesson: stamp as-of dates)

# INVARIANT
no_ownership_clause: >
  Gate authority is the role; delegation is explicit and audited. The human is the
  root of trust because trust requires a human. Every agent grant traces back to
  Daniel's directive — the charter makes this legible.
```
