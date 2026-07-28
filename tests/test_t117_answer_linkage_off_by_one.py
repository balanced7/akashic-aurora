"""T117 -- AN ANSWERED ASK MUST STOP REDRIVING. RED first (M3).

THE RECEIPT, from the live bus. kimi complained it was being asked the same thing
a fourth time. It was right, and the cause was not the sender being impatient --
it was the expectation machinery failing to notice it had been answered:

    ask   1785226575154-0  to kimi   (armed expectation, keyed on this id)
    reply 1785228386835-0  frm kimi  meta.answers = '1785226575153-0'
                                                              ^^^ off by one

Same message, two ids. The bus dual-writes to the lane stream and the legacy
stream, so one send produces two stream ids one apart. The EXPECTATION is armed on
the id `send()` returned (legacy); the PEER answers against the id it actually
received (lane). Exact linkage compares them and finds no match.

That alone would be survivable -- there is a FIFO fallback for exactly this. But
the fallback is skipped whenever `meta.answers` is present at all:

    for r in replies:                      # 2) FIFO fallback: one clear per reply
        if (getattr(r, "meta", None) or {}).get("answers"):
            continue                       # <-- a NON-MATCHING answers id lands here

So a reply that names an id we do not recognise is treated as "already handled by
exact linkage" when exact linkage in fact rejected it. The expectation survives,
the deadline expires, and it REDRIVES -- three times, at 08:50, 09:34 and 12:41,
each one a full turn kimi spent re-answering a question it had answered.

Measured on the live fleet before writing this: sweep('claude') returned {} with
four armed expectations, 43 visible answers, and 9 of them from kimi.

It is also the arc's recurring shape once more: a signal emitted correctly (kimi
DID answer, with correct linkage metadata) and not received by the reader that
needed it, because the two sides identify the same message by different names.

  P1  A REPLY WHOSE `answers` ID MATCHES NOTHING STILL CLEARS VIA FIFO. The
      fallback exists for unlinked replies; an UNRECOGNISED link is unlinked.
  P2  THE DUAL-WRITE ID PAIR RESOLVES. An ask armed on one of the two ids a
      single send produces is settled by an answer naming the other.
  P3  AN ANSWERED ASK NEVER REDRIVES. The end-to-end property, stated directly.
  P4  EXACT LINKAGE STILL WINS. When the id does match, it clears that specific
      expectation and not merely the oldest -- the fix must not blunt the
      precise path into the fuzzy one.
  P5  A REPLY FROM THE WRONG AGENT CLEARS NOTHING. Widening the match must not
      let anyone's reply settle anyone's ask.
"""

import json
import os
import sys
import time
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import expectations as E

NS = "t117"


@pytest.fixture(autouse=True)
def _env():
    saved = os.environ.get("BIFROST_NAMESPACE")
    os.environ["BIFROST_NAMESPACE"] = NS
    yield
    if saved is None:
        os.environ.pop("BIFROST_NAMESPACE", None)
    else:
        os.environ["BIFROST_NAMESPACE"] = saved


class _Reply:
    """The shape sweep() reads off a Message: id, frm, kind, meta."""

    def __init__(self, mid, frm, answers=None, kind="reply"):
        self.id, self.frm, self.kind = mid, frm, kind
        self.meta = {"answers": answers} if answers else {}


def _arm(sender, oid, to, anchor, created, deadline_past=True, redrives=2):
    c = E._client()
    if c is None:
        pytest.skip("redis offline")
    rec = {"to": to, "kind": "question", "content": "please review", "anchor": anchor,
           "created": created, "within_s": 1800, "redrives_left": redrives, "attempt": 0,
           "deadline_ts": (time.time() - 60) if deadline_past else (time.time() + 3600)}
    c.hset(E._key(sender), oid, json.dumps(rec))


@pytest.fixture
def sender():
    s = f"t117{uuid.uuid4().hex[:6]}"
    yield s
    c = E._client()
    if c is not None:
        c.delete(E._key(s))


def _sweep_with(sender, replies, monkeypatch):
    monkeypatch.setattr(E, "_answers_since", lambda *a, **k: replies)
    return E.sweep(sender)


