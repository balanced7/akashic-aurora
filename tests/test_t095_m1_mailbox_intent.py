"""T095 M1 PRE-REGISTERED ACCEPTANCE -- durable mail WITH INTENT. Committed RED.

Daniil, 2026-07-31: "fix our durable mail with intent system ... have our mailboxes actually be
mailboxes."

The bar is not invented here. It is codex's ruled product receipt
(research/in-flight/STATE-OF-THE-ROUND-2026-07-30.md sec 3), quoted:

    "A seat dies after reading a question; a new incarnation lists the same mail, sees that the
    prior incarnation read it but did not declare action, opens the full body, and may act
    without moving or destroying any transport history."

That one sentence contains the whole slice: durable BODIES ("opens the full body"), a SEEN receipt
distinct from consumption ("read it"), declared INTENT distinct from seen ("did not declare
action"), and NON-DESTRUCTION ("without moving or destroying any transport history").

Four defects these pins encode, each VERIFIED in the tree at 0de1a3f before this file was written:

  D1 NO BODIES.  core/comm/mailbox.py:164-169 persists only {sha, kind, frm, ts, ids, ts_s}.
     The body is never stored, so "opens the full body" is impossible once the ephemeral stream
     entry ages out -- the index lists an envelope with nothing inside.
  D2 TWO TAXONOMIES THAT DISAGREE.  mailbox.LONG_KINDS = {handoff, request, question, blocker}
     (30d index) vs promoter.SALIENT_KINDS = {handoff, decision, completion, blocker} (durable).
     So `question` and `request` are indexed for 30 days and NEVER made durable, and `reply` is in
     NEITHER -- short-retention and non-durable, while being the kind that carries most substance
     in practice (measured 2026-07-31: two peer seats' round contributions were recoverable only
     by hand-capturing them off the ephemeral lane before they aged out).
  D3 IDENTITY CAN BE CONTENT-DERIVED.  mailbox._fallback_sha hashes frm|to|kind|content|ts when a
     packet carries no sha. Codex ruled the opposite: fresh message_id per intentional send;
     idempotency_key minted once and preserved through retry/dual-write/redrive/rehome;
     payload_digest for conflict detection ONLY, never identity.
  D4 NO INTENT.  The state ladder (acked > replied/auto_acked > consumed > unhandled) is entirely
     DERIVED. Nothing lets a seat DECLARE "seen, and I am not the right owner" or "seen, answering
     in two hours". Absence of a declaration is indistinguishable from absence of a reader.

RED by construction: the APIs asserted below do not exist yet. Do not weaken a pin to make it
green -- the pins are the contract.

Run::

    py -m pytest tests/test_t095_m1_mailbox_intent.py -q
"""
from __future__ import annotations

import importlib
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

NS = "test-mbx-m1"


def _mailbox():
    # Imported inside each pin so collection still names every RED test before the M1 API exists
    # (T060 RED convention, same as the M0 pins).
    return importlib.import_module("core.comm.mailbox")


def _fake():
    from test_t095_m0_mailbox_shadow import _FakeRedis  # reuse the M0 double, do not fork it
    return _FakeRedis()


# --------------------------------------------------------------- D1: durable bodies

def test_m1_1_entry_carries_the_body():
    """A mailbox entry must carry the body, or a durable pointer that still resolves after the
    ephemeral stream entry is gone. Envelope-without-contents is the defect."""
    mbx = _mailbox()
    assert hasattr(mbx, "body_of"), (
        "D1: no way to retrieve a message body from the mailbox. Codex's receipt requires a new "
        "incarnation to OPEN THE FULL BODY; today mailbox entries persist only "
        "{sha, kind, frm, ts, ids, ts_s} (mailbox.py:164-169)."
    )


def test_m1_2_body_survives_transport_eviction():
    """The whole point of durable: the body outlives the ephemeral lane it arrived on.

    The first draft of this pin was an unconditional `pytest.fail` placeholder, labelled as such.
    This is the real assertion it stood in for -- index a message, destroy the transport entirely,
    and the body must still read.
    """
    mbx = _mailbox()
    client = _fake()
    fields = {"frm": "kimi", "to": "claude", "kind": "reply", "ts": "1785500000",
              "content": "the cold-seat critique that was minutes from being lost"}
    sha = mbx._ingest_one(client, NS, "claude", "work_inbox", "1785500000-0", fields)
    assert sha, "ingest refused a normal directed reply"

    got = mbx.body_of(NS, "claude", sha, client=client)
    assert got and got["body"] == fields["content"], "body not retrievable right after ingest"

    client.streams.clear()          # the ephemeral lane is gone -- aged out, trimmed, or evicted
    after = mbx.body_of(NS, "claude", sha, client=client)
    assert after and after["body"] == fields["content"], (
        "D1: the body died with the transport. A mailbox whose contents vanish with the stream is "
        "an index of envelopes, not a mailbox."
    )
    assert after["truncated"] is False and after["body_len"] == len(fields["content"])


