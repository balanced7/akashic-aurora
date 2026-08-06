"""
T196d -- one durable ask's honest state: pre-registered acceptance (committed RED).

Spec: docs/library/design/20260805_t196-ask-transaction-spec_b59657.md, "The state
machine". Sol's five success-shaped states, rebuilt with the unflattering ones the house
laws require. The readout is a FOLD with a precedence order -- expectation record (open
states) -> durable terminal events (closed states) -> nothing (UNKNOWN) -- and it is the
ORACLE the T196c verb polls: the verb is this state machine in a loop.

Contract frozen here:
  core.comm.ask_state.STATES: dict state -> (terminal: bool, caller_should: str)
      exactly the spec's seven; every state answers "what should the caller do NOW"
  core.comm.ask_state.state_of(sender, ask_id, *, log=None, now=None) -> dict with
      at least: state, terminal, caller_should, ask_id, resolved_id, peer
      -- id resolution follows the {ns}:idalias chain (bounded, <=2 hops), so a
         REDRIVE id resolves to the original ask instead of lying UNKNOWN
      -- OPEN.* from the armed record: attempt>0 -> REDRIVING; else a directed
         NON-answer from the peer after the anchor -> NOTED; else DISPATCHED
      -- CLOSED.* from durable terminal events (T196b kinds), refs[0] == ask id;
         duration_s computed from detail.created when present, None otherwise
      -- UNKNOWN when no record and no terminal event: terminal True, and the
         caller_should says re-ask -- never a confident guess
      `log` injectable (an object with .scan(agent=...)) so pins write NOTHING to the
      live firehose; `now` injectable so pins never sleep.
  CLI: `ask --status <id> --as <sender>` renders one state row (door pin).

Run: py -m pytest tests/test_t196d_ask_state.py -q
"""
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

try:
    from core.comm import expectations
    from core.comm.bus import Bus
except ImportError:
    expectations = Bus = None

try:
    from core.comm import ask_state
    _BUILT = hasattr(ask_state, "state_of") and hasattr(ask_state, "STATES")
except ImportError:
    ask_state = None
    _BUILT = False

try:
    _ONLINE = bool(Bus and Bus("t196d-probe").online)
except Exception:
    _ONLINE = False

needs_built = pytest.mark.skipif(not _BUILT, reason="ask_state pending (pins frozen)")
needs_live = pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline")

SEVEN = {"OPEN.DISPATCHED", "OPEN.NOTED", "OPEN.REDRIVING",
         "CLOSED.ANSWERED", "CLOSED.ECHO", "CLOSED.DEAD", "UNKNOWN"}


class _StubLog:
    """Injectable event source: pins construct terminal evidence instead of writing it."""
    def __init__(self, events):
        self._events = list(events)

    def scan(self, agent=None, limit=None):
        return list(self._events)


@pytest.fixture()
def pair():
    s = f"t196dsnd-{uuid.uuid4().hex[:8]}"
    r = f"t196drcv-{uuid.uuid4().hex[:8]}"
    for aid in (s, r):
        b = Bus(aid)
        b.advance_to(bc=b.tail().get("bc"), generation=0)
    yield s, r
    try:
        c = Bus(s)._client
        for k in (f"bifrost:expect:{s}", f"bifrost:inbox:{s}", f"bifrost:inbox:{r}",
                  f"bifrost:cursor:{s}", f"bifrost:cursor:{r}",
                  f"bifrost:presence:{s}", f"bifrost:presence:{r}"):
            c.delete(k)
    except Exception:
        pass


def _arm(s, r, within=60, content="answer me"):
    orig = Bus(s).send(r, "request", content)
    assert orig
    assert expectations.arm(s, orig, r, "request", content, within)
    return str(orig)


# --- P1: the seven states, no more, no fewer, each with terminal + caller_should ---

def test_states_are_the_spec_seven():
    assert _BUILT, "core/comm/ask_state.py with STATES + state_of is the T196d deliverable"
    assert set(ask_state.STATES) == SEVEN
    for name, (terminal, should) in ask_state.STATES.items():
        assert isinstance(terminal, bool)
        assert should and isinstance(should, str), f"{name} must answer 'what now?'"


# --- P2: OPEN.DISPATCHED -- armed, nothing observable happened ---

@needs_built
@needs_live
def test_dispatched(pair):
    s, r = pair
    orig = _arm(s, r)
    st = ask_state.state_of(s, orig, log=_StubLog([]))
    assert st["state"] == "OPEN.DISPATCHED" and st["terminal"] is False
    assert st["peer"] == r and st["resolved_id"] == orig
    assert st["caller_should"] == ask_state.STATES["OPEN.DISPATCHED"][1]


