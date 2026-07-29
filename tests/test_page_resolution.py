"""PRE-REGISTERED ACCEPTANCE -- a page whose condition RESOLVED must stop shouting.

THE RECEIPT, and it is my own regression from the same night. The lane_stall page shipped
@8a8c213 fired correctly at 00:0x for claude (22 undrained) and deepseek (24 undrained). Both
lanes were drained within the hour. The pages kept rendering into EVERY UserPromptSubmit for the
next NINE HOURS ("529m ago"), because core/comm/pager.py only clears on an explicit, fleet-wide
ack_pages() and nothing ties an escalation to the condition that raised it.

That is precisely the failure deepseek argued about in the recall fence -- an agent that sees a
stale banner on every turn learns to ignore banners, and the habit outlasts the fix. An
escalation channel that cannot retract is a channel that trains people to ignore it, which
returns us to the 45-hour silence this whole arc exists to prevent.

ack_pages() is also all-or-nothing: acking the resolved claude page would have discarded
deepseek's live one. So "just ack it" is not a fix, it is a data-loss trade.

  P1  a page carries a stable key identifying (agent, state)
  P2  clearing one key leaves every other page standing
  P3  the doctor retracts its own escalation once the finding is gone
  P4  retraction also clears the dedup key, so a RECURRENCE pages immediately
  P5  reconciliation only touches agents actually examined
  P6  fail-open: a pager/Redis fault never breaks the doctor's round

Run: py -m pytest tests/test_page_resolution.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeRedis:
    def __init__(self):
        self.kv, self.lists = {}, {}
    def set(self, k, v, nx=False, ex=None):
        if nx and k in self.kv:
            return None
        self.kv[k] = v
        return True
    def get(self, k):
        return self.kv.get(k)
    def delete(self, *keys):
        n = 0
        for k in keys:
            n += 1 if (self.kv.pop(k, None) is not None or
                       self.lists.pop(k, None) is not None) else 0
        return n
    def keys(self, pattern="*"):
        pre = pattern.rstrip("*")
        return [k for k in list(self.kv) + list(self.lists) if k.startswith(pre)]
    def lpush(self, k, v):
        self.lists.setdefault(k, []).insert(0, v)
        return len(self.lists[k])
    def ltrim(self, k, a, b):
        self.lists[k] = self.lists.get(k, [])[a:b + 1]
    def lrange(self, k, a, b):
        L = self.lists.get(k, [])
        return L[a:] if b == -1 else L[a:b + 1]


@pytest.fixture()
def fake(monkeypatch):
    c = FakeRedis()
    monkeypatch.setenv("BIFROST_NAMESPACE", "t-pageres")
    monkeypatch.setattr("core.comm.doctor._client", lambda: c)
    return c


def _finding(agent="kimi", state="lane_stall"):
    return {"agent": agent, "state": state, "grade": "page",
            "line": f"{agent}: LANE STALL -- 55 undrained", "drill": f"py agent_cli.py unwedge {agent}"}


def test_p1_a_page_carries_its_identity(fake):
    from core.comm import pager
    pager.page("kimi", "stalled", c=fake, key="kimi:lane_stall")
    items = pager.unread_pages(c=fake)
    assert items and items[0].get("key") == "kimi:lane_stall", (
        "a page with no key cannot be retracted individually -- only fleet-wide ack, "
        "which discards other agents' live pages")


def test_p2_clearing_one_key_leaves_the_others(fake):
    from core.comm import pager
    pager.page("kimi", "stalled", c=fake, key="kimi:lane_stall")
    pager.page("deepseek", "stalled", c=fake, key="deepseek:lane_stall")
    pager.clear_key("kimi:lane_stall", c=fake)
    left = pager.unread_pages(c=fake)
    assert len(left) == 1 and left[0]["agent"] == "deepseek", (
        "retracting a resolved page must never discard a live one")


def test_p3_the_doctor_retracts_a_finding_that_is_gone(fake):
    """The whole point: escalate, then examine again with the condition resolved."""
    from core.comm import doctor, pager
    doctor._emit_pages([_finding()], notes=False)
    assert pager.unread_pages(c=fake), "precondition: the page was raised"
    doctor.examine_fleet(["kimi"], probes=_probes(), page_notes=False)
    assert not pager.unread_pages(c=fake), (
        "the condition resolved and the doctor kept shouting -- 9 hours of that is how a "
        "page channel becomes background noise")


def test_p4_a_recurrence_pages_immediately(fake):
    """Retraction must also clear the dedup key. Otherwise a stall that resolves and
    returns inside the hour is silent -- the worst case, because a flapping consumer is
    exactly what a human needs to see."""
    from core.comm import doctor, pager
    doctor._emit_pages([_finding()], notes=False)
    doctor.examine_fleet(["kimi"], probes=_probes(), page_notes=False)   # resolves
    doctor._emit_pages([_finding()], notes=False)                       # recurs
    assert pager.unread_pages(c=fake), (
        "a recurrence inside the dedup window was swallowed -- flapping is a signal, not noise")


def test_p5_reconciliation_only_touches_examined_agents(fake):
    from core.comm import doctor, pager
    doctor._emit_pages([_finding("deepseek")], notes=False)
    doctor.examine_fleet(["kimi"], probes=_probes(), page_notes=False)
    assert pager.unread_pages(c=fake), (
        "examining kimi retracted deepseek's page -- a fleet round must never clear an "
        "agent it did not look at")


def test_p6_a_pager_fault_never_breaks_the_round(monkeypatch):
    from core.comm import doctor

    class Hostile:
        def __getattr__(self, _):
            raise RuntimeError("redis down")

    monkeypatch.setattr("core.comm.doctor._client", lambda: Hostile())
    rep = doctor.examine_fleet(["kimi"], probes=_probes(), page_notes=False)
    assert "summary" in rep, "the doctor must render through its own escalation channel's outage"


def _ghost_page(fake, age_s: float, agent="claude#dead1234", state="hard_wedge"):
    """Plant a page whose subject has left the examinable universe, aged as given."""
    import json
    import time
    from core.comm import pager
    fake.lpush(pager._key(), json.dumps({
        "ts": time.time() - age_s, "agent": agent,
        "text": "HARD WEDGE -- worker died inside the turn", "key": f"{agent}:{state}"}))


def test_p7_ghost_page_for_vanished_subject_is_retracted(fake, monkeypatch):
    """[observed RED 2026-07-29] A page whose SUBJECT left the examinable universe
    (no worklive/runner/presence/recent-mail -> never in known_agents()) can never be
    re-examined, so the P5 scoping guard makes it IMMORTAL. Live receipt: the
    claude#b2a4c581 hard_wedge page rendered into every prompt whisper for 14+ hours
    after the incarnation's pulse expired. A FULL round must retract it once aged."""
    from core.comm import doctor, pager
    _ghost_page(fake, age_s=7200)
    monkeypatch.setattr(doctor, "known_agents", lambda: ["kimi"])
    doctor._reconcile_pages([], ["kimi"])          # scope covers the whole universe
    assert not pager.unread_pages(c=fake), (
        "a page for a vanished incarnation survived a full round -- the scoping guard "
        "has become an immortality clause; this exact ghost haunted every whisper for 14h")