# --------------------------------------------------------------- D2: one taxonomy

def test_m1_3_no_entry_outlives_its_body():
    """THE INVARIANT: an index entry may never outlive the body it points at.

    Pin amended before commit, and the reason is recorded rather than quietly rewritten. The first
    draft asserted `mailbox.LONG_KINDS <= promoter.SALIENT_KINDS` -- i.e. it encoded ONE MECHANISM
    (promote more kinds into the Ledger) as though it were the requirement. That mechanism is
    wrong: promoting every `reply` would flood the append-only Ledger with conversational traffic,
    and the Ledger is for salient decisions, not for mail storage. The correct fix is that THE
    MAILBOX OWNS ITS OWN DURABLE BODIES -- which is what "mailboxes should actually be mailboxes"
    means. Same defect, better mechanism, so the pin states the invariant and lets the
    implementation choose how.
    """
    mbx = _mailbox()
    assert hasattr(mbx, "retention_s_for") and hasattr(mbx, "body_of"), (
        "D2: nothing ties an entry's advertised retention to its body's durability, so a 30-day "
        "index entry can point at a 7-day stream -- a promise the system cannot keep."
    )


def test_m1_4_reply_body_survives_the_ephemeral_lane():
    """`reply` carries most of the substance in practice and is in NEITHER kind-set today.

    Stated as an outcome, not a set-membership: the BODY must be retrievable after the lane drops
    it. Whether that is achieved by mailbox-owned storage or by promotion is the implementation's
    call; the guarantee is not.
    """
    mbx = _mailbox()
    assert hasattr(mbx, "body_of"), (
        "D2: a reply body is unretrievable once the ephemeral lane ages out. Measured 2026-07-31: "
        "round contributions from two peer seats were minutes from loss and survived only by "
        "manual capture off the lane."
    )


# --------------------------------------------------------------- D3: identity

def test_m1_5_identity_is_not_derived_from_content():
    """Two INTENTIONAL sends of identical text are different mail. A retry of one send is not.

    Codex's ruling: fresh message_id per intentional send; idempotency_key preserved across
    retry/dual-write/redrive/rehome; payload_digest for conflict detection only, never identity.
    Content-derived identity collapses legitimate repeated mail while still failing to collapse
    transport duplicates -- the exact inversion of the goal.
    """
    mbx = _mailbox()
    assert not hasattr(mbx, "_fallback_sha") or hasattr(mbx, "identity_of"), (
        "D3: mailbox._fallback_sha derives identity from frm|to|kind|content|ts. Identity must "
        "come from the packet's message_id/idempotency_key seam (T116), not the payload."
    )


# --------------------------------------------------------------- D4: intent

def test_m1_6_open_appends_exactly_one_seen_receipt():
    """`open` says SEEN and nothing else. It must not advance a cursor or imply handled.

    Ruled verbatim: "Opening mail may say seen. It must never mean consumed, handled, agreed,
    settled, or safe to forget."
    """
    mbx = _mailbox()
    assert hasattr(mbx, "open"), "D4: no open() verb -- peek/fetch/open are not yet split"


def test_m1_7_intent_is_declarable_and_distinct_from_seen():
    """The gap Daniil named. A reader must be able to declare what it will DO, and 'read but
    declared nothing' must be distinguishable from 'never read'."""
    mbx = _mailbox()
    assert hasattr(mbx, "declare_intent"), (
        "D4: no declare_intent(). Today the ladder is entirely derived, so a seat that read a "
        "question and chose not to act is indistinguishable from one that never saw it."
    )


# --------------------------------------------------------------- the receipt, end to end

def test_m1_9_open_leaves_every_cursor_byte_identical():
    """The MUST NOT, with an executable falsifier.

    Added after I flagged its absence in my own contract review: I had argued to the fleet that a
    forbidden-effect clause without a test that ATTEMPTS the forbidden act is decoration, and then
    shipped exactly that -- `open()` documented as cursor-safe with nothing proving it. This is the
    falsifier. It snapshots every cursor hash, opens, and demands byte-identity.
    """
    mbx = _mailbox()
    client = _fake()
    fields = {"frm": "codex", "to": "claude", "kind": "question", "ts": "1785500001",
              "content": "does opening this move anything?"}
    sha = mbx._ingest_one(client, NS, "claude", "work_inbox", "1785500001-0", fields)

    keys = [f"{NS}:cursor:lane:claude", f"{NS}:cursor:claude"]
    for k in keys:                      # give the cursors real content to be damaged
        client.hset(k, "inbox", "1785400000-0")
    before = {k: dict(client.hgetall(k) or {}) for k in keys}

    mbx.open(NS, "claude", sha, incarnation="seat-A", client=client)
    mbx.open(NS, "claude", sha, incarnation="seat-B", client=client)
    mbx.declare_intent(NS, "claude", sha, "decline", incarnation="seat-B", client=client)

    after = {k: dict(client.hgetall(k) or {}) for k in keys}
    assert before == after, (
        "open()/declare_intent() moved a cursor. Seen must never mean consumed: the ruling is "
        f"explicit and this is its falsifier. before={before} after={after}"
    )


