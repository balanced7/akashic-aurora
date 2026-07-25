"""T070 pins: the suite must not be able to reach canonical knowledge state.

WHY THIS EXISTS
---------------
Standing hazard, carried in every boot's LIVE CONSTRAINTS for weeks: "the pytest suite
DESTROYS the live learning index -- run scripts/repair_learning_index.py --check after ANY
suite run." It replaced canonical `learn:experiments:all` with its own fixtures and wrote
fixture records into the live store. The documented workaround was to remember to repair
afterwards.

That workaround had a second cost, and it is the one that actually hurt: a suite that is
DANGEROUS to run is a suite nobody runs. It rotted unnoticed, and on 2026-07-25 CI turned
out to have been red for over a day with the whole suite skipped behind a failing gate. The
hazard and the rot are one loop.

THE MECHANISM, censused 2026-07-25:
  150 test files touch a default store / knowledge surface.
    8 imported `isolate_canonical` (the root-cause fix, opt-in per file).
  142 did not -- free to read and write canonical Redis db 0 and the live
      session_logs/store_state.json.

THE DESIGN QUESTION T070 ASKS is whether isolation should be implicit. conftest.py already
answered it once, for recall scratch: "NO test ever legitimately wants the real recall
scratch, so this one is unconditional." Backend isolation stayed opt-in only to protect
"suites that intentionally exercise the real backends" -- but `isolate_canonical` redirects
to Redis **db 15**, not to nothing, so a test wanting a live Redis still gets one. Only a
test asserting on CANONICAL CONTENT could break, and those are flaky by construction (T070's
own evidence: a boot under the flag read live data, '8 lesson(s)', and live notes leaked
non-ASCII into an ASCII pin).

So: isolate by default, opt OUT explicitly. Deny-by-default, matching the security schema.
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_the_suite_runs_isolated_by_default():
    """The flag conftest sets for every test, without any per-file opt-in."""
    assert os.environ.get("_AISETUP_TEST_ISOLATED") == "1", (
        "backend isolation is not universal -- this suite can reach canonical state"
    )


def test_ai_setup_is_not_the_real_repo():
    ai_setup = Path(os.environ.get("AI_SETUP", "")).resolve()
    assert ai_setup != ROOT, (
        f"AI_SETUP still points at the live repo ({ai_setup}) -- file-store writes would "
        f"land in canonical session_logs/"
    )


def test_redis_db_is_not_canonical():
    db = os.environ.get("REDIS_DB")
    assert db not in (None, "", "0"), (
        f"REDIS_DB={db!r} -- the suite would read and write the canonical logical DB"
    )


def test_canonical_state_file_is_unreachable_from_here():
    """The concrete artifact the hazard destroyed: session_logs/store_state.json."""
    from core.foundation.store import create_store
    s = create_store()
    path = getattr(s, "_path", None)
    if path is None:                      # Redis-backed: the db pin above covers it
        return
    resolved = Path(str(path)).resolve()
    canonical = (ROOT / "session_logs" / "store_state.json").resolve()
    assert resolved != canonical, (
        f"the default store resolves to CANONICAL {canonical} -- a write here is the "
        f"2026-06-20 incident and the learning-index destruction"
    )


def test_isolation_is_idempotent():
    """Importing the helper again must not re-roll the temp dir mid-run."""
    before = os.environ.get("AI_SETUP")
    sys.path.insert(0, str(ROOT / "tests"))
    import importlib
    import isolate_canonical
    importlib.reload(isolate_canonical)
    assert os.environ.get("AI_SETUP") == before, (
        "re-importing isolate_canonical moved AI_SETUP mid-run -- state would split"
    )


def test_spill_dir_is_isolated_too(tmp_path):
    """The store is not the only thing a test writes through.

    Found 2026-07-25 while tracing live pollution: agent_cli.py:83 derives the spill dir from
    `__file__` -- the location of agent_cli.py itself -- NOT from AI_SETUP:

        spill_dir = os.getenv("AKASHIC_SPILL_DIR") or os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "state", "spill")

    So no amount of AI_SETUP redirection reaches it: agent_cli.py lives in the real repo, so
    spills land in the real repo. My own T070 acceptance run left
    state/spill/actual_outcome-20260725-125317-*.txt in canonical WHILE the store stayed
    clean at 434 -> 434. I verified the store and missed the side channel, and reported the
    hazard retired on that basis.

    The lesson generalises past this one path: isolation that redirects a ROOT does not cover
    a sibling that derives its own root from __file__. Every such derivation is a hole.
    """
    spill = os.environ.get("AKASHIC_SPILL_DIR")
    assert spill, "AKASHIC_SPILL_DIR is unset -- spills fall back to the LIVE repo"
    assert Path(spill).resolve() != (ROOT / "state" / "spill").resolve(), (
        f"spill dir resolves to canonical {spill}"
    )


def test_an_explicit_opt_out_exists_and_is_documented():
    """Deny-by-default needs a legible escape hatch, or someone edits conftest instead."""
    conftest = (ROOT / "tests" / "conftest.py").read_text(encoding="utf-8")
    assert "AKASHIC_TEST_USE_CANONICAL" in conftest, (
        "no documented way to run against real backends deliberately"
    )