def test_p8_fresh_ghost_page_survives_the_age_gate(fake, monkeypatch):
    """A subject can drop out of the universe transiently (pulse TTL flap, runner
    restart window). The ghost clause must wait out GHOST_PAGE_AGE_S before retracting."""
    from core.comm import doctor, pager
    _ghost_page(fake, age_s=60)
    monkeypatch.setattr(doctor, "known_agents", lambda: ["kimi"])
    doctor._reconcile_pages([], ["kimi"])
    assert pager.unread_pages(c=fake), (
        "a seconds-old page was retracted as a ghost -- the age gate must protect "
        "subjects in a transient presence gap")


def test_p9_partial_round_never_retracts_ghosts(fake, monkeypatch):
    """P5 extended: only a round that examined the WHOLE known universe can declare a
    subject universe-absent. A single-agent round keeps its hands off, aged or not."""
    from core.comm import doctor, pager
    _ghost_page(fake, age_s=7200)
    monkeypatch.setattr(doctor, "known_agents", lambda: ["kimi", "deepseek"])
    doctor._reconcile_pages([], ["kimi"])          # partial: deepseek not examined
    assert pager.unread_pages(c=fake), (
        "a partial round retracted a ghost page -- universe-absence can only be judged "
        "by a round that looked at everything")


def _probes(**over):
    import time
    base = dict(
        worklive=lambda a: {"phase": "idle", "detail": "", "turn": 1,
                            "since_ts": time.time() - 5, "beat_ts": time.time() - 1},
        progress=lambda a: None,
        backlog=lambda a: 0,
        stalled_since=lambda a, present: None,
        halted=lambda a: None,
        lane_health=lambda a: None,
        token_cost=lambda a: None,
        bench_count=lambda a: 0,
        now=time.time(),
    )
    base.update(over)
    return base
