"""
T208 -- "is this failure mine?" answered by the thing that already knows. RED first.

MEASURED TODAY, and this is the receipt that made the slice. I hit four test failures
while shipping T200 and T203, and for each one I ran a manual `git stash` bisect to learn
whether it pre-dated my change. That cost 2-4 turns apiece, and ONE of them I got WRONG --
I concluded "that one IS mine" from a single-test run that was inconclusive, said so, and
had to correct myself two messages later.

The system already knew one of the four. `state/coord/suite_baseline.json` has recorded
`test_t060_n0_shadow_router.py::test_cli_and_mcp_route_json_are_identical` as a known
failure since 2026-07-24. Nothing surfaced it at the moment I hit it. This is the same
shape as T197 (`the verdict existed, the door never asked`) in a second organ, hours later.

WHY IT ONLY ANSWERED 1 OF 4: the baseline is 320h stale (recorded at bb0beac). The other
three broke AFTER it was recorded -- T196c landed 2026-08-05 and turned the T171/T181 laws
red. So the organ is not the wrong shape; it is out of date and silent about it.

THE DEFECT THIS PINS, confirmed at line level by a grounded helper reading the module:
`delta()` (suite_baseline.py:113-120) does pure set math against the stored failures and
performs NO sha comparison anywhere -- not in delta, not in read, not in any helper. The
stored `sha` is displayed by the boot line and never checked. So "new" silently means two
completely different things:

    * genuinely new since the baseline  -> probably yours, investigate
    * broke sometime in the 14-day gap  -> UNKNOWN, could be anyone's

Collapsing those is how a baseline trains a lie. It is also the same one-word-two-meanings
failure as `drained`, `unread` and `wakeable` -- the fourth instance in this arc.

STALENESS CONTAMINATES BOTH DIRECTIONS, which the naive fix misses. A node IN the baseline
looks inherited -- but over 14 days it could have been fixed and re-broken by me, so a
stale baseline weakens the exculpating verdict too. Pinned below, because "it was failing
before" is the more comfortable answer and therefore the one that will rot first.

Run: py -m pytest tests/test_t208_whose_failure.py -q
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import suite_baseline as SB  # noqa: E402


@pytest.fixture
def baseline(tmp_path, monkeypatch):
    """A baseline recorded at a known sha, isolated from the real state file."""
    path = tmp_path / "suite_baseline.json"
    monkeypatch.setattr(SB, "BASELINE_PATH", str(path))

    def _write(sha, nodes):
        import json
        path.write_text(json.dumps({
            "v": 1, "sha": sha, "seat": "claude", "at": "2026-07-24T00:14:40",
            "failures": [{"node": n, "lane": ""} for n in nodes],
            "claims_at_snapshot": {}}), encoding="utf-8")
    return _write


def test_a_fresh_baseline_can_say_a_failure_is_yours(baseline, monkeypatch):
    """Same sha as HEAD: the baseline saw this exact tree, so a node absent from it is
    genuinely new. This is the ONLY condition under which 'yours' is honest."""
    baseline("abc1234", ["tests/a.py::old"])
    monkeypatch.setattr(SB, "head_sha", lambda: "abc1234")
    v = SB.verdicts(["tests/a.py::old", "tests/b.py::fresh"])
    assert v["by_node"]["tests/b.py::fresh"]["verdict"] == "YOURS"
    assert v["by_node"]["tests/a.py::old"]["verdict"] == "INHERITED"
    assert v["stale"] is False


def test_a_stale_baseline_never_says_yours(baseline, monkeypatch):
    """THE DEFECT. delta() called this 'new'. Over a 14-day gap a failure could have
    arrived from anyone -- claiming it is yours is a fabricated attribution, and the
    cost of it is a wrong public claim (which I made today)."""
    baseline("bb0beac", ["tests/a.py::old"])
    monkeypatch.setattr(SB, "head_sha", lambda: "99ffff0")
    v = SB.verdicts(["tests/b.py::fresh"])
    assert v["by_node"]["tests/b.py::fresh"]["verdict"] == "UNKNOWN"
    assert v["stale"] is True


def test_staleness_also_weakens_the_exculpating_verdict(baseline, monkeypatch):
    """The half a naive fix misses. A node IN a stale baseline is only PROBABLY
    inherited -- it could have been fixed and re-broken in the gap. 'It was failing
    before' is the comfortable answer, so it is the one that rots unwatched."""
    baseline("bb0beac", ["tests/a.py::old"])
    monkeypatch.setattr(SB, "head_sha", lambda: "99ffff0")
    v = SB.verdicts(["tests/a.py::old"])
    assert v["by_node"]["tests/a.py::old"]["verdict"] == "LIKELY_INHERITED"


