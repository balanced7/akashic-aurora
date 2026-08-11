"""T282: a dead incarnation's page must retract on SUCCESSION, not haunt the hour.

WHAT HAPPENED, night of 2026-08-10/11. Three seats cycled normally (kimi#34876 -> #10648 ->
#60900, deepseek#63940 -> #58820 -> #67664). Each death looks exactly like a hard wedge at the
emission site -- pulse dies (5s TTL), seat beat goes stale (45s), while the worklive record
lingers with a non-idle phase -- so the doctor paged HARD WEDGE into each seat's wake. The
dead incarnation then decayed out of known_agents() within a minute, which pushed every page
behind the GHOST_PAGE_AGE_S (1h) gate: unretractable, rendered into every prompt whisper,
6+ times per page. kimi's cross-seat diagnosis named the stake: "a page that fires on healthy
seats trains us to ignore pages."

THE FIX. Succession is the strongest resolution evidence there is: when a round examines a
DIFFERENT live incarnation of the same base agent, any page keyed to an older incarnation of
that base retracts immediately -- no age gate. The true-ghost path (a base with NO successor)
is deliberately untouched: those pages still stand until the ghost gate, because a seat that
dies WITHOUT succession is exactly what the pager exists to say.

Pins:
  P1 (RED first)  succession retracts: page for kimi#old, scope holds kimi#new -> cleared
  P2 (guard)      no successor -> the page STANDS inside the ghost window (pager still fires)
  P3 (guard)      keyless pages are never touched by reconciliation
  P4 (structural) the hard_wedge page text names the signals it keyed on (pulse / beat / phase)

Run: py -m pytest tests/test_t282_succession_retracts_page.py -q
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import doctor, pager  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


class FakeRedis:
    def __init__(self):
        self.lists = {}
        self.kv = {}
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
        self.kv.pop(k, None)
    def set(self, k, v, nx=False, ex=None):
        if nx and k in self.kv:
            return None
        self.kv[k] = v
        return True


def _page_for(c, agent, state="hard_wedge", age_s=300):
    """Seed a page the way the doctor emits one: keyed, recent."""
    assert pager.page(agent, f"HARD WEDGE -- synthetic ({agent})", c=c,
                      key=f"{agent}:{state}")
    # backdate: reconciliation reads ts from the record
    raw = c.lists[pager._key()][0]
    rec = json.loads(raw)
    rec["ts"] = time.time() - age_s
    c.lists[pager._key()][0] = json.dumps(rec)


def _keys(c):
    return [json.loads(r).get("key") for r in c.lists.get(pager._key(), [])]


def test_p1_succession_retracts(monkeypatch):
    """RED first: successor incarnation in scope -> the old incarnation's page clears."""
    c = FakeRedis()
    _page_for(c, "kimi#10648-ki", age_s=300)          # 5 minutes old: inside the ghost gate
    monkeypatch.setattr(doctor, "_client", lambda: c)
    monkeypatch.setattr(doctor, "known_agents",
                        lambda: ["kimi#60900-ki", "claude#af0ca6b8"])
    doctor._reconcile_pages(pages=[], agents=["kimi#60900-ki", "claude#af0ca6b8"])
    assert "kimi#10648-ki:hard_wedge" not in _keys(c), (
        "P1: a live successor incarnation of the same base agent was examined this round; "
        "the dead predecessor's page must retract NOW, not after GHOST_PAGE_AGE_S")


def test_p2_no_successor_page_stands(monkeypatch):
    """A true ghost (no successor) keeps its page inside the ghost window."""
    c = FakeRedis()
    _page_for(c, "deepseek#63940-de", age_s=300)
    monkeypatch.setattr(doctor, "_client", lambda: c)
    monkeypatch.setattr(doctor, "known_agents", lambda: ["claude#af0ca6b8"])
    doctor._reconcile_pages(pages=[], agents=["claude#af0ca6b8"])
    assert "deepseek#63940-de:hard_wedge" in _keys(c), (
        "P2: no successor examined -- the page must STAND (the pager still fires for real "
        "unsucceeded deaths inside the ghost window)")


def test_p3_keyless_untouched(monkeypatch):
    c = FakeRedis()
    assert pager.page("gauge", "storm", c=c)          # keyless, legacy form
    monkeypatch.setattr(doctor, "_client", lambda: c)
    monkeypatch.setattr(doctor, "known_agents", lambda: ["claude#af0ca6b8"])
    doctor._reconcile_pages(pages=[], agents=["claude#af0ca6b8"])
    assert len(c.lists.get(pager._key(), [])) == 1, "P3: keyless pages are never reconciled away"


def test_p4_page_text_names_its_signals():
    """Acceptance (T282): 'the detector names WHICH signal it keyed on in every page'."""
    src = io.open(ROOT / "core" / "comm" / "doctor.py", encoding="utf-8").read()
    i = src.find('"hard_wedge", "page"')
    assert i > 0, "P4: hard_wedge page emission site missing"
    body = src[i:i + 500]
    for marker in ("pulse", "beat", "phase"):
        assert marker in body, (
            f"P4: the hard_wedge page body must name the '{marker}' signal it keyed on -- "
            "a page that does not show its evidence cannot be recalibrated, only ignored")
