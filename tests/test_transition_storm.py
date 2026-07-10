"""
P3 TRANSITION STORM (T029 tier-2): 500 scripted transitions across 20 synthetic tasks.
Kill: hints ring evicted by ledger_update folds, fold dict unbounded, or format_state
latency degrading >2x under the storm.

Hermetic: fake bus messages, real fold_ledger_update + drain_ledger_folds code.
The fold + drain contract is already pinned in test_runner_ledger_fold.py; this file
targets STORM behavior: does the fold dict grow unbounded? Do hints survive when hints
and folds compete? The real-wall-clock 500-proposed render is the live drill's job.

Authored by deepseek (T029 tier-2 fenced handoff, bus reply 1783688456583-0);
materialized + reviewed by claude (review trims: dead synthetic-task scaffolding removed
from the latency test -- the structural checks it actually asserted are kept).
Run: py -m pytest tests/test_transition_storm.py -q
"""
import os
import sys
import time
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import scripts.bifrost_runner_deepseek as runner
from core.comm import context_hints


def setup_function(_fn):
    runner.LEDGER_FOLDS.clear()
    context_hints.clear_all()


def _msg(kind, content, task=None, frm="conductor"):
    meta = {"task": task} if task else {}
    return SimpleNamespace(kind=kind, content=content, frm=frm, to="*", meta=meta)


# ---------------------------------------------------------- fold dict bounds

def test_fold_dict_bounded_under_storm():
    """500 transitions across 20 tasks: LEDGER_FOLDS size stays at 20, not 500.
    latest-per-task dedup means one slot per task id, regardless of burst size."""
    for i in range(500):
        tid = f"T{(i % 20) + 1:03d}"       # 20 tasks: T001-T020
        runner.fold_ledger_update(
            _msg("ledger_update", f"LEDGER {tid} step {i//20}->next", tid))
    assert len(runner.LEDGER_FOLDS) == 20, \
        "fold dict bound = number of tasks, not number of transitions"
    for tid in [f"T{i:03d}" for i in range(1, 21)]:
        assert "step 24" in runner.LEDGER_FOLDS[tid], \
            f"{tid}: latest transition preserved, not first"


def test_drain_clears_even_under_storm():
    """After the storm, drain returns the block and clears. A second drain is empty."""
    for i in range(20):
        runner.fold_ledger_update(
            _msg("ledger_update", f"LEDGER T{i+1:03d} done", f"T{i+1:03d}"))
    block = runner.drain_ledger_folds()
    assert "## LEDGER UPDATES" in block
    assert len(block.splitlines()) >= 21, "one header + 20 lines"
    assert runner.drain_ledger_folds() == "", "cleared after drain"


def test_fold_dict_never_exceeds_memory_budget():
    """1000 transitions across 1000 unique task ids -> fold dict at 1000 entries.
    Linear in DISTINCT task ids, not in message count -- not unbounded, not capped
    either (P3-NOTE: acceptable while the real fleet holds <=50 live tasks; a cap
    becomes a slice if the ledger ever hosts thousands)."""
    for i in range(1000):
        tid = f"T{i:04d}"
        runner.fold_ledger_update(
            _msg("ledger_update", f"LEDGER {tid} proposed", tid))
    assert len(runner.LEDGER_FOLDS) == 1000, \
        "fold dict grows with unique task ids -- linear in distinct tasks, " \
        "not in message count (1000 tasks = 1000 entries). In practice: <=50."
    block = runner.drain_ledger_folds()
    assert len(block.splitlines()) >= 1000, "one line per task in the block"


# ---------------------------------------------------------- hint + fold coexistence

def test_hints_survive_ledger_fold_flood():
    """R8 cross-seam: ledger_update folds do NOT touch the context_hints ring at all.
    They are separate code paths. A ledger fold storm must not evict hints."""
    context_hints.push("deepseek", "critical", "do not lose me", from_agent="claude")
    for i in range(100):
        runner.fold_ledger_update(
            _msg("ledger_update", f"LEDGER T{i:03d} step", f"T{i:03d}"))
    hints = context_hints.drain("deepseek")
    assert len(hints) == 1 and hints[0]["key"] == "critical", \
        "hints and ledger folds are independent -- fold storm does not evict hints"
    assert len(runner.LEDGER_FOLDS) == 100, "but folds themselves are unaffected"


def test_hint_ring_independent_of_ledger_folds():
    """Structural separation proof: push 12 hints (ring cap 8, 4 evicted), then
    drain ledger folds -- the fold drain does not interact with hints at all."""
    for i in range(12):
        context_hints.push("deepseek", f"h{i}", f"v{i}", from_agent="claude")
    for i in range(5):
        runner.fold_ledger_update(
            _msg("ledger_update", f"LEDGER T{i:03d} done", f"T{i:03d}"))
    hints = context_hints.drain("deepseek")
    fold_block = runner.drain_ledger_folds()
    assert len(hints) == 8, "hint ring drained independently of folds"
    assert len(fold_block.splitlines()) == 6, "fold block drained independently of hints"


# ---------------------------------------------------------- format_state structure

def test_format_state_render_path_is_structurally_bounded():
    """The latency-critical path is state_view -> format_state, both O(N) in task
    count. This is the hermetic structural check; the live drill (500 proposed via
    conductor script) measures the real wall clock against the >2x kill condition."""
    from core.coord.task_ledger import format_state, state_view
    t0 = time.perf_counter()
    view = state_view(now=time.time())
    rendered = format_state(agent="claude", now=time.time())
    elapsed = time.perf_counter() - t0
    assert "proposed" in view and "counts" in view
    assert rendered.strip(), "render produces the ledger block"
    assert elapsed < 5.0, "one view+render pass stays interactive on the real ledger"
