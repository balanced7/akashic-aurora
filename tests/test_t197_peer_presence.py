"""
T197 -- the transaction learns whether anyone was home: pre-registered acceptance
(committed RED, before impl).

WHY THIS EXISTS, measured rather than asserted. The friction reader (T196a) read the
collaboration tax on 2026-08-06 over a 336h window: 32 closed ask-episodes, 0 ANSWERED,
26 DEAD (81.2%). The cause was not the verb, the transaction, or the seven-state machine
-- all three work and are pinned. The launcher registry showed ALL EIGHT launchable
agents at `never_launched`. Every durable ask had been addressed to a seat with no
process behind it, and nothing in the transaction ever said so.

THE HONEST VERDICT ALREADY EXISTED. core.comm.liveness.attendance (T155) answers
ATTENDED / UNATTENDED / UNKNOWN over a three-probe ladder, consulted in ONE direction so
a probe can only rescue a false death, never invent one. bus.send() already calls it and
prints an UNATTENDED RECIPIENT warning -- to STDERR, where the transaction that most
needed it threw it away. This slice does not build a new instrument. It makes the front
door KEEP the answer the system was already giving it.

FENCED WITH DEEPSEEK (2026-08-06), and the fence moved the design twice:
  (C) Preflight must NOT gate the send. Instant refusal conflates "down right now" with
      "never coming" and destroys the late-binding detection window -- a peer absent at
      t=0 can be alive by the second redrive, and the 30-minute expectation is exactly
      the instrument that catches that. PINNED BELOW AS LAW, because it is the rule a
      future optimizer is most likely to "improve" away.
  (F) A t=0 verdict ALONE is diagnostic poison: a fixed-time observation is structurally
      incapable of explaining a deferred outcome, and freezing one into the record turns
      a debugging aid into a systemic attribution error. The fix is ONE more observation,
      taken AT DEATH. Only the PAIR partitions the failures.

THE PAIR IS THE WHOLE POINT. Today every dead ask is the same row. With both ends:
  UNATTENDED -> UNATTENDED   absent       nobody was ever home      -> launch the peer
  ATTENDED   -> UNATTENDED   vanished     died mid-flight           -> chase the crash
  ATTENDED   -> ATTENDED     ignored      home and did not answer   -> chase the consumer
  UNATTENDED -> ATTENDED     arrived_late late binding, still mute  -> chase the backlog
Four different bugs, four different actions, one row until now.

Contract frozen here:
  expectations.arm(sender, orig_id, to, kind, content, within_s, *, peer_state=None,
      peer_why=None)   -- optional; when given, stored on the record as peer_at_ask /
      peer_at_ask_why. Omitted -> absent from the record (never defaulted to a guess).
  expectations._emit_dead   -- detail carries peer_at_ask (from the record) AND
      peer_at_death (observed FRESH at death, best-effort, never raises into the sweep).
  expectations._emit_settled -- detail carries peer_at_ask (answered episodes deserve
      the same column, or the partition is only defined on failures).
  ask.ask_peer(...)  -- observes attendance BEFORE send, arms with it, returns it in
      detail["peer_at_ask"]/["peer_at_ask_why"]; ALWAYS sends regardless of verdict.
  ask_state.state_of -- surfaces peer_at_ask for OPEN (record) and CLOSED (event) alike.
  friction.fold      -- dead episodes partition into dead_absent / dead_vanished /
      dead_ignored / dead_arrived_late / dead_peer_unknown, summing EXACTLY to n_dead.

BACKWARD COMPATIBILITY IS A HONESTY REQUIREMENT, NOT A COURTESY. The 26 historical dead
episodes carry no peer fields at all. They must partition as dead_peer_unknown -- never
be back-filled, inferred, or quietly counted as `absent` because that is the likely
answer. A reader that guesses the past is the exact defect this arc exists to remove.

Run: py -m pytest tests/test_t197_peer_presence.py -q
"""
import inspect
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.foundation.timeutil import now_iso  # noqa: E402

