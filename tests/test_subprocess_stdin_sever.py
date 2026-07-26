"""C7-4 CLASS PIN -- no child of the MCP door may inherit the JSON-RPC handle.

The failure (failure-ledger-2026-07.md C7-4): the MCP server owns stdin as its
JSON-RPC transport. A child process that inherits that handle makes Windows'
Proactor defer the pending stdout completion until the next inbound frame -- so a
tool's work runs to completion and the reply never returns. The seat hangs on boot;
any later frame flushes it in <0.07s. It cost a session on 2026-07-16.

Why this file exists. C7-4 was point-fixed on 2026-07-17 by severing stdin in
agent_cli's `_git` helper, and the ledger closed the boot path while explicitly
naming the CLASS as still open. On 2026-07-25 `_head_commit_epoch` landed on the
boot path without the sever, and on 2026-07-26 every seat -- claude and codex both
-- was hanging on boot again. Nine days. The existing P6 end-to-end pin was red and
caught it, but only ONE site had ever been fixed, and an audit found 17 more
unsevered spawns in MCP-reachable modules; each is one refactor from a verb's path.

So these pins hold the INVARIANT rather than the call sites, because "remember to
pass stdin=DEVNULL" is a hope, not a guard -- the same shape as the `_ARG_DEFAULTS`
keep-in-sync comment that test_mcp_arg_defaults_parity.py replaced:

  S1  the door's membrane is installed: a child spawned with no stdin= gets DEVNULL
  S2  explicit stdin still wins -- subprocess.run(input=...) keeps piping (the pin
      that stops S1 from silently breaking scripts/gemini_web.py and friends)
  S3  the BOOT path spawns no stdin-inheriting child, judged on what the CALLER
      passes (defence in depth: agent_cli is embeddable in other stdio doors, and
      this is the exact property that regressed twice)

Run: py -m pytest tests/test_subprocess_stdin_sever.py -q
"""
import argparse
import contextlib
import io
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)


# ------------------------------------------------------------------------- S1
def test_s1_door_severs_stdin_for_children_by_default():
    """Importing the door installs the membrane; an unspecified stdin becomes DEVNULL."""
    import ai_setup_mcp as door

    assert subprocess.Popen is door._StdinSeveredPopen, (
        "S1: the stdin membrane is not installed -- children of the MCP server would "
        "inherit the JSON-RPC transport handle (C7-4)"
    )

    # Behavioural, not just structural: the child must see EOF, not an inherited handle.
    r = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stdout.write(repr(sys.stdin.read()))"],
        capture_output=True, text=True, timeout=30,
    )
    assert r.stdout == "''", f"S1: child did not get DEVNULL stdin (got {r.stdout!r})"


# ------------------------------------------------------------------------- S2
def test_s2_explicit_stdin_and_piped_input_still_work():
    """The membrane fills a GAP; it must never override a caller that means it.

    subprocess.run(input=...) sets stdin=PIPE itself, so the door's script helpers
    (_run_script feeds prompts to scripts/gemini_web.py this way) keep working.
    """
    import ai_setup_mcp  # noqa: F401  -- installs the membrane

    r = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stdout.write(sys.stdin.read().upper())"],
        input="membrane holds", capture_output=True, text=True, timeout=30,
    )
    assert r.stdout == "MEMBRANE HOLDS", f"S2: piped input broken (got {r.stdout!r})"


# ------------------------------------------------------------------------- S3
def test_s3_boot_path_spawns_no_stdin_inheriting_child():
    """Run a real boot and judge every spawn by what the CALLER passed.

    The membrane would mask a leaky call site here (it corrects stdin on the way
    through), so the tracer records the caller's own argument before delegating.
    A violation names the exact file:line to fix -- pass stdin=subprocess.DEVNULL,
    close_fds=True, as agent_cli's `_git` helper does.
    """
    import traceback

    import agent_cli
    import ai_setup_mcp as door

    base = subprocess.Popen          # the membrane class, already installed
    leaks = []

    class _Tracer(base):
        def __init__(self, args, bufsize=-1, executable=None, stdin=None, *a, **kw):
            if stdin is None:        # the inherit case, as the CALLER wrote it
                site = "<unknown>"
                for fr in reversed(traceback.extract_stack()[:-1]):
                    f = fr.filename.replace("\\", "/")
                    if "/AI-Setup/" in f and "/subprocess.py" not in f and "/tests/" not in f:
                        site = f"{os.path.relpath(fr.filename, ROOT)}:{fr.lineno}"
                        break
                argv = args if isinstance(args, str) else " ".join(map(str, args))
                leaks.append(f"{site}  ->  {argv[:70]}")
            super().__init__(args, bufsize, executable, stdin, *a, **kw)

    ns = argparse.Namespace(**{**door._ARG_DEFAULTS,
                               "agent_id": "c7-4-class-pin",
                               "task": "S3 stdin-sever boot-path pin"})
    # Plain redirect_stdout, NOT the door's thread-local proxy: the proxy installs
    # itself as sys.stdout at import, and pytest swaps sys.stdout per test, so arming
    # it here would capture only when this test happened to run first.
    buf = io.StringIO()
    subprocess.Popen = _Tracer
    try:
        with contextlib.redirect_stdout(buf):
            agent_cli.cmd_boot(ns)
    except SystemExit:
        pass
    finally:
        subprocess.Popen = base

    assert buf.getvalue().strip(), "S3: boot rendered nothing -- the pin proved nothing"
    assert not leaks, (
        "S3: %d spawn(s) on the BOOT path inherit stdin (C7-4 -- an MCP seat's boot "
        "will hang until another frame arrives):\n  %s" % (len(leaks), "\n  ".join(leaks))
    )
