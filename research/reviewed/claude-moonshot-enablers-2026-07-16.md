# Moonshot Enablers — claude half (architect lens) — 2026-07-16

Status: blind round-1 half, four-voice panel (Daniel directive; verbatim in note
four-voice-directive). Lens: the substrate seams — what the moonshots (T060 M1-M7,
T079 engine-room, fleet-lattice-vision, recall-as-network) need underneath, ranked by
how much unbuilt future each item unlocks per unit of build.

## Top 6, ranked by leverage

E1 **Headless claude workers — the CLI seat as a spawnable worker tier.** New capability
AS OF TONIGHT: claude CLI installed + workspace trust + repo allowlist = `claude -p
"<charter>"` produces a working, tombstoning, self-reporting seat with zero human taps
(three probe runs = the receipts). Generalize from audit-probe to WORK: `seat_setup.py`
(provision id + grant template) + a daemon verb `spawn_seat(charter, model, budget)`.
This IS M1's worker tier and the lattice's "cheap claude instances" — the missing piece
of continuous presence was never the wake loop, it was on-demand hands.
Smallest version: daemon spawns one charter-scoped CLI seat on a work-lane backlog
threshold; seat files its result and dies clean (S1 already guarantees the dying).

E2 **T047 legacy retirement + per-agent trace lanes.** The capacity floor under every
moonshot: dual-write taxes each message 2×, the shared trace ring saturates at N≥5, and
M7's legible per-agent streams NEED per-agent lanes. Nothing fleet-shaped scales until
this lands. Smallest: retire legacy (spec exists), trace ring per agent id.

E3 **Operator gauges: fleet health verdict + per-agent cost meters + empty-turn alarm
(T056 + readiness items).** Daniel's attention is THE scarce resource; every moonshot is
"runnable by one human" only if fleet state reads in one line and burn reads in one number.
Smallest: FLEET: GREEN/YELLOW/RED line in doctor + token rollup per agent per day.

E4 **Gauge integrity → unpark the knowledge network.** Fix C8-3 (hook double-fire),
recount/annotate the funnel series, THEN unpark recall-as-network (N0-N7 roster, parked
at Daniel's gate since 07-12). The knowledge moonshot is gated on trusting the funnel —
tonight we learned its headline number is ~half-reported. Truth first, then routing.
Smallest: single-surface hook registration + a gauge-correction event + N0 (the dead-ECN
fix from the parked research).

E5 **Capability routing table (T078 → fleet v2).** The lattice needs a routing INPUT:
task-class → tier (frontier/cheap/local/outside) driven by E3's cost data + T078's
capability map. The `fleet` verb already dispatches local models; extend its roster with
API tiers (deepseek, gemini one-shots, headless claude) and let slice stages declare their
tier. Smallest: a static routing table in the ledger task schema (stage → suggested tier),
honored by whoever claims.

E6 **Panel-as-primitive.** Tonight's four-voice exercise, hand-orchestrated, becomes ONE
verb: `py agent_cli.py panel "<question>" --voices <roster>` — blind round → cross-critique
→ synthesis slot, fence workspace underneath (T053 slots exist). Research agents and
review paradigms stop being events and become a ritual any seat can invoke.
Smallest: panel = N ask-scripts + a synthesis template over the existing fence verb.

## The dependency spine

E2 (capacity) and E3 (gauges) are load-bearing for everything; E1 rides tonight's
infrastructure as-is; E4 unblocks the knowledge arc; E5/E6 turn the fleet from a set of
agents into an ECONOMY. If Daniel gates only two: **E1 + E3** (hands + eyes).

## Honest bounds

- E1's cost model (plan-budget per CLI seat) needs one measured week before fleet-scale.
- E4's recount may not be cleanly separable from live counters — may land as an annotation
  epoch ("pre-fix numbers × ~0.5") rather than a rewrite.
- Blind half: filed before reading review/deepseek/gemini voices.
