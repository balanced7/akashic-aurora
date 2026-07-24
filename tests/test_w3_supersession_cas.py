"""
Wave 3 / RB-8 -- CAS on the note-supersession write: the chain cannot fork under
concurrency. Pre-registered acceptance, committed BEFORE the implementation (M3 /
T031 hook 2). Spec: docs/library/design/20260711_wave-3-reconciled-build-spec-rb-8-12-dic_4f427b.md (dual-half, reconciled).

Bar (slice text, docs/library/design/20260701_resilience-battery-sliced-execution-plan_8d660c.md RB-8): two concurrent
supersessions of one title leave exactly ONE active note; the loser errors loudly
naming the winner; the chain stays linear.

Contract under test (spec "RB-8"):
  AgentMemory.decide(...)            -- single attempt; loser self-retires + raises
  SupersedeRaceError                 -- carries the winner's id in its message
  AgentMemory.decide_with_retry(...) -- door-level helper; re-reads head, cap 3
  normalize_title(str) -> str        -- NFC + strip (RB-9's function, born here)
  HEAD_KEY_PREFIX = "mem:decisions:head:"
  DictStore                          -- in-memory Store (differential slice pair)

Run: py -m pytest tests/test_w3_supersession_cas.py -q
"""
import os
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from core.foundation.store import DictStore  # noqa: E402
    from core.learning.agent_memory import (  # noqa: E402
        HEAD_KEY_PREFIX,
        AgentMemory,
        SupersedeRaceError,
        normalize_title,
    )
    _W3_BUILT = True
except ImportError:  # pre-impl: names land with the RB-8 slice
    _W3_BUILT = False

# Pre-registered pins skip (never error) until the impl exists, then MUST flip to PASS.
# Weakening any assertion after this commit violates the pre-registration bar (M3/T031).
pytestmark = pytest.mark.skipif(
    not _W3_BUILT, reason="W3/RB-8 pins pre-registered; impl pending (RB-8 slice)"
)

TITLE = "where-we-are"


@pytest.fixture()
def mem():
    return AgentMemory(store=DictStore())


def _actives(m, title=TITLE):
    return [d for d in m.get_decisions(days=3650) if normalize_title(d.title) == normalize_title(title)]


def _all(m, title=TITLE):
    return [d for d in m.get_decisions(days=3650, include_superseded=True)
            if normalize_title(d.title) == normalize_title(title)]


def _head(m, title=TITLE):
    return m.store.get(HEAD_KEY_PREFIX + normalize_title(title))


# --- (1) the slice's named acceptance: same-target race -> one active, loud loser ---

def test_same_target_race_one_active_loser_errors(mem):
    a = mem.decide_with_retry(TITLE, "state A")
    winner = mem.decide(TITLE, "state B", supersedes=a)
    assert winner and _head(mem) == winner
    with pytest.raises(SupersedeRaceError) as ei:
        mem.decide(TITLE, "state B-prime", supersedes=a)   # same stale target = the race
    assert winner in str(ei.value), "the error teaches: it names the winning head"
    actives = _actives(mem)
    assert len(actives) == 1 and actives[0].id == winner
    assert all(d.superseded for d in _all(mem) if d.id != winner), \
        "the loser's own record is auto-retired, never left active-unheaded"


# --- (2) concurrent FIRST notes: the nx gate ---

def test_concurrent_first_note_gated(mem):
    first = mem.decide(TITLE, "genesis")            # supersedes=None claims fresh head
    assert first and _head(mem) == first
    with pytest.raises(SupersedeRaceError):
        mem.decide(TITLE, "rival genesis")          # head now foreign+active -> lose
    assert len(_actives(mem)) == 1


# --- (3) door helper: corrected retry keeps the chain LINEAR ---

def test_decide_with_retry_chains_linearly(mem):
    a = mem.decide_with_retry(TITLE, "A")
    b = mem.decide_with_retry(TITLE, "B")
    c = mem.decide_with_retry(TITLE, "C")
    assert _head(mem) == c
    recs = {d.id: d for d in _all(mem)}
    assert recs[b].supersedes == a and recs[c].supersedes == b, "linear: C<-B<-A"
    targets = [d.supersedes for d in recs.values() if d.supersedes]
    assert len(targets) == len(set(targets)), "never two records claiming one ancestor"
    assert len(_actives(mem)) == 1


# --- (4) retry cap: never an unbounded door loop ---

