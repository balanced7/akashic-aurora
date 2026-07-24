"""T075 M1-BETA PRE-REGISTERED ACCEPTANCE -- the clean-death trio at SessionEnd.

Spec: docs/library/report/20260715_t060-m1-continuous-presence-reconciliati_32cac4.md ruling 3 + slice table
M1-beta (claude builds, deepseek verifies): a session that ends CLEANLY releases,
in the same breath, (1) its consumer SEAT, (2) its incarnation CARD, (3) its wake
LISTENER's seat file + activity marker. TTL expiry stays the CRASH net -- the trio
only makes the clean path instant. REGRESSION STORY: the 2026-07-15 ~03:xx thirty-
minute seat shadow (receipt f9207c90) -- a dead session's SESSION_CONSUMER_TTL seat
blocked its successor for up to 30 minutes.

Committed RED before core/comm/session_exit.py exists (method baseline).

Design binds pinned here (flagged for deepseek's verify, T073 precedent):
  B-a  The trio lives in core/comm/session_exit.clean_death(agent, sid, event=...)
       and the EVENT GUARD lives inside it: only event='SessionEnd' acts --
       PreCompact means the session CONTINUES (the hook passes its event through,
       so the guard is pinnable in-process instead of trusting hook wiring).
  B-b  Listener stand-down is FILE REMOVAL, never a kill: bifrost_wake's own
       seat-lost path ('heartbeat file gone') turns removal into a benign exit at
       the watcher's next check (displacement doctrine, wake_seat K-laws).
  B-c  Kill switch AKASHIC_CLEAN_DEATH=0 (ruling 4's first-week hatch pattern).
  B-d  Every leg only ever touches ITS OWN session's artifacts (token match /
       exact card key / exact file names) -- sibling sessions are untouchable.

Run: py -m pytest tests/test_t075_m1_beta_clean_death.py -q   (no live Redis needed)
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.comm import session_exit
except ImportError:
    session_exit = None

from core.comm import incarnation as inc
from core.comm import runner_lock
from core.comm import wake_seat

SID = "aaaabbbb-1111-2222-3333-444455556666"
SID2 = "ccccdddd-7777-8888-9999-000011112222"
AGENT = "t075beta"


class FakeRedis:
    """T074's fake + the nx/ex/incr the lock path needs."""

    def __init__(self):
        self.kv, self.ex, self.counters = {}, {}, {}

    def set(self, k, v, ex=None, nx=False):
        if nx and k in self.kv:
            return None
        self.kv[k], self.ex[k] = v, ex
        return True

    def get(self, k):
        return self.kv.get(k)

    def delete(self, k):
        self.kv.pop(k, None), self.ex.pop(k, None)

    def incr(self, k):
        self.counters[k] = self.counters.get(k, 0) + 1
        return self.counters[k]

    def scan_iter(self, match=None):
        import fnmatch
        return iter([k for k in list(self.kv) if match is None or fnmatch.fnmatch(k, match)])


@pytest.fixture
def fake(monkeypatch):
    """One fake bus client wired into BOTH the lock module and the card door."""
    c = FakeRedis()
    monkeypatch.setattr(runner_lock, "_client", lambda: c)
    monkeypatch.delenv("AKASHIC_CLEAN_DEATH", raising=False)
    monkeypatch.setenv("BIFROST_NAMESPACE", "bifrost")   # deterministic key text
    return c


def _built():
    assert session_exit is not None, \
        "M1-beta build target core/comm/session_exit.py does not exist yet (RED until built)"


def _seat_key():
    return f"bifrost:runner:{AGENT}"


# --------------------------------------------------------------- B1 + B7 (the shadow dies)
def test_b1_own_seat_released_and_successor_claims_instantly(fake, tmp_path):
    _built()
    tok = f"session:{SID}"
    ok, gen, _ = runner_lock.claim_consumer(AGENT, tok)
    assert ok and fake.get(_seat_key()), "fixture: session must hold the seat first"
    out = session_exit.clean_death(AGENT, SID, tmp=str(tmp_path), c=fake, event="SessionEnd")
    assert out.get("seat") is True, f"B1: held seat not released: {out}"
    assert fake.get(_seat_key()) is None, "B1: seat key still present after clean death"
    ok2, gen2, _ = runner_lock.claim_consumer(AGENT, f"session:{SID2}")
    assert ok2 and gen2 > gen, \
        "B7: successor must claim INSTANTLY after a clean death (the f9207c90 30-min shadow)"


