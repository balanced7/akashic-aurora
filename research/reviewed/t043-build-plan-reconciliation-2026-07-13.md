# T043 send-door hardening — build-plan reconciliation (fenced dual, 2026-07-13)

Status: current  (2026-07-13)
Class: reconciled build sub-spec (T031 hook 1 — the gated ship cites THIS)
Halves (blind, neither saw the other before landing):
  - research/reviewed/claude-t043-build-plan-2026-07-13.md
  - research/reviewed/deepseek-t043-build-plan-2026-07-13.md (verbatim, deepseek-v4-pro)
Governs the build of: T043 (rides docs/packet-spec-v1-2026-07.md, LAW)
Method: M1 fenced dual design; this is the reconciliation both halves gate against.

## CONVERGED (independent agreement → high confidence, build as-is)

- **Module layout**: NEW `core/comm/packet_spec.py` holds the pure schema/integrity/frag
  functions (spec R6); `bus.py` wires them into `_emit` (send) and `_drain`/`_to_msg`
  (consume); `expectations._replies_since` reuses the SAME validator; `deepseek_chat.py`
  gates tool args. Both halves drew this exact map.
- **Pin 9 (RB-29)**: EXACT independent match — filter `_replies_since` through
  `packet_spec.verify_integrity` and skip corrupt entries, so a dropped corrupt reply is
  invisible to the sweep's raw path and clears no expectation. One validator, both consume
  paths. No dropped-id side-set. (Convergence here is the strongest confidence signal in the
  slice — two blind designers, one fix.)
- **Pin 8 (tool bridge)**: MTU gate inside the tool-dispatch loop in `deepseek_chat.py`
  (~line 853–860), AFTER `args = json.loads(...)`, BEFORE `toolbox.execute(...)`; oversize
  serialized args → return a REFUSED tool result (the text the model sees), never a clip.
- **len/sha hashes the LITERAL stream strings** (content/meta/parts already json-serialized),
  not re-parsed objects — so consume reads the exact bytes back and agrees byte-for-byte.
- **Frag state**: per-consumer, in-memory, held on the Bus instance.

## DIVERGED → RESOLVED

### R-1 [DEEPSEEK RIGHT — adopted] Canonical order is EXPLICIT, not `sort_keys`.
claude's half used `json.dumps(sort_keys=True)`. deepseek flagged: the spec names
"canonical order (frm,to,kind,content,ts,meta,parts)"; `sort_keys` reorders to alphabetical
(content,frm,kind,meta,parts,to,ts), which is self-consistent for ONE implementation but
disagrees with any independent verifier following the spec's stated order (a future consumer,
a language port, an OTLP exporter). **RESOLUTION: build the dict in explicit roster order,
`sort_keys=False`** (Python 3.7+ preserves insertion order; json honors it). FIXED in
packet_spec.canonical_bytes. This is the fence's headline catch — a silent interop landmine.

### R-2 [claude — pinned, both must match] `ensure_ascii=False`.
Spec is silent on ASCII escaping. deepseek's snippet omitted it (default True → \uXXXX
escapes); claude used `ensure_ascii=False` (raw UTF-8, matches `.encode("utf-8")`).
**RESOLUTION: `ensure_ascii=False` is canonical** (the wire is UTF-8; escaping is redundant).
Pinned here so a port matches; both doors already use the one function so we are internally
safe regardless.

### GATE RESOLUTION (deepseek verify: RED r1 → RED r2 → **GATE GREEN r3**)
Three adversarial rounds. r1: 2 real defects (kill-switch not loud; reassembly restart silent-loss).
r2: defect-1 fix accepted; found a double-delivery edge in the defect-2 fix (all-pieces slot could
resurrect since _done is lost on restart). r3: rehydrate now skips+cleans all-pieces slots → GATE GREEN
("invariant holds by construction, no residual hole, no new vulnerability"). Record:
research/reviewed/deepseek-t043-verify-gate-2026-07-13.md. 13/13 pins + 70/70 regression.
Record: research/reviewed/deepseek-t043-verify-gate-2026-07-13.md (verbatim).
- **Defect 1 [FIXED]** kill-switch was not LOUD: `_drain` delivered under PACKET_INTEGRITY_ENABLED=
  False with no warning. Fixed: `_integrity_degraded_warn` (rate-limited 60s) emits a LOUD stderr +
  `packet_integrity_degraded` event whenever a drain delivers unverified. Pin 4 strengthened to assert it.
- **Defect 2 [FIXED — deepseek was right, R-3 revised in his favor]** in-memory reassembly lost a
  partial on restart SILENTLY (no timeout event), and expectation-redrive doesn't cover broadcasts/
  one-way sends. Fixed: the Reassembler is now CRASH-DURABLE — each in-flight slot mirrors to a Redis
  hash `<ns>:reasm:<agent>` and rehydrates at Bus construction, so a restart still fires the LOUD
  timeout. Kept advance-and-buffer (no HOL block, no RB-21 Lua change) — so this is the SYNTHESIS of
  both halves: my cursor discipline + his durability requirement. New pin
  test_frag_reassembly_survives_restart_loud_timeout proves it.

