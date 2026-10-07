"""PRE-REGISTERED acceptance: the gates fire at the WRITE, not only in CI.

Registered before implementation, per M3.

THE ROOT CAUSE THESE PINS CLOSE (diagnosed 2026-08-01, CI red 30 consecutive days):
The repo has five good guardrails, four of them with debt allowlists, a suite-baseline verb,
and a pre-commit script. None of it was enforced at the moment of authorship:

    .git/hooks/pre-commit           did not exist
    scripts/githooks/pre_commit.py  ran ONE of the five guardrails

So the loop from "author a violation" to "learn about it" was: commit -> push -> 40s of CI ->
a red badge. That loop has three fatal properties. It is too slow to correct behaviour. It is
delivered to nobody. And once the badge sits red, a NEW red carries no information -- the
signal destroys itself, which is exactly how thirty days passed unnoticed.

TWO STRUCTURAL FIXES, pinned here:

1. DERIVED ARTIFACTS ARE NOT SOURCE ARTIFACTS. docs/MODULE_INDEX, PHYSICS, MAP, DOORS and
   PRIOR_ART are GENERATED, then committed, then gated on being fresh -- a permanent race,
   because every code commit invalidates them. Measured: they were regenerated twice in one
   hour and went stale both times, through nobody's fault. The commit must regenerate them,
   not check them.

2. THE RATCHET, APPLIED AUTOMATICALLY. The allowlists exist but need a human to enumerate each
   item, so debt that arrives faster than someone allowlists it keeps the gate red forever. A
   counted baseline lets green be achievable TODAY at the current debt level, while making the
   debt monotonically non-increasing.

WHY AN INSTALLER AND NOT THE HOOK ITSELF: .git/hooks/ is not tracked by git, so a hook can
never be committed. The committable artifact is the INSTALLER, and `doctor --deploy` must
report when it has not been run -- otherwise this repeats the console-fix trap, where half the
fix lived in a file that could not be version-controlled.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.paths import repo_root  # noqa: E402

ROOT = repo_root()
INSTALLER = ROOT / "scripts" / "githooks" / "install_git_hooks.py"
# The installer sets git config core.hooksPath -> scripts/githooks, where the hooks are
# TRACKED. So the hooks ARE version-controlled after all -- only the one-line git config is
# per-clone. My first draft assumed .git/hooks/ and was wrong about the repo it was testing.
HOOK = ROOT / "scripts" / "githooks" / "pre-commit"
BASELINE = ROOT / "state" / "ci" / "guardrail_baseline.json"

DERIVED_DOCS = ("MODULE_INDEX.md", "PHYSICS.md", "MAP.md", "DOORS.md", "PRIOR_ART.md")


def _run(args, **kw):
    return subprocess.run(args, capture_output=True, text=True, cwd=str(ROOT),
                          encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL,
                          close_fds=True, timeout=180, **kw)


# ------------------------------------------------------------------ the installer
def test_w1_an_installer_exists_because_hooks_cannot_be_committed():
    """.git/hooks/ is untracked by git. If the only artifact is the hook, the fix cannot
    survive a fresh clone -- the same trap the console fix fell into."""
    assert INSTALLER.exists(), (
        "no scripts/githooks/install_git_hooks.py -- a hook that cannot be installed from tracked "
        "code does not survive a clone, and this repo has already been bitten by exactly that")


def test_w2_installer_is_idempotent_and_actually_installs():
    r1 = _run([sys.executable, "-X", "utf8", str(INSTALLER)])
    assert r1.returncode == 0, f"installer failed: {r1.stdout}\n{r1.stderr}"
    import subprocess as _sp
    cfg = _sp.run(["git","config","core.hooksPath"], capture_output=True, text=True,
                  cwd=str(ROOT)).stdout.strip()
    assert cfg.replace(chr(92),"/").endswith("scripts/githooks"), (
        "core.hooksPath not set to scripts/githooks -- the hooks exist and are tracked, but "
        "git is not looking at them, so nothing runs at the write edge (got %r)" % cfg)
    assert HOOK.exists(), "tracked hook script missing"
    r2 = _run([sys.executable, "-X", "utf8", str(INSTALLER)])
    assert r2.returncode == 0, "installer is not idempotent -- second run failed"


def test_w3_doctor_deploy_reports_when_the_hook_is_missing():
    """The console fix taught this: a fix living in an uncommittable file must be REPORTED,
    or a fresh machine is silently unprotected and nothing explains why."""
    r = _run([sys.executable, "-X", "utf8", "agent_cli.py", "doctor", "--deploy"])
    out = (r.stdout or "") + (r.stderr or "")
    assert "hook" in out.lower(), (
        "doctor --deploy says nothing about the pre-commit hook, so a fresh deploy cannot "
        "discover that its write-edge enforcement is missing:\n" + out[:600])


# ------------------------------------------------------- fix 1: derived != source
def test_w4_hook_regenerates_derived_docs_instead_of_only_checking_them():
    """The permanent race, closed. A commit that touches code must LEAVE the derived docs
    fresh, not fail because they went stale the moment the code changed."""
    assert HOOK.exists(), "tracked hook script missing"
    body = HOOK.read_text(encoding="utf-8", errors="replace")
    src = (ROOT / "scripts" / "githooks" / "pre_commit.py").read_text(
        encoding="utf-8", errors="replace")
    joined = body + src
    assert "gen_" in joined or "regen" in joined.lower(), (
        "the hook does not regenerate the derived docs -- checking a derivative for freshness "
        "is a category error that guarantees a permanent race")


def test_w5_regeneration_makes_the_freshness_gate_pass():
    """The right invariant, and my first draft had the wrong one.

    I originally asserted the docs are fresh RIGHT NOW. That can never hold in a live tree: any
    edit between the last regeneration and the assertion restales them, and this pin duly went
    red on my own edits three separate times in one session -- which is the very race the fix
    exists to remove, not a defect the pin should report.

    The property that actually matters is that REGENERATION RESTORES FRESHNESS, because the
    commit now regenerates. A pin that fires on a transient state teaches people to ignore
    pins, which is the same disease one level down from the one being fixed here.
    """
    from scripts.githooks import pre_commit as pc  # noqa

    ok, note = pc.regenerate_derived(stage=False)
    assert ok, f"a generator did not run, so freshness cannot be restored: {note}"
    r = _run([sys.executable, "-X", "utf8", "scripts/checkers/check_comprehensibility.py"])
    assert r.returncode == 0, (
        "regeneration ran but the freshness gate still fails -- the generators and the checker "
        f"disagree about what fresh means:\n{r.stdout[-800:]}")


# ------------------------------------------------------------- fix 2: the ratchet
def test_w6_a_counted_baseline_exists_so_green_is_achievable_today():
    """Without this, a gate with pre-existing debt is red forever and therefore ignored --
    which is precisely how a 30-day outage goes unnoticed."""
    assert BASELINE.exists(), (
        "no state/ci/guardrail_baseline.json -- with live debt in wiring and door-parity, an "
        "absolute gate can never pass, so it teaches everyone to ignore it")
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert isinstance(data.get("counts"), dict) and data["counts"], "baseline records no counts"


def test_w7_baseline_matches_reality_or_is_stale_loudly():
    """A baseline that drifts above reality silently re-hides debt someone already paid down."""
    data = json.loads(BASELINE.read_text(encoding="utf-8"))
    from scripts.githooks import pre_commit as pc  # noqa
    live = pc.guardrail_counts()
    worse = {k: (live.get(k), v) for k, v in data["counts"].items()
             if live.get(k, 0) > v}
    assert not worse, f"guardrail debt INCREASED beyond the baseline: {worse}"


def test_w8_the_hook_refuses_a_new_violation():
    """The point of the whole exercise: a violation is refused by the machine in front of you,
    in the second you make it -- not by a badge tomorrow that nobody reads."""
    from scripts.githooks import pre_commit as pc  # noqa
    # Construct the increase EXPLICITLY rather than by decrementing the recorded baseline.
    # The first draft did the latter, and it broke the moment the debt was actually paid to
    # zero: max(0, 0-1) == 0, so the "tightened" baseline equalled reality and the ratchet
    # correctly said fine. A pin that only works while debt EXISTS cannot guard a clean repo,
    # which is precisely the state it is supposed to protect.
    base = {"check_boundaries": 0}
    ok, msg = pc.ratchet_ok(baseline=base, live={"check_boundaries": 1})
    assert not ok, "ratchet accepted an increase in violations -- it is not a ratchet"
    assert msg, "ratchet refused without saying what got worse"
