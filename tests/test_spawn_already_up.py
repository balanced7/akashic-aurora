"""RED: an EADDRINUSE refusal is not a corpse. Defer item 7347ae30c9, 2026-08-26:
Daniil ran `!spawn Rill` from his phone and got a red warning -- "that spawn never
lived -- exit 1: Node.js v24.14.1". The real cause, in state/spawn-logs/
launch-rill-1787760845.log, was `listen EADDRINUSE: address already in use
127.0.0.1:3080` because Rill was ALREADY ALIVE. The port acted as a de facto
singleton and correctly refused a second instance -- the right outcome, reported
as a failure, and the one fact that would have reassured him (already running,
here is the address) was buried in a log file he cannot read from a phone.

`spawn_stillborn_reason` has no vocabulary for "already running"; it falls through
to the log's last line, which for a Node crash is the interpreter banner. This pin
holds `spawn_already_up_reason`, the function that names the condition BEFORE the
stillborn fallback ever gets a turn.

Run:  py -m pytest tests/test_spawn_already_up.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import discord_inbound as DI  # noqa: E402

RILL_LOG = (REPO / "state" / "spawn-logs" / "launch-rill-1787760845.log")


def test_eaddrinuse_is_recognized_not_a_stillbirth():
    """The exact incident log: EADDRINUSE names the seat as already up, not dead."""
    log_text = RILL_LOG.read_text(encoding="utf-8") if RILL_LOG.exists() else (
        "Error: listen EADDRINUSE: address already in use 127.0.0.1:3080\n"
        "Node.js v24.14.1\n")
    already = DI.spawn_already_up_reason(log_text)
    assert already is not None, "EADDRINUSE must be recognized as already-up, not silence"
    assert already == "127.0.0.1:3080", already


def test_already_up_wins_over_the_interpreter_banner():
    """The bug verbatim: the last line is 'Node.js v24.14.1', not the real cause.
    spawn_stillborn_reason alone falls through to that banner -- the caller must
    check spawn_already_up_reason FIRST and never let the fallback answer instead."""
    log_text = "Error: listen EADDRINUSE: address already in use 127.0.0.1:3080\nNode.js v24.14.1\n"
    stillborn = DI.spawn_stillborn_reason(1, log_text)
    assert stillborn is not None and "Node.js" in stillborn, (
        "the fallback reason must still be the banner -- that IS the defect this "
        "already-up check is designed to be consulted ahead of")
    already = DI.spawn_already_up_reason(log_text)
    assert already == "127.0.0.1:3080"


def test_marker_without_a_readable_address_is_still_already_up():
    """Matched but addressless: caller must branch on `is not None`, not truthiness."""
    already = DI.spawn_already_up_reason("Error: EADDRINUSE\n")
    assert already is not None
    assert already == ""


def test_ordinary_death_is_not_already_up():
    """No false positives: a plain crash must not be misread as a refused port."""
    assert DI.spawn_already_up_reason("Failed to authenticate: OAuth session expired\n") is None


def test_no_log_is_not_already_up():
    assert DI.spawn_already_up_reason("") is None
    assert DI.spawn_already_up_reason(None) is None


def test_case_insensitive_and_one_line_result():
    already = DI.spawn_already_up_reason("ERROR: ADDRESS ALREADY IN USE 10.0.0.5:9999\n")
    assert already == "10.0.0.5:9999"
