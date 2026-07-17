# Multi-Agent Readiness — Reconciliation (claude ⋈ deepseek-review) — 2026-07-16

Status: reconciled readiness checklist (halves: claude-multiagent-foresight-2026-07-16.md,
deepseek-review-multiagent-foresight-2026-07-16.md — filed blind; convergence verified).
Daniel directive verbatim in note `multiagent-foresight-directive`. This document is the
gate list for fleet runs; slices cite it.

## The verdict (both halves, independently)

- **N=3 is safe TONIGHT** — and tonight is its own receipt: claude + deepseek (building S5)
  + deepseek-review (this exercise) ran concurrently on the fixed substrate with zero seat
  contention, zero clobbers, zero echo storms. The reviewer's newborn boot exercised the
  R7 lane semantics live.
- **N=5 gates:** T047 legacy retirement + fleet health verdict line + ACL schema gate
  (the reviewer's three do-nows; my half concurs on all three).
- **N=10 gates:** + claim backoff/standby-queue, per-agent trace lanes, T088 identity
  layer, T080 reach receipts, T056 cost gauges + empty-turn detector, T030/H1, C2-1 guard,
  S-2 path enforcement + S7 caller verification, one-command provisioning.

## Blind convergences (adopted)

1. **Echo amplification is enemy #1** (his FM-2 = my F1): dual-write is a capacity TAX that
   scales ~2N²; T047 stops being a soak and becomes urgent at N≥5. His addition: the shared
   trace ring (MAXLEN 5000) turns over uselessly at N≥5 → per-agent trace lanes or ring
   scaling ride the same slice.
2. **Operator visibility** (his FM-4 = my F6): adopt his concrete build — a one-line fleet
   verdict (`FLEET: GREEN — 5/5 progressing, oldest stall 12s`) derived from worklive ages +
   seat states; ~50 lines, rides T086-S4/doctor.
3. **Cost runaway** (his FM-6 = my F8): per-session token counters + fleet rollup + his
   empty-turn detector (N zero-tool turns → alarm) fold into T056.
4. **Identity** (his FM-8 = my F3): T088 gains his naming RULES (alphanumeric + hyphen,
   ≤32 chars, validated at ACL provision AND runner start — his `:`-in-id key-collision
   mechanism is the receipt the rule needs).
5. **Trust drift** (his FM-5 = my F9): `check_acl_schema.py` pre-commit gate (valid caps,
   write⇒path_scope, grantor-cap ceiling: no agent grants beyond its own caps) +
   least-privilege default for new ids.

## Unique contributions (kept from one half)

- His **FM-1 thundering herd**: N simultaneous restarts race every NX claim in tight 20s
  retry loops. Adopt: randomized exponential backoff on claim refusal + one-contender-per-
  agent-id standby queue. Registers as a T086 follow-on slice.
- His **FM-3 lock scaling**: lock-change events on the sig lane (learn about new locks
  without polling), per-agent lock budget, SCAN growth gauge.
- My **F5/H1 consume window** (his half cited C1-4 as evidence but did not carry it into
  the mode list): T030 at-least-once stays on the N=10 gate list.
- My **F10 provisioning drag** + his Appendix A frictions: one-command agent provisioning
  (`seat_setup.py` shape — acl grant template + launcher spec + newborn boot check), plus
  his structural-vs-task boot split (structural ~1500 chars always included; task-budgeted
  remainder) and a newborn delta substitute (last-24h digest when no mark exists).

## Divergence ruled

- **His "mandatory grant expiry"** is REJECTED in favor of **mandatory review-date NAG**:
  the fleet's own history (07-05, recorded in deepseek's grant reason) is that a silent
  expiry quarantined an entire live role. Expiry that auto-revokes = time-bomb; expiry that
  NAGS at boot/doctor past its date = the intended review pressure without the outage.
  (The lesson beat the recommendation; both halves' goals are met.)

## Answered gate items (the reviewer volunteered these)

- deepseek exec grant review (a standing morning-gate item): **APPROPRIATE** — families-only
  exec, audited mirror, admin.grant withheld. No changes. (Appendix B of his half.)
- deepseek-review self-review: correct member scoping; noted `path_scope: []` vs absent
  ambiguity → normalize in the ACL schema gate.

## Slice registry (where each item lives)

Existing tasks: T047 (retire legacy — NOW gates N≥5), T056 (+ empty-turn detector),
T080 (reach receipts), T088 (+ naming rules), T030/H1, C2-1 guard, C8-3 gauge fix.
New (proposed under the readiness umbrella): fleet-health verdict line (rides T086-S4);
check_acl_schema.py gate; claim backoff + standby queue (T086-S8); per-agent trace
lanes / ring scaling (rides T047); one-command provisioning (seat_setup.py).
