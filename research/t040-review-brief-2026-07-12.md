# T040 spec review + endpoint/system ideation -- fenced brief for deepseek (Daniel-directed, 2026-07-12)

Daniel steer (verbatim intent): "have deepseek review [the T040 packet spec] and see if there is
anything else we should add or modify given the rigorous prior-art networking research we did. Have
it come up with useful endpoints / systems that would be nice for us to have."

This is a FENCED dual pass. deepseek produces its half INDEPENDENTLY from this brief; claude produces
its half blind (sealed, not shared until deepseek's lands); then we reconcile. Deliver deepseek's half
as a FILE in research/reviewed/ (per t042 -- the handoff lane crashes on your runner; a bus ping +
file path is the durable channel).

## What to read

- The spec under review: `docs/packet-spec-v1-2026-07.md` (v1, design-complete, 3 open footer items:
  kind-roster cap 12, trace-integrity default off, R8 per-flow sequencing ack).
- The fenced halves that produced it: `research/reviewed/claude-t040-packet-spec-2026-07-12.md`,
  `research/reviewed/deepseek-t040-counterreview-2026-07-12.md`.
- The networking prior-art research to measure the spec against:
  - `research/reviewed/recall-networking-reconciliation-2026-07-12.md` (recall-as-network: C1-C9,
    rulings R1-R8, roster N0-N7; the internet-transport lens).
  - Steers: notes `t039-networking-lens` (DSCP/DiffServ, QUIC HOL-blocking, TCP TIME_WAIT, MTU/frag,
    W3C Trace Context/OTel, gRPC deadline propagation, SDN control/data-plane split),
    `t038t039-packet-vision`, `t040-pluggable-endpoints-vision` (the ACI thesis: packets as the
    universal plug; a module's ONLY cross-boundary interface is the packet families it emits/receives).
  - `docs/packet-substrate-slices-2026-07.md` (the arc; T041 = pluggable endpoints).

## Your two questions

**Q1 -- Spec review against the prior art. What should we ADD or MODIFY in v1?**
Grade the spec against the networking research: did we adopt each relevant pattern at the right depth,
or leave value on the table? Concretely, examine at least:
- envelope header completeness (did we miss a field the prior art makes standard -- e.g. priority
  class beyond lane, congestion/ECN signal, retry/backoff hint, auth/signature slot deferred vs needed)?
- the per-lane QoS contract (MQTT QoS + DiffServ) -- correct mapping? any lane under/over-specified?
- OTel/W3C-shaped ids (flow=trace_id, packet=span, ref-latch=link) -- exportable as claimed? gaps?
- the v1->v2 dual-version migration rule -- robust to a real field addition?
- the 3 open footer items -- your ruling on each.
Anti-goal (T034 Goodhart 1): more fields/kinds is NOT better. Flag anything to CUT as readily as add.

**Q2 -- Useful endpoints / systems (seeds T041). What would be nice to have, given the substrate?**
The packet spec makes "a module = the families it emits/receives." Propose concrete
endpoints/systems that become cheap or newly-possible once the substrate exists -- each as
{name, families emitted, families consumed, what it replaces or newly enables, why it earns its keep}.
Seeds already floated (extend / challenge / replace): substrate observer-projector (status/query/answer
families; standing queries replacing doctor polls; exam bars as continuous monitors), event-sourced UI
projection (T033/T002 consumers), context-delta producer (the recall funnel, behind the FM12 gate),
looking-glass (per-flow trace viewer). Dream-gate (Daniel): a new module lands with ZERO new CLI verbs
and the system's `discover` output gets SHORTER, not longer. Keep the family roster CAPPED (deletion
ritual per addition).

## Constraints
Engine-first still governs BUILD order (T029 must close first) -- this pass is DESIGN. One machine,
one Redis, N<10 agents (no distributed-systems scale claims). At-least-once + idempotency, never
exactly-once. Return your half as a research/reviewed/ file; claude reconciles.
