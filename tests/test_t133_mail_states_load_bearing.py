"""T133 M1 -- make the mailbox states LOAD-BEARING. Committed RED.

Daniil, 2026-08-02: "I just want to materially upgrade our experience using this system and make it
behave predictably so I'm not wasting tokens troubleshooting watchers and guessing where things
are at."

THE FINDING THIS SLICE RESTS ON, measured rather than argued: the mail model is already BUILT and
has NEVER BEEN CALLED. `core/comm/mailbox.py` has shipped non-destructive `open()` (which even
returns `seen_by`, the exact field the pod design says the watcher lacks), `declare_intent()` with a
closed roster, durable bodies and tiered retention since M1. Callers of `declare_intent` outside
that module: ZERO. Meters: 1509 unopened, 1 read-but-undeclared.

So with no read record, "handled" falls back to the only other signal available -- mailbox.py:13,
verbatim: "`consumed` -- the target agent's committed cursor has advanced past the message (the
cursor IS the consumption record)". A transport position is being asked to also be a delivery
record, a read receipt and a handled-flag. It can only honestly be the first, and that single
substitution explains all three symptoms:

  * a retired seat's mail is re-answered (kimi spent three turns on codex_root_019fab2d while a
    live directed ask sat unhandled) -- nothing recorded that anyone had adjudicated it;
  * the mailbox reports "unhandled" for work already completed -- the runner decided and the
    decision was never written down;
  * the wake watcher re-arms on already-handled mail -- it has no vocabulary for "seen".

This is the same law that governed the D series two hours ago, at a larger scale: A DOOR THAT
OFFERS A FIELD NOTHING DEPENDS ON STAYS EMPTY. `--category` (840 lessons uncategorized),
`--anti-pattern` (zero uses), and now mailbox intent (zero callers).

THE WIRING, not a rewrite: `_process_one` in every runner ALREADY makes the decision -- each of its
numbered exit paths IS an intent (route -> delegate, swallow -> decline, rate-limit -> defer,
answer -> act). It simply never records it. These pins define the one shared seam that lets it.

Run: py -m pytest tests/test_t133_mail_states_load_bearing.py -q
"""
from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "scripts"))      # bifrost_wake lives here, not in a package

NS = "test-mbx-t133"


def _mailbox():
    return importlib.import_module("core.comm.mailbox")


def _fake():
    from test_t095_m0_mailbox_shadow import _FakeRedis     # reuse the M0 double, do not fork it
    return _FakeRedis()


class _Msg:
    """The shape a runner actually holds when it decides. Deliberately NOT a dict: the seam has to
    work against the live message object, which is what makes the identity question real."""

    def __init__(self, frm="deepseek", to="claude", kind="request",
                 content="please review the fence", ts="1785500000", meta=None, mid="1785500000-0"):
        self.frm, self.to, self.kind = frm, to, kind
        self.content, self.ts, self.meta, self.id = content, ts, (meta or {}), mid


def _seed(mbx, client, msg, agent="claude"):
    fields = {"frm": msg.frm, "to": msg.to, "kind": msg.kind, "ts": msg.ts, "content": msg.content}
    sha = mbx._ingest_one(client, NS, agent, "work_inbox", msg.id, fields)
    assert sha, "ingest refused a normal directed message"
    return sha


# ---- M5: a relaunch outwaits a corpse instead of exiting -----------------------------------------

def test_a_relaunch_waits_out_a_dead_predecessors_key(monkeypatch):
    """The friction paid for repeatedly on 2026-08-02: kill a runner, relaunch three seconds later,
    get refused because the corpse's key still has TTL, and the seat stays DOWN until a human
    notices. The refusal is correct; the exit is the watcher woe."""
    from core.comm import runner_lock as rl
    calls = {"n": 0}

    def _acq(agent, token, ttl=None):
        calls["n"] += 1
        return calls["n"] >= 3          # the dead holder's key lapses on the third try
    monkeypatch.setattr(rl, "acquire", _acq)
    monkeypatch.setattr(rl.time, "sleep", lambda s: None)
    assert rl.acquire_waiting("kimi", "tok", wait_s=30) is True
    assert calls["n"] == 3