try:
    from core.comm import expectations, friction
    from core.comm.bus import Bus
except ImportError:                                             # pragma: no cover
    expectations = friction = Bus = None


def _redis_up():
    try:
        from core.comm.bus import _connect
        c = _connect()
        return c is not None and c.ping()
    except Exception:
        return False


needs_redis = pytest.mark.skipif(not _redis_up(), reason="bus Redis unreachable")


# --------------------------------------------------------------------------------------
# 1. The pure fold: the partition, and its refusal to guess about the past.
# --------------------------------------------------------------------------------------

def _dead_ev(ask_id, *, at_ask=None, at_death=None, created=1000.0, at="2026-08-06T00:00:00Z"):
    detail = {"to": "deepseek", "kind": "request", "attempts": 3, "created": created}
    if at_ask is not None:
        detail["peer_at_ask"] = at_ask
    if at_death is not None:
        detail["peer_at_death"] = at_death
    return {"kind": "expectation_dead", "at": at, "refs": [ask_id], "detail": detail}


def test_dead_partition_names_four_different_bugs():
    """The 2x2 that turns one row into four actions. This is the finding the whole
    slice exists to produce; if it collapses, the reader is back to 'they all died'."""
    events = [
        _dead_ev("a-1", at_ask="UNATTENDED", at_death="UNATTENDED"),   # absent
        _dead_ev("a-2", at_ask="ATTENDED", at_death="UNATTENDED"),     # vanished
        _dead_ev("a-3", at_ask="ATTENDED", at_death="ATTENDED"),       # ignored
        _dead_ev("a-4", at_ask="UNATTENDED", at_death="ATTENDED"),     # arrived_late
    ]
    agg = friction.fold(events, {}, now=2000.0)["agg"]
    assert agg["n_dead"] == 4
    assert agg["dead_absent"] == 1, "UNATTENDED at both ends = nobody was ever home"
    assert agg["dead_vanished"] == 1, "ATTENDED then UNATTENDED = died mid-flight"
    assert agg["dead_ignored"] == 1, "ATTENDED at both ends = home and did not answer"
    assert agg["dead_arrived_late"] == 1, "UNATTENDED then ATTENDED = late binding"
    assert agg["dead_peer_unknown"] == 0


def test_partition_sums_to_n_dead_exactly():
    """A partition that does not sum is not a partition -- it is a set of overlapping
    guesses, and the missing rows would be invisible rather than named."""
    events = [
        _dead_ev("b-1", at_ask="UNATTENDED", at_death="UNATTENDED"),
        _dead_ev("b-2"),                                            # legacy: no fields
        _dead_ev("b-3", at_ask="UNKNOWN", at_death="UNATTENDED"),   # probe unreadable
        _dead_ev("b-4", at_ask="ATTENDED"),                         # half-observed
    ]
    agg = friction.fold(events, {}, now=2000.0)["agg"]
    keys = ("dead_absent", "dead_vanished", "dead_ignored",
            "dead_arrived_late", "dead_peer_unknown")
    assert sum(agg[k] for k in keys) == agg["n_dead"] == 4


def test_the_past_is_never_back_filled():
    """The 26 historical dead episodes have no peer fields. They are UNKNOWN, not
    'probably absent' -- guessing the past is the defect this arc removes."""
    agg = friction.fold([_dead_ev(f"c-{i}") for i in range(26)], {}, now=2000.0)["agg"]
    assert agg["dead_peer_unknown"] == 26
    assert agg["dead_absent"] == 0, "a missing observation is not an observation of absence"


