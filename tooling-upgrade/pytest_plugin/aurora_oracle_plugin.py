"""pytest plugin loaded by tooling-upgrade/oracle.py (`-p aurora_oracle_plugin`) for O1.

Records every test's per-phase outcome by node id, and every collection error, to the JSON file
named by $AURORA_ORACLE_OUT. Observation only: it changes no outcome.
"""
import json
import os

_results = {}
_collect_errors = []


def pytest_runtest_logreport(report):
    rec = _results.setdefault(report.nodeid, {})
    outcome = report.outcome
    if hasattr(report, "wasxfail"):
        outcome = "xfailed" if report.skipped else "xpassed"
    rec[report.when] = outcome


def pytest_collectreport(report):
    if report.failed:
        _collect_errors.append(report.nodeid)


def pytest_sessionfinish(session, exitstatus):
    out = os.environ.get("AURORA_ORACLE_OUT")
    if not out:
        return
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"results": _results, "collect_errors": sorted(set(_collect_errors)),
                   "exitstatus": int(exitstatus)}, fh)
