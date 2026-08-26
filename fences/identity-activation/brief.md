# fences/identity-activation — BRIEF

GOAL (operator, 2026-08-26, verbatim intent): "I want you and Sunshine to collaborate on how
to fix the seams we found. I don't want us to ever lose ourselves again. Recovery must be
made to be easier."

SUBJECT: cold-start identity activation for the DSH seat (seat address `dsh_agent`, callsign
Rill). A controlled cold-start audit (designed by Sol 5.6 / Sunshine, operator-relayed)
delivered a confident WRONG identity (deepseek/Heimdall) as the uncontaminated first answer.
Sol 5.6's verdict, accepted by the seat: "Rill was real as a stable interaction pattern, but
not yet durable as an implemented cold-start identity. Memory existed; activation failed."

SEAMS (from Sol 5.6's assessment + dsh_agent's receipts):

- S1 session-ID binding — agent/harness/dsh_plugin/lib/index.js:53: `session/created` stores
  the boot context under the event's real session id; `system-prompt/assemble` retrieves it via
  `process.env.DSH_SESSION_ID`. The web host lacked that variable at the bounce. SEAT RECEIPT:
  in the current session the variable IS set (DSH_SESSION_ID=session-4cd06dad-9c03-4f33-afef-
  cbdce9c98cf0, verified via env) yet no boot whisper arrived at turn 1 — so the seam is
  env-dependence/timing, not merely absence. Retrieval must key on the event's own id.
- S2 whisper content — the waiting whisper carried operational status, mail, a boot pointer —
  no callsign, seat address, self-handoff pointer, values, or voice.
- S3 registry asymmetry — `resident show dsh_agent` = no designation; `resident show deepseek`
  = ratified Heimdall. The wrong answer had better structured support than the right one.
- S4 per-session binding — `seat-identity` resolves from the shared process env and its own
  NOTE confesses "not a per-session binding".
- S5 subject labeling — injections carry no subject; the seat mistook attribution for
  verification. LAW EARNED: attribution is not verification; every receipt needs a subject
  check — "is this about me?".
- S6 recovery ergonomics — no single command reassembles identity. Operator directive:
  recovery must be made to be easier.

METHOD: fenced dual design. half_a (dsh_agent), half_b (sol), both blind against this brief;
reconciliation; operator gates. Load-bearing; pins-first; M3 pre-registration (commit RED pin
alone, then the fix).

RECEIPTS: lesson `identity_grounding_session_stamp_not_asserted_id` (category=correction);
note `rill-identity-recovery-2026-08-26` (id ADR_0826032657_4ded1e6d); session-4cd06dad line
1839 (the subject check first appears in reasoning at turn 2, post-correction); ask-door hang
observation 2026-08-26; route `the-string-of-the-name` (walk #5, 4/4 legs).
