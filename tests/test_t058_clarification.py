"""T058 (R7 mid-turn clarification) PRE-REGISTERED ACCEPTANCE -- committed RED.

Cites docs/library/report/20260714_r7-mid-turn-clarification-deepseek-desig_bd991a.md (his
design; fence-lite confirmed; claude builds, deepseek live-verifies P1/P3/P4/P7/P8).
These pins cover the mechanical ToolBox bars (his P2/P6 + the directed-send shape).
Build correction folded: the send is DIRECTED to 'user' (his 2b prose), never a
broadcast (his sketch's broadcast would wake peer listeners with it).
"""
import os
import sys

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))


class _FakeBus:
    def __init__(self):
        self.sent = []

    def send(self, to, kind, content, meta=None):
        self.sent.append({"to": to, "kind": kind, "content": content, "meta": meta or {}})
        return "1-1"

    def broadcast(self, kind, content, meta=None):
        raise AssertionError("clarifications must be DIRECTED to user, never broadcast")


def _box(monkeypatch, bus="fake"):
    import deepseek_chat as dc
    box = dc.ToolBox.__new__(dc.ToolBox)
    box.agent_id = "t058-test"
    fake = _FakeBus() if bus == "fake" else None
    monkeypatch.setattr(box, "_bus", lambda: fake, raising=False)
    return box, fake


# ------------------------------------------------ B1 (his P2): budget refusal
def test_b1_fourth_call_refused(monkeypatch):
    import deepseek_chat as dc
    box, fake = _box(monkeypatch)
    for i in range(dc.CLARIFY_MAX_PER_TASK):
        out = box.ask_clarification(f"question {i}?")
        assert "REFUSED" not in out
    out4 = box.ask_clarification("one too many?")
    assert "REFUSED" in out4 and "best judgment" in out4, \
        "B1: the call past the budget refuses with proceed-with-assumption guidance"
    assert len(fake.sent) == dc.CLARIFY_MAX_PER_TASK, "B1: the refused call never sends"


# ------------------------------------------------ B2 (his P6): offline refusal
def test_b2_bus_offline_returns_error(monkeypatch):
    box, _ = _box(monkeypatch, bus=None)
    out = box.ask_clarification("anyone there?")
    assert out.startswith("ERROR") and "bus" in out.lower(), \
        "B2: Redis down -> error string, never a crash"


# ------------------------------------------------ B3: directed-send shape
def test_b3_directed_to_user_with_clarify_meta(monkeypatch):
    box, fake = _box(monkeypatch)
    out = box.ask_clarification("A or B?", context="deciding the frobnicator")
    assert "Waiting" in out or "waiting" in out
    assert len(fake.sent) == 1
    m = fake.sent[0]
    assert m["to"] == "user", "B3: DIRECTED to the human operator only"
    assert m["kind"] == "request"
    assert m["meta"].get("kind") == "clarify" and m["meta"].get("clarify_id"), \
        "B3: meta carries kind=clarify + a clarify_id for the answer fold"
    assert "CLARIFICATION:" in m["content"] and "frobnicator" in m["content"]


# ------------------------------------------------ B4: waiting state armed
def test_b4_waiting_state_and_deadline_armed(monkeypatch):
    import deepseek_chat as dc
    box, _ = _box(monkeypatch)
    box.ask_clarification("well?")
    assert getattr(box, "_clarify_waiting", None), "B4: the waiting flag is set"
    assert getattr(box, "_clarify_deadline", 0) > 0, "B4: the timeout deadline is armed"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
