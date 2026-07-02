"""JIT learn-nudge tests (friction audit D5): a FAIL->SUCCESS flip is the moment a lesson was just
earned -- resolve_action_outcome reports it + logs it, the PostToolUse hook nudges ONCE (rate-limited,
kill-switchable), and the wrap draft turns logged flips into pre-filled candidate `learn` commands."""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import core.recall.at_action as aa
from scripts.hooks import claude_posttooluse as hook
import agent_cli


def _patch_state_dirs(monkeypatch, tmp_path):
    for name in ("_IMP_DIR", "_OUTCOME_DIR", "_FLIP_DIR"):
        monkeypatch.setattr(aa, name, str(tmp_path / name))
    for name in ("_TXW_DIR", "_CAP_DIR", "_NUDGE_DIR"):
        monkeypatch.setattr(hook, name, str(tmp_path / name))
    monkeypatch.setattr(aa, "record_feedback", lambda src, kind="useful", store=None: True)


# --- core: the full-report resolver + flip log -----------------------------------------------------

def test_resolve_action_outcome_reports_and_logs_flip(tmp_path, monkeypatch):
    _patch_state_dirs(monkeypatch, tmp_path)
    sid, tgt = "nudge-core", "c:py failing_probe.py"
    aa.mark_impression(sid, tgt, ["learn:experiment:a", "learn:experiment:b"])
    assert aa.resolve_action_outcome(sid, tgt, True) == {"flipped": False, "credited": 0, "sources": []}, \
        "first-try success must not flip"
    aa.resolve_action_outcome(sid, tgt, False)
    rep = aa.resolve_action_outcome(sid, tgt, True)
    assert rep["flipped"] is True and rep["credited"] == 2
    assert rep["sources"] == ["learn:experiment:a", "learn:experiment:b"]
    flips = aa.session_flips(sid)
    assert len(flips) == 1 and flips[0]["t"] == tgt and flips[0]["credited"] == 2


def test_flip_logs_even_without_impressions(tmp_path, monkeypatch):
    """A flip with NO surfaced lesson is the strongest capture signal -- the corpus had nothing."""
    _patch_state_dirs(monkeypatch, tmp_path)
    sid, tgt = "nudge-gap", "c:py gap_probe.py"
    aa.resolve_action_outcome(sid, tgt, False)
    rep = aa.resolve_action_outcome(sid, tgt, True)
    assert rep["flipped"] is True and rep["credited"] == 0 and rep["sources"] == []
    assert len(aa.session_flips(sid)) == 1


def test_resolve_outcome_compat_returns_int(tmp_path, monkeypatch):
    _patch_state_dirs(monkeypatch, tmp_path)
    sid, tgt = "nudge-compat", "c:x"
    aa.mark_impression(sid, tgt, ["learn:experiment:a"])
    aa.resolve_outcome(sid, tgt, False)
    assert aa.resolve_outcome(sid, tgt, True) == 1


def test_recent_flips_window(tmp_path, monkeypatch):
    _patch_state_dirs(monkeypatch, tmp_path)
    aa.resolve_action_outcome("s1", "c:a", False)
    aa.resolve_action_outcome("s1", "c:a", True)
    aa.resolve_action_outcome("s2", "c:b", False)
    aa.resolve_action_outcome("s2", "c:b", True)
    # a stale flip (2h old, injected -- NOT a real-clock zero-width window, which flakes on
    # Windows tick granularity) must fall outside a 1h window
    import time as _t
    stale = {"t": "c:stale", "credited": 0, "s": [], "at": _t.time() - 7200}
    with open(os.path.join(aa._FLIP_DIR, "s3.jsonl"), "w", encoding="utf-8") as f:
        f.write(json.dumps(stale) + "\n")
    got = aa.recent_flips(hours=1)
    assert [r["t"] for r in got] == ["c:a", "c:b"], "in-window flips across sessions, oldest first; stale excluded"


# --- core: nudge text + pre-filled command ---------------------------------------------------------

def test_learn_command_prefills_slug_and_agent():
    cmd = aa.learn_command_for("c:py -m pytest tests/test_ranker.py", agent_id="claude")
    assert cmd.startswith("py agent_cli.py learn claude --experiment fix_")
    assert "--tried" in cmd and "--result" in cmd


def test_build_learn_nudge_gap_vs_credited():
    gap = aa.build_learn_nudge("c:py probe.py", 0, [], agent_id="claude")
    assert "[flip]" in gap and "corpus gap" in gap and "learn claude" in gap
    credited = aa.build_learn_nudge("c:py probe.py", 2, ["learn:experiment:a"], agent_id="claude")
    assert "2 stored lesson(s)" in credited and "corpus gap" not in credited
    assert len(credited) < 600, "small-when-not: the nudge must never be a wall of text"


