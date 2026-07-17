# Multi-Agent Failure-Mode Foresight — claude half (2026-07-16)

Status: blind half (filed before reading deepseek-review's). Daniel directive verbatim in
note `multiagent-foresight-directive`. Evidence base: docs/failure-ledger-2026-07.md (every
class below extrapolates from a two-agent incident that ALREADY happened), t086 reconciliation,
tonight's live provisioning of deepseek-review (receipts inline).

## Failure modes for N-agent runs (trigger → blast radius → earliest signal → containment)

F1 **Echo amplification.** Dual-write legacy lane × N agents × redrives: every ask exists
2×, every redrive multiplies it, every new agent adds a consumer that can re-answer stale
copies. Blast: token burn + wrong-work (deepseek lost a morning to 67 echoes). Signal:
pending-count gauge at boot (T076b, unbuilt). Containment today: T076c settle + skip-to-now
(sender-side only until S6 durable dedup lands). ROOT: T047 retire the legacy lane. UNCONTAINED
at N>2 until T047.

F2 **Ghost/zombie seats at scale.** Every agent-session pair arms watchers; every crash or
window-close mints a candidate ghost. Blast: unwakeable agents, mail blackholes. Signal:
doctor + standby seat reports. Containment: S1 tombstones + S2a renewal-primacy + S3 backstop
dedup — CONTAINED for harness seats (three live receipts today incl. probes); runner-side
supervision arrives with S5 (in flight tonight).

F3 **Identity collision.** Two processes boot one agent_id simultaneously: runner-vs-runner
is REFUSED (singleton lock — live receipt tonight: my relaunch was refused while the killed
runner's 20s TTL drained); session-vs-session conflates memory/credit/presence (contained
for claude by twin protocol; UNGUARDED for accidental new-id collisions). No registration
handshake; no display names (Daniel cannot tell 5 agents apart in the UI). T088, unbuilt.

F4 **New-file write collisions.** Advisory locks cover existing hot files; NEW files have a
naming convention only (C2-1, live incident 2026-07-16 W4). At 5 writers the convention WILL
miss. Containment: per-surface naming + locks; the create-collision guard (C2-1 proposal)
unbuilt. Partial.

F5 **Consume-window message loss.** Crash between read and process loses the in-flight copy
(H1); redelivery dedup in-memory only (C1-4). N agents = N crash surfaces. T030 unbuilt.
Sender-side L4 redrives mask singles; storms mask the masking. Partial containment.

F6 **Operator blindness.** Daniel broadcasts to N agents; nothing reports who received,
who acted, who ignored (T080 designed, unbuilt). Blast: silent non-compliance reads as
consensus. At N=2 he reads both transcripts; at N=6 he cannot.

F7 **Gauge corruption under concurrency.** C8-3 (hook double-fire) already halves the
funnel's honesty at N=1 seat-type; concurrent writers on shared counters (funnel, injections,
turn_metrics) have no per-writer attribution audit. Tuning decisions ride corrupted numbers.
Fix C8-3 + T056 per-agent meters before ANY fleet tuning.

F8 **Cost runaway.** Per-runner token journals exist; no fleet rollup, no budget alarm, no
per-arc ROI join (T056). An echo storm or a looping agent burns silently. Signal today:
Daniel's bill. Unacceptable at N>3.

F9 **ACL sprawl / trust drift.** Each new agent = a hand-edited grant (tonight: reviewer
grant took one edit + one restart-quirk). At N agents, grants drift, path_scope stays
ADVISORY (S-2 unbuilt), and the mirror family's caller-verification gap (S7) widens: any
fleet process can tombstone/commit within scope. Needs: grant templates + S-2 enforcement
+ S7 caller checks.

F10 **Onboarding drag.** Every new agent pays the cold-start tax: tonight's reviewer needed
a quoting-bug restart and its boot skipped once (root mangling); the CLI probes needed three
rounds to get working hands. Newborn semantics (R7) and boot-fold WORK once configured —
but provisioning is a hand ritual. Needs: `seat_setup.py`-style one-command provisioning
(probe round-2's recommendation, generalized to runners).

## Readiness bars (my half's recommendation)

- **Small fleet (3-4 agents), supervised runs:** T047 + S5/S6 + C2-1 guard. Closes every
  class with a live two-agent incident on record.
- **Stress-free fleets:** + T088 (registration + display names), T080 (reach receipts),
  T056 (fleet cost rollup + alarm), C8-3 fix, S-2 path enforcement, S7 caller verification,
  one-command agent provisioning.
- **Keep as doctrine:** distinct agent_id per process, per-surface file naming, pins-before-
  mirror, the fence for anything load-bearing, quarantine-by-default for unknown ids.

Honest bound: F1-F10 extrapolate from one week of two-agent operation; the reviewer's half
sees the substrate with fresh eyes and may find classes invisible from inside. Reconciliation
follows both halves.
