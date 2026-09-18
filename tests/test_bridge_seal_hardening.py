"""Pins for the adversarial review of bridge_seal (2026-09-17). Each test is an attack that WORKED
against the first implementation; the numbering is the review's.

The critical one is #1 and it was not a crypto break — the signature construction survived every
attack on it. The break was architectural: `tombstone()` discarded the signature, and tombstones are
what feed gap detection, so a midpoint could withhold 2,3,4, deposit three tombstones it invented,
and `missing()` came back empty. The property the whole design exists to provide, handed to the
attacker by the retirement path.
"""
import base64
import json
import math

import pytest

seal = pytest.importorskip("core.comm.bridge_seal")


@pytest.fixture()
def alice():
    return seal.generate_identity()


@pytest.fixture()
def bob():
    return seal.generate_identity()


INNER = {"id": "m1", "frm": "vandor", "kind": "note", "content": "x", "sent_at": 1789700000}


def _env(alice, bob, **kw):
    kw.setdefault("to", "serge")
    kw.setdefault("frm", "daniil")
    kw.setdefault("seq", 1)
    kw.setdefault("prev", "")
    kw.setdefault("epoch", "e1")
    return seal.seal(INNER, sender=alice, recipient_public=bob["seal_public"], **kw)


# ------------------------------------------------------------------- 1 CRITICAL: tombstone forgery
def test_a_forged_tombstone_is_refused(alice, bob):
    """The midpoint withholds a message and invents a tombstone to cover the hole."""
    real = seal.tombstone(_env(alice, bob, seq=2))
    forged = {**real, "seq": 3, "id": "invented-3"}
    with pytest.raises(seal.SealRefused):
        seal.verify_tombstone(forged, sender_public=alice["verify_public"])


def test_a_real_tombstone_still_verifies_after_the_body_is_gone(alice, bob):
    tomb = seal.tombstone(_env(alice, bob, seq=2, prev="m1"))
    assert "ct" not in tomb and "sig" not in tomb, "the body must not survive retirement"
    got = seal.verify_tombstone(tomb, sender_public=alice["verify_public"])
    assert got["seq"] == 2 and got["prev"] == "m1"


def test_the_chain_refuses_records_that_were_never_verified(tmp_path):
    """observe_in must not be reachable with unverified routing data."""
    c = seal.Chain(tmp_path / "c.json")
    with pytest.raises(seal.SealRefused):
        c.observe_in("serge", seq=2, mid="x", prev="", epoch="e1", verified=False)


# ------------------------------------------------------------- 2,3,15 uniform refusal (no leaks)
@pytest.mark.parametrize("bad", ["abc", float("inf"), float("nan"), [1], {"a": 1}, None])
def test_is_retired_never_raises_a_foreign_type(bad):
    assert seal.is_retired({"expires_at": bad}) in (True, False)


@pytest.mark.parametrize("bad", ["abc", float("inf"), float("-inf"), float("nan"), [1], {"a": 1}])
def test_unseal_refuses_uniformly_on_a_poisoned_created_at(alice, bob, bad):
    env = _env(alice, bob)
    env["created_at"] = bad                       # after a VALID signature, per the review
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"], me="serge")


@pytest.mark.parametrize("kw", [{"seq": "abc"}, {"seq": None}, {"created_at": float("nan")},
                                {"expires_at": float("inf")}])
def test_seal_refuses_uniformly(alice, bob, kw):
    with pytest.raises(seal.SealRefused):
        _env(alice, bob, **kw)


def test_seal_refuses_a_broken_identity(bob):
    for ident in ({"seal_public": "x"}, {"sign_secret": "!!not-b64!!", "seal_public": "a",
                                         "seal_secret": "a", "verify_public": "a"}):
        with pytest.raises(seal.SealRefused):
            seal.seal(INNER, sender=ident, recipient_public=bob["seal_public"],
                      to="serge", frm="daniil", seq=1, prev="", epoch="e1")


def test_seal_refuses_an_unserialisable_inner(alice, bob):
    with pytest.raises(seal.SealRefused):
        seal.seal({**INNER, "content": {1, 2, 3}}, sender=alice,
                  recipient_public=bob["seal_public"], to="serge", frm="daniil",
                  seq=1, prev="", epoch="e1")


# --------------------------------------------------------------------- 4,14 bounded seq and state
def test_an_absurd_seq_is_refused_rather_than_materialised(tmp_path):
    c = seal.Chain(tmp_path / "c.json")
    c.observe_in("serge", seq=1, mid="m1", prev="", epoch="e1", verified=True)
    with pytest.raises(seal.SealRefused):
        c.observe_in("serge", seq=2 ** 70, mid="m", prev="m1", epoch="e1", verified=True)
    assert c.missing("serge") == []