def test_a_half_observed_episode_is_unknown_not_half_credited():
    """One end observed is not the pair. `peer_at_ask` alone cannot distinguish
    'vanished' from 'ignored' -- that was deepseek's (F), and it is the reason the
    death-time probe exists at all."""
    agg = friction.fold([_dead_ev("d-1", at_ask="ATTENDED")], {}, now=2000.0)["agg"]
    assert agg["dead_peer_unknown"] == 1
    assert agg["dead_ignored"] == 0 and agg["dead_vanished"] == 0


def test_episode_rows_carry_both_ends():
    """The aggregate is the headline; the row is what an operator acts on."""
    rows = friction.fold([_dead_ev("e-1", at_ask="UNATTENDED", at_death="ATTENDED")],
                         {}, now=2000.0)["episodes"]
    assert rows[0]["peer_at_ask"] == "UNATTENDED"
    assert rows[0]["peer_at_death"] == "ATTENDED"
    assert rows[0]["peer_verdict"] == "arrived_late"


def test_blind_list_names_the_new_blindness():
    """No-silent-caps, kept structural: the pair is two point-samples over a 30-minute
    window and says nothing about the middle. A reader that does not confess that is
    claiming a continuous observation it never took."""
    blind = " ".join(friction.fold([], {}, now=1.0)["blind"]).lower()
    assert "peer" in blind
    assert any(w in blind for w in ("between", "middle", "point", "sample", "continuous"))


# --------------------------------------------------------------------------------------
# 2. The law the fence bought: preflight OBSERVES, it never gates.
# --------------------------------------------------------------------------------------

def test_preflight_never_gates_the_send():
    """DEEPSEEK'S (C), PINNED AS LAW. An UNATTENDED verdict must not stop the send:
    a peer absent at t=0 can be alive by the second redrive, and refusing fast would
    conflate 'down right now' with 'never coming' -- destroying both the late-binding
    window and the measurement that found this bug.

    Pinned structurally (no bus needed): once the verdict EXISTS, no path may return a
    failure before the send. The window is anchored on the verdict rather than on the
    probe call, because an input guard that rejects an empty prompt is validation, not
    a peer gate -- and a pin that cannot tell those apart would fire on the wrong thing.
    """
    from core.comm import ask as ask_mod
    src = inspect.getsource(ask_mod.ask_peer)
    probe = src.index("attendance(")                 # the call, not the prose
    verdict = src.index("peer_state, peer_why")      # the moment the answer exists
    send = src.index("b.send(")
    assert probe < verdict < send, (
        "the verdict must be observed BEFORE the send, or it cannot be armed onto the "
        "record the death event inherits")
    for forbidden in ("return _BO.failed", "return BoundaryOutcome.failed", "return None"):
        assert forbidden not in src[verdict:send], (
            "preflight refused to send -- that is the design deepseek's (C) argument "
            "removed. Observe, report, arm, and SEND anyway.")


def test_ask_peer_is_durable_but_still_not_a_seat():
    """THE NARROWER LAW the T171/T181 amendment owes.

    Those two pins scan core/comm/ask.py for seat machinery, and T196c's `ask_peer` -- a
    durable ask that rides the expectation machinery BY DESIGN -- turned both red on a
    reference the design requires. They were scoped to the stateless path on 2026-08-06;
    this is the tooth that replaces what they gave up, and it must be STRICTLY stronger
    than nothing or the amendment was a weakening wearing a scoping's clothes.

    `ask_peer` may touch expectations (its declared transport) and liveness (T197's
    observation). Everything else that makes a seat -- a lock, a cursor, a roster row, a
    heartbeat, a role queue -- stays forbidden. The moment it acquires one of those it
    has stopped being a call and become a seat, which is the whole T171 claim.
    """
    import ast
    from core.comm import ask as ask_mod

    tree = ast.parse(open(ask_mod.__file__, encoding="utf-8").read())
    fn = next(n for n in tree.body
              if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == "ask_peer")

    referenced = set()
    for node in ast.walk(fn):
        if isinstance(node, ast.Import):
            for alias in node.names:
                referenced.update(alias.name.split("."))
        elif isinstance(node, ast.ImportFrom):
            referenced.update((node.module or "").split("."))
            for alias in node.names:
                referenced.add(alias.name)
        elif isinstance(node, ast.Attribute):
            referenced.add(node.attr)
        elif isinstance(node, ast.Name):
            referenced.add(node.id)

    forbidden = {"runner_lock", "seed_cursor", "roster", "mailbox", "worklive",
                 "acquire", "bifrost_send", "heartbeat", "role_queue"}
    assert not sorted(forbidden & referenced), (
        "ask_peer acquired seat machinery -- it is a durable CALL, not a seat")
    assert "expectations" in referenced, (
        "and it must still be durable: an ask_peer that stopped arming an expectation "
        "would pass this law by becoming the wrong thing")


