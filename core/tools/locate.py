"""core/tools/locate.py -- the plocate engine for the ``find`` verb (Linux/macOS's Everything).

WHY: off Windows, ``find`` had only the bounded walk -- 6 s per query, and it never looked
outside home, /usr/local and /opt, so it could not see /mnt/lnx-storage where the projects
live (measured 2026-10-16: 1 of 42 copies of agent_cli.py found). Everything answers the same
question from an index in milliseconds. plocate is that index on Linux: a trigram index over
every path on the machine, queried in ~10 ms for 4.2 M files on this box.

WHAT EVERYTHING HAS THAT A PLAIN plocate DOES NOT, and how this module closes each gap:

  * Freshness. Everything follows the NTFS change journal, so a new file is visible at once.
    The system plocate index is rebuilt once a day by cron, as root. This module keeps a
    SECOND, user-owned index (no root needed) and refreshes it in the background whenever a
    query finds it older than ``AKASHIC_FIND_INDEX_MAX_AGE`` seconds (default 600): the query
    answers instantly from the index it has, and the next query sees the fresh one
    (stale-while-revalidate). The answer always says how old its index is.
  * Deleted files. An index outlives the files in it. Every hit is lstat()ed before it is
    returned, so a deleted file never shows up -- and the same stat yields size and mtime, so
    every hit carries metadata (es.exe needs -add-columns for that).
  * Metadata sorts. es.exe sorts by size/date itself; here the stat above feeds the sort.

The matching grammar mirrors Everything's defaults: a bare term is a case-insensitive
substring of the NAME, several space-separated terms must ALL match, and a term with * or ?
is a glob over the whole name. --path matches the full path instead, --regex is an extended
regex, --case makes it case-sensitive.
"""

from __future__ import annotations

import os
import re
import shutil
import stat as _stat
import subprocess
import time
from datetime import UTC, datetime

from core.tools.everything import Hit, SearchResult, _basename, _rank_exact_first, is_valid_sort_key

#: The distro's own index: root-owned, read through plocate's setgid group, rebuilt daily.
SYSTEM_INDEX = "/var/lib/plocate/plocate.db"

#: Ubuntu's PRUNEPATHS minus /media and /tmp (see refresh_index). Pseudo-filesystems such as
#: /proc and /sys stay out through PRUNEFS, which this does not touch.
_PRUNE_PATHS = "/var/spool /var/lib/os-prober /var/lib/ceph /home/.ecryptfs /var/lib/schroot"


def resolve_plocate() -> str | None:
    """Full path to ``plocate``, or None. Never on Windows: es.exe is the index there."""
    if os.name == "nt":
        return None
    return shutil.which("plocate")


def user_index_path() -> str:
    """Aurora's own index. One per MACHINE, not per world: it describes the disk, which every
    world shares. ``AKASHIC_FIND_DB`` overrides the default under the XDG cache home."""
    override = (os.environ.get("AKASHIC_FIND_DB") or "").strip()
    if override:
        return os.path.expanduser(override)
    cache = (os.environ.get("XDG_CACHE_HOME") or "").strip() or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(cache, "aurora", "find", "plocate.db")


def _max_age_s() -> float:
    try:
        return float(os.environ.get("AKASHIC_FIND_INDEX_MAX_AGE") or 600)
    except ValueError:
        return 600.0


def _mtime(path: str) -> float | None:
    try:
        return os.stat(path).st_mtime
    except OSError:
        return None


def pick_index() -> tuple[str | None, float | None]:
    """The FRESHEST index on the machine: (path, built-at epoch). Path None means "plocate's
    default" (the system index) -- passed without -d so plocate's setgid read applies, since
    the system database is not readable by the user directly. (None, None) when neither exists.
    """
    user_db, sys_db = user_index_path(), SYSTEM_INDEX
    user_t, sys_t = _mtime(user_db), _mtime(sys_db)
    if user_t is not None and (sys_t is None or user_t >= sys_t):
        return user_db, user_t
    if sys_t is not None:
        return None, sys_t
    return None, None


