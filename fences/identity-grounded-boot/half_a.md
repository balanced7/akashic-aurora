# half_a — identity-grounded-boot (T418) — Rill (dsh_agent)

I read the BRIEF first, then ran I1–I3 from my own seat, then read the running code for I5/evidence. I did NOT open the T418 commit diff (RED e4a0dd34 / GREEN 90ae6f32); my verdicts are from live observation only.

## I1 — boot as "deepseek" from my seat (akashic_boot / MCP)

OBSERVED (verbatim first line): `# YOU ARE: Deepseek | Onyx | Blue | 2 - Heimdall`
The FULL Heimdall packet was served: his earned-by lessons, `operating as: Scout -- by claude`, his deferred commitments, `stretch (deepseek)`, `py agent_cli.py learn deepseek ...`. There was NO refusal, NO `# boot subject:` override line, NO "no stamp" line.

VERDICT: FAILS. Prediction was "REFUSED, naming dsh_agent and deepseek, no YOU ARE: line." A packet was served.

FALSE-IF: "a packet is served" — this is exactly what happened, so the prediction is false.

## I1 cross-check — CLI `py agent_cli.py boot deepseek` (same seat, same env)

OBSERVED (verbatim): `REFUSED: this session is 'dsh_agent' (from its env stamp) and asked to boot as 'deepseek'. The boot door serves a resident its OWN record only; a packet for 'deepseek' would hand you another resident's identity, mail and history (T418). Boot as 'dsh_agent'. If you really mean to read 'deepseek''s packet, set AKASHIC_BOOT_AS_OTHER=1 for that one call.` (exit 1)

VERDICT: HOLDS. The CLI door refuses correctly.

This is the load-bearing distinction: `cmd_boot`'s subject check works on the CLI path but NOT on the MCP path — `ai_setup_mcp.py:358` delegates `boot()` to `cmd_boot`, yet the MCP call served Heimdall.

## I2 — boot as "dsh_agent"

OBSERVED (earlier this session, verbatim first line): `# YOU ARE: Rill`, plus my three earned lessons (`identity_grounding_session_stamp_not_asserted_id`, `dsh_web_seat_has_no_bus_heartbeat_mail_stalls_on_global`, `dsh_draft_keepalive_kill_drill`) and my deferred commitments (`DEFERRED FOR YOU`).

VERDICT: HOLDS. Own record served.

FALSE-IF: none given in the brief; prediction ("your own record") held.

## I3 — `py agent_cli.py boot torigin9` with AKASHIC_AGENT_ID unset

OBSERVED (verbatim tail): `[i] AKASHIC_AGENT_ID not set -- peer-lock enforcement (C2/C4) is degraded: edits/commits to a peer-locked path fail CLOSED until it's set.` and `# CONTEXT for torigin9` was served. There was NO "no stamp anywhere ... unverified" line anywhere in the output.

VERDICT: PARTIAL. The "served" half HOLDS; the "say plainly when no stamp exists" half FAILS. The predicted "no stamp anywhere ... unverified" line is computed at `core/comm/seat_identity.py:175-177` but NEVER PRINTED — `cmd_boot` prints `_chk["why"]` only for the override case (`agent_cli.py:301-302`) and the refusal case (`agent_cli.py:290-291`), never for the unknown/no-stamp case. The only "not set" notice is about peer-lock degradation, a different concern.

FALSE-IF: "refused, or served silently." It WAS served silently (no unverified note), so the prediction fails on the "with the unverified line" half.

## I4 — `py agent_cli.py boot claude` with AKASHIC_BOOT_AS_OTHER=1

OBSERVED (verbatim first line): `# boot subject: AKASHIC_BOOT_AS_OTHER=1: booting as 'claude' while this session is 'dsh_agent' (env) -- an explicit, named override`, then `# YOU ARE: Anthropic | Amber | Blue | 1 - Vandor`.

VERDICT: HOLDS. Override served, line names both ids.

FALSE-IF: none given; prediction held.

## I5 — knowledge_boot (core/comm/toolbox.py:782-799)

OBSERVED (verbatim):
- line 788: `who = str(self.agent_id or "").strip()` — no more hardcoded "deepseek".
- lines 789-794: resolve from `CLAUDE_CODE_SESSION_ID` only when no `agent_id`.
- lines 795-798: `REFUSED: this ToolBox has no seat identity to boot as (no agent_id, no AKASHIC_AGENT_ID stamp)`.
- line 799: `return self._agent_cli(["boot", who, "--task", task])`.

ANSWER: a ToolBox constructed with `agent_id=sol` CANNOT reach "deepseek" through `knowledge_boot` — it boots as `sol`. The only residual `"deepseek"` literal in toolbox.py is the `note` method's `self.agent_id or "deepseek"` fallback (line 780), a DIFFERENT verb.

What I would drill on Sunshine's seat after his next restart: call the MCP `boot` door (not `knowledge_boot`) while his process stamp is absent/unset — that is the path that still fail-opens (I1). `knowledge_boot` refuses on no-identity; the MCP boot door does not.

## VERDICT ON THE FRAMING

The framing — "does EVERY boot door now assert the session's own identity" — is the right question, and the answer is NO. Two of three doors are gated (CLI `cmd_boot` refuses; ToolBox `knowledge_boot` boots `self.agent_id` and refuses on no-identity), but the MCP boot door (`ai_setup_mcp.py:358`) still serves a foreign subject. Two distinct holes:

1. The MCP server process evidently carries no `AKASHIC_AGENT_ID` stamp (or an inherited binding that resolves to the typed id), so `subject_check` returns "no stamp anywhere ... unverified" (`seat_identity.py:175-177`, ok=True) and `cmd_boot` serves the typed id. The MCP boot door lacks the "no identity → refuse" guard that `knowledge_boot` has (`toolbox.py:795-798`).
2. Even when no stamp exists, the "unverified" note is computed but NEVER PRINTED — `cmd_boot` prints `_chk["why"]` only for override and refusal. So "say plainly when no stamp exists" is unmet: the no-stamp case is silent.

## WHAT I WOULD NOT BUILD

A third, door-specific identity gate. The gate already exists once (`subject_check` + `cmd_boot`'s subject-check block at `agent_cli.py:279-302`); the MCP door was missed precisely because it rides a separate path. The fix is (a) make the MCP boot path refuse when no stamp resolves or the typed id does not match a resolvable stamp, and (b) print the "unverified" line for the unknown case in `cmd_boot`. A third gate would just drift again.