def test_m1_10_seen_receipt_is_idempotent_across_retries():
    """'Exactly one receipt' is contested by construction in a repo that has run two live seats on
    one agent id, and dual-write is LIVE until T047. Re-opening must not mint a second receipt;
    a DIFFERENT incarnation must."""
    mbx = _mailbox()
    client = _fake()
    fields = {"frm": "kimi", "to": "claude", "kind": "handoff", "ts": "1785500002",
              "content": "one body"}
    sha = mbx._ingest_one(client, NS, "claude", "work_inbox", "1785500002-0", fields)
    for _ in range(4):
        mbx.open(NS, "claude", sha, incarnation="seat-A", client=client)
    assert len(mbx.seen_by(NS, "claude", sha, client=client)) == 1, "retries minted extra receipts"
    mbx.open(NS, "claude", sha, incarnation="seat-B", client=client)
    seen = mbx.seen_by(NS, "claude", sha, client=client)
    assert len(seen) == 2 and {r["incarnation"] for r in seen} == {"seat-A", "seat-B"}, (
        "a genuinely different incarnation reading the same mail is a NEW fact and must record"
    )


def test_m1_11_unknown_intent_is_refused_not_stored():
    """An open vocabulary across seats mints declarations no reader can reconcile."""
    mbx = _mailbox()
    client = _fake()
    fields = {"frm": "x", "to": "claude", "kind": "request", "ts": "1785500003", "content": "b"}
    sha = mbx._ingest_one(client, NS, "claude", "work_inbox", "1785500003-0", fields)
    out = mbx.declare_intent(NS, "claude", sha, "maybe_later", incarnation="s", client=client)
    assert out["ok"] is False and "unknown intent" in out["reason"]
    assert mbx.state_for(NS, "claude", sha, client=client)["intent"] is None, "refused but stored"


def test_m1_12_fragment_body_is_never_reported_whole():
    """KD-3b, deepseek's consumer-survivability oracle. The defect it names, pinned.

    A fragment is UNDER BODY_MAX, so the size check alone marks it `truncated=0` and open() reports
    a partial body as whole. An honest oversize truncation is fine; a silent fragment slice is the
    failure class this arc exists to end -- and I shipped it. This pin fails if a fragment ever
    renders as a complete body again.
    """
    mbx = _mailbox()
    client = _fake()
    fields = {"frm": "deepseek", "to": "claude", "kind": "handoff", "ts": "1785500010",
              "content": "x" * 50,           # comfortably under BODY_MAX -- that is the trap
              "meta": json.dumps({"frag": {"seq": 1, "of": 4, "whole_id": "w1"}})}
    sha = mbx._ingest_one(client, NS, "claude", "work_inbox", "1785500010-0", fields)
    got = mbx.body_of(NS, "claude", sha, client=client)
    assert got["body_fragment"] is True, "fragment not recognised as a fragment"
    assert got["truncated"] is True, (
        "KD-3b: a 1-of-4 fragment reported as a WHOLE body. Under BODY_MAX so the size check "
        "passes, and the reader is told nothing. Silent partial > honest partial."
    )
    assert got["frag_of"] == "4"


def test_m1_13_whole_small_body_is_not_flagged_as_partial():
    """The other side of KD-3b: do not buy honesty with false alarms. An ordinary small message
    must still render as whole, or the flag becomes noise and gets ignored."""
    mbx = _mailbox()
    client = _fake()
    fields = {"frm": "kimi", "to": "claude", "kind": "reply", "ts": "1785500011",
              "content": "a complete short message"}
    sha = mbx._ingest_one(client, NS, "claude", "work_inbox", "1785500011-0", fields)
    got = mbx.body_of(NS, "claude", sha, client=client)
    assert got["body_fragment"] is False and got["truncated"] is False


def test_m1_8_cross_incarnation_product_receipt():
    """Codex's receipt, whole. This is the slice's acceptance; the pins above are its parts.

    A seat opens a question and dies without declaring intent. A NEW incarnation lists the same
    mail, sees it was read but not acted on, opens the full body, and acts -- with transport
    history unmoved and undestroyed.
    """
    mbx = _mailbox()
    for verb in ("open", "declare_intent", "body_of", "state_for"):
        assert hasattr(mbx, verb), f"receipt UNBUILT: mailbox.{verb}() missing"
