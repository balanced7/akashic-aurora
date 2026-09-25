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
import json
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
class Hit:
    """One structured search hit: the full capability of es.exe per match.

    Surfacing the WHOLE tool (Daniil 2026-09-25): es.exe exposes per-hit properties
    (-size, -date-modified, -date-created, -date-accessed, -extension, -attributes,
    -run-count) that the bare-path wrapper was discarding. This record carries them so
    the `find` verb can answer "where is the file AND how old is it AND how big", which
    is the fuel for the inventory/provenance join (mtime ↔ file_edit events).
    """
    path: str
    name: str = ""
    size: Optional[int] = None
    date_modified: str = ""
    date_created: str = ""
    date_accessed: str = ""
    extension: str = ""
    attributes: str = ""
    run_count: Optional[int] = None
    raw: Optional[dict] = None

    @property
    def mtime(self) -> str:
        """Alias so the inventory combo reads 'mtime', not es.exe's 'date-modified'."""
        return self.date_modified


@dataclass
class SearchResult:
    query: str
    paths: List[str] = field(default_factory=list)
    ok: bool = False
    error: Optional[str] = None
    #: Structured per-hit records (the full capability surface). Populated when
    #: format='json' is requested; `paths` remains the bare-path projection for
    #: backward-compatible callers and rendering.
    hits: List[Hit] = field(default_factory=list)
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


#: es.exe's -sort keys (verified against -h); the named flag surfaces these verbatim.
_SORT_KEYS = frozenset({
    "name", "path", "size", "extension", "date-created", "date-modified",
    "date-accessed", "attributes", "filelist-filename", "run-count",
    "date-recently-changed", "date-run",
})


def _build_query_flags(*, regex=False, case=False, whole_word=False, dirs_only=False,
                       files_only=False, scope=None, attributes=None):
    """Map the clean named query flags to es.exe argv (module-level so it is pinnable).

    The grammar is es.exe's own (verified 1.1.0.38 -h): regex -> -r, case -> -i,
    whole-word -> -w, dirs-only -> /ad, files-only -> /a-d, scope -> -path <dir>,
    attributes -> /a<mask>. Returns a list of argv tokens, never a shell string (list
    argv means no injection surface).
    """
    argv = []
    if regex:
        argv.append("-r")
    if case:
        argv.append("-i")
    if whole_word:
        argv.append("-w")
    if dirs_only:
        argv.append("/ad")
    if files_only:
        argv.append("/a-d")
    if scope:
        argv.append("-path")
        argv.append(str(scope))
    if attributes:
        argv.append("/a" + str(attributes))
    return argv


def _parse_json_hits(text: str) -> List[Hit]:
    """Parse es.exe -json output into structured Hit records.

    es.exe -json emits a SINGLE JSON ARRAY (verified live against 1.1.0.38), each
    element a dict with `filename` (the full path) plus whatever columns were requested
    via -add-columns / the property flags (size, date_modified, date_created,
    date_accessed, extension, attributes, run_count). Fail-soft: malformed input yields
    an empty list, never a crash -- a bad record must not sink the structured result.

    Tolerates BOTH the array form and line-delimited JSON (defensive: different es.exe
    builds have emitted both; the array form is authoritative for 1.1.0.38).
    """
    hits: List[Hit] = []
    text = (text or "").strip()
    if not text:
        return hits

    # Primary: one JSON array (the documented 1.1.0.38 shape).
    try:
        decoded = json.loads(text)
        if isinstance(decoded, list):
            for rec in decoded:
                if isinstance(rec, dict) and _record_path(rec):
                    hits.append(_hit_from_record(rec))
            return hits
        if isinstance(decoded, dict) and _record_path(decoded):
            hits.append(_hit_from_record(decoded))
            return hits
    except (ValueError, TypeError):
        pass  # not a single JSON value -> fall through to line-delimited

    # Fallback: line-delimited JSON objects (older/newer es.exe or hand-shaped output).
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except (ValueError, TypeError):
            continue
        if isinstance(rec, dict) and _record_path(rec):
            hits.append(_hit_from_record(rec))
    return hits


