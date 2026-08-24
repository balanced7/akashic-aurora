"""RED-first pins for agent/harness/actions.py — the rule-of-three extraction (t383).

Behavior cloned from the two in-hook copies BEFORE the move (sealed migration order,
fences/t383-dsh-adapter/reconciliation.md): claude_pretooluse._recall_context and
cursor_posttooluse's outcome flow + _recall_block, plus claude_userpromptsubmit's
build_plan_recall. Written RED (module absent at authoring time); green means the
extraction reproduces the hooks in behavior, including:
  - fail-open everywhere (any exception -> ""),
  - anti-repeat via seen keyed on seen_key,
  - impressions/ledger keyed on session_key (the FAIL->SUCCESS join key),
  - the IDENTITY THREAD: explicit agent_id beats env at the outcome stage
    (the t383 leak fix — a DSH seat inheriting a foreign env must not
    mis-attribute its outcome records).

Run: py -m pytest tests/test_harness_actions.py -q
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _fake_engine(monkeypatch, lessons=None, render_out="RECALL-TEXT"):
    """Patch the at_action seams recall_block/plan_block ride; record every call."""
    calls = {}
    import core.recall.at_action as at

    def recall_at(**kw):
        calls["recall_at"] = kw
        return {"lessons": lessons if lessons is not None else [{"source": "learn:experiment:x"}]}

    def render(res, header=None):
        calls["render_header"] = header
        return render_out if res.get("lessons") else ""

    monkeypatch.setattr(at, "recall_at", recall_at)
    monkeypatch.setattr(at, "render", render)
    monkeypatch.setattr(at, "mark_impression", lambda sid, t, s: calls.__setitem__("impression", (sid, t, list(s))))
    monkeypatch.setattr(at, "log_injection", lambda sid, alt, t, s, n: calls.__setitem__("injection", (sid, alt, t, list(s), n)))
    import agent.harness.seen as seen
    monkeypatch.setattr(seen, "load_seen", lambda k: calls.__setitem__("load_seen", k) or set())
    monkeypatch.setattr(seen, "mark_seen", lambda k, s: calls.__setitem__("mark_seen", (k, list(s))))
    return calls


# ---------------- recall_block ----------------

def test_recall_block_renders_marks_and_ledgers(monkeypatch):
    from agent.harness.actions import recall_block
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    calls = _fake_engine(monkeypatch)
    out = recall_block("agent-key", "seen-key", None, "py agent_cli.py status")
    assert out == "RECALL-TEXT"
    assert calls["load_seen"] == "seen-key"          # anti-repeat reads the seen side
    assert calls["mark_seen"][0] == "seen-key"
    assert calls["impression"][0] == "agent-key"     # the join key is the session side
    assert calls["injection"][0] == "agent-key"
    assert calls["injection"][1] == "action"


def test_recall_block_kill_switch_is_silent(monkeypatch):
    from agent.harness.actions import recall_block
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "0")
    calls = _fake_engine(monkeypatch)
    assert recall_block("k", "s", "core/x.py", None) == ""
    assert "recall_at" not in calls                  # engine never reached


def test_recall_block_empty_target_is_silent(monkeypatch):
    from agent.harness.actions import recall_block
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    calls = _fake_engine(monkeypatch)
    assert recall_block("k", "s", None, None) == ""
    assert "recall_at" not in calls


def test_recall_block_fails_open(monkeypatch):
    from agent.harness.actions import recall_block
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    import core.recall.at_action as at
    def _boom(**kw):
        raise RuntimeError("store down")
    monkeypatch.setattr(at, "recall_at", _boom)
    assert recall_block("k", "s", "core/x.py", None) == ""


def test_recall_block_explicit_agent_beats_env(monkeypatch):
    from agent.harness.actions import recall_block
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")   # the inherited, wrong value
    calls = _fake_engine(monkeypatch)
    recall_block("k", "s", "core/x.py", None, agent_id="dsh_agent")
    assert calls["recall_at"]["agent_id"] == "dsh_agent"


def test_recall_block_default_agent_is_env(monkeypatch):
    """Byte-for-byte hook behavior: no explicit agent -> env (claude/cursor unchanged)."""
    from agent.harness.actions import recall_block
    monkeypatch.setenv("AKASHIC_RECALL_AT_ACTION", "1")
    monkeypatch.setenv("AKASHIC_AGENT_ID", "composer")
    calls = _fake_engine(monkeypatch)
    recall_block("k", "s", "core/x.py", None)
    assert calls["recall_at"]["agent_id"] == "composer"


# ---------------- outcome_block ----------------

def _fake_outcome(monkeypatch, flipped, credited=2, nudge_ok=True):
    calls = {}
    import core.recall.at_action as at
    monkeypatch.setattr(at, "resolve_action_outcome",
                        lambda sid, t, ok, **kw: calls.__setitem__("resolve", (sid, t, ok, kw)) or
                        {"flipped": flipped, "credited": credited, "sources": ["learn:experiment:x"]})
    monkeypatch.setattr(at, "build_learn_nudge",
                        lambda t, c, s, a: calls.__setitem__("nudge_agent", a) or "NUDGE-TEXT")
    import agent.harness.nudge as nudge
    monkeypatch.setattr(nudge, "nudge_allowed", lambda d, k, t: nudge_ok)
    monkeypatch.setattr(nudge, "mark_nudged", lambda d, k, t: calls.__setitem__("nudged", (k, t)))
    import core.events.event_log as ev
    monkeypatch.setattr(ev, "capture_event",
                        lambda kind, msg, **kw: calls.__setitem__("event", (kind, kw.get("agent_id"))))
    return calls


def test_outcome_block_failure_resolves_fail_silently(monkeypatch):
    from agent.harness.actions import outcome_block
    calls = _fake_outcome(monkeypatch, flipped=False)
    out = outcome_block("agent-key", "seen-key", "c:py x", False)
    assert out == ""
    assert calls["resolve"][:3] == ("agent-key", "c:py x", False)


def test_outcome_block_flip_emits_nudge(monkeypatch):
    from agent.harness.actions import outcome_block
    calls = _fake_outcome(monkeypatch, flipped=True)
    out = outcome_block("agent-key", "seen-key", "c:py x", True)
    assert out == "NUDGE-TEXT"
    assert calls["nudged"][0] == "seen-key"          # rate limit rides the seen side


def test_outcome_block_flip_rate_limited_stays_silent(monkeypatch):
    from agent.harness.actions import outcome_block
    calls = _fake_outcome(monkeypatch, flipped=True, nudge_ok=False)
    assert outcome_block("agent-key", "seen-key", "c:py x", True) == ""
    assert "nudged" not in calls
    assert calls["resolve"][2] is True               # resolution still happened


def test_outcome_block_threads_explicit_agent_to_event_and_nudge(monkeypatch):
    """THE LEAK FIX PIN: env carries the WRONG (inherited) id; the explicit param wins
    everywhere identity leaves this function — the flip event, the nudge, the resolver."""
    from agent.harness.actions import outcome_block
    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")
    calls = _fake_outcome(monkeypatch, flipped=True)
    outcome_block("dsh_agent", "seen-key", "c:py x", True, agent_id="dsh_agent")
    assert calls["event"] == ("flip", "dsh_agent")
    assert calls["nudge_agent"] == "dsh_agent"
    assert calls["resolve"][3].get("agent_id") == "dsh_agent"


def test_outcome_block_fails_open(monkeypatch):
    from agent.harness.actions import outcome_block
    import core.recall.at_action as at
    def _boom(sid, t, ok, **kw):
        raise RuntimeError("boom")
    monkeypatch.setattr(at, "resolve_action_outcome", _boom)
    assert outcome_block("k", "s", "t", True) == ""


# ---------------- plan_block ----------------

def test_plan_block_renders_and_ledgers_plan_altitude(monkeypatch):
    from agent.harness.actions import plan_block
    monkeypatch.setenv("AKASHIC_PLAN_RECALL", "1")
    calls = _fake_engine(monkeypatch)
    out = plan_block("how do we ship this", "agent-key", "seen-key")
    assert out == "RECALL-TEXT"
    assert calls["injection"][0] == "agent-key"
    assert calls["injection"][1] == "plan"
    assert calls["recall_at"]["limit"] == 2


def test_plan_block_kill_switch(monkeypatch):
    from agent.harness.actions import plan_block
    monkeypatch.setenv("AKASHIC_PLAN_RECALL", "0")
    calls = _fake_engine(monkeypatch)
    assert plan_block("prompt", "k", "s") == ""
    assert "recall_at" not in calls


def test_plan_block_empty_prompt_is_silent(monkeypatch):
    from agent.harness.actions import plan_block
    monkeypatch.setenv("AKASHIC_PLAN_RECALL", "1")
    calls = _fake_engine(monkeypatch)
    assert plan_block("   ", "k", "s") == ""
    assert "recall_at" not in calls


# ---------------- the identity thread at the engine (at_action level) ----------------

def test_resolve_action_outcome_stage_record_prefers_explicit_agent(monkeypatch, tmp_path):
    """The engine half of the leak fix: the outcome-stage record's agent field takes the
    explicit param over env; without the param, env (today's behavior) is preserved."""
    import core.recall.at_action as at
    monkeypatch.setattr(at, "_STAGE_DIR", str(tmp_path))
    monkeypatch.setattr(at, "_impressions_for", lambda sid, t: [])
    monkeypatch.setattr(at, "_get_outcome", lambda sid, t: None)
    monkeypatch.setattr(at, "_set_outcome", lambda sid, t, v: None)
    monkeypatch.setenv("AKASHIC_AGENT_ID", "claude")

    at.resolve_action_outcome("sess-1", "c:x", True, agent_id="dsh_agent")
    at.resolve_action_outcome("sess-1", "c:x", True)

    recs = [json.loads(l) for l in (tmp_path / "sess-1.jsonl").read_text(encoding="utf-8").splitlines()]
    assert recs[0]["agent"] == "dsh_agent"
    assert recs[1]["agent"] == "claude"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
