"""PRE-REGISTERED ACCEPTANCE (T178) -- a missing baseline is UNKNOWN debt, never zero.

THE DEFECT. state/ci/guardrail_baseline.json is gitignored by `state/*`, nothing generated it,
and read_baseline() collapsed every failure -- including file-not-found -- into {}. ratchet_ok
then hit `if not base: return True`. So the write-edge ratchet, the 2026-08-01 root-cause fix for
thirty days of red CI, silently did not run for anyone who had not hand-built a baseline. Verified
before the fix: ratchet_ok(baseline={}, live={"check_boundaries": 99}) -> (True, "").

The irony sits one function deep. guardrail_counts' own docstring says "A CRASHED guardrail returns
-1 and NEVER counts as zero. Absence must not look like success" -- and read_baseline did exactly
that, immediately below it.

SECOND-ORDER: ratchet_ok iterates the BASELINE's keys, so a guard in GUARDRAILS with no entry was
never compared at all. That is why check_kind_policy (T177) enforced only on the machine that
baselined it -- it blocked nobody, and it protected nobody.

  K1  _load_baseline distinguishes present / missing / unreadable -- three states, not one falsy
  K2  ratchet_ok REFUSES an empty baseline (the exact call that proved the bug)
  K3  ratchet_ok REFUSES when the baseline file is absent, rather than passing
  K4  ensure_baseline materialises a missing baseline from live counts, and SAYS SO
  K5  ensure_baseline adopts a live guard that has no entry, and SAYS SO
  K6  a real baseline still ratchets a rise (W8's contract survives the fix)
  K7  a crashed guard (-1) still fails -- absence of a RUN is not a pass either
  K8  the baseline is TRACKED BY GIT, so the debt allowance travels with the repo

K8 is the half that makes the rest matter. A ratchet whose baseline is untracked is per-machine,
and "green" means green HERE.

Run: py -m pytest tests/test_t178_absence_is_not_zero_debt.py -q
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "scripts", "githooks"))

import pre_commit as pc  # noqa: E402

BASELINE_REL = "state/ci/guardrail_baseline.json"


def _point_at(monkeypatch, tmp_path, payload=None):
    """Aim the module at a throwaway baseline; None means 'no file at all'."""
    target = tmp_path / "guardrail_baseline.json"
    if payload is not None:
        target.write_text(json.dumps(payload), encoding="utf-8")
    monkeypatch.setattr(pc, "BASELINE_PATH", str(target))
    return str(target)


def test_k1_load_baseline_has_three_states_not_one_falsy(monkeypatch, tmp_path):
    _point_at(monkeypatch, tmp_path)
    assert pc._load_baseline() == ({}, "missing")

    _point_at(monkeypatch, tmp_path, {"counts": {"check_boundaries": 3}})
    assert pc._load_baseline() == ({"check_boundaries": 3}, "present")

    bad = tmp_path / "guardrail_baseline.json"
    bad.write_text("{not json", encoding="utf-8")
    counts, status = pc._load_baseline()
    assert (counts, status) == ({}, "unreadable"), (
        "a corrupt baseline must be distinguishable from an absent one and from a clean one")


def test_k2_an_empty_baseline_is_refused_not_passed():
    """The exact call that demonstrated the defect. It returned (True, '')."""
    ok, msg = pc.ratchet_ok(baseline={}, live={"check_boundaries": 99})
    assert ok is False, "an empty baseline ratchets NOTHING; that is not the same as clean"
    assert msg, "it must say why -- a silent refusal repeats the defect in the other direction"


def test_k3_a_missing_baseline_file_is_refused(monkeypatch, tmp_path):
    _point_at(monkeypatch, tmp_path)
    ok, msg = pc.ratchet_ok(live={"check_boundaries": 99})
    assert ok is False and "missing" in msg.lower(), (
        "a fresh clone had NO enforcement and NO notice -- absence read as success")


def test_k4_ensure_baseline_materialises_a_missing_file_and_says_so(monkeypatch, tmp_path):
    target = _point_at(monkeypatch, tmp_path)
    created, note = pc.ensure_baseline(live={"check_boundaries": 0, "check_kind_policy": 2})
    assert created is True and note, "materialising in silence would be the same defect"
    written = json.loads(open(target, encoding="utf-8").read())["counts"]
    assert written == {"check_boundaries": 0, "check_kind_policy": 2}, (
        "adopt TODAY's debt: a commit cannot be blamed for debt that predates it")
    ok, _ = pc.ratchet_ok(live={"check_boundaries": 0, "check_kind_policy": 2})
    assert ok is True, "having adopted the current level, the very next check must pass"


def test_k5_a_live_guard_absent_from_the_baseline_is_adopted_and_announced(monkeypatch, tmp_path):
    target = _point_at(monkeypatch, tmp_path, {"counts": {"check_boundaries": 0}})
    created, note = pc.ensure_baseline(live={"check_boundaries": 0, "check_kind_policy": 2})
    assert created is True, "a NEW guard with no entry was silently never compared -- T177's fate"
    assert "check_kind_policy" in note
    assert json.loads(open(target, encoding="utf-8").read())["counts"]["check_kind_policy"] == 2


def test_k6_a_real_baseline_still_refuses_a_rise():
    """W8's contract. The fix must not buy honesty about absence by losing the ratchet."""
    ok, msg = pc.ratchet_ok(baseline={"check_boundaries": 0}, live={"check_boundaries": 1})
    assert ok is False and "0 -> 1" in msg


def test_k7_a_crashed_guard_still_fails():
    ok, msg = pc.ratchet_ok(baseline={"check_boundaries": 0}, live={"check_boundaries": -1})
    assert ok is False and "did not RUN" in msg


def test_k8_the_baseline_travels_with_the_repo():
    """The half that makes the rest matter: a ratchet whose baseline is untracked is per-machine,
    so 'green' means green HERE. T177 enforced on exactly one workstation because of this."""
    tracked = subprocess.run(["git", "ls-files", BASELINE_REL], cwd=ROOT,
                             capture_output=True, text=True).stdout.strip()
    assert tracked == BASELINE_REL, (
        f"{BASELINE_REL} is not tracked by git, so the debt allowance does not travel -- "
        f"every fresh clone and CI itself runs with no ratchet at all")