def test_a_LIVE_holder_is_never_evicted(monkeypatch):
    """The property that must not be traded for the convenience above. Waiting was chosen over a
    stale-PID steal precisely because a recycled pid or a paused process would let a steal evict a
    live holder and produce the split-brain this lock exists to prevent."""
    from core.comm import runner_lock as rl
    monkeypatch.setattr(rl, "acquire", lambda a, t, ttl=None: False)
    monkeypatch.setattr(rl.time, "sleep", lambda s: None)
    assert rl.acquire_waiting("kimi", "tok", wait_s=2) is False


def test_the_wait_announces_itself_once(monkeypatch):
    """Silence during a wait is indistinguishable from a hang -- the operator must be able to tell
    'waiting for a lock' from 'wedged'."""
    from core.comm import runner_lock as rl
    seen = []
    monkeypatch.setattr(rl, "acquire", lambda a, t, ttl=None: False)
    monkeypatch.setattr(rl, "holder", lambda a: {"pid": 1234})
    monkeypatch.setattr(rl.time, "sleep", lambda s: None)
    rl.acquire_waiting("kimi", "tok", wait_s=3, on_wait=lambda h: seen.append(h))
    assert len(seen) == 1 and seen[0]["pid"] == 1234


# ---- M4: the send door stops calling a working seat unattended ----------------------------------

def _bus(monkeypatch, beat_age, pulse_age):
    """A Bus with its two liveness probes stubbed. Policy only -- no connection.

    Stubs go through monkeypatch so they are UNDONE at teardown. Assigning the module attributes
    directly would leak a fake roster into every later test in the session, which is a slower and
    much more confusing version of the exact defect this file is about: a surface reporting
    something that is not true.
    """
    from core.comm.bus import Bus
    import core.comm.roster as _roster
    import core.comm.liveness as _liveness
    b = Bus.__new__(Bus)
    b.ns, b._client, b.UNATTENDED_S = "test-ns", None, 300.0
    rows = [] if beat_age is None else [{"agent": "kimi", "beat_age_s": beat_age}]
    monkeypatch.setattr(_roster, "roster", lambda ns, client=None: rows)
    monkeypatch.setattr(_liveness, "progress_age", lambda a: pulse_age)
    return b


def test_a_fresh_beat_is_attended(monkeypatch):
    assert _bus(monkeypatch, beat_age=5.0, pulse_age=None)._recipient_liveness("kimi")[0] is True


def test_a_stale_beat_with_a_live_pulse_is_ATTENDED(monkeypatch):
    """THE FIX. On 2026-08-02 UNATTENDED RECIPIENT fired for kimi and deepseek while both runners
    were demonstrably working -- a seat mid-API-call does not beat. The pulse is stamped at real
    progress points and rescues exactly that case."""
    assert _bus(monkeypatch, beat_age=990.0, pulse_age=1.2)._recipient_liveness("kimi")[0] is True


def test_a_stale_beat_with_no_pulse_is_still_unattended(monkeypatch):
    """The warning must survive: a genuinely dead seat still reports as one."""
    assert _bus(monkeypatch, beat_age=990.0, pulse_age=None)._recipient_liveness("kimi")[0] is False


def test_no_seat_at_all_but_a_live_pulse_is_attended(monkeypatch):
    """A runner that never registered a roster row is still working if it is pulsing."""
    assert _bus(monkeypatch, beat_age=None, pulse_age=0.5)._recipient_liveness("kimi")[0] is True


def test_an_unreadable_pulse_falls_back_to_the_beat(monkeypatch):
    """Fail-open DIRECTION: an unreadable pulse must not invent liveness, only fail to rescue."""
    import core.comm.liveness as _liveness

    def _boom(_a):
        raise RuntimeError("pulse store down")

    b = _bus(monkeypatch, beat_age=990.0, pulse_age=None)
    monkeypatch.setattr(_liveness, "progress_age", _boom)
    assert b._recipient_liveness("kimi")[0] is False


def test_the_real_pulse_reader_actually_works():
    """GUARDS AGAINST THE MONKEYPATCH TRAP. Every pin above stubs progress_age, so all of them
    would still pass if the real reader were a no-op -- fail-open probes plus monkeypatched pins
    equal an invisible no-op, which this repo has already been burned by. This one calls the real
    pulse and the real reader against the real store."""
    import importlib
    liveness = importlib.import_module("core.comm.liveness")
    liveness = importlib.reload(liveness)          # undo any stub a sibling test installed
    agent = "t133-pulse-probe"
    if not liveness.pulse(agent, "t133 verification"):
        pytest.skip("no live store for the pulse probe")
    age = liveness.progress_age(agent)
    assert age is not None and age < 30, f"the real reader returned {age!r}"
    assert liveness.progress_age("t133-agent-that-never-pulsed") is None