def refresh_index(*, wait: bool = False, timeout: float = 600.0) -> str:
    """Rebuild the user-owned index. Background by default (detached, lowest CPU and IO
    priority); ``wait=True`` blocks until it is done (the ``--reindex`` flag).

    Only one rebuild runs at a time: ``flock -n`` on a lock file beside the index means a
    burst of stale queries starts one rebuild, not one each. updatedb writes a temporary file
    and renames it over the old index, so a query never reads a half-built one.

    Returns a one-line status for the caller to show."""
    updatedb = shutil.which("updatedb")
    flock = shutil.which("flock")
    if not updatedb:
        return "no updatedb on PATH (install plocate)"
    db = user_index_path()
    os.makedirs(os.path.dirname(db), exist_ok=True)
    # -l no: a user-owned index needs no visibility check (it only ever holds what this user
    # could stat while building it). -U /: the whole machine. --prunepaths REPLACES the distro's
    # list, which skips /media and /tmp: that hid a zip on a USB stick the day this was written
    # (/media/ubuntu/F571-7D02/lessons-for-simon-2026-10-14.zip), and Everything indexes
    # attached drives. A drive unplugged since the build is caught by the lstat at query time.
    argv = [updatedb, "-l", "no", "-U", "/", "-o", db, "--prunepaths", _PRUNE_PATHS]
    if flock:
        argv = [flock, "-n", db + ".lock", *argv]
    nice = [p for p in (shutil.which("nice"), shutil.which("ionice")) if p]
    if len(nice) == 2:
        argv = [nice[0], "-n", "19", nice[1], "-c", "3", *argv]
    if wait:
        started = time.monotonic()
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return f"index rebuild timed out after {timeout:.0f}s"
        except OSError as e:
            return f"index rebuild failed to start: {e}"
        if proc.returncode == 1 and flock:
            return "another index rebuild is already running"
        if proc.returncode != 0:
            return f"index rebuild failed: {(proc.stderr or '').strip() or f'exit {proc.returncode}'}"
        return f"index rebuilt in {time.monotonic() - started:.1f}s: {db}"
    try:
        subprocess.Popen(
            argv,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,  # outlives this short CLI process
        )
    except OSError as e:
        return f"index refresh failed to start: {e}"
    return "index refresh started in the background"


def _iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, tz=UTC).astimezone().isoformat(timespec="seconds")


#: es.exe sort keys this engine can honour from a stat(). Linux exposes no creation time
#: through os.stat, so date-created sorts by mtime -- said in the result's notes, not hidden.
_STAT_SORTS = {
    "name": lambda h, st: h.path.lower(),
    "path": lambda h, st: h.path.lower(),
    "size": lambda h, st: st.st_size,
    "extension": lambda h, st: (h.extension.lower(), h.path.lower()),
    "datemodified": lambda h, st: st.st_mtime,
    "datecreated": lambda h, st: st.st_mtime,
    "dateaccessed": lambda h, st: st.st_atime,
    "daterecentlychanged": lambda h, st: st.st_ctime,
}


