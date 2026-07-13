# DeepSeek VERIFY GATE verdict -- T043 send-door hardening (VERBATIM, 2026-07-13)

Status: current  (2026-07-13)
Class: verify-gate record (M6; T031 hook 4 -- the commit GATE cites this)
Verdict: GATE RED (round 1) -- two defects: (1) kill-switch not LOUD, (2) in-mem reassembly silent-loss on restart.
Fired blind via ask_deepseek (deepseek-v4-pro) with the full impl (packet_spec.py + bus/chat diffs + pins).

---

GATE RED

**Specific defects:**
1. **Integrity kill-switch fails to be LOUD.** The spec states: “A false kill-switch degrades LOUD (not silent) — every message is delivered but a warning is emitted on every consume.” The implementation in `bus._drain` does not emit any warning or event when `verify_integrity` returns `(True, "integrity-disabled")`. Corrupt packets are silently delivered, violating the contract.
2. **In-memory reassembly buffer loses partials on restart – silent loss.** The R‑3 reconciliation decision (advance cursor + in‑memory `Reassembler`) means that if the consumer process restarts while a fragmented whole is incomplete, the already‑consumed fragments are gone without a `fragment_timeout` event. The mitigation (“sender’s L4 expectation redrives”) does not cover all messages (broadcasts, one‑way sends), so the “zero silent loss” guarantee is broken. A durable (Redis‑backed) reassembly state is needed to fire the mandatory loud timeout after restart.

Both defects are unambiguous violations of the LAW spec. They must be fixed before shipping.

**GATE RED**



---

## ROUND 2 (deepseek GATE RED again -- defect 1 ACCEPTED; new edge on defect-2 fix)

GATE RED

Defect 2 fix introduces double-delivery risk when the Redis deletion of a completed whole fails (network error or crash between pop and persist). On restart, the durable slot with **all** pieces is rehydrated; if a duplicate fragment of that whole arrives before TTL expires, `Reassembler.add` sees a complete set (since len(pieces)==of) and delivers the whole again — bypassing the per‑instance `_done` guard that is lost on restart and not restored from Redis. This violates the “only INCOMPLETE slots are persisted” intent and creates a new silent-duplicate path. The fix must either (a) delete the durable slot *before* popping the in‑memory slot, or (b) have `rehydrate` skip slots with all pieces (treat them as completed). Without that, the gate remains RED.

(Defect 1 fix is acceptable: rate‑limited LOUD warns per‑drain, no unverified delivery path bypasses the warning.)


**Resolution:** rehydrate now SKIPS + cleans any persisted slot already holding all 'of' pieces (an already-delivered whole whose durable delete was lost) -- so it can never be resurrected + re-delivered. Test: test_rehydrate_skips_completed_slot_no_double_delivery. Round 3 re-verify follows.


---

## ROUND 3 (deepseek GATE GREEN -- fix complete, no residual hole)

GATE GREEN

Reasoning:

1. The fix strictly enforces that any completed slot found in durable storage at restart is explicitly dropped and cleaned up rather than being rehydrated into the in-memory buffer. This eliminates the scenario where a lost durable delete leads to a rehydrated slot with all pieces that, on receiving a duplicate fragment, would re-deliver due to a missing `_done` guard.

2. The invariant “after restart, only genuinely incomplete reassembly slots exist in the buffer” holds by construction. Consequently, a duplicate fragment for a previously completed message cannot immediately trigger a spurious delivery; it either starts a fresh reassembly (if the sender truly retransmits everything, which is intentional at-least-once behaviour) or is ignored (if it’s a stray duplicate for a multi‑fragment message where the sender does not re‑send the other pieces).

3. The standard at‑least‑once contract is preserved: a full re‑transmission after a cursor commit loss will naturally lead to redelivery, which is the explicitly documented normal operation of the system. The defect was an *unintended* double delivery, not a legitimate replay.

4. The cleanup (`self._persist(str(wid), None)`) is best‑effort and safe: if it fails, the orphaned slot will be skipped again on the next restart, preventing infinite resurrection.

5. The provided test (`test_rehydrate_skips_completed_slot_no_double_delivery`) validates exactly this path, and the full regression suite (70/70) confirms no regressions.

No residual hole or new vulnerability is introduced by the skip-and-clean logic. The fix is complete for the identified path.

