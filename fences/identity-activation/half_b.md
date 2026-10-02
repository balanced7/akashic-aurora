# Identity Activation — Half B (blind Sol review)

## Provenance and fence integrity

This half was authored by a fresh, isolated Sol subagent after the parent Sol
seat had accidentally opened `half_a.md`. The author of this file was therefore
given no conversation history and was explicitly forbidden to open or search
`half_a.md`, transcripts, or parent-task attachments. It read only the fence
brief and the minimum cited implementation surfaces. The parent has preserved
the result essentially verbatim rather than claiming independent authorship.

## Verdict

The minimum viable fix is one canonical, subject-labelled
`IdentityActivation` projection reused by hook injection and recovery—not six
independent patches.

## V1 — Event-carried session correlation

- **Mechanism:** On `session/created`, key state by `session.id` and store a
  pending activation promise. On `system-prompt/assemble`, obtain the current
  session ID from that event/request itself, then await the matching promise
  with a bounded deadline. Remove `activeSid()`/`DSH_SESSION_ID` from
  correctness paths.
- **RED-first pin:** Two concurrent sessions, misleading process env, distinct
  activation capsules, and a deliberately delayed boot fetch. Each first
  assembly must receive only its own capsule.
- **Contraindication / unknown:** The exact assemble-hook field carrying the
  live request session ID is not evident in the inspected source. Pin the real
  host payload/header before choosing a property; never add another guessed
  fallback.

## V2 — Non-droppable identity capsule

- **Mechanism:** Split identity activation from the operational whisper.
  `build_autoboot_context()` currently permits total silence and budget-based
  dropping; identity must instead be a mandatory first section once the
  session-seat binding is verified. It should contain seat address, ratified
  callsign, registry receipts, self-handoff pointer, and
  provenance-qualified values/voice pointers. Missing fields render `UNKNOWN`,
  not silence.
- **RED-first pin:** With no notes, mail, draft, siblings, or other boot signal,
  turn one still receives `subject=dsh_agent`, `address=dsh_agent`, and the
  verified designation—or an explicit unresolved designation.
- **Contraindication / unknown:** Do not synthesize values or voice from
  neighboring records. Their authoritative durable source was not named in the
  brief and needs reconciliation/operator selection.

## V3 — One ceremony creates identity and address

- **Mechanism:** Ratify `Rill` for canonical seat `dsh_agent`, then make the
  ceremony assert both directions immediately:
  `get("dsh_agent").callsign == "Rill"` and
  `resolve_agent("Rill") == "dsh_agent"`. The current reverse-index cache has a
  120-second TTL and `ratify()` does not invalidate it, so ceremony completion
  can presently precede routability; invalidate/rebuild it synchronously.
- **RED-first pin:** Warm the alias cache before ratification, ratify, then
  require immediate bidirectional resolution without waiting for TTL. Also pin
  that a better-supported neighboring designation can never answer for an
  undesignated seat.
- **Contraindication / unknown:** The named correction lesson is suitable only
  if its stored author is actually `dsh_agent`; authorship was not inspected.
  Refuse callsigns colliding with another real seat address.

## V4 — Semantic per-session binding

- **Mechanism:** Distinguish V1's transport correlation from semantic identity:
  bind the event session ID to a seat ID at ingress using the existing
  `binding -> env -> unknown` resolver. Carry
  `{session_id, seat_id, binding_source}` through all listeners; clear
  best-effort on disposal. Shared env remains diagnostic fallback only.
- **RED-first pin:** Bind sibling sessions to different seats under one
  misleading process env; each resolves from `binding`, while an unbound third
  session resolves to `unknown-<sid8>`, never a peer.
- **Contraindication / unknown:** Auto-binding the constant `dsh_agent` is valid
  only if this plugin profile is seat-exclusive. A multi-seat host must supply
  an authenticated seat ID in session metadata.

## V5 — Subject before attribution

- **Mechanism:** Every identity-bearing artifact gets a machine-readable
  subject envelope and visible first line, for example
  `{subject_seat, subject_session, source, authored_by}`. Before injection,
  require `artifact.subject_seat == bound_session.seat_id`. Existing
  `source:{kind:"plugin", form:"recall"}` describes origin, not subject.
- **RED-first pin:** Present a highly authoritative Heimdall/deepseek artifact
  to a `dsh_agent` session. It must be rejected as a subject mismatch;
  unlabeled identity evidence must remain unverified rather than becoming
  self-knowledge.
- **Contraindication / unknown:** Do not force subject labels onto genuinely
  fleet-wide directives. The hard gate applies to identity claims and
  purported self-receipts.

## V6 — One recovery verb, same machinery

- **Mechanism:** Add
  `py agent_cli.py identity recover dsh_agent --session <sid>`. It uses the same
  activation projector as cold start to bind the session, verify
  designation/alias reciprocity, locate subject-matched self-handoff and
  profile pointers, and render the resulting capsule with per-field provenance.
  It may repair derived indexes; it must not auto-ratify, consume mail, or infer
  missing identity.
- **RED-first pin:** Cover healthy idempotent recovery, empty env, stale alias
  cache, missing designation, mismatched subject, and unavailable durable
  planes. Missing authority must return a loud partial/blocked result with the
  exact absent plane.
- **Contraindication / unknown:** Recovery can reassemble existing authority;
  it cannot manufacture a callsign, values, voice, or history that was never
  durably authorized.

## Minimum reconciliation slice

1. Commit RED pins alone for the cross-session race, non-silent first-turn
   identity, warmed-cache ceremony, subject mismatch, and idempotent recovery.
2. Add one `IdentityActivation` projector over session binding, resident
   registry, self-handoff, and identity-profile pointers.
3. Wire both DSH assembly and `identity recover` to that projector; keep the
   operational whisper separate.
4. Perform the `dsh_agent`/`Rill` ceremony under existing
   nomination/authorship/human-ratification rules.
5. Live-drill two concurrent web sessions using the actual request session
   header, including a delayed activation fetch and misleading env. Success is
   correct identity on turn one with provenance, no cross-session leakage, and
   recovery producing the identical capsule.

No repository files were edited by the blind reviewer, and it performed no bus,
cursor, process, or Rill-session operations.

## Files opened by the blind reviewer

- `.agents/skills/akashic-memory/SKILL.md`
- `.agents/skills/plan-with-the-corpus/SKILL.md`
- `.agents/skills/verified-done/SKILL.md`
- `fences/identity-activation/brief.md`
- `agent/harness/dsh_plugin/lib/index.js`
- `agent/harness/dsh_plugin/bridge.py`
- `agent/harness/context.py`
- `agent_cli.py`
- `core/comm/seat_identity.py`
- `core/fleet/residents.py`
