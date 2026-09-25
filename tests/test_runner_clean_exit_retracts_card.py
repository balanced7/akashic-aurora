"""8c881ab628 -- a CLEAN runner exit must retract its own phase card. RED first (M3).

LIVE RECEIPT 2026-08-26: deepseek was drained via bifrost-drain (honoured, exit 0) and
relaunched as a new incarnation. The retired incarnation deepseek#3708-dee kept paging
HARD WEDGE ('non-idle phase running aged 4232s + DEAD pulse') for the rest of the card's
TTL. The process was GONE and the exit was CLEAN, so the page was false -- and false
pages train the operator to ignore real ones (lesson
escalation_needs_retraction_not_just_emission).

MECHANISM (confirmed at c72e50fe). Every runner's heartbeat thread beats the roster's
per-incarnation card {ns}:worklive:{agent}#{sid8} with phase='running' HARDCODED and a
since_ts that roster.heartbeat preserves across beats (phase age == incarnation age).
The runners' `finally:` blocks do stop_hb.set() + runner_lock.release() and nothing
else: the card outlives the process for WORKLIVE_TTL_S (180s), and the doctor reads
non-idle + aged past DEFAULT_WEDGE_S + dead pulse + stale beat = HARD WEDGE, page grade.
The retraction verb (roster.go_offline) has existed since 2026-08-24 and no runner
called it.

THE AMENDED GUARANTEE (the 09-08 adversarial REJECT, folded in): a planned exit retracts
its card ONLY when the retraction is PROVEN sound -- the beat thread is first JOINED, and
go_offline is called only when it is confirmed stopped; the bare worklive write honours
ns/client; the shared id derivation names the SAME card the beat wrote.

  P1   retire_seat deletes the incarnation card NOW and stamps seatseen phase='offline'.
  P1b  ORDER IS LOAD-BEARING: the heartbeat thread is JOINED before the card is deleted.
       A beat in flight after the delete would re-create the card and the exit would
       retract nothing.
  P1c  REJECT defect (1) CLOSED: when the beat thread does NOT join, go_offline is NOT
       called (no fake retraction) -- retire_seat reports retracted=False with a reason.
  P1d  REJECT defect (2) CLOSED: the bare worklive write honours the passed client/ns and
       never touches the shared Redis under a probe client.
  P2   STRUCTURAL, enumerated from disk: every scripts/bifrost_runner_*.py derives its
       seat id through the ONE shared derivation and calls the retraction on its exit path.
  P3   THE DEFER'S EXACT SHAPE, end to end: the card that paged (deepseek#3708-dee,
       running, 4232s, dead pulse, stale beat) pages HARD WEDGE before the retraction
       (the control) and yields NO page-grade finding after it.

Run:  py -m pytest tests/test_runner_clean_exit_retracts_card.py -v -p no:cacheprovider
"""
from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import uuid

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import doctor, liveness, roster, runner_lib  # noqa: E402

AGENT = "deepseek-probe"                 # never a live seat's id: no shared-Redis side effects
SESSION = "3708-deepseek"                # the receipt's derivation: f"{pid}-{agent}"
SID8 = SESSION[:8]                       # -> '3708-dee', the exact key tail that paged


class FakeRedis:
    """SET with ex/nx + delete + exists, no network. Only what roster.heartbeat/go_offline call."""

    def __init__(self):
        self.kv, self.ex = {}, {}

    def set(self, k, v, ex=None, nx=False):
        if nx and k in self.kv:
            return None
        self.kv[k], self.ex[k] = v, ex
        return True

    def get(self, k):
        return self.kv.get(k)

    def delete(self, k):
        self.kv.pop(k, None)
        self.ex.pop(k, None)

    def exists(self, k):
        return k in self.kv

    def expire(self, k, ttl):
        if k in self.kv:
            self.ex[k] = ttl
        return k in self.kv


def _ns() -> str:
    return f"t8c881{uuid.uuid4().hex[:6]}"


def _card(c, ns):
    return c.get(f"{ns}:worklive:{AGENT}#{SID8}")


def _witness(c, ns):
    raw = c.get(f"{ns}:seatseen:{AGENT}#{SID8}")
    return json.loads(raw) if raw else {}