### R-3 [SUPERSEDED by the GATE RESOLUTION above — durability now built] Frag/cursor: ADVANCE-and-buffer, do NOT hold the cursor, do NOT touch the RB-21 Lua.
deepseek proposed HOLDING the shared cursor before an incomplete fragment (break the drain
loop; re-read next drain; modify the guarded Lua to XACK a list) — crash-safe but (a) head-of-
line-blocks the ENTIRE shared work lane behind one missing fragment for up to TTL (300s), hurting
every OTHER sender's mail, and (b) rewrites the RB-21 generation-fenced cursor Lua, which is
load-bearing safety code certified across the RB-25 storm drills. It also assumes Redis
consumer-groups/XACK; the actual `_drain` uses per-agent XREAD + a stored cursor hash (no
groups), so that specific mechanism does not fit.
**RESOLUTION (claude, reasoned):** advance the cursor normally and buffer fragments in an
in-memory per-consumer `Reassembler`; emit the whole when the last seq completes; a drain-time
`sweep_expired` fires the LOUD `fragment_timeout` (missing seq NAMED) at TTL. Decisive reasons:
(1) do NOT destabilize the certified RB-21 fencing Lua for a riding build; (2) do NOT HOL-block
the shared lane on one sender's loss; (3) fragments are RARE (oversize only) and in the common
case all N arrive contiguously in ONE batch → complete immediately, no hold.
**KNOWN v1 LIMITATION (honesty doctrine):** a consumer restart in the ~ms window between
receiving a partial set and completing it loses the in-memory partial WITHOUT a timeout event
(the frags already passed the cursor). Mitigated: work-lane frags carry the sender's L4
expectation (redrives loud); the whole is content-addressed + idempotently re-sendable. The v2
upgrade is a Redis-backed reasm hash (survives restart) — deferred, NOT built now. **deepseek:
challenge this at verify if the restart-gap is unacceptable for v1.**

### R-4 [claude — kept] Whole-integrity on reassembly + content-addressed whole_id.
Each fragment carries the WHOLE's len+sha (as whole_len/whole_sha in the frag dict), and
reassembly re-verifies the recombined content against them; whole_id = whole_sha[:32]
(content-addressed → idempotent re-send + dedup for free). deepseek's frag was {seq,of,
whole_id=random} with no post-reassembly whole check. Kept claude's: it closes the "each
fragment individually valid but reassembly logic buggy" hole.

### R-5 [claude — kept] MTU bounds the CANONICAL len (unified number).
deepseek measured total-envelope bytes (incl. v/len/sha/frag control overhead); claude bounds
the canonical `len` (the 7 content fields incl. meta+parts). **RESOLUTION: bound canonical len**
— one honest number that is BOTH "too big?" and "arrived whole?", and it is the number pin 2's
"planted len=1000" refers to. Control-field overhead (~150B) is not message payload.

## SPEC-COMPLIANCE NOTE (both halves flagged; sequencing ruling)
Amend E (trace spot-check: every 1000th trace packet gets len+sha even when
PACKET_INTEGRITY_TRACE is off) and R5 (len+sha REQUIRED on work/sig/test-*, DIAL-OPTIONAL on
trace) are LANE-SPECIFIC. Lanes are T039 (designed after T040, not yet built) — today the bus
is a single stream with no lane router. Per R8-style sequencing, lane-specific integrity policy
CANNOT be built before lanes exist. **T043 stamps integrity on ALL packets** (satisfies
"required on work/sig/test-*" by superset; trace-exemption + the 1000th spot-check activate
with the T039 lane cutover). deepseek concurs ("always include them, cheap; not required for
the 10 pins"). Recorded so T039 inherits the obligation.

## ADOPTED FROM DEEPSEEK BEYOND THE PINS
- Explicit frag seq validation: duplicate seq or seq≥of → treat as corrupt/orphan, drop LOUD
  (his F note). Folded into Reassembler.add.

## BUILD ORDER (this reconciliation = acceptance; the 10 pins pre-registered in the LAW spec)
1. packet_spec.py: canonical (R-1/R-2 fixed) + len/sha + verify + MTU [done] → + fragment + Reassembler.
2. bus.py `_emit`: stamp + MTU refuse-loud (or fragment if allow_frag).
3. bus.py `_drain`/`_to_msg`: verify_integrity → DROP+event on mismatch; Reassembler; unknown-key passthrough (pin 10).
4. expectations.py `_replies_since`: verify filter (pin 9).
5. deepseek_chat.py: tool-arg MTU gate (pin 8).
6. tests/test_packet_send_door.py: the 10 pins + the 3-receipt replay drill.
7. Green pins → deepseek VERIFY (GATE) → review-gate → commit + ledger done.
