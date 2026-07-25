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

# Deliberately NOT `import ai_setup_mcp`. This pin is static AST analysis of two source
# files (see the docstring) and never touches the live module -- the import existed only to
# locate the repo root. But importing it pulls in `mcp`, which needs `anyio`, and neither is
# in requirements.txt because the MCP door is optional. So on any machine without the
# optional extras -- including CI -- this module failed at COLLECTION, which aborts the whole
# pytest run before a single test executes. A static-analysis pin must not depend on the
# runtime it analyses.
ROOT = Path(__file__).resolve().parents[1]


def _arg_defaults_keys(src: str) -> set:
    """The keys of ai_setup_mcp's module-level `_ARG_DEFAULTS = dict(...)`, read statically.

    Read from the AST rather than the imported module so this pin keeps working without the
    optional MCP extras. Fails LOUD if the assignment moves or changes shape -- an empty set
    here would silently pass every assertion below, which is the failure mode this file
    exists to prevent in the door itself.
    """
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "_ARG_DEFAULTS" for t in node.targets
        ):
            call = node.value
            if isinstance(call, ast.Call):
                keys = {kw.arg for kw in call.keywords if kw.arg}
                keys |= {
                    k.value for a in call.args if isinstance(a, ast.Dict)
                    for k in a.keys if isinstance(k, ast.Constant)
                }
                if keys:
                    return keys
            if isinstance(call, ast.Dict):
                keys = {k.value for k in call.keys if isinstance(k, ast.Constant)}
                if keys:
                    return keys
    raise AssertionError(
        "could not read _ARG_DEFAULTS statically from ai_setup_mcp.py -- the assignment "
        "moved or changed shape. Fix this extractor; do NOT let it return an empty set."
    )
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
    assert "all" in _arg_defaults_keys(MCP_SRC)
    assert "retire" in _arg_defaults_keys(MCP_SRC)


def test_every_delegated_cmd_attribute_is_covered():
    mcp_tree = ast.parse(MCP_SRC)
    cli_tree = ast.parse(CLI_SRC)
    delegations = _delegations(mcp_tree)
    assert delegations, "no _run(agent_cli.cmd_*) delegations found -- test wiring broke"
    defaults = _arg_defaults_keys(MCP_SRC)
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