# --------------------------------------------------------------- P1
def test_p1_an_unrecognised_answers_id_still_clears_via_fifo(sender, monkeypatch):
    """The live case: kimi answered with meta.answers='...153-0' against an
    expectation keyed '...154-0'. Exact linkage rejected it; the FIFO fallback then
    SKIPPED it because `answers` was truthy. An unrecognised link is unlinked."""
    _arm(sender, "1785226575154-0", "kimi", "1785226472805-0", 1785226575.19)
    out = _sweep_with(sender, [_Reply("1785228386835-0", "kimi",
                                      answers="1785226575153-0")], monkeypatch)
    assert "1785226575154-0" in out["cleared"], (
        f"REDRIVE ON AN ANSWERED ASK: the reply named an id we do not hold, so exact "
        f"linkage rejected it -- and the FIFO fallback skipped it anyway because "
        f"`answers` was merely PRESENT. kimi paid three extra turns for this. out={out}")
    assert not out["redriven"], f"an answered ask must never redrive: {out}"


# --------------------------------------------------------------- P2
def test_p2_the_dual_write_id_pair_resolves(sender, monkeypatch):
    """One send, two stream ids one apart (lane + legacy). The expectation is armed
    on the id send() returned; the peer answers against the id it received."""
    _arm(sender, "1785226575154-0", "kimi", "1785226472805-0", 1785226575.19)
    out = _sweep_with(sender, [_Reply("1785228386835-0", "kimi",
                                      answers="1785226575153-0")], monkeypatch)
    assert out["cleared"] == ["1785226575154-0"], (
        f"the sibling id of the SAME send must settle the ask: {out}")


# --------------------------------------------------------------- P3
def test_p3_an_answered_ask_never_redrives(sender, monkeypatch):
    """The end-to-end property, stated where a reader will find it."""
    _arm(sender, "1785226575154-0", "kimi", "1785226472805-0", 1785226575.19)
    _sweep_with(sender, [_Reply("1785228386835-0", "kimi",
                                answers="1785226575153-0")], monkeypatch)
    c = E._client()
    assert "1785226575154-0" not in (c.hgetall(E._key(sender)) or {}), (
        "the expectation must be GONE, not merely reported cleared")


# --------------------------------------------------------------- P4
def test_p4_exact_linkage_still_wins(sender, monkeypatch):
    """Widening the fallback must not blunt the precise path: an exactly-linked reply
    clears ITS OWN expectation, not merely the oldest one."""
    _arm(sender, "1785220000000-0", "kimi", "1785219000000-0", 1785220000.0)   # older
    _arm(sender, "1785226575154-0", "kimi", "1785226472805-0", 1785226575.19)  # newer
    out = _sweep_with(sender, [_Reply("1785228386835-0", "kimi",
                                      answers="1785226575154-0")], monkeypatch)
    assert out["cleared"] == ["1785226575154-0"], (
        f"an exact link must clear the ask it NAMES, never the oldest: {out}")


# --------------------------------------------------------------- P5
def test_p5_a_reply_from_the_wrong_agent_clears_nothing(sender, monkeypatch):
    """Widening the match must not let anyone's reply settle anyone's ask."""
    _arm(sender, "1785226575154-0", "kimi", "1785226472805-0", 1785226575.19,
         deadline_past=False)
    out = _sweep_with(sender, [_Reply("1785228386835-0", "deepseek",
                                      answers="1785226575153-0")], monkeypatch)
    assert not out["cleared"], (
        f"deepseek's reply must not settle an ask addressed to kimi: {out}")