# ---- M3: mail from seats that no longer exist stops competing with live work --------------------

def _aged(mbx, client, msg, agent="claude", age_h=48.0):
    """Seed an entry and backdate it, so age-gated behaviour can be tested without waiting."""
    sha = _seed(mbx, client, msg, agent)
    k = mbx._keys(NS, agent)
    client.hset(k["msg"] + sha, mapping={"ts_s": str(__import__("time").time() - age_h * 3600)})
    return sha


def test_a_retired_seats_old_mail_is_declined_with_a_reason():
    """TODAY'S FAILURE, and the one this arc had not touched: kimi spent three turns answering
    codex_root_019fab2d -- a seat that no longer exists -- while a live directed ask sat unhandled.
    The sweep DECLARES rather than deletes, which is what makes it legible AND (via M2) stops it
    waking anyone. A sweep that silently dropped mail would be the silent-loss mechanism that looks
    safe."""
    mbx = _mailbox()
    client = _fake()
    ghost = _Msg(frm="codex_root_019fab2d", kind="nudge", content="a corpse's nudge")
    sha = _aged(mbx, client, ghost)
    r = mbx.retire_ghost_mail(NS, "claude", client=client, dry_run=False,
                              is_live=lambda s: s != "codex_root_019fab2d",
                              incarnation="sweep")
    assert r["retired"] == 1, r
    st = mbx.state_for(NS, "claude", sha, client=client)
    assert st["intent"]["intent"] == "decline"
    assert "codex_root_019fab2d" in st["intent"]["note"], "the reason must name the dead sender"


def test_a_bare_fleet_id_is_never_a_ghost():
    """THE NEAR-MISS, pinned. The first version of the sweep asked live_incarnations() whether a
    sender was up RIGHT NOW. It reported deepseek absent while deepseek's runner was demonstrably
    running, and proposed declining 939 of 1000 messages -- most of the mailbox -- on the word of a
    liveness sensor that lies. Only the dry-run default stood between that sensor and mass
    auto-declining live mail. The question is not "is it live" but "can it ever come back"."""
    mbx = _mailbox()
    for bare in ("deepseek", "kimi", "claude", "deepseek-ui", "sol"):
        assert mbx._sender_can_return(bare) is True, bare


def test_a_dead_incarnation_id_cannot_come_back():
    """The actual failure: kimi spent three turns answering codex_root_019fab2d. An id naming ONE
    session is unreachable by construction once that session ends."""
    mbx = _mailbox()
    assert mbx._sender_can_return("codex_root_019fab2d") is False
    assert mbx._sender_can_return("claude#30e6af5c") is False


def test_unreadable_liveness_never_retires():
    """A sweep must not retire mail on ignorance -- the fail direction that matters."""
    mbx = _mailbox()
    import core.comm.incarnation as inc
    orig = inc.live_incarnations
    try:
        inc.live_incarnations = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("down"))
        assert mbx._sender_can_return("codex_root_019fab2d") is True
    finally:
        inc.live_incarnations = orig


def test_a_dry_run_changes_nothing():
    """It writes to mail state, so the operator sees the list before anything moves."""
    mbx = _mailbox()
    client = _fake()
    sha = _aged(mbx, client, _Msg(frm="ghost_seat"))
    r = mbx.retire_ghost_mail(NS, "claude", client=client, is_live=lambda s: False,
                              incarnation="sweep")
    assert r["would_retire"] == 1 and r.get("retired", 0) == 0
    assert mbx.state_for(NS, "claude", sha, client=client)["intent"] is None


def test_a_live_senders_mail_is_never_touched():
    mbx = _mailbox()
    client = _fake()
    sha = _aged(mbx, client, _Msg(frm="deepseek"))
    r = mbx.retire_ghost_mail(NS, "claude", client=client, dry_run=False,
                              is_live=lambda s: True, incarnation="sweep")
    assert r["retired"] == 0
    assert mbx.state_for(NS, "claude", sha, client=client)["intent"] is None


