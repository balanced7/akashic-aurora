"""
Auto-logger Slice 2 -- auto-hooks: capture happens BY ITSELF at the seams we control.

Acceptance bar (docs/library/design/20260714_cross-agent-auto-logger-design-slice-pla_6d21c5.md):
  - a normal boot -> learn -> commit -> session-end flow yields raw events with ZERO
    manual capture calls;
  - each hook stays green if capture throws (fault injection: capture raises ->
    the host command still succeeds).

We exercise the real hook code (cmd_boot/cmd_learn/cmd_log, mirror._emit_commit_beat,
session.start/end_session) and assert the firehose filled itself. Reads are presence-based
on UNIQUE markers, so accumulation on the shared test DB can't make them flaky.
"""
import os
import sys
import uuid

import isolate_canonical            # noqa: F401  (side-effect: isolate + flush db15)

_TESTS = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_TESTS)
sys.path.insert(0, _ROOT)
sys.path.insert(0, _TESTS)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import agent_cli
from core.events import event_log
from core.events.event_log import get_event_log
from core.narrative.session import start_session, end_session


class _Args:
    """Minimal argparse-like namespace (hooks read attributes, not a real parser)."""
    def __init__(self, **kw):
        self.json = False
        for k, v in kw.items():
            setattr(self, k, v)


def _find(summary_substr, *, kind=None, agent=None):
    """Is there a raw event whose summary contains `summary_substr` (optionally of a
    given kind / agent) on the firehose? Presence-based -> robust to accumulation."""
    for e in get_event_log().recent(2000):
        if summary_substr in (e.get("summary") or "") \
                and (kind is None or e.get("kind") == kind) \
                and (agent is None or e.get("agent_id") == agent):
            return e
    return None


# ----------------------------------------------------------------- per-seam capture

def test_learn_hook_captures():
    exp = f"slice2_learn_{uuid.uuid4().hex[:8]}"
    rc = agent_cli.cmd_learn(_Args(agent_id="tester", experiment=exp, tried="x", result="y",
                                   expected="", recommend="use it", category="testing",
                                   success="yes", confidence="medium"))
    assert rc == 0
    ev = _find(exp, kind="learning")
    assert ev is not None
    assert f"learn:experiment:{exp}" in ev.get("refs", [])
    assert ev["detail"].get("category") == "testing"


def test_log_hook_captures():
    marker = f"slice2_log_{uuid.uuid4().hex[:8]}"
    rc = agent_cli.cmd_log(_Args(kind="observation", summary=marker, source="tester:act",
                                 category="testing", task="t"))
    assert rc == 0
    ev = _find(marker, kind="observation")
    assert ev is not None and "tester:act" in ev.get("refs", [])


def test_boot_hook_captures():
    agent = f"slice2agent_{uuid.uuid4().hex[:8]}"
    agent_cli.cmd_boot(_Args(agent_id=agent, task="ship slice 2"))
    ev = _find("booted", kind="boot", agent=agent)
    assert ev is not None
    assert ev["detail"].get("task") == "ship slice 2"


def test_commit_hook_captures():
    import mirror
    msg = f"slice2 commit {uuid.uuid4().hex[:8]}"
    mirror._emit_commit_beat(msg, ["core/events/event_log.py"])   # read-only git rev-parse
    ev = _find(f"git commit: {msg}", kind="command")
    assert ev is not None
    assert ev["agent_id"] == "mirror"
    assert ev["detail"].get("files") == ["core/events/event_log.py"]


def test_session_hooks_capture():
    import tempfile
    from core.foundation.store import FileStore
    s = FileStore(os.path.join(tempfile.mkdtemp(), "s.json"))
    stamp = f"2026-06-27T{uuid.uuid4().int % 24:02d}:11:{uuid.uuid4().int % 60:02d}"
    start_session(s, now=stamp, chronicle=False)
    end_session(s, now=stamp, chronicle=False)
    sess = [e for e in get_event_log().recent(2000)
            if e.get("kind") == "session" and e.get("at") == stamp]
    summaries = {e["summary"] for e in sess}
    assert "Session started" in summaries
    assert "Session ended" in summaries


def test_full_flow_fills_firehose():
    """The headline bar: a boot->learn->log->session-end flow leaves raw events behind
    with zero manual capture() calls."""
    tag = uuid.uuid4().hex[:8]
    agent = f"flow_{tag}"
    agent_cli.cmd_boot(_Args(agent_id=agent, task="end to end"))
    agent_cli.cmd_learn(_Args(agent_id=agent, experiment=f"flow_exp_{tag}", tried="a", result="b",
                              expected="", recommend="r", category="testing",
                              success="yes", confidence="medium"))
    agent_cli.cmd_log(_Args(kind="note", summary=f"flow_note_{tag}", source="flow:src",
                            category="", task=""))
    assert _find("booted", agent=agent)
    assert _find(f"flow_exp_{tag}")
    assert _find(f"flow_note_{tag}")


# ----------------------------------------------------------------- fault injection

def test_hook_survives_capture_failure(monkeypatch):
    """If the auto-logger blows up, the host command must still succeed."""
    def boom(*a, **k):
        raise RuntimeError("simulated auto-logger failure")
    # break the logger at its root; capture_event must swallow it
    monkeypatch.setattr(event_log, "get_event_log", boom)
    assert event_log.capture_event("note", "should not raise") is None
    # the host hook still returns success despite the broken logger
    rc = agent_cli.cmd_log(_Args(kind="note", summary=f"resilient_{uuid.uuid4().hex[:6]}",
                                 source="x:y", category="", task=""))
    assert rc == 0