def test_retry_cap_three_then_loud(mem, monkeypatch):
    calls = []
    def always_lose(*a, **k):
        calls.append(1)
        raise SupersedeRaceError("lost to ADR_ghost_head")
    monkeypatch.setattr(mem, "decide", always_lose)
    with pytest.raises(SupersedeRaceError):
        mem.decide_with_retry(TITLE, "never lands")
    assert len(calls) == 3, "cap is 3 attempts, then fail loud (no livelock)"


# --- (5) retired current head is claimable (retire-last-note then re-note works) ---

def test_retired_head_is_claimable(mem):
    a = mem.decide_with_retry(TITLE, "A")
    assert mem.retire_decision(a)                   # tombstone; sentinel untouched by design
    assert _head(mem) == a, "retire_decision never touches the sentinel"
    b = mem.decide(TITLE, "B after tombstone")      # retired current -> claimable
    assert b and _head(mem) == b
    assert len(_actives(mem)) == 1


# --- (6) dangling head (manual deletion drift) is claimable ---

def test_dangling_head_is_claimable(mem):
    mem.store.set(HEAD_KEY_PREFIX + normalize_title(TITLE), "ADR_ghost_00000000")
    b = mem.decide(TITLE, "B over dangling pointer")
    assert b and _head(mem) == b


# --- (7) id hardening: same-second generation cannot collide ---

def test_id_generation_unique_x1000(mem):
    ids = {mem._gen_id("ADR") for _ in range(1000)}
    assert len(ids) == 1000


# --- (8) uncontended cost: exactly one CAS, no retries ---

def test_uncontended_single_cas(mem):
    a = mem.decide_with_retry(TITLE, "A")
    cas_calls = []
    real_cas = mem.store.cas
    mem.store.cas = lambda *args, **kw: (cas_calls.append(1), real_cas(*args, **kw))[1]
    b = mem.decide(TITLE, "B", supersedes=a)
    assert b and len(cas_calls) == 1, "happy path pays exactly one CAS"


# --- (9) lazy head bootstrap over a pre-RB-8 corpus; idempotent ---

def test_lazy_bootstrap_pre_head_corpus(mem):
    import json as _json
    from dataclasses import asdict
    from datetime import datetime
    from core.learning.agent_memory import Decision
    # forge a legacy chain written before head keys existed: old superseded, new active
    old = Decision(id="ADR_0101000001_aaaaaaaa", title=TITLE, status="accepted", context="",
                   decision="legacy old", rationale=[], alternatives=[],
                   consequences={"positive": [], "negative": []},
                   created_at=datetime(2026, 1, 1, 0, 0, 1).isoformat(), session_id="",
                   supersedes=None, superseded=True)
    new = Decision(id="ADR_0101000002_bbbbbbbb", title=TITLE, status="accepted", context="",
                   decision="legacy new", rationale=[], alternatives=[],
                   consequences={"positive": [], "negative": []},
                   created_at=datetime(2026, 1, 1, 0, 0, 2).isoformat(), session_id="",
                   supersedes="ADR_0101000001_aaaaaaaa", superseded=False)
    for d in (old, new):
        mem.store.hset(mem.KEY_DECISIONS, field=d.id, value=_json.dumps(asdict(d)))
        mem.store.zadd(mem.KEY_DECISION_INDEX,
                       {d.id: datetime.fromisoformat(d.created_at).timestamp()})
    assert _head(mem) is None, "pre-head corpus: no sentinel yet"
    c = mem.decide_with_retry(TITLE, "post-RB-8 write")
    assert c and _head(mem) == c
    recs = {d.id: d for d in _all(mem)}
    assert recs[c].supersedes == new.id, "bootstrap derived the head from the newest active"
    assert len(_actives(mem)) == 1


# --- (10) threaded smoke: N racers, one title, all through the door helper ---

def test_threaded_door_smoke(mem):
    errs = []
    def racer(n):
        try:
            mem.decide_with_retry(TITLE, "racer %d" % n)
        except SupersedeRaceError as e:   # cap-exhaustion under heavy contention is LOUD, not silent
            errs.append(e)
        except Exception as e:
            errs.append(e)
    threads = [threading.Thread(target=racer, args=(i,)) for i in range(8)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert len(_actives(mem)) == 1, "whatever raced, exactly one active survives"
    assert all(isinstance(e, SupersedeRaceError) for e in errs), \
        "the only permitted failure is the loud race error"
    targets = [d.supersedes for d in _all(mem) if d.supersedes and not d.superseded]
    assert len(targets) <= 1, "no fork: at most the single active claims an ancestor"
