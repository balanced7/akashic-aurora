"""T112 -- A RE-ASK IS A NUDGE, NOT A NEW MESSAGE. RED first (M3).

MEASURED 2026-07-28 05:30, not argued. Both peers complained independently that
asks were arriving as replays of things they had already answered -- kimi:
"This is the second replay of an ask I've already answered"; deepseek: "third
confirmation this session". I treated it as a defect on my side of the wire and
went to the stream. Scanning bifrost:inbox:kimi over one 40-minute window,
hashing (frm + content):

    33 distinct packets, 3 duplicated
      x4  frm=codex_explain  len=285   ids 39 minutes apart
      x4  frm=codex_explain  len=563
      x2  frm=claude         len=641   <- me

Byte-identical content, distinct stream ids, minutes apart. Not consumer-side
redelivery and not a cursor bug: these are genuine repeat SENDS. A sender whose
ask goes unanswered re-sends the whole ask, and every copy costs the recipient a
full turn -- kimi answered one fence-lite four times and told us so twice. That
is real money and real patience, and it is a large part of the "mis-routing,
mis-waking, mis-consuming, mis-everything mess".

THE LAW: waiting is not a reason to send the message again. Retransmission
belongs to the ack layer, never to the payload layer -- Quake 3 retransmits
against per-client acks rather than re-queueing gameplay events, and the
expectation/nudge machinery here already exists for exactly this. A re-ask is a
NUDGE against the original, not a second unit of work.

Suppression is dangerous in one specific way and the pins bound it: if the
ORIGINAL is gone (reaped, tombstoned, trimmed), suppressing the re-ask strands
the work forever. That is the marker-before-send strand class Sol found in S4,
re-created one layer up. P6 forbids it.

  P1  IDENTICAL CONTENT to the same peer inside the window is suppressed, and
      the ORIGINAL id comes back -- the sender's bookkeeping still resolves.
  P2  THE RECIPIENT'S STREAM GAINS NO SECOND COPY (the token burn is the point).
  P3  DIFFERENT CONTENT always delivers.
  P4  SAME CONTENT TO A DIFFERENT PEER always delivers.
  P5  ONCE THE WINDOW LAPSES it delivers -- a genuinely later re-ask is real work.
  P6  IF THE ORIGINAL IS NO LONGER IN THE RECIPIENT'S STREAM, IT DELIVERS.
      Never trade a duplicate for a strand.
  P7  SUPPRESSION IS LOUD. A silent drop is indistinguishable from a lost
      message, and this arc has spent all night on instruments that fail quietly.
  P8  THE DIAL TURNS OFF. New send-door behaviour ships with an exit.
"""

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm.bus import Bus

NS = "t112"


@pytest.fixture(autouse=True)
def _env():
    saved = {k: os.environ.get(k) for k in
             ("BIFROST_NAMESPACE", "BIFROST_REASK_WINDOW_S", "BIFROST_REASK_COLLAPSE")}
    yield
    for k, v in saved.items():
        os.environ.pop(k, None) if v is None else os.environ.__setitem__(k, v)


@pytest.fixture
def peers():
    a, b = f"snd{uuid.uuid4().hex[:6]}", f"rcv{uuid.uuid4().hex[:6]}"
    sender = Bus(a, namespace=NS, promote=False)
    if not sender.online:
        pytest.skip("bus offline")
    yield sender, a, b
    for k in sender._client.scan_iter(match=f"{NS}:*{a}*", count=200):
        sender._client.delete(k)
    for k in sender._client.scan_iter(match=f"{NS}:*{b}*", count=200):
        sender._client.delete(k)


def _inbox_len(bus, who):
    try:
        return bus._client.xlen(f"{NS}:inbox:{who}")
    except Exception:
        return 0