def test_every_verdict_carries_what_to_do(baseline, monkeypatch):
    """A classification with no next move is a label. UNKNOWN in particular must say
    'bisect this one' -- that is the whole ergonomic win: bisect 3 instead of 4."""
    baseline("bb0beac", ["tests/a.py::old"])
    monkeypatch.setattr(SB, "head_sha", lambda: "99ffff0")
    v = SB.verdicts(["tests/a.py::old", "tests/b.py::fresh"])
    for node, row in v["by_node"].items():
        assert row.get("next"), f"{node} has no next step"
    assert "bisect" in v["by_node"]["tests/b.py::fresh"]["next"].lower()


def test_no_baseline_is_unknown_not_yours(baseline, monkeypatch):
    """An absent baseline must not read as 'everything is new and therefore yours'.
    delta() documents that behaviour as 'an honest first run', which is fine for a diff
    and wrong for an ATTRIBUTION."""
    monkeypatch.setattr(SB, "head_sha", lambda: "abc1234")
    v = SB.verdicts(["tests/b.py::fresh"])
    assert v["by_node"]["tests/b.py::fresh"]["verdict"] == "UNKNOWN"
    assert v.get("baseline_sha") in (None, "")


def test_unreadable_head_is_unknown_never_fresh(baseline, monkeypatch):
    """If we cannot resolve HEAD we cannot know the baseline is current, and the safe
    reading is UNKNOWN. Failing toward 'fresh' would manufacture confident attributions
    out of a broken git call."""
    baseline("abc1234", ["tests/a.py::old"])
    monkeypatch.setattr(SB, "head_sha", lambda: "")
    v = SB.verdicts(["tests/b.py::fresh"])
    assert v["stale"] is True
    assert v["by_node"]["tests/b.py::fresh"]["verdict"] == "UNKNOWN"


def test_fixed_nodes_are_reported_separately(baseline, monkeypatch):
    """A baseline failure that now passes is news worth having -- and it is the signal
    that the baseline is due for a re-record. Only claimable on a FULL run."""
    baseline("abc1234", ["tests/a.py::old", "tests/c.py::gone"])
    monkeypatch.setattr(SB, "head_sha", lambda: "abc1234")
    v = SB.verdicts(["tests/a.py::old"], full_suite=True)
    assert v["fixed"] == ["tests/c.py::gone"]


def test_a_subset_run_never_calls_unrun_tests_fixed(baseline, monkeypatch):
    """CAUGHT LIVE on this function's first real use: running three files reported TEN
    baseline failures as 'fixed' because they were absent from the results -- they had
    simply not been run. 'Fixed' invites a re-record, which would have deleted ten known
    failures from the receipt. Correct under one assumption, silently wrong under
    another: the same shape as every other defect in this arc."""
    baseline("abc1234", ["tests/a.py::old", "tests/c.py::never_ran"])
    monkeypatch.setattr(SB, "head_sha", lambda: "abc1234")
    v = SB.verdicts(["tests/a.py::old"])          # subset: full_suite defaults False
    assert v["fixed"] == [], "a subset run cannot prove anything was fixed"
    assert v["not_evaluated"] == ["tests/c.py::never_ran"]
    assert v["full_suite"] is False


def test_summary_counts_match_the_rows(baseline, monkeypatch):
    """A headline that disagrees with its own detail is worse than no headline."""
    baseline("bb0beac", ["tests/a.py::old"])
    monkeypatch.setattr(SB, "head_sha", lambda: "99ffff0")
    v = SB.verdicts(["tests/a.py::old", "tests/b.py::x", "tests/c.py::y"])
    counts = v["counts"]
    assert sum(counts.values()) == len(v["by_node"]) == 3


def test_delta_keeps_its_old_contract(baseline, monkeypatch):
    """Existing callers must be untouched: verdicts() is ADDITIVE. Changing delta's
    shape would break the boot line and whatever else reads it."""
    baseline("abc1234", ["tests/a.py::old"])
    d = SB.delta(["tests/a.py::old", "tests/b.py::fresh"])
    assert set(d.keys()) == {"new", "fixed", "inherited"}
    assert d["new"] == ["tests/b.py::fresh"]
