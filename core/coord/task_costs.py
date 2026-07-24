"""Task cost telemetry (T056 / wishlist R5) -- per-slice ROI, honestly attributed.

Build spec: docs/library/report/20260714_r5-cost-telemetry-reconciliation-build-s_d7f3a8.md (full-fence
reconciliation; deepseek's owner-attributed accumulator design ADOPTED -- his half won
the central divergence on the verified one-in-progress gate). Pins: K1-K7 in
tests/test_t056_cost_telemetry.py.

Mechanics (his D1-D3): the HOT path (turn_metrics.record) calls attribute_turn() --
owner-matched active task gets HINCRBYs on {ns}:task_cost:{tid}; fail-open, <=4 Redis
ops, never touches the turn it measures (pin K2 = the recorder lesson honored). The
COLD path (task_ledger.transition -> DONE) calls finalize() -- accumulator becomes
durable cost_* fields on the task record, key deleted, bounces never double-count
(K4). Render (cost_line) is RETRO-ONLY: done tasks only (K5 -- the Goodhart guard:
no live ticker, never codify pace), one line <=120 chars, tokens drop first (K6),
absent stamps render absent (K7 -- pre-T056 tasks look exactly as they always did).
UNDER-report is the only permitted error direction (C5).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

FIELDS = ("turns", "duration_cs", "tool_calls", "tokens")   # duration in centiseconds (int HINCRBY)
COST_KEYS = ("cost_turns", "cost_duration_s", "cost_tool_calls", "cost_tokens")
LINE_BUDGET = 120


def _ns() -> str:
    return os.environ.get("BIFROST_NAMESPACE", "bifrost")


def _acc_key(tid: str) -> str:
    return f"{_ns()}:task_cost:{tid}"


def _client():
    try:
        from core.comm.bus import get_bus
        return get_bus("task-costs")._client
    except Exception:
        return None


def _active_task_for(agent: str, ledger=None) -> Optional[str]:
    """The ONE task owned by `agent` in IN_PROGRESS or VERIFYING, else None. The
    one-in-progress serialize gate (task_ledger.py:195-199) makes this at most one."""
    try:
        if ledger is None:
            from core.coord.task_ledger import TaskLedger
            ledger = TaskLedger()
        hits = [t["id"] for t in ledger.tasks.values()
                if t.get("owner") == str(agent)
                and t.get("status") in ("in_progress", "verifying")]
        return hits[0] if len(hits) == 1 else None   # 0 or (defensively) >1 -> refuse
    except Exception:
        return None


def attribute_turn(agent: str, row: Dict[str, Any], ledger=None) -> Optional[str]:
    """HOT PATH (called from turn_metrics.record, inside its fail-open try): attribute
    one turn's facts to the agent's active task. Returns the tid or None. Never raises."""
    try:
        tid = _active_task_for(agent, ledger=ledger)
        if not tid:
            return None
        c = _client()
        if c is None:
            return None
        key = _acc_key(tid)
        c.hincrby(key, "turns", 1)
        c.hincrby(key, "duration_cs", int(round(float(row.get("duration_s", 0) or 0) * 100)))
        c.hincrby(key, "tool_calls", int(row.get("tool_count", 0) or 0))
        toks = row.get("tokens") or {}
        if isinstance(toks, dict) and toks:
            c.hincrby(key, "tokens", int(sum(int(v or 0) for v in toks.values())))
        return tid
    except Exception:
        return None


def finalize(tid: str, task: Dict[str, Any]) -> Dict[str, Any]:
    """COLD PATH (called at the DONE transition): accumulator -> durable cost_* keys on
    the task dict; the Redis key is deleted. Missing/empty accumulator -> {} and the
    task is untouched (absent honesty, K3/K7; a verifying bounce that already finalized
    finds an empty accumulator and changes nothing, K4). Never raises."""
    try:
        c = _client()
        if c is None:
            return {}
        key = _acc_key(str(tid))
        acc = c.hgetall(key) or {}
        c.delete(key)
        if not acc or int(acc.get("turns", 0) or 0) <= 0:
            return {}
        stamped = {
            "cost_turns": int(acc.get("turns", 0) or 0),
            "cost_duration_s": round(int(acc.get("duration_cs", 0) or 0) / 100.0, 1),
            "cost_tool_calls": int(acc.get("tool_calls", 0) or 0),
        }
        if int(acc.get("tokens", 0) or 0) > 0:
            stamped["cost_tokens"] = int(acc.get("tokens", 0))
        task.update(stamped)
        return stamped
    except Exception:
        return {}


def _fmt_tokens(n: int) -> str:
    if n >= 10 ** 9:
        return f"{n / 10**9:.1f}G tok"
    if n >= 10 ** 6:
        return f"{n / 10**6:.1f}M tok"
    if n >= 1000:
        return f"{round(n / 1000)}k tok"
    return f"{n} tok"


def cost_line(task: Dict[str, Any]) -> str:
    """RETRO-ONLY render: '' unless the task is DONE and carries cost_turns (K5/K7).
    One line, <=LINE_BUDGET chars; under pressure tokens drop first, then duration --
    the turn count always renders (K6). Never raises."""
    try:
        if str(task.get("status")) != "done":
            return ""
        turns = task.get("cost_turns")
        if not turns:
            return ""
        parts = [f"cost: {int(turns)} turn(s)"]
        dur = task.get("cost_duration_s")
        if dur:
            parts.append(f"{int(round(float(dur)))}s")
        tools = task.get("cost_tool_calls")
        if tools:
            parts.append(f"{int(tools)} tools")
        toks = task.get("cost_tokens")
        if toks:
            parts.append(_fmt_tokens(int(toks)))
        line = " · ".join(parts) + "  (fleet-shared window)"
        while len(line) > LINE_BUDGET and len(parts) > 1:
            parts.pop()                       # tokens first, then tools, then duration
            line = " · ".join(parts) + "  (fleet-shared window)"
        return line[:LINE_BUDGET]
    except Exception:
        return ""
