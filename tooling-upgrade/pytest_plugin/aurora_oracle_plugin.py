# pyright: strict
"""pytest plugin loaded by tooling-upgrade/oracle.py (`-p aurora_oracle_plugin`) for O1.

Records every test's per-phase outcome by node id, and every collection error, to the JSON file
named by $AURORA_ORACLE_OUT. Observation only: it changes no outcome.
"""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

_results: dict[str, dict[str, str]] = {}
_collect_errors: list[str] = []


def pytest_runtest_logreport(report: pytest.TestReport) -> None:
    rec = _results.setdefault(report.nodeid, {})
    outcome = report.outcome
    if hasattr(report, "wasxfail"):
        outcome = "xfailed" if report.skipped else "xpassed"
    rec[report.when] = outcome


def pytest_collectreport(report: pytest.CollectReport) -> None:
    if report.failed:
        _collect_errors.append(report.nodeid)


def pytest_sessionfinish(session: pytest.Session, exitstatus: int | pytest.ExitCode) -> None:
    out = os.environ.get("AURORA_ORACLE_OUT")
    if not out or hasattr(session.config, "workerinput"):
        # an xdist worker holds only its own share; the controller receives every worker's
        # reports through the same hooks and writes the one complete record
        return
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(
            {"results": _results, "collect_errors": sorted(set(_collect_errors)), "exitstatus": int(exitstatus)}, fh
        )