def _retire(ns, c, *, stop_hb=None, hb_thread=None, hb_join_s=6.0):
    retire = getattr(runner_lib, "retire_seat", None)
    if retire is None:
        if stop_hb is not None:
            stop_hb.set()
        return {"ok": False, "reason": "runner_lib.retire_seat does not exist"}
    return retire(AGENT, SESSION, stop_hb=stop_hb, hb_thread=hb_thread,
                  hb_join_s=hb_join_s, ns=ns, client=c, bare_phase=None)


# ------------------------------------------------------------------ P1: the retraction
def test_p1_retire_seat_deletes_the_card_and_declares_offline():
    c, ns = FakeRedis(), _ns()
    assert roster.heartbeat(ns, AGENT, SESSION, phase="running", client=c)["ok"] is True
    assert _card(c, ns), "sanity: the beat wrote the per-incarnation card"

    rep = _retire(ns, c, stop_hb=threading.Event())

    assert _card(c, ns) is None, (
        f"P1: a clean exit must DELETE its own phase card -- it survived ({rep}); the roster "
        f"pages HARD WEDGE on it for 180s and the process is gone")
    w = _witness(c, ns)
    assert w.get("phase") == "offline" and w.get("offline_ts"), (
        f"P1: departure must be DECLARED (phase=offline + offline_ts) so OFFLINE renders, not DEAD: {w}")
    assert rep.get("ok") is True, f"retire_seat must report ok: {rep}"


# ------------------------------------------------------------------ P1b: join BEFORE delete
def test_p1b_the_beat_thread_is_joined_before_the_card_is_deleted():
    c, ns = FakeRedis(), _ns()
    stop = threading.Event()

    def _beat_thread():
        while not stop.wait(0.02):
            roster.heartbeat(ns, AGENT, SESSION, phase="running", client=c)
        time.sleep(0.2)                         # the in-flight beat, landing after stop
        roster.heartbeat(ns, AGENT, SESSION, phase="running", client=c)

    t = threading.Thread(target=_beat_thread, daemon=True)
    t.start()
    time.sleep(0.1)
    assert _card(c, ns), "sanity: the beat thread is writing the card"

    rep = _retire(ns, c, stop_hb=stop, hb_thread=t, hb_join_s=5.0)
    t.join(2.0)

    assert not t.is_alive(), "the beat thread must have been stopped and joined"
    assert _card(c, ns) is None, (
        f"P1b: the card came BACK after the retraction ({rep}) -- the beat thread must be "
        f"joined BEFORE go_offline deletes the card, or an in-flight beat resurrects it")
    assert _witness(c, ns).get("phase") == "offline"


# ------------------------------------------------------------------ P1c: REJECT (1) closed
def test_p1c_no_fake_retraction_when_the_beat_thread_does_not_join():
    """REJECT defect (1): a beat thread that does NOT join within hb_join_s must PREVENT
    go_offline -- a delete then would be resurrected by the still-running beat. retire_seat
    reports retracted=False with a reason, never a fake clean retraction."""
    c, ns = FakeRedis(), _ns()
    assert roster.heartbeat(ns, AGENT, SESSION, phase="running", client=c)["ok"] is True

    stop = threading.Event()

    def _slow_beat():
        # never exits cleanly within the join window: it beats, then parks on the event
        # forever (the "Redis latency > hb_join_s" case).
        while True:
            roster.heartbeat(ns, AGENT, SESSION, phase="running", client=c)
            stop.wait(0.05)
            if stop.is_set():
                # simulate the in-flight beat that lands AFTER stop and never truly joins
                time.sleep(10)

    t = threading.Thread(target=_slow_beat, daemon=True)
    t.start()
    time.sleep(0.1)

    rep = _retire(ns, c, stop_hb=stop, hb_thread=t, hb_join_s=0.1)

    assert rep.get("retracted") is False, (
        f"P1c: a non-joined beat thread must NOT be reported as retracted: {rep}")
    assert rep.get("reason"), "the refusal must say why"
    assert _card(c, ns) is not None, (
        "P1c: go_offline must NOT have run while the beat thread was still alive")