def locate_search(
    query: str,
    *,
    match_path: bool = False,
    timeout: float = 15.0,
    sort: str = "",
    regex: bool = False,
    case: bool = False,
    whole_word: bool = False,
    dirs_only: bool = False,
    files_only: bool = False,
    scope: str | None = None,
    attributes: str | None = None,
) -> SearchResult:
    """Every match for ``query`` in the freshest plocate index, verified on disk and ranked.

    Unpaged: search_page slices the result. ``engine`` is "plocate"; ``index_age_s`` says how
    old the answering index was, and ``notes`` carries anything the caller should know
    (a refresh started, a sort that had to approximate).
    """
    started = time.monotonic()
    q = (query or "").strip()
    if not q:
        return SearchResult(query=query or "", ok=False, error="empty query", engine="plocate")
    if attributes:
        return SearchResult(
            query=q,
            ok=False,
            engine="plocate",
            error="--attrs filters Windows file attributes; it needs Everything and has no Linux meaning",
        )
    if sort and not is_valid_sort_key(sort):
        return SearchResult(query=q, ok=False, engine="plocate", error=f"unknown sort key {sort!r}")

    plocate = resolve_plocate()
    if plocate is None:
        return SearchResult(query=q, ok=False, engine="plocate", error="plocate is not installed")

    notes: list[str] = []
    db, built = pick_index()
    if built is None:
        notes.append(refresh_index())
        return SearchResult(
            query=q, ok=False, engine="plocate", error="no plocate index yet; " + notes[-1], notes=notes
        )
    age = max(time.time() - built, 0.0)
    user_t = _mtime(user_index_path())
    if user_t is None or time.time() - user_t > _max_age_s():
        notes.append(refresh_index())

    argv = [plocate, "-0"]
    if db:
        argv += ["-d", db]
    if not case:
        argv.append("-i")
    if not match_path:
        argv.append("-b")
    if regex:
        argv += ["--regex", "--", q]
    else:
        # Everything ANDs space-separated terms; so does plocate given several patterns.
        argv += ["--", *q.split()]
    try:
        proc = subprocess.run(argv, capture_output=True, timeout=timeout or 15.0)
    except subprocess.TimeoutExpired:
        return SearchResult(query=q, ok=False, engine="plocate", error=f"timed out after {timeout}s")
    except OSError as e:
        return SearchResult(query=q, ok=False, engine="plocate", error=f"spawn failed: {e}")
    # plocate exits 1 for "no matches", like grep; anything else is a real failure.
    if proc.returncode not in (0, 1):
        err = proc.stderr.decode("utf-8", "replace").strip() or f"exit {proc.returncode}"
        return SearchResult(query=q, ok=False, engine="plocate", error=err)

    raw = [p.decode("utf-8", "surrogateescape") for p in proc.stdout.split(b"\0") if p]
    word = None
    if whole_word and not regex:
        flags = 0 if case else re.IGNORECASE
        word = [re.compile(rf"(?<![0-9A-Za-z_]){re.escape(t)}(?![0-9A-Za-z_])", flags) for t in q.split()]
    scope_dir = os.path.join(os.path.abspath(os.path.expanduser(scope)), "") if scope else None

    hits: list[Hit] = []
    stats: dict[str, os.stat_result] = {}
    stale = 0
    for path in raw:
        if scope_dir and not path.startswith(scope_dir):
            continue
        if word is not None:
            hay = path if match_path else _basename(path)
            if not all(w.search(hay) for w in word):
                continue
        try:
            st = os.lstat(path)
        except OSError:
            stale += 1  # in the index, gone from the disk
            continue
        is_dir = _stat.S_ISDIR(st.st_mode)
        if (dirs_only and not is_dir) or (files_only and is_dir):
            continue
        name = _basename(path)
        ext = "" if is_dir else os.path.splitext(name)[1].lstrip(".")
        hits.append(
            Hit(
                path=path,
                name=name,
                size=None if is_dir else st.st_size,
                date_modified=_iso(st.st_mtime),
                date_accessed=_iso(st.st_atime),
                extension=ext,
                attributes="D" if is_dir else ("L" if _stat.S_ISLNK(st.st_mode) else ""),
            )
        )
        stats[path] = st
    if stale:
        notes.append(f"{stale} indexed path(s) no longer exist and were dropped")

    if sort:
        key = sort.strip().lower().replace("-", "")
        descending = key.endswith("descending")
        key = key.removesuffix("descending").removesuffix("ascending")
        by = _STAT_SORTS.get(key)
        if by is None:
            return SearchResult(
                query=q, ok=False, engine="plocate", error=f"sort {sort!r} needs Everything (no Linux equivalent)"
            )
        if key == "datecreated":
            notes.append("Linux exposes no creation time here; sorted by modification time instead")
        hits.sort(key=lambda h: by(h, stats[h.path]), reverse=descending)
    else:
        order = {p: i for i, p in enumerate(_rank_exact_first([h.path for h in hits], q))}
        hits.sort(key=lambda h: order[h.path])

    return SearchResult(
        query=q,
        paths=[h.path for h in hits],
        hits=hits,
        ok=True,
        engine="plocate",
        exhaustive=True,
        roots=[db or SYSTEM_INDEX],
        elapsed_s=round(time.monotonic() - started, 3),
        index_age_s=round(age, 1),
        notes=notes,
    )


def main(argv: list[str] | None = None) -> int:
    """The fast door: ``python -m core.tools.locate <term>...`` prints matching paths, best
    first, one per line. It exists because ``agent_cli.py find`` spends ~0.4 s starting up
    (compiling a 16k-line script, building 160 subparsers, importing the Redis client) around
    a search that takes ~5 ms; this imports only the two search modules. Status lines go to
    stderr so stdout stays a clean path list for pipes."""
    import argparse
    import sys

    p = argparse.ArgumentParser(prog="python -m core.tools.locate", description=main.__doc__)
    p.add_argument("terms", nargs="*", help="name terms; all must match (Everything's grammar)")
    p.add_argument("-p", "--path", action="store_true", help="match the full path, not just the name")
    p.add_argument("-c", "--case", action="store_true", help="case-sensitive")
    p.add_argument("-r", "--regex", action="store_true", help="extended regex")
    p.add_argument("-n", "--limit", type=int, default=0, help="print at most N paths")
    p.add_argument("--sort", default="", help="name|path|size|extension|date-modified|... (+ -descending)")
    p.add_argument("--reindex", action="store_true", help="rebuild the index now and wait")
    a = p.parse_args(argv)
    if a.reindex:
        print(refresh_index(wait=True), file=sys.stderr)
        if not a.terms:
            return 0
    if not a.terms:
        p.error("give a search term")
    res = locate_search(" ".join(a.terms), match_path=a.path, case=a.case, regex=a.regex, sort=a.sort)
    if not res.ok:
        print(f"ERROR: {res.error}", file=sys.stderr)
        return 2
    from core.tools.everything import describe_age

    paths = res.paths[: a.limit] if a.limit > 0 else res.paths
    sys.stdout.write("".join(path + "\n" for path in paths))
    print(
        f"{res.count} match(es), {describe_age(res.index_age_s)}, {res.elapsed_s * 1000:.0f}ms"
        + "".join(f"; {n}" for n in res.notes),
        file=sys.stderr,
    )
    return 0 if res.paths else 1


if __name__ == "__main__":
    raise SystemExit(main())
