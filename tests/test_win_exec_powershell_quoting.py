"""Pin the Windows shell-command splitter (_win_exec) that root-causes the
2026-10-13 PowerShell quote-mangling incident.

The bug: the SHELL_SEATS branch of ToolBox.run_command split commands with
`shlex.split(command, posix=False)`, which on Windows DROPS the quotes it was
supposed to honour. A command like `powershell -Command "Get-Date"` became the
token list ['powershell', '-Command', 'Get-Date'] (quotes gone), and PowerShell,
receiving `Get-Date` as a bare `-Command` string, ECHOED it instead of running it.
Similarly `^|` (a cmd.exe pipe escape) was passed LITERALLY to PowerShell, whose
escape is the backtick, so the pipe didn't parse.

The fix (_win_exec): for a `powershell`/`cmd` invocation on Windows, hand the
interpreter a SINGLE -Command//c string -- never re-tokenize it through POSIX
shlex. The interpreter that understands PowerShell syntax receives it verbatim.

These pins assert the helper's CONTRACT directly (no process spawn, no ACL):
an `argv` list must be a hand-off to the right interpreter, with quotes and pipes
preserved, and leading invocation flags stripped rather than re-wrapped.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import toolbox


def _win(*args):
    # _win_exec is a no-op (returns None) off Windows; these pins are Windows-only
    # because the bug is Windows-only (POSIX shlex is actually correct on POSIX).
    return toolbox._win_exec(*args)


def test_powershell_quoted_command_preserves_quotes():
    argv = _win('powershell -Command "Get-Date"')
    if os.name != "nt":
        return  # helper is platform-specific; pins exercise it only on Windows
    # The -Command body must carry the quotes AND the command verbatim: this is the
    # exact case that used to DEGRADE to an echo of the bareword `Get-Date`.
    assert argv[0].lower().endswith("powershell"), argv
    assert argv[-1] == '"Get-Date"', argv


def test_powershell_pipe_is_not_reinterpreted():
    argv = _win("powershell Get-Process | Select-Object Name")
    if os.name != "nt":
        return
    # The pipe must survive as literal text for PowerShell to parse, not be split by us.
    assert "|" in argv[-1], argv
    assert argv[-1].startswith("Get-Process"), argv


def test_powershell_leading_flags_are_stripped_not_rewrapped():
    argv = _win('powershell -NoProfile -Command "Write-Output hi"')
    if os.name != "nt":
        return
    # The seat's own -NoProfile/-Command tokens must NOT become re-wrapped script text.
    assert argv[0].lower().endswith("powershell"), argv
    assert argv[1] == "-NoProfile", argv
    assert argv[2] == "-Command", argv
    assert argv[3] == '"Write-Output hi"', argv


def test_powershell_bareword_invocation_still_yields_a_script():
    argv = _win("powershell write-output hello")
    if os.name != "nt":
        return
    assert argv[-1] == "write-output hello", argv


def test_cmd_handoff_uses_c():
    argv = _win("cmd echo hello")
    if os.name != "nt":
        return
    assert argv[0].lower() in ("cmd", "cmd.exe"), argv
    assert argv[1] == "/c", argv
    assert argv[2] == "echo hello", argv


def test_non_windows_commands_fall_back_to_none():
    # A non-shell command is not our job; _win_exec must decline so the caller
    # falls back to the ordinary shlex splitter.
    assert _win("git push origin master") is None
    assert _win("py -m pytest --version") is None
