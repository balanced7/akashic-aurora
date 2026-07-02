# Cursor hook payload fixtures (pinned ground truth)

Empty until composer pins them (Integration Tiers H2 handoff). The cursor_*.py adapters
capture every live payload -- truncated, bounded -- into
`%TEMP%/akashic_recall/payloads_cursor/` (kill switch `AKASHIC_PAYLOAD_CAPTURE=0`).

To pin: run a Cursor session with the hooks wired (`.cursor/hooks.json`), exercise a
shell command + a file write + one deliberate failure, then copy the interesting
captures here named by event, e.g.:

    sessionstart.json
    beforeshell_git_add.json
    pretooluse_shell.json
    posttooluse_shell_success.json
    posttoolusefailure_shell.json
    sessionend.json

`tests/test_cursor_hook_contract.py` un-skips itself as soon as .json files exist here
and pins the adapters' assumptions (field names, event routing, output shapes) to what
Cursor ACTUALLY sends -- the same payload-truth discipline as tests/fixtures/claude_payloads/.
If Cursor changes shape: re-capture, diff, update fixtures AND adapters together.
