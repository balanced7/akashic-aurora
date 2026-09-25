"""T408 RED pins -- nothing asks whether what the house believes is landed actually is.

THE NIGHT THAT PRODUCED THIS (2026-09-24/25). Six findings in one session, one shape:

  1. tests/test_find_everything_red.py   pinned SHIPPED code, untracked; survived only because
                                         a peer's message happened to name the file
  2. tests/test_eye_seat_capture.py      the SPEC of an unbuilt slice carrying the operator's
                                         verbatim ask, untracked 36 days; a prior-art search
                                         could not reach it, so the slice was partly rebuilt
  3. 42 of 764 test pins                 untracked, 5.5%, measured at HEAD 2c27a64f
  4. a lesson announced as "captured"    absent from the store; the knowledge survived only in
                                         working code and a chat transcript
  5. wish W214                           filed through the door, its file edit never committed
  6. state/coord/tasks.json              577 uncommitted lines, while boot's own precedence
                                         line reads "TASK LEDGER (git-durable, gated
                                         transitions) beats durable NOTES ..."

Six instances, one missing organ. In EVERY case the reporting surface said success: the door
printed [OK], the suite was green, the handoff said "everything below is pushed" while two
commits sat unpushed. Nothing in the house asks the question these all answer badly --

    WHAT DOES THIS HOUSE BELIEVE IS DURABLE THAT IS NOT?

There are 19 checkers and none of them ask it. The closest neighbours ask adjacent questions:
check_wiring asks whether built code is REACHABLE, check_pointer_promises whether a link's
target holds what the prose PROMISES, check_preregistration whether a pin landed BEFORE its
implementation. All three presume the artifact is in git. This one does not.

Item 6 is the sharpest and the reason this is a durability question rather than a hygiene one:
it is not a file someone forgot to commit, it is the house's TOP PRECEDENCE AUTHORITY
self-describing as git-durable while diverging from git. The claim and the state disagree, and
the claim is what every seat reads at boot.

DESIGN CONSTRAINTS these pins encode, each from a law this house already paid for:

  * RATCHET, NOT VERDICT. 42 untracked pins exist today. A gate that fails on all of them on
    day one gets switched off by lunchtime, which is how check_wiring's EXCEPTIONS baseline
    came to exist. Freeze today, fail on NEW.
  * ZERO IS NOT NO. "checked, nothing found" and "could not check" must be different answers.
    A sweep that reports 0 when git is unavailable is the exact failure it exists to catch.
  * A POSITIVE CANARY. A guard that infers from context shares the failure it guards, so the
    pins PLANT a real untracked file in a real temp repo and require detection -- never a
    mocked git.
  * STATE THE SCOPE. The report names what it scanned, per the coverage-contract law.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

os.environ.setdefault("AI_SETUP", tempfile.mkdtemp())
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo)] + list(args),
                          capture_output=True, text=True)


@pytest.fixture
def repo(tmp_path):
    """A real git repo with one commit. Real, because a mocked git cannot fail the way git does."""
    _git(tmp_path, "init", "-q", "-b", "master")
    _git(tmp_path, "config", "user.email", "pin@akashic-aurora.local")
    _git(tmp_path, "config", "user.name", "pin")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_landed.py").write_text("def test_ok():\n    assert True\n")
    _git(tmp_path, "add", "tests/test_landed.py")
    _git(tmp_path, "commit", "-q", "-m", "seed")
    return tmp_path


def _sweep():
    try:
        from scripts.checkers import check_durability
    except ImportError as e:
        pytest.fail(
            f"scripts/checkers/check_durability.py does not exist ({e}). Nineteen checkers ask "
            "whether committed things are correct; none asks whether the things the house "
            "believes it has committed are actually there.")
    return check_durability


# ---------------------------------------------------------------- the organ exists
def test_sweep_reports_three_planes():
    """One call, one answer, covering the three mechanically checkable durability claims."""
    mod = _sweep()
    out = mod.sweep(ROOT)
    assert isinstance(out, dict), f"sweep() must return a dict, got {type(out).__name__}"
    for key in ("untracked_pins", "unpushed_commits", "uncommitted_durable_state"):
        assert key in out, (
            f"sweep() does not report '{key}'. All three were live defects on 2026-09-24 and "
            f"each was invisible to every existing checker. Got: {sorted(out)}")
    assert "scanned" in out, (
        "the report must state WHAT IT SCANNED -- a count without its frame is not a coverage "
        "claim (a_coverage_contract_must_state_the_scope_it_globs_not_just_the_files_it_read)")


# ---------------------------------------------------------------- the positive canary
def test_a_planted_untracked_pin_is_found(repo):
    """Plant the exact defect and require detection. No mocked git: a guard that infers from
    context shares the failure it guards."""
    mod = _sweep()
    before = mod.untracked_pins(repo)
    assert before == [], f"a freshly committed repo has no untracked pins, got {before}"
    (repo / "tests" / "test_orphan_red.py").write_text("def test_x():\n    assert False\n")
    after = mod.untracked_pins(repo)
    assert any("test_orphan_red.py" in str(p) for p in after), (
        f"the planted untracked pin was not detected. Found: {after}. This is the "
        "test_eye_seat_capture.py case -- a red pin that sat outside git for 36 days.")


def test_a_planted_unpushed_commit_is_found(repo):
    """The handoff said 'everything below is pushed (origin/master ec169def)'. Two commits were
    not. An outside reviewer is structurally incapable of seeing them, which is precisely why
    the claim survived."""
    mod = _sweep()
    (repo / "tests" / "test_landed.py").write_text("def test_ok():\n    assert 1\n")
    _git(repo, "add", "tests/test_landed.py")
    _git(repo, "commit", "-q", "-m", "local only")
    found = mod.unpushed_commits(repo)
    assert found, (
        "a commit with no upstream counterpart was not reported. A repo with no remote at all "
        "is the strongest form of this: NOTHING here has been published.")


# ---------------------------------------------------------------- zero is not no
def test_unknown_is_not_zero(tmp_path):
    """THE LAW THIS ORGAN MUST NOT BREAK. A sweep that answers 0 when it could not look is the
    same failure it exists to catch, wearing the organ's own badge. A directory that is not a
    git repository must produce an explicit unknown, never an empty list that reads as clean."""
    mod = _sweep()
    out = mod.sweep(tmp_path)          # not a git repo
    verdict = str(out.get("verdict", "")).upper()
    assert "UNKNOWN" in verdict or out.get("unknown"), (
        f"sweeping a non-repository returned {out.get('verdict')!r} with no unknown marker. "
        "'checked, nothing found' and 'could not check' must be different answers "
        "(zero_is_not_no_silence_is_not_a_verdict).")


def test_clean_repo_says_checked_not_unknown(repo):
    """The other half of the same law: when it CAN look and finds nothing, that is a real zero
    and must not hide behind unknown."""
    mod = _sweep()
    out = mod.sweep(repo)
    assert not out.get("unknown"), \
        f"a readable git repo was reported as unevaluable: {out.get('verdict')!r}"
    assert out["untracked_pins"] == [], f"clean repo reported pins: {out['untracked_pins']}"


# ---------------------------------------------------------------- the ratchet
def test_ratchet_passes_known_and_fails_new(repo):
    """42 untracked pins exist today. A gate failing on all of them is a gate nobody runs --
    the reason check_wiring froze its known-standalone modules into EXCEPTIONS. Freeze today,
    fail on NEW."""
    mod = _sweep()
    (repo / "tests" / "test_known_orphan.py").write_text("def test_x():\n    assert True\n")
    baseline = mod.untracked_pins(repo)
    assert mod.new_since(repo, baseline) == [], \
        "a pin already in the baseline must not fail the gate"
    (repo / "tests" / "test_fresh_orphan.py").write_text("def test_y():\n    assert True\n")
    fresh = mod.new_since(repo, baseline)
    assert any("test_fresh_orphan" in str(p) for p in fresh), (
        f"a NEW untracked pin must fail the ratchet; new_since returned {fresh}")


# ---------------------------------------------------------------- the declared authority
def test_durable_state_paths_are_declared_not_inferred():
    """Which files claim durability is a DECLARATION, not a guess.

    boot prints: "Precedence when sources conflict: TASK LEDGER (git-durable, gated
    transitions) beats durable NOTES ...". The ledger is therefore the house's top authority
    AND self-described as git-durable, so a divergence between it and git is the claim
    contradicting itself -- measured at 577 uncommitted lines on 2026-09-25."""
    mod = _sweep()
    declared = getattr(mod, "DURABLE_STATE_PATHS", None)
    assert declared, (
        "check_durability.DURABLE_STATE_PATHS does not exist. Which paths carry a durability "
        "CLAIM must be written down, or the sweep is one seat's opinion about what matters.")
    joined = " ".join(str(p) for p in declared).replace("\\", "/").lower()
    assert "tasks.json" in joined, (
        f"the task ledger is the precedence authority boot names first and must be watched; "
        f"declared paths are {declared}")


# ---------------------------------------------------------------- postal inertness
def test_sweep_reads_no_credential(tmp_path, monkeypatch):
    """T365's bar, applied before the seam exists: a durability probe reads git and the
    filesystem. It must never resolve a credential to decide what is durable."""
    mod = _sweep()
    monkeypatch.setenv("AKASHIC_SECRETS_DIR", str(tmp_path))
    out = mod.sweep(ROOT)
    assert isinstance(out, dict)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
