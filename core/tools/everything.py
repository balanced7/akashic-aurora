"""core/tools/everything.py -- the Search Everything (voidtools) search seam.

``find`` verb's search half: locate a file BY NAME anywhere on the machine, using
voidtools' Everything index — the index that already found tonight's lost Discord
attachment at ``C:\\Users\\L5\\AppData\\Local\\AkashicAurora\\worktrees\\sunshine-discord-split\\state\\inbound-media``
when every project-scoped search came up empty.

WHY THIS EXISTS, in one sentence: the house scans files inside ``E:\\AI-Setup``; a
conversation or attachment that lands in a stale worktree (or anywhere outside the
project root) is INVISIBLE to every existing read verb. Everything indexes ALL of
``C:\\Users\\L5\\`` in the background, so one name lookup answers "where is this file
REALLY" in milliseconds — the exact question that cost a whole session on 2026-09-23.

MECHANISM: Everything ships a CLI, ``es.exe`` (the "Everything command-line interface"
installed alongside ``Everything.exe``). No API key, no service to start — ``es.exe
<query>`` prints one full path per line. We shell to it. There is no Everything SDK
dependency in this module on purpose: ``es.exe`` is the stable, boring interface, and
the alternative (the Everything IPC SDK / HTTP server) needs a running Everything
service and a configured port.

FAIL-SOFT: if ``es.exe`` is missing (Everything not installed, or the CLI not added to
PATH), search() returns a RESULT object that says ``available=False`` with the reason,
never a KeyError-style crash — the tier must REFUSE, not return a false "no results"
the way a bare empty list would.

The seat-facing contract is ``SearchResult``: (``paths``, ``query``, ``ok``,
``error``). ``ok`` is True only when we actually asked Everything and it answered;
``ok=False`` + empty ``paths`` means WE failed to search (not "there is no such
file") — the distinction a silent empty list would destroy.
"""
from __future__ import annotations

import fnmatch
import os
import shutil
import subprocess
import time
from dataclasses import dataclass, field
from typing import List, Optional

#: Everything's own suggested install roots (checked when it is not on PATH).
#: es.exe lives next to Everything.exe; if the user installed to a non-default dir
#: we still accept it via $PATH or the ES_EXE override.
_EVERYTHING_ROOTS = (
    # %LOCALAPPDATA%\Everything FIRST: es.exe is a SEPARATE voidtools download from the
    # Everything app, so it does not appear beside Everything.exe unless someone put it there.
    # Installing it here needs no admin and leaves the vendor's Program Files directory alone.
    os.path.join(os.environ.get("LOCALAPPDATA", ""), "Everything"),
    r"C:\Program Files\Everything",
    r"C:\Program Files (x86)\Everything",
    r"C:\Tools\Everything",
)


@dataclass
class SearchResult:
    query: str
    paths: List[str] = field(default_factory=list)
    ok: bool = False
    error: Optional[str] = None
    #: WHICH ENGINE ANSWERED. "everything" is the indexed whole-machine answer;
    #: "walk" is the bounded fallback. A caller that cannot tell them apart will read a
    #: bounded miss as machine-wide absence, which is the failure this whole module exists
    #: to prevent one layer down.
    engine: str = ""
    #: False when a budget (time or directory count) stopped the search early. An
    #: empty, NON-exhaustive result means "not found in what we managed to look at",
    #: never "not on this machine".
    exhaustive: bool = True
    scanned_dirs: int = 0
    roots: List[str] = field(default_factory=list)
    elapsed_s: float = 0.0

    @property
    def count(self) -> int:
        return len(self.paths)


def resolve_es() -> Optional[str]:
    """Return the full path to ``es.exe``, or None if it cannot be found.

    Order: an explicit ``ES_EXE`` env override (for a non-default install), then
    PATH (``shutil.which``), then the three default install roots. Never raises.
    """
    import os

    override = os.environ.get("ES_EXE")
    if override and shutil.which(override) is None:
        # ES_EXE may be an absolute path, not a bare name on PATH.
        if __import__("os").path.isfile(override):
            return override
    from_path = shutil.which("es") or shutil.which("es.exe") or (override and shutil.which(override))
    if from_path:
        return from_path
    for root in _EVERYTHING_ROOTS:
        candidate = __import__("os").path.join(root, "es.exe")
        if __import__("os").path.isfile(candidate):
            return candidate
    return None



