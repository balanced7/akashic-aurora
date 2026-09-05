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
from pathlib import Path

import pytest

from core.fleet import seat_launchers as sl

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _which_ok(name):
    return {"dsh": str(Path(ROOT) / ".test-bin" / "dsh")}.get(name)


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


# SUPERSEDED ENTRY, recorded rather than quietly dropped: `"vandor"` was in this list
# when the file was written, asserting it must stay a task. Daniil then asked for
# `!spawn vandor` to launch the app and a seat, so the bare word now resolves BY
# INSTRUCTION. The invariant it was protecting is unchanged and still pinned below —
# a SENTENCE beginning with a seat name is still a task, vandor included.
@pytest.mark.parametrize("word", [
    "rill and check the ui", "fix the wedge", "", "   ",
    "boot and take the watch", "spawn a seat to audit the gate",
    "vandor and take the watch", "vandor please drain the lane",
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


# ============================================================================
# THE EXEC PIN. Daniil, 2026-08-24: "lets make sure the cli version it spawns is
# exec enabled so it can respond, we have been bitten by that so many times."
#
# A seat spawned read-only cannot arm its own wake watcher, drain its mail, commit,
# or run a test. It boots, appears on every dial, and can do nothing — which is
# indistinguishable from a working seat until he needs one. The house has paid for
# this repeatedly. These pins make the regression impossible rather than unlikely.
# ============================================================================
@pytest.mark.parametrize("mode", ["default", "arm", "", None, "nonsense", "ARM", "Default"])
def test_a_spawned_claude_seat_can_ALWAYS_exec(mode):
    """Bash must ride the launch line for every mode that is not the break-glass one.
    An unknown mode degrades to ARMED, never silently to read-only."""
    flags = " ".join(sl.claude_permission_flags(mode))
    assert "Bash" in flags, f"mode {mode!r} spawned a seat that cannot exec: {flags}"
    assert "Write" in flags and "Edit" in flags, flags
    assert "acceptEdits" in flags, flags


def test_dangerous_is_the_only_mode_that_skips_permissions():
    assert sl.claude_permission_flags("dangerous") == ["--dangerously-skip-permissions"]
    for m in ("default", "arm", "nonsense"):
        assert "--dangerously-skip-permissions" not in sl.claude_permission_flags(m)


@pytest.mark.parametrize("mode", ["default", "arm", "", None, "nonsense"])
def test_a_spawned_claude_seat_can_ALSO_use_powershell(mode):
    """2026-09-03: a headless Discord spawn tried a read-only PowerShell WMI query
    (Get-CimInstance Win32_VideoController, driver-version recon) and was blocked twice by
    'requires approval' with nobody at a terminal to grant it -- not because the command was
    risky, but because PowerShell was never in --allowedTools to begin with. Bash rode the
    launch line (the pin above); PowerShell -- this harness's PRIMARY shell tool on Windows
    per claude_pretooluse.py's own docstring -- did not. An unattended seat that cannot open
    PowerShell cannot answer any Windows-native diagnostic (drivers, services, WMI, registry)
    without a human standing by to click a prompt that headless mode can never show."""
    flags = " ".join(sl.claude_permission_flags(mode))
    assert "PowerShell" in flags, f"mode {mode!r} spawned a seat with no PowerShell: {flags}"


# ------------------------------------------------------------------ flag parsing
def test_flags_parse_off_so_a_flagged_seat_still_resolves():
    rec, flags = sl.parse_spawn_target("vandor --repair")
    assert rec and rec["seat"] == "claude" and flags == {"--repair"}


def test_a_flagged_SENTENCE_is_still_a_task():
    rec, _ = sl.parse_spawn_target("vandor --repair and then audit the gate")
    assert rec is None, "a sentence must not become a launch just because it carries a flag"


# --------------------------------------------------------- options, not surprises
def _plan(**kw):
    base = dict(app_healthy=False, app_repairable=True, app_detail="status Modified",
                live_seats=0, flags=set())
    base.update(kw)
    return sl.claude_seat_plan(**base)


def test_app_missing_with_no_flag_OFFERS_rather_than_acting():
    """Daniil: 'have it give me options if claude code is not detected'. Package surgery
    triggered from a phone by a bare word is not something this house does silently."""
    p = _plan()
    assert p["action"] == "options", p
    assert "NOT DETECTED" in p["message"], p["message"]
    for choice in ("--repair", "--seat", "!revive --target app"):
        assert choice in p["message"], p["message"]


def test_the_options_message_does_not_read_like_it_acted():
    m = _plan()["message"].lower()
    assert "spawning" not in m and "launched" not in m, m


def test_repair_is_opt_in_and_says_what_it_will_do():
    p = _plan(flags={"--repair"})
    assert p["action"] == "repair_then_spawn"
    assert "verifying payload" in p["message"] and "stale status bit" in p["message"]
    # And it must not read as proven. The MSIX rung is drilled; the end-to-end
    # app-down -> repair -> seat chain is not, and cannot be from inside the app.
    assert "NOT" in p["message"] and "end-to-end" in p["message"].lower(), p["message"]


def test_seat_flag_skips_the_app_because_the_cli_works_without_it():
    p = _plan(flags={"--seat"})
    assert p["action"] == "spawn" and "works without it" in p["message"]


def test_a_healthy_app_just_spawns_without_a_menu():
    p = _plan(app_healthy=True, app_detail="status Ok", live_seats=2)
    assert p["action"] == "spawn" and "2 live claude seat(s)" in p["message"]


def test_status_reports_and_never_acts_even_when_everything_is_fine():
    p = _plan(app_healthy=True, app_detail="status Ok", flags={"--status"})
    assert p["action"] == "options", p


def test_an_unrepairable_app_refuses_repair_by_name_instead_of_trying():
    p = _plan(app_repairable=False, app_detail="status Tampered", flags={"--repair"})
    assert p["action"] == "options"
    assert "NOT repairable" in p["message"], p["message"]
