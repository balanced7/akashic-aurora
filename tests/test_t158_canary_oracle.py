"""PRE-REGISTERED ACCEPTANCE (T158) -- the canary oracle.

kimi's convergence objection, filed 2026-08-04 and adopted: a pool of same-checkpoint players
cannot distinguish "the system got better" from "this pool ran out of ideas". Role hats
decorrelate the PROMPTS; error covariance lives in the INDUCTION. So a declining find-rate has
two causes the board burn-down cannot separate, and A5 is the live demonstration -- a fourth gate
hole found AFTER a three-round streak, by a lens the streak did not contain.

The instrument that separates them is a control the players cannot be correlated with, because
they cannot see it: defects PLANTED by the adjudicator with answers sealed before the round. A
tired pool stops catching planted canaries too, so exhaustion cannot masquerade as completeness.

  K1  three canary CLASSES exist and are distinguishable -- catchable (the T143 compound-statement
      shape the current gate SHOULD find), undetectable (the A5 string-dispatch shape it
      structurally CANNOT), and bait (a genuinely LIVE function planted to look dead)
  K2  the LIVE TREE IS NEVER WRITTEN -- planting happens in a shadow copy, full stop
  K3  the answer key is SEALED before the round and is tamper-evident afterwards
  K4  scoring produces a confusion matrix BY CLASS, not one number
  K5  catch-rate is computed on CATCHABLE canaries only -- scoring an undetectable canary as a
      miss would punish the pool for the gate's blind spot, which is the honesty this exists for
  K6  a claimed catch on an UNDETECTABLE canary voids the round (kimi's K0 tripwire: the
      instrument is corrupt or the key leaked)
  K7  planting is deterministic under a seed, so a round is reproducible and re-scoreable

Run: py -m pytest tests/test_t158_canary_oracle.py -q
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _mod():
    from scripts import canary_oracle
    return canary_oracle


def test_k1_three_classes_exist(tmp_path):
    c = _mod()
    shadow = tmp_path / "shadow"
    shadow.mkdir()
    (shadow / "target.py").write_text("def live_one():\n    return 1\n", encoding="utf-8")
    manifest = c.plant(str(shadow), k=6, seed=42)
    classes = {x["cls"] for x in manifest["canaries"]}
    assert classes == {"catchable", "undetectable", "bait"}, f"got {classes}"


def test_k2_the_live_tree_is_never_written(tmp_path):
    """The operator's scope is live store READ-ONLY. Planting into the real repo would be the
    single worst thing this module could do, so it refuses by construction, not by convention."""
    c = _mod()
    import pytest
    with pytest.raises(Exception):
        c.plant(ROOT, k=3, seed=1)          # the real repo root must be refused outright


def test_k3_the_key_is_sealed_and_tamper_evident(tmp_path):
    c = _mod()
    shadow = tmp_path / "s3"
    shadow.mkdir()
    (shadow / "t.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    m = c.plant(str(shadow), k=3, seed=7)
    p = str(tmp_path / "key.json")
    c.seal(m, p)
    assert c.verify_seal(p) is True
    raw = open(p, encoding="utf-8").read().replace('"catchable"', '"bait"', 1)
    open(p, "w", encoding="utf-8").write(raw)
    assert c.verify_seal(p) is False, "a tampered answer key must not verify"


def test_k4_scoring_is_a_confusion_matrix_by_class(tmp_path):
    c = _mod()
    shadow = tmp_path / "s4"
    shadow.mkdir()
    (shadow / "t.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    m = c.plant(str(shadow), k=6, seed=11)
    ids = [x["id"] for x in m["canaries"] if x["cls"] == "catchable"]
    res = c.score(m, claims=ids[:1])
    assert "by_class" in res
    for cls in ("catchable", "undetectable", "bait"):
        assert cls in res["by_class"], f"missing class {cls}"
        assert {"caught", "missed", "total"} <= set(res["by_class"][cls])


def test_k5_catch_rate_uses_catchable_only(tmp_path):
    """Scoring an undetectable canary as a miss punishes the pool for the gate's blind spot."""
    c = _mod()
    shadow = tmp_path / "s5"
    shadow.mkdir()
    (shadow / "t.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    m = c.plant(str(shadow), k=6, seed=13)
    catchable = [x["id"] for x in m["canaries"] if x["cls"] == "catchable"]
    res = c.score(m, claims=catchable)                     # every catchable found, nothing else
    assert res["catch_rate"] == 1.0, f"expected 1.0, got {res['catch_rate']}"
    assert res["voided"] is False


def test_k6_claiming_an_undetectable_canary_voids_the_round(tmp_path):
    """kimi's K0 tripwire. If a player 'finds' a hole the gate structurally cannot see, either the
    key leaked or the instrument is being gamed -- the round's evidence is worthless either way."""
    c = _mod()
    shadow = tmp_path / "s6"
    shadow.mkdir()
    (shadow / "t.py").write_text("def a():\n    return 1\n", encoding="utf-8")
    m = c.plant(str(shadow), k=6, seed=17)
    undetectable = [x["id"] for x in m["canaries"] if x["cls"] == "undetectable"]
    res = c.score(m, claims=undetectable[:1])
    assert res["voided"] is True, "an undetectable-canary catch must void the round"
    assert res["void_reason"]


def test_k7_planting_is_deterministic_under_a_seed(tmp_path):
    c = _mod()
    out = []
    for n in ("a", "b"):
        shadow = tmp_path / n
        shadow.mkdir()
        (shadow / "t.py").write_text("def a():\n    return 1\n", encoding="utf-8")
        out.append(_mod().plant(str(shadow), k=6, seed=99))
    assert [x["id"] for x in out[0]["canaries"]] == [x["id"] for x in out[1]["canaries"]]
    assert [x["cls"] for x in out[0]["canaries"]] == [x["cls"] for x in out[1]["canaries"]]
