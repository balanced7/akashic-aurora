"""Plan-time recall (UserPromptSubmit hook, field-survey C3): highest-altitude surfacing,
shared anti-repeat with the action-time hook, ledgered as altitude=plan, killable, scoped."""
import io
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.hooks import claude_userpromptsubmit as hook


def _wire(monkeypatch, lessons, seen=None, seen_log=None, inj_log=None):
    import core.recall.at_action as aa
    from scripts.hooks import claude_pretooluse as pre
    monkeypatch.setattr(aa, "recall_at",
                        lambda **kw: {"lessons": lessons, "locks": [], "counter": None,
                                      "shown": len(lessons), "total": len(lessons),
                                      "faithful": True, "confidence": 1.0})
    monkeypatch.setattr(pre, "_load_seen", lambda sid: set(seen or set()))
    monkeypatch.setattr(pre, "_mark_seen",
                        lambda sid, srcs: (seen_log if seen_log is not None else []).extend(srcs))
    monkeypatch.setattr(aa, "log_injection",
                        lambda *a, **k: (inj_log if inj_log is not None else []).append(a))


def test_plan_recall_surfaces_with_plan_header(monkeypatch):
    seen_log, inj_log = [], []
    _wire(monkeypatch, [{"text": "watch the seam", "source": "learn:experiment:x"}],
          seen_log=seen_log, inj_log=inj_log)
    out = hook.build_plan_recall("refactor the consolidator seam", "sess-1", "claude")
    assert out.startswith("Plan-time recall (Akashic)")
    assert "learn:experiment:x" in out
    assert seen_log == ["learn:experiment:x"], "plan-time surfacing feeds the shared anti-repeat"
    assert inj_log and inj_log[0][1] == "plan", "ledgered at plan altitude"


def test_plan_recall_silent_when_nothing_clears_floor(monkeypatch):
    _wire(monkeypatch, [])
    assert hook.build_plan_recall("anything", "sess-1", "claude") == ""


def test_plan_recall_kill_switch_and_empty_prompt(monkeypatch):
    _wire(monkeypatch, [{"text": "t", "source": "learn:experiment:x"}])
    monkeypatch.setenv("AKASHIC_PLAN_RECALL", "0")
    assert hook.build_plan_recall("real prompt", "s", "claude") == ""
    monkeypatch.delenv("AKASHIC_PLAN_RECALL")
    assert hook.build_plan_recall("   ", "s", "claude") == ""


def test_main_out_of_scope_is_silent(monkeypatch, capsys):
    _wire(monkeypatch, [{"text": "t", "source": "learn:experiment:x"}])
    payload = {"cwd": "C:\\Somewhere\\Else" if os.name == "nt" else "/somewhere/else",
               "prompt": "do things", "session_id": "s"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert hook.main() == 0
    assert capsys.readouterr().out.strip() == ""


def test_main_in_repo_emits_valid_json(monkeypatch, capsys):
    _wire(monkeypatch, [{"text": "t", "source": "learn:experiment:x"}])
    from scripts.hooks.claude_sessionstart import _ROOT_RAW
    payload = {"cwd": _ROOT_RAW, "prompt": "plan the slice", "session_id": "s"}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(payload)))
    assert hook.main() == 0
    out = json.loads(capsys.readouterr().out)
    assert out["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    assert "Plan-time recall" in out["hookSpecificOutput"]["additionalContext"]