def test_state_stays_small_over_a_long_run(tmp_path):
    c = seal.Chain(tmp_path / "c.json")
    for s in range(1, 2001):
        c.observe_in("serge", seq=s, mid=f"m{s}", prev=f"m{s-1}", epoch="e1", verified=True)
    assert c.missing("serge") == []
    assert (tmp_path / "c.json").stat().st_size < 8000, "in-order arrivals must not accumulate state"


# ------------------------------------------------------------------------- 5 fail-closed on damage
def test_a_corrupt_chain_file_refuses_instead_of_forgetting(tmp_path):
    p = tmp_path / "c.json"
    c = seal.Chain(p)
    c.observe_in("serge", seq=1, mid="m1", prev="", epoch="e1", verified=True)
    p.write_text('{"out": {"serge": {"seq": 4', encoding="utf-8")      # truncated write
    with pytest.raises(seal.ChainCorrupt):
        seal.Chain(p)


def test_an_absent_chain_file_is_a_fresh_start_not_an_error(tmp_path):
    assert seal.Chain(tmp_path / "nope.json").next_out("serge")["seq"] == 1


# --------------------------------------------------------------------------- 6 no duplicate seqs
def test_concurrent_claims_never_hand_out_the_same_seq(tmp_path):
    import threading
    p = tmp_path / "c.json"
    seen, lock, errors = [], threading.Lock(), []

    def claim():
        try:
            for _ in range(25):
                s = seal.Chain(p).next_out("serge")["seq"]
                with lock:
                    seen.append(s)
        except Exception as e:                                    # noqa: BLE001
            errors.append(e)

    threads = [threading.Thread(target=claim) for _ in range(4)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors, f"a claim crashed: {errors[:2]}"
    assert len(seen) == len(set(seen)), f"{len(seen) - len(set(seen))} duplicate seq(s) issued"


# ------------------------------------------------------------- 7,8,9,10,11 strictness at the door
def test_an_unsigned_extra_field_is_refused(alice, bob):
    env = _env(alice, bob)
    env["retired"] = True                                         # outside _HEADER_FIELDS
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"], me="serge")


def test_a_malleable_base64_spelling_is_refused(alice, bob):
    env = _env(alice, bob)
    env["ct"] = "!!!" + env["ct"][:10] + "\n\n" + env["ct"][10:] + "   \t"
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"], me="serge")


@pytest.mark.parametrize("missing", ["seq", "to", "from", "id", "prev", "v", "epoch"])
def test_a_missing_header_field_is_refused(alice, bob, missing):
    env = _env(alice, bob)
    del env[missing]
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"], me="serge")


def test_an_envelope_addressed_elsewhere_is_refused(alice, bob):
    env = _env(alice, bob, to="someone-else")
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"], me="serge")


def test_an_unknown_version_is_refused(alice, bob):
    env = _env(alice, bob)
    env["v"] = 99
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"], me="serge")


# ----------------------------------------------------------------------------- 12 prev is checked
def test_a_broken_prev_chain_is_reported(tmp_path):
    c = seal.Chain(tmp_path / "c.json")
    c.observe_in("serge", seq=1, mid="m1", prev="", epoch="e1", verified=True)
    out = c.observe_in("serge", seq=2, mid="m2", prev="TOTAL-NONSENSE", epoch="e1", verified=True)
    assert out.get("chain_broken") is True, "prev must be compared, not decoration"


# ------------------------------------------------------------------- 13 a sender reset is visible
def test_a_sender_side_chain_reset_is_visible_not_swallowed(tmp_path):
    c = seal.Chain(tmp_path / "c.json")
    for s in (1, 2, 3):
        c.observe_in("serge", seq=s, mid=f"m{s}", prev="", epoch="e1", verified=True)
    out = c.observe_in("serge", seq=1, mid="new-m1", prev="", epoch="e2", verified=True)
    assert out.get("epoch_changed") is True, "a reissued seq under a new epoch is not a duplicate"


# ------------------------------------------------------------------------------- 16 no silent coercion
def test_default_str_no_longer_corrupts_the_inner_message(alice, bob):
    """A set used to ship as the string '{1, 2, 3}' with no error on either side."""
    with pytest.raises(seal.SealRefused):
        seal.seal({**INNER, "extra": {1, 2}}, sender=alice, recipient_public=bob["seal_public"],
                  to="serge", frm="daniil", seq=1, prev="", epoch="e1")


# ------------------------------------------------------------------------------- 18 expiry is real
def test_an_expired_envelope_does_not_unseal(alice, bob):
    env = _env(alice, bob, created_at=1789700000, expires_at=1789700001)
    with pytest.raises(seal.SealRefused):
        seal.unseal(env, recipient=bob, sender_public=alice["verify_public"], me="serge",
                    now=1789700500, within_s=100000)


# ------------------------------------------------------------------------------- 19 type confusion
def test_a_structurally_wrong_chain_file_refuses(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"out": 5, "in": {}}', encoding="utf-8")
    with pytest.raises(seal.ChainCorrupt):
        seal.Chain(p)