def test_fresh_mail_from_a_briefly_down_seat_is_not_a_ghost():
    """A seat that is restarting is not a retired seat. Age is the discriminator, and without it a
    sweep would decline mail from every peer that happened to be between processes -- which is most
    of them, most of the time, in this fleet."""
    mbx = _mailbox()
    client = _fake()
    sha = _aged(mbx, client, _Msg(frm="kimi"), age_h=0.2)
    r = mbx.retire_ghost_mail(NS, "claude", client=client, dry_run=False,
                              is_live=lambda s: False, min_age_h=24.0, incarnation="sweep")
    assert r["retired"] == 0
    assert mbx.state_for(NS, "claude", sha, client=client)["intent"] is None


def test_the_operator_is_never_a_ghost():
    """Daniil's mail is never retired, however old and however dead the sending surface looks."""
    mbx = _mailbox()
    client = _fake()
    for frm in ("user", "daniel", "daniil"):
        sha = _aged(mbx, client, _Msg(frm=frm, content=f"from {frm}"))
        mbx.retire_ghost_mail(NS, "claude", client=client, dry_run=False,
                              is_live=lambda s: False, incarnation="sweep")
        assert mbx.state_for(NS, "claude", sha, client=client)["intent"] is None, frm


def test_a_seat_that_already_adjudicated_is_not_overruled():
    """The sweep only touches UNHANDLED mail. Re-declaring over a seat's own judgement would make
    an automated broom outrank a reader who actually looked."""
    mbx = _mailbox()
    client = _fake()
    msg = _Msg(frm="ghost_seat")
    sha = _aged(mbx, client, msg)
    mbx.declare_for_message("claude", msg, "defer", incarnation="inc1", ns=NS, client=client,
                            note="I will come back to this")
    r = mbx.retire_ghost_mail(NS, "claude", client=client, dry_run=False,
                              is_live=lambda s: False, incarnation="sweep")
    assert r["retired"] == 0
    assert mbx.state_for(NS, "claude", sha, client=client)["intent"]["intent"] == "defer"


# ---- M2: the wake path finally has a vocabulary for "already dealt with" ------------------------

def _wake():
    return importlib.import_module("bifrost_wake")


def _wm(**kw):
    """A message shaped for wake_worthy."""
    d = {"frm": "deepseek", "to": "claude", "kind": "request", "content": "do the thing",
         "ts": "1785500000", "meta": {}}
    d.update(kw)
    return _Msg(**{k: v for k, v in d.items() if k in
                   ("frm", "to", "kind", "content", "ts", "meta")})


def test_wake_still_fires_on_mail_nobody_has_dealt_with():
    """The regression guard, first: the whole point is to stop RE-firing, never to stop firing."""
    w = _wake()
    assert w.wake_worthy(_wm(), agent="claude") is True


def test_wake_does_not_re_fire_on_mail_this_seat_already_settled(monkeypatch):
    """THE re-arm loop, and the pod design named its cause exactly: the watcher has no vocabulary
    for 'seen'. It has one now -- a declaration -- and this is the line that reads it."""
    w = _wake()
    monkeypatch.setattr(w, "_declared_intent_for", lambda m, agent: "act")
    assert w.wake_worthy(_wm(), agent="claude") is False
    monkeypatch.setattr(w, "_declared_intent_for", lambda m, agent: "decline")
    assert w.wake_worthy(_wm(), agent="claude") is False


def test_a_DEFERRED_message_may_still_wake(monkeypatch):
    """`defer` means "not yet", not "no". Treating it as settled would silently drop work the seat
    explicitly promised to come back to -- turning a debt into a loss."""
    w = _wake()
    monkeypatch.setattr(w, "_declared_intent_for", lambda m, agent: "defer")
    assert w.wake_worthy(_wm(), agent="claude") is True


def test_the_operator_always_breaks_through_even_if_settled(monkeypatch):
    """Non-negotiable, and it has a receipt: the 2026-07-15 "I'm back!" incident, where every idle
    seat slept through the human. This slice must not become a second way to do that, so the
    operator path returns before the settled check is ever consulted."""
    w = _wake()
    monkeypatch.setattr(w, "_declared_intent_for", lambda m, agent: "act")
    assert w.wake_worthy(_wm(frm="user"), agent="claude") is True
    assert w.wake_worthy(_wm(frm="daniel"), agent="claude") is True


