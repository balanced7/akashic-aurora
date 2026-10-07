"""Selected recall content must survive every output adapter, including its tail.

Fixtures are deliberately larger than all former recall/output caps. Backends are
isolated by conftest; model responses and subprocess output are fakes, not API calls.
"""
import asyncio
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from types import SimpleNamespace as NS

import pytest

from core.recall import at_action as aa
from core.comm.toolbox import ToolBox, MAX_CMD_OUT

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))


def long_text(label, repeats=1500):
    return (f"{label} complete evidence αβ " * repeats) + f"\nQUALIFICATION: {label} TAIL — do not generalize."


@pytest.fixture
def selected():
    return {
        "lessons": [dict(text=long_text(str(i), 25), source=f"learn:experiment:long_{i}",
                         success="no", field="recommendation", agent_id="test",
                         timestamp=time.time() - 100 * 86400) for i in range(3)],
        "total": 7, "locks": [{"held_by": "peer"}],
        "counter": {"text": long_text("dissent", 25), "source": "learn:experiment:counter"},
        "verbs": [{"verb": "recall", "purpose": long_text("purpose", 25)}],
    }


def assert_selected_intact(out, selected):
    for item in selected["lessons"] + [selected["counter"]]:
        assert item["text"] in out
        assert item["source"] in out
    assert selected["verbs"][0]["purpose"] in out
    assert "3 of 7 relevant lesson(s) shown" in out
    assert "verify named files/flags still exist before leaning on it" in out
    assert out.endswith("advice=forward-looking")


def test_renderer_keeps_content_and_every_footer(selected):
    out = aa.render(selected)
    assert len(out) > 900
    assert_selected_intact(out, selected)
    assert "[unverified test advice]" in out
    assert "[lock] peer" in out


def test_cli_and_mcp_use_complete_common_renderer(monkeypatch, capsys, selected):
    import agent_cli
    monkeypatch.setattr(aa, "recall_at", lambda **kw: selected)
    args = agent_cli.build_parser().parse_args(["recall-at", "--command", "example"])
    assert args.fn(args) == 0
    assert_selected_intact(capsys.readouterr().out.rstrip(), selected)
    import ai_setup_mcp
    # _run's thread-local stdout proxy is installed at module import.
    out = asyncio.run(ai_setup_mcp.recall_at(command="example"))
    assert_selected_intact(out, selected)


@pytest.mark.parametrize("field", ["recommendation", "actual", "what_tried"])
def test_keyword_pull_keeps_selected_field_sources_and_count(monkeypatch, capsys, field):
    import agent_cli
    from core.learning import learning_store
    text = long_text(field, 25)
    rows = [dict(experiment_name=f"lesson_{i}", category="test", **{field: text}) for i in range(26)]
    monkeypatch.setattr(learning_store, "get_learning_store", lambda: NS(
        search_learnings_by_keyword=lambda *a, **kw: rows))
    args = agent_cli.build_parser().parse_args(["recall", "query"])
    assert args.fn(args) == 0
    out = capsys.readouterr().out
    assert out.count(text) == 25
    assert "learn:experiment:lesson_24" in out
    assert "25 of 26" in out
    assert "lesson_25" not in out


@pytest.mark.parametrize("altitude", ["action", "plan"])
def test_seen_sources_have_complete_delivered_text(monkeypatch, selected, altitude):
    from agent.harness import actions, seen
    delivered = []
    monkeypatch.setattr(aa, "recall_at", lambda **kw: selected)
    monkeypatch.setattr(aa, "mark_impression", lambda *a: None)
    monkeypatch.setattr(aa, "log_injection", lambda *a: None)
    monkeypatch.setattr(seen, "load_seen", lambda key: set())
    monkeypatch.setattr(seen, "mark_seen", lambda key, sources: delivered.extend(sources))
    monkeypatch.setenv("AKASHIC_PLAN_RECALL", "1")
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    out = (actions.recall_block("session", "seen", None, "example") if altitude == "action"
           else actions.plan_block("example", "session", "seen"))
    assert delivered == [lesson["source"] for lesson in selected["lessons"]]
    assert_selected_intact(out, selected)
    if altitude == "action":
        from agent.harness.hooks.claude_pretooluse import _emit_context
        import contextlib
        import io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            _emit_context(out)
        assert json.loads(buf.getvalue())["hookSpecificOutput"]["additionalContext"] == out