# --- P3: OPEN.NOTED -- a directed NON-answer arrived; the ask is neither dead nor done ---

@needs_built
@needs_live
def test_noted(pair):
    s, r = pair
    orig = _arm(s, r)
    Bus(r).send(s, "note", "(runner timed out -- api call abandoned)")
    st = ask_state.state_of(s, orig, log=_StubLog([]))
    assert st["state"] == "OPEN.NOTED" and st["terminal"] is False


# --- P4: OPEN.REDRIVING -- deadline passed, a copy went out ---

@needs_built
@needs_live
def test_redriving(pair):
    s, r = pair
    t0 = time.time()
    orig = _arm(s, r, within=60)
    assert expectations.sweep(s, now=t0 + 61)["redriven"] == [orig]
    st = ask_state.state_of(s, orig, log=_StubLog([]))
    assert st["state"] == "OPEN.REDRIVING" and st["terminal"] is False


# --- P5: a REDRIVE id resolves to the original (idalias walk) instead of lying UNKNOWN ---

@needs_built
@needs_live
def test_redrive_id_resolves(pair):
    s, r = pair
    t0 = time.time()
    orig = _arm(s, r, within=60)
    assert expectations.sweep(s, now=t0 + 61)["redriven"] == [orig]
    copies = [m for m in Bus(r).inbox(limit=50, advance=False)
              if (m.meta or {}).get("redrive_of") == orig]
    assert copies, "redrive copy visible on the peer inbox"
    rid = copies[0].id
    st = ask_state.state_of(s, rid, log=_StubLog([]))
    assert st["resolved_id"] == orig, "the alias chain resolves a redrive id to its ask"
    assert st["state"] == "OPEN.REDRIVING"


# --- P6: CLOSED.ANSWERED from durable evidence, duration computed from created ---

@needs_built
def test_answered_from_terminal_event():
    ev = {"kind": "expectation_settled_answered", "at": "2026-08-05T12:01:40+00:00",
          "agent_id": "s", "refs": ["ASK-1", "REPLY-9"],
          "detail": {"to": "peerx", "attempt": 1, "created": 1786017600.0,
                     "answer_id": "REPLY-9"}}
    st = ask_state.state_of("s", "ASK-1", log=_StubLog([ev]))
    assert st["state"] == "CLOSED.ANSWERED" and st["terminal"] is True
    assert st["answer_id"] == "REPLY-9" and st["peer"] == "peerx"
    assert st["duration_s"] is not None, "created present -> duration computed"


# --- P7: CLOSED.ECHO and CLOSED.DEAD from their durable kinds ---

@needs_built
def test_echo_and_dead_from_terminal_events():
    echo = {"kind": "expectation_settled_done_task", "at": "2026-08-05T12:00:00+00:00",
            "agent_id": "s", "refs": ["ASK-2"],
            "detail": {"to": "peerx", "settle": "referenced tasks terminal: T042=done"}}
    dead = {"kind": "expectation_dead", "at": "2026-08-05T12:00:00+00:00",
            "agent_id": "s", "refs": ["ASK-3"],
            "detail": {"to": "peery", "attempts": 3}}
    st_e = ask_state.state_of("s", "ASK-2", log=_StubLog([echo, dead]))
    st_d = ask_state.state_of("s", "ASK-3", log=_StubLog([echo, dead]))
    assert st_e["state"] == "CLOSED.ECHO" and st_e["terminal"] is True
    assert st_d["state"] == "CLOSED.DEAD" and st_d["terminal"] is True
    assert st_d["duration_s"] is None, "legacy dead event without created: None, no guess"


# --- P8: UNKNOWN -- no record, no evidence: terminal, and it says so ---

@needs_built
@needs_live
def test_unknown_never_guesses(pair):
    s, _ = pair
    st = ask_state.state_of(s, "1700000000000-0", log=_StubLog([]))
    assert st["state"] == "UNKNOWN" and st["terminal"] is True
    assert "re-ask" in st["caller_should"].lower()


# --- P9: the door is wired ---

def test_door_wired():
    cli = open(os.path.join(_ROOT, "agent_cli.py"), encoding="utf-8").read()
    # The ASK parser specifically -- a bare '"--status"' grep matched other verbs' flags
    # and made this pin green before the build, which is no pin at all.
    assert 'ask_p.add_argument("--status"' in cli and 'ask_p.add_argument("--as"' in cli, \
        "ask --status <id> --as <sender> renders the state row"