# --------------------------------------------------------------- B2 (foreign seat untouched)
def test_b2_foreign_seat_untouched(fake, tmp_path):
    _built()
    foreign = f"session:{SID2}"
    assert runner_lock.claim_consumer(AGENT, foreign)[0]
    before = fake.get(_seat_key())
    out = session_exit.clean_death(AGENT, SID, tmp=str(tmp_path), c=fake, event="SessionEnd")
    assert out.get("seat") is False, "B2: trio claimed to release a seat it never held"
    assert fake.get(_seat_key()) == before, "B2: foreign session's seat was touched (B-d violation)"


# --------------------------------------------------------------- B3 (own card only)
def test_b3_own_card_deleted_sibling_card_kept(fake, tmp_path):
    _built()
    inc.publish_card(AGENT, SID, pid=111, c=fake)
    inc.publish_card(AGENT, SID2, pid=222, c=fake)
    out = session_exit.clean_death(AGENT, SID, tmp=str(tmp_path), c=fake, event="SessionEnd")
    assert out.get("card") is True
    keys = list(fake.scan_iter(match=f"bifrost:incarnation:{AGENT}:*"))
    assert keys == [f"bifrost:incarnation:{AGENT}:{SID2}"], \
        f"B3: exactly the sibling's card must survive, got {keys}"


# --------------------------------------------------------------- B4 (listener files, own only)
def test_b4_listener_seat_and_marker_removed_own_session_only(fake, tmp_path):
    _built()
    tmp = str(tmp_path)
    for sid in (SID, SID2):
        with open(wake_seat.seat_path(AGENT, sid, tmp), "w") as f:
            f.write("12345")
        wake_seat.touch_activity(AGENT, sid, tmp)
    out = session_exit.clean_death(AGENT, SID, tmp=tmp, c=fake, event="SessionEnd")
    assert out.get("listener") is True and out.get("marker") is True
    assert not os.path.exists(wake_seat.seat_path(AGENT, SID, tmp)), \
        "B4: own wake seat file must be removed (B-b stand-down by displacement)"
    assert not os.path.exists(wake_seat.activity_marker_path(AGENT, SID, tmp)), \
        "B4: own activity marker must be removed (no sibling ghosts)"
    assert os.path.exists(wake_seat.seat_path(AGENT, SID2, tmp)), \
        "B4: SIBLING session's seat file was touched (B-d violation)"
    assert os.path.exists(wake_seat.activity_marker_path(AGENT, SID2, tmp))


# --------------------------------------------------------------- B5 (PreCompact = continue)
def test_b5_precompact_never_acts(fake, tmp_path):
    _built()
    tok = f"session:{SID}"
    runner_lock.claim_consumer(AGENT, tok)
    inc.publish_card(AGENT, SID, c=fake)
    out = session_exit.clean_death(AGENT, SID, tmp=str(tmp_path), c=fake, event="PreCompact")
    assert out.get("disabled") is True, "B5/B-a: a PreCompact must never run the trio"
    assert fake.get(_seat_key()) and fake.get(f"bifrost:incarnation:{AGENT}:{SID}"), \
        "B5: PreCompact released living resources -- the session was still running"


# --------------------------------------------------------------- B6 (kill switch)
def test_b6_kill_switch(fake, tmp_path, monkeypatch):
    _built()
    monkeypatch.setenv("AKASHIC_CLEAN_DEATH", "0")
    runner_lock.claim_consumer(AGENT, f"session:{SID}")
    out = session_exit.clean_death(AGENT, SID, tmp=str(tmp_path), c=fake, event="SessionEnd")
    assert out.get("disabled") is True and fake.get(_seat_key()), \
        "B6/B-c: AKASHIC_CLEAN_DEATH=0 must be a total no-op"


# --------------------------------------------------------------- provenance is auditable
def test_provenance_line_appended(fake, tmp_path):
    _built()
    tmp = str(tmp_path)
    session_exit.clean_death(AGENT, SID, tmp=tmp, c=fake, event="SessionEnd")
    log = wake_seat.provenance_path(AGENT, tmp)
    assert os.path.exists(log), "clean death must leave an auditable provenance line"
    body = open(log, encoding="utf-8").read()
    assert "clean-death" in body and SID[:8] in body