# --------------------------------------------------------------- P6/P7 sol's NO-GO
def test_p6_the_reply_settles_the_ASK_IT_NAMES_not_the_fifo_oldest(sender, monkeypatch):
    """Sol's NO-GO on f813e34, adversarial repro. The live twin ids differ in the
    MILLISECOND (1785226575154-0 vs ...153-0, seq 0 in both); _resolve_link held ms
    fixed and adjusted seq, so on the real shape it returned None -- and my P1-P3
    passed via the FIFO fallback, which with ONE armed expectation happens to clear
    the right one. With TWO armed asks to the same target, FIFO clears the OLDEST:
    the reply meant for the newer ask silently settles the older work, and the
    intended ask stays armed and redrives. A false green wearing a green suite.

    The fix must resolve by EVIDENCE (the dual-id alias captured at _emit, where
    both ids are actually known), never by id arithmetic -- Sol's words: independent
    streams can share or differ in ms, and adjacent sends collide."""
    from core.comm.bus import Bus as _Bus
    s = sender
    c = E._client()
    # Arm two expectations to the same target. The OLDER is the FIFO trap.
    _arm(s, "1785226575000-0", "kimi", "1785226574000-0", 1785226575.0)
    _arm(s, "1785226575154-0", "kimi", "1785226575100-0", 1785226575.19)
    # The alias a real dual-write send records: sibling lane id -> returned id.
    c.set(f"{E._ns()}:idalias:1785226575153-0", "1785226575154-0", ex=600)
    try:
        out = _sweep_with(s, [_Reply("1785228386835-0", "kimi",
                                     answers="1785226575153-0")], monkeypatch)
        assert out["cleared"] == ["1785226575154-0"], (
            f"WRONG WORK SETTLED: the reply names the sibling of the NEWER ask, and the "
            f"sweep cleared {out['cleared']} -- FIFO ate the oldest while the intended "
            f"ask stays armed to redrive. Resolution must follow the alias, not the "
            f"queue order: {out}")
        left = c.hgetall(E._key(s)) or {}
        assert "1785226575000-0" in left, "the OLDER unanswered ask must remain armed"
    finally:
        c.delete(f"{E._ns()}:idalias:1785226575153-0")


def test_p7_the_bus_records_the_dual_id_alias_at_emit():
    """The alias is captured where both ids are KNOWN -- inside _emit, when the lane
    and legacy writes both return. Everywhere else is reconstruction; here it is a
    fact. Redis-ephemeral with a TTL, same lifecycle as the expectation itself."""
    import uuid as _uuid
    from core.comm.bus import Bus as _Bus
    ns = "t117p7"
    a, b = f"snd{_uuid.uuid4().hex[:6]}", f"rcv{_uuid.uuid4().hex[:6]}"
    bus = _Bus(a, namespace=ns, promote=False)
    if not bus.online:
        pytest.skip("bus offline")
    try:
        mid = bus.send(b, "question", "alias pin: does the emit record the twin?")
        assert mid
        aliases = list(bus._client.scan_iter(match=f"{ns}:idalias:*", count=200))
        vals = {bus._client.get(k) for k in aliases}
        assert mid in vals, (
            f"NO ALIAS RECORDED: a dual-write send produced no idalias -> {mid}. "
            f"Without it, a reply naming the sibling id can only be resolved by "
            f"arithmetic (proven wrong) or FIFO (proven to settle the wrong work). "
            f"aliases={aliases}")
    finally:
        for k in bus._client.scan_iter(match=f"{ns}:*", count=500):
            bus._client.delete(k)


# --------------------------------------------------------------- P8 sol's third NO-GO
def test_p8_one_reply_settles_exactly_one_ask_across_sweeps(sender, monkeypatch):
    """Sol's third NO-GO, the sharpest: sweep() re-reads answers from the OLDEST
    anchor every pass, and nothing remembers that a reply already settled
    something. Sweep 1: the reply exact-clears the newer ask -- correct. Sweep 2:
    the SAME stored reply is read again; its target is gone from recs, so the link
    is unrecognised, and FIFO hands it the OLDER ask. One reply, two settlements,
    the second one wrong -- and the older ask's real answer, when it arrives,
    finds nothing left to settle.

    The fix is idempotent settlement: a reply that settled an ask is durably
    marked and never settles again. PER-REPLY markers, not a stream frontier --
    sol's own warning: a frontier could skip a reply needed by a later-armed
    expectation whose anchor predates it."""
    s = sender
    c = E._client()
    _arm(s, "1785226575000-0", "kimi", "1785226574000-0", 1785226575.0,
         deadline_past=False)                                  # older, UNANSWERED
    _arm(s, "1785226575200-0", "kimi", "1785226575100-0", 1785226575.2)   # newer
    reply = _Reply("1785228386835-0", "kimi", answers="1785226575200-0")

    out1 = _sweep_with(s, [reply], monkeypatch)
    assert out1["cleared"] == ["1785226575200-0"], f"sweep 1 must clear the newer: {out1}"

    out2 = _sweep_with(s, [reply], monkeypatch)    # same stored reply, next pass
    assert not out2["cleared"], (
        f"ONE REPLY SETTLED TWO ASKS: the same stored reply cleared again on the "
        f"second sweep -- FIFO handed it the older ask whose real answer has not "
        f"arrived. Settlement must be idempotent per reply: {out2}")
    assert "1785226575000-0" in (c.hgetall(E._key(s)) or {}), (
        "the older unanswered ask must still be armed after both sweeps")


