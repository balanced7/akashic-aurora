---
akashic_id: art_20260825_console-spam-suppression-for-serge_c8a21c
akashic_sha: 37ba52abbb70
schema_version: 1
status: current
type: report
date: 2026-08-25
title: console-spam-suppression-for-serge
gist: "# Killing console-window spam on Windows (the test phase, and what is really causing it) From Vandor / Daniil's fleet, for Serge's team. Eve"
visibility: fleet
body_type: markdown
seats: []
category: [recall, testing, ui]
origin: authored
settled: settled
supersedes: null
superseded: null
citations: []
created: "2026-08-25T21:27:04"
updated: "2026-08-25T21:27:04"
---
<!-- GENERATED PROJECTION of art_20260825_console-spam-suppression-for-serge_c8a21c -- DO NOT EDIT. The atom is the truth; regeneration overwrites this file. Edit through the doc verbs. -->

# console-spam-suppression-for-serge

# Killing console-window spam on Windows (the test phase, and what is really causing it)

From Vandor / Daniil's fleet, for Serge's team. Everything here is measured on our tree, not
recalled. The pins named at the bottom were re-run green tonight (8/8) before sending this.

## 0. THE FINDING THAT MATTERS MOST: fix by SPAWN RATE, not by where the complaint points

Daniil reported "the test suite strobes the desktop." We patched the tests. He reported it
STILL spammed. The tests were the MINOR source.

Count spawns per minute before patching anything:

    agent-harness hooks : 2-3 console spawns PER TOOL CALL, continuously, all day,
                          whether or not tests are running
    the test suite      : dozens per run, only while running

Our hook wiring outnumbered the entire suite by orders of magnitude. If you have
PreToolUse/PostToolUse hooks shelling out to python, that is your loudest source and it is
not the test phase at all -- the test phase just made it noticeable enough to report.

We skipped this count and it cost us a wrong first fix plus a week of believing we were done.

## 1. WHY IT HAPPENS

py.exe, git.exe and cmd.exe are CONSOLE-subsystem binaries. When the parent has no console
of its own, Windows hands every console child a BRAND NEW window -- and a new window takes
focus. That is why it alt-tabs someone out of a full-screen game.

Note the precondition: the PARENT must be console-less. Run pytest from a terminal you opened
yourself and the children inherit that console, so you see nothing. It reproduces for the
agent harness / IDE runner / scheduled task and NOT for the developer at a prompt. That
asymmetry is exactly why it survives so long unfixed, and why "works on my machine" is not
evidence here.

## 2. THE FOUR LAYERS, IN THE ORDER WE WOULD DO THEM AGAIN

### L1 -- Hooks: use `pyw`, not `py`  (biggest win, do it first)

`pyw` is the windowless launcher with the SAME version-selection semantics as `py`. Every
hook command in our settings.json became `pyw E:/AI-Setup/scripts/hooks/<name>.py`.

VERIFY BEFORE YOU SWITCH. pythonw with an unredirected stdout is a classic silent-hook-death
trap. Confirm pyw reads piped stdin and writes piped stdout/stderr, then run one real hook
and check it still returns its JSON at exit 0. Ours does. Hook CONFIG may not hot-reload --
restart the client to be certain.

### L2 -- conftest.py: patch Popen once, not in 35 files

Popen is the single chokepoint; run/call/check_output all funnel through it.

    if sys.platform == "win32" and not os.environ.get("AKASHIC_TEST_SHOW_CONSOLES"):
        import subprocess as _sp
        _NO_WINDOW   = getattr(_sp, "CREATE_NO_WINDOW",   0x08000000)
        _NEW_CONSOLE = getattr(_sp, "CREATE_NEW_CONSOLE", 0x00000010)
        _DETACHED    = getattr(_sp, "DETACHED_PROCESS",   0x00000008)
        _INTENT = _NEW_CONSOLE | _DETACHED | _NO_WINDOW

        _orig = _sp.Popen.__init__
        def _quiet(self, *a, **kw):
            flags = kw.get("creationflags", 0)
            if not flags & _INTENT:
                kw["creationflags"] = flags | _NO_WINDOW
            return _orig(self, *a, **kw)
        _sp.Popen.__init__ = _quiet

The conservative rule is load-bearing. Add the flag ONLY when the caller expressed no opinion:

  * CREATE_NEW_CONSOLE set -> the caller WANTS a window. Never override intent.
  * DETACHED_PROCESS set   -> already console-less, AND mutually exclusive with
                              CREATE_NO_WINDOW in Win32 (ERROR_INVALID_PARAMETER). OR-ing it
                              in does not merely annoy, IT BREAKS THE SPAWN.
  * CREATE_NO_WINDOW set   -> already correct, leave it.

Fix it here rather than in N test files because it is a property of running the SUITE, not of
any one test -- and because a per-file convention is the one someone forgets on file 36.

### L3 -- sitecustomize.py: the layer that actually finished it

This is the one we missed for a week. If you copy one thing, copy this.

conftest patches Popen inside the PYTEST process, so it covers what a test spawns DIRECTLY
and nothing deeper. Measured on our tree 2026-08-01:

    tests spawn scripts/mirror.py       x17   -> silenced by conftest
    mirror.py itself spawns git         x3    -> NOT silenced: that process never imported
                                                 conftest, so every git.exe got a window

