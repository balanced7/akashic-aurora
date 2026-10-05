"""Pin the Codex hook SCOPE GATE itself -- prod-reconcile DP5.

tests/test_codex_hook_contract.py monkeypatches ``event_in_scope`` to True so it can test the
payload contract without the scope policy in the way. That is fine for those tests and left the
gate itself with no pin anywhere (grep event_in_scope tests/ found only the bypass). Heimdall's
blind grade called this "a residual assumption deserving a second look"; this is the look.

What is pinned is the gate's SHAPE, not the scope policy: deny by default for a tool it does not
route; a routed tool with nothing to check is out of scope; and a scope module that raises is a
NO, never a yes (unknown is not a yes -- the same law the arsenal caps check states).
"""

import importlib


def _common():
    return importlib.import_module("agent.harness.hooks.codex_common")


def test_unrouted_tool_is_out_of_scope():
    c = _common()
    assert c.event_in_scope({"tool_name": "Read", "tool_input": {"path": "x"}}) is False
    assert c.event_in_scope({}) is False


def test_apply_patch_with_no_paths_is_out_of_scope():
    c = _common()
    assert c.event_in_scope({"tool_name": "apply_patch", "tool_input": {}}) is False


def test_bash_routes_to_shell_in_scope_and_is_fail_closed(monkeypatch):
    c = _common()
    scope = importlib.import_module("agent.harness.scope")
    seen = {}

    def _yes(cwd, command):
        seen["cwd"], seen["command"] = cwd, command
        return True

    monkeypatch.setattr(scope, "shell_in_scope", _yes)
    ev = {"tool_name": "Bash", "cwd": "E:/somewhere", "tool_input": {"command": "git status"}}
    assert c.event_in_scope(ev) is True
    assert seen == {"cwd": "E:/somewhere", "command": "git status"}

    def _boom(cwd, command):
        raise RuntimeError("scope policy unreadable")

    monkeypatch.setattr(scope, "shell_in_scope", _boom)
    assert c.event_in_scope(ev) is False, "a scope module that raises must read as NO"


def test_apply_patch_routes_through_file_in_scope_and_is_fail_closed(monkeypatch):
    c = _common()
    scope = importlib.import_module("agent.harness.scope")
    monkeypatch.setattr(c, "action_paths", lambda data: ["core/x.py", "elsewhere/y.py"])
    monkeypatch.setattr(scope, "file_in_scope", lambda p: p.startswith("core/"))
    ev = {"tool_name": "apply_patch", "tool_input": {}}
    assert c.event_in_scope(ev) is True
    assert c.in_scope_paths(ev) == ["core/x.py"]

    def _boom(p):
        raise RuntimeError("scope policy unreadable")

    monkeypatch.setattr(scope, "file_in_scope", _boom)
    assert c.in_scope_paths(ev) == []
    assert c.event_in_scope(ev) is False, "a scope module that raises must read as NO"
