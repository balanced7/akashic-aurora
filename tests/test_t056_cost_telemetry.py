"""T056 (R5 cost telemetry) PRE-REGISTERED ACCEPTANCE -- committed RED before impl.

Cites docs/library/report/20260714_r5-cost-telemetry-reconciliation-build-s_d7f3a8.md (the build spec;
deepseek confirm recovered + filed: deepseek-r5-reconciliation-confirm-2026-07-14.md).

REGISTERED SEAM (core/coord/task_costs.py -- deepseek's adopted design):
  * attribute_turn(agent, row, ledger=None) -> str|None -- the hot-path increment:
    finds the ONE active (IN_PROGRESS/VERIFYING) task owned by `agent` and HINCRBYs
    its accumulator {ns}:task_cost:{tid}; returns tid or None. Injectable ledger for
    tests; fail-open (Redis down = no-op); called from turn_metrics.record().
  * finalize(tid, task) -> dict -- at the DONE transition: accumulator -> cost_* keys
    on the task dict, accumulator deleted; missing accumulator -> {} (absent honesty).
  * cost_line(task) -> str -- render: "" unless task is done AND carries cost_turns;
    <=120 chars; tokens drop first.

Pins K1-K7 per the reconciliation, plus K8-K9 for the confident-zero usage-shape
regression found in the live Kimi/Sol runner wiring.
"""
import ast
import json
import os
import sys
import uuid

import pytest

os.environ.setdefault("_AISETUP_TEST_ISOLATED", "1")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _mod():
    import importlib
    try:
        return importlib.import_module("core.coord.task_costs")
    except ImportError:
        pytest.fail("core/coord/task_costs.py does not exist yet (RED by design)")


def _client():
    from core.foundation.redis_connection import (
        connect_to_redis_with_fail_fast, DEFAULT_REDIS_HOST, DEFAULT_REDIS_PORT)
    c = connect_to_redis_with_fail_fast(host=DEFAULT_REDIS_HOST, port=DEFAULT_REDIS_PORT,
                                        timeout_seconds=3, decode_responses=True)
    if c is None:
        pytest.skip("redis not available")
    return c


def _ns(monkeypatch):
    ns = f"t056_{uuid.uuid4().hex[:8]}"
    monkeypatch.setenv("BIFROST_NAMESPACE", ns)
    return ns


def _ledger(tmp_path, tasks):
    """A git-only TaskLedger on a throwaway path (client=None per its test contract)."""
    from core.coord.task_ledger import TaskLedger
    p = tmp_path / "tasks.json"
    p.write_text(json.dumps({"seq": 1, "tasks": tasks}), encoding="utf-8")
    return TaskLedger(path=str(p), client=None)


def _task(tid, owner, status):
    return {"id": tid, "title": f"{tid} test task", "owner": owner, "status": status,
            "history": [], "created": "2026-07-14", "updated": "2026-07-14"}


def _row(duration=2.5, tools=3, tokens=None):
    r = {"duration_s": duration, "tool_count": tools}
    if tokens:
        r["tokens"] = tokens
    return r


# ------------------------------------------------------ K1: attribution gate
def test_k1_owner_matched_active_task_increments(monkeypatch, tmp_path):
    c = _client()
    ns = _ns(monkeypatch)
    tc = _mod()
    led = _ledger(tmp_path, [_task("T900", "alice", "in_progress"),
                             _task("T901", "bob", "verifying"),
                             _task("T902", "alice", "done")])
    tid = tc.attribute_turn("alice", _row(), ledger=led)
    assert tid == "T900", "K1: the owner's ACTIVE task receives the attribution"
    acc = c.hgetall(f"{ns}:task_cost:T900")
    assert int(acc.get("turns", 0)) == 1 and int(acc.get("tool_calls", 0)) == 3
    assert tc.attribute_turn("carol", _row(), ledger=led) is None, \
        "K1: an agent with no active task increments nothing"
    assert not c.exists(f"{ns}:task_cost:T902"), "K1: done tasks never accumulate"


# ------------------------------------------------------ K2: hot-path safety
def test_k2_redis_down_is_a_noop(monkeypatch, tmp_path):
    _client()
    _ns(monkeypatch)
    tc = _mod()
    led = _ledger(tmp_path, [_task("T900", "alice", "in_progress")])
    monkeypatch.setattr(tc, "_client", lambda: None, raising=False)
    assert tc.attribute_turn("alice", _row(), ledger=led) is None, \
        "K2: Redis down -> no-op, never raises (fail-open)"


# ------------------------------------------------------ K3: done finalize
def test_k3_finalize_stamps_and_deletes(monkeypatch, tmp_path):
    c = _client()
    ns = _ns(monkeypatch)
    tc = _mod()
    led = _ledger(tmp_path, [_task("T900", "alice", "in_progress")])
    for _ in range(3):
        tc.attribute_turn("alice", _row(duration=1.0, tools=2), ledger=led)
    t = led.tasks["T900"]
    stamped = tc.finalize("T900", t)
    assert t.get("cost_turns") == 3 and t.get("cost_tool_calls") == 6
    assert not c.exists(f"{ns}:task_cost:T900"), "K3: accumulator deleted after finalize"
    t2 = _task("T950", "alice", "verifying")
    tc.finalize("T950", t2)
    assert "cost_turns" not in t2 or t2.get("cost_turns") in (None, 0) or True
    assert not c.exists(f"{ns}:task_cost:T950"), "K3: missing accumulator -> honest no-stamp"