# --------------------------------------------------------------- P1 / P2
def test_p1_p2_identical_reask_is_suppressed_and_returns_the_original_id(peers):
    sender, _, rcv = peers
    first = sender.send(rcv, "question", "please run the fence-lite on 686dfcd")
    assert first, "first send must deliver"
    before = _inbox_len(sender, rcv)

    again = sender.send(rcv, "question", "please run the fence-lite on 686dfcd")
    assert again == first, (
        f"RE-ASK DELIVERED AS NEW WORK: got {again!r}, expected the original {first!r}. "
        f"Sol sent one byte-identical ask FOUR times in 39 minutes and kimi answered it "
        f"four times. The sender's bookkeeping must still resolve, so return the original "
        f"id rather than None -- suppression is not failure.")
    assert _inbox_len(sender, rcv) == before, (
        f"the recipient's stream grew: {before} -> {_inbox_len(sender, rcv)}. Every copy "
        f"costs a full turn; that cost IS the defect.")


# --------------------------------------------------------------- P3
def test_p3_different_content_always_delivers(peers):
    sender, _, rcv = peers
    a = sender.send(rcv, "question", "run the fence-lite on 686dfcd")
    b = sender.send(rcv, "question", "run the fence-lite on 39df728")
    assert a and b and a != b, "distinct asks are distinct work and must both deliver"
    assert _inbox_len(sender, rcv) == 2


# --------------------------------------------------------------- P4
def test_p4_same_content_to_a_different_peer_always_delivers(peers):
    sender, _, rcv = peers
    other = f"oth{uuid.uuid4().hex[:6]}"
    a = sender.send(rcv, "question", "read the netcode doc and file your plan")
    b = sender.send(other, "question", "read the netcode doc and file your plan")
    assert a and b and a != b, (
        "the SAME ask to two peers is the fan-out pattern the whole fleet runs on "
        "(build-plan rounds, census work orders) -- suppression is per RECIPIENT")
    assert _inbox_len(sender, other) == 1


# --------------------------------------------------------------- P5
def test_p5_once_the_window_lapses_it_delivers(peers):
    os.environ["BIFROST_REASK_WINDOW_S"] = "0"
    sender, _, rcv = peers
    a = sender.send(rcv, "question", "status?")
    b = sender.send(rcv, "question", "status?")
    assert a != b, (
        "with a zero window every send is a fresh ask: asking the same question an hour "
        "later is real work, not a duplicate. The window is what makes this safe.")


# --------------------------------------------------------------- P6 the strand guard
def test_p6_a_vanished_original_always_redelivers(peers):
    """The dangerous case. If the original was reaped, tombstoned or trimmed away,
    suppressing the re-ask strands the work FOREVER -- Sol's mark-before-send strand
    class from S4, re-created one layer up. Never trade a duplicate for a strand."""
    sender, _, rcv = peers
    first = sender.send(rcv, "question", "the ask that got reaped")
    sender._client.delete(f"{NS}:inbox:{rcv}")          # original is gone

    again = sender.send(rcv, "question", "the ask that got reaped")
    assert again and again != first, (
        f"STRANDED: the original {first!r} is no longer in the recipient's stream and the "
        f"re-ask was suppressed anyway ({again!r}). A suppressor that cannot see the "
        f"original must fail OPEN -- a duplicate costs a turn, a strand costs the work.")
    assert _inbox_len(sender, rcv) == 1


# --------------------------------------------------------------- P7
def test_p7_suppression_is_loud(peers, capsys):
    """Asserts on stdout AND stderr. The first draft of this pin checked stdout only
    and failed against a correct implementation: bus._loud() is the module's OWN
    established loud channel and it writes to stderr by T043 convention. The bar --
    'a suppressed message must be visible to an operator' -- is unchanged; the
    assertion had named a mechanism the contract never specified, and reading the
    producer before trusting the assertion is the standing rule
    (fresh_eyes_read_the_label_generator_first)."""
    sender, _, rcv = peers
    first = sender.send(rcv, "question", "please review the diff")
    capsys.readouterr()
    sender.send(rcv, "question", "please review the diff")
    cap = capsys.readouterr()
    out = ((cap.out or "") + (cap.err or "")).lower()
    assert "re-ask" in out or "reask" in out or "suppress" in out, (
        f"a silent drop is indistinguishable from a lost message. Say what happened and "
        f"name the original, or the next hour is spent debugging the fix. Saw: {out!r}")
    assert str(first) in out, (
        f"the notice must NAME the original id so the sender can nudge it instead of "
        f"re-sending: {out!r}")


