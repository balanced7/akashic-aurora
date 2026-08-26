"""Pins: a deliberately-gitignored path is ABSENT BY DESIGN, not drift.

CI went red for 8 consecutive pushes on 11 identical FAILs, all naming security/acl.json.
Nobody caught it locally because the stale-ref guard asks `os.path.exists`, and on a
developer machine that file DOES exist -- it is gitignored, not deleted. So the guard
returned green on every workstation and red on every clone. A check that disagrees with
itself across machines is worse than no check: it trains you to read CI as noise.

The absence is correct and permanent. Fence t384-acl-instance-split deliberately
un-tracked security/acl.json so a grant minted on one Aurora instance stops applying
verbatim on every instance that pulls -- an authority leak in both directions. The
tracked template (security/acl.example.json) stays, and the eleven references are all
still TRUE at runtime; they are just never satisfiable in a fresh clone.

A dated REF_ALLOWLIST entry was the other option and it is the wrong shape here: the
allowlist exists for refs that are TEMPORARILY missing, and its `expires` field is a
deliberate landmine that re-fails the build so nobody forgets. Pointing that at a
permanent condition just schedules this same outage for a future date.

So: git decides. A missing ref that git deliberately ignores is reported as a WARN
(visible, never silent), and only a ref that is missing for no declared reason FAILS.

Run: py -m pytest tests/test_ci_instance_local_refs_pins.py -q
"""
from __future__ import annotations

import os
import sys

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_ROOT, "scripts", "checkers"))
sys.path.insert(0, os.path.join(_ROOT, "scripts"))

import check_comprehensibility as cm  # noqa: E402


# ------------------------------------------------------------ asking git, not guessing
def test_gitignored_recognises_the_instance_local_acl():
    """security/acl.json is gitignored by .gitignore -- git is the authority, not us."""
    assert "security/acl.json" in cm._gitignored({"security/acl.json"})


def test_gitignored_does_not_claim_a_tracked_file():
    """A tracked, committed file must never be excused as absent-by-design."""
    assert cm._gitignored({"AGENTS.md"}) == set()


def test_gitignored_is_empty_for_no_input():
    """No refs in, no git call, no crash."""
    assert cm._gitignored(set()) == set()


# ------------------------------------------------------------------- the pure partition
def test_partition_routes_ignored_to_warn_and_the_rest_to_fail():
    missing = [("docs/MAP.md", "security/acl.json"),
               ("docs/MAP.md", "core/totally_invented.py")]
    drift, instance_local = cm.partition_missing(missing, {"security/acl.json"})

    assert drift == [("docs/MAP.md", "core/totally_invented.py")], (
        "a ref missing for no declared reason must still FAIL")
    assert instance_local == [("docs/MAP.md", "security/acl.json")], (
        "a deliberately-ignored ref is absent by design -- WARN, not FAIL")


# --------------------------------------------- the CI condition, reproduced on this box
@pytest.fixture()
def acl_looks_absent(monkeypatch):
    """Make security/acl.json look missing, exactly as it is in a fresh clone."""
    real_exists = os.path.exists

    def fake_exists(path):
        if str(path).replace("\\", "/").endswith("security/acl.json"):
            return False
        return real_exists(path)

    monkeypatch.setattr(cm.os.path, "exists", fake_exists)


def test_absent_gitignored_ref_does_not_fail_the_build(acl_looks_absent):
    """THE REGRESSION. This is precisely what reddened CI 8 times."""
    fails = cm._stale_refs()
    offenders = [f for f in fails if "security/acl.json" in f]
    assert offenders == [], (
        f"a gitignored path must not FAIL as drift; got {len(offenders)}: {offenders[:2]}")


def test_absent_gitignored_ref_is_still_reported_as_a_warning(acl_looks_absent):
    """Excused is not invisible -- the guard must not go quiet about it."""
    warns = cm._instance_local_refs()
    assert any("security/acl.json" in w for w in warns), (
        f"expected an instance-local WARN naming the ref, got {warns}")


def test_the_build_is_green_under_the_ci_condition(acl_looks_absent):
    """End to end: with acl.json absent, main() returns 0."""
    monkey_argv = ["check_comprehensibility.py"]
    old = sys.argv
    sys.argv = monkey_argv
    try:
        assert cm.main() == 0
    finally:
        sys.argv = old


# ------------------------------------------------------------------ no regression today
def test_stale_refs_still_clean_on_a_normal_working_copy():
    assert cm._stale_refs() == []