def _record_path(rec: dict) -> str:
    """The path field of an es.exe JSON record (key is `filename`, the only field -json
    emits unless columns are requested; tolerate the obvious aliases)."""
    return (rec.get("filename") or rec.get("full_path") or rec.get("path")
            or rec.get("name") or "")


def _hit_from_record(rec: dict) -> Hit:
    path = _record_path(rec)
    return Hit(
        path=path,
        name=rec.get("name") or os.path.basename(path),
        size=rec.get("size"),
        date_modified=rec.get("date_modified") or rec.get("dm") or "",
        date_created=rec.get("date_created") or rec.get("dc") or "",
        date_accessed=rec.get("date_accessed") or rec.get("da") or "",
        extension=rec.get("extension") or rec.get("ext") or "",
        attributes=rec.get("attributes") or rec.get("attrib") or "",
        run_count=rec.get("run_count") or rec.get("run-count"),
        raw=rec,
    )


def walk_search(query: str, *, max_results: int = None, match_path: bool = False,
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

    ``max_results`` is None/0 => no result cap (walk the whole budget); any other number
    stops after that many hits. The default is None so the bounded-and-honest walk does
    not silently page itself; the budget_s/max_dirs ceilings still apply and are reported
    via ``exhaustive``.
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
    cap = None if max_results is None or int(max_results) <= 0 else int(max_results)

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
                    if cap is not None and len(hits) >= cap:
                        exhaustive = False
                        break
            if cap is not None and len(hits) >= cap:
                break
        if (cap is not None and len(hits) >= cap) or not exhaustive:
            break

    hits = _rank_exact_first(hits, needle)

    return SearchResult(query=q, paths=hits, ok=True, engine="walk",
                        exhaustive=exhaustive, scanned_dirs=scanned,
                        roots=seen_roots, elapsed_s=round(time.monotonic() - started, 2))


def search(query: str, *,
           max_results: int = 200,
           match_path: bool = False,
           sort_by_name: bool = True,
           timeout: float = 15.0,
           sort: str = "",
           columns: Optional[List[str]] = None,
           format: str = "",
           regex: bool = False,
           case: bool = False,
           whole_word: bool = False,
           dirs_only: bool = False,
           files_only: bool = False,
           scope: Optional[str] = None,
           attributes: Optional[str] = None) -> SearchResult:
    """Search the Everything index for ``query`` and return full paths.

    ``query`` is an Everything search — a bare word matches any substring of a file
    or folder name (case-insensitive). Wrap in spaces/wildcards for Everything's
    full syntax; we keep it boring: pass it through verbatim, no injection risk
    because we use a list argv, never a shell string.

    max_results caps output (default 200). match_path adds ``-match-path`` so the query is
    matched against the full path, not just the name. sort_by_name adds ``-s``, which ES sorts by FULL PATH (the
    parameter name predates the flag's documented meaning). A zero-timeout is not permitted (empty -> default).

    FULL CAPABILITY SURFACE (Daniil 2026-09-25) — the named params that map to es.exe:
      sort:       one of _SORT_KEYS, passed to -sort (replaces -s when set)
      columns:    list of property names -> -add-columns 'p;p;...'
      format:     'json' -> -json (structured per-hit records land in result.hits)
      regex/case/whole_word/dirs_only/files_only/scope/attributes -> the query grammar.
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
    if sort:
        if sort not in _SORT_KEYS:
            return SearchResult(query=query, ok=False,
                                error=f"unknown sort key {sort!r} (allowed: {sorted(_SORT_KEYS)})")
        argv.extend(["-sort", sort])
    elif sort_by_name:
        argv.append("-s")
    if columns:
        argv.extend(["-add-columns", ";".join(columns)])
    if format == "json":
        argv.append("-json")
        argv.extend(["-date-format", "1"])  # ISO-8601 dates, parseable
        # -json alone emits ONLY `filename`; the metadata surface requires explicit columns.
        # When the caller asked for json but no columns, request the full metadata set so
        # the structured result is actually useful (the whole point of the surface).
        if not columns:
            argv.extend(["-add-columns",
                         "size;date-modified;date-created;date-accessed;extension;attributes"])
    argv.extend(_build_query_flags(
        regex=regex, case=case, whole_word=whole_word,
        dirs_only=dirs_only, files_only=files_only,
        scope=scope, attributes=attributes,
    ))
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

    if format == "json":
        parsed = _parse_json_hits(proc.stdout or "")
        base = os.path.basename(str(query or "").strip().lower())
        # rank exact-basename-first, same rule as the path form (shared intent, Hits not paths)
        parsed.sort(key=lambda h: (os.path.basename(h.path).lower() != base, len(h.path)))
        sliced = parsed[:int(max_results)]
        return SearchResult(
            query=query, paths=[h.path for h in sliced], hits=sliced,
            ok=True, engine="everything", exhaustive=len(parsed) < _fetch,
        )

    lines = [ln.rstrip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    ranked = _rank_exact_first(lines, query)
    # `exhaustive` reports whether ES had MORE than our fetch window, not whether we trimmed
    # to max_results -- the caller asked for a page, and a page is not a bounded search.
    return SearchResult(query=query, paths=ranked[:int(max_results)], ok=True,
                        engine="everything", exhaustive=len(lines) < _fetch)


def search_page(query: str, *, limit: int = None, offset: int = 0,
                match_path: bool = False, sort_by_name: bool = True,
                timeout: float = 15.0,
                sort: str = "",
                columns: Optional[List[str]] = None,
                format: str = "",
                regex: bool = False,
                case: bool = False,
                whole_word: bool = False,
                dirs_only: bool = False,
                files_only: bool = False,
                scope: Optional[str] = None,
                attributes: Optional[str] = None) -> SearchResult:
    """Search the Everything index and return a PAGED slice of the ranked result.

    search() hard-caps at ``max_results`` because it asks ES for a fixed over-fetch
    window (``max_results * 10``, floor 200) and trims -- which is correct for a single
    page but makes results ``limit+1`` onward unreachable. This is the paged form: it
    over-fetches a window wide enough to cover ``offset + limit`` (floor 200 for small
    offsets), ranks exact-basename-first, then slices ``[offset : offset+limit]``.

    ``limit`` is now the SIZE OF ONE PAGE from ``offset``, NOT a cap on how much the
    machine can be searched. ``limit=None`` (the default) means NO CAP: return every
    matching path the index holds, ranked exact-basename-first, after ``offset`` skips.
    A caller that wants a bounded page asks for one explicitly (``limit=200``); a caller
    that just says "find it" gets the whole answer, because a silent default ceiling is
    how a wide query on this machine (`es.ex`, `lib`, `.env`) hid every hit past 200.

    ``exhaustive`` is set from the FULL ES answer (all lines, not the slice), so a caller
    can tell "there are more pages past this one" from "we saw everything".

    The full-capability params (sort/columns/format/regex/case/whole_word/dirs_only/
    files_only/scope/attributes) pass through to search(), which owns argv construction.
    ``format='json'`` returns structured Hit records in ``result.hits`` (and a bare-path
    projection in ``result.paths``), sliced to the same offset/limit window.
    """
    if not query or not query.strip():
        return SearchResult(query=query or "", ok=False, error="empty query")

    offset = max(int(offset or 0), 0)
    # limit=None/0 => "no cap, return everything the index holds". Any other number is a
    # page SIZE from ``offset`` -- we still OVER-FETCH then rank then slice so the
    # exact-basename match survives, but the returned slice is bounded only when asked.
    unlimited = limit is None or int(limit or 0) <= 0
    limit = 0 if unlimited else max(int(limit), 1)

    es = resolve_es()
    if es is None:
        # Fall back to the bounded walk; it has no paging, so honour offset/limit by
        # slicing its ranked result (best effort -- the walk may itself be bounded).
        walked = walk_search(query, max_results=0 if unlimited else offset + limit,
                             match_path=match_path)
        walked.paths = walked.paths[offset:] if unlimited else walked.paths[offset:offset + limit]
        return walked

    # OVER-FETCH, THEN RANK, THEN (optionally) SLICE. When unlimited, ask ES for
    # everything (a window wide enough that the -n cap is not the story); when bounded,
    # fetch enough to reach offset+limit so the slice exists in what we hold. Rank first
    # so the exact-basename match still lands at the top of whatever we return (the
    # cap-before-rank bug paid for once).
    fetch = None if unlimited else max((offset + limit) * 10, 200)
    argv = [es, query]
    if match_path:
        argv.append("-match-path")
    if sort:
        if sort not in _SORT_KEYS:
            return SearchResult(query=query, ok=False,
                                error=f"unknown sort key {sort!r} (allowed: {sorted(_SORT_KEYS)})")
        argv.extend(["-sort", sort])
    elif sort_by_name:
        argv.append("-s")
    if columns:
        argv.extend(["-add-columns", ";".join(columns)])
    if format == "json":
        argv.append("-json")
        argv.extend(["-date-format", "1"])
        if not columns:
            argv.extend(["-add-columns",
                         "size;date-modified;date-created;date-accessed;extension;attributes"])
    argv.extend(_build_query_flags(
        regex=regex, case=case, whole_word=whole_word,
        dirs_only=dirs_only, files_only=files_only,
        scope=scope, attributes=attributes,
    ))
    if fetch is not None:
        argv.extend(["-n", str(fetch)])

    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout or 15.0)
    except subprocess.TimeoutExpired:
        return SearchResult(query=query, ok=False, error=f"timed out after {timeout}s")
    except OSError as e:
        return SearchResult(query=query, ok=False, error=f"spawn failed: {e}")

    if proc.returncode != 0:
        err = (proc.stderr or "").strip() or f"exit {proc.returncode}"
        return SearchResult(query=query, ok=False, error=err)

    if format == "json":
        parsed = _parse_json_hits(proc.stdout or "")
        base = os.path.basename(str(query or "").strip().lower())
        parsed.sort(key=lambda h: (os.path.basename(h.path).lower() != base, len(h.path)))
        sliced = parsed[offset:] if unlimited else parsed[offset:offset + limit]
        return SearchResult(
            query=query, paths=[h.path for h in sliced], hits=sliced,
            ok=True, engine="everything",
            exhaustive=True if unlimited else len(parsed) < fetch,
        )

    lines = [ln.rstrip() for ln in (proc.stdout or "").splitlines() if ln.strip()]
    ranked = _rank_exact_first(lines, query)
    sliced = ranked[offset:] if unlimited else ranked[offset:offset + limit]
    # Unlimited means we returned everything ES gave us, therefore exhaustive by
    # definition (there is no further page). Bounded means ES may hold more than our
    # fetch window -- report it honestly so the caller can page.
    return SearchResult(query=query, paths=sliced, ok=True,
                        engine="everything", exhaustive=True if unlimited else len(lines) < fetch)


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


def format_hits(res: SearchResult) -> str:
    """Human-readable render of the STRUCTURED (full-capability) result.

    One aligned line per Hit: mtime, size, then path — so `find --json` reads as a
    sortable inventory, not a bare path list. mtime is the inventory combo's fuel:
    "when was this file last modified" beside "where is it".
    """
    if not res.ok:
        return f"ERROR: {res.error or 'search unavailable'}"
    if not res.hits:
        return f"(no matches for {res.query!r} — Everything answered, nothing found)"

    rows = []
    for h in res.hits:
        mtime = h.date_modified or "?          "[:10]
        size = "" if h.size is None else f"{h.size:>11}"
        rows.append(f"{mtime[:19]:<19} {size}  {h.path}")

    header = (f"{len(res.hits)} match(es) for {res.query!r}  [engine: {res.engine}, "
              f"structured; columns: mtime, size]:")
    return header + "\n" + "\n".join(rows)


def format_result_json(res: SearchResult) -> str:
    """Serialize the full result (paths + structured hits) as JSON for callers that
    want machine-readable output rather than the human render."""
    import dataclasses
    def _hit(h):
        d = dataclasses.asdict(h)
        d.pop("raw", None)
        return d
    return json.dumps({
        "query": res.query,
        "ok": res.ok,
        "error": res.error,
        "engine": res.engine,
        "exhaustive": res.exhaustive,
        "count": res.count,
        "paths": res.paths,
        "hits": [_hit(h) for h in res.hits],
    }, ensure_ascii=False, indent=2)
