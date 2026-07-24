"""The comprehensibility guard is the project's immune system -- so it must itself be TESTED (property
P3 "trustworthy": an untested guard that silently breaks is false-green, the exact cascade this system
exists to prevent). These tests: (1) prove the guard is GREEN on the real repo for the right reason,
(2) INJECT each drift class and prove the guard FAILs, (3) prove the false-positive controls (root-
anchoring, dated exemptions) hold, (4) prove a CRASHING check fails LOUD, never silent-passes.

Design: docs/library/design/20260701_the-comprehensibility-immune-system-desi_339b01.md.
"""
import os
import sys

import pytest

_TESTS = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(_TESTS))
sys.path.insert(0, os.path.join(os.path.dirname(_TESTS), "scripts"))

import check_comprehensibility as cm


# --- green baseline: the guard passes on the real repo (trustworthy = green for the RIGHT reason) ----

def test_guard_is_green_on_the_real_repo(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["check_comprehensibility.py"])
    assert cm.main() == 0


def test_fast_mode_is_green_and_runs_only_FG(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["check_comprehensibility.py", "--fast"])
    assert cm.main() == 0


def test_stale_refs_and_case_are_clean_now():
    assert cm._stale_refs() == []
    assert cm._filename_case() == []


# --- B2: the derived maps (PHYSICS.md, MAP.md) join the immune system (drift-injected FAIL) ---------

def test_derived_docs_current_is_green_now():
    assert cm._derived_docs_current() == []          # both generators match their on-disk output


def test_derived_docs_drift_is_flagged(monkeypatch):
    # Inject staleness the way it really happens: the on-disk read returns yesterday's content
    # while the generator renders today's. The guard must FAIL and name the regenerate command.
    real = cm._read

    def fake_read(rel):
        if rel == "docs/PHYSICS.md":
            return "# PHYSICS -- stale hand-edited copy\n(drifted)\n"
        return real(rel)

    monkeypatch.setattr(cm, "_read", fake_read)
    out = cm._derived_docs_current()
    assert any("PHYSICS.md is stale" in m for m in out)
    assert all("MAP.md is stale" not in m for m in out)   # MAP untouched -> not falsely flagged


# --- F: stale-ref scanner -- root-anchoring is the false-positive firewall --------------------------

def test_scan_refs_extracts_root_anchored_paths():
    refs = cm.scan_refs("see `tests/foo.py` and core/bar/baz.py plus docs/FAQ.md")
    assert "tests/foo.py" in refs and "core/bar/baz.py" in refs and "docs/FAQ.md" in refs


def test_scan_refs_ignores_deployment_and_midpath_prefixes():
    # the DEPLOY.md false-positive class: `scripts/...` inside `aurora/scripts/...` must NOT be a ref
    assert cm.scan_refs("deploy to aurora/scripts/hooks/claude_pretooluse.py") == []
    assert cm.scan_refs("vendored at thirdparty/core/utils.py") == []   # mid-path core/ not anchored


def test_scan_refs_dedupes_case_insensitively():
    assert cm.scan_refs("core/x.py core/X.PY core/x.py") == ["core/x.py"]


def test_stale_ref_is_flagged_but_a_real_path_is_not(tmp_path):
    # a doc citing a nonexistent repo path is caught; a real one is not
    fake = "refs core/foundation/store.py (real) and core/foundation/GONE_totally.py (deleted)"
    refs = cm.scan_refs(fake)
    assert "core/foundation/store.py" in refs and "core/foundation/GONE_totally.py" in refs
    assert os.path.exists(os.path.join(cm.ROOT, "core/foundation/store.py"))
    assert not os.path.exists(os.path.join(cm.ROOT, "core/foundation/GONE_totally.py"))


# --- NON-EVADABLE: exemptions are dated; an expired one is itself a failure -------------------------

def test_exemption_active_respects_expiry():
    ref = "some/gone.py"
    monkeypatch_al = {ref: {"expires": "2999-01-01", "reason": "future"}}
    orig = dict(cm.REF_ALLOWLIST)
    cm.REF_ALLOWLIST.clear(); cm.REF_ALLOWLIST.update(monkeypatch_al)
    try:
        assert cm.exemption_active(ref, "2026-07-07") is True          # unexpired -> active
        assert cm.exemption_active(ref, "3000-01-01") is False         # past expiry -> not active
        assert cm.exemption_active("other/x.py", "2026-07-07") is False
    finally:
        cm.REF_ALLOWLIST.clear(); cm.REF_ALLOWLIST.update(orig)


def test_expired_exemption_is_itself_a_fail(monkeypatch):
    monkeypatch.setattr(cm, "REF_ALLOWLIST",
                        {"nowhere/x.py": {"expires": "2000-01-01", "reason": "long expired"}})
    fails = cm._stale_refs()
    assert any("EXPIRED" in f and "nowhere/x.py" in f for f in fails), fails


# --- G: filename case-drift (the lexicon.md vs LEXICON.md class) ------------------------------------

def test_case_mismatches_detects_wrong_case_and_passes_clean():
    # git tracks docs/LEXICON.md but disk has lexicon.md -> a mismatch
    bad = cm.case_mismatches(["docs/LEXICON.md"], lambda d: {"lexicon.md", "OTHER.md"})
    assert bad == [("docs/LEXICON.md", "docs/lexicon.md")]
    # exact-case present -> clean
    assert cm.case_mismatches(["docs/LEXICON.md"], lambda d: {"LEXICON.md"}) == []
    # tracked-but-missing-on-disk -> reported with actual=None
    assert cm.case_mismatches(["core/x.py"], lambda d: set()) == [("core/x.py", None)]


# --- crash-loud: a broken check FAILs, never silently passes (the false-confidence guard) -----------

def test_run_wrapper_turns_a_crash_into_a_loud_fail():
    def boom():
        raise ValueError("simulated broken check")
    got, crash = cm._run("boomcheck", boom)
    assert got == [] and crash is not None and "CRASHED" in crash and "boomcheck" in crash


def test_main_fails_loud_when_a_check_crashes(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["check_comprehensibility.py"])
    monkeypatch.setattr(cm, "_stale_refs", lambda: (_ for _ in ()).throw(RuntimeError("guard bug")))
    assert cm.main() == 1, "a crashing check must make the guard FAIL, not pass green"
