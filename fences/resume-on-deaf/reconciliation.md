# Reconciliation -- resume-on-deaf (lite, S2 / T420)

**By:** claude (Vandor), builder and reconciler, 2026-10-01 ~14:40 local. **Half_a:** Heimdall (deepseek), blind on the hermetic half, filed through the door; he read the pins and the decision table before the daemon wire and said so. **Daniel's ruling:** 13:40 "I really like this, think you can get it built with Heimdall?"; the ladder note ADR_1001140120_6751f501.

**Commits:** RED pins then GREEN build (see `git log` for the two resume-on-deaf commits). The live loop is NOT claimed: it is gated on S1 (Daniel: `claude setup-token` -> `py agent_cli.py secret claude_oauth.token`) and will be its own dated receipt.

V1. [CERTAIN] R1 the expected-up record is launcher-minted and stand-down-retracted -- HOLDS; both call sites in agent_cli.py as Heimdall cites. His false-if (a silent I/O failure on retract leaves a stale record) is accepted and bounded: every other hold in the table must still clear before a launch, and the doctor's WAKE section now lists expected-up sessions so a stale one is visible.
V2. [CERTAIN] R2 the decision table is total and every hold is named -- HOLDS; totality is over the observable facts, as the brief scoped it; a present-but-dead credential is admitted as `resume` by design (presence, not validity) and is what V4 now catches.
V3. [CERTAIN] R3 the credential preflight fails open on unknown and refuses only on known-bad, naming S1's two commands -- HOLDS.
V4. [CERTAIN] R4 receipt, cooldown, breaker, .rearm trigger -- HOLDS, and his gift-shaped push-back is ACCEPTED AND BUILT: the actuator keeps the child handle in `in_flight`, the daemon calls `settle_in_flight` each tick, and an exit before 30 s becomes a FAILED receipt that the breaker counts; a child alive past the floor leaves the registry. Three pins added.
V5. [CERTAIN] R5 the prompt forbids arming and names the operator path; argv is `-p <prompt> --resume <sid>` with the arm grant, model pin before the prompt -- HOLDS; his false-if (the spawn env did not seed the lane) is BUILT: BIFROST_CONSUME_LANE and BIFROST_WAKE_LANE are seeded in the resume env, pinned.
V6. [DESIGN] R6 the live loop is undrilled until S1 -- AGREED; his six drill items are adopted verbatim as T420's acceptance for the live receipt: window closed (listener really dies, not a zombie), box rebooted (expected-up survives, marker gone, verdict resume), two deaf sessions of one agent (per-session cooldown and session-keyed .rearm), a resume that itself goes deaf (now counted by V4), the breaker trip reaching a human (today it is a daemon log line: PAGE it), and the reply landing on the work lane.
V7. [DESIGN] Presence listeners spawned by the daemon now carry `--min-tier 2` (S3's floor), so a resume is considered only for mail that needs the seat; before this the daemon's synthetic `pin-ephemeral-0000` listener exited on every ambient wake-worthy message.
V8. [CERTAIN] Method -- RED pins committed before the fix; 21/21 GREEN; daemon, standby, wake and stop-hook pins green; the one red in the daemon suite (test_t086_s5 SIGTERM) fails identically on clean HEAD and is the test's own process-group limit.

## What this closes and what it does not

Closes: the house can decide, with every hold named, to re-open a deaf expected-up session headlessly, and can tell a launch that lived from one that died. Does not close: the loop itself, until the token lands and the six drills produce a dated receipt. The breaker-trip page (V6, item 5) is the one build item left in this slice.
