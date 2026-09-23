"""The gateway census counts the observer -- and anything that merely MENTIONS it.

INCIDENT, 2026-09-23 ~09:02 EDT. `agent_cli.py gateway status` was asked twice inside
one minute about a gateway whose liveness never changed, and gave two wrong answers in
opposite directions:

    09:02:35  # gateway: NOT RUNNING (no live bifrost_runner_discord.py process)
    09:03:40  # gateway: LIVE pid 61020     <- the real one (pythonw.exe)
              # gateway: LIVE pid 21660     <- an investigator's bash shell
              # gateway: LIVE pid 20476     <- an investigator's bash shell
              # gateway: LIVE pid 18260     <- an investigator's bash shell

Root cause, one line: the census is a SUBSTRING test of "bifrost_runner_discord"
against every process's command line. So `grep bifrost_runner_discord` IS a gateway,
and `py -c "...bifrost_runner_discord..."` IS a gateway. Investigating the gateway
manufactures gateways, which is worst precisely during the incident the verb exists for.

This is not a new law. tests/test_dc6200d491_gateway_singleton.py's own docstring
records that "its sole idempotence was revive counting a process-table string, which is
how 4 concurrent gateways existed at 00:20 on 2026-08-26". The GUARD was then fixed
with a real DaemonLock. The string-counting census was left in place one layer up,
where it now reports four phantoms instead of creating four gateways. The corpus
already holds the rule -- learn:experiment:process_census_must_exclude_the_observer,
"match launch SHAPE (argv length + exact script path), never substring" -- filed
against a different census and point-applied there.

So these pins are deliberately written against a SHARED primitive
(wake_seat.script_processes) rather than against cmd_gateway's inline loop: a law that
stays a lesson keeps recurring, a law that becomes a callable stops.

The second family of pins covers `gateway restart`, which the same incident proved is a
KILL-ONLY lever in two separate ways:
  (a) it sleeps 1.0s "to let the socket release" and then relaunches -- but the thing
      actually held is DaemonLock, TTL 120s, released only on CLEAN exit. taskkill is
      not a clean exit, so the relaunch races a corpse's lease and is refused by the
      singleton guard (exit 2). Observed verbatim in state/logs/discord-gateway.log:
        [gateway-restart 1790168499] relaunching (killed: [35432])
        [discord-in] REFUSED: another discord gateway already holds the daemon lock
  (b) it never looks at the child again, and prints "restarted" unconditionally -- a
      success message for an action that failed two seconds later.

And a third defect the incident exposed: the live production gateway is scheduler-owned
out of a DIFFERENT worktree under `run_aurora_service.py --world prod`, while restart
relaunches THIS repo's scripts/bifrost_runner_discord.py. A "successful" relaunch would
therefore start a different-world gateway from a different branch. Refusing is the only
honest answer; see learn:experiment:discord_persistent_services_must_pin_one_runtime_world.

Run:  py -m pytest tests/test_gateway_census_observer_contamination.py -v
"""
from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

GATEWAY_SCRIPT = "bifrost_runner_discord.py"


# --------------------------------------------------------------------------- fixtures
def _snap(rows):
    """rows: iterable of (pid, name, cmdline) -> a process_snapshot()-shaped dict."""
    return {
        pid: {"ppid": 1, "name": name, "cmdline": cmdline, "created": 0}
        for pid, name, cmdline in rows
    }


REAL_GATEWAY_CMD = (
    r'"C:\Users\L5\AppData\Local\Programs\Python\Python311\pythonw.exe" '
    r"C:\Users\L5\AppData\Local\AkashicAurora\worktrees\sunshine-discord-split"
    r"\scripts\run_aurora_service.py --world prod -- "
    r"C:\Users\L5\AppData\Local\AkashicAurora\worktrees\sunshine-discord-split"
    r"\scripts\bifrost_runner_discord.py"
)

# Verbatim shapes from the 2026-09-23 census, all of which were counted as gateways.
OBSERVER_BASH_CMD = (
    r'"C:\Program Files\Git\bin\bash.exe" -c "source /c/Users/L5/.claude/'
    r'shell-snapshots/snapshot.sh && cd /e/AI-Setup && grep -rn bifrost_runner_discord"'
)
OBSERVER_PY_CMD = (
    r'py -c "from core.comm import wake_seat as WS; '
    r"m='bifrost_runner_discord'; print([p for p in WS.process_snapshot()])\""
)


# ------------------------------------------------------- the shared census primitive
def _script_processes():
    """The primitive these pins are written against. Absent today -- that IS the RED."""
    from core.comm import wake_seat as WS

    fn = getattr(WS, "script_processes", None)
    if fn is None:
        pytest.fail(
            "core.comm.wake_seat.script_processes(snap, script_name, exclude_pids=...) "
            "does not exist. The gateway census is still an inline substring test in "
            "agent_cli.cmd_gateway, so every future census re-derives the same defect. "
            "The fix is a shared primitive, not another point-fix."
        )
    return fn


