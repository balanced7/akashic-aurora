"""The DISK plane of the delta door -- what moved that no Aurora plane recorded.

PINS: ``tests/test_the_wake_delta_names_who_changed_what.py``.
SIBLING, NOT RIVAL: ``agent/harness/delta.py`` (T052) owns "what moved since I was last here" on
the planes -- a per-agent mark over git_commit / ledger_seq / notes_head / promoted_id. This module
never re-answers that. It answers the question T052 structurally cannot:

  1. UNCOMMITTED work. T052's position IS ``git_commit``, so anything written and not committed is
     invisible to it. Measured 2026-10-07: ~60 modified tracked files and 300+ untracked paths.
  2. WORK OUTSIDE THE REPO. T052 pins REPO to the repo directory. A single day's work landed in
     three trees: the repo, the PRIVATE documents tree, and volatile TEMP.
  3. PER-FILE ATTRIBUTION. Every seat in this house commits as one git author, so "who changed
     this" is unanswerable from the plane T052 reads.

``touch.py`` names the hazard of doing this badly: "One fact on the spine twice under two names
would be a second writer for one transition, which is the rival assembler both maps warn about."
So this reports the GAP, never the overlap.

WHY IT IS BUILDABLE NOW. It asks ``find`` for a date order and takes the answer. That verb is
backed by the Everything index and answers in ~0.64 s where a tree walk costs 10.4 s and 172,070
stat() calls -- but until 2026-10-07 every ``--sort`` key and every ``--preset`` was silently
inert, so "what changed, newest first" had no fast answer anywhere in the house.

THREE TREES, THREE FATES, and only one of them is an alarm:
  ``repo``      durable and reviewable -- git has it or will.
  ``private``   durable and MUST NEVER be committed. Read to report on, never copied.
  ``volatile``  TEMP, scratchpads and the ramdisk. Gone at the next reboot or sweep. The headline.

METADATA ONLY. Name, size and mtime. This organ is pointed at a directory holding tax returns and
identity documents, so never reading contents is not a style choice -- it is the reason it is safe
to point there at all. Same rule ``touch.py`` already holds: "NOTHING RAW IS STORED."

HONEST DENOMINATORS. Every report says how many roots it scanned, how many it skipped and why, how
many files it examined, and how many touch records were DROPPED before it ran. ``touch.drops()``
read 214 when this was written; its own Law 2 is already written: "a swallowed failure that is not
COUNTED is just a lie with better manners."
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Sequence

#: Trees whose contents vanish. Checked FIRST, because a worktree on the ramdisk is volatile no
#: matter how repo-shaped its path looks.
_VOLATILE_MARKS = (
    "appdata\\local\\temp", "appdata/local/temp",
    "\\temp\\", "/temp/", "\\scratchpad", "/scratchpad",
)
_VOLATILE_DRIVES = ("x:",)          # the ramdisk: logs and scratch only, by standing rule

#: The private tree. Read to report on; never copied, never committed.
_PRIVATE_MARKS = ("desktop\\!documents", "desktop/!documents")

#: Root names that are test debris. Measured 2026-10-07: `touch.default_roots()` returned 63
#: worktrees and 46 matched these -- season dry-runs, probes and one t187 shadow. They all still
#: EXIST on disk, so a naive sweep does not fail; it quietly reports test garbage as the house's
#: activity, which is the worse failure.
_DEBRIS_MARKS = ("season_dryrun", "season_fan_calibration", "probe_", "t187_", "/shadow", "\\shadow")


def _repo_root() -> str:
    try:
        from core import paths
        return str(paths.repo_root())
    except Exception:                                                     # noqa: BLE001
        return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def classify_tree(path: str) -> str:
    """``repo`` | ``private`` | ``volatile`` | ``other`` -- three fates and an escape hatch.

    Order matters: volatile wins over everything, because a worktree living under TEMP or on the
    ramdisk is losable regardless of how repo-shaped its path reads.
    """
    p = str(path or "").replace("/", "\\").lower()
    if p[:2] in _VOLATILE_DRIVES:
        return "volatile"
    if any(m.replace("/", "\\") in p for m in _VOLATILE_MARKS):
        return "volatile"
    if any(m.replace("/", "\\") in p for m in _PRIVATE_MARKS):
        return "private"
    if p.startswith(_repo_root().replace("/", "\\").lower()):
        return "repo"
    return "other"


def is_debris(root: str) -> bool:
    """A registered root that is test residue rather than a place work happens."""
    r = str(root or "").replace("/", "\\").lower()
    return any(m.replace("/", "\\") in r for m in _DEBRIS_MARKS)


# --------------------------------------------------------------------------- attribution


@dataclass(frozen=True)
class Attribution:
    """WHO changed a file, and HOW WELL WE KNOW.

    Three answers, never two. ``seat=None, source="unattributed"`` is a value, not a failure: a
    file nothing recorded is a real fact about the house, and it must never be indistinguishable
    from one a seat claimed. ``touch.py`` already holds this discipline for its own records and
    this inherits it rather than inventing a weaker one.

    ``source`` travels with the answer because the claims are not equally strong: the touch stream
    carries ``(session_id, agent_id)`` per action and can separate two incarnations of one seat,
    whereas git author cannot -- every seat here commits under the same name.
    """

    seat: Optional[str] = None
    session: Optional[str] = None
    source: str = "unattributed"
    at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"seat": self.seat, "session": self.session, "source": self.source, "at": self.at}


def _touch_records_for(key: str) -> List[Dict[str, Any]]:
    """Touch records naming this target, or [] when the spine cannot answer. Never raises."""
    try:
        from core.events.event_query import get_event_query
        return list(get_event_query().events_for_ref(key) or [])
    except Exception:                                                     # noqa: BLE001
        return []


def attribute(path: str, *, since_ts: float = 0.0) -> Attribution:
    """Who touched ``path``, per the touch stream -- or UNATTRIBUTED, said out loud.

    The touch stream is the only plane carrying ``(session_id, agent_id)`` per action, which is
    what separates two live incarnations of one seat. It is also LOSSY and counts its own losses,
    so a caller must read :func:`touch_drops` beside any answer from here.
    """
    key = str(path or "")
    for cand in (key, os.path.basename(key), key.replace("\\", "/")):
        for rec in _touch_records_for(cand):
            seat = rec.get("agent_id") or None
            sess = rec.get("session_id") or None
            if not (seat or sess):
                continue
            return Attribution(seat=seat, session=sess, source="touch",
                               at=rec.get("ts") or rec.get("at"))
    return Attribution()


def touch_drops() -> Optional[int]:
    """How many touches were SWALLOWED before this ran. None when unreadable -- never a cheerful 0."""
    try:
        from core.events import touch
        return int(touch.drops())
    except Exception:                                                     # noqa: BLE001
        return None


# --------------------------------------------------------------------------- the sweep


@dataclass(frozen=True)
class Change:
    path: str
    mtime: float
    size: int
    tree: str
    attribution: Attribution = field(default_factory=Attribution)

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "mtime": self.mtime, "size": self.size, "tree": self.tree,
                "attribution": self.attribution.to_dict()}


@dataclass
class DiskDelta:
    """The envelope. Carries its own denominator, because a count without one is the cheapest lie
    a tool can tell -- and without it "nothing changed" and "nothing was looked at" render the
    same."""

    changes: List[Change] = field(default_factory=list)
    roots_scanned: List[str] = field(default_factory=list)
    roots_skipped: List[str] = field(default_factory=list)
    files_examined: int = 0
    window_hours: float = 0.0
    drops: Optional[int] = None
    degraded: List[str] = field(default_factory=list)

    def __iter__(self) -> Iterator[Change]:
        return iter(self.changes)

    def __len__(self) -> int:
        return len(self.changes)

    def by_tree(self, tree: str) -> List[Change]:
        return [c for c in self.changes if c.tree == tree]

    def to_dict(self) -> Dict[str, Any]:
        return {"window_hours": self.window_hours,
                "files_examined": self.files_examined,
                "roots_scanned": self.roots_scanned,
                "roots_skipped": self.roots_skipped,
                "touch_drops": self.drops,
                "degraded": self.degraded,
                "counts": {t: len(self.by_tree(t)) for t in ("repo", "private", "volatile", "other")},
                "changes": [c.to_dict() for c in self.changes]}


def default_scopes() -> List[str]:
    """The trees worth sweeping: the house's own registered roots MINUS the test debris, plus the
    private and volatile trees T052 never looks at.

    `touch.default_roots()` is the right source and the wrong default: measured 2026-10-07 it
    returned 63 worktrees of which 46 were dry-run shadows. Taking it wholesale reports test
    garbage as activity, so it is filtered rather than trusted.
    """
    # NORMALISED, because `E:\AI-Setup` and `E:/AI-Setup` are one tree with two spellings and a
    # string compare treats them as two. The first run scanned both and emitted 59 duplicate rows.
    out: List[str] = []
    seen = set()

    def _add(p: str) -> None:
        if not p or not os.path.isdir(p):
            return
        canon = os.path.normcase(os.path.realpath(p))
        if canon in seen:
            return
        seen.add(canon)
        out.append(p)

    _add(_repo_root())
    try:
        from core.events import touch
        for w in list(touch.default_roots().worktrees):
            if not is_debris(w):
                _add(w)
    except Exception:                                                     # noqa: BLE001
        pass
    home = os.path.expanduser("~")
    _add(os.path.join(home, "Desktop", "!Documents"))
    _add(os.path.join(home, "AppData", "Local", "Temp", "claude"))
    return out


def _find_recent(scope: str, limit: int, timeout: float) -> tuple:
    """Ask the indexed `find` verb for this scope, newest first. Returns (hits, degraded_reason)."""
    argv = [sys.executable, "-X", "utf8", os.path.join(_repo_root(), "agent_cli.py"),
            "find", "*", "--scope", scope, "--preset", "recent", "--files",
            "--format", "json", "--limit", str(int(limit))]
    try:
        res = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8",
                             errors="replace", cwd=_repo_root(), timeout=timeout)
    except Exception as exc:                                              # noqa: BLE001
        return ([], "%s: %s" % (type(exc).__name__, exc))
    if res.returncode != 0:
        return ([], (res.stderr or "").strip()[:160] or "exit %s" % res.returncode)
    try:
        return (json.loads(res.stdout).get("hits", []) or [], None)
    except Exception as exc:                                              # noqa: BLE001
        return ([], "unparseable find output (%s)" % type(exc).__name__)


def _mtime_of(hit: Dict[str, Any]) -> Optional[float]:
    raw = hit.get("date_modified") or hit.get("date-modified") or ""
    if not raw:
        return None
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(raw)[:19]).timestamp()
    except Exception:                                                     # noqa: BLE001
        return None


#: Derived artifacts: machine output, not anyone's work. Excluded by default because a wake-time
#: report is read by a person, and a list where the authored files are outnumbered by bytecode is
#: a list nobody finishes. Measured while building this: a single pytest run emitted enough .pyc
#: churn to make two sweeps a second apart disagree -- the instrument was perturbing its own
#: measurement.
_NOISE_MARKS = ("__pycache__", ".pyc", ".pyo", "\\.git\\", "/.git/", "node_modules",
                "\\.pytest_cache", "/.pytest_cache",
                # Claude Code's internal diff workspace holds a BARE git store, so its object
                # files sit under \objects\ with no \.git\ in the path and slipped the filter
                # above: 968 of the first run's 973 volatile rows were these. Measured, not feared.
                "bash-edit-diff",
                # background task logs: machine output about machine work
                "\\tasks\\", "/tasks/")


def is_noise(path: str) -> bool:
    p = str(path or "").replace("/", "\\").lower()
    return any(m.replace("/", "\\") in p for m in _NOISE_MARKS)


def since(hours: float = 12.0, *, roots: Optional[Sequence[str]] = None,
          limit_per_root: int = 2000, attribute_changes: bool = True,
          timeout: float = 60.0, now: Optional[float] = None,
          include_noise: bool = False) -> DiskDelta:
    """What moved on disk in the last ``hours``, by tree, with attribution where it exists.

    ``now`` ANCHORS THE WINDOW. Without it the window slides with the wall clock, so two calls a
    second apart genuinely cover different spans and a published number cannot be re-derived --
    the same reason ``recall-audit`` takes a seed. Pass the anchor to make a report auditable.

    The index is asked for a date order and the answer is taken, never re-sorted: re-sorting here
    would re-create the defect that made ``--sort`` inert for as long as it was.
    """
    scopes = [str(r) for r in (roots if roots is not None else default_scopes())]
    anchor = float(now) if now is not None else time.time()
    cutoff = anchor - (float(hours) * 3600.0)
    out = DiskDelta(window_hours=float(hours), drops=touch_drops())

    for scope in scopes:
        if is_debris(scope):
            out.roots_skipped.append("%s  (test debris)" % scope)
            continue
        if not os.path.isdir(scope):
            out.roots_skipped.append("%s  (absent)" % scope)
            continue
        hits, degraded = _find_recent(scope, limit_per_root, timeout)
        if degraded:
            out.degraded.append("%s: %s" % (scope, degraded))
        out.roots_scanned.append(scope)
        for h in hits:
            out.files_examined += 1
            p = h.get("path") or ""
            if not include_noise and is_noise(p):
                continue
            mt = _mtime_of(h)
            if mt is None or mt < cutoff or mt > anchor:
                continue
            try:
                size = int(h.get("size") or 0)
            except Exception:                                             # noqa: BLE001
                size = 0
            out.changes.append(Change(path=p, mtime=mt, size=size, tree=classify_tree(p)))

    # One file reached through two overlapping roots is still one change.
    _seen_paths = set()
    _deduped: List[Change] = []
    for c in out.changes:
        canon = os.path.normcase(c.path)
        if canon in _seen_paths:
            continue
        _seen_paths.add(canon)
        _deduped.append(c)
    out.changes = _deduped
    out.changes.sort(key=lambda c: (-c.mtime, c.path))
    if attribute_changes:
        out.changes = [Change(path=c.path, mtime=c.mtime, size=c.size, tree=c.tree,
                              attribution=attribute(c.path, since_ts=cutoff))
                       for c in out.changes]
    return out


# --------------------------------------------------------------------------- render


def render(d: DiskDelta, *, cap: int = 12) -> str:
    """Operator-facing. VOLATILE first, because it is the only class that disappears."""
    lines = ["[delta --disk] last %.1fh | %d change(s) over %d file(s) examined | %d root(s), "
             "%d skipped" % (d.window_hours, len(d.changes), d.files_examined,
                             len(d.roots_scanned), len(d.roots_skipped))]
    if d.drops is None:
        lines.append("  attribution: touch drop count UNREADABLE -- treat every seat below as a floor")
    elif d.drops:
        lines.append("  attribution: %d touch record(s) were DROPPED before this ran; unattributed "
                     "rows may simply be lost, not unowned" % d.drops)
    for reason in d.degraded[:3]:
        lines.append("  DEGRADED %s" % reason)

    for tree, banner in (("volatile", "VOLATILE -- gone at the next reboot or temp sweep"),
                         ("private", "private (read-only here; never committed)"),
                         ("repo", "repo"),
                         ("other", "other")):
        rows = d.by_tree(tree)
        if not rows:
            continue
        lines.append("  %s: %d" % (banner, len(rows)))
        for c in rows[:cap]:
            who = c.attribution.seat or "UNATTRIBUTED"
            src = "" if c.attribution.source == "touch" else "  (%s)" % c.attribution.source
            lines.append("    %s  %-44s %s%s"
                         % (time.strftime("%m-%d %H:%M", time.localtime(c.mtime)),
                            os.path.basename(c.path)[:44], who, src))
        if len(rows) > cap:
            lines.append("    ...+%d more" % (len(rows) - cap))
    return "\n".join(lines)
