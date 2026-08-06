"""
T196c -- `ask --peer`: one durable ask, ergonomically synchronous (committed RED).

Spec: docs/library/design/20260805_t196-ask-transaction-spec_b59657.md, "The verb".
Sol's principle delivered: one command, transport invisible. Send + arm + poll, where
sweep() is the ACTOR and ask_state.state_of() is the ORACLE -- the verb is the state
machine in a loop. The interactive wait is short; the EXPECTATION is durable: when the
wait gives up, the ask stays armed, redrives continue, and the caller gets a handle,
not an error.

Contract frozen here:
  core.comm.ask.ask_peer(sender, peer, prompt, *, wait_s, poll_s, within_s, kind)
      -> BoundaryOutcome, never raises
  settled within wait  -> done: detail carries answer (the peer's text), ask_id,
      state CLOSED.ANSWERED, elapsed_s
  not settled          -> PARTIALLY (an OPEN ask is a normal state, not a failure):
      detail carries ask_id, state OPEN.*, how_to_check naming ask --status
      AND the expectation record survives the wait (the durable tail is the point)
  empty prompt         -> failed (parallel to ask())
  NON-CONSUMING: the sender's lane cursors are untouched by the whole flow --
      concurrent sibling sessions must never be starved (two-live-seats law)
  door: ask_p grows --peer and --wait

Run: py -m pytest tests/test_t196c_ask_peer.py -q
"""
import os
import sys
import threading
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
    from core.comm.ask import ask_peer
    _BUILT = True
except ImportError:
    ask_peer = None
    _BUILT = False

try:
    _ONLINE = bool(Bus and Bus("t196c-probe").online)
except Exception:
    _ONLINE = False

needs_built = pytest.mark.skipif(not _BUILT, reason="ask_peer pending (pins frozen)")
needs_live = pytest.mark.skipif(not _ONLINE, reason="live-Redis pins; bus offline")


@pytest.fixture()
def pair():
    s = f"t196csnd-{uuid.uuid4().hex[:8]}"
    r = f"t196crcv-{uuid.uuid4().hex[:8]}"
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


def _responder(r, s, text="the peer's answer", delay=0.4, stop=None):
    """A scripted peer: peek (non-consuming) for the request, reply with the linkage
    the T117 machinery resolves (meta.answers = the id the peer actually SAW)."""
    def run():
        end = time.time() + 10
        while time.time() < end and not (stop and stop.is_set()):
            try:
                reqs = [m for m in Bus(r).inbox(limit=20, advance=False)
                        if getattr(m, "frm", None) == s
                        and getattr(m, "kind", "") == "request"]
                if reqs:
                    time.sleep(delay)
                    Bus(r).send(s, "reply", text,
                                meta={"answers": reqs[-1].id})
                    return
            except Exception:
                pass
            time.sleep(0.1)
    t = threading.Thread(target=run, daemon=True)
    t.start()
    return t


# --- P1: the seam exists (RED today) ---

def test_seam_exists():
    assert _BUILT and callable(ask_peer), \
        "core.comm.ask.ask_peer is the T196c deliverable -- the verb family lives together"


# --- P2: settled within the wait -> done, answer in-band, cursors untouched ---

@needs_built
@needs_live
def test_settles_in_band_without_consuming(pair):
    s, r = pair
    cursors_before = Bus(s).read_lane_cursor()
    t = _responder(r, s, text="42, obviously")
    o = ask_peer(s, r, "what is the answer?", wait_s=15, poll_s=0.2)
    t.join(timeout=1)
    assert o.ok and not o.partial, f"settled ask must be a clean done, got: {o.why}"
    d = o.detail
    assert d["state"] == "CLOSED.ANSWERED" and d["ask_id"]
    assert d["answer"] == "42, obviously", "the peer's text comes back IN-BAND"
    assert d["elapsed_s"] < 15
    assert Bus(s).read_lane_cursor() == cursors_before, \
        "the whole flow is non-consuming: sibling sessions keep their mail"


# --- P3: not settled -> PARTIALLY with a handle; the expectation OUTLIVES the wait ---

@needs_built
@needs_live
def test_timeout_returns_handle_and_stays_armed(pair):
    s, r = pair
    o = ask_peer(s, r, "anyone home?", wait_s=1, poll_s=0.25)
    # House vocabulary (T181): done = ok and not partial; PARTIALLY = ok AND partial
    # (ok means "not failed"); failed = not ok. The first cut of this pin asserted
    # `partial and not ok` -- a foreign outcome type, corrected to the contract's
    # actual intent: a timeout is PARTIALLY, never failed, never a clean done.
    assert o.partial and not bool(o), \
        "an OPEN ask is a normal state: PARTIALLY, never failed, never a clean done"
    d = o.detail
    assert d["state"].startswith("OPEN.") and d["ask_id"]
    assert "--status" in d.get("how_to_check", ""), "the handle says how to check later"
    recs = expectations.snapshot(s)
    assert str(d["ask_id"]) in {str(k) for k in recs}, \
        "the DURABLE tail is the point: the record survives the interactive wait"
    assert recs[str(d["ask_id"])].get("to") == r


# --- P4: an empty prompt is a failure, same as the stateless verb ---

@needs_built
def test_empty_prompt_fails():
    o = ask_peer("anyone", "peer", "   ", wait_s=1)
    assert not o.ok and not o.partial and "empty" in (o.why or "").lower()


# --- P6 (post-incident, first live use 2026-08-06): the CLI render must branch on
#     partial BEFORE ok. BoundaryOutcome's ok means NOT-FAILED, so a timeout PARTIALLY
#     has ok=True -- and an `if o.ok:` echo-branch swallowed it, rendering CLOSED.ECHO
#     for an ask that was OPEN.DISPATCHED and armed. The library told the truth; the
#     render lied. Same trap this file's own P3 hit an hour earlier: pinned so the
#     class closes. ---

@needs_built
def test_cli_render_partial_is_not_echo(monkeypatch, capsys):
    import types
    import agent_cli
    from core.outcome import BoundaryOutcome

    fake = BoundaryOutcome.partially(
        "not settled within 1s -- the ask stays armed",
        ask_id="123-0", peer="deepseek", state="OPEN.DISPATCHED",
        elapsed_s=1.0, armed=True, redrives=0,
        how_to_check="py agent_cli.py ask --status 123-0 --as claude")
    import core.comm.ask as ask_mod
    monkeypatch.setattr(ask_mod, "ask_peer", lambda *a, **k: fake)

    args = types.SimpleNamespace(
        text=["anyone", "home?"], prompt_file=None, prompts_file=None, fan=0,
        system="", model="", max_tokens=None, workers=None, json=False,
        status=None, as_agent="claude", peer="deepseek", wait=1.0, poll=0.25)
    rc = agent_cli.cmd_ask(args)
    err = capsys.readouterr().err
    assert rc == 0, "an OPEN handle is a normal outcome: exit 0"
    assert "OPEN.DISPATCHED" in err and "--status" in err
    assert "ECHO" not in err, \
        "a PARTIALLY must never render as CLOSED.ECHO -- partial checks BEFORE ok"


# --- P5: the door is wired ---

def test_door_wired():
    cli = open(os.path.join(_ROOT, "agent_cli.py"), encoding="utf-8").read()
    assert 'ask_p.add_argument("--peer"' in cli and 'ask_p.add_argument("--wait"' in cli, \
        "ask --peer <seat> [--wait N] is the durable route on the SAME verb"