#: Roots the fallback walks, in order. Deliberately NOT bare ``C:\\``: a full-volume walk
#: on Windows spends its entire budget in WinSxS and package caches and never reaches the
#: places software actually installs to.
_WALK_ROOTS = (
    os.environ.get("LOCALAPPDATA") or r"C:\Users\Default\AppData\Local",
    os.environ.get("APPDATA") or "",
    os.environ.get("USERPROFILE") or "",
    os.environ.get("ProgramFiles") or r"C:\Program Files",
    os.environ.get("ProgramFiles(x86)") or r"C:\Program Files (x86)",
    r"C:\Tools",
    r"C:\ffmpeg",
)

#: Directories with enormous fan-out and near-zero chance of holding a program a human
#: installed. Skipped by name at any depth. Each one is a budget sink, not a hiding place.
_WALK_SKIP = frozenset({
    "winsxs", "$recycle.bin", "system volume information", "node_modules",
    ".git", "__pycache__", "packages", "servicing", "installer", "assembly",
})



def _rank_exact_first(paths, needle):
    """Exact basename matches first, for EVERY engine.

    Substring matching is Everything's own default and we keep it -- dropping it would lose
    real hits -- but unranked it buries the answer. Searching `es.exe` on this machine returns
    Cities.exe, WhoUses.exe, SetupAsusServices.exe and RemoveLicenses.exe, each of which
    genuinely contains the literal "es.exe". A reader skimming the first line of that list
    learns the opposite of the truth.

    This lives OUTSIDE walk_search on purpose. The first version of it was inside, so the
    bounded walk was ranked and the indexed path -- the one people will actually use -- was
    not. Fixing the instance and leaving the class open is the recurring defect of this
    session; a shared helper is the version that cannot drift apart.
    """
    base = os.path.basename(str(needle or "").strip().lower())
    return sorted(paths, key=lambda p: (os.path.basename(p).lower() != base, len(p)))


def walk_search(query: str, *, max_results: int = 200, match_path: bool = False,
                roots=None, budget_s: float = 25.0,
                max_dirs: int = 400_000) -> SearchResult:
    """The engine this module has when Everything is not installed.

    Everything is an INDEX; this is a walk. It is slower and it is bounded, and both of
    those facts are reported rather than hidden -- an empty bounded search is not an
    absence, and a caller told only "0 results" would conclude the file is not on the
    machine. That is the same mistake the search half of the web door was making the day
    this was written: reporting a wall as an empty world.

    Matching mirrors Everything's default: a bare term is a case-insensitive SUBSTRING of
    the file name. A term containing * or ? is treated as a glob instead.
    """
    q = (query or "").strip()
    if not q:
        return SearchResult(query=query or "", ok=False, error="empty query", engine="walk")

    is_glob = any(ch in q for ch in "*?")
    needle = q.lower()
    started = time.monotonic()
    seen_roots, hits, scanned = [], [], 0
    visited = set()
    exhaustive = True

    for root in (roots if roots is not None else _WALK_ROOTS):
        if not root or not os.path.isdir(root):
            continue
        seen_roots.append(root)
        for dirpath, dirnames, filenames in os.walk(root, topdown=True, onerror=lambda e: None):
            if time.monotonic() - started > budget_s or scanned >= max_dirs:
                exhaustive = False
                break
            # Do not descend twice into the same real directory (junctions/symlinks on
            # Windows make USERPROFILE and LOCALAPPDATA overlap constantly).
            try:
                key = os.path.normcase(os.path.realpath(dirpath))
            except OSError:
                key = os.path.normcase(dirpath)
            if key in visited:
                dirnames[:] = []
                continue
            visited.add(key)
            scanned += 1
            dirnames[:] = [d for d in dirnames if d.lower() not in _WALK_SKIP]
            for name in filenames:
                hay = os.path.join(dirpath, name) if match_path else name
                hay_l = hay.lower()
                ok = fnmatch.fnmatch(hay_l, needle) if is_glob else (needle in hay_l)
                if ok:
                    hits.append(os.path.join(dirpath, name))
                    if len(hits) >= max_results:
                        exhaustive = False
                        break
            if len(hits) >= max_results:
                break
        if len(hits) >= max_results or not exhaustive:
            break

    hits = _rank_exact_first(hits, needle)

    return SearchResult(query=q, paths=hits, ok=True, engine="walk",
                        exhaustive=exhaustive, scanned_dirs=scanned,
                        roots=seen_roots, elapsed_s=round(time.monotonic() - started, 2))


