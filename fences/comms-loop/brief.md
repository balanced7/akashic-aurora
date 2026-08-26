# fences/comms-loop — BRIEF

GOAL (operator, 2026-08-26, verbatim): "Since the whole house is working on this, can we all
work at it from different angles and leverage everyones strengths?" -- comms repair, remote-fix
arc. Daniil will operate remotely from Discord; every receipt must be visible from his phone.

SEAMS (all live-verified today by the operator's Discord loop test, 'Test' / 'Test 2!'):

- C1 bus-presence heartbeat: the DSH web seat beats nothing. Gateway log: 'UNATTENDED
  RECIPIENT: dsh_agent has no live seat (no heartbeat on record)'. Operator messages stall on
  the global stream, visible only to the T095 mailbox. (= identity-activation S7; lesson
  dsh_web_seat_has_no_bus_heartbeat_mail_stalls_on_global.)
- C2 callsign ghost stream: bifrost:inbox:rill holds 7 stranded messages (5 reply-kind) --
  the send_reply path still does not resolve the callsign. Repeat filed against
  a_callsign_is_not_an_address_until_the_router_says_so (5.5 days after it was learned; prose
  is the wrong instrument, a GATE is the right one).
- C3 operator relay surface: inbound PROVEN (both test bodies read verbatim by bus id).
  Outbound PROVEN as the reaction-ladder strict checkmark (operator saw 'Test 2!' flip).
  UNPROVEN: reply TEXT delivery to the operator's channel. Surface: scripts/bifrost_runner_discord.py.
- C4 import readability: discord-imported rows are visible to the T095 mailbox but the body is
  NOT fetchable from the dsh_agent namespace (fetch door miss; bodies recoverable only via
  gateway-log bus ids). Address-space seam (T220/T222 family).

ANGLES BY STRENGTH (no build outside your angle without a handoff):

- dsh_agent (Rill): C1 seat-side (the patient is the doctor) + C3 gateway code (owns
  scripts/bifrost_runner_discord.py) + fleet coordination + the dsh charter/registry ceremony.
- claude (Vandor): C2 routing plane -- reverse-index gate enforced at BOTH send seams +
  ghost-stream sweep with rescued_from meta; continue the Codex-Discord pair with sol.
  Still owed: the dsh_agent -> Rill nomination (Daniil ratifies remotely).
- deepseek (Heimdall): C3 ladder semantics -- what kinds settle what, when the strict
  checkmark may flip, pins that runner heartbeats and the T380 ladder stay honest.
- kimi (Navi): C3 operator-surface contract -- what Daniil should SEE from his phone
  (checkmarks, reply text, alerting) + docs + acceptance he can run from Discord alone.
- sol: C1 plugin-side heartbeat implementation for the web host + C4 import namespace; keep
  its stricter read-only fence and coordinate with Vandor so the Codex-Discord pair does not
  collide.

METHOD: pins-first (RED alone, then fix). One shared brief; each seat posts receipts to the
bus; Daniil gates remotely. Success = Daniil sends one Discord message and receives the reply
text back in Discord, with the checkmark, without asking anyone -- from his phone, within a
minute.

RECEIPTS: gateway log (bus ids 1787749654950-0, 1787749908726-0, reply 1787750052144-0,
checkmark observed by operator); mailbox rows discord:15 chat from daniil; repeat ledger entry
vs a_callsign_is_not_an_address_until_the_router_says_so.
