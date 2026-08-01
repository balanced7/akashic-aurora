"""No console windows -- and specifically, none from GRANDCHILDREN.

WHY THIS PIN EXISTS AT ALL
--------------------------
The console-spam class was fixed once already (2026-07-25, lesson
windows_console_spam_is_mostly_the_hooks_not_the_tests) at three layers: pyw for the hooks,
a Popen patch in tests/conftest.py, and CREATE_NO_WINDOW in core/comm/launcher.py. All three
are still in place and all three are correct. The windows kept flashing anyway, and it went
unnoticed because NOTHING PINNED THE PROPERTY -- the fix was believed rather than measured.

The gap, measured 2026-08-01: conftest.py patches Popen inside the PYTEST process, so it
covers what a test spawns DIRECTLY and nothing deeper.

    tests spawn scripts/mirror.py  x17     -> silenced by conftest
    mirror.py itself spawns git    x3      -> NOT silenced: that process never imported
                                              conftest, so every git.exe got a window

git.exe, py.exe and cmd.exe are CONSOLE-subsystem binaries: a parent with no console of its
own makes Windows hand each child a fresh window, and a fresh window takes focus. Dozens per
suite run is enough to alt-tab someone out of a full-screen game, which is how it was
reported.

The fix is sitecustomize.py at the repo root plus the repo root on PYTHONPATH. PYTHONPATH is
an ENVIRONMENT variable, so it is inherited transitively and every descendant at any depth
auto-imports the patch. These pins hold that property at the depth that actually broke.
"""
from __future__ import annotations

import os
import subprocess
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIN_ONLY = pytest.mark.skipif(sys.platform != "win32",
                              reason="console windows are a Windows-only phenomenon")

_PROBE = (
    "import subprocess,sys;"
    "print(getattr(subprocess.Popen.__init__,'_akashic_quiet',False))"
)


def _run(code_or_args, env=None):
    return subprocess.run(code_or_args, capture_output=True, text=True, cwd=ROOT,
                          env=env, stdin=subprocess.DEVNULL, close_fds=True, timeout=90)


@WIN_ONLY
def test_c1_sitecustomize_exists_and_is_importable_from_the_repo_root():
    """The mechanism's foundation: a file Python auto-imports at interpreter startup."""
    assert os.path.exists(os.path.join(ROOT, "scripts", "quiet", "sitecustomize.py")), (
        "sitecustomize.py is missing from the repo root -- grandchildren lose the no-window "
        "patch entirely and the flashing returns")


@WIN_ONLY
def test_c2_conftest_exports_the_repo_root_on_pythonpath():
    """Without this, sitecustomize is never found by a child and the chain breaks at depth 1.

    Asserted on the LIVE env rather than by reading conftest's source: this file's own import
    proves conftest already ran, so the variable must be set right now.
    """
    quiet = os.path.join(ROOT, "scripts", "quiet")
    pp = os.environ.get("PYTHONPATH", "")
    assert quiet in pp.split(os.pathsep), (
        f"scripts/quiet not on PYTHONPATH ({pp!r}) -- descendants cannot find sitecustomize")


@WIN_ONLY
def test_c3_the_patch_is_active_in_a_direct_child():
    r = _run([sys.executable, "-c", _PROBE])
    assert r.stdout.strip() == "True", f"child unpatched: {r.stdout!r} / {r.stderr[:200]!r}"


@WIN_ONLY
def test_c4_the_patch_is_active_in_a_GRANDCHILD():
    """THE LOAD-BEARING PIN. This is the exact depth conftest cannot reach and the depth the
    real offender (mirror.py -> git) lives at."""
    chain = (
        "import subprocess,sys;"
        f"r=subprocess.run([sys.executable,'-c',{_PROBE!r}],capture_output=True,text=True);"
        "print(r.stdout.strip())"
    )
    r = _run([sys.executable, "-c", chain])
    assert r.stdout.strip() == "True", (
        f"GRANDCHILD unpatched -- every spawn it makes opens a console window. "
        f"got {r.stdout!r} / {r.stderr[:200]!r}")


