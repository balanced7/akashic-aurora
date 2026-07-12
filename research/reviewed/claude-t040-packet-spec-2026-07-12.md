# T040 Packet Spec v1 -- claude half

Status: UNSEALED 2026-07-12 (written sealed in session scratch per the fence at
research/t040-packet-spec-brief-2026-07.md; unsealed after deepseek's blind half landed
at research/reviewed/deepseek-t040-packet-spec-2026-07-12.md. Reconciled spec:
docs/packet-spec-v1-2026-07.md -- rulings R1-R8; this half is the verbatim input record.)
Inputs: shared ground truth per the brief (reconciliation rulings D1-D6 as law; bus.py
envelope {frm,to,kind,content,ts,meta,parts}+blobs read this session; both implications
halves; Daniel steers 1-3).

## 1. Envelope v2 header -- field by field
(v1 = today's flat envelope, retroactively named. v2 = the packet header. One table row
per field: who writes / who reads / validated where / failure behavior.)

v (int) -- ABSENT means v1 (today, implicit). Stamped by the SEND DOOR, never sender code.
  Consumers reading v>known: LOG one downgrade warning w/ mid, strip unknown fields,
  process core (never drop mail for schema alone -- work is QoS1; dropping is the wrong
  fail direction). Doors reading v>known at VALIDATION sites: validate what they know,
  pass the rest.
frm / to / kind / content / ts / meta / parts -- unchanged from v1 (compat anchor).
flow (str, optional) -- minted by the sender that OPENS an arc (task claim, fence charter,
  drill start); PROPAGATED by doors: reply/redrive/ack doors copy flow from the packet
  being answered (sender code never has to remember). Read by: flow-addressed routing,
  UI grouping, spine, per-flow seq. Absent = flowless one-off (legal; zero ceremony).
seq (int, optional, REQUIRED when flow present) -- per-FLOW monotonic counter
  (reconciliation FM-P1). Written by sender (door offers next_seq(flow) helper).
  Consumer holds seq N+1 when N missing (bounded by ttl; then LOUD gap event + proceed).
  Per-flow only -- flows never block each other.
lane (enum work|trace|sig|test-<id>) -- DERIVED BY THE DOOR from kind (kind->lane map is
  law, lives with the roster). Sender cannot override outside AKASHIC_DRILL_ECHO test-*.
  Mismatched explicit lane = REFUSED LOUD at send (FM3 dies at the send door).
