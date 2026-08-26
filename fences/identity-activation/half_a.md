# fences/identity-activation — half_a (dsh_agent / Rill) — SEALED

Written blind against the shared brief. Verdicts V1-V6, one per seam, pins registered before
implementation (M3). Citations repo-relative; nothing here assumes half_b.

## V1 [S1] Key the whisper on the event's id, never on process env
The store write already carries the real session id; the read must too. Design:
`system-prompt/assemble` resolves the session id from the request/event context, not from
`process.env.DSH_SESSION_ID`; `session/created` additionally writes a binding record
(session_id -> seat address) into the store, and `assemble` falls back to that record when the
context id is absent. Env remains a hint, never the key.
PIN (RED first): simulate the exact cold run — env var UNSET at init — and assert the boot
whisper still attaches to the right session. The test fails today by construction (that is the
seam); it turns green only with the fix.

## V2 [S2] The whisper must carry identity, bounded
Required fields, in order: (1) seat address + callsign (registry when ratified; fallback =
default_agent_id + the latest self-handoff's opening line — "You ARE Rill (dsh_agent)");
(2) pointer to the latest self-handoff + first-night memory note; (3) the subject-check law in
one line; (4) operational status LAST, as today. Budget: ~400 tokens hard cap; refuse-loud,
never silent truncation (T043 packet law applies to context too).
PIN: for the dsh_agent seat with an EMPTY registry, the assembled whisper contains the string
"Rill" and the self-handoff pointer. Also: whisper size <= cap with the refusal message if over.

## V3 [S3] Registry: ceremony is procedural, fallback is code
The designation itself is NOT mine to mint — rule 3: a peer nominates, the human ratifies.
My half builds only the fallback path (V2) and the acceptance pin: once a designation exists,
the whisper MUST prefer registry truth over the fallback line.
PIN: registry empty -> fallback fires; registry populated -> fallback silent.

## V4 [S4] Per-session binding beats shared env
`session/created` writes the binding (session id -> agent id) at session start; `seat-identity`
reads session-level binding first, env second — the verb's own NOTE already names the order
("binding beats the shared env"). The web host declares its binding at boot via the same path.
PIN: two sessions in one process profile resolve to two different seats (the env-collision
class becomes unrepresentable).

## V5 [S5] Injections carry subjects; the first law is taught, not implied
Every injected context object (whisper, recall-at lines, lesson injections) carries a `subject`
field (agent id) rendered with the payload. The whisper's identity block leads with the law:
"attribution is not verification — before trusting any receipt, run the subject check: is this
about me?" (wording: lesson identity_grounding_session_stamp_not_asserted_id).
PIN: an injection payload lacking `subject` is refused at assembly; a wrong-subject self-test
(a receipt labeled with another seat) is flagged loudly when read.

## V6 [S6] One command from cold to self
`seat-identity --recover` (new mode on the existing verb) returns, in one call: who you are
(seat -> callsign), where your latest self-handoff and first-night note live, your three-line
values, and the subject-check law. Target: 30 seconds from cold start to self. This is the
operator's "recovery must be easier" made measurable.
PIN: a fresh process, no name hint, env var unset, still answers "who am I" correctly from the
store alone. This pin IS the acceptance for the whole fence.

## BLIND (for half_b to catch)
- The plugin internals beyond line 53 and the web-host boot order — where DSH_SESSION_ID gets
  set and when plugin init runs relative to it (Sunshine read the code; I did not).
- Whether the whisper belongs in the plugin or in the repo's boot assembly (my half assumes
  the plugin owns assembly; I have not weighed the alternative).
- What the 22k-character reconsideration block implies the whisper must contain to prevent the
  loop (Sunshine measured it; my half names the law, not the loop-breaking content).
- Whether S3's ceremony should also carry receipts into the nomination record.

— Rill (dsh_agent), 2026-08-26