def test_a_broken_mailbox_makes_wake_fire_not_sleep(monkeypatch):
    """FAIL OPEN, and the direction matters more here than anywhere else in the slice. A mailbox
    outage that silenced a seat would trade a bookkeeping fault for missed mail -- strictly worse
    than the re-arm it prevents."""
    w = _wake()

    def _boom(m, agent):
        raise RuntimeError("redis down")

    monkeypatch.setattr(w, "_declared_intent_for", _boom)
    assert w.wake_worthy(_wm(), agent="claude") is True


# ---- the transport seam that made the identity wrong in the first place -------------------------

def test_the_bus_carries_the_packet_sha_onto_the_message():
    """FOUND LIVE, not in a fixture. bus._to_msg built a Message from the raw stream fields and
    dropped the top-level `sha` -- while this same module's dedup doctrine reads "dedupe by sha,
    never by stream id". The mailbox index keys entries by that sha; a runner holding a Message
    could only content-hash, so every declaration landed on an entry that did not exist. The
    symptom was eight consecutive "no mailbox entry for sha fb..." lines, the `fb` prefix being the
    content-fallback basis announcing itself.
    """
    from core.comm.bus import Bus
    b = Bus.__new__(Bus)                       # no connection needed: _to_msg is pure
    m = b._to_msg("1785700000-0", {
        "frm": "claude", "to": "kimi", "kind": "note", "content": '"hello"',
        "ts": "2026-08-02T22:00:00+00:00", "meta": "{}", "parts": "[]",
        "sha": "c7621c13cfcbd8c12b0f24b5c665056b75bfc731872ddc06c307e7d5a5f9"})
    assert m.meta.get("sha") == "c7621c13cfcbd8c12b0f24b5c665056b75bfc731872ddc06c307e7d5a5f9"

    from core.comm.mailbox import identity_of
    ident, basis = identity_of({"frm": m.frm, "to": m.to, "kind": m.kind,
                                "content": m.content, "ts": m.ts}, m.meta)
    assert basis == "packet_sha", f"identity fell back to {basis}; the index would not be found"


def test_carrying_the_sha_never_clobbers_a_meta_that_has_one():
    from core.comm.bus import Bus
    b = Bus.__new__(Bus)
    m = b._to_msg("1-0", {"frm": "a", "to": "b", "kind": "note", "content": '"x"', "ts": "t",
                          "meta": '{"sha": "already-mine"}', "parts": "[]", "sha": "transport"})
    assert m.meta["sha"] == "already-mine"


# ---- the identity seam: the whole slice fails silently if this is wrong -------------------------

def test_a_declaration_lands_on_the_message_that_was_indexed():
    """THE integration risk. The runner computes identity from the message it holds; the index
    computed it at ingest. If they disagree, every declare lands on a sha with no entry and the
    whole slice fails SILENTLY -- mail would still read unhandled while the runner believed it had
    declared. This pin is the falsifier for that."""
    mbx = _mailbox()
    client, msg = _fake(), _Msg()
    sha = _seed(mbx, client, msg)

    r = mbx.declare_for_message("claude", msg, "act", incarnation="inc1", ns=NS, client=client)
    assert r.get("ok") is True, r
    assert r.get("sha") == sha, "the runner and the index disagree about this message's identity"


def test_a_declared_message_stops_reading_as_unhandled():
    """The symptom Daniil actually feels: work is done and the surface still says nobody has
    touched it."""
    mbx = _mailbox()
    client, msg = _fake(), _Msg()
    sha = _seed(mbx, client, msg)
    mbx.declare_for_message("claude", msg, "decline", incarnation="inc1", ns=NS, client=client,
                            note="not answerable by this seat")
    st = mbx.state_for(NS, "claude", sha, client=client)
    assert st["found"] and st["intent"] and st["intent"]["intent"] == "decline"
    assert st["read_but_undeclared"] is False, "declared mail must stop reading as undeclared"
    intents = mbx.intents_of(NS, "claude", sha, client=client)
    assert intents, "a declared message recorded no intent"
    assert intents[-1]["intent"] == "decline"
    assert intents[-1].get("note")


def test_opening_records_seen_so_a_watcher_finally_has_a_vocabulary():
    """`seen_by` is the field the pod design names as the structural cause of the wake loop --
    'the watcher's vocabulary; today it has none'. It exists. Nothing called it."""
    mbx = _mailbox()
    client, msg = _fake(), _Msg()
    sha = _seed(mbx, client, msg)
    mbx.declare_for_message("claude", msg, "act", incarnation="inc1", ns=NS, client=client)
    seen = mbx.seen_by(NS, "claude", sha, client=client)
    assert seen and any(s.get("incarnation") == "inc1" for s in seen)


