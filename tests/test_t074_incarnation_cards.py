"""T074 Phase 3 pins -- incarnation cards (W11-W12 of the reconciled build spec;
deepseek's sec. 4 governs: publish at SessionStart, refresh at stop-hook, TTL expiry,
claims from the ledger, live_incarnations() upgraded to read cards).

BUILD REFINEMENTS (flagged, T073 precedent):
  R9   Cards are NAMESPACE-prefixed ({BIFROST_NAMESPACE}:incarnation:<agent>:<sid>)
       like every other comm key -- a drill's cards never leak into the live fleet
       (T039 test-* discipline).
  R10  live_incarnations() MERGES cards with Phase-1 activity markers (cards win on
       a shared sid): a pre-Phase-3 live session has a marker but no card, and it
       must not vanish from SIBLINGS during the organic migration (R7 sibling).
  R11  Card status is derived at READ time: refreshed <5m ago = active, older = idle
       (spec: "idle when activity marker > 5 min stale"). The writer never guesses.
  R12  refresh_card on a MISSING card self-heals by publishing fresh (a Redis outage
       window must not leave a session cardless until restart).
"""
import fnmatch
import json
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import incarnation as inc


class FakeRedis:
    def __init__(self):
        self.kv, self.ex = {}, {}

    def set(self, k, v, ex=None):
        self.kv[k], self.ex[k] = v, ex
        return True

    def get(self, k):
        return self.kv.get(k)

    def delete(self, k):
        self.kv.pop(k, None), self.ex.pop(k, None)

    def scan_iter(self, match=None):
        return iter([k for k in list(self.kv) if match is None or fnmatch.fnmatch(k, match)])


SID = "aaaabbbb-1111-2222-3333-444455556666"
SID2 = "ccccdddd-1111-2222-3333-444455556666"


def _key(agent, sid):
    return f"bifrost:incarnation:{agent}:{sid}"


# ---------------------------------------------------------------- W11 publish + refresh
def test_w11_publish_writes_card_with_ttl_and_fields():
    c = FakeRedis()
    assert inc.publish_card("claude", SID, pid=4242, claims=["T074"], c=c) is True
    key = _key("claude", SID)
    assert key in c.kv, "R9: card key is namespace-prefixed bifrost:incarnation:<agent>:<sid>"
    assert c.ex[key] == inc.CARD_TTL_SEC == 1800, "W12: the 30-min TTL IS the expiry contract"
    card = json.loads(c.kv[key])
    for field in ("session_id", "pid", "started", "refreshed", "claims", "status"):
        assert field in card, f"W11: card missing {field}"
    assert card["session_id"] == SID and card["pid"] == 4242 and card["claims"] == ["T074"]


def test_w11_refresh_preserves_started_resets_ttl():
    c = FakeRedis()
    inc.publish_card("claude", SID, claims=["T074"], c=c)
    key = _key("claude", SID)
    started = json.loads(c.kv[key])["started"]
    c.ex[key] = 60                       # simulate an aged TTL
    assert inc.refresh_card("claude", SID, c=c) is True
    card = json.loads(c.kv[key])
    assert card["started"] == started, "refresh keeps the birth stamp"
    assert card["claims"] == ["T074"], "refresh keeps claims unless given new ones"
    assert c.ex[key] == inc.CARD_TTL_SEC, "W11: every stop-hook firing re-arms the TTL"


def test_r12_refresh_self_heals_missing_card():
    c = FakeRedis()
    assert inc.refresh_card("claude", SID, c=c) is True
    assert _key("claude", SID) in c.kv, "R12: a lost card is republished at the next stop"


def test_w11_no_redis_fails_soft():
    assert inc.publish_card("claude", SID, c=None, allow_fallback=False) is False
    assert inc.refresh_card("claude", SID, c=None, allow_fallback=False) is False


# ---------------------------------------------------------------- R11 derived status
def test_r11_status_derived_at_read_time():
    c = FakeRedis()
    inc.publish_card("claude", SID, claims=[], c=c)
    fresh = inc.read_cards("claude", c=c)
    assert fresh and fresh[0]["status"] == "active"
    # age the refresh stamp 6 minutes
    key = _key("claude", SID)
    card = json.loads(c.kv[key])
    card["refreshed"] = (datetime.now() - timedelta(minutes=6)).strftime("%Y-%m-%dT%H:%M:%S")
    c.kv[key] = json.dumps(card)
    aged = inc.read_cards("claude", c=c)
    assert aged[0]["status"] == "idle", "R11: >5m without a hook firing reads as idle"


# ---------------------------------------------------------------- R10 merge with markers
def _touch_marker(tmp, agent, sid, age_s=0.0):
    p = os.path.join(tmp, f"bifrost_wake_{agent}_{sid}.alive")
    with open(p, "w") as f:
        f.write(str(time.time() - age_s))


def test_r10_cards_merge_with_markers_cards_win(tmp_path):
    c = FakeRedis()
    tmp = str(tmp_path)
    inc.publish_card("claude", SID, claims=["T074"], c=c)      # card + marker for SID
    _touch_marker(tmp, "claude", SID, age_s=60)
    _touch_marker(tmp, "claude", SID2, age_s=60)               # marker-only sibling (pre-P3 session)
    out = inc.live_incarnations("claude", tmp=tmp, c=c)
    sids = {o["session_id"] for o in out}
    assert sids == {SID, SID2}, "R10: the migration window keeps marker-only sessions visible"
    carded = next(o for o in out if o["session_id"] == SID)
    assert carded.get("status") == "active" and carded.get("claims") == ["T074"], \
        "R10: where both exist, the CARD's richer fields win"


def test_r10_own_session_excluded_from_cards(tmp_path):
    c = FakeRedis()
    inc.publish_card("claude", SID, c=c)
    out = inc.live_incarnations("claude", my_session=SID, tmp=str(tmp_path), c=c)
    assert out == []


def test_r10_no_redis_falls_back_to_markers(tmp_path):
    tmp = str(tmp_path)
    _touch_marker(tmp, "claude", SID2, age_s=30)
    out = inc.live_incarnations("claude", tmp=tmp, c=None, allow_fallback=False)
    assert [o["session_id"] for o in out] == [SID2], "Phase-1 marker path survives a dead bus"