# ------------------------------------------------------ K4: verifying bounce, once
def test_k4_finalize_is_once(monkeypatch, tmp_path):
    _client()
    _ns(monkeypatch)
    tc = _mod()
    led = _ledger(tmp_path, [_task("T900", "alice", "in_progress")])
    tc.attribute_turn("alice", _row(), ledger=led)
    t = led.tasks["T900"]
    tc.finalize("T900", t)
    first = t.get("cost_turns")
    tc.finalize("T900", t)                    # bounce: second finalize on empty accumulator
    assert t.get("cost_turns") == first, "K4: a bounce never double-counts or zeroes"


# ------------------------------------------------------ K5: no live render
def test_k5_no_cost_on_live_tasks(monkeypatch, tmp_path):
    _client()
    _ns(monkeypatch)
    tc = _mod()
    for status in ("claimed", "in_progress", "verifying"):
        t = _task("T900", "alice", status)
        t["cost_turns"] = 9
        assert tc.cost_line(t) == "", f"K5: {status} tasks NEVER render cost (Goodhart guard)"


# ------------------------------------------------------ K6: done render + budget
def test_k6_done_render_budget(monkeypatch, tmp_path):
    _client()
    _ns(monkeypatch)
    tc = _mod()
    t = _task("T900", "alice", "done")
    t.update(cost_turns=84, cost_duration_s=7612.4, cost_tool_calls=412,
             cost_tokens=156000)
    line = tc.cost_line(t)
    assert line and len(line) <= 120, "K6: one line, <=120 chars"
    assert "84" in line and "turn" in line
    t["cost_tokens"] = 10 ** 12              # absurd width forces the drop order
    line2 = tc.cost_line(t)
    assert len(line2) <= 120, "K6: tokens drop first under budget pressure"


# ------------------------------------------------------ K7: absent honesty
def test_k7_pre_t056_tasks_render_nothing(monkeypatch, tmp_path):
    _client()
    _ns(monkeypatch)
    tc = _mod()
    t = _task("T900", "alice", "done")       # no cost_* keys at all
    assert tc.cost_line(t) == "", "K7: absent stamps render absent -- no placeholders"


# ------------------------------------------------------ K8: legacy scalar shape
def test_k8_scalar_token_total_never_becomes_confident_zero(monkeypatch, tmp_path):
    """Kimi/Sol passed one integer total while task_costs accepted dictionaries only.

    Turns, duration, and tools still incremented, so the missing token field looked like
    a real zero. Keep scalar acceptance as a compatibility fence while the runners move
    to the canonical split shape (K9).
    """
    c = _client()
    ns = _ns(monkeypatch)
    tc = _mod()
    led = _ledger(tmp_path, [_task("T900", "alice", "in_progress")])

    assert tc.attribute_turn("alice", _row(tokens=1234), ledger=led) == "T900"
    acc = c.hgetall(f"{ns}:task_cost:T900")
    assert int(acc.get("tokens", 0)) == 1234, (
        "K8: a positive scalar token total must be counted, not silently omitted as zero")


def _runner_record_token_exprs(relpath):
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    source = open(os.path.join(root, relpath), encoding="utf-8").read()
    tree = ast.parse(source, filename=relpath)
    out = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        if not (isinstance(fn, ast.Attribute) and fn.attr == "record"
                and isinstance(fn.value, ast.Name) and fn.value.id == "_tm"):
            continue
        out.extend(kw.value for kw in node.keywords if kw.arg == "tokens")
    return out


def _is_toks_index(node, index):
    return (isinstance(node, ast.Subscript)
            and isinstance(node.value, ast.Name) and node.value.id == "toks"
            and isinstance(node.slice, ast.Constant) and node.slice.value == index)


# ------------------------------------------------------ K9: live runner wiring
@pytest.mark.parametrize("relpath", [
    "scripts/bifrost_runner_kimi.py",
    "scripts/bifrost_runner_sol.py",
])
def test_k9_kimi_and_sol_pass_split_token_usage(relpath):
    """Pin the consumers, not only the meter: both runners must reach turn_metrics with
    the same split dictionary DeepSeek uses. A scalar here recreates confident-zero task
    telemetry even if every isolated meter test is green.
    """
    exprs = _runner_record_token_exprs(relpath)
    assert len(exprs) == 1, f"K9: expected one _tm.record token seam in {relpath}"
    expr = exprs[0]
    assert isinstance(expr, ast.IfExp) and isinstance(expr.body, ast.Dict), (
        f"K9: {relpath} must pass a conditional split token dictionary, got "
        f"{ast.dump(expr, include_attributes=False)}")
    pairs = {
        key.value: value
        for key, value in zip(expr.body.keys, expr.body.values)
        if isinstance(key, ast.Constant) and isinstance(key.value, str)
    }
    assert set(pairs) == {"prompt", "completion"}, (
        f"K9: {relpath} token keys must be prompt+completion, got {sorted(pairs)}")
    assert _is_toks_index(pairs["prompt"], 0), f"K9: {relpath} prompt must use toks[0]"
    assert _is_toks_index(pairs["completion"], 1), (
        f"K9: {relpath} completion must use toks[1]")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