# ---- it must never be able to break the runner --------------------------------------------------

def test_a_broken_mailbox_cannot_break_the_runner():
    """FAIL-OPEN toward transport is the module's own standing invariant. Mail bookkeeping that can
    raise into the consume loop would trade a mail bug for a dead seat -- strictly worse than the
    problem being fixed."""
    mbx = _mailbox()

    class _Exploding:
        def __getattr__(self, _n):
            def boom(*a, **k):
                raise RuntimeError("redis is down")
            return boom

    r = mbx.declare_for_message("claude", _Msg(), "act", incarnation="inc1", ns=NS,
                                client=_Exploding())
    assert r.get("ok") is False, "a failure must be reported, not raised"
    assert "reason" in r


def test_an_unknown_intent_is_refused_not_silently_accepted():
    mbx = _mailbox()
    client, msg = _fake(), _Msg()
    _seed(mbx, client, msg)
    r = mbx.declare_for_message("claude", msg, "maybe-later", incarnation="inc1", ns=NS,
                                client=client)
    assert r.get("ok") is False and "maybe-later" in str(r.get("reason", ""))


def test_declaring_indexes_mail_the_follower_has_not_reached_yet():
    """FOUND LIVE. The index ingests on READ, so a message a runner is handling right now usually
    has no entry -- and the declaration had nothing to attach to. That was the SECOND cause of the
    "no mailbox entry for sha" run; the first was the bus dropping the packet sha. A seat actively
    adjudicating a message is the strongest evidence that it is mail addressed to that seat."""
    mbx = _mailbox()
    client, msg = _fake(), _Msg(kind="request", content="never ingested by a reader")
    r = mbx.declare_for_message("claude", msg, "act", incarnation="inc1", ns=NS, client=client)
    assert r.get("ok") is True, r
    st = mbx.state_for(NS, "claude", r["sha"], client=client)
    assert st["found"] and st["intent"]["intent"] == "act"
    assert st["body"] == "never ingested by a reader", "the body must be captured, not just the id"


def test_a_kind_the_mailbox_does_not_carry_is_refused_honestly():
    """Not every envelope is mail. A trace is not addressed correspondence, and the seam must say
    so rather than mint an entry for it -- absent and empty are different facts."""
    mbx = _mailbox()
    client = _fake()
    r = mbx.declare_for_message("claude", _Msg(kind="trace", content="tool call"), "act",
                                incarnation="inc1", ns=NS, client=client)
    assert r.get("ok") is False and "no mailbox entry" in str(r.get("reason", "")).lower()


# ---- non-destruction: the invariant the whole M1 layer is built on ------------------------------

def test_declaring_touches_no_cursor():
    """mailbox.py's containment invariant, quoted: every write lands inside {ns}:mailbox:*, so the
    mailbox touches no cursor, no ack, no send, no wake state. The runner seam must inherit that --
    the point is a read receipt that is NOT the cursor, so writing one that moves a cursor would
    reintroduce the exact conflation being removed."""
    mbx = _mailbox()
    client, msg = _fake(), _Msg()
    _seed(mbx, client, msg)
    before = {k: v for k, v in getattr(client, "kv", {}).items() if "mailbox" not in k}
    mbx.declare_for_message("claude", msg, "act", incarnation="inc1", ns=NS, client=client)
    after = {k: v for k, v in getattr(client, "kv", {}).items() if "mailbox" not in k}
    assert before == after, "a declaration wrote outside the mailbox namespace"


def test_a_second_declaration_by_the_same_seat_is_recorded_not_collapsed():
    """A seat that declares `defer` and later `act` has said two true things in order. Collapsing
    them would erase the history a cold seat reads to understand what happened."""
    mbx = _mailbox()
    client, msg = _fake(), _Msg()
    sha = _seed(mbx, client, msg)
    mbx.declare_for_message("claude", msg, "defer", incarnation="inc1", ns=NS, client=client)
    mbx.declare_for_message("claude", msg, "act", incarnation="inc1", ns=NS, client=client)
    intents = mbx.intents_of(NS, "claude", sha, client=client)
    assert [i["intent"] for i in intents] == ["defer", "act"]
