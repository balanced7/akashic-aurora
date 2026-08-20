"""T365 RED: no 🌱 for a seat that never lived.

Daniil, 2026-08-19, unreachable all day: "Can you check what made you unreachable
to me?" He had pulled the one lever built for exactly that case -- !spawn from his
phone -- and Discord answered 🌱. The seat was already dead. state/spawn-logs/
spawn-1787154927.log holds the whole story in one line:

    Failed to authenticate: OAuth session expired and could not be refreshed

The gateway promised PROCESS START and nothing ever asked whether the process
lived. A 🌱 on a stillborn seat is the ✅-on-a-dead-send lie (6eacf225) wearing
gloves: the receipt was true about the syscall and false about the world, and the
operator reads receipts, not syscalls.

The verdict is DECIDABLE, so it lives in core where the pins are; the shell keeps
the clock and the process handle (that file owns the TOKEN, the SOCKET and the
event loop, and nothing else).

Run:  py -m pytest tests/test_t365_spawn_proves_life.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import discord_inbound as DI  # noqa: E402

OAUTH = "Failed to authenticate: OAuth session expired and could not be refreshed"


# ------------------------------------------------------------------ the verdict
def test_still_running_is_alive_the_sprout_is_honest():
    """exit_code None = still breathing after the grace window. 🌱 is TRUE here."""
    assert DI.spawn_stillborn_reason(None, "") is None


def test_nonzero_exit_is_stillborn_and_carries_the_real_line():
    """The reason must quote the log, not say 'spawn failed' -- he needs the WHY."""
    reason = DI.spawn_stillborn_reason(1, OAUTH + "\n")
    assert reason, "a child that exited 1 inside the grace window did not become a seat"
    assert "authenticate" in reason.lower(), reason
    assert "OAuth session expired" in reason, reason


def test_known_fatal_line_is_stillborn_even_on_a_zero_exit():
    """A truthful exit code is not guaranteed; the log line is the harder evidence."""
    reason = DI.spawn_stillborn_reason(0, OAUTH + "\n")
    assert reason and "authenticate" in reason.lower(), reason


def test_clean_fast_exit_is_not_an_alarm():
    """False-alarm floor: exit 0 with an ordinary log is a finished run, not a death.
    A gate nobody trusts is worse than no gate (sample_a_new_gate_for_its_fp_rate)."""
    assert DI.spawn_stillborn_reason(0, "did the work, wrapped, goodbye\n") is None


def test_reason_is_one_line_a_phone_reads_it():
    """It rides a Discord reaction/line on his phone -- no 40-line traceback."""
    reason = DI.spawn_stillborn_reason(1, "trace\n" * 200 + OAUTH + "\n")
    assert reason is not None
    assert "\n" not in reason.strip(), "the reason must be one line"
    assert len(reason) <= 300, len(reason)


def test_empty_log_still_names_the_exit_code():
    """Silence plus a corpse is still a stillbirth; say what little is known."""
    reason = DI.spawn_stillborn_reason(2, "")
    assert reason and "2" in reason, reason


# ------------------------------------------------------- no receipt for a corpse
def test_handle_message_does_not_sprout_when_the_spawner_raises():
    """The shell raises on stillbirth; handle_message must NOT swallow it into a 🌱.
    on_message's existing except-> ⚠️ path is the surfacing organ (T149 honesty)."""
    reactions = []

    def dead_spawner(task):
        raise RuntimeError(f"spawn died before it lived: {OAUTH}")

    cfg = DI.build_config()
    with pytest.raises(RuntimeError, match="died"):
        DI.handle_message(
            cfg,
            author_id=str(cfg["operator_id"]),
            author_name="daniil",
            channel_id="1539625011365552180",
            content="!spawn take the watch",
            bus=None,
            react=lambda e: reactions.append(e),
            role_mentions=[],
            spawner=dead_spawner,
        )
    assert "🌱" not in reactions, "a sprout receipt fired over a corpse"


# ------------------------------------------------------- the budget is a measurement
def test_proof_window_outlives_the_measured_death():
    """A guard against a slow failure needs a LATENCY BUDGET, not a round number.

    Measured 2026-08-19 on the real CLI with an expired OAuth session: 15.76s, 16.16s,
    16.92s (n=3, every one exit 1). The first window written here was 5s -- it called
    all three of those a living seat. This pin holds the measurement so the next person
    to 'tidy' the constant has to argue with the stopwatch instead of their intuition."""
    import re
    src = (REPO / "scripts" / "bifrost_runner_discord.py").read_text(encoding="utf-8")
    m = re.search(r'_SPAWN_PROOF_SECONDS\s*=\s*float\(.*?or\s*([\d.]+)\s*\)', src)
    assert m, "the proof window is no longer a readable default -- re-pin it"
    assert float(m.group(1)) >= 20.0, (
        f"proof window {m.group(1)}s is inside the measured 15.8-16.9s death window")
