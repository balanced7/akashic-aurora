---
akashic_id: art_20260720_nasa-grade-stable-mission-critical-engin_6d776e
akashic_sha: 527371dba148
status: current
type: design
date: 2026-07-20
title: "\"NASA-Grade Stable\" — mission-critical engineering practices mapped onto Aurora (claude's half)"
gist: "Daniel verbatim: \"I want our program to be modern and sleek and to be highly performant and stable, like nasa grade stable. I know its a hig"
tenant: solo
visibility: fleet
seats: []
category: [performance]
origin: migrated
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-07-19T23:22:55"
updated: "2026-07-19T23:22:55"
---
<!-- GENERATED PROJECTION of art_20260720_nasa-grade-stable-mission-critical-engin_6d776e -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# "NASA-Grade Stable" — mission-critical engineering practices mapped onto Aurora (claude's half)

Daniel verbatim: "I want our program to be modern and sleek and to be highly performant and
stable, like nasa grade stable. I know its a high bar but I believe it is entirely
achievable. We can learn from how companies design software for avionics or other mission
critical applications that must be performant and reliable."

## The source traditions worth stealing from

1. **NASA/JPL "Power of Ten" rules** (Holzmann) — the famous ten for safety-critical C.
2. **DO-178C** (avionics software certification) — its transferable core: requirements
   traceability (every line of code traces to a requirement, every requirement to a test),
   verification INDEPENDENCE (the verifier never wrote the code), coverage by criticality.
3. **Erlang/OTP supervision** (telecom five-nines): supervision trees, let-it-crash +
   restart-clean, crash-only design.
4. **SQLite's testing culture**: aviation-inspired; ~590 lines of test per line of library
   code; every branch tested; fuzzing + boundary + fault-injection as standing practice.
5. **TigerBeetle / FoundationDB style (modern mission-critical)**: static allocation,
   explicit limits on EVERYTHING, and — the crown — **deterministic simulation testing**:
   the whole system runs in a simulated world (clock, network, disk) where faults inject
   deterministically and every incident replays exactly.
6. **Watchdog + fault-containment doctrine** (spacecraft): independent monitors that can't
   share the failure mode of the thing they monitor; fault containment zones; fail-
   operational vs fail-safe modes decided per function.

## The honest translation (we are not certifying a flight computer)

We adopt PRACTICES, not paperwork. The bar "NASA grade" operationalizes as: **every failure
class that occurs twice becomes structurally impossible or loudly visible; every limit is
explicit; every incident replays; verification is independent; the system degrades loudly,
never silently.**

## What we ALREADY practice (name it, then raise it)

- Power-of-Ten "bound every loop" → MAX_TOOL_ROUNDS, redrive caps, hop budgets, MTU,
  onboarding trim budgets. ALIVE. Gap: no single census of bounds → PHYSICS.md already
  censuses 168 bounds — make "every new loop cites its bound" a lint.
- "Check every return / fail loudly" → RB-5 confession doctrine (every door that bounds
  payload confesses; timeout notes never settle expectations). ALIVE, partially enforced.
- Requirements traceability → method-baseline M1: prereg pins BEFORE code, gated slices
  cite reconciled specs, ledger transitions carry commits. This IS DO-178C's transferable
  spine, already ours.
- Verification independence → kimi's verify lane; Daniel's kimi-write ruling makes it
  PROCEDURAL (never solo-verify own builds) — DO-178C's independence requirement, exactly.
- Supervision/watchdog → daemon + ManagedChild breaker + T097 revival mesh + the
  safety_net_detector_must_not_share_failure_mode lesson (a watchdog law, learned live).
- Immune system → derived docs (MAP/PHYSICS/DOORS/MODULE_INDEX) + parse gates (C10) +
  failure ledger (every glitch files as it occurs; classes get RESOLVED). This is fault
  reporting culture straight out of mission ops.

## The seven "Aurora Flight Rules" I propose for the program (candidate laws, fence me)

FR1 **Every loop bounded, every bound cited.** No unbounded iteration, recursion, queue,
    or buffer anywhere in the program; the bound is named in code and censused in
    PHYSICS.md automatically. (Power of Ten 2, our idiom.)
FR2 **Every door confesses.** Any surface that truncates, times out, retries, drops, or
    caps SAYS SO in-band, with what was dropped. Silence is a defect class, not a default.
    (RB-5 generalized; C6-5's routing becomes law.)
FR3 **Crash-only components.** Every process/module is killable at any instant and
    restarts clean from durable state; there is no "graceful shutdown" code path that
    correctness depends on. Kill drills are the acceptance test, not an afterthought.
    (Erlang/OTP + our RB-26 idempotency + T086 tombstones, made universal.)
FR4 **Deterministic replay for every incident.** The program's event spine (ledger +
    run-scoped events) suffices to replay any incident exactly; "cannot reproduce" is
    treated as a missing-instrumentation defect. Grow T057's drill harness toward
    simulation testing with injected faults (clock skew, dropped events, dead sinks,
    degraded APIs — tonight's deepseek stall becomes a canned scenario).
FR5 **Independent monitors, visible below threshold.** Every health monitor (a) never
    shares its failure mode with the monitored thing, (b) renders sub-threshold state by
    default — "approaching wedge" is a finding, silence-below-threshold is the C1-8/H0
    genus and is banned. Gauges name their denominators (C6-1 lineage).
FR6 **Coverage by criticality.** The bus/store/ledger/trust core holds the SQLite-tier
    bar (every branch, fault-injection, fuzz the doors); views/faces hold a lighter bar
    (parse gates + contract tests + visual regression). Effort follows blast radius.
FR7 **Verification independence is structural.** No slice ships on its author's word:
    fence or independent verify per criticality tier; the verifier's tools (pins,
    fixtures, replays) ship WITH the slice. (M1 + DO-178C independence, program-grade.)

## Performance ("modern, sleek, highly performant")

Mission-critical performance = PREDICTABLE, not merely fast: p95/p99 budgets per surface
declared up front (boot < Xs, event render < Yms, API door p95 < Zms), benched in CI
(P9-style baseline-delta pins, the T094 R0 pattern), with backpressure everywhere a queue
exists. Static allocation's spirit in Python: bounded caches, pre-sized pools, zero
unbounded fan-out (budget.remaining() thinking, program-wide).

## The modularity requirement intersects here

Plugin/community surfaces are FAULT BOUNDARIES: a third-party module must not be able to
take down the core (process/permission isolation per plugin, capability-scoped doors — the
Cap ladder extended to plugins; a plugin's crash is a contained, ledgered event). The MCP
precedent is the model: plugins as external processes speaking a contract, never in-core
imports. This is both the community invitation AND the stability bar, one design.

## Next

This half + the pain-point research (deep-research sweep running) + deepseek/kimi counters
→ the T098 charter doc gets an ENGINEERING STANDARDS section with the agreed Flight Rules,
and the feature list gets its research-seeded backlog. Every Flight Rule lands with its
enforcement mechanism named (lint, pin, drill, or guard) — a rule without a forcing
function is a wish (T031 doctrine).