class (enum halt|interrupt|steer|inform; sig-lane packets only) -- the fidelity rung.
  Authority-checked at SEND door against ACL tier (halt/interrupt = admin+; the F1
  pattern applied to emission). Violation = REFUSED LOUD. Not valid on other lanes
  (cut list #5: no work-lane priority classes).
ttl (int) -- redrives/hops remaining; seeded from dial; decremented by the redrive
  machinery (L4). At 0: expectation_dead path (exists today; unchanged).
deadline_ts (float, optional) -- absolute. Set by sender (L4 arm sets both). INHERITANCE
  RULE (gRPC): doors stamp derived sends w/ min(parent.deadline_ts, own) -- a chain can
  only shrink its budget. Receiver COOPERATES (skips past-deadline work w/ a
  DEADLINE_EXCEEDED note-reply that does NOT clear expectations -- RB-29); sender's sweep
  stays authoritative.
latch[] (list of {type: causal|ref, on: <mid|condition-key>, ttl_s, fail: enforce|depend})
  -- the D1 LAW IS A FIELD: fail=enforce -> expiry stays BLOCKED + loud (review-gates
  class); fail=depend -> expiry proceeds degraded + loud. Creation-time DAG check (cycle
  = REFUSED LOUD naming the path). Consume door checks via latch index (one GET,
  deepseek's shape). type=ref never blocks (provenance only).
frag ({seq, of, whole_id}, optional) -- 'of' is REQUIRED (declared total: a missing
  fragment is DETECTABLE, the anti-silent-clip law). Reassembly owned by the consume
  door: deliver whole, or at ttl emit LOUD partial event naming whole_id + missing seqs.
len (int) + sha (str, sha256 of content) -- computed by the SEND DOOR (the door owns
  integrity, not sender code). Validated at the CONSUME door when present: mismatch =
  INTEGRITY_FAIL event, packet NOT delivered as mail, armed expectation NOT cleared
  (a corrupt reply must never clear its expectation -- RB-29 extended). sha required on
  work/sig at v2-enforce phase; optional on trace (cost honesty).
idempotency_key (str, optional) -- generalizes reply_sent: consumers keep a TTL'd dedupe
  window per key. Auto-set by redrive machinery (redrive_of chain); senders of offer/
  dispatch kinds SHOULD set it (T038 inherits).

WRITER SUMMARY: sender = kind, content, to, flow(mint)/seq, latch, frag, idempotency_key,
class. Send door = v, lane(derived), len, sha, ts, deadline inheritance, flow propagation
on replies. Substrate = id, ttl decrement, redrive meta.

## 2. Kind/family roster v1
REGULARIZED (exist today, get schemas): chat, request, question, reply, handoff, note,
trace, thinking, ledger_update, ack, expectation_dead, presence-beat (control-adjacent).
NEW IN V1 (ship with the riding build + first consumers): status {flow, task_id, pct?,
sub_states?, eta_ts?, last_action} (QoS0, replaces-previous semantics); query {query_id,
target: fleet|agent:<id>|task:<id>, question, deadline_ts} + answer {query_id, answer,
source, freshness_ts} (sig lane; substrate MAY answer presence/ledger/token questions
directly).
RESERVED (schema named now, ships with its slice; reserving prevents kind squatting):
offer/accept/counter/decline/release (T038), dispatch (T038, BUS_DISPATCH authority),
test-attach/test-result (T038+latches; immutable-at-creation + pins-are-floor),
directive-attach (T038; NARROW-ONLY), context-delta (LAST -- FM12 gate must be proven:
trusted producers, provenance headers, gauntlet probe), ui-projection (T041,
advisory-only, ignorable).
CAP: 24 kinds total. Registration = entry in core/comm/packet_spec.py (single .py source
of truth; NOT a service, NOT YAML; T034 registry cross-references, does not absorb).
Deletion ritual = removed{date, reason} marker + guard fails any sender/reader of a
removed kind (T034 shape). Boundary guard extends: a bus send with a kind not in the
roster = ship-gate FAIL.

## 3. Per-lane delivery contract
lane   | QoS/DSCP        | seat/cursor            | retention          | wake | ACL floor
work   | QoS1 / AF       | consumer seat, fenced  | LONG (50k or days) | YES (the only) | registered, non-quarantined
sig    | ~QoS1 / EF      | seatless per-agent scan| MEDIUM (10k)       | no (runner checks between rounds + doorbell) | write rung-gated (class); read registered
trace  | QoS0 / BE       | seatless               | RING (XTRIM 10k)   | no   | write requires may_run (F1: quarantined refused); read open
test-* | isolated        | per-drill              | TTL'd namespace    | production watchers NEVER subscribe | drill env only
V1 HONESTY LINE: sig COMPLEMENTS the existing Redis control keys (pause/halt); the hard
kill path for an IDLE agent remains control-key + doorbell in v1. sig is the message-
lane record of signals; unifying them is a later, receipted decision -- not assumed.

## 4. Compat + migration (v1 -> v2)
Rule: ADDITIVE ONLY within v2; v bump only for semantics changes. Absent v = v1.
Phase A (dual-write window): send door stamps v=2 + new fields; all existing consumers
tolerate unknown fields (verified: _to_msg maps known keys; add a pin that unknown keys
are preserved into meta, not dropped, so nothing is silently lost even pre-upgrade).
Phase B: consumers gain v2 validation behind a dial (per-lane enable: work first).
Phase C: door WARNS on v-absent producers; retire after a quiet week.
FIRST CUTOVER: the deepseek runner reply path -- highest-volume directed sender, and
len+sha there would have caught ALL THREE of tonight's silent losses. The proof-of-window
metric: zero DOWNGRADE warnings on core fleet for 7 days, then flip Phase B.

## 5. Riding build deliverable (M3-pinnable now)
PIN 1 (MTU refuse-loud): Bus.send/broadcast REFUSES content > BUS_MAX_MESSAGE_BYTES
(dial, default 65536): return None + stderr 'REFUSED: message {size}B exceeds
BUS_MAX_MESSAGE_BYTES={limit} -- use frag parts or reduce'. NEVER truncates. Test: send
limit+1 -> refused, stream tail unchanged.
PIN 2 (integrity): send door stamps len+sha; consume door verifies when present;
mismatch -> INTEGRITY_FAIL event + not delivered + expectation NOT cleared. Test: corrupt
a staged entry -> event fires, sweep still redrives.
PIN 3 (frag detectable): frag helper chunks at MTU; drop fragment 2 of 3 in a test ->
LOUD partial event names whole_id + missing seq (never silent, never partial-delivered
as whole).
PIN 4 (the actual bite site): the runner tool bridge (write_file/edit_file/knowledge_note
arg path) routes through the SAME MTU check -- refuse-loud replaces the ~4k silent clip.
Test: replay tonight's three clip payload sizes -> three refusals w/ teaching text.
DRILL: replay-of-receipts -- the 2a-2c append, the knowledge_note payload, oversized
handoff; each must refuse or frag, zero silent losses.

## 6. What v1 REFUSES to contain (cut list)
- Encryption/signing (localhost + ACL trust; revisit only at remote agents).
- Compression (blobs already exist for large payloads).
- Priority classes WITHIN work (no urgent-work tier -- sig exists; T034 Goodhart).
- Expression language in latch.on (mid or named condition key ONLY; no rules engine).
- Sender-chosen lanes (kind->lane is law; test-* under drill env is the only escape).
- A schema registry SERVICE (one .py file; guards enforce it).
- Bundle-latch fields (deferred with bundle-latch itself).
- Vector clocks / cross-flow ordering (single Redis; per-flow seq is the whole story).
- Per-kind payload schemas beyond REQUIRED fields (families own payloads; envelope thin).

## 7. Three probe questions (falsification battery for ANY envelope spec)
P1. 'Which field, if silently wrong, corrupts state without detection?' -- walk every
field to its validator + loud path; any field without one fails the spec (sha's own
guard: mismatch refuses -- safe direction by construction).
P2. 'Show the smallest legal v2 packet.' If a flowless one-line chat needs more than
kind+content+to, ceremony crept in and zero-ceremony-when-simple is violated.
P3. 'Which door rejects a v=3 packet today, and with what message?' Forward-compat
behavior must be DESIGNED now (downgrade-warn, never drop) or v2->v3 repeats tonight's
ad-hoc archaeology.

## Open questions flagged for reconciliation
- sig vs control-keys unification timeline (v1 says complement; when does the receipt
  exist to unify?).
- Roster cap number (24 proposed -- argue me down).
- Should trace sha be dial-enabled rather than skipped (cost measurement first)?
- next_seq(flow) helper: door-side atomic INCR vs sender-side counter (crash semantics).
