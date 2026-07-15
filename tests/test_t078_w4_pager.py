"""T078-W4 PRE-REGISTERED ACCEPTANCE -- the page surface (the 6h-invisible killer).

Spec: t078 reconciliation W4 (claude builds, deepseek verifies). A PAGE is a
page-grade finding (breaker trip, runner down >10m, storm gauge) that must reach
a HUMAN, not a bus reader. v1 channel: daemon/doctor writers -> one Redis list ->
the UserPromptSubmit hook injects [PAGE] lines into any live seat, whose doctrine
is to relay via PushNotification (harness tool, seat-side). The unattended path
(no live seat) is wave-2's scheduled-session anchor -- documented, not faked.

Pins:
  P1  page() appends {ts, agent, text} to <ns>:pages; capped at 50 (oldest drop)
  P2  unread_pages() returns newest-first and does NOT consume
  P3  ack_pages() clears; idempotent on empty
  P4  hook_lines() renders '[PAGE] agent: text (age)' lines, empty when none
  P5  page() is fail-open: no client -> False, never raises

Run: py -m pytest tests/test_t078_w4_pager.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.comm import pager
except ImportError:
    pager = None


def _built():
    assert pager is not None, "W4 build target core/comm/pager.py missing (RED until built)"


class FakeRedis:
    def __init__(self):
        self.lists = {}
    def lpush(self, k, v):
        self.lists.setdefault(k, []).insert(0, v)
        return len(self.lists[k])
    def ltrim(self, k, a, b):
        self.lists[k] = self.lists.get(k, [])[a:b + 1]
    def lrange(self, k, a, b):
        L = self.lists.get(k, [])
        return L[a:] if b == -1 else L[a:b + 1]
    def delete(self, k):
        self.lists.pop(k, None)


def test_p1_p2_append_capped_and_peek():
    _built()
    c = FakeRedis()
    for i in range(55):
        assert pager.page("deepseek", f"finding {i}", c=c)
    items = pager.unread_pages(c=c)
    assert len(items) == 50, "P1: capped at 50"
    assert items[0]["text"] == "finding 54", "P2: newest first"
    assert pager.unread_pages(c=c), "P2: peek does not consume"


def test_p3_ack_clears_idempotent():
    _built()
    c = FakeRedis()
    pager.page("a", "x", c=c)
    assert pager.ack_pages(c=c) is True
    assert pager.unread_pages(c=c) == []
    assert pager.ack_pages(c=c) is True, "P3: idempotent on empty"


def test_p4_hook_lines_render():
    _built()
    c = FakeRedis()
    assert pager.hook_lines(c=c) == []
    pager.page("deepseek", "runner down 12m", c=c)
    lines = pager.hook_lines(c=c)
    assert len(lines) == 1 and "[PAGE]" in lines[0] and "runner down 12m" in lines[0]


def test_p5_fail_open():
    _built()
    assert pager.page("a", "x", c=None, allow_fallback=False) is False
