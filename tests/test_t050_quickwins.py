"""T050 -- wishlist quick-wins bundle (both agents' felt friction; synthesis Q1-Q6).

Design record: research/reviewed/wishlist-synthesis-2026-07-14.md (two blind halves converged).

Pins:
  W1 _trim_onboarding: under-budget unchanged; over-budget NAMES dropped sections + pull
     pointers (Q2 -- the T043 refuse-loud law applied to boot context).
  W2 memory_note/memory_recall: private scratchpad round-trip via AgentMemory (Q1).
  W3 lock note: acquire(note=...) renders WHY in the holder record (Q5).
  W4 seat-path parity: the fast (import-free) seat path EXACTLY equals wake_seat.seat_path
     (Q6 -- a drifted convention would un-arm every session silently).

Run: py -m pytest tests/test_t050_quickwins.py -q
"""
import os
import sys
import types
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import bifrost_runner_deepseek as runner
import bifrost_wake
import deepseek_chat as dc
from pathlib import Path


# ------------------------------------------------------------------ W1: loud trim
def test_trim_under_budget_unchanged():
    assert runner._trim_onboarding("short digest", 6000) == "short digest"


def test_trim_over_budget_names_dropped_sections():
    digest = ("HEAD " * 20) + "\n## KEPT SECTION\nbody\n" + ("x" * 200) + \
             "\n## DROPPED ALPHA\nbody\n## DROPPED BETA\nmore"
    out = runner._trim_onboarding(digest, budget_chars=140)
    assert "TRIMMED at its 140-char budget" in out
    assert "DROPPED ALPHA" in out and "DROPPED BETA" in out
    assert "knowledge_boot" in out, "the trim must carry a pull pointer, never a dead end"
    assert "trimmed to keep bus replies lean" not in out, "the silent-cut string is retired"


# ------------------------------------------------------------- W2: private scratchpad
class _FakeDecision:
    def __init__(self, title, decision, superseded=False):
        self.title, self.decision, self.superseded = title, decision, superseded


class _FakeMemory:
    def __init__(self):
        self.notes = []

    def decide_with_retry(self, title, decision, **kw):
        self.notes.append(_FakeDecision(title, decision))
        return f"dec_{len(self.notes)}"

    def get_decisions(self, days=30, include_superseded=False):
        return list(self.notes)


def _toolbox():
    return dc.ToolBox(Path("E:/AI-Setup"), allow_exec=False, trust=False, allow_secrets=False,
                      confirm=lambda _p: False, agent_id="testagent")


def test_memory_note_and_recall_roundtrip(monkeypatch):
    import core.learning.agent_memory as am
    fake = _FakeMemory()
    monkeypatch.setattr(am, "get_agent_memory", lambda *a, **k: fake)
    tb = _toolbox()
    out = tb.memory_note("t039 reviews", "start at packet_spec.py")
    assert "noted" in out
    assert fake.notes[0].title == "scratch:testagent:t039 reviews"
    listing = tb.memory_recall()
    assert "t039 reviews: start at packet_spec.py" in listing
    assert "scratch:testagent:" not in listing, "render strips the namespace prefix"


def test_memory_recall_empty_teaches(monkeypatch):
    import core.learning.agent_memory as am
    monkeypatch.setattr(am, "get_agent_memory", lambda *a, **k: _FakeMemory())
    assert "memory_note" in _toolbox().memory_recall()


# ------------------------------------------------------------------ W3: lock notes
def test_lock_note_rendered_in_holder():
    from core.comm.locks import LockManager
    lm = LockManager("t050-tester")
    if not lm.online:
        pytest.skip("redis not available")
    path = f"zz-t050-{uuid.uuid4().hex[:8]}.md"
    try:
        res = lm.acquire(path, ttl=30, note="pin probe: why-field")
        assert res["ok"]
        h = lm.holder(path)
        assert h and h.get("note") == "pin probe: why-field"
    finally:
        lm.release(path)


# ------------------------------------------------------------- W4: seat-path parity
def test_fast_seat_path_matches_wake_seat():
    from core.comm import wake_seat
    for sid in ("abc-123", None):
        assert bifrost_wake._hb_path_fast("claude", sid) == wake_seat.seat_path("claude", sid), \
            "fast path MUST mirror wake_seat.seat_path -- drift silently un-arms every session"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