def test_ask_peer_signature_does_not_grow_a_gate_flag():
    """No `require_live=` / `skip_if_dead=` escape hatch: an option to gate is a gate
    with a default, and defaults migrate."""
    from core.comm.ask import ask_peer
    params = set(inspect.signature(ask_peer).parameters)
    assert not (params & {"require_live", "skip_if_dead", "only_if_attended", "gate"})


# --------------------------------------------------------------------------------------
# 3. arm() carries the verdict, and never invents one.
# --------------------------------------------------------------------------------------

@needs_redis
def test_arm_stores_the_verdict_when_given():
    sender = f"t197arm{uuid.uuid4().hex[:6]}"
    oid = f"{int(time.time()*1000)}-0"
    assert expectations.arm(sender, oid, "deepseek", "request", "q", 1800,
                            peer_state="UNATTENDED", peer_why="no beat, pulse, or worklive")
    rec = expectations.snapshot(sender)[oid]
    assert rec["peer_at_ask"] == "UNATTENDED"
    assert "worklive" in rec["peer_at_ask_why"]
    expectations._client().delete(expectations._key(sender))


@needs_redis
def test_arm_omits_the_field_rather_than_defaulting_it():
    """An unobserved verdict is ABSENT, not 'UNKNOWN' written into the record as if it
    had been probed. The reader distinguishes 'we looked and could not tell' from 'we
    never looked', and a default would erase that distinction at the source."""
    sender = f"t197arm{uuid.uuid4().hex[:6]}"
    oid = f"{int(time.time()*1000)}-1"
    assert expectations.arm(sender, oid, "deepseek", "request", "q", 1800)
    assert "peer_at_ask" not in expectations.snapshot(sender)[oid]
    expectations._client().delete(expectations._key(sender))


@needs_redis
def test_arm_keeps_its_old_positional_contract():
    """Existing callers (T030/T117 paths) must be untouched: the new arguments are
    keyword-only and optional, or this slice breaks the settle machinery it rides on."""
    sig = inspect.signature(expectations.arm)
    for name in ("peer_state", "peer_why"):
        p = sig.parameters[name]
        assert p.kind == inspect.Parameter.KEYWORD_ONLY and p.default is None


# --------------------------------------------------------------------------------------
# 4. The death-time observation: the half of the pair that makes it diagnostic.
# --------------------------------------------------------------------------------------

@needs_redis
def test_dead_event_carries_both_ends(monkeypatch):
    """The record dies in the transition that closes it (T196b's law), so the closing
    event must carry every field the episode will ever be judged by -- now including
    the peer at BOTH ends."""
    captured = {}

    def fake_capture(kind, msg, **kw):
        captured["kind"], captured["detail"] = kind, kw.get("detail") or {}

    monkeypatch.setattr("core.events.event_log.capture_event", fake_capture)
    monkeypatch.setattr("core.comm.liveness.attendance",
                        lambda a, **kw: __import__("core.comm.liveness", fromlist=["x"])
                        .Attendance("ATTENDED", "roster beat 3s", 3.0, a))
    expectations._emit_dead("s1", "9-0",
                            {"to": "deepseek", "kind": "request", "attempt": 3,
                             "created": 100.0, "peer_at_ask": "UNATTENDED",
                             "peer_at_ask_why": "no beat, pulse, or worklive"})
    assert captured["kind"] == "expectation_dead"
    assert captured["detail"]["peer_at_ask"] == "UNATTENDED"
    assert captured["detail"]["peer_at_death"] == "ATTENDED", "observed FRESH at death"


