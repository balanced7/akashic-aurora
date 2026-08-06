"""
T200 -- ask + friction get MCP twins. RED before impl.

PAYING DOWN DEBT THE MANIFEST ALREADY NAMED. check_door_parity has carried `ask` and
`friction` as `gap` (not `cli_only`) with this reason written next to `ask`: "SHOULD be
shared and is recorded as debt, not as a design choice. Its whole purpose is cutting the
cost of asking for help, and THE SEAT THAT NEEDS IT MOST IS THE MCP-ATTACHED CONDUCTOR --
so an MCP twin is the right end state. CLI-only is survivable today only because seats
shell out."

Measured 2026-08-06: the MCP-attached conductor shelled out to `py agent_cli.py ask`
eight times in one session while building the collaboration front door, which is the
exact friction Sol's write-up says to remove ("make one direct collaboration flow so easy
that nobody needs to understand Bifrost to use it"). A front door reachable from only one
of two doors is not a front door.

THE FIDELITY TRAP THIS SLICE MUST NOT FALL INTO, and the reason these pins exist. The MCP
adapter (_run) captures STDOUT ONLY -- by design, since core logging goes to stderr. But:
  * cmd_ask writes the T197 peer verdict to STDERR ("NOBODY HOME", state, how_to_check)
  * cmd_friction writes its BLIND LIST to STDERR
So a naive text twin returns the answer while silently dropping the peer verdict, and
returns friction's numbers while dropping the confession of what they cannot see -- "a
report that names no blindness is claiming omniscience", now with the blindness removed
by the transport. Both twins therefore return the STRUCTURED record (json=True), which is
a superset of both streams. That is the contract pinned here.

DELIBERATELY NOT EXPOSED: launch. Spawning a peer process is a privileged side effect,
and the MCP door widens the caller set from "someone with shell" to "any attached seat" --
the same reasoning the manifest already applies to `grant` and `season_score`. Recorded as
a classification with a reason, never as an oversight.

Run: py -m pytest tests/test_t200_ask_friction_mcp_twins.py -q
"""
import ast
import inspect
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _mcp_src():
    with open(os.path.join(_ROOT, "ai_setup_mcp.py"), encoding="utf-8") as fh:
        return fh.read()


def _tool_names():
    """Names of every @mcp.tool()-decorated function, read from the AST so prose in a
    docstring can never be mistaken for a tool (the T171 K6 lesson)."""
    tree = ast.parse(_mcp_src())
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                fn = dec.func if isinstance(dec, ast.Call) else dec
                if isinstance(fn, ast.Attribute) and fn.attr == "tool":
                    out.add(node.name)
    return out


def _fn(name):
    tree = ast.parse(_mcp_src())
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    return None


# --------------------------------------------------------------------------------------
# The twins exist and are reachable.
# --------------------------------------------------------------------------------------

def test_ask_and_friction_are_on_the_mcp_door():
    names = _tool_names()
    assert "ask" in names, "the front door must be reachable from the door the conductor uses"
    assert "friction" in names


def test_ask_peer_is_reachable_not_just_the_stateless_helper():
    """The durable seat-addressed transport is the half that needed a twin most -- the
    stateless helper was always one HTTP call away."""
    node = _fn("ask")
    args = {a.arg for a in node.args.args} | {a.arg for a in node.args.kwonlyargs}
    assert "peer" in args, "ask_peer must be reachable from MCP, not only the CLI"


def test_manifest_no_longer_calls_them_gaps():
    """The debt is paid DOWN, not renamed. check_door_parity must now class both as
    shared, so the guard fails if a future edit removes a twin."""
    from scripts.checkers import check_door_parity as dp
    assert dp.MANIFEST["ask"] == "shared"
    assert dp.MANIFEST["friction"] == "shared"


def test_door_parity_guard_passes():
    """The guard is the falsifier for this whole slice: it compares the manifest against
    the ACTUAL surfaces, so a manifest edit without a real tool fails here."""
    from scripts.checkers import check_door_parity as dp
    rc = dp.main() if hasattr(dp, "main") else 0
    assert rc == 0, "door parity must pass with ask/friction reclassified as shared"


# --------------------------------------------------------------------------------------
# The fidelity contract: nothing the CLI tells an operator may be lost in transport.
# --------------------------------------------------------------------------------------

def test_ask_twin_returns_the_structured_record_not_stdout_text():
    """cmd_ask writes the T197 peer verdict to STDERR, and the MCP adapter captures
    stdout only. A text twin would return the answer while silently dropping 'NOBODY
    HOME' -- the transport deleting the honesty. json=True is the fix and is pinned."""
    src = ast.unparse(_fn("ask"))
    assert "json=True" in src, (
        "the ask twin must request the structured record, or the peer verdict "
        "(stderr-only on the CLI) vanishes on the MCP door")


def test_friction_twin_keeps_the_blind_list():
    """friction prints `blind` to STDERR. Dropping it would ship the numbers without
    the confession of what they cannot see -- omniscience by transport."""
    src = ast.unparse(_fn("friction"))
    assert "json=True" in src


@pytest.mark.parametrize("name", ["ask", "friction"])
def test_twins_delegate_to_the_cli_command_never_reimplement(name):
    """One implementation, two doors. A twin that re-derived the render would drift,
    which is the exact class check_door_parity exists to catch."""
    src = ast.unparse(_fn(name))
    assert f"cmd_{name}" in src, f"{name} twin must call agent_cli.cmd_{name}"


# --------------------------------------------------------------------------------------
# The deliberate omission, recorded as a decision.
# --------------------------------------------------------------------------------------

def test_launch_is_not_exposed_on_the_mcp_door():
    """Spawning a peer process is a privileged side effect. On the CLI the caller already
    needs shell access; on MCP it would become callable by any attached seat. Same
    reasoning the manifest applies to `grant` and `season_score`. If this is ever
    revisited it must be a decision, not a drift."""
    node = _fn("ask")
    args = {a.arg for a in node.args.args} | {a.arg for a in node.args.kwonlyargs}
    assert "launch" not in args
    src = ast.unparse(node)
    assert "launch=False" in src, "the twin must pass launch=False EXPLICITLY, not by omission"


def test_the_omission_is_explained_in_the_docstring():
    """An undocumented omission reads as an oversight to the next person and gets
    'fixed' silently."""
    doc = (_fn("ask").body[0].value.value or "").lower()
    assert "launch" in doc, "the docstring must say launch is absent and why"
