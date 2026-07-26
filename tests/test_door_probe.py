"""Pins for the door probe -- the guard that stands outside the door.

Context: 2026-07-26, C7-4 regressed and every MCP seat hung on boot. The pin that
would have caught it (P6) was red and unrun, so this arc built the delivery side: a
probe that drives the real door from outside, a pre-push gate that blocks on it, and
the whisper line a fresh seat reads. core/comm/door_probe.py is now load-bearing --
if it lies, the gate passes a fleet-wide boot hang.

It ALREADY lied once, and that is the reason B3 exists. The first version used a
hang-only timeout of 25s and called the reproduced 2026-07-25 bug GREEN: with both
protections disabled the door still answered, in 11.38s against a 1.29s healthy
baseline, because the leaking spawn carries subprocess timeout=10 which bounds the
park. C7-4 does not always present as an infinite hang -- it presents as a reply
parked behind someone else's timeout, and that bound can be any number. Only the
mutation test caught it.

  B1  the probe answers GREEN end-to-end against the real door, and leaves no trace
  B2  the verdict cache round-trips (the whisper reads this, never a live probe)
  B3  the latency budget still sits between the healthy baseline and the known defect
  B4  every non-GREEN verdict carries a recovery line -- a red that does not teach
      just moves the confusion

Run: py -m pytest tests/test_door_probe.py -q
"""
import ast
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from core.comm import door_probe as dp   # noqa: E402

#: Measured 2026-07-26 by mutation-testing the probe against the reproduced bug.
HEALTHY_BASELINE_S = 1.3
KNOWN_DEFECT_S = 11.4


# ------------------------------------------------------------------------- B1
def test_b1_probe_is_green_against_the_real_door_and_leaves_no_trace():
    """End-to-end: real server subprocess, real stdio, real boot -- and a clean store.

    The probe boots into a temp AI_SETUP so the incarnation card, presence and boot
    event land in a throwaway dir. The hang class is still exercised, because the
    spawns that leak resolve the repo from os.path.dirname(__file__), not AI_SETUP.
    """
    v = dp.probe(cache=False)
    assert v["verdict"] == dp.GREEN, (
        f"B1: the door is not healthy right now -- {v.get('cause')}: {v.get('detail')}\n"
        f"    -> {v.get('recovery')}")
    assert v["elapsed_s"] < dp.SLOW_BUDGET_S


# ------------------------------------------------------------------------ B1b
def test_b1b_probe_isolation_contract_is_intact():
    """The probe must write its boot into a throwaway store, never the fleet's.

    Pinned on the ENV rather than by observing the roster: under pytest, conftest
    redirects this process to the same isolated store the probe writes to, so the
    probe's own seat is visible there by construction -- an observational assertion
    fails on a probe that is perfectly clean in production. Verified separately in a
    non-isolated shell: known_agents() before and after a probe is unchanged.
    """
    env = dp._probe_env("/tmp/door-probe-xyz")
    assert env["_AISETUP_TEST_ISOLATED"] == "1", (
        "B1b: the Redis isolation primitive is gone -- the probe's boot will register "
        "presence in canonical Redis and door-probe will appear in the fleet roster")
    assert env["AI_SETUP"] == "/tmp/door-probe-xyz", "B1b: file plane not redirected"
    assert env["AI_SETUP"] != str(dp.ROOT), "B1b: the probe is writing into the real repo"


# ------------------------------------------------------------------------- B2
def test_b2_verdict_cache_round_trips(tmp_path, monkeypatch):
    """The whisper reads the cache; it must never pay for (or hang on) a live probe."""
    monkeypatch.setattr(dp, "CACHE", tmp_path / "door" / "last_probe.json")
    v = dp._verdict(dp.RED, "boot", 9.9, "response_path_hang", "detail", "do the thing")
    dp.write_verdict(v)
    got = dp.read_verdict()
    assert got["verdict"] == dp.RED
    assert got["cause"] == "response_path_hang"
    assert got["recovery"] == "do the thing"


# ------------------------------------------------------------------------- B3
def test_b3_latency_budget_still_brackets_the_known_defect():
    """The number that makes the probe honest, pinned against being widened.

    A budget above the defect's latency turns the probe back into a reassurance
    machine -- which is exactly what the first version was. A budget at or below the
    healthy baseline makes it flap. Anyone moving this must move these numbers too,
    deliberately, with a fresh measurement.
    """
    assert HEALTHY_BASELINE_S < dp.SLOW_BUDGET_S < KNOWN_DEFECT_S, (
        f"B3: SLOW_BUDGET_S={dp.SLOW_BUDGET_S} no longer sits between the healthy "
        f"baseline ({HEALTHY_BASELINE_S}s) and the 2026-07-25 defect ({KNOWN_DEFECT_S}s). "
        "Above the defect the probe cannot see the bug it exists for.")
    assert dp.SLOW_BUDGET_S >= HEALTHY_BASELINE_S * 3, (
        "B3: less than 3x headroom over a healthy probe -- ordinary load will flap it")


# ------------------------------------------------------------------------- B4
def test_b4_every_non_green_verdict_teaches_a_recovery():
    """A RED that does not carry the fix just relocates the confusion.

    Walks the module: every _verdict(...) call constructing RED or UNKNOWN must pass a
    non-empty recovery. Checked in the source rather than at runtime because most of
    these branches only fire when the door is genuinely broken.
    """
    tree = ast.parse(open(dp.__file__, encoding="utf-8").read())
    bad = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and getattr(node.func, "id", "") == "_verdict"):
            continue
        first = node.args[0] if node.args else None
        level = getattr(first, "id", None)          # RED / UNKNOWN / GREEN as names
        if level not in {"RED", "UNKNOWN"}:
            continue
        # _verdict(verdict, stage, elapsed, cause, detail="", recovery="")
        recovery = node.args[5] if len(node.args) >= 6 else next(
            (k.value for k in node.keywords if k.arg == "recovery"), None)
        # A recovery is either a plain string or an f-string (JoinedStr) -- several of
        # them interpolate the failing stage or a command, which is the point.
        if isinstance(recovery, ast.JoinedStr):
            ok = bool(recovery.values)
        else:
            text = getattr(recovery, "value", None)
            ok = isinstance(text, str) and bool(text.strip())
        if not ok:
            bad.append(f"{os.path.basename(dp.__file__)}:{node.lineno}")
    assert not bad, f"B4: non-GREEN verdict(s) with no recovery line at {', '.join(bad)}"


# ------------------------------------------------------------------------- B4b
def test_b4b_render_surfaces_the_recovery_for_a_red():
    line = dp.render(dp._verdict(dp.RED, "boot", 9.9, "response_path_hang",
                                 "boot did not answer", "Boot via CLI: py agent_cli.py boot <you>"))
    assert "RED" in line and "Boot via CLI" in line