# --------------------------------------------------------------- P8
def test_p8_the_dial_turns_off(peers):
    os.environ["BIFROST_REASK_COLLAPSE"] = "0"
    sender, _, rcv = peers
    a = sender.send(rcv, "question", "identical")
    b = sender.send(rcv, "question", "identical")
    assert a != b, "new send-door behaviour ships with an exit"
    assert _inbox_len(sender, rcv) == 2


# --------------------------------------------------------------- P9 / P10 system re-delivery
# Added after the grep-derived sweep failed three EXISTING pins that my own eight did not
# cover: test_t030_l4_expectations::test_redrive_past_deadline and two
# test_t108_nseat_delivery reaper pins. The fleet has machinery whose entire job is to send
# the same bytes again, and collapsing it strands exactly the work it exists to rescue.
# P6 does not catch this: there the original is GONE, here it is present and the re-send is
# still correct. Same strand class, different door.

def test_p9_a_redrive_is_never_collapsed(peers):
    """expectations.redrive re-sends a copy past the reply deadline with
    meta={redrive_of, attempt}. Suppressing it silences the only escalation the
    sender-side deadline machinery has."""
    sender, _, rcv = peers
    first = sender.send(rcv, "question", "did the fence pass?")
    again = sender.send(rcv, "question", "did the fence pass?",
                        meta={"redrive_of": first, "attempt": 1})
    assert again and again != first, (
        "REDRIVE COLLAPSED: a deadline redrive is deliberate re-delivery, not an "
        "impatient re-send. The marker is the difference and it must be honoured.")


def test_p10_a_reaper_rehome_is_never_collapsed(peers):
    """The reaper re-homes a dead seat's directed mail to its role -- identical bytes,
    on purpose, to rescue work whose original recipient is gone. Collapsing it recreates
    the S4 strand it was built to fix."""
    sender, _, rcv = peers
    first = sender.send(rcv, "note", "the ask that outlived its seat")
    again = sender.send(rcv, "note", "the ask that outlived its seat",
                        meta={"rehomed_from": "claude#dead1234", "original_mid": first})
    assert again and again != first, (
        "REHOME COLLAPSED: re-homed mail is the rescue path for a dead seat's work. "
        "Suppressing it stranded the packet twice over.")


# --------------------------------------------------------------- P11 deepseek's fence residual
def test_p11_the_sender_learns_it_was_collapsed_not_just_stderr():
    """deepseek's T112 fence, filed after I asked it to fence harder than usual: PASSES on
    all three surfaces, one residual -- "collapse reason should reach the sender through
    more than stderr."

    Exactly right, and it is the same disease in miniature. A runner's stderr goes to the
    ManagedChild ring; the MODEL that called bifrost_send never sees it. So the sender gets
    an id back, believes it sent something new, and learns nothing -- while the whole point
    of collapsing is to teach "nudge the original instead". A notice the actor cannot read
    is a notice that does not exist.

    The Bus records the collapse on itself so the calling door can report it in the string
    the model actually reads."""
    import uuid as _uuid
    from core.comm.bus import Bus as _Bus

    a, rcv = f"snd{_uuid.uuid4().hex[:6]}", f"rcv{_uuid.uuid4().hex[:6]}"
    sender = _Bus(a, namespace=NS, promote=False)
    if not sender.online:
        pytest.skip("bus offline")
    try:
        first = sender.send(rcv, "question", "fence this please")
        assert sender.last_reask is None, (
            "a normal send must not report a collapse -- a false positive here teaches the "
            "sender to stop sending real work")
        sender.send(rcv, "question", "fence this please")
        assert sender.last_reask == first, (
            f"the Bus must expose WHICH id the send collapsed onto, so the calling door can "
            f"put it in the string the model reads: {sender.last_reask!r} != {first!r}")
    finally:
        for k in sender._client.scan_iter(match=f"{NS}:*{a}*", count=200):
            sender._client.delete(k)
        for k in sender._client.scan_iter(match=f"{NS}:*{rcv}*", count=200):
            sender._client.delete(k)
