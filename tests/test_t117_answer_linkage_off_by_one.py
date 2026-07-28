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
