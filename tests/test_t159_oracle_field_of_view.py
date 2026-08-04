"""PRE-REGISTERED ACCEPTANCE (T159) -- the oracle must measure the detector's REAL field of view.

T159 was filed as a hole in check_wiring: "a try-block def in a REACHABLE core module is seen by
public_defs and never reported; detector health 0.67 where it should be 1.0". Reproducing it
refuted that diagnosis on its central factual claim.

  core/recall/precision_audit.py is NOT reachable.  `t in reachable` -> False. It is on the
  module-level backlog (EXCEPTIONS, 17 entries) precisely BECAUSE it is unwired at module
  granularity, and check_wiring.py:499 drops every function in such a module from the candidate
  list on purpose -- reporting each dead function inside an already-reported dead module is the
  noise that turns a guard into a thing people silence (docstring at :420).

TWO-ARM EXPERIMENT that settled it (seed and k held constant, so plant() drew the SAME template
and the SAME generated name in both arms; only the target module varied):

  Arm A  core/recall/precision_audit.py  (unreachable)  ->  emit_0e912c  MISSED
  Arm B  core/comm/blobs.py              (reachable)    ->  emit_0e912c  CAUGHT  "(:104) [NEW]"

Same shape string in both: 'try-block def (T143 shape)'. The shape is INNOCENT. The gate is
healthy. The 0.67 was an ARTEFACT -- and it is the SAME defect as calibration RUN 1 ("a canary
outside the detector's field of view measures nothing"), one level deeper: RUN 1 aligned the
oracle to `core_universe` (151 modules), but the gate's real field of view is `cand` (134),
computed downstream. 11.3% of the oracle's target universe was blind-by-design territory where a
MISS is correct behaviour, and a canary landing there was scored as detector failure.

The fix is therefore in the ORACLE, not the detector -- and it must be structural. The reason
RUN 1's fix failed is that it RE-IMPLEMENTED the detector's selector by walking core/. Any copy
drifts. The oracle must ASK the detector what it examines.

  K9   check_wiring exposes ONE definition of the function gate's field of view, and the gate
       itself uses it -- so the oracle and the gate cannot disagree
  K10  that field of view EXCLUDES unreachable and excepted modules (the 11.3% blind region)
  K11  the oracle's default selector is DERIVED FROM THE DETECTOR, not re-implemented: no module
       the detector excludes may ever be offered as a plant target
  K12  the manifest RECORDS how the universe was resolved and how big it was, so a silently
       shrinking field of view is visible in the receipts. A fix that makes detector health look
       good by narrowing what it measures is the worst available outcome, so narrowing must be
       impossible to do quietly.
  K13  END TO END, the claim T159 actually made: every CATCHABLE canary planted by the DEFAULT
       selector into a real worktree is caught by the real gate. Detector health 1.0, not 0.67.

Run: py -m pytest tests/test_t159_oracle_field_of_view.py -q
"""
import json
import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


def _wiring():
    from scripts.checkers import check_wiring
    return check_wiring


def _oracle():
    from scripts import canary_oracle
    return canary_oracle


@pytest.fixture(scope="module")
def worktree(tmp_path_factory):
    """A real detached worktree of HEAD -- the oracle's shadow, outside the live tree."""
    path = str(tmp_path_factory.mktemp("t159_shadow") / "wt")
    r = subprocess.run(["git", "worktree", "add", "--detach", path, "HEAD"],
                       cwd=ROOT, capture_output=True, text=True)
    if r.returncode != 0:
        pytest.skip(f"git worktree unavailable: {r.stderr.strip()}")
    yield path
    subprocess.run(["git", "worktree", "remove", "--force", path],
                   cwd=ROOT, capture_output=True)


# --------------------------------------------------------------------------- K9

def test_k9_one_definition_of_the_gates_field_of_view():
    """check_wiring OWNS the definition, and function_level() consumes it.

    Two copies of a selector is how RUN 1's fix failed: the oracle walked core/ and the gate
    filtered downstream, and nothing made them agree.
    """
    W = _wiring()
    assert hasattr(W, "candidate_modules"), (
        "check_wiring must expose candidate_modules() -- the single definition of what the "
        "FUNCTION gate actually examines. Without it every consumer re-implements the filter.")

    cand = W.candidate_modules()
    assert isinstance(cand, (list, tuple)) and cand, "candidate_modules() returned nothing"

    # the gate's own analysis must agree with the exported definition, or they have drifted
    core_universe, reachable, _unwired = W.analyze()
    expected = sorted(m for m in core_universe
                      if m in reachable and m not in W.EXCEPTIONS)
    assert sorted(cand) == expected, (
        "candidate_modules() disagrees with the filter check_wiring applies internally")


