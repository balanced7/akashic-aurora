"""Tests for ship.py's plan builder -- the gated slice-ship ritual, encoded once.

Run: py tests/test_ship.py   (or via pytest)

We test build_plan (pure: ordered steps, no side effects) rather than executing real git/pytest.
The discipline that must hold: the GATE comes before the commit; the commit uses EXPLICIT paths;
flags add/remove the right steps.
"""
import os
import sys
from argparse import Namespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import ship


def _args(**over):
    base = dict(message="msg", paths=["a.py", "b.py"], agent="claude", learn_exp=None,
                tried="", result="", recommend="", anti_pattern="", no_test=False,
                no_snapshot=False, dry_run=False)
    base.update(over)
    return Namespace(**base)


def _labels(plan):
    return [label for label, _ in plan]


def test_full_plan_order():
    plan = ship.build_plan(_args())
    labels = _labels(plan)
    # gate BEFORE commit, then snapshot. Guards grew with the membrane work (comprehensibility /
    # door-parity / wiring) -- assert the fixed anchors + that every guard runs before the tests+commit.
    assert labels[0] == "guard: boundaries" and labels[1] == "guard: doc-freshness", labels
    assert labels[-3:] == ["tests (full suite)", "commit + push", "snapshot"], labels
    assert all("guard" in l for l in labels[:labels.index("tests (full suite)")]), labels
    commit = dict(plan)["commit + push"]
    assert "scripts/mirror.py" in commit and "a.py" in commit and "b.py" in commit, commit
    assert "msg" in commit, "commit message is passed to mirror"
    print("\n--- full plan ---\n  gate -> commit(explicit paths) -> snapshot OK")


def test_no_test_skips_gate():
    labels = _labels(ship.build_plan(_args(no_test=True)))
    assert not any("guard" in l or "tests" in l for l in labels), labels
    assert "commit + push" in labels
    print("--- --no-test ---\n  gate skipped, commit still present OK")


def test_no_snapshot():
    assert "snapshot" not in _labels(ship.build_plan(_args(no_snapshot=True)))
    print("--- --no-snapshot ---\n  snapshot step removed OK")


def test_learn_step_included_with_args():
    plan = ship.build_plan(_args(learn_exp="ship_test", tried="t", result="r", recommend="rec"))
    assert "record lesson" in _labels(plan)
    learn = dict(plan)["record lesson"]
    assert "learn" in learn and "ship_test" in learn and "t" in learn and "r" in learn, learn
    print("--- lesson step ---\n  --learn-exp adds a faithful learn step OK")


def test_anti_pattern_threaded_into_learn():
    plan = ship.build_plan(_args(learn_exp="ship_test", anti_pattern="sync_flush_bad"))
    learn = dict(plan)["record lesson"]
    assert "--anti-pattern" in learn and "sync_flush_bad" in learn, learn
    # and absent when not provided (no empty flag leaking into the command)
    assert "--anti-pattern" not in dict(ship.build_plan(_args(learn_exp="x")))["record lesson"]
    print("--- anti-pattern threaded ---\n  --anti-pattern flows into the learn step, absent otherwise OK")


if __name__ == "__main__":
    print("=" * 60)
    print("SHIP PLAN TESTS")
    print("=" * 60)
    test_full_plan_order()
    test_no_test_skips_gate()
    test_no_snapshot()
    test_learn_step_included_with_args()
    test_anti_pattern_threaded_into_learn()
    print("\n" + "=" * 60)
    print("ALL SHIP TESTS PASSED")
    print("=" * 60)