@pytest.mark.parametrize("argv", [["recall-at", "--command", "x"], ["recall", "x", "--json"],
                                  ["recall", "--full", "learn:experiment:x", "--json"], ["list"]])
def test_toolbox_cli_keeps_recall_beyond_generic_cap(monkeypatch, tmp_path, argv):
    import core.comm.toolbox as tb
    payload = json.dumps({"recommendation": long_text("cli")})
    monkeypatch.setattr(tb.subprocess, "run", lambda *a, **kw: NS(stdout=payload, stderr=""))
    box = ToolBox.__new__(ToolBox)
    box.root = tmp_path
    assert box._agent_cli(argv) == payload
    assert box._agent_cli(["status"]) == payload[:MAX_CMD_OUT]


def test_toolbox_pre_and_postflight_keep_complete_recall(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_RECALL_AT", "1")
    box = ToolBox.__new__(ToolBox)
    box.agent_id = "recall-test"
    text = long_text("injection")
    monkeypatch.setattr(box, "_agent_cli", lambda *a, **kw: text)
    assert box._recall_at("read_file", {"path": "x"}).endswith(text)
    pre = box._preflight_recall("read_file", {"path": "x"})
    assert pre.replace("[recall (pre-flight)] ", "").rstrip() == text


def test_deepseek_history_preserves_recall_around_capped_ordinary_output(monkeypatch):
    import deepseek_chat as dc
    box = ToolBox.__new__(ToolBox)
    pre, post, body = long_text("pre"), long_text("post"), long_text("ordinary")
    monkeypatch.setattr(box, "read_file", lambda **kw: body)
    monkeypatch.setattr(box, "_preflight_recall", lambda *a: pre)
    monkeypatch.setattr(box, "_recall_at", lambda *a: post)
    ag = dc.Agent.__new__(dc.Agent)
    ag.messages, ag.toolbox, ag.model = [], box, "fake"
    ag.interrupt = ag.inject = None
    ag._activity = ag._trace = lambda *a: None
    turns = iter([("", [{"id": "call", "name": "read_file", "arguments": "{}"}]), ("done", [])])
    ag._stream_turn = lambda: next(turns)
    assert ag.send("test") == "done"
    out = next(m["content"] for m in ag.messages if m["role"] == "tool")
    assert pre in out and post in out
    assert body not in out and "[clipped " in out
    assert "[hop 1 | tool-round 1" in out


@pytest.mark.parametrize("error", [TypeError, ValueError, RuntimeError])
def test_ordinary_errors_still_obey_output_bound(monkeypatch, error):
    import deepseek_chat as dc
    box = ToolBox.__new__(ToolBox)
    def fail(**kw):
        raise error(long_text("error"))
    monkeypatch.setattr(box, "read_file", fail)
    out = box.execute("read_file", {}, output_transform=dc.clip_tool_result)
    assert len(out) < len(long_text("error"))
    assert "ERROR:" in out and "[clipped " in out
    assert "error TAIL" not in out


@pytest.mark.parametrize("module_name", ["kimi_chat", "gemini_chat", "sol_chat", "deepseek_chat"])
@pytest.mark.parametrize("tool_name", ["recall_at", "knowledge_recall", "knowledge_full", "run_command", "read_file"])
def test_runner_model_history_preserves_explicit_recall(module_name, tool_name, monkeypatch):
    module = importlib.import_module(module_name)
    text = long_text("history")
    arguments = '{"command": "py agent_cli.py recall query"}' if tool_name == "run_command" else "{}"
    if module_name == "deepseek_chat":
        box = ToolBox.__new__(ToolBox)
        monkeypatch.setattr(box, tool_name, lambda **kw: text)
        monkeypatch.setattr(box, "_recall_at", lambda *a: "")
        monkeypatch.setattr(box, "_preflight_recall", lambda *a: "")
        ag = module.Agent.__new__(module.Agent)
        ag.messages, ag.toolbox, ag.model = [], box, "fake"
        ag.interrupt = ag.inject = None
        ag._activity = ag._trace = lambda *a: None
        turns = iter([("", [{"id": "call", "name": tool_name, "arguments": arguments}]), ("done", [])])
        ag._stream_turn = lambda: next(turns)
    elif module_name == "sol_chat":
        from test_t090_sol_agent import FakeTransport, _tool_resp, _call, _final
        transport = FakeTransport([_tool_resp(_call("call", tool_name, arguments)), _final("done")])
        ag = module.SolAgent(transport, instructions="test", dispatch=lambda *a: text)
    else:
        call = NS(id="call", function=NS(name=tool_name, arguments=arguments))
        turns = iter([NS(choices=[NS(message=NS(content="", tool_calls=[call]))], usage=None),
                      NS(choices=[NS(message=NS(content="done", tool_calls=[]))], usage=None)])
        client = NS(chat=NS(completions=NS(create=lambda **kw: next(turns))))
        cls = module.KimiAgent if module_name == "kimi_chat" else module.GeminiAgent
        ag = cls(instructions="test", client=client, meter=NS(record=lambda *a: None),
                 dispatch=lambda *a: text)
    assert ag.send("test") == "done"
    history = ag.messages if module_name == "deepseek_chat" else ag.history
    row = next(m for m in history if isinstance(m, dict) and
               (m.get("role") == "tool" or m.get("type") == "function_call_output"))
    out = row.get("content", row.get("output"))
    assert "[hop 1" in out
    if tool_name == "read_file":
        assert len(out) < len(text)
    else:
        assert text in out


@pytest.mark.parametrize("verb", ["recall query", "recall-at --command query", "list"])
def test_authorized_command_recall_keeps_output_and_exit(monkeypatch, tmp_path, verb):
    import core.comm.toolbox as tb
    box = ToolBox.__new__(ToolBox)
    box.root, box.allow_exec, box.trust, box.agent_id = tmp_path, True, True, None
    text = long_text("command")
    monkeypatch.setattr(tb.subprocess, "run", lambda *a, **kw: NS(stdout=text, stderr="diagnostic", returncode=2))
    assert box.run_command(f"py agent_cli.py {verb}") == text + "\n[stderr]\ndiagnostic\n[exit 2]"
    assert len(box.run_command("py agent_cli.py status")) < len(text)
    box.allow_exec = False
    assert box.run_command("py agent_cli.py recall query").startswith("run_command is DISABLED")


@pytest.mark.parametrize("command", ["py agent_cli.py status", "echo recall", "py agent_cli.py recall x; other",
                                   "py agent_cli.py recall x | other", "py agent_cli.py recall \"unterminated"])
def test_unrelated_or_compound_commands_keep_generic_policy(command):
    from core.comm.toolbox import recall_tool_request
    assert not recall_tool_request("run_command", {"command": command})
    assert not recall_tool_request("read_file", {"path": "recall"})


@pytest.mark.parametrize("args", [None, [], ["unexpected"], "unexpected", 42])
def test_malformed_tool_arguments_return_errors_instead_of_crashing(args):
    from core.comm.toolbox import recall_tool_request
    box = ToolBox.__new__(ToolBox)
    assert not recall_tool_request("run_command", args)
    assert box.execute("run_command", args, output_transform=lambda out: out[:20000]).startswith("ERROR: bad arguments")


@pytest.mark.parametrize("script", ["agent_cli.py", "./agent_cli.py", "C:/project/agent_cli.py"])
def test_authorized_cli_path_spellings_keep_recall_at_history_boundary(monkeypatch, script):
    box = ToolBox.__new__(ToolBox)
    text = long_text("path")
    monkeypatch.setattr(box, "run_command", lambda **kw: text)
    monkeypatch.setattr(box, "_recall_at", lambda *a: "")
    assert box.execute("run_command", {"command": f"py {script} recall x"},
                       output_transform=lambda out: out[:20000]) == text


@pytest.mark.parametrize("steps", [
    [["recall", "x"], ["doctor"], ["doctor"]],
    [["doctor"], ["doctor"], ["recall", "x"]],
])
@pytest.mark.parametrize("failed", [False, True])
def test_codex_combo_keeps_recall_after_generic_budget_exhausted(monkeypatch, steps, failed):
    from agent.harness.codex_bifrost_wake import CodexBifrostWake
    watcher = CodexBifrostWake.__new__(CodexBifrostWake)
    watcher.allow_exec = True
    text = long_text("combo") + ("\n[exit 2]" if failed else "")
    watcher._toolbox = NS(run_command=lambda command, **kw: text if " recall " in command else "x" * 16000)
    monkeypatch.setattr(watcher, "_safe_combo_catalog", lambda: {"probe": steps})
    out = watcher.handle_dynamic_tool_call({"tool": "aurora_read_combo", "arguments": {"name": "probe"}})
    body = out["contentItems"][0]["text"]
    assert text in body
    assert body.count("x") <= 24000
    assert out["success"] is not failed


def test_real_cli_process_returns_complete_selected_and_full_records(tmp_path):
    """Exercise the real parser/store/ranker/render path in fresh isolated processes."""
    root = Path(__file__).resolve().parents[1]
    env = dict(os.environ, AI_SETUP=str(tmp_path), REDIS_PORT="1", REDIS_DB="15",
               AKASHIC_STORE_BACKEND="file", AKASHIC_AGENT_ID="recall-intact-test",
               AKASHIC_RECALL_STATE_DIR=str(tmp_path / "recall"), PYTHONUTF8="1",
               _AISETUP_TEST_ISOLATED="1")
    # The existing per-line FAITH gate expects one line carrying its source.
    # Multiline fidelity is tested above at the rendering/delivery boundary;
    # this fixture must clear unchanged selection and faithfulness first.
    text = "Use when editing quasarrecall: " + long_text("quasarrecall", 35).replace("\n", " ")
    rows = [dict(experiment_name=f"quasarrecall_{i}", recommendation=text,
                 what_tried=long_text("trial", 25), actual_outcome=long_text("outcome", 25),
                 success="yes", agent_id="fixture", files_affected=["quasarrecall.py"])
            for i in range(4)]
    # Keep the query discriminative: the real IDF ranker correctly suppresses a
    # token present in every record, even when that tiny corpus is just fixtures.
    rows += [dict(experiment_name=f"other_{i}", recommendation="Unrelated orbital calibration.",
                  success="yes", agent_id="fixture") for i in range(16)]
    seed = ("import json,sys; from core.learning.learning_store import get_learning_store; "
            "ls=get_learning_store(); "
            "assert all(ls.persist_learning_derived_from_experiment(r) for r in json.load(sys.stdin))")
    subprocess.run([sys.executable, "-c", seed], input=json.dumps(rows), cwd=root,
                   env=env, text=True, encoding="utf-8", capture_output=True, check=True)

    def cli(*args):
        proc = subprocess.run([sys.executable, "agent_cli.py", *args], cwd=root,
                              env=env, text=True, encoding="utf-8", capture_output=True, timeout=30)
        assert proc.returncode == 0, proc.stderr + proc.stdout
        return proc.stdout

    selected = json.loads(cli("recall-at", "--command", "quasarrecall", "--limit", "3", "--json"))
    assert len(selected["lessons"]) == 3, selected
    rendered = cli("recall-at", "--command", "quasarrecall", "--limit", "3")
    for lesson in selected["lessons"]:
        assert lesson["text"] == text
        assert text in rendered and lesson["source"] in rendered
    assert "3 of 4 relevant lesson(s) shown" in rendered
    assert len(rendered) > 900
    pulled = cli("recall", "quasarrecall")
    assert pulled.count(text) == 4
    full = cli("recall", "--full", "learn:experiment:quasarrecall_0")
    assert text in full and rows[0]["what_tried"] in full and rows[0]["actual_outcome"] in full
    print(f"door receipt: recall-at={len(rendered)} chars; keyword={len(pulled)}; full={len(full)}; all tails intact")