@WIN_ONLY
def test_c5_grandchild_output_is_not_swallowed():
    """The silent-death trap, pinned. CREATE_NO_WINDOW must suppress the WINDOW and nothing
    else: a child whose stdout vanishes is far worse than a visible console, because it fails
    invisibly. (The corpus already records this trap for pythonw with unredirected stdout.)"""
    chain = (
        "import subprocess,sys;"
        "r=subprocess.run([sys.executable,'-c','print(\"GRANDCHILD_SPOKE\")'],"
        "capture_output=True,text=True);"
        "print(r.returncode, r.stdout.strip(), repr(r.stderr[:80]))"
    )
    r = _run([sys.executable, "-c", chain])
    assert "GRANDCHILD_SPOKE" in r.stdout, f"grandchild stdout lost: {r.stdout!r}"
    assert r.stdout.strip().startswith("0 "), f"grandchild did not exit 0: {r.stdout!r}"


@WIN_ONLY
def test_c6_escape_hatch_restores_windows_for_debugging():
    """A child that dies before it can log must still be watchable. A silencer with no off
    switch is how a debuggable failure becomes an undebuggable one."""
    env = dict(os.environ, AKASHIC_SHOW_CONSOLES="1")
    r = _run([sys.executable, "-c", _PROBE], env=env)
    assert r.stdout.strip() == "False", (
        f"AKASHIC_SHOW_CONSOLES=1 did not restore visible windows: {r.stdout!r}")


@WIN_ONLY
def test_c8_pythonpath_does_not_grow_across_generations():
    """Found live while wiring this: the directory was already listed TWICE -- once with
    backslashes (os.path.join) and once with forward slashes (settings.json). A raw string
    compare treats those as different entries and appends one more at EVERY hop, so a deep
    spawn chain would grow PYTHONPATH without bound. Dedup now compares normalised PATHS.

    Asserts on DISTINCT NORMALISED entries rather than raw count, so the pre-existing
    two-spelling state does not mask a genuine regression.
    """
    chain = (
        "import subprocess,sys,os;"
        "r=subprocess.run([sys.executable,'-c',"
        "\"import os;print(os.environ.get('PYTHONPATH',''))\"],"
        "capture_output=True,text=True);"
        "print(r.stdout.strip())"
    )
    r = _run([sys.executable, "-c", chain])
    entries = [e for e in r.stdout.strip().split(os.pathsep) if e.strip()]
    norm = [os.path.normcase(os.path.normpath(e)) for e in entries]
    assert len(norm) == len(set(norm)), (
        f"PYTHONPATH accumulated duplicate entries across a spawn chain: {entries}")


@WIN_ONLY
def test_c7_explicit_console_intent_is_never_overridden():
    """CREATE_NEW_CONSOLE means the caller WANTS a window; DETACHED_PROCESS is mutually
    exclusive with CREATE_NO_WINDOW in Win32 (ERROR_INVALID_PARAMETER), so blindly OR-ing the
    flag would not merely be rude, it would break the spawn."""
    probe = (
        "import subprocess,sys\n"
        "seen={}\n"
        "orig=subprocess.Popen.__init__\n"
        "def cap(self,*a,**k):\n"
        "    seen['f']=k.get('creationflags',0)\n"
        "    raise SystemExit(0)\n"
        "subprocess.Popen.__init__=cap\n"
        "try:\n"
        "    subprocess.Popen([sys.executable,'-c','pass'],"
        "creationflags=subprocess.DETACHED_PROCESS)\n"
        "except SystemExit:\n"
        "    pass\n"
        "print(seen['f'] & subprocess.CREATE_NO_WINDOW)\n"
    )
    r = _run([sys.executable, "-c", probe])
    assert r.stdout.strip() == "0", (
        f"DETACHED_PROCESS got CREATE_NO_WINDOW OR-ed in -- that combination fails the spawn "
        f"outright in Win32. got {r.stdout!r} / {r.stderr[:200]!r}")
