"""
P3 / T023 -- runner-side ledger fold: latest-per-task, drained once, never answered.

Bar: ledger_update/resolved markers coalesce to one line per task (a lifecycle burst never
evicts unrelated context -- the fold spec's ring-budget caveat, solved outside the ring);
the drained block appears once and clears; the intercept path never reaches the responder.

Run: py -m pytest tests/test_runner_ledger_fold.py -q
"""
import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import scripts.bifrost_runner_deepseek as runner


def _msg(kind, content, task=None):
    return SimpleNamespace(kind=kind, content=content, frm="conductor", to="*",
                           meta={"task": task} if task else {})


def setup_function(_fn):
    runner.LEDGER_FOLDS.clear()


def test_burst_coalesces_to_latest_per_task():
    for frm, to in (("new", "proposed"), ("proposed", "approved"),
                    ("approved", "claimed"), ("claimed", "in_progress")):
        runner.fold_ledger_update(_msg("ledger_update", f"LEDGER T042 {frm}->{to}: drill", "T042"))
    runner.fold_ledger_update(_msg("ledger_update", "LEDGER T043 new->proposed: other", "T043"))
    assert len(runner.LEDGER_FOLDS) == 2, "one slot per task, not four for the burst"
    assert "claimed->in_progress" in runner.LEDGER_FOLDS["T042"], "latest transition wins"


def test_drain_renders_once_then_clears():
    runner.fold_ledger_update(_msg("ledger_update", "LEDGER T042 verifying->done: drill", "T042"))
    block = runner.drain_ledger_folds()
    assert "## LEDGER UPDATES" in block and "verifying->done" in block
    assert runner.drain_ledger_folds() == "", "steering context appears exactly once"


def test_resolved_markers_fold_too():
    ok = runner.fold_ledger_update(_msg("resolved", "RESOLVED T042: drill @abc -- CLOSED", "T042"))
    assert ok and "RESOLVED T042" in runner.LEDGER_FOLDS["T042"]


def test_process_one_intercepts_without_answering():
    calls = []
    bus = SimpleNamespace(send=lambda *a, **k: calls.append(("send", a)),
                          broadcast=lambda *a, **k: calls.append(("broadcast", a)))
    args = SimpleNamespace(agent="deepseek", agentic=True, model="m")
    rate = SimpleNamespace(allow=lambda: (_ for _ in ()).throw(AssertionError("rate touched")))
    responder = lambda *a, **k: (_ for _ in ()).throw(AssertionError("responder touched"))
    runner._process_one(_msg("ledger_update", "LEDGER T042 new->proposed: drill", "T042"),
                        bus, args, responder, rate)
    assert runner.LEDGER_FOLDS.get("T042"), "folded"
    assert calls == [], "no reply, no broadcast -- fold is detect-only"
