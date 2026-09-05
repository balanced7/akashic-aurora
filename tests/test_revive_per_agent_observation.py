"""RED-first pins: the revive ladder must observe PER AGENT, not in aggregate.

Found by drill 2026-08-24 (Daniil: "I don't want to ... be hard stuck if anthropics
servers go down again"). Killing kimi's daemon and runner and firing the lever printed
`PROVE daemon: verified alive` -- and it would have printed that even with kimi dead
forever, because observe() asked `daemon_n > 0`: ANY live daemon marks EVERY agent
healthy. One survivor masks the rest. That is the false-receipt class this house has paid
for repeatedly (a heartbeat read as a service, a sprout receipt over a corpse), arriving
in the one lever the operator reaches for from his phone.

Second, independent defect in the same three lines: the runner counter matches SCRIPT
names (`bifrost_runner_{agent}`), but every runner agent runs `bifrost_runner_deepseek.py`
with `--agent <name>`. So `bifrost_runner_kimi` matches nothing ever, and
`bifrost_runner_deepseek` matches BOTH agents -- the count is structurally incapable of
saying which agent is down.

The fix these pin: observation keys on `--agent <name>` in the cmdline, health means
EVERY expected agent is present, and the detail NAMES who is missing.

Run: py -m pytest tests/test_revive_per_agent_observation.py -q
"""
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DAEMON = "python E:/AI-Setup/scripts/bifrost_daemon.py --agent {a} --spawn-runner"
RUNNER = "python E:/AI-Setup/scripts/bifrost_runner_deepseek.py --agent {a} --agentic --allow-write --allow-exec"
GATEWAY = "python E:/AI-Setup/scripts/bifrost_runner_discord.py"


def _observe(cmdlines):
    """_cmdlines() returns ONE newline-joined string (counting is substring-based),
    so the fixture must be that same shape or the pins test a fiction."""
    import scripts.revive as revive
    orig = revive._cmdlines
    revive._cmdlines = lambda: "\n".join(cmdlines) + "\n"
    try:
        return revive.observe()
    finally:
        revive._cmdlines = orig


def test_one_live_daemon_does_not_mark_a_dead_agent_healthy():
    """THE DEFECT: deepseek's daemon alive, kimi's dead -> must NOT report healthy."""
    out = _observe([DAEMON.format(a="deepseek"),
                    RUNNER.format(a="deepseek"),
                    GATEWAY])
    assert not out["daemon"]["healthy"], (
        "a live deepseek daemon masked kimi's dead one: " + out["daemon"]["detail"])


def test_dead_agent_is_named_in_the_detail():
    """The confession is relayed verbatim to Discord; it must say WHO is down, because
    'N process(es)' is unactionable from a phone."""
    out = _observe([DAEMON.format(a="deepseek"), RUNNER.format(a="deepseek"), GATEWAY])
    assert "kimi" in out["daemon"]["detail"]


def test_all_daemons_present_is_healthy():
    # roster grew 2026-09-03 (S1): claude's manage-listener daemon is now a rung,
    # so "all present" includes it -- fixture premise updated, assertion unchanged.
    out = _observe([DAEMON.format(a="deepseek"), DAEMON.format(a="kimi"),
                    "python.exe E:\\AI-Setup\\scripts\\bifrost_daemon.py "
                    "--agent claude --manage-listener",
                    RUNNER.format(a="deepseek"), RUNNER.format(a="kimi"), GATEWAY])
    assert out["daemon"]["healthy"], out["daemon"]["detail"]
    assert out["runners"]["healthy"], out["runners"]["detail"]


def test_runner_is_counted_by_agent_not_by_script_name():
    """Every runner agent runs bifrost_runner_deepseek.py; only --agent distinguishes
    them. Counting script names made kimi invisible and double-counted deepseek."""
    out = _observe([DAEMON.format(a="deepseek"), DAEMON.format(a="kimi"),
                    RUNNER.format(a="deepseek"), GATEWAY])   # kimi RUNNER missing
    assert not out["runners"]["healthy"], out["runners"]["detail"]
    assert "kimi" in out["runners"]["detail"]


def test_two_deepseek_runners_do_not_satisfy_a_missing_kimi():
    """The old sum() could reach the threshold from duplicates of ONE agent."""
    out = _observe([DAEMON.format(a="deepseek"), DAEMON.format(a="kimi"),
                    RUNNER.format(a="deepseek"), RUNNER.format(a="deepseek"), GATEWAY])
    assert not out["runners"]["healthy"], out["runners"]["detail"]


def test_gateway_requires_its_own_ready_generation(monkeypatch):
    """A command line is necessary, but it is no longer sufficient health proof."""
    from core.comm import gateway_readiness

    record = {
        "pid": 4242,
        "generation": "4242-test",
        "ready": True,
        "world": "prod",
        "beat_ts": time.time(),
        "code_sha": "test",
        "detail": "discord on_ready",
    }
    monkeypatch.setattr(gateway_readiness, "read", lambda *a, **k: record)
    out = _observe(["4242\t" + GATEWAY])
    assert out["gateway"]["healthy"]
    monkeypatch.setattr(gateway_readiness, "read", lambda *a, **k: None)
    out = _observe(["4242\t" + GATEWAY])
    assert not out["gateway"]["healthy"]
    out2 = _observe([DAEMON.format(a="kimi")])
    assert not out2["gateway"]["healthy"]


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q"]))
