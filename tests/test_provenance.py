"""Session provenance (meta-harness task 01): every lesson, flip and fail points at a durable
record of the harness, model and effort that produced it.

Acceptance pinned here:
  * a lesson written through the CLI, a runner tool or a hook resolves to a record with
    harness and model filled in, and effort where the harness exposes it;
  * a field the harness does not expose reads `unknown`, never a guess;
  * old lessons, with no provenance fields, still load.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.fleet import provenance  # noqa: E402  # sys.path bootstrap


def _sid() -> str:
    return f"test-{uuid.uuid4().hex[:12]}"


# --------------------------------------------------------------------------- detection
def test_claude_code_harness_and_version_come_from_its_env():
    env = {"CLAUDECODE": "1", "CLAUDE_CODE_SESSION_ID": "s1", "AI_AGENT": "claude-code_2-1-292_agent"}
    assert provenance._harness(env) == ("claude-code", "2.1.292")


def test_an_explicit_harness_wins_over_detection():
    env = {"CLAUDECODE": "1", "AKASHIC_HARNESS": "codex-desktop"}
    assert provenance._harness(env)[0] == "codex-desktop"


def test_codex_cursor_and_bare_shell_are_told_apart():
    assert provenance.detect_harness({"CODEX_SANDBOX": "seatbelt"}) == "codex-cli"
    assert provenance.detect_harness({"CURSOR_TRACE_ID": "x"}) == "cursor"
    assert provenance.detect_harness({}) == "shell"


def test_unexposed_fields_read_unknown_not_a_guess(tmp_path):
    rec = provenance.detect({"cwd": str(tmp_path)}, {}, session_id="s-none")
    assert rec["model"] == provenance.UNKNOWN
    assert rec["effort"] == provenance.UNKNOWN
    assert rec["harness"] == "shell"


def test_model_and_effort_come_from_the_payload_first(tmp_path):
    rec = provenance.detect(
        {"cwd": str(tmp_path), "model": "claude-opus-5-5", "effort": "high"},
        {"AKASHIC_MODEL": "other", "CLAUDE_EFFORT": "low"},
        session_id="s-pay",
    )
    assert (rec["model"], rec["effort"]) == ("claude-opus-5-5", "high")


def test_model_is_read_from_the_transcript_tail(tmp_path):
    t = tmp_path / "t.jsonl"
    lines = [
        {"type": "user", "message": {"role": "user", "content": "hi"}},
        {"type": "assistant", "message": {"role": "assistant", "model": "claude-sonnet-5-5"}},
        {"type": "assistant", "message": {"role": "assistant", "model": "<synthetic>"}},
    ]
    t.write_text("\n".join(json.dumps(x) for x in lines), encoding="utf-8")
    rec = provenance.detect({"cwd": str(tmp_path), "transcript_path": str(t)}, {}, session_id="s-t")
    assert rec["model"] == "claude-sonnet-5-5"


def test_the_project_fingerprint_moves_when_harness_config_moves(tmp_path):
    before = provenance.project_fingerprint(tmp_path)
    (tmp_path / "AGENTS.md").write_text("rules", encoding="utf-8")
    after = provenance.project_fingerprint(tmp_path)
    (tmp_path / ".claude" / "skills" / "s1").mkdir(parents=True)
    (tmp_path / ".claude" / "skills" / "s1" / "SKILL.md").write_text("x", encoding="utf-8")
    with_skill = provenance.project_fingerprint(tmp_path)
    assert len({before, after, with_skill}) == 3


# --------------------------------------------------------------------------- storage
def test_ensure_is_idempotent_and_fills_unknowns_later(tmp_path):
    from core.foundation.store import create_store

    st = create_store()
    sid = _sid()
    first = provenance.ensure({"cwd": str(tmp_path)}, {}, session_id=sid, store=st)
    assert first["model"] == provenance.UNKNOWN
    second = provenance.ensure({"cwd": str(tmp_path)}, {"AKASHIC_MODEL": "m1"}, session_id=sid, store=st)
    assert second["model"] == "m1"
    assert second["started_at"] == first["started_at"]
    third = provenance.ensure({"cwd": str(tmp_path)}, {"AKASHIC_MODEL": "m2"}, session_id=sid, store=st)
    assert third["model"] == "m1", "a known field must never be overwritten"
    stored = provenance.get(sid, store=st)
    assert stored is not None
    assert stored["model"] == "m1"


def test_no_session_means_no_record_unless_minted(tmp_path):
    assert provenance.ensure({"cwd": str(tmp_path)}, {}) == {}
    env: dict[str, str] = {}
    rec = provenance.ensure({"cwd": str(tmp_path)}, env, mint=True)
    assert rec["session_id"].startswith("local-")


def test_stamp_adds_the_pointer_only_when_a_session_is_known():
    got = provenance.stamp({"a": 1}, session_id="abc")
    assert got == {"a": 1, "session_id": "abc", "prov": "prov:session:abc"}


# --------------------------------------------------------------------------- the three write paths
def _cli(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "agent_cli.py", *args],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _record(name: str, env: dict[str, str]) -> dict:
    got = _cli("recall", "--full", f"learn:experiment:{name}", "--json", env=env)
    assert got.returncode == 0, got.stderr[-400:]
    return json.loads(got.stdout)


def _base_env() -> dict[str, str]:
    """os.environ minus the harness variables, so a test controls which harness it claims.
    The isolation variables stay: a child that loses them writes to the live store."""
    env = {
        k: v
        for k, v in os.environ.items()
        if not k.startswith(("CLAUDE", "CODEX_", "CURSOR_", "AKASHIC_SESSION", "AKASHIC_HARNESS", "AI_AGENT"))
    }
    env.pop("AKASHIC_MODEL", None)
    env.pop("AKASHIC_EFFORT", None)
    return env


def test_a_cli_lesson_points_at_a_record_with_harness_and_model():
    sid = _sid()
    env = {
        **_base_env(),
        "CLAUDECODE": "1",
        "CLAUDE_CODE_SESSION_ID": sid,
        "AI_AGENT": "claude-code_2-1-300_agent",
        "AKASHIC_MODEL": "claude-opus-5-5",
        "CLAUDE_EFFORT": "high",
    }
    name = f"prov_cli_{sid[-6:]}"
    r = _cli("learn", "provtest", "--experiment", name, "--tried", "t", "--result", "r", env=env)
    assert r.returncode == 0, r.stderr[-400:]
    rec = _record(name, env)
    assert rec.get("session_id") == sid
    assert rec.get("prov") == f"prov:session:{sid}"
    shown = _cli("provenance", "--session", sid, "--json", env=env)
    prov = json.loads(shown.stdout)["record"]
    assert (prov["harness"], prov["harness_version"]) == ("claude-code", "2.1.300")
    assert (prov["model"], prov["effort"]) == ("claude-opus-5-5", "high")


def test_a_runner_tool_lesson_records_the_runner_and_its_model():
    from core.comm.toolbox import ToolBox

    tb = ToolBox(
        ROOT,
        allow_exec=False,
        trust=False,
        allow_secrets=False,
        confirm=lambda _p: False,
        agent_id="provrunner",
        model="deepseek-v4-flash",
    )
    sid = tb._prov_env["AKASHIC_SESSION_ID"]
    name = f"prov_runner_{uuid.uuid4().hex[:6]}"
    # The toolbox's child inherits os.environ, and that MUST keep the suite's isolation
    # (temp AI_SETUP + db 15). So only the harness variables are removed, never the rest:
    # clearing the environment once sent this test's lessons to the live store.
    stripped = {k: os.environ.pop(k) for k in list(os.environ) if k not in _base_env()}
    assert os.environ.get("_AISETUP_TEST_ISOLATED")
    assert os.environ.get("REDIS_DB") == "15"
    try:
        tb._kb_write_ok = lambda: None  # the capability gate is not what this pins
        out = tb.knowledge_learn(name, "t", "r", "use when x")
        assert "[OK]" in out, out
        rec = _record(name, dict(os.environ))
    finally:
        os.environ.update(stripped)
    assert rec.get("agent_id") == "provrunner"
    assert rec.get("prov") == f"prov:session:{sid}"
    prov = provenance.get(sid)
    assert prov
    assert prov["harness"] == "runner:provrunner"
    assert prov["model"] == "deepseek-v4-flash"


def test_the_sessionstart_hook_writes_the_record(tmp_path):
    sid = _sid()
    payload = {"session_id": sid, "cwd": str(tmp_path), "source": "startup", "model": "claude-haiku-4-5"}
    env = {**_base_env(), "CLAUDECODE": "1", "AKASHIC_SESSION_ID": sid}
    r = subprocess.run(
        [sys.executable, "agent/harness/hooks/claude_sessionstart.py"],
        cwd=str(ROOT),
        env=env,
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert r.returncode == 0, r.stderr[-400:]
    rec = provenance.get(sid)
    assert rec
    assert rec["harness"] == "claude-code"
    assert rec["model"] == "claude-haiku-4-5"


def test_a_hook_fail_event_carries_the_pointer():
    import importlib.util

    spec = importlib.util.spec_from_file_location("ptu", ROOT / "agent/harness/hooks/claude_posttooluse.py")
    assert spec
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sid = _sid()
    mod._capture_fail("cmd:false", "Bash", sid)
    from core.events.event_log import get_event_log

    hits = [e for e in get_event_log().recent(50) if e.get("kind") == "fail" and e.get("session_id") == sid]
    assert hits, "the fail event was not captured with its session"
    assert hits[0]["detail"]["prov"] == f"prov:session:{sid}"


def test_a_repeat_carries_the_pointer():
    from core.learning.learning_store import get_learning_store_instance

    ls = get_learning_store_instance()
    name = f"prov_repeat_{uuid.uuid4().hex[:6]}"
    assert ls.record_learning({"experiment_name": name, "agent_id": "t", "what_tried": "t", "actual_outcome": "r"})
    rec = ls.record_repeat(of=name, agent_id="t", what="again", session_id="sess-r")
    assert rec["prov"] == "prov:session:sess-r"


def test_old_lessons_without_provenance_still_load():
    from core.learning.learning_store import get_learning_store_instance

    ls = get_learning_store_instance()
    name = f"prov_old_{uuid.uuid4().hex[:6]}"
    assert ls.record_learning({"experiment_name": name, "agent_id": "t", "what_tried": "t", "actual_outcome": "r"})
    rec = ls._load_experiment(name)
    assert rec
    assert "prov" not in rec
    assert "session_id" not in rec
    assert any(x.get("experiment_name") == name for x in ls.load_all_learnings_from_store())