@needs_redis
def test_death_probe_failure_never_breaks_the_sweep(monkeypatch):
    """Fail-open, like every other observability field on this path: a probe that
    raises must cost the column, never the terminal event. An instrument that can kill
    the transition it observes is worse than no instrument."""
    captured = {}

    def fake_capture(kind, msg, **kw):
        captured["detail"] = kw.get("detail") or {}

    def boom(*a, **k):
        raise RuntimeError("probe down")

    monkeypatch.setattr("core.events.event_log.capture_event", fake_capture)
    monkeypatch.setattr("core.comm.liveness.attendance", boom)
    expectations._emit_dead("s1", "9-1", {"to": "deepseek", "created": 100.0,
                                          "peer_at_ask": "UNATTENDED"})
    assert captured, "the dead event must still be emitted"
    assert captured["detail"].get("peer_at_death") in (None, "UNKNOWN")


@needs_redis
def test_settled_event_carries_the_ask_end_too(monkeypatch):
    """Answered episodes get the column as well. A partition defined only over failures
    cannot answer 'do live peers answer more often?' -- the question the whole arc is
    ultimately for."""
    captured = {}
    monkeypatch.setattr("core.events.event_log.capture_event",
                        lambda kind, msg, **kw: captured.update(kw.get("detail") or {}))
    expectations._emit_settled("s1", "9-2", "10-0",
                               {"to": "deepseek", "attempt": 0, "created": 100.0,
                                "peer_at_ask": "ATTENDED"})
    assert captured["peer_at_ask"] == "ATTENDED"


# --------------------------------------------------------------------------------------
# 5. The readout: what the caller is told at t=0, which is the friction being removed.
# --------------------------------------------------------------------------------------

@needs_redis
def test_state_of_surfaces_the_ask_end_for_an_open_record():
    from core.comm.ask_state import state_of
    sender = f"t197st{uuid.uuid4().hex[:6]}"
    oid = f"{int(time.time()*1000)}-2"
    expectations.arm(sender, oid, "deepseek", "request", "q", 1800,
                     peer_state="UNATTENDED", peer_why="no beat, pulse, or worklive")
    st = state_of(sender, oid)
    assert st["state"].startswith("OPEN")
    assert st["peer_at_ask"] == "UNATTENDED"
    expectations._client().delete(expectations._key(sender))


@needs_redis
def test_ask_peer_reports_the_verdict_at_t0_without_waiting(monkeypatch):
    """THE FRICTION THIS SLICE REMOVES. Today an absent peer costs a 120s silent wait,
    then a handle, then a forensic dig 30 minutes later. The verdict must be in the
    outcome the caller already receives -- at t=0, on the same object, with no extra
    command."""
    from core.comm.ask import ask_peer
    import core.comm.liveness as _lv
    monkeypatch.setattr(_lv, "attendance",
                        lambda a, **kw: _lv.Attendance("UNATTENDED", "no beat, pulse, or "
                                                       "worklive", None, a))
    sender = f"t197p{uuid.uuid4().hex[:6]}"
    o = ask_peer(sender, f"nobody{uuid.uuid4().hex[:6]}", "ping", wait_s=0.1, poll_s=0.05)
    d = o.detail or {}
    assert d["peer_at_ask"] == "UNATTENDED"
    assert d.get("peer_at_ask_why")
    assert d.get("ask_id"), "and it SENT anyway -- the transaction exists"
    try:
        expectations._client().delete(expectations._key(sender))
    except Exception:
        pass
