"""Pin the pipe/redirect routing fix in ToolBox.run_command's SHELL_SEATS branch.

The bug (live 2026-10-13): `foo | bar` from a shell seat returned ONLY `foo`'s
output -- the `| bar` half was SILENTLY DISCARDED. Root cause: the SHELL_SEATS
branch split the command with _win_exec/shlex and ran it shell=False, so there
was no shell interpreter to understand `|`; the tokenizer turned it into a
literal token that went nowhere. (The `_win_exec` PowerShell quote fix is
orthogonal and already pinned in test_win_exec_powershell_quoting.py.)

The fix: a compound command (pipe/redirect/&&/;) is now routed through a REAL
shell interpreter -- cmd.exe /c on Windows, /bin/sh -c elsewhere -- instead of
being argv-split. This is the same interpreter the human-confirmed `shell=True`
path uses. A PLAIN command still uses the argv path (shell-less), so normal
quoting/`python -c ...` behaviour is unchanged.

These pins assert the ROUTING CONTRACT directly (the _needs_shell predicate and
the _shell_command_for shape) -- no process spawn, no ACL, so they run on any OS.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.comm import toolbox


def test_pipe_is_a_shell_command():
    assert toolbox._needs_shell("python -c 'print(1)' | find /c 1")


def test_redirect_is_a_shell_command():
    assert toolbox._needs_shell("cmd echo hi > out.txt")


def test_joiners_are_shell_commands():
    assert toolbox._needs_shell("pytest && echo done")
    assert toolbox._needs_shell("a; b")


def test_plain_command_is_not_a_shell_command():
    # No metacharacter -> stay on the argv (shell-less) path. This is the guard that
    # keeps `python -c "..."` and normal quoting from round-tripping a second shell.
    assert not toolbox._needs_shell('python -c "print(1)"')
    assert not toolbox._needs_shell("py -m pytest tests/x.py -q")
    assert not toolbox._needs_shell("git status")


def test_shell_command_for_is_a_real_interpreter():
    argv = toolbox._shell_command_for("a | b")
    if os.name == "nt":
        assert argv == ["cmd", "/c", "a | b"], argv
    else:
        assert argv == ["/bin/sh", "-c", "a | b"], argv


def test_pipe_preserved_verbatim_in_shell_argv():
    # The pipe must reach the interpreter as literal text, never re-tokenized by us.
    argv = toolbox._shell_command_for('python -c "print(\'a\\nb\\nc\')" | find /c "b"')
    assert "|" in argv[-1], argv
    assert argv[-1].startswith("python"), argv
