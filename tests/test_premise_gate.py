"""Premise-gate pins — the settled-ask short-circuit (frugality made mechanical).

Born 2026-07-21 night: the runner's backlog discharge answered superseded asks at full
agentic depth (the RECIPE/MACRO inversion was born in exactly that burn). The gate:
an ask PAST THE AGE FLOOR whose named T-numbers are ALL ledger-settled earns one
settled-line reply (with the RB-29 answers-link) instead of a full answer.

Laws:
  G1  settled_tasks partitions named T-numbers: settled ('T075 PARKED') vs live;
      unknown ids read LIVE (fail toward answering); no ids -> ([], [])
  G2  premise_settled fires ONLY on: ask-kind + past age floor + >=1 named + ALL
      settled; fresh asks, live-naming asks, non-asks, disabled gate -> []
  G3  ledger unreachable -> [] (fail-open to answering, never to silence)
  (W04's directive cross-check now rides the same helper -- its own pins re-run
   with this suite as the refactor guard.)
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import task_ledger as tl

TWO_H = 2 * 3600 * 1000


@pytest.fixture()
def ledger(monkeypatch):
    monkeypatch.setattr(tl, "state_view", lambda *a, **k: {
        "done": [{"id": "T075", "status": "done"}],
        "parked": [{"id": "T080", "status": "parked"}],
        "active": [{"id": "T099", "status": "claimed"}],
    })


def test_g1_partition(ledger):
    settled, live = tl.settled_tasks("re T075 and T080 please advise, also T099")
    assert settled == ["T075 DONE", "T080 PARKED"] and live == ["T099"]
    settled, live = tl.settled_tasks("what about T123?")
    assert settled == [] and live == ["T123"], "unknown ids read LIVE"
    assert tl.settled_tasks("no task numbers here") == ([], [])


def test_g2_verdict_fires_only_on_stale_all_settled(ledger):
    old, fresh = TWO_H + 60_000, 60_000
    assert tl.premise_settled("question", old, "approve T075 and T080",
                              min_age_ms=TWO_H) == ["T075 DONE", "T080 PARKED"]
    assert tl.premise_settled("question", old, "T075 vs T099?", min_age_ms=TWO_H) == [], \
        "one live named task -> answer normally"
    assert tl.premise_settled("question", fresh, "approve T075", min_age_ms=TWO_H) == [], \
        "a FRESH ask about closed work is deliberate -- answer it"
    assert tl.premise_settled("inform", old, "T075", min_age_ms=TWO_H) == [], \
        "non-ask kinds never gate"
    assert tl.premise_settled("question", old, "T075", min_age_ms=0) == [], \
        "min_age 0 disables the gate"
    assert tl.premise_settled("question", None, "T075", min_age_ms=TWO_H) == [], \
        "unknowable age reads FRESH (fail toward answering)"
    assert tl.premise_settled("question", old, "no tasks named", min_age_ms=TWO_H) == []


def test_g3_ledger_down_fails_open(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("redis down")
    monkeypatch.setattr(tl, "state_view", boom)
    assert tl.settled_tasks("T075") == ([], [])
    assert tl.premise_settled("question", TWO_H * 2, "T075", min_age_ms=TWO_H) == []