# --------------------------------------------------------------- P9-P11 sol's fence round 2
def test_p9_a_wrong_sender_exact_id_never_clears(sender, monkeypatch):
    """sol: the exact-linkage path never checked WHO answered. A reply from agent X
    naming an id armed for agent Y cleared Y's ask -- the one property P5 guarded on
    the FIFO path was absent from the precise path."""
    _arm(sender, "1785226575154-0", "kimi", "1785226472805-0", 1785226575.19,
         deadline_past=False)
    out = _sweep_with(sender, [_Reply("1785228386835-0", "deepseek",
                                      answers="1785226575154-0")], monkeypatch)
    assert not out["cleared"], (
        f"WRONG SENDER SETTLED THE ASK: deepseek's reply cleared an expectation "
        f"addressed to kimi via the exact-id path: {out}")


def test_p10_marker_write_failure_never_reopens_double_settlement(sender, monkeypatch):
    """sol, fault-injected: _mark_settled ran AFTER hdel, best-effort -- so a failed
    marker SET with a healthy HDEL restored the exact prior defect on the next
    sweep. Settle+mark must be one atomic transition; if the marker cannot be
    written, the expectation must survive (loud redrive beats silent wrong-work)."""
    s = sender
    c = E._client()
    _arm(s, "1785226575000-0", "kimi", "1785226574000-0", 1785226575.0,
         deadline_past=False)                                  # older, UNANSWERED
    _arm(s, "1785226575200-0", "kimi", "1785226575100-0", 1785226575.2)   # newer
    reply = _Reply("1785228386835-0", "kimi", answers="1785226575200-0")

    real_set = c.set
    def _failing_set(k, *a, **kw):
        if "reply_settled" in str(k):
            raise RuntimeError("marker plane down")
        return real_set(k, *a, **kw)
    monkeypatch.setattr(c, "set", _failing_set)
    out1 = _sweep_with(s, [reply], monkeypatch)
    monkeypatch.setattr(c, "set", real_set)

    out2 = _sweep_with(s, [reply], monkeypatch)
    still = c.hgetall(E._key(s)) or {}
    assert "1785226575000-0" in still, (
        f"DOUBLE SETTLEMENT REOPENED: marker write failed, HDEL succeeded anyway, and "
        f"the re-read reply FIFO-cleared the older ask on the next sweep. "
        f"sweep1={out1} sweep2={out2} remaining={sorted(still)}")


def test_p11_a_reply_to_the_redrive_settles_the_original(sender, monkeypatch):
    """sol: a redrive is a NEW send with NEW stream ids; a peer that answers the
    REDRIVE's id (the only id it ever saw) resolved to nothing, so the original
    expectation redrove again -- the T117 disease reborn one generation down.
    The redrive branch must alias its new ids back to the ORIGINAL ask."""
    s = sender
    c = E._client()
    _arm(s, "1785226575154-0", "kimi", "1785226472805-0", 1785226575.19,
         deadline_past=True, redrives=2)

    sent = {}
    class _FakeBus:
        """TEST-DOUBLE WIDTH LESSON, learned by three rounds of ghost-chasing: sweep
        reaches core.comm.bus TWICE -- the redrive's `Bus(sender).send`, and
        `_client()` via get_bus, which CONSTRUCTS Bus per call. The first draft
        replaced the class without `_client`, so `_client()` hit AttributeError,
        the except returned None, and sweep exited at the top looking exactly like
        'the redrive never fired'. A double must satisfy EVERY door the seam uses,
        or it tests a system that does not exist."""
        _client = E._client()                     # the real client: get_bus path stays alive

        def __init__(self, *a, **k): pass

        def send(self, to, kind, content, meta=None):
            sent["mid"] = "1785228000000-0"
            return sent["mid"]

        def tail(self):
            return {"inbox": "0", "bc": "0"}
    import core.comm.bus as bus_mod
    monkeypatch.setattr(bus_mod, "Bus", _FakeBus)

    out1 = _sweep_with(s, [], monkeypatch)          # deadline passed -> redrives
    assert "1785226575154-0" in out1["redriven"], f"precondition: must redrive: {out1}"

    out2 = _sweep_with(s, [_Reply("1785228386900-0", "kimi",
                                  answers=sent["mid"])], monkeypatch)
    assert out2["cleared"] == ["1785226575154-0"], (
        f"REPLY TO THE REDRIVE LOST: the peer answered the only id it ever saw "
        f"(the redrive's) and the original ask did not settle: {out2}")