# --------------------------------------------------------------------------- K10

def test_k10_the_field_of_view_excludes_the_blind_region():
    """Unreachable and excepted modules are OUTSIDE the function gate, by design."""
    W = _wiring()
    cand = set(W.candidate_modules())
    core_universe, reachable, _unwired = W.analyze()

    blind = {m for m in core_universe if m not in reachable or m in W.EXCEPTIONS}
    assert blind, "expected a non-empty blind region (17 modules when T159 was filed)"
    assert not (cand & blind), "candidate set leaked a module the gate cannot report on"

    # the specific module T159 was filed against, named so the ticket stays refutable
    t = "core/recall/precision_audit.py"
    if t in core_universe:
        assert t not in reachable, (
            "T159 asserted this module IS reachable; if that ever becomes true this pin must be "
            "re-derived rather than deleted")
        assert t not in cand


# --------------------------------------------------------------------------- K11

def test_k11_oracle_targets_are_derived_from_the_detector(worktree):
    """The default selector ASKS the shadow's own detector. It never re-implements it."""
    C = _oracle()
    W = _wiring()

    universe = C._gate_universe(worktree)
    assert universe, "the default selector resolved to nothing"

    rel = {os.path.relpath(p, worktree).replace(os.sep, "/") for p in universe}
    cand = set(W.candidate_modules())

    leaked = rel - cand
    assert not leaked, (
        f"the oracle offered {len(leaked)} target(s) the gate structurally cannot report on -- "
        f"a canary planted there is a MISLABEL, not a miss. Sample: {sorted(leaked)[:5]}")


# --------------------------------------------------------------------------- K12

def test_k12_the_manifest_records_how_the_universe_was_resolved(worktree):
    """A shrinking field of view must be visible in the receipts, never silent."""
    C = _oracle()
    m = C.plant(worktree, k=3, seed=1234)

    assert "universe" in m, (
        "the manifest must record the field of view it planted into -- otherwise a fix that "
        "improves detector health by narrowing the universe is indistinguishable from a real "
        "improvement, which is the exact failure this ticket is made of")
    u = m["universe"]
    assert u.get("source") == "detector", (
        f"a real worktree must resolve its universe by ASKING the detector; got {u.get('source')!r}")
    assert isinstance(u.get("size"), int) and u["size"] > 0

    # Against the SHADOW's own detector, not this tree's. They legitimately differ: a worktree
    # holds only TRACKED files, so an untracked core module present here is absent there (that
    # exact case, core/comm/room_feed.py, made this assertion fail the first time it was written).
    # Comparing to the live number would reintroduce T159's mistake in the pin itself -- asserting
    # against a universe that is not the one being measured.
    r = subprocess.run([sys.executable, "scripts/checkers/check_wiring.py", "--candidates"],
                       cwd=worktree, capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, "the shadow's own detector could not report its field of view"
    assert u["size"] == len(json.loads(r.stdout))


# --------------------------------------------------------------------------- K13

def test_k13_every_catchable_canary_is_caught_end_to_end(worktree):
    """The claim T159 actually made, measured against the real gate.

    This is the pin that would have refuted the ticket before it was filed.
    """
    C = _oracle()
    manifest = C.plant(worktree, k=9, seed=4242)

    r = subprocess.run([sys.executable, "scripts/checkers/check_wiring.py", "--report"],
                       cwd=worktree, capture_output=True, text=True, timeout=600)
    out = r.stdout + r.stderr

    catchable = [c for c in manifest["canaries"] if c["cls"] == "catchable"]
    assert catchable, "no catchable canaries planted"

    missed = [c for c in catchable if c["name"] not in out]
    health = 1.0 - (len(missed) / len(catchable))
    assert not missed, (
        f"detector health {health:.2f} -- {len(missed)}/{len(catchable)} catchable canaries "
        f"missed: {[(c['name'], c['file'], c['shape']) for c in missed]}")

    # the try-block shape specifically, since that is what T159 accused
    tryblock = [c for c in catchable if "try-block" in (c.get("shape") or "")]
    if tryblock:
        assert all(c["name"] in out for c in tryblock), (
            "the T143 try-block shape was missed -- T159's original diagnosis would be back")
