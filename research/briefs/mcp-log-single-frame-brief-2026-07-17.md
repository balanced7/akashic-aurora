# MCP `log` Single-Frame Repair — M1-LITE Brief

Status: active diagnostic repair slice, 2026-07-17
Owner: `codex_root`
Review seat: `deepseek-review`

## CHARTER

Make the native MCP `log` tool return on its own request frame under the default
keyword-theme configuration, without changing CLI output, narrative semantics, or
the opt-in embedding-theme path. This is an experiment-support repair discovered
while checkpointing the T060 three-frontier panel.

## INPUTS

- `ai_setup_mcp.py::_run` and `ai_setup_mcp.py::log`
- `agent_cli.py::cmd_log`
- `core/narrative/beat_log.py::_assign_themes`
- `core/narrative/theme_discovery.py`
- `core/narrative/theme_assigner.py`
- `tests/test_t078_w3_mcp_door.py` (transport pattern only; do not edit because a
  separate C7-4 slice is uncommitted there)
- `docs/method-baseline-2026-07.md` M1-LITE, M3, and M4

Observed receipts:

1. Attached native `log` did not return in 60 seconds and was terminated; no event
   was written. The equivalent CLI completed in 0.9 seconds.
2. A new stdio MCP process timed out on `log` after five seconds. Sending a second
   inbound tool frame released the first response, reproducing the C7-class symptom.
3. A faulthandler dump at three seconds placed the server event-loop thread at
   `beat_log.py::_assign_themes` importing `theme_discovery.py`, which eagerly imports
   NumPy at module load even though `AKASHIC_EMBED_THEMES` is off by default.
4. Calling the same MCP wrapper directly, including from a worker thread, completed
   in about one second. The cold import on FastMCP's synchronous event-loop path is
   the discriminating mechanism; Redis and `cmd_log` output are exonerated.

## RULES OF ENGAGEMENT

- Pre-register and observe a RED pin before implementation.
- Fix the default cold-import root cause in `beat_log.py`; do not add sleeps,
  second-frame probes, broad subprocess wrappers, or timing-only retries.
- Preserve opt-in embedding themes byte-for-byte in behavior: only the default/off
  selection bypasses importing the heavy discovery module.
- Use a new isolated test file so the in-flight C7-4 boot slice is untouched.
- Run targeted pins, the narrative regression set, and the real stdio log drill.
- File a peer countercheck before claiming the slice verified.

## THE QUESTION

Can default keyword theming be selected without importing the opt-in embedding stack,
so a fresh native MCP `log` call completes on one frame while CLI and explicit
`AKASHIC_EMBED_THEMES=1` behavior remain unchanged?

## OUTPUT CONTRACT

- Code: `core/narrative/beat_log.py`
- Preregistered pins: `tests/test_mcp_log_single_frame.py`
- Required RED evidence:
  - default/off `_assign_themes` attempts to import `theme_discovery` before the fix;
  - fresh stdio `log` either misses the single-frame latency bar or is accompanied by
    the deterministic import-attempt failure (cache warmth must not hide the class).
- Required GREEN evidence:
  1. default/off path never imports `core.narrative.theme_discovery`;
  2. opt-in path still delegates to `select_theme_assigner`;
  3. fresh real stdio MCP `log` returns useful output from one request in <5 seconds;
  4. existing narrative/log and MCP-door target tests remain green.
- Review: `research/reviewed/mcp-log-single-frame-deepseek-review-2026-07-17.md`
- No commit or “fixed” claim until peer review and fresh verification.

