"""T083 C7-1 pin: the MCP door's _ARG_DEFAULTS must cover every attribute any
delegated cmd_* reads off its Namespace.

Class of defect (sol's day-one receipt, 2026-07-17): ai_setup_mcp builds
Namespace(**{**_ARG_DEFAULTS, **overrides}) per tool call. cmd_notes read args.all
and cmd_note read args.retire; neither key was in _ARG_DEFAULTS nor in the tools'
overrides, so the MCP twins raised AttributeError while the CLI (whose argparse
always defines them) worked. Door-parity defects of this class are invisible until
an MCP-native seat trips them -- this pin makes the whole class loud at test time.

Method: static AST both sides. Collect every _run(agent_cli.cmd_foo, k=...) call in
ai_setup_mcp.py -> {cmd_foo: override_keys}. For each such cmd_foo, walk its AST in
agent_cli.py for direct `<argsparam>.<attr>` reads. Every attr must be a key of
_ARG_DEFAULTS or of that tool's overrides. getattr(args, "x", default) is exempt by
construction (it is a Call node, not an Attribute read, and cannot raise).
"""
import ast
from pathlib import Path

import ai_setup_mcp

ROOT = Path(ai_setup_mcp.__file__).resolve().parent
MCP_SRC = (ROOT / "ai_setup_mcp.py").read_text(encoding="utf-8")
CLI_SRC = (ROOT / "agent_cli.py").read_text(encoding="utf-8")


def _delegations(mcp_tree: ast.AST) -> dict:
    """{cmd_name: set(override_keys)} for every cmd_* delegation.

    Two shapes, both covered (O1 2026-07-23 moved dispatch to worker threads):
      legacy:  _run(agent_cli.cmd_foo, k=...)
      O1:      await _athread(_run, agent_cli.cmd_foo, lock=..., k=...)
    `lock` is a dispatch kwarg consumed by _athread, never a cmd override.
    """
    out = {}
    for node in ast.walk(mcp_tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not isinstance(fn, ast.Name):
            continue
        target = None
        if fn.id == "_run" and node.args:
            target = node.args[0]
        elif (fn.id == "_athread" and len(node.args) >= 2
              and isinstance(node.args[0], ast.Name) and node.args[0].id == "_run"):
            target = node.args[1]
        if isinstance(target, ast.Attribute) and target.attr.startswith("cmd_"):
            keys = {kw.arg for kw in node.keywords if kw.arg and kw.arg != "lock"}
            out.setdefault(target.attr, set()).update(keys)
    return out


def _args_attr_reads(cli_tree: ast.AST, cmd_name: str) -> set:
    """Direct attribute reads on the first positional parameter of cmd_name."""
    for node in ast.walk(cli_tree):
        if isinstance(node, ast.FunctionDef) and node.name == cmd_name:
            if not node.args.args:
                return set()
            param = node.args.args[0].arg
            return {
                sub.attr
                for sub in ast.walk(node)
                if isinstance(sub, ast.Attribute)
                and isinstance(sub.value, ast.Name)
                and sub.value.id == param
            }
    return set()


def test_regression_notes_all_and_note_retire_present():
    # The two live AttributeError receipts from sol's MCP-native seat.
    assert "all" in ai_setup_mcp._ARG_DEFAULTS
    assert "retire" in ai_setup_mcp._ARG_DEFAULTS


def test_every_delegated_cmd_attribute_is_covered():
    mcp_tree = ast.parse(MCP_SRC)
    cli_tree = ast.parse(CLI_SRC)
    delegations = _delegations(mcp_tree)
    assert delegations, "no _run(agent_cli.cmd_*) delegations found -- test wiring broke"
    defaults = set(ai_setup_mcp._ARG_DEFAULTS)
    misses = {}
    for cmd_name, overrides in sorted(delegations.items()):
        reads = _args_attr_reads(cli_tree, cmd_name)
        uncovered = reads - defaults - overrides
        if uncovered:
            misses[cmd_name] = sorted(uncovered)
    assert not misses, (
        "cmd_* attributes missing from _ARG_DEFAULTS (MCP twin would raise "
        f"AttributeError while CLI works): {misses}"
    )
