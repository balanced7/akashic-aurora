"""sitecustomize -- no console windows, for EVERY python process in this tree.

WHY THIS FILE EXISTS AND tests/conftest.py WAS NOT ENOUGH
--------------------------------------------------------
conftest.py patches subprocess.Popen inside the PYTEST process, which covers the children a
test spawns directly. It cannot cover GRANDCHILDREN, and that is where the remaining flashing
came from. Measured 2026-08-01:

    tests spawn scripts/mirror.py 17 times          <- patched by conftest, no window
    scripts/mirror.py itself spawns git 3 times     <- NOT patched: its own process never
                                                       imported conftest, so every git.exe
                                                       got a console window

git.exe, py.exe and cmd.exe are all CONSOLE subsystem binaries: when a parent has no console
of its own, Windows hands each child a brand-new window, and a new window takes focus. One
suite run therefore strobed the desktop dozens of times -- enough to alt-tab someone out of a
full-screen game.

Python imports `sitecustomize` automatically at interpreter startup for any process that can
find it on sys.path. PYTHONPATH is an ENVIRONMENT variable, so it is inherited transitively:
child, grandchild, great-grandchild. Putting the patch here and naming THIS DIRECTORY on
PYTHONPATH is therefore the only placement that reaches arbitrarily deep spawn chains without
every author remembering to opt in -- the same reasoning conftest.py already gives for fixing
the suite in one place rather than in 35 files, carried one level further out.

The directory is deliberately DEDICATED and holds only this file. Naming the repo root instead
would put every top-level module in the tree on the import path of every process that inherits
the env -- a shadowing hazard accepted in exchange for a cosmetic fix, which is a bad trade.

WHAT IT DOES NOT DO
-------------------
It does not silence a console this process was BORN with. A terminal you launched pytest from
keeps its window, correctly. It also cannot suppress the window of the top-level process
itself, because that window is created by whoever spawned it, before any Python runs.

ESCAPE HATCH: AKASHIC_SHOW_CONSOLES=1 restores visible windows for debugging a child that
dies before it can log anything. tests/conftest.py honours AKASHIC_TEST_SHOW_CONSOLES for the
suite specifically; either one turns the windows back on.
"""
import os
import sys

if sys.platform == "win32" and not (os.environ.get("AKASHIC_SHOW_CONSOLES")
                                    or os.environ.get("AKASHIC_TEST_SHOW_CONSOLES")):
    try:
        import subprocess as _sp

        # Idempotent: a grandchild inherits PYTHONPATH and imports this file again. Patching a
        # patched Popen would nest wrappers on every generation of a deep spawn chain.
        if not getattr(_sp.Popen.__init__, "_akashic_quiet", False):
            _NO_WINDOW = getattr(_sp, "CREATE_NO_WINDOW", 0x08000000)
            _NEW_CONSOLE = getattr(_sp, "CREATE_NEW_CONSOLE", 0x00000010)
            _DETACHED = getattr(_sp, "DETACHED_PROCESS", 0x00000008)
            # Respect an explicit opinion, whichever way it points:
            #   CREATE_NEW_CONSOLE -> the caller WANTS a window; never override intent.
            #   DETACHED_PROCESS   -> already console-less, AND mutually exclusive with
            #                         CREATE_NO_WINDOW in Win32 (ERROR_INVALID_PARAMETER),
            #                         so adding it would break the spawn outright.
            #   CREATE_NO_WINDOW   -> already correct.
            _INTENT = _NEW_CONSOLE | _DETACHED | _NO_WINDOW

            _orig = _sp.Popen.__init__
            _QUIET_DIR = os.path.dirname(os.path.abspath(__file__))

            def _already_listed(value, entries):
                """Compare PATHS, not STRINGS. The same directory arrives in different
                spellings -- settings.json writes forward slashes, os.path.join writes
                backslashes, and Windows is case-insensitive besides. A raw string compare
                treats those as distinct and appends a duplicate at EVERY generation of a
                spawn chain, so a deep chain grows PYTHONPATH without bound. Measured: two
                spellings of one directory already present after a single hop."""
                try:
                    want = os.path.normcase(os.path.normpath(value))
                    return any(os.path.normcase(os.path.normpath(e)) == want
                               for e in entries if e)
                except Exception:
                    return value in entries

            def _carry_pythonpath(env):
                """Keep the chain alive across an env-REPLACING spawn.

                Inheritance covers the common case, but `subprocess.run(..., env=...)` builds a
                fresh environment and silently drops PYTHONPATH -- so that child never imports
                this file, and every process below it flashes again. launcher.py and several
                runners pass an explicit env, so this is a real path, not a hypothetical.
                """
                if env is None:
                    return None
                try:
                    cur = env.get("PYTHONPATH", "")
                    if not _already_listed(_QUIET_DIR, cur.split(os.pathsep)):
                        env = dict(env)
                        env["PYTHONPATH"] = (_QUIET_DIR + os.pathsep + cur) if cur else _QUIET_DIR
                except Exception:
                    pass
                return env

            def _quiet_init(self, *args, **kwargs):
                flags = kwargs.get("creationflags", 0)
                if not flags & _INTENT:
                    kwargs["creationflags"] = flags | _NO_WINDOW
                if "env" in kwargs:
                    kwargs["env"] = _carry_pythonpath(kwargs["env"])
                return _orig(self, *args, **kwargs)

            _quiet_init._akashic_quiet = True
            _sp.Popen.__init__ = _quiet_init

            def _dedup(entries):
                """First occurrence of each distinct PATH wins; order preserved.

                Self-healing on purpose. Avoiding NEW duplicates is not enough: an env that
                already carries two spellings of one directory (which is exactly how this was
                found -- settings.json's forward slashes alongside os.path.join's backslashes)
                hands that pair to every descendant forever. Cleaning as we pass it on means a
                chain converges instead of carrying the wart down. Entries are never dropped,
                only de-duplicated, so nothing a caller put there is lost."""
                out, seen = [], set()
                for e in entries:
                    if not e.strip():
                        continue
                    try:
                        key = os.path.normcase(os.path.normpath(e))
                    except Exception:
                        key = e
                    if key not in seen:
                        seen.add(key)
                        out.append(e)
                return out

            # And for plain inherited spawns: make sure OUR OWN env names the dir, so a child
            # that inherits (the common case) finds this file without anyone passing anything.
            _cur = os.environ.get("PYTHONPATH", "")
            _entries = _dedup(_cur.split(os.pathsep))
            if not _already_listed(_QUIET_DIR, _entries):
                _entries.insert(0, _QUIET_DIR)
            os.environ["PYTHONPATH"] = os.pathsep.join(_entries)
    except Exception:
        # NEVER break interpreter startup. A missed window is cosmetic; a sitecustomize that
        # raises takes down every python process in the tree, including the ones that would
        # tell you why.
        pass
