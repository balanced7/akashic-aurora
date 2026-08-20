"""The discord gateway becomes observable: a heartbeat the liveness plane can read, and a log
that outlives whatever launched it.

EARNED TONIGHT, 2026-08-19/20. I restarted the gateway, told Daniil it was up, and then a task
notification reported exit 127. The service was fine -- the harness WRAPPER had exited while the
detached process kept serving. But the diagnosis took four tool calls and ended at a worse place
than it started:

  - `grep -c heartbeat scripts/bifrost_runner_discord.py` -> 4 references
  - `doctor | grep -ic discord`                            -> 0

The gateway does not register in the liveness plane at all. So its DEATH is undetectable by the
organ built to detect death, and its stdout went to a wrapper that is now gone. I made his
Discord bridge unobservable and said so out loud instead of fixing it, which is the exact
name-it-and-move-on pattern I spent the evening criticising in the ledger.

WHY A HEARTBEAT AND NOT A WATCHER, which is the whole lesson: a pipe-watcher only knows about
death while it holds the pipe. control_channel.py already documents the fatal version of this --
"control.is_halted is checked inside the message-handling path, which only runs AFTER a message
arrives, which is exactly what a blocked read prevents" -- and kimi was once up, heartbeating and
uncommandable for twelve hours. State-based liveness is readable from anywhere, forever, including
after the watcher itself dies.

THE INTERVAL IS NOT MINE TO CHOOSE. liveness.WORKLIVE_TTL is 45s and its comment says it is sized
"> the ~5s heartbeat refresh, so a live record never flaps". Picking my own cadence would put two
numbers in charge of one behaviour -- the T263 defect, and the same mistake I made earlier tonight
guessing 5s for a 16s failure. So it derives from the constant and a pin holds the relationship.

Run:  py -m pytest tests/test_gateway_observability.py -v
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))


def _gateway():
    """Load the runner shell by path -- it is a script, not a package member."""
    spec = importlib.util.spec_from_file_location(
        "_gw", REPO / "scripts" / "bifrost_runner_discord.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ------------------------------------------------------------------ the heartbeat cadence
def test_heartbeat_interval_derives_from_the_ttl_it_must_not_outlive():
    """One number in charge of one behaviour. If someone retunes WORKLIVE_TTL, the gateway's
    cadence follows instead of silently letting the record flap."""
    from core.comm.liveness import WORKLIVE_TTL
    gw = _gateway()
    assert gw.HEARTBEAT_S * 3 <= WORKLIVE_TTL, (
        f"a {gw.HEARTBEAT_S}s beat under a {WORKLIVE_TTL}s TTL leaves too little margin -- "
        "a live gateway would intermittently read as dead")
    assert gw.HEARTBEAT_S >= 1, "a sub-second beat spends more on saying it is alive than on work"


def test_the_gateway_has_a_stable_liveness_identity():
    """doctor discovers agents; an anonymous service is invisible to it by construction."""
    gw = _gateway()
    assert isinstance(gw.GATEWAY_AGENT_ID, str) and gw.GATEWAY_AGENT_ID.strip()
    assert gw.GATEWAY_AGENT_ID != "daniil", (
        "the gateway SPEAKS as the operator on the bus (R3) but it must not claim his liveness "
        "identity -- that would report the operator as alive whenever the socket is up")


def test_the_beat_is_fail_open():
    """liveness._flush already promises 'observability must never wedge the path it observes'.
    The gateway's beat inherits that promise: a dead bus costs the signal, never the service."""
    gw = _gateway()

    class _Broken:
        def refresh(self):
            raise RuntimeError("redis is having a night")

        def set(self, *a, **k):
            raise RuntimeError("redis is having a night")

    gw.beat(_Broken(), phase="online")          # must not raise


# ------------------------------------------------------------------ the durable log
def test_the_log_outlives_its_launcher(tmp_path):
    """The whole defect: stdout went to a wrapper that exited. A file does not exit."""
    gw = _gateway()
    dest = tmp_path / "gw.log"
    tee = gw.Tee(sys.stdout, dest)
    tee.write("listening as somebody\n")
    tee.flush()
    assert "listening as somebody" in dest.read_text(encoding="utf-8")


def test_the_log_survives_the_emoji_this_file_already_prints(tmp_path):
    """The runner prints a sprout and a warning glyph. A cp1252 file handle would crash the
    gateway on its own receipt -- which is how an observability feature kills a service."""
    gw = _gateway()
    dest = tmp_path / "gw.log"
    tee = gw.Tee(sys.stdout, dest)
    tee.write("[discord-in] \U0001F331 spawned pid 1 -- ⚠️ never lived\n")
    tee.flush()
    body = dest.read_text(encoding="utf-8")
    assert "\U0001F331" in body and "⚠" in body


def test_the_tee_never_swallows_the_original_stream(tmp_path):
    """A log that eats the console trades one blind spot for another."""
    gw = _gateway()
    seen = []

    class _Stream:
        def write(self, s):
            seen.append(s)

        def flush(self):
            pass

    tee = gw.Tee(_Stream(), tmp_path / "gw.log")
    tee.write("both places\n")
    assert seen == ["both places\n"]


def test_a_broken_log_never_takes_the_gateway_down(tmp_path):
    """Same rule as the beat, applied to the file: if the disk refuses, we lose the record and
    keep the bridge. The inverse would be an observability feature causing an outage."""
    gw = _gateway()
    tee = gw.Tee(sys.stdout, tmp_path / "no-such-dir" / "nested" / "gw.log")
    tee.write("still fine\n")        # must not raise even if the path is unopenable
    tee.flush()


def test_the_log_path_is_env_overridable(monkeypatch, tmp_path):
    """So a pin never appends to the live gateway log -- the ambient-state class that already
    cost us a real thread in his server once."""
    gw = _gateway()
    monkeypatch.setenv("AKASHIC_DISCORD_GATEWAY_LOG", str(tmp_path / "elsewhere.log"))
    assert str(tmp_path) in str(gw.gateway_log_path())
