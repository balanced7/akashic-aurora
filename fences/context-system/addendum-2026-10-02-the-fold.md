# Addendum to the context-system reconciliation — 2026-10-02, the fold

Dated addendum beside the sealed reconciliation, per its own §7 rule: later rounds fold by an
addendum, never by editing sealed text. Author: claude (Vandor). Awaiting Daniel's ratification.

## What this adds

The `one-spine` fence (`fences/one-spine/`, four halves: Heimdall, Navi, Sunshine, Rill) asked
whether Heimdall's four gaps and this Wave 0 table are one spine. **They are**, 4 of 4, and the fold
is three-way rather than two-way. The full reasoning, the three reconciler findings and the weld
order are in `fences/one-spine/reconciliation.md`. What changes HERE, in this table:

| row | change |
|---|---|
| **W0.1** | **DONE** — `core/coord/target.py`, RED `9aee64c9`, GREEN `653b5723`, 73 pins. Built against Amendment 1 (`research/in-flight/context-system-navi-m1-amendment-1.md`), which answers eighteen measured contradictions between the sealed grammar and the live tree. Navi's blind verification is still owed. |
| **W0.2** | now explicitly **absorbs Gap 3** of the record-is-total map. A hook firing IS the idle→active transition, so activity needs no separate `kind`. Asserting that flip is part of W0.2's acceptance. |
| **W0.2a–d** | four new sub-rows: Gap 2 (phase/wedge at `core/comm/liveness.py:146`), Gap 4 (expected/retract/revoke, which is T424), Gap 1 (wire metadata, bodies out), and **Gap 5, new** — Rill's machine-diary design of 2026-09-24, whose S0 spike passed and which covers facts none of the other four reach. |

## Two corrections to sealed text, recorded rather than edited

1. **§3's V35 cite is wrong.** It reads "evolves session_focus's normalize_target". That function is
   `core/recall/at_action.py:835`; `core/coord/session_focus.py` has no such function. Navi ruled it
   a typo (Amendment A11); it is corrected here rather than in the sealed line.
2. **The sealed spec's worktree line treats `E:/AI-Setup-*` as one plane with the two worktree
   directories.** Measured: only `E:/AI-Setup-publish` is a true worktree; `-Alpha`, `-Beta` and
   `-Sandbox` are separate clones owned by the WORLD organ. Amendment A2 rules `work:` covers true
   worktrees only.

## The constraint this round adds, which the sealed round did not carry

> **Daniel, 2026-08-07:** "I think there should be both flavors in the system."

One spine, with the plane kept legible ON it: every gap emit carries its plane in `kind` and its
origin in `detail`, so cross-matching what one plane knows and another does not survives without a
second store. See finding 3 of the one-spine reconciliation.

## Open against this table

`§7`'s first open item — "half-rill.md not filed" — is now **closed**: Rill filed in the one-spine
round and named the Gap 2 emit seam independently of Heimdall, reaching the same line.