# --- hook: rate limiting ----------------------------------------------------------------------------

def test_nudge_once_per_target_and_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "_NUDGE_DIR", str(tmp_path))
    sid = "rate-limit"
    assert hook._nudge_allowed(sid, "c:a") is True
    hook._mark_nudged(sid, "c:a")
    assert hook._nudge_allowed(sid, "c:a") is False, "same target never nudges twice"
    for t in ("c:b", "c:c"):
        assert hook._nudge_allowed(sid, t) is True
        hook._mark_nudged(sid, t)
    assert hook._nudge_allowed(sid, "c:d") is False, "session cap (default 3) reached"


def test_nudge_kill_switch(tmp_path, monkeypatch):
    monkeypatch.setattr(hook, "_NUDGE_DIR", str(tmp_path))
    monkeypatch.setenv("AKASHIC_LEARN_NUDGE", "0")
    assert hook._nudge_allowed("s", "c:a") is False


# --- hook e2e: a flip emits ONE PostToolUse additionalContext nudge --------------------------------

def _bash_payload(command, sid):
    return {"session_id": sid, "transcript_path": "missing.jsonl", "cwd": "C:\\Elsewhere",
            "hook_event_name": "PostToolUse", "tool_name": "Bash",
            "tool_input": {"command": command},
            "tool_response": {"stdout": "ok", "stderr": "", "interrupted": False}}


def _run_hook(monkeypatch, payload, capsys):
    import core.events.event_log as ev
    monkeypatch.setattr(ev, "capture_event", lambda *a, **k: None)
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert hook.main() == 0
    return capsys.readouterr().out.strip()


def test_hook_emits_nudge_on_flip_then_goes_quiet(tmp_path, monkeypatch, capsys):
    _patch_state_dirs(monkeypatch, tmp_path)
    cmd = "py agent_cli.py boot probe && exit 0"   # 'agent_cli.py' keeps it in scope, cwd elsewhere
    sid = "nudge-e2e"
    tgt = aa.normalize_target(None, cmd)
    aa.mark_impression(sid, tgt, ["learn:experiment:a"])
    aa._set_outcome(sid, tgt, "FAIL")
    out = _run_hook(monkeypatch, _bash_payload(cmd, sid), capsys)
    payload = json.loads(out)
    ctx = payload["hookSpecificOutput"]["additionalContext"]
    assert payload["hookSpecificOutput"]["hookEventName"] == "PostToolUse"
    assert "[flip]" in ctx and "learn" in ctx
    # the same success again: no FAIL preceding -> no flip -> silence (silent-when-irrelevant)
    out2 = _run_hook(monkeypatch, _bash_payload(cmd, sid), capsys)
    assert out2 == ""


def test_hook_flip_without_nudge_budget_stays_silent(tmp_path, monkeypatch, capsys):
    _patch_state_dirs(monkeypatch, tmp_path)
    monkeypatch.setenv("AKASHIC_LEARN_NUDGE", "0")
    cmd = "py agent_cli.py boot probe2 && exit 0"
    sid = "nudge-off"
    tgt = aa.normalize_target(None, cmd)
    aa._set_outcome(sid, tgt, "FAIL")
    out = _run_hook(monkeypatch, _bash_payload(cmd, sid), capsys)
    assert out == "", "kill switch: flip still resolves (credit/log) but no context is emitted"
    assert len(aa.session_flips(sid)) == 1


# --- wrap draft: flips become pre-filled candidate lessons -----------------------------------------

def test_session_draft_includes_candidate_lessons():
    flips = [{"t": "c:py -m pytest tests/test_x.py", "credited": 1, "s": ["learn:experiment:a"], "at": 1.0}]
    d = agent_cli.build_session_draft([], [], [], flips=flips)
    assert "Candidate lessons" in d
    assert "py agent_cli.py learn" in d and "--experiment fix_" in d


def test_session_draft_no_flips_no_section():
    d = agent_cli.build_session_draft([("abc123", "a commit")], [], [], flips=[])
    assert "Candidate lessons" not in d


def test_session_draft_dedupes_repeated_flip_target():
    flips = [{"t": "c:py probe.py", "credited": 0, "s": [], "at": 1.0},
             {"t": "c:py probe.py", "credited": 2, "s": ["learn:experiment:a"], "at": 2.0},
             {"t": "p:/other.py", "credited": 0, "s": [], "at": 3.0}]
    d = agent_cli.build_session_draft([], [], [], flips=flips)
    assert d.count("command: py probe.py") == 1, "one candidate per target, not one per retry"
    assert "c:py probe.py" not in d, "the raw join key never reaches the human draft"
    assert "(credited: 2)" in d, "the LAST flip's credited count wins"
    assert d.count("py agent_cli.py learn") == 2