def test_census_finds_the_real_gateway():
    """Baseline: the honest positive must still be found, pythonw.exe and all."""
    sp = _script_processes()
    snap = _snap([(61020, "pythonw.exe", REAL_GATEWAY_CMD)])
    assert sorted(sp(snap, GATEWAY_SCRIPT)) == [61020]


def test_census_excludes_a_shell_that_merely_greps_for_it():
    """A bash.exe whose argv MENTIONS the script is not a gateway.

    This is the one that produced three phantom gateways during the incident.
    """
    sp = _script_processes()
    snap = _snap(
        [
            (61020, "pythonw.exe", REAL_GATEWAY_CMD),
            (21660, "bash.exe", OBSERVER_BASH_CMD),
            (20476, "bash.exe", OBSERVER_BASH_CMD),
            (18260, "bash.exe", OBSERVER_BASH_CMD),
        ]
    )
    assert sorted(sp(snap, GATEWAY_SCRIPT)) == [61020], (
        "a shell that greps for the gateway was counted as a gateway"
    )


def test_census_excludes_a_python_that_only_mentions_it_in_a_c_program():
    """A python interpreter is necessary but not sufficient -- the script must be an
    argv TOKEN, not a substring of one. `py -c "...name..."` is not a gateway."""
    sp = _script_processes()
    snap = _snap(
        [
            (61020, "pythonw.exe", REAL_GATEWAY_CMD),
            (51952, "py.exe", OBSERVER_PY_CMD),
        ]
    )
    assert sorted(sp(snap, GATEWAY_SCRIPT)) == [61020], (
        "an interpreter running a -c program that names the script was counted"
    )


def test_census_excludes_the_observer_itself():
    """`status` has no self-exclusion at all today (restart has one; status does not).

    A census must never count the process running it, even when that process is a
    genuine python interpreter that legitimately names the script.
    """
    sp = _script_processes()
    me = os.getpid()
    snap = _snap(
        [
            (61020, "pythonw.exe", REAL_GATEWAY_CMD),
            (me, "python.exe", f"python.exe agent_cli.py gateway status {GATEWAY_SCRIPT}"),
        ]
    )
    assert me not in sp(snap, GATEWAY_SCRIPT, exclude_pids={me}), (
        "the census counted the process performing the census"
    )


def test_census_never_reports_absence_it_could_not_measure():
    """T176 at a door: a failed measurement must not read as 'there are none'.

    process_snapshot() returns None on ANY failure. cmd_gateway does `(snap or {})`,
    silently converting "I could not look" into "nothing is there" -- and then prints
    NOT RUNNING, which an operator reads as a measured verdict.
    """
    sp = _script_processes()
    with pytest.raises(Exception):
        sp(None, GATEWAY_SCRIPT)


# --------------------------------------------------------------- `gateway restart`
def _restart_source() -> str:
    import agent_cli

    return inspect.getsource(agent_cli.cmd_gateway)


def test_restart_waits_for_the_daemon_lease_not_a_fixed_socket_sleep():
    """The contended resource is DaemonLock (TTL 120s, released only on clean exit),
    not the socket. A 1-second sleep races the corpse's lease and loses."""
    src = _restart_source()
    assert "daemon" in src.lower() and (
        "lease" in src.lower() or "DaemonLock" in src or "bifrost:daemon:" in src
    ), (
        "restart still does not consult the daemon lock before relaunching; it sleeps a "
        "fixed interval sized for a socket and is refused by the singleton guard"
    )


def test_restart_verifies_the_child_survived_before_claiming_success():
    """The incident printed '[gateway] restarted' for a child that exited 2 two seconds
    later. A supervisor's report must be about the SERVICE, not about its own Popen."""
    src = _restart_source()
    tail = src.split("Popen", 1)[-1]
    assert any(tok in tail for tok in ("poll(", "returncode", "verify", "confirm")), (
        "restart prints success without ever looking at the child again"
    )


def test_restart_refuses_to_relaunch_a_gateway_it_does_not_own():
    """Production runs from another worktree under `run_aurora_service.py --world prod`.
    Relaunching THIS repo's runner would start a different-world, different-branch
    gateway. Refuse and name the owner instead."""
    src = _restart_source()
    assert "world" in src.lower() or "foreign" in src.lower() or "scheduler" in src.lower(), (
        "restart relaunches this repo's runner regardless of where the live gateway "
        "actually runs from -- a cross-world resuscitation with no refusal path"
    )
