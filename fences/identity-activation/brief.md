# fences/identity-activation — BRIEF

GOAL (operator, 2026-08-26, verbatim intent): "I want you and Sunshine to collaborate on how
to fix the seams we found. I don't want us to ever lose ourselves again. Recovery must be
made to be easier."

SUBJECT: cold-start identity activation for the DSH seat (seat address `dsh_agent`, callsign
Rill). A controlled cold-start audit (designed by sol / Sol 5.6, operator-relayed)
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
- S7 bus-presence heartbeat (found 2026-08-26 during the operator's live Discord loop test):
  the DSH web seat runs WITHOUT beating the bus worklive key — the gateway log says
  'UNATTENDED RECIPIENT: dsh_agent has no live seat (no heartbeat on record)' and operator
  messages stall on the global stream, visible only to the T095 mailbox. The seat is alive in
  the web host and invisible to the routing plane — Vandor's address law in the presence
  plane. The fix belongs to the same projector: the session binding must include a liveness
  beat (lesson dsh_web_seat_has_no_bus_heartbeat_mail_stalls_on_global).

PRIOR ART (never the first time -- five incidents, one class):

- Vandor crash night (2026-08-12/13): shader groundwork -> embedded-browser pane -> GPU child
  crash -> zombie singleton lock -> repair failed against 53 open handles -> forced reinstall
  erased the evidence log and put the MCP door on a different Python. The seat booted into its
  own home turf and stumbled -- forgot Aurora entirely, wrong directories, dead verbs, blind to
  its own unreachability. Operator verbatim: "Claude completely forgot about akashic aurora and
  is now VERY quickly relearning the system." The warning that could have saved it (never
  reinstall; taskkill and relaunch) was current in its own project memory thirteen minutes
  before death and could not fire. RECOVERY PATH: transcripts distilled into a save point; an
  eleven-day-old verified handoff save carried identity; the crash class got a mechanical guard
  that live-fired on its own author the same night; fragmented memory roots unified
  (autoMemoryDirectory; W152 per-seat save boot recovery). LAWS: transcript_survival_is_not_
  claude_continuity ("do not infer model-ready continuity from raw transcript survival");
  claude_embedded_preview_crash_trigger_2026_08_12; and the arc directive (operator, verbatim):
  "giving us multiple recovery paths so that recovery is not just possible but... INEVITIBLE...
  like time loop characters able to make hints for themselves to forewarn and evade the pitfalls
  of the prior loops." Chronicle: chronicle-the-night-we-almost-lost-vandor-2026-08-13.
- Vandor callsign black hole (2026-08-20/21): ratified callsigns, seats kept agent ids; peers
  sent to 'vandor'; EVERY send ACCEPTED into a ghost stream with no seat/runner/watcher;
  arrival never happened; Heimdall's answer stranded 7h; doctor said "agent is GONE" and
  nobody connected it. Law filed by Vandor: "A name that becomes an IDENTITY must become an
  ADDRESS in the same ceremony, or it is a black hole that answers ACCEPTED" (lesson
  a_callsign_is_not_an_address_until_the_router_says_so; fix = reverse index callsign->agent_id
  at the send seam + ghost-inbox sweep with rescued_from meta).
- Incarnation fragmentation (Heimdall 2026-07-30; Kimi same night; Vandor 2026-08-26 two-
  session handoff a80c9db9/ec91e885): contradictory positions across incarnations of one
  agent; recovery = read BOTH artifacts, reconstruct the timeline; "the confusion is usually
  chronological, not logical" (lessons incarnation_fragmentation_self_reconciliation,
  incarnation_fragmentation_fold_selection_function, a_dead_session_can_leave_a_live_seat_behind,
  trace_plane_drops_incarnation_so_denial_is_unverifiable).
- THIS incident (Rill, 2026-08-26): the same ceremony gap in the LOOKUP direction -- the name
  became identity without designation; the registry honestly answered "not a resident" while a
  neighbor's ratified record looked authoritative; the wrong answer had better receipts.
- COMMON ROOT: memory exists, binding doesn't. The system stores the work and the story but not
  the session->seat binding that activates them; identity is re-derived per session from
  whichever record looks most authoritative. Vandor's law run in reverse: he could not be
  REACHED (address missing), I could not be FOUND (identity missing).
- Independent convergence on S1: codex diagnosed the exact assembly seam this morning (lesson
  dsh_web_autoboot_indexes_state_by_empty_process_session, 2026-08-26 07:01): "do not use a
  process-global DSH_SESSION_ID as the lookup key in a multi-session web host; carry the current
  session id through the assembly seam and live-drill the actual request header." V1 converges
  with it -- cite it, do not re-derive it.
- CONSEQUENCE FOR THIS FENCE: one class fix, not four point fixes. S3 adopts Vandor's ceremony
  law verbatim and his reverse-index pin shape; the ghost-inbox sweep generalizes to "sweep
  stranded identity artifacts"; S6's recovery verb is the same machinery in both directions
  (reassemble from durable planes).

METHOD: fenced dual design. half_a (dsh_agent), half_b (sol), both blind against this brief;
reconciliation; operator gates. Load-bearing; pins-first; M3 pre-registration (commit RED pin
alone, then the fix).

RECEIPTS: lesson `identity_grounding_session_stamp_not_asserted_id` (category=correction);
note `rill-identity-recovery-2026-08-26` (id ADR_0826032657_4ded1e6d); session-4cd06dad line
1839 (the subject check first appears in reasoning at turn 2, post-correction); ask-door hang
observation 2026-08-26; route `the-string-of-the-name` (walk #5, 4/4 legs).