# --------------------------------------------------------------- P12/P13 sol's receipts
def test_p12_a_broken_settle_transition_preserves_everything(sender, monkeypatch):
    """sol's pre-GREEN review: the first P10 patched c.set -- obsolete the moment the
    atomic Lua landed, so the pin went nominal while proving nothing. This one
    faults the REAL transition (_settle_once) and demands total preservation:
    both asks armed, cleared=[]. Loud redrive beats deletion without receipt."""
    s = sender
    c = E._client()
    _arm(s, "1785226575000-0", "kimi", "1785226574000-0", 1785226575.0,
         deadline_past=False)
    _arm(s, "1785226575200-0", "kimi", "1785226575100-0", 1785226575.2,
         deadline_past=False)
    monkeypatch.setattr(E, "_settle_once", lambda *a, **k: False)
    out = _sweep_with(s, [_Reply("1785228386835-0", "kimi",
                                 answers="1785226575200-0")], monkeypatch)
    assert out["cleared"] == [], f"a failed transition must clear NOTHING: {out}"
    still = c.hgetall(E._key(s)) or {}
    assert "1785226575000-0" in still and "1785226575200-0" in still, (
        f"BOTH expectations must survive a broken settle plane: {sorted(still)}")


def test_p13_redrive_lane_id_settles_only_the_original_never_the_fifo_trap(sender, monkeypatch):
    """sol: the first P11 was n=1 and replied to the fake bus's LEGACY return id --
    it could pass via FIFO with the redrive mapping entirely missing (the original
    masking error, repeated). This one arms an OLDER same-target FIFO trap, dual-
    aliases the redrive (lane sibling -> legacy -> original, the real emit shape),
    and replies against the LANE id a real runner actually sees. Only the newer
    original may clear; the trap must survive."""
    s = sender
    c = E._client()
    _arm(s, "1785226570000-0", "kimi", "1785226569000-0", 1785226570.0,
         deadline_past=False)                                   # the FIFO trap
    _arm(s, "1785226575154-0", "kimi", "1785226575100-0", 1785226575.19,
         deadline_past=True, redrives=2)                        # the original

    sent = {}
    class _FakeBus:
        _client = E._client()
        def __init__(self, *a, **k): pass
        def send(self, to, kind, content, meta=None):
            sent["legacy"] = "1785228000000-0"
            sent["lane"] = "1785227999999-0"
            # the real emit records the dual-id alias both directions
            c.set(f"{E._ns()}:idalias:{sent['lane']}", sent["legacy"], ex=600)
            c.set(f"{E._ns()}:idalias:{sent['legacy']}", sent["lane"], ex=600)
            return sent["legacy"]
        def tail(self):
            return {"inbox": "0", "bc": "0"}
    import core.comm.bus as bus_mod
    monkeypatch.setattr(bus_mod, "Bus", _FakeBus)

    out1 = _sweep_with(s, [], monkeypatch)
    assert "1785226575154-0" in out1["redriven"], f"precondition: {out1}"

    out2 = _sweep_with(s, [_Reply("1785228386900-0", "kimi",
                                  answers=sent["lane"])], monkeypatch)   # LANE id
    assert out2["cleared"] == ["1785226575154-0"], (
        f"the reply names the redrive's LANE id; it must reach the ORIGINAL through "
        f"lane->legacy->original and never fall to FIFO: {out2}")
    still = c.hgetall(E._key(s)) or {}
    assert "1785226570000-0" in still, f"the FIFO trap must survive: {sorted(still)}"
