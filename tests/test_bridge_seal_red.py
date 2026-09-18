"""RED pins for the sealed bridge envelope + chain (design: research/in-flight/bridge-midpoint-cache-2026-09-17).

These land BEFORE core/comm/bridge_seal.py exists. They pin the two properties that make a midpoint
survivable, and they are written to run offline with no network, no peer and no clock authority:

  SEALING   the midpoint holds ciphertext it cannot read and cannot forge, and — the part a Box alone
            does NOT give — it cannot rewrite the ROUTING HEADER either, because seq/prev live outside
            the ciphertext so the midpoint can route on them. A midpoint able to edit seq could erase
            a gap it caused, hiding exactly the loss this design exists to detect.

  CHAIN     per-pair seq + prev, so a recipient can say "I am missing 7" instead of never learning that
            7 existed. On 2026-09-04 our door shut and thirteen days of mail was refused at the wire;
            nothing on either side could tell. That silence is what these pins outlaw.
"""
import base64
import json

import pytest

seal = pytest.importorskip("core.comm.bridge_seal", reason="bridge_seal not built yet (RED)")


# --------------------------------------------------------------------------------------- fixtures
@pytest.fixture()
def alice():
    return seal.generate_identity()


@pytest.fixture()
def bob():
    return seal.generate_identity()


INNER = {"id": "vandor-test-1", "frm": "vandor", "kind": "handoff",
         "content": "the playbook is unfetchable while your door is shut", "sent_at": 1789700000}


def _sealed(alice, bob, **kw):
    kw.setdefault("to", "serge")
    kw.setdefault("frm", "daniil")
    kw.setdefault("seq", 1)
    kw.setdefault("prev", "")
    return seal.seal(INNER, sender=alice, recipient_public=bob["seal_public"], **kw)


# ------------------------------------------------------------------------------------- 1. sealing
def test_seal_unseal_round_trips_the_inner_message(alice, bob):
    env = _sealed(alice, bob)
    got = seal.unseal(env, recipient=bob, sender_public=alice["verify_public"])
    assert got["content"] == INNER["content"]
    assert got["id"] == INNER["id"] and got["kind"] == INNER["kind"]


def test_the_midpoint_cannot_read_the_body(alice, bob):
    """Everything the midpoint stores is the envelope. The plaintext must not be in it anywhere."""
    env = _sealed(alice, bob)
    blob = json.dumps(env, sort_keys=True)
    assert INNER["content"] not in blob
    assert "handoff" not in blob, "kind rides INSIDE the ciphertext — the midpoint sees no kinds at all"
    assert base64.b64decode(env["ct"]) != json.dumps(INNER).encode("utf-8")


def test_a_rewritten_seq_is_refused(alice, bob):
    """THE pin. Box authenticates the body and says nothing about the header; the detached
    signature is what stops a midpoint from editing routing it must be able to read."""
    env = _sealed(alice, bob, seq=7)
    env["seq"] = 6                                        # a midpoint erasing a gap it caused
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"])


def test_a_rewritten_prev_or_recipient_is_refused(alice, bob):
    for field, value in (("prev", "some-other-id"), ("to", "someone-else"), ("from", "impostor")):
        env = _sealed(alice, bob)
        env[field] = value
        with pytest.raises(seal.SealRefused):
            seal.unseal(env, recipient=bob, sender_public=alice["verify_public"])


def test_tampered_ciphertext_is_refused(alice, bob):
    env = _sealed(alice, bob)
    raw = bytearray(base64.b64decode(env["ct"]))
    raw[0] ^= 0xFF
    env["ct"] = base64.b64encode(bytes(raw)).decode("ascii")
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"])


def test_a_stranger_cannot_forge_and_the_wrong_recipient_cannot_open(alice, bob):
    mallory = seal.generate_identity()
    env = _sealed(alice, bob)
    with pytest.raises(seal.SealRefused):                  # signed by alice, claimed as mallory
        seal.unseal(env, recipient=bob, sender_public=mallory["verify_public"])
    with pytest.raises(seal.SealRefused):                  # sealed to bob, opened by mallory
        seal.unseal(env, recipient=mallory, sender_public=alice["verify_public"])


def test_replay_outside_the_window_is_refused(alice, bob):
    env = _sealed(alice, bob, created_at=1_000_000)
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"],
                    now=1_000_000 + 10_000, within_s=300)


def test_ciphertext_is_padded_into_buckets(alice, bob):
    """The midpoint learns a size bucket, not a length — the one thing it can genuinely observe."""
    short = seal.seal({**INNER, "content": "hi"}, sender=alice, recipient_public=bob["seal_public"],
                      to="serge", frm="daniil", seq=1, prev="")
    longer = seal.seal({**INNER, "content": "x" * 900}, sender=alice,
                       recipient_public=bob["seal_public"], to="serge", frm="daniil", seq=2, prev="")
    assert len(base64.b64decode(short["ct"])) == len(base64.b64decode(longer["ct"]))
    assert len(base64.b64decode(short["ct"])) in seal.PAD_BUCKETS_CT


def test_a_control_verb_never_crosses_even_sealed(alice, bob):
    """The allowlist moves inside the ciphertext; it does not stop applying there."""
    with pytest.raises(seal.SealRefused):
        seal.seal({**INNER, "kind": "halt"}, sender=alice, recipient_public=bob["seal_public"],
                  to="serge", frm="daniil", seq=1, prev="")


# --------------------------------------------------------------------------------------- 2. chain
def test_seq_is_per_pair_monotonic_and_survives_a_restart(tmp_path):
    c = seal.Chain(tmp_path / "chain.json")
    a1 = c.next_out("serge")
    a2 = c.next_out("serge")
    b1 = c.next_out("other")
    assert (a1["seq"], a2["seq"], b1["seq"]) == (1, 2, 1), "counters are per recipient, not global"
    assert a2["prev"] == "" or a2["prev"] is not None
    reopened = seal.Chain(tmp_path / "chain.json")
    assert reopened.next_out("serge")["seq"] == 3, "a counter that resets on restart re-uses seqs"


def test_prev_names_the_previous_id_to_that_peer(tmp_path):
    c = seal.Chain(tmp_path / "chain.json")
    c.next_out("serge")
    c.sent("serge", "msg-1")
    nxt = c.next_out("serge")
    assert nxt["prev"] == "msg-1"


def test_a_gap_is_reported_not_silently_tolerated(tmp_path):
    c = seal.Chain(tmp_path / "chain.json")
    assert c.observe_in("serge", seq=1, mid="m1", prev="") == []
    assert c.observe_in("serge", seq=2, mid="m2", prev="m1") == []
    gaps = c.observe_in("serge", seq=4, mid="m4", prev="m3")
    assert gaps == [3], "seq 3 never arrived and the recipient must be able to say so"


def test_out_of_order_arrival_is_not_a_false_gap(tmp_path):
    c = seal.Chain(tmp_path / "chain.json")
    c.observe_in("serge", seq=1, mid="m1", prev="")
    c.observe_in("serge", seq=3, mid="m3", prev="m2")      # reports [2]
    assert c.observe_in("serge", seq=2, mid="m2", prev="m1") == []
    assert c.missing("serge") == [], "2 arrived late; it is no longer missing"


def test_a_duplicate_does_not_advance_the_chain(tmp_path):
    c = seal.Chain(tmp_path / "chain.json")
    c.observe_in("serge", seq=1, mid="m1", prev="")
    assert c.observe_in("serge", seq=1, mid="m1", prev="") == []
    assert c.missing("serge") == []
