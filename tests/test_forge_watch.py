"""Forge F4 Tier-1 watch (core/recall/curator.py) -- characterization.

The discipline (design sec.4 Tier 1, locked decisions 2+5): a provisionally-applied edit
is watched against the counters snapshot taken AT APPLY TIME. Rollback triggers are
one-sided (any new noise vote; credit-rate regression once >= 8 fresh impressions exist
for a lesson that HAD a baseline rate); surviving the window (14d or 8 impressions)
CONFIRMS the variant. Unreviewed optimizer proposals expire after 7 days. All stamps are
reversible state, never deletes.
"""
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.recall.curator import curation_report, apply_curation
from core.learning.learning_store import LearningStore
from core.foundation.store import FileStore

OLD_TEXT = "Use when editing the seam, before refactoring: route through it. Don't when prototyping."
NEW_TEXT = "Use when editing the seam, before refactoring: route every source through it. Don't when prototyping."


def _fixture(baseline, use_now, *, forged_days_ago=1.0):
    d = tempfile.mkdtemp()
    ls = LearningStore(store=FileStore(os.path.join(d, "learn.json")))
    ls.persist_learning_derived_from_experiment({
        "experiment_name": "watched", "what_tried": "x", "actual_outcome": "y",
        "success": "yes", "recommendation": OLD_TEXT, "agent_id": "t"})
    assert ls.apply_forge_edit("watched", NEW_TEXT, {"floor": 0.2}, baseline=baseline)
    # backdate the provisional stamp to simulate elapsed time (production-shaped naive utcnow)
    forged_at = (datetime.utcnow() - timedelta(days=forged_days_ago)).isoformat()
    ls.store.hset("learn:experiment:watched", mapping={"forge_provisional": forged_at,
                                                       "forged_at": forged_at})
    use = FileStore(os.path.join(d, "use.json"))
    use.set("recall:use:learn:experiment:watched", json.dumps(use_now))
    return ls, use


def test_rollback_on_new_noise_vote():
    ls, use = _fixture(baseline={"surfaced": 10, "noise": 0}, use_now={"surfaced": 12, "noise": 1})
    rep = curation_report(store=use, learning_store=ls)
    assert [r["name"] for r in rep["forge_rollback"]] == ["watched"], rep["forge_rollback"]
    out = apply_curation(rep, store=use, learning_store=ls)
    assert out["forge_rolled_back"] == ["watched"]
    rec = ls._load_experiment("watched")
    assert rec.get("recommendation") == OLD_TEXT and not rec.get("forge_provisional")
    print("\n--- noise rollback ---\n  one noise vote on the variant -> text restored OK")


def test_rollback_on_credit_rate_regression():
    # baseline rate 2/10 = 0.2; then +10 fresh impressions with zero fresh credit
    ls, use = _fixture(baseline={"surfaced": 10, "helped": 2},
                       use_now={"surfaced": 20, "helped": 2})
    rep = curation_report(store=use, learning_store=ls)
    assert rep["forge_rollback"] and "credit rate" in rep["forge_rollback"][0]["why"]
    print("--- rate rollback ---\n  credited lesson goes quiet after the edit -> rollback OK")


def test_confirm_after_quiet_window():
    # never-credited baseline (rate 0 -> no rate trigger), 9 fresh impressions, no noise
    ls, use = _fixture(baseline={"surfaced": 10}, use_now={"surfaced": 19})
    rep = curation_report(store=use, learning_store=ls)
    assert [r["name"] for r in rep["forge_confirm"]] == ["watched"], rep
    out = apply_curation(rep, store=use, learning_store=ls)
    assert out["forge_confirmed"] == ["watched"]
    rec = ls._load_experiment("watched")
    assert rec.get("recommendation") == NEW_TEXT, "confirm keeps the variant"
    assert not rec.get("forge_provisional") and rec.get("forge_confirmed")
    print("--- confirm ---\n  quiet window -> provisional cleared, variant kept OK")


def test_young_provisional_is_left_alone():
    ls, use = _fixture(baseline={"surfaced": 10}, use_now={"surfaced": 13},
                       forged_days_ago=0.5)
    rep = curation_report(store=use, learning_store=ls)
    assert not rep["forge_rollback"] and not rep["forge_confirm"], rep
    print("--- patience ---\n  young provisional with thin data -> no action OK")


def test_stale_proposal_expires():
    ls, use = _fixture(baseline={"surfaced": 10}, use_now={"surfaced": 11},
                       forged_days_ago=0.5)
    old = (datetime.utcnow() - timedelta(days=9)).isoformat()
    ls.store.hset("learn:experiment:watched", mapping={"forge_proposal": json.dumps(
        {"draft": "stale draft", "verdict": "PASS", "at": old, "by": "deepseek-optimizer"})})
    rep = curation_report(store=use, learning_store=ls)
    assert [r["name"] for r in rep["forge_expire"]] == ["watched"], rep
    out = apply_curation(rep, store=use, learning_store=ls)
    assert out["forge_proposals_expired"] == ["watched"]
    assert not str(ls._load_experiment("watched").get("forge_proposal") or "")
    print("--- proposal expiry ---\n  9-day-old unreviewed proposal swept OK")


if __name__ == "__main__":
    print("=" * 60)
    print("FORGE F4 TIER-1 WATCH")
    print("=" * 60)
    test_rollback_on_new_noise_vote()
    test_rollback_on_credit_rate_regression()
    test_confirm_after_quiet_window()
    test_young_provisional_is_left_alone()
    test_stale_proposal_expires()
    print("\nALL FORGE F4 TESTS PASSED")
