"""T113 -- AN OVERSIZE SEND SPILLS TO A BLOB; IT DOES NOT LOSE THE TAIL. RED first (M3).

COST US DATA TONIGHT. deepseek's demand-census handoff arrived with:

    [clipped at 8000 chars -- full content did NOT send; resend in chunks]

The tally and the stated disagreement survived; per-case detail past case 30 did
not, and the reconciliation had to record the loss instead of the content. Daniel
asked about this directly earlier in the arc -- "What can we do to remove the 2.5k
limit? fragment and then reconstruct? a staging area on the bus...?"

THE ODD PART: THE TRANSPORT UNDERNEATH ALREADY SOLVES THIS, TWICE.
  * bus._emit auto-fragments any payload over the 64KB MTU into seq/of/whole_sha
    packets and reassembles them (T043) -- a REFUSE-LOUD, never a truncation.
  * core/comm/blobs.py is a content-addressed store whose stated design is the
    "lossless-pointer rule": large payloads live as blobs, the wire carries a
    tiny blob:<sha>, the bytes are fetched on demand.

So the bus can carry it and the blob store can hold it. The TOOL door clips it
anyway, at 8000 chars, and the bytes are gone -- `bound_tool_text` keeps a prefix
and appends a confession. RB-5 ("a bound must confess, never clip silently") is
honoured, and that is exactly what makes this worth fixing rather than excusing:
the confession is doing its job, telling us plainly that we destroy data on a
path where nothing below us needs us to.

WHY THE BOUND EXISTS AND WHY IT STAYS: an 8000-char message is already a lot to
push into one runner turn. That is a RENDERING concern. It is not a reason to
destroy the tail -- clip what the reader SEES, keep what the sender SAID.

  P1  UNDER THE BOUND IS UNTOUCHED. No blob, no pointer, byte-identical.
  P2  OVER THE BOUND KEEPS EVERY BYTE: the full text is recoverable from the ref.
  P3  THE WIRE STAYS SMALL: the delivered text still respects the bound.
  P4  THE POINTER IS IN THE TEXT, not only in meta -- a model reads the body,
      and a retrieval handle nobody can see is the lookback battery's disease
      (content preserved, handle lost) repeated on the bus.
  P5  THE CONFESSION SURVIVES AND IMPROVES: it must say the content is FETCHABLE,
      not that it "did NOT send". A confession that overstates the loss teaches
      the sender to re-send the whole thing -- which is the T112 defect, fed.
  P6  META CARRIES THE SPILL FACTS durably (ref + true length).
  P7  A BLOB-STORE FAILURE FALLS BACK TO THE OLD CLIP. Degrade to today's
      behaviour, never to a dropped message.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import packet_spec
from core.comm.blobs import get_blob_store

LIMIT = packet_spec.TOOL_SEND_TEXT_MAX
BIG = ("CENSUS CASE DETAIL. " * 900)[:LIMIT * 2]        # ~2x the door
assert len(BIG) > LIMIT


# --------------------------------------------------------------- P1
def test_p1_under_the_bound_is_untouched():
    small = "a short handoff"
    out, meta = packet_spec.spill_tool_text(small)
    assert out == small, f"a message that fits must pass through byte-identical: {out!r}"
    assert not meta, f"no spill metadata for a message that fits: {meta}"


# --------------------------------------------------------------- P2 the whole point
def test_p2_over_the_bound_keeps_every_byte():
    out, meta = packet_spec.spill_tool_text(BIG)
    ref = (meta or {}).get("spill_ref")
    assert ref, f"an oversize send must produce a retrievable ref, got meta={meta}"
    recovered = get_blob_store().get(ref)
    assert recovered is not None, f"blob {ref} is not readable back"
    assert recovered.decode("utf-8") == BIG, (
        "THE TAIL WAS LOST. This is the defect: deepseek's census detail past case 30 "
        "went into the confession instead of into the store. Every byte the sender said "
        "must be recoverable, or the bound is a shredder with an apology attached.")


# --------------------------------------------------------------- P3
def test_p3_the_wire_stays_small():
    out, _ = packet_spec.spill_tool_text(BIG)
    assert len(out) <= LIMIT, (
        f"the delivered text grew to {len(out)}; the bound exists to protect the "
        f"recipient's turn and spilling must not defeat it")


# --------------------------------------------------------------- P4
def test_p4_the_pointer_is_visible_in_the_body():
    """A model reads the BODY. A retrieval handle that lives only in envelope meta is
    exactly the lookback battery's disease -- content preserved, handle unreachable."""
    out, meta = packet_spec.spill_tool_text(BIG)
    assert str(meta["spill_ref"]) in out, (
        f"the ref must appear in the text the reader actually sees: {out[-300:]!r}")


# --------------------------------------------------------------- P5
def test_p5_the_confession_says_fetchable_not_lost():
    """'full content did NOT send; resend in chunks' is now FALSE and actively harmful:
    it instructs the sender to re-send, which is the T112 duplicate-ask defect being fed
    by our own error message."""
    out, _ = packet_spec.spill_tool_text(BIG)
    tail = out[-400:].lower()
    assert "did not send" not in tail, (
        f"the confession still claims the content was lost: {tail!r}")
    assert "fetch" in tail or "retriev" in tail, (
        f"the confession must tell the reader HOW to get the rest: {tail!r}")
    assert str(len(BIG)) in out, "say how much there is, so the reader can judge"


# --------------------------------------------------------------- P6
def test_p6_meta_carries_the_spill_facts():
    _, meta = packet_spec.spill_tool_text(BIG)
    assert meta.get("spilled") is True
    assert int(meta.get("spill_len", 0)) == len(BIG), (
        f"the TRUE length must ride the envelope durably: {meta}")


# --------------------------------------------------------------- P7
def test_p7_a_blob_failure_degrades_to_the_old_clip(monkeypatch):
    """Degrade to today's behaviour, never to a dropped message."""
    class _Broken:
        def put(self, data):
            raise RuntimeError("blob store down")

    monkeypatch.setattr(packet_spec, "_blob_store", lambda: _Broken())
    out, meta = packet_spec.spill_tool_text(BIG)
    assert len(out) <= LIMIT and out, "a broken blob store must still deliver a message"
    assert not (meta or {}).get("spill_ref"), "no ref may be advertised when none was stored"
    assert "clipped" in out.lower(), (
        f"falling back must still CONFESS -- RB-5 holds in every branch: {out[-200:]!r}")