def search(query: str, *,
           max_results: int = 200,
           match_path: bool = False,
           sort_by_name: bool = True,
           timeout: float = 15.0) -> SearchResult:
    """Search the Everything index for ``query`` and return full paths.

    ``query`` is an Everything search — a bare word matches any substring of a file
    or folder name (case-insensitive). Wrap in spaces/wildcards for Everything's
    full syntax; we keep it boring: pass it through verbatim, no injection risk
    because we use a list argv, never a shell string.

    max_results caps output (default 200). match_path adds ``-path`` so the query is
    matched against the full path, not just the name. sort_by_name adds ``-s``, which ES sorts by FULL PATH (the
    parameter name predates the flag's documented meaning). A zero-timeout is not permitted (empty -> default).
    """
    if not query or not query.strip():
        return SearchResult(query=query or "", ok=False, error="empty query")

    es = resolve_es()
    if es is None:
        # FALL BACK RATHER THAN REFUSE. The previous behaviour was an honest refusal --
        # it said plainly that no search had run -- but an honest refusal is still a door
        # that does not open, and on a machine without Everything this verb did not exist
        # for anybody. A bounded answer that admits its bounds beats no answer.
        return walk_search(query, max_results=max_results, match_path=match_path)

    # ES FLAG SHAPES, verified against es.exe 1.1.0.38 -h rather than assumed. Two of the three
    # flags this function used were wrong, and only one of them failed loudly:
    #   -n200   REJECTED -- "Error 6: Unknown switch". `-n` takes a SEPARATE argument.
    #   -path   ACCEPTED, WRONG MEANING. In ES, `-path <path>` restricts the search to a
    #           directory; matching the query against the full path is `-p`/`-match-path`.
    #           So match_path=True quietly searched for a folder named after the query.
    #   -s      correct, but it sorts by FULL PATH, not by name as the parameter implies.
    argv = [es, query]
    if match_path:
        argv.append("-match-path")
    if sort_by_name:
        argv.append("-s")
    # OVER-FETCH, THEN RANK, THEN TRUNCATE. es.exe applies `-n` with ITS OWN sort order, so
    # asking for exactly max_results lets the cap discard the exact-basename match before we
    # ever see it -- ranking afterwards can only reorder what survived. Measured: `es.exe`
    # with -n 4 returned WhoUses.exe / SetupAsusServices.exe / FindPackages.exe / Cities.exe
    # and the actual es.exe was not among them. Pull a wider window, rank, then cut.
    _fetch = max(int(max_results) * 10, 200)
    argv.extend(["-n", str(_fetch)])

    try:
        proc = subprocess.run(
            argv,
            capture_output=True,
            text=True,
            timeout=timeout or 15.0,
        )
    except subprocess.TimeoutExpired:
        return SearchResult(query=query, ok=False, error=f"timed out after {timeout}s")
    except OSError as e:
        return SearchResult(query=query, ok=False, error=f"spawn failed: {e}")

    if proc.returncode != 0:
        err = (proc.stderr or "").strip() or f"exit {proc.returncode}"
        return SearchResult(query=query, ok=False, error=err)

    lines = [ln.rstrip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    ranked = _rank_exact_first(lines, query)
    # `exhaustive` reports whether ES had MORE than our fetch window, not whether we trimmed
    # to max_results -- the caller asked for a page, and a page is not a bounded search.
    return SearchResult(query=query, paths=ranked[:int(max_results)], ok=True,
                        engine="everything", exhaustive=len(lines) < _fetch)


def format_result(res: SearchResult) -> str:
    """Human-readable render for the CLI/MCP door (kept out of search() so search()
    stays a pure value-returning seam)."""
    if not res.ok:
        return f"ERROR: {res.error or 'search unavailable'}"

    if res.engine == "walk":
        scope = (f"walked {res.scanned_dirs} dir(s) under {len(res.roots)} root(s) "
                 f"in {res.elapsed_s}s")
        if not res.paths:
            if res.exhaustive:
                return (f"(no matches for {res.query!r} -- the walk COMPLETED: {scope}. "
                        f"Not present under those roots.)")
            # THE LINE THAT MATTERS. A bounded miss must never read as absence.
            return (f"(no matches for {res.query!r}, but THE SEARCH WAS BOUNDED: {scope} "
                    f"and hit its budget before finishing. This is NOT evidence the file "
                    f"is absent -- raise --timeout, narrow with --path, or install "
                    f"Everything (voidtools.com) for the indexed whole-machine answer.)")
        tail = "" if res.exhaustive else "  [BOUNDED -- more may exist beyond the budget]"
        return (f"{res.count} match(es) for {res.query!r}  [engine: walk, {scope}]{tail}:"
                + "\n" + "\n".join(res.paths))

    if not res.paths:
        return f"(no matches for {res.query!r} — Everything answered, nothing found)"
    header = f"{res.count} match(es) for {res.query!r}  [engine: Everything index]:"
    return header + "\n" + "\n".join(res.paths)
