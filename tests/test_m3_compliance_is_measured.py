"""PRE-REGISTERED ACCEPTANCE -- the scorecard must report MEASURED M3 compliance, not self-report.

THE RECEIPT (2026-07-27). check_preregistration.py has shipped an `--audit N` mode since T031
and had NEVER BEEN RUN. First run, over the last 40 commits:

    M3 pre-registration compliance: 8/24 test-adding commits clean (33%)

Sixteen of twenty-four test-adding commits landed their pins IN THE SAME COMMIT as the
implementation, so git holds no evidence the acceptance came first. My own commits from that
night are among them -- including ones where I demonstrably wrote the pin, ran it RED, watched
it fail, and only then built. The practice happened; the RECEIPT did not. The project's own
doctrine: "a practice without a measurable signal is an aspiration, not a baseline."

Meanwhile arc_scorecard.py (T031 hook 3, the wrap-time reader) renders M3 as
"{prereg} registration-marked ship(s)" -- a count of commits whose MESSAGE mentions
registration. That is self-report. It counts what we SAID, never what we DID, and it would have
rendered a healthy-looking number through the entire 33% window. Compliance measured by
announcement is the WHO-checklist failure in one line of output.

  P1  the audit is a PURE FUNCTION returning numbers -- not a printed line to be re-parsed
      (a gate that scrapes rendered text is fragile; delimiters collide with content)
  P2  a clean history reads 100%
  P3  a test+source commit is counted as a violation
  P4  the scorecard renders the MEASURED rate, not the self-reported count

Run: py -m pytest tests/test_m3_compliance_is_measured.py -q
"""
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _repo(tmp_path, commits):
    """A throwaway git repo. `commits` = [(message, {path: content}), ...]."""
    d = tmp_path / "r"
    d.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.email", "t@t"], cwd=d, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=d, check=True)
    for msg, files in commits:
        for rel, body in files.items():
            p = d / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(body, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=d, check=True)
        subprocess.run(["git", "commit", "-q", "-m", msg], cwd=d, check=True)
    return d


def test_p1_audit_returns_numbers_not_a_printed_line(tmp_path):
    """A caller must be able to ASK for the rate. Re-parsing stdout is the fragile path."""
    from scripts.checkers import check_preregistration as cp
    assert hasattr(cp, "audit_stats"), (
        "no pure audit_stats(n, root) -- the scorecard would have to scrape the printed "
        "compliance line, and rendered text is not an API")
    r = cp.audit_stats(5, root=str(_repo(tmp_path, [("init", {"README.md": "x"})])))
    assert set(r) >= {"total", "clean", "violations", "pct"}


def test_p1b_checker_uses_the_canonical_core_measurement():
    """The ship gate and boot reader must not carry forked metric implementations."""
    from core.coord import preregistration as canonical
    from scripts.checkers import check_preregistration as checker

    assert checker.audit_stats is canonical.audit_stats


def test_p1c_audit_reads_one_git_snapshot(monkeypatch):
    """Boot cost must not grow by spawning one ``git show`` for every candidate commit."""
    from core.coord import preregistration as prereg

    calls = []

    class Result:
        stdout = ""

    def fake_run(args, **kwargs):
        calls.append(args)
        result = Result()
        if "--name-status" in args:
            result.stdout = ("\x01abc123\tpins and impl\n\n"
                             "A\ttests/test_thing.py\nM\tcore/thing.py\n")
        elif args[:2] == ["git", "log"]:
            result.stdout = "\x01abc123 pins and impl\n\ntests/test_thing.py\n"
        else:
            result.stdout = "tests/test_thing.py\ncore/thing.py\n"
        return result

    monkeypatch.setattr(prereg.subprocess, "run", fake_run)
    measured = prereg.audit_stats(30, root="unused")

    assert measured["total"] == 1 and measured["violations"] == 1
    assert len(calls) == 1, "audit_stats spawned an N+1 git show loop"
    assert "--name-status" in calls[0]
    assert "--diff-filter=A*" in calls[0]


def test_p2_a_clean_history_reads_100(tmp_path):
    from scripts.checkers import check_preregistration as cp
    d = _repo(tmp_path, [
        ("seed", {"README.md": "x"}),
        ("pins first, RED", {"tests/test_thing.py": "def test_x():\n    assert True\n"}),
        ("impl", {"core/thing.py": "x = 1\n"}),
    ])
    r = cp.audit_stats(10, root=str(d))
    assert r["total"] == 1 and r["clean"] == 1 and r["pct"] == 100.0


def test_p3_a_test_plus_source_commit_is_a_violation(tmp_path):
    from scripts.checkers import check_preregistration as cp
    d = _repo(tmp_path, [
        ("seed", {"README.md": "x"}),
        ("pins and impl together", {"tests/test_thing.py": "def test_x():\n    assert True\n",
                                    "core/thing.py": "x = 1\n"}),
    ])
    r = cp.audit_stats(10, root=str(d))
    assert r["total"] == 1 and r["violations"] == 1 and r["pct"] == 0.0


def test_p4_the_scorecard_reports_the_measured_rate(tmp_path, capsys):
    """The whole point. The wrap reader must show the MEASURED compliance, so a 33% window
    can never render as a healthy-looking count of commits that merely claimed the practice."""
    import importlib
    sc = importlib.import_module("scripts.arc_scorecard")
    src = open(os.path.join(ROOT, "scripts", "arc_scorecard.py"), encoding="utf-8").read()
    assert "audit_stats" in src, (
        "the scorecard still renders M3 from self-report (commits whose MESSAGE mentions "
        "registration) instead of the measured audit -- it counts what we said, not what we did")
