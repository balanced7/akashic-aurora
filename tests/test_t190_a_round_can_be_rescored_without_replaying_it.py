"""PRE-REGISTERED ACCEPTANCE (T190) -- a round's evidence must outlive the round.

THE DEFECT, found while checking codex_root's proposed next step ("replay the existing three
rounds through scoreboard v2 before buying another model call"): it is impossible. The nine
surviving season_dryrun temp directories hold `key.json` and `shadow` -- and no claims. The
player's output was printed and discarded. Three rounds costing $1.069 produced evidence and threw
it away, which is this arc's invariant applied to the round itself.

WHY IT BLOCKS THE SCOREBOARD WORK. Without archived rounds, the next LIVE round becomes the new
scorer's test fixture -- an instrument validated on the only data it will ever be judged by. The
whole value of an archive is an old-score/new-score comparison on identical claims.

TRUST BOUNDARY, which decides where the record lives. Claims carry `dedupe_key: canary::<name>`,
so a COMMITTED record would leak name->class for that seed and let a replay of the same seed
cheat. canary_oracle already refuses to seal anywhere git tracks. The round record inherits
exactly that boundary: it lives outside the repository beside the key, and may therefore also
carry the manifest so replay is self-contained. The repo gets summaries and digests only.

  K1  a completed round writes a record and hands back its path
  K2  the record carries the CLAIMS -- the thing that was being lost
  K3  it REFUSES to write anywhere git tracks, by construction rather than by care
  K4  replay re-scores stored claims with NO model call and reproduces the original adjudication
  K5  the SAME stored claims under a DIFFERENT scorer produce a DIFFERENT verdict
  K6  a record without claims is a named failure, never an empty replay that reads as a clean one

K5 is the entire point. If replay cannot change a verdict it is decorative, and the scoreboard
rewrite would still have to be validated on live rounds.

K6 exists because "no claims" and "no findings" are the two facts this project keeps confusing.

Run: py -m pytest tests/test_t190_a_round_can_be_rescored_without_replaying_it.py -q
"""
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import pytest  # noqa: E402

from scripts import round_archive as A  # noqa: E402


def _manifest():
    return {"universe": {"source": "test", "size": 3},
            "canaries": [
                {"id": "c00_aaa", "cls": "catchable", "name": "route_aaa", "shape": "t143"},
                {"id": "c01_bbb", "cls": "undetectable", "name": "emit_bbb", "shape": "a5"},
                {"id": "c02_ccc", "cls": "bait", "name": "apply_ccc", "shape": "live"},
            ]}


def _claims(ids=("c00_aaa",)):
    return [{"player": "llm", "dedupe_key": f"canary::x{i}", "claim_class": "needs-caller",
             "outcome": "confirmed", "confidence": "high", "stream_id": f"{i}-0",
             "evidence": ["window shows no invocation"], "_canary_id": cid}
            for i, cid in enumerate(ids)]


def _record(ids=("c00_aaa",)):
    return {"seed": 20260804, "k": 3, "key_sha256": "deadbeef" * 8,
            "player_name": "llm", "player_config": {"batch_size": 20, "workers": 6},
            "manifest": _manifest(), "claims": _claims(ids),
            "player_report": {"candidates": 630, "unjudged": 4, "usd": 0.349},
            "scoring": {"policy": "v1_doc", "totals": {"llm": 9}}}


def test_k1_archiving_returns_a_path_that_exists(tmp_path):
    path = A.archive_round(_record(), round_dir=str(tmp_path))
    assert os.path.isfile(path), "a round that reports a path must have written one"
    assert path.endswith(".json")


def test_k2_the_record_carries_the_claims(tmp_path):
    path = A.archive_round(_record(("c00_aaa", "c01_bbb")), round_dir=str(tmp_path))
    stored = json.loads(open(path, encoding="utf-8").read())
    assert [c["_canary_id"] for c in stored["claims"]] == ["c00_aaa", "c01_bbb"], (
        "the claims are the whole point -- everything else is reconstructible")
    assert stored["manifest"]["canaries"], "replay needs the key it was scored against"


def test_k3_it_refuses_to_write_anywhere_git_tracks():
    """By construction, matching canary_oracle.seal's own rule. A round record carries
    dedupe_key canary::<name>, so committing one leaks name->class for that seed."""
    with pytest.raises(ValueError) as e:
        A.archive_round(_record(), round_dir=os.path.join(ROOT, "research", "rounds"))
    assert "repositor" in str(e.value).lower() or "git" in str(e.value).lower()


def test_k4_replay_reproduces_the_original_verdict_with_no_model_call(tmp_path):
    path = A.archive_round(_record(("c00_aaa",)), round_dir=str(tmp_path))
    out = A.replay_round(path)
    assert out["adjudication"]["catch_rate"] == 1.0
    assert out["adjudication"]["voided"] is False
    assert out["model_calls"] == 0, "replay that spends money is not replay"


def test_k5_a_different_scorer_changes_the_verdict_on_identical_claims(tmp_path):
    """THE POINT. A claim on the baseline-blind class voids under the current rule. If a
    replacement scorer cannot be exercised on the SAME claims and reach a different verdict,
    the archive is decorative and the scoreboard rewrite still has to be validated live."""
    path = A.archive_round(_record(("c00_aaa", "c01_bbb")), round_dir=str(tmp_path))

    old = A.replay_round(path)
    assert old["adjudication"]["voided"] is True, "current rule voids a baseline-blind claim"

    def lenient(manifest, claimed):
        """A stand-in v2: a hard-class claim is a finding, not fraud."""
        ids = {c["id"] for c in manifest["canaries"] if c["cls"] == "undetectable"}
        return {"voided": False, "capability_findings": sorted(set(claimed) & ids)}

    new = A.replay_round(path, score_fn=lenient)
    assert new["adjudication"]["voided"] is False
    assert new["adjudication"]["capability_findings"] == ["c01_bbb"]


def test_k6_a_record_without_claims_is_a_named_failure(tmp_path):
    bad = _record()
    bad.pop("claims")
    path = os.path.join(str(tmp_path), "broken.json")
    open(path, "w", encoding="utf-8").write(json.dumps(bad))
    with pytest.raises(ValueError) as e:
        A.replay_round(path)
    assert "claim" in str(e.value).lower(), (
        "a round with no claims recorded and a round where the player found nothing are "
        "different facts; replaying the first as an empty clean round is the defect this "
        "whole slice exists to stop")
