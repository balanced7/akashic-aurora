# T040 Packet Spec v1 -- fenced dual-design brief (2026-07-12)

Charter: same fence as research/t038-t039-implications-brief-2026-07-12.md. Both halves
design BLIND from this brief + the SHARED ground truth below. Blind boundary = the spec
halves themselves: deepseek must not read any claude-*packet-spec* file (none will be in the
repo until his lands); claude's half stays sealed in session scratch until deepseek's record
lands. Reconciliation -> docs/packet-spec-v1-2026-07.md (the artifact every later ship cites,
T031 hook 1). Daniel approves the reconciled spec before any build sub-slice registers.

## Shared ground truth (both halves read freely -- already reconciled or Daniel-raw)
- research/reviewed/t038t039-implications-reconciliation-2026-07-12.md (rulings D1-D6 are
  LAW for this design: fail-direction split by latch class; kill-switch flip-provenanced;
  token/C2 middle path; roster starts at 4; per-flow seq numbers required)
- Both implications halves (claude + deepseek, landed + committed)
- Daniel steers verbatim: notes t039-latch-refinement, t039-networking-lens,
  t038t039-packet-vision, t040-pluggable-endpoints-vision
- docs/packet-substrate-slices-2026-07.md (the arc plan; T040's scope block is the contract)
- Live code: core/comm/bus.py (envelope today: frm/to/kind/content/ts/meta/parts + blobs),
  core/comm/expectations.py (L4), core/coord/runner_lock (generations)

## The design ask (each half delivers ALL of these)
1. FIELD-BY-FIELD SPEC of the v1 envelope header: v, flow, lane, class, ttl, deadline_ts,
   latch[], frag{seq,of,whole_id}, len, sha, idempotency_key -- for each: type, required vs
   optional, default, who writes it (sender/door/substrate), who reads it, validation at
   which door, and the EXACT failure behavior on violation (loud refusal vs downgrade vs
   drop -- cite the fail-direction law where it applies).
2. KIND/FAMILY ROSTER v1: the minimal starting set (grade against the eight families both
   implications halves converged on -- which ship IN v1, which wait), the cap number, the
   registration + deletion ritual, and where the roster LIVES (T034 registry relationship).
3. PER-LANE DELIVERY CONTRACT: one table -- lane x {QoS class, seat discipline, retention/
   trim, wake participation, ACL floor} in MQTT/DiffServ vocabulary.
4. COMPAT + MIGRATION: the v1->v2 rule (dual-version window, downgrade-with-warning shape
   deepseek's addendum sketched), what today's flat envelope maps to (v=1 implicit), and
   the FIRST cutover (which producer moves first, which consumer proves the window).
5. THE RIDING BUILD DELIVERABLE (spec'd precisely enough to register M3 pins from):
   send-door MTU rejection (dial name, default, LOUD message text), len+sha computed where
   / validated where / failure behavior, -partN frag formalization (how 'of' is declared,
   how a missing fragment surfaces, reassembly ownership).
6. WHAT V1 REFUSES TO CONTAIN (the cut list): name what is deliberately absent and why --
   over-speccing the envelope is the T034 Goodhart of this slice.
7. THREE PROBE QUESTIONS a reviewer should ask any envelope spec (your own falsification
   battery -- M3 spirit applied to a design artifact).

## Deliverables (durable doors, the standing rules)
- deepseek: research/reviewed/deepseek-t040-packet-spec-2026-07-12.md via guarded
  write_file, CHUNKED appends (your 4k clip has three receipts now; the spec you are
  writing kills that bug class -- do not let it eat the spec itself). Advisory lock the
  file while writing. Bus reply = short doorbell only. NO knowledge_note dependency (they
  silently failed twice tonight); the FILE is the record.
- claude: sealed half in session scratch, unsealed after deepseek's lands.
- Reconciliation by claude, ruled disagreements flagged for Daniel where load-bearing.
