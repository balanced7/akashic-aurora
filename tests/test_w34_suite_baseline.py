"""W34 pins — the suite-baseline receipt (B4; the next seat diffs instead of re-classifying).

Consensus: claude opening + kimi counter (KEEP + amendments). Kimi's blocking (a): delta
by TEST NODE ID, never by count — "12 failures -> 12 failures" must expose 3-fixed+3-new
churn. (b): classification decays — a failure labeled "sibling lane T067" means something
only while T067 is open; boot flags closed-since-snapshot lanes. (c): atomic write +
provenance (sha, seat, age). Q3 consensus: NOBODY runs the suite at wrap; seats produce
receipts when they run suites anyway, the baseline snapshots the freshest.

  P1  ingest_pytest parses FAILED node ids from real pytest output
  P2  record/read round-trip: atomic file, provenance (sha/seat/at), claims snapshot
  P3  delta by node id: new / fixed / inherited (count-identical churn exposed)
  P4  auto-classification: a failing node whose file rides an active task's files
      list gets that lane; unmatched stays unclassified
  P5  decay: a snapshot-classified lane now CLOSED renders the re-run advisory
  P6  no baseline -> boot line is "" (fail-open, never a [GAP] shout)
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.coord import suite_baseline as sb


PYTEST_TAIL = """
=========================== short test summary info ===========================
FAILED tests/test_agent_interface.py::test_messy_input_is_sanitized - Asserti...
FAILED tests/test_t067_1_toolbox_parity.py::test_d1_toolbox_enumerated_and_reality_passes
FAILED tests/test_t067_1_toolbox_parity.py::test_d4_report_includes_toolbox
FAILED tests/test_t068_r3_preflight.py::test_p9_double_fail_sends_anyway_loud
============================== 4 failed, 900 passed in 60.00s ==================
"""


@pytest.fixture()
def qfile(tmp_path, monkeypatch):
    p = str(tmp_path / "suite_baseline.json")
    monkeypatch.setattr(sb, "BASELINE_PATH", p)
    return p


def test_p1_ingest_parses_node_ids():
    nodes = sb.ingest_pytest(PYTEST_TAIL)
    assert len(nodes) == 4
    assert "tests/test_t067_1_toolbox_parity.py::test_d1_toolbox_enumerated_and_reality_passes" in nodes
    assert all("::" in n for n in nodes)


def test_p2_record_read_roundtrip(qfile, monkeypatch):
    monkeypatch.setattr(sb, "_ledger_claims", lambda: {"T067": "verifying"})
    rec = sb.record(sb.ingest_pytest(PYTEST_TAIL), seat="claude", sha="abc1234")
    assert rec["sha"] == "abc1234" and rec["seat"] == "claude" and rec["at"]
    stored = json.load(open(qfile, encoding="utf-8"))
    assert len(stored["failures"]) == 4
    assert stored["claims_at_snapshot"] == {"T067": "verifying"}


def test_p3_delta_by_node_id(qfile, monkeypatch):
    monkeypatch.setattr(sb, "_ledger_claims", lambda: {})
    sb.record(["tests/a.py::t1", "tests/a.py::t2", "tests/b.py::t3"],
              seat="s", sha="x")
    d = sb.delta(["tests/a.py::t1", "tests/b.py::t9", "tests/c.py::t4"])
    assert d["inherited"] == ["tests/a.py::t1"]
    assert sorted(d["new"]) == ["tests/b.py::t9", "tests/c.py::t4"]
    assert sorted(d["fixed"]) == ["tests/a.py::t2", "tests/b.py::t3"]
    # kimi (a): same COUNT, different content -- the churn is visible
    assert len(d["new"]) + len(d["inherited"]) == 3 == 3


def test_p4_auto_classification(qfile, monkeypatch):
    monkeypatch.setattr(sb, "_task_files", lambda: {
        "T067": ["tests/test_t067_1_toolbox_parity.py", "core/comm/toolbox.py"],
        "T068": ["tests/test_t068_r3_preflight.py"]})
    lanes = sb.classify(sb.ingest_pytest(PYTEST_TAIL))
    assert lanes["tests/test_t067_1_toolbox_parity.py::test_d1_toolbox_enumerated_and_reality_passes"] == "T067"
    assert lanes["tests/test_t068_r3_preflight.py::test_p9_double_fail_sends_anyway_loud"] == "T068"
    assert lanes["tests/test_agent_interface.py::test_messy_input_is_sanitized"] == ""


def test_p5_decay_advisory(qfile, monkeypatch):
    monkeypatch.setattr(sb, "_ledger_claims", lambda: {"T067": "verifying"})
    monkeypatch.setattr(sb, "_task_files",
                        lambda: {"T067": ["tests/test_t067_1_toolbox_parity.py"]})
    sb.record(sb.ingest_pytest(PYTEST_TAIL), seat="claude", sha="abc")
    # the lane closes after the snapshot
    monkeypatch.setattr(sb, "_ledger_claims", lambda: {"T067": "done"})
    line = sb.render_boot_line()
    assert "4 known failure(s)" in line and "abc" in line
    assert "since closed" in line and "re-run advised" in line


def test_p6_no_baseline_silent(qfile):
    assert sb.render_boot_line() == ""
    assert sb.read() is None
