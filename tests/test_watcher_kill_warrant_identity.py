"""The kill warrant is a substring test, so anything that TALKS about watchers is one.

wake_seat.is_watcher() gates the only live-process kill left in the wake protocol
(scripts/bifrost_wake.py:600, the K6 legacy-seat migration):

    if pid in snap and wake_seat.is_watcher(pid, snap):
        wake_seat.taskkill(pid)

Its docstring states the exact property it is there to provide -- "Identity check: the
pid is OUR kind of process (never judge a recycled pid)" -- and its body is:

    return "bifrost_wake" in (snap.get(pid, {}).get("cmdline") or "")

MEASURED on the live host, 2026-09-23: that predicate accepted TWELVE processes. Two
were real watchers. The other ten were six bash shells and four python one-liners --
every one of them a shell that merely NAMED bifrost_wake while investigating it. Shape
matching on the same snapshot returned exactly 2 (plus 2 of sol's codex_bifrost_wake
variant).

So the recycled-pid guard fails precisely in the scenario it exists for: the pid comes
out of a stale seat file, Windows recycles it onto an unrelated process, and any shell
in the middle of DIAGNOSING the wake system satisfies the warrant and is killed.

This also refutes the attractive fix for the same file's other open rung. A census of
this repo proposed closing watcher_state's pid-only probe by wiring in is_watcher(),
"a one-line change" -- which would have handed any_armed twelve armed watchers and made
reachable() answer True for every session forever. The neighbouring predicate has the
same defect; borrowing it would have rebuilt the original outage while looking like a
repair. A fix that passes for the wrong reason certifies nothing.

The remedy is the primitive already landed for the gateway census (ddf88661):
wake_seat.script_processes -- interpreter kind + exact argv-TOKEN basename + observer
excluded. Same law, same callable, second door.

Run:  py -m pytest tests/test_watcher_kill_warrant_identity.py -v
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))

from core.comm import wake_seat as WS


def _snap(rows):
    return {
        pid: {"ppid": 1, "name": name, "cmdline": cmdline, "created": 0}
        for pid, name, cmdline in rows
    }


# Verbatim shapes from the live host on 2026-09-23.
REAL_WATCHER = (
    r"C:\Users\L5\AppData\Local\Programs\Python\Python311\python.exe "
    r"E:\AI-Setup\scripts\bifrost_wake.py --agent claude --session c097980f"
)
REAL_WATCHER_PYW = (
    r"C:\Users\L5\AppData\Local\Programs\Python\Python311\pythonw.exe "
    r"E:\AI-Setup\scripts\bifrost_wake.py --agent claude --session bee0f118"
)
CODEX_WATCHER = (
    r"C:\WINDOWS\py.exe -3.11 scripts\codex_bifrost_wake.py --agent sol "
    r"--allow-from claude --allow-from dsh_agent"
)
DIAGNOSING_SHELL = (
    r'"C:\Program Files\Git\bin\bash.exe" -c "source /c/Users/L5/.claude/'
    r'shell-snapshots/snapshot.sh && cd /e/AI-Setup && '
    r'grep -rn is_watcher scripts/bifrost_wake.py"'
)
DIAGNOSING_PY = (
    r'C:\WINDOWS\py.exe -c "from core.comm import wake_seat as WS; '
    r"print([p for p in WS.process_snapshot() if 'bifrost_wake' in p])\""
)


def test_a_real_watcher_is_still_a_watcher():
    """Baseline. Tightening the warrant must not stop recognising the real thing."""
    snap = _snap([(65860, "python.exe", REAL_WATCHER)])
    assert WS.is_watcher(65860, snap) is True


def test_a_windowless_watcher_is_still_a_watcher():
    snap = _snap([(63804, "pythonw.exe", REAL_WATCHER_PYW)])
    assert WS.is_watcher(63804, snap) is True


def test_the_codex_watcher_variant_is_still_a_watcher():
    """sol's watcher is a different script and a legitimate watcher kind. A basename
    match against bifrost_wake.py alone would silently stop recognising it."""
    snap = _snap([(55332, "python.exe", CODEX_WATCHER)])
    assert WS.is_watcher(55332, snap) is True


def test_a_shell_diagnosing_the_wake_system_is_not_a_kill_target():
    """THE HAZARD. A recycled pid landing on a shell that merely names bifrost_wake
    currently satisfies the kill warrant."""
    snap = _snap([(63776, "bash.exe", DIAGNOSING_SHELL)])
    assert WS.is_watcher(63776, snap) is False, (
        "a bash shell grepping for is_watcher satisfied the kill warrant"
    )


def test_a_python_one_liner_about_watchers_is_not_a_kill_target():
    snap = _snap([(58456, "py.exe", DIAGNOSING_PY)])
    assert WS.is_watcher(58456, snap) is False, (
        "a python -c program that prints watcher pids satisfied the kill warrant"
    )


def test_an_unknown_pid_is_not_a_kill_target():
    """Absence of evidence is not a warrant."""
    assert WS.is_watcher(999999, _snap([(1, "python.exe", REAL_WATCHER)])) is False


def test_an_empty_cmdline_is_not_a_kill_target():
    """A process whose command line could not be read is unproven, not convicted."""
    snap = _snap([(4242, "python.exe", "")])
    assert WS.is_watcher(4242, snap) is False


def test_the_live_ratio_is_the_regression_this_pin_exists_for():
    """One snapshot holding both kinds: only the two real watchers may be warrants."""
    snap = _snap(
        [
            (65860, "python.exe", REAL_WATCHER),
            (63804, "pythonw.exe", REAL_WATCHER_PYW),
            (55332, "python.exe", CODEX_WATCHER),
            (63776, "bash.exe", DIAGNOSING_SHELL),
            (61232, "bash.exe", DIAGNOSING_SHELL),
            (60136, "bash.exe", DIAGNOSING_SHELL),
            (58456, "py.exe", DIAGNOSING_PY),
        ]
    )
    warranted = sorted(p for p in snap if WS.is_watcher(p, snap))
    assert warranted == [55332, 63804, 65860], (
        f"kill warrant granted over {warranted}; only the three watchers qualify"
    )
