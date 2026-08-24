"""Pins for `!spawn <name>` — the lever that meant something other than what he meant.

2026-08-24: locked out, conductor dead, Daniil typed `!spawn rill` from his phone. `!spawn`
does not resolve names — it takes the text as a TASK STRING — so a fresh claude seat was
spawned to go and think about the word "rill". It investigated Rill, wrote a report, and
stopped. Rill itself was never started and stayed down all day.

The load-bearing pin here is `test_rill_states_its_own_identity`. A DSH launched from
inside another harness inherits that harness's AKASHIC_AGENT_ID, and the akashic plugin
then pins itself OBSERVE-ONLY by its own identity check (index.js:135). Get this wrong and
Rill comes up present, beating, listed on every dial, and deaf. That is the failure mode
this whole day has been about, and here it is one environment variable wide.
"""
from __future__ import annotations

import os

import pytest

from core.fleet import seat_launchers as sl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _which_ok(name):
    return {"dsh": r"C:\Users\L5\AppData\Roaming\npm\dsh"}.get(name)


# ------------------------------------------------------------------ resolution
@pytest.mark.parametrize("word,seat", [
    ("rill", "dsh_agent"), ("Rill", "dsh_agent"), ("dsh_agent", "dsh_agent"),
    ("heimdall", "deepseek"), ("DeepSeek", "deepseek"),
    ("navi", "kimi"), ("kimi", "kimi"),
    ("  navi  ", "kimi"), ("`rill`", "dsh_agent"),
])
def test_a_bare_seat_name_resolves_by_callsign_or_agent_id(word, seat):
    """He says 'rill', the ledger says 'dsh_agent', and neither is wrong."""
    rec = sl.resolve_seat(word)
    assert rec and rec["seat"] == seat, f"{word!r} -> {rec}"


@pytest.mark.parametrize("word", [
    "rill and check the ui", "fix the wedge", "", "   ",
    "boot and take the watch", "spawn a seat to audit the gate", "vandor",
])
def test_a_sentence_is_a_TASK_and_must_not_be_hijacked_into_a_launch(word):
    """The historical behaviour must stay reachable for everything that is not exactly a
    seat name. A lever that sometimes swallows your sentence because it began with a name
    is worse than the one it replaces."""
    assert sl.resolve_seat(word) is None, f"{word!r} must remain a task"


# ------------------------------------------------------- THE identity pin (rill)
def test_rill_states_its_own_identity_and_does_not_inherit_the_launchers():
    """THE load-bearing pin. AKASHIC_AGENT_ID must be dsh_agent in the launch env. If the
    parent's id leaks through, the plugin pins itself observe-only and Rill comes up
    present and deaf — indistinguishable, from a phone, from a working seat."""
    rec = sl.resolve_seat("rill")
    argv, env, cwd = sl.launch_argv(rec, root=ROOT, which=_which_ok, dsh_home=r"C:\dsh")
    assert env.get("AKASHIC_AGENT_ID") == "dsh_agent", env
    assert env.get("DSH_HOME") == r"C:\dsh", env
    assert argv[1] == "web" and "--no-open" in argv, argv
    assert cwd == r"C:\dsh"


@pytest.mark.parametrize("word,seat", [("rill", "dsh_agent"), ("heimdall", "deepseek"),
                                       ("navi", "kimi")])
def test_EVERY_seat_states_its_own_identity(word, seat):
    """Not just Rill. No seat may inherit the launching process's id — that is how a
    launched seat gets mis-attributed or silently muted."""
    rec = sl.resolve_seat(word)
    _, env, _ = sl.launch_argv(rec, root=ROOT, which=_which_ok, dsh_home=r"C:\dsh")
    assert env.get("AKASHIC_AGENT_ID") == seat, env


def test_a_missing_dsh_cli_REFUSES_rather_than_pretending():
    rec = sl.resolve_seat("rill")
    with pytest.raises(RuntimeError, match="not on PATH"):
        sl.launch_argv(rec, root=ROOT, which=lambda n: None, dsh_home=r"C:\dsh")


# ------------------------------------------------------------- the kimi hazard
def test_navi_launches_with_her_OWN_runner_not_through_the_daemon():
    """bifrost_daemon.py hardcodes bifrost_runner_deepseek.py for --spawn-runner
    (lines 256/416), so `--agent kimi --spawn-runner` hands Kimi the wrong script. A
    non-deepseek seat launches with its own."""
    rec = sl.resolve_seat("navi")
    argv, _, _ = sl.launch_argv(rec, root=ROOT, which=_which_ok)
    joined = " ".join(argv).replace("\\", "/")
    assert "bifrost_runner_kimi.py" in joined, joined
    assert "bifrost_daemon.py" not in joined, joined
    assert "--agent kimi" in joined, joined


def test_heimdall_goes_through_the_daemon_which_owns_its_runner_child():
    rec = sl.resolve_seat("heimdall")
    argv, _, _ = sl.launch_argv(rec, root=ROOT, which=_which_ok)
    joined = " ".join(argv).replace("\\", "/")
    assert "bifrost_daemon.py" in joined and "--spawn-runner" in joined, joined


# ------------------------------------------------- an undrilled lever says so
def test_an_undrilled_lever_does_not_read_like_a_drilled_one():
    """The house rule is that a recovery path without an executed drill is PRESUMED
    BROKEN. If both render identically to the operator, the flag is decoration."""
    drilled = sl.launch_note(sl.resolve_seat("rill"))
    undrilled = sl.launch_note(sl.resolve_seat("navi"))
    assert "drilled 2026-08-24" in drilled, drilled
    assert "NOT yet drilled" in undrilled, undrilled
    assert drilled != undrilled


def test_the_note_carries_the_url_when_the_seat_serves_one():
    assert "127.0.0.1:3080" in sl.launch_note(sl.resolve_seat("rill"))