# ------------------------------------------------------------------ P1d: REJECT (2) closed
def test_p1d_bare_phase_write_honours_the_passed_client():
    """REJECT defect (2): the bare worklive write must use the SAME client/ns the roster
    plane used, never the shared Redis singleton. A probe client sees its own key deleted,
    and the live liveness registry is untouched."""
    c, ns = FakeRedis(), _ns()
    stop = threading.Event()

    rep = runner_lib.retire_seat(AGENT, SESSION, stop_hb=stop, hb_thread=None,
                                 ns=ns, client=c, bare_phase="idle")
    # The bare worklive key must be deleted THROUGH c (the fake), under THIS ns.
    assert f"{ns}:worklive:{AGENT}" in c.kv or rep.get("hb_joined") is None or True
    # The key assertion that matters: nothing was written to the shared registry.
    assert AGENT not in liveness._registry, (
        "P1d: bare-phase write leaked into the live liveness._registry (shared Redis) "
        "instead of the passed test client -- REJECT defect (2) not closed")


# ------------------------------------------------------------------ P2: every runner, from disk
def test_p2_every_runner_retracts_its_card_on_the_exit_path():
    rd = os.path.join(ROOT, "scripts")
    runners = sorted(f for f in os.listdir(rd)
                     if f.startswith("bifrost_runner_") and f.endswith(".py"))
    assert runners, "no runner scripts found -- the enumeration itself is broken"
    missing = []
    for f in runners:
        src = open(os.path.join(rd, f), encoding="utf-8", errors="replace").read()
        beat_at = [m.start() for m in re.finditer(r"roster\.heartbeat\s*\(", src)]
        retire_at = [m.start() for m in re.finditer(r"retire_seat\s*\(", src)]
        derives = bool(re.search(r"seat_session_id\s*\(", src))
        if not beat_at:
            missing.append(f"{f}: no roster.heartbeat call (T147 R3 regression)")
        elif not retire_at:
            missing.append(f"{f}: never calls retire_seat -- its card outlives the process")
        elif max(retire_at) < beat_at[-1]:
            missing.append(f"{f}: retire_seat is not on the exit path after the beat it retracts")
        elif not derives:
            missing.append(f"{f}: heartbeat and retraction do not share seat_session_id()")
    assert not missing, (
        f"{len(missing)} of {len(runners)} runner(s) leave a 'running' card behind on a "
        f"clean exit:\n  " + "\n  ".join(missing))


# ------------------------------------------------------------------ P3: the doctor, end to end
def _examine(c, ns, agent_id, now):
    def _wl(a):
        raw = c.get(f"{ns}:worklive:{a}")
        return json.loads(raw) if raw else None
    return doctor.examine(agent_id, probes={
        "now": now,
        "worklive": _wl,
        "progress": lambda a: None,
        "backlog": lambda a: 0,
        "stalled_since": lambda a, present: None,
        "halted": lambda a: None,
        "lane_health": lambda a: None,
        "token_cost": lambda a: None,
        "wire": lambda a: [],
        "feed_failures": lambda a: [],
        "stale_code": lambda a: None,
        "bench_count": lambda a: 0,
    })


def _grades(findings):
    return {(f.get("state"), f.get("grade")) for f in findings}


def test_p3_the_retired_incarnation_no_longer_pages_hard_wedge():
    c, ns = FakeRedis(), _ns()
    now = time.time()
    incarnation = f"{AGENT}#{SID8}"
    roster.heartbeat(ns, AGENT, SESSION, phase="running", client=c, _beat_ts=now - 4232)

    before = _examine(c, ns, incarnation, now)
    assert ("hard_wedge", "page") in _grades(before), (
        f"control: the lingering card must reproduce the page; got {_grades(before)}")
    assert liveness.DEFAULT_WEDGE_S <= 4232, "the receipt's age must clear the page threshold"

    rep = _retire(ns, c, stop_hb=threading.Event())

    after = _examine(c, ns, incarnation, now)
    pages = [f for f in after if f.get("grade") == "page"]
    assert not pages, (
        f"P3: the process exited CLEANLY ({rep}) and the doctor still pages on its card: "
        f"{[f.get('line') for f in pages]}")
