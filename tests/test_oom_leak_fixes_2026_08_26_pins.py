"""Pins for the four defects found in the 2026-08-26 post-OOM audit.

The machine ran out of 62GB overnight and the forensics found no smoking gun, because
nothing was recording process memory. What the audit DID find was four defects, each
verified line by line. These are their pins, written RED before the fixes.

  P1  deepseek tool results append to history with NO clip, while gemini/kimi/sol all
      clip at 20000. Combined with MAX_TOOL_ROUNDS defaulting to 10**9 and a convos
      dict that never evicts, one big read is re-sent every remaining hop and retained
      for the life of the process. The codebase already MEASURED this: 393M tokens over
      309 turns, worst turn 11.4M over 127 hops.

  P2  revive._cmdlines() swallows every exception -- including its own 25s CIM timeout --
      into an empty string, which counts as ZERO gateways to a consumer whose only move
      is to spawn one. The EarWatchdog scheduled task runs it every 5 minutes, so memory
      pressure slows the probe, the timeout reads as death, and the cure is another
      process. Receipts: 4 then 3 concurrent gateways ~50 min before the poweroff.
      THE RULE: an unanswerable probe must REFUSE, never remediate. "I don't know" may
      not be spelled the same as "it's dead". revive.py already states this rule for its
      app rung (a probe that cannot run must read as NOT healthy) -- the process rungs
      just never honoured it.

  P3  remote_relay._write_jsonl uses a FIXED temp filename and accept() does an unlocked
      read-modify-write under a ThreadingHTTPServer with no thread cap. Two concurrent
      admits race os.replace and one message is SILENTLY DROPPED -- on the inbox that is
      also the idempotency ledger.

  P4  ManagedChild turns env=None into {} and hands that to Popen, which means a truly
      empty environment -- no PATH, no SYSTEMROOT, none of the AKASHIC_* overrides.
      subprocess.Popen's own contract is that env=None INHERITS. remote_bridge_supervise
      is the one caller that omits env, and it is the file that exists because the
      listener kept vanishing.

Run: py -m pytest tests/test_oom_leak_fixes_2026_08_26_pins.py -q
"""
from __future__ import annotations

import json
import os
import sys
import threading
from pathlib import Path

import pytest

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "scripts"))


# ------------------------------------------------------------------ P1: the clip
def test_deepseek_clips_tool_results_like_its_siblings():
    """A tool result larger than the bound is clipped before it enters history.

    The retention is what matters: an unclipped 120KB result is not merely sent once,
    it is RE-SENT on every remaining hop and kept for the process lifetime.
    """
    import deepseek_chat

    limit = deepseek_chat.MAX_TOOL_RESULT_CHARS
    assert limit > 0, "a clip bound must exist and be positive"

    huge = "x" * (limit * 3)
    clipped = deepseek_chat.clip_tool_result(huge)

    assert len(clipped) < len(huge), "an oversized tool result must shrink"
    # Room for a short truncation notice, but nothing like the original payload.
    assert len(clipped) <= limit + 200, (
        f"clipped result is {len(clipped)} chars, bound is {limit}")
    assert "x" * 100 in clipped, "the head of the result must survive the clip"


def test_deepseek_clip_leaves_small_results_untouched():
    """The clip must be a ceiling, not a transform -- ordinary results pass through."""
    import deepseek_chat

    small = "the quick brown fox"
    assert deepseek_chat.clip_tool_result(small) == small


def test_deepseek_clip_bound_matches_the_siblings():
    """gemini, kimi and sol all clip at 20000. Divergence here is what caused this."""
    import deepseek_chat

    assert deepseek_chat.MAX_TOOL_RESULT_CHARS == 20000


# ------------------------------------------------- P2: the probe that must refuse
def test_decide_refuses_to_spawn_a_gateway_it_cannot_see():
    """decide() is PURE. An organ that is down but NOT repairable earns no plan.

    This is the whole defect: 'I could not read the process table' became 'there are
    zero gateways', and the only consumer of that was a spawner.
    """
    import revive

    observed = {
        "app": {"healthy": True},
        "redis": {"healthy": True},
        "daemon": {"healthy": True},
        "runners": {"healthy": True},
        "gateway": {"healthy": False, "repairable": False,
                    "detail": "process probe unreadable -- cannot prove absence"},
    }
    plan = revive.decide(observed, target="gateway")
    assert plan == [], f"a blind probe must not plan a spawn, got: {plan}"