Grandchildren were the remaining flash.

Python auto-imports `sitecustomize` at interpreter startup for any process that can find it
on sys.path. PYTHONPATH is an ENVIRONMENT variable, so it is inherited TRANSITIVELY: child,
grandchild, great-grandchild, arbitrary depth, with no opt-in required from any author. That
makes it the only placement that reaches a spawn chain you do not control.

Put it in a DEDICATED directory holding exactly that one file (ours: `scripts/quiet/`). Do
NOT name the repo root instead: that puts every top-level module in your tree on the import
path of every python process that inherits the env -- a shadowing hazard traded for a
cosmetic fix, which is a bad trade.

Four non-obvious properties, every one of them found by it breaking:

1. IDEMPOTENT. A grandchild inherits PYTHONPATH and imports the file AGAIN. Without a marker
   attribute (`_akashic_quiet`) you nest a wrapper on every generation of a deep chain.

2. CARRY PYTHONPATH ACROSS env-REPLACING SPAWNS. `subprocess.run(..., env={...})` builds a
   FRESH environment and silently drops PYTHONPATH. That child never imports the file and
   everything below it flashes again. This is a real path, not a hypothetical -- our launcher
   and several runners pass an explicit env. So the Popen patch must also re-inject the quiet
   dir into any `env=` kwarg it sees.

3. COMPARE PATHS, NOT STRINGS. The same directory arrives in different spellings:
   settings.json writes forward slashes, os.path.join writes backslashes, and Windows is
   case-insensitive besides. A raw string compare treats those as distinct and appends a
   duplicate at EVERY hop, so a deep chain grows PYTHONPATH WITHOUT BOUND. We found the
   directory already listed twice, live, before we normalised. Dedup on
   os.path.normcase(os.path.normpath(e)), keep first occurrence, preserve order, drop nothing.

4. NEVER RAISE. Wrap the entire body in try/except: pass. A missed window is cosmetic; a
   sitecustomize that raises takes down EVERY python process in the tree, including the ones
   that would tell you why.

### L4 -- production spawn sites

Same flag wherever your own code spawns and stdio is already piped. Ours: launcher.py spawned
every agent runner with CREATE_NEW_PROCESS_GROUP and no window flag.

## 3. ESCAPE HATCHES ARE NOT OPTIONAL

`AKASHIC_SHOW_CONSOLES=1` (everything) and `AKASHIC_TEST_SHOW_CONSOLES=1` (suite only) put the
windows back. The case you need them for is a child that dies BEFORE it can log anything --
which is precisely the case where you have nothing else to look at. A silencer with no off
switch turns a debuggable failure into an undebuggable one.

## 4. PIN IT, OR YOU WILL BELIEVE A FIX THAT IS NOT WORKING

This is the part we got wrong, and it is the most transferable thing here.

The class was "fixed" on 2026-07-25 at three layers. All three were correct. All three are
still in place. The windows kept flashing anyway for a week, and it went unnoticed because
NOTHING PINNED THE PROPERTY. The fix was believed rather than measured.

Our pins (`tests/test_no_console_windows.py`, 8 tests, green tonight):

    c1  sitecustomize.py exists where the mechanism expects it
    c2  the quiet dir is on PYTHONPATH -- asserted on the LIVE env, not by reading
        conftest's source (this file's own import proves conftest already ran)
    c3  the patch is active in a direct CHILD
    c4  the patch is active in a GRANDCHILD          <-- the load-bearing pin
    c5  grandchild stdout is NOT swallowed           <-- the silent-death trap
    c6  the escape hatch really restores windows
    c7  DETACHED_PROCESS never gets CREATE_NO_WINDOW OR-ed in
    c8  PYTHONPATH does not grow across generations

If you take only two: c4, because it is the exact depth conftest cannot reach and where the
real bug lived; and c5, because the fix for a COSMETIC problem must never create a DIAGNOSTIC
one. A child whose stdout vanishes is far worse than a visible console -- it fails invisibly.

The probe c3/c4 use is small enough to lift directly:

    _PROBE = ("import subprocess,sys;"
              "print(getattr(subprocess.Popen.__init__,'_akashic_quiet',False))")

    # c4: run a python that runs a python that reports whether the patch reached it
    chain = ("import subprocess,sys;"
             f"r=subprocess.run([sys.executable,'-c',{_PROBE!r}],capture_output=True,text=True);"
             "print(r.stdout.strip())")

## 5. IF CONSOLES KEEP COMING AFTER YOU THINK YOU STOPPED THE SOURCE

Separate lesson, learned the hard way: pausing the message bus does NOT stop an already-running
agent turn, or a separate launcher, from spawning console children. Bus pause is not
process-tree cancellation. Trace each new conhost/cmd process to its PARENT before declaring
the source stopped. We announced "paused, that is the source" and were promptly refuted by the
windows continuing.

## 6. WHAT WE WOULD DO DIFFERENTLY

Count the spawners before writing any patch. We patched where the complaint pointed, shipped,
were told it still spammed, and only then went looking for every spawn path. The count was a
five-minute job and would have ordered the entire fix correctly on the first pass.

And pin the property the day you fix it. Every layer above was right on 2026-07-25 and the
desktop still strobed on 2026-08-01. The gap between "fixed" and "measured" was the whole bug.
