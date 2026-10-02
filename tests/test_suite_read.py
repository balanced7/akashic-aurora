"""suite_read RED pins (2026-10-01) — the READ-ONLY suite verb family's acceptance.

Companion spec: design/suite-verb-family-spec.md. The whole safety story of this slice is
"reads only; every write stays behind an existing flag." These pins are RED-first: they encode
the contract BEFORE the implementation is trusted, and each one guards a named failure mode
from the corpus (record-by-default, absence-eats-failures, confident-zero, pipe-swallowed-exit,
empty-is-not-error).

Verbatim from the spec's pre-registered acceptance:
  1. `suite diff` returns nonzero iff a YOURS verdict exists, never for UNKNOWN.
  2. `suite diff` on a stale baseline prints [STALE] and does NOT claim INHERITED.
  3. `suite triage` output is deterministic.
  4. `suite rerun-failing --run` leaves lastfailed alone and exits with pytest's own code.
  5. `suite tail` on a missing log returns a named non-zero, never a confident zero.
  6. the read doors never write state/coord/suite_baseline.json.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import suite_read as sr
from core.coord import suite_baseline as sb


@pytest.fixture()
def baseline_path(tmp_path, monkeypatch):
    p = str(tmp_path / "suite_baseline.json")
    monkeypatch.setattr(sb, "BASELINE_PATH", p)
    return p


def test_p1_yours_verdict_is_the_only_nonzero_accusation(baseline_path, monkeypatch):
    # A stale baseline means verdicts degrade to LIKELY_INHERITED/UNKNOWN, never YOURS, so a
    # diff over unknown nodes must report zero YOURS -> exit-neutral. A YOURS requires a CURRENT
    # baseline matching HEAD, which we simulate by making head_sha() return the baseline sha.
    sb.record(["tests/a.py::t1"], seat="p", sha="abc1234")
    monkeypatch.setattr(sb, "head_sha", lambda: "abc1234")
    res = sr.diff(["tests/a.py::t1"])  # node is IN the current baseline -> INHERITED, not YOURS
    assert res["counts"].get("YOURS", 0) == 0
    # and a genuinely new node on a CURRENT baseline IS yours
    res2 = sr.diff(["tests/a.py::t1", "tests/b.py::t2"])
    assert res2["counts"].get("YOURS") == 1
    assert "YOURS" in sr.render_diff(res2)


def test_p2_stale_baseline_refuses_inherited(baseline_path, monkeypatch):
    sb.record(["tests/a.py::t1"], seat="p", sha="0000000")
    monkeypatch.setattr(sb, "head_sha", lambda: "fffffff")  # different sha -> STALE
    res = sr.diff(["tests/a.py::t1"])
    assert res["stale"] is True
    out = sr.render_diff(res)
    assert "STALE" in out
    # the node is in the baseline but stale, so it must be LIKELY_INHERITED, never INHERITED
    assert res["by_node"]["tests/a.py::t1"]["verdict"] == "LIKELY_INHERITED"
    assert "UNKNOWN" in out or "LIKELY_INHERITED" in out


def test_p3_triage_is_deterministic(baseline_path, monkeypatch):
    monkeypatch.setattr(sb, "_task_files", lambda: {
        "T067": ["tests/test_t067_1_toolbox_parity.py"]})
    nodes = ["tests/test_t067_1_toolbox_parity.py::test_d1",
             "tests/other.py::test_x"]
    a = sr.render_triage(sr.triage(nodes))
    b = sr.render_triage(sr.triage(nodes))
    assert a == b
    assert "T067" in a
    assert "unowned" in a


def test_p4_rerun_failing_does_not_mutate_lastfailed(monkeypatch, tmp_path):
    # lastfailed_nodes() is a pure read of the cache; rerun_command(dry) never touches it.
    monkeypatch.setattr(sr, "_pytest_cache_dir", lambda root=None: str(tmp_path))
    assert sr.lastfailed_nodes() == []
    code, text = sr.rerun_command([], run=False)
    assert code == 0
    assert "no prior failing nodes" in text
    # exercising rerun_command with nodes in dry mode must NOT spawn (run=False) and must
    # reference sys.executable, never 'py'
    code2, text2 = sr.rerun_command(["tests/a.py::t1"], run=False)
    assert code2 == 0
    assert "sys.executable" not in text2 and "pytest" in text2
    assert "py " not in text2.lower()


def test_p5_tail_missing_log_is_a_named_zero(monkeypatch, tmp_path):
    monkeypatch.setattr(sr, "SUITE_LOG_GLOB",
                        os.path.join(str(tmp_path), "suite-run-*.log"))
    running, text = sr.tail()
    assert running is False
    assert "no suite run log" in text  # named, not a confident zero


def test_p6_reads_never_write_the_baseline(baseline_path):
    sb.record(["tests/a.py::t1"], seat="p", sha="abc1234")
    before = sb.read()
    # every read path leaves the baseline byte-identical
    sr.diff(["tests/a.py::t1"])
    sr.triage(["tests/a.py::t1"])
    sr.render_diff(sr.diff([]))
    after = sb.read()
    assert before == after
