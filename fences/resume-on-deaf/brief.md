# FENCE BRIEF — resume-on-deaf (S2, T420): the house re-opens a deaf seat

**Fence:** `resume-on-deaf` · **Tier:** lite · **Opened by:** claude (Vandor), 2026-10-01 · **Builder:** claude · **Blind half (half_a):** Heimdall (deepseek) · **Reconciler:** claude · **Live drill:** GATED on S1 (Daniel: `claude setup-token` -> `py agent_cli.py secret claude_oauth.token`)

## CHARTER

Daniel, 2026-10-01 13:37/13:40: the ladder (note wake-ideal-ladder-2026-10-01, ADR_1001140120_6751f501), property (1): "If no harness-parented listener exists for a seat that should be up, the daemon RESUMES the session headlessly (claude -p --resume <sid>, proven in 26 s on 09-02) under a long-lived token; it boots, drains, answers, re-arms. Closing the app stops being deafness."

## THE QUESTION

Does the daemon now re-open a session that its launcher declared expected-up, that has been silent past the grace, and that has no listener able to start a turn, by taking a headless `--resume` turn on the exact session under the vaulted token, with every hold named (not expected, tombstoned, reachable, no marker, grace, stale, breaker, cooldown, no credential), a receipt per attempt, and a .rearm trigger so presence returns afterwards?

## INPUTS

- `core/comm/resume_on_deaf.py`: expected-up record (declare/retract/list under state/wake-expected/), `resume_decision()` (the total table), `resume_argv()` / `resume_prompt()`, `vault_token()` / `cli_logged_in()` (the gateway's preflight shape, fail-open on unknown), `trigger_resume()` (detached launch, own log under state/spawn-logs/resume-*.log, receipt under state/wake-resumes/<agent>.jsonl), `resume_history()`, `maybe_resume()` (the daemon's one call).
- `agent_cli.py`: bifrost-standby declares expected-up before parenting the listener; stand-down retracts it.
- `scripts/bifrost_daemon.py` (--manage-listener loop): on a listener exit 0, `maybe_resume(agent, sid)`; on resume, `write_rearm_trigger` so a presence listener re-spawns; holds are said once per (sid, reason).
- Pins: `tests/test_resume_on_deaf.py` (18, hermetic: fake which/popen, records in tmp).
- Prior art: lesson exact_session_resume_actuator_proven_26s (2026-09-03); the gateway's `_spawn` lever in scripts/bifrost_runner_discord.py (credential preflight, node.exe-direct argv, spawn GRANT flags).

## RULES OF ENGAGEMENT

- Blind on the hermetic half: run the pins and read `resume_decision`'s table BEFORE the daemon wire; say which you read first.
- Do NOT run a live resume against Vandor's session bb86400e or any live seat until S1 lands: a resume turn with no credential dies in ~16 s and leaves a failed receipt that counts toward the breaker.
- Zero is not no: a hold is a named verdict; an absent record is "not expected-up", never silence.
- One document, written once, `fence write resume-on-deaf --slot half_a --file <path> --by deepseek`.

## OUTPUT CONTRACT

half_a: sections R1-R6, each OBSERVED / VERDICT (HOLDS / FAILS / UNCHECKABLE) / FALSE-IF; then VERDICT ON THE FRAMING and what you would not build; file:line for every code claim.

- R1 The expected-up record is minted by the launcher (bifrost-standby) and never by the listener; stand-down retracts it. Point at the two call sites.
- R2 The decision table is total and every hold is named; find an input combination that is not covered, or say none exists.
- R3 The credential preflight fails open on an unknown login state and refuses only on a KNOWN-bad one; the refusal names S1's two commands.
- R4 A resume writes a receipt and a .rearm trigger; a second resume inside the cooldown holds; three failed launches trip the breaker.
- R5 The headless prompt forbids arming a listener and names the operator reply path; the argv is `-p <prompt> --resume <sid>` with the arm grant, model pin first.
- R6 What this does not claim: the live loop (daemon listener detects mail -> resume turn answers -> daemon listener re-spawns) is UNDRILLED until S1; name what else you would drill the day the token lands (window closed, box rebooted, two deaf sessions of one agent, a resume that itself goes deaf).

## 5. Acceptance (pre-registered)

Pins GREEN after RED; R1-R5 observed by Heimdall; the live drill (close the desktop window, send one directed message from your seat, receive a reply on the work lane within 5 min, daemon log shows RESUME-ON-DEAF then a re-spawned listener) is a SEPARATE dated receipt once S1 lands and is not claimed here.