def test_decide_still_spawns_a_gateway_that_is_genuinely_absent():
    """The refusal must not break the lever. A PROVEN-absent gateway is still healed."""
    import revive

    observed = {
        "app": {"healthy": True},
        "redis": {"healthy": True},
        "daemon": {"healthy": True},
        "runners": {"healthy": True},
        "gateway": {"healthy": False, "repairable": True, "detail": "0 gateway process(es)"},
    }
    plan = revive.decide(observed, target="gateway")
    assert len(plan) == 1 and plan[0]["organ"] == "gateway", (
        f"a genuinely dead gateway must still be planned, got: {plan}")


def test_observe_marks_process_rungs_unrepairable_when_the_probe_is_blind(monkeypatch):
    """When the process probe cannot answer, every rung that depends on it says so."""
    import revive

    monkeypatch.setattr(revive, "_cmdlines", lambda: None)
    observed = revive.observe(include_app=False)

    for organ in ("gateway", "daemon", "runners"):
        row = observed.get(organ) or {}
        assert row.get("repairable") is False, (
            f"{organ} must be unrepairable when the probe is blind, got {row}")


def test_observe_reports_a_real_zero_as_repairable(monkeypatch):
    """A probe that ANSWERS and finds nothing is a real absence -- still healable."""
    import revive

    monkeypatch.setattr(revive, "_cmdlines", lambda: "")
    observed = revive.observe(include_app=False)

    gw = observed.get("gateway") or {}
    assert gw.get("healthy") is False
    assert gw.get("repairable") is True, (
        f"an answered probe finding zero gateways is repairable, got {gw}")


# --------------------------------------------- P3: the read-modify-write that drops
def test_concurrent_appends_do_not_drop_rows(tmp_path):
    """N threads appending concurrently must yield N rows.

    The unlocked read-modify-write plus a FIXED temp filename means two admits race
    os.replace and the loser's message vanishes -- silently, on the file that doubles
    as the idempotency ledger.
    """
    from core.comm import remote_relay

    path = tmp_path / "inbox.jsonl"
    n = 24
    barrier = threading.Barrier(n)
    errors: list = []

    def _append(i: int) -> None:
        try:
            barrier.wait(timeout=10)
            remote_relay._append_row(path, {"id": f"msg-{i}", "content": f"body {i}"})
        except Exception as exc:                                        # noqa: BLE001
            errors.append(exc)

    threads = [threading.Thread(target=_append, args=(i,)) for i in range(n)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)

    assert not errors, f"appends raised: {errors[:3]}"
    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    got = sorted(r["id"] for r in rows)
    want = sorted(f"msg-{i}" for i in range(n))
    assert got == want, f"lost {len(want) - len(got)} row(s) to the race"


def test_append_row_is_idempotent_on_a_repeated_id(tmp_path):
    """The inbox is the idempotency ledger; the same id must not land twice."""
    from core.comm import remote_relay

    path = tmp_path / "inbox.jsonl"
    remote_relay._append_row(path, {"id": "dup", "content": "first"})
    added = remote_relay._append_row(path, {"id": "dup", "content": "second"})

    rows = [json.loads(ln) for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    assert len(rows) == 1, f"a repeated id must not append twice, got {rows}"
    assert added is False, "a duplicate append reports that it did not add"
    assert rows[0]["content"] == "first", "the first write wins; the duplicate is dropped"


def test_write_jsonl_uses_a_unique_temp_name(tmp_path):
    """Two writers must never collide on one temp path, whatever else is true."""
    from core.comm import remote_relay

    seen = set()
    for _ in range(5):
        seen.add(remote_relay._tmp_for(tmp_path / "inbox.jsonl"))
    assert len(seen) == 5, f"temp names must be unique per write, got {seen}"


# ------------------------------------------------------- P4: the empty environment
def test_managed_child_inherits_the_environment_by_default():
    """env=None must INHERIT, exactly as subprocess.Popen documents.

    An empty environment on Windows has no PATH and no SYSTEMROOT; the child cannot
    resolve its own interpreter, and none of the AKASHIC_* overrides reach it.
    """
    from bifrost_child import ManagedChild

    child = ManagedChild([sys.executable, "-c", "pass"])
    env = child._env

    assert env, "a default-constructed child must not get an empty environment"
    key = "PATH" if "PATH" in os.environ else next(iter(os.environ))
    assert key in env, f"{key} must be inherited by default"


def test_managed_child_still_honours_an_explicit_environment():
    """An explicit env is still exactly what the caller asked for -- no silent merge."""
    from bifrost_child import ManagedChild

    child = ManagedChild([sys.executable, "-c", "pass"], env={"ONLY": "this"})
    assert child._env == {"ONLY": "this"}
