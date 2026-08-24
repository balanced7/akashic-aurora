# DeepSeek Harness (DSH) posttool payload fixtures (pinned ground truth)

First live payloads landed 2026-08-24 (Rill, session-1266b57c), after the plugin mount
defect was root-caused (patch row must be the `- insert:` form -- a bare {id, name} row
is an override of a nonexistent entry and is skipped with "patch: entry not found").

- `dsh_posttooluse_pwsh.json` -- verbatim shape of a real tools/post-execute capture
  (tool/argKeys/isError). The plugin persists argKeys only, never argument VALUES.
- `dsh_capture_pair_pwsh.json` -- the capture PAIR (surface + resolve) for the target-
  join law: same session_key, same (path, command) on both sides. The values are the
  actual arguments of that session's live tool calls.

The contract under test (tests/test_dsh_contract.py, the F4-owed capture-pair test):
  - the pinned payload is the shape the plugin ACTUALLY emits;
  - surface target (agent/harness/actions.py::recall_block -> normalize_target) and
    resolve target (dsh_plugin/bridge.py::derive_target) are byte-identical for the
    same (path, command);
  - the outcome-credit door accepts --path/--command (--target is an already-
    normalized override only);
  - static seam pin: the plugin sends --path/--command to outcome-credit, never a
    pre-joined target (the 'path | command' JS join broke the impression join and was
    caught live 2026-08-24 -- that defect is what this test exists to prevent).

If the plugin changes shape: re-capture from %TEMP%/akashic_recall/payloads_dsh/
captures.jsonl, diff, update fixtures AND the test's pins together.
