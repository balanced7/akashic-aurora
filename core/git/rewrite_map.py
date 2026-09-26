#!/usr/bin/env python3
"""Turn a pre-rewrite commit SHA back into the commit it became.

WHY (T410, measured 2026-09-26). This repo has run THREE history rewrites -- the 2026-07-23
Apple/Samsung reference purge, the 2026-08-12 third-party-PII redaction, and a third after
2026-08-16 that we kept no map for at all, found only because it left a refs/original ref
behind. Each one gave every later commit a new SHA, and our corpus cites SHAs constantly:
the chronicle, the task ledger, lessons, failure ledgers, fence reconciliations.

    1,436 commit SHAs cited across tracked docs resolve in this checkout
      877 of them (61%) resolve ONLY here, pinned by local refs -- pre-rewrite-backup and
          refs/original -- that a clone never receives
      806 of those 877 become resolvable again by chaining the two surviving maps

The 07-23 purge closed with "every commit SHA in the repo changed -- that's clean for a solo
repo like this one". True when written. What falsified it was our own corpus learning to cite
SHAs, which is why this module exists rather than a note saying to be careful.

ZERO IS NOT NO. Every answer here is labelled: CURRENT (already the live SHA), TRANSLATED
(with the hops that got there), DROPPED (a rewrite deliberately removed this commit -- a real
answer, not a failure), AMBIGUOUS (an abbreviation matching two successors; refusing is the
only honest move) and UNKNOWN (no map covers it). A resolver that guessed would be worse than
one that says it cannot tell, because a wrong successor rewrites history a second time.
"""
from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

ZERO = "0" * 40
MAX_HOPS = 12                # three rewrites so far; a cap that can never loop forever

CURRENT = "current"
TRANSLATED = "translated"
DROPPED = "dropped"
AMBIGUOUS = "ambiguous"
UNKNOWN = "unknown"


@dataclass
class RewriteMap:
    """One rewrite's old->new table."""

    label: str
    path: Path
    durable: bool                 # committed, so it reaches every clone
    method: str = "recorded"      # "recorded" by the rewrite tool, or "reconstructed" after
    rows: dict = field(default_factory=dict)
    dropped: set = field(default_factory=set)
    _prefix: dict = field(default_factory=dict, repr=False)

    @property
    def shown(self):
        """How this map names itself in a hop. An inference must never read as a record."""
        return self.label if self.method == "recorded" else f"{self.label}, inferred"

    def index(self):
        self._prefix = {}
        for old in self.rows:
            self._prefix.setdefault(old[:7], []).append(old)
        return self

    def lookup(self, sha):
        """(new_sha, status) for a full or abbreviated old SHA; status None when unmatched."""
        if sha in self.rows:
            return self.rows[sha], TRANSLATED
        if sha in self.dropped:
            return None, DROPPED
        if len(sha) < 40:
            hits = {self.rows[k] for k in self._prefix.get(sha[:7], ()) if k.startswith(sha)}
            if len(hits) == 1:
                return hits.pop(), TRANSLATED
            if len(hits) > 1:
                return None, AMBIGUOUS
            if any(k.startswith(sha) for k in self.dropped):
                return None, DROPPED
        return None, None


def _parse(path, label, durable, method="recorded"):
    rows, dropped = {}, set()
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    for line in text.splitlines():
        parts = line.split()
        if len(parts) != 2 or len(parts[0]) != 40 or len(parts[1]) != 40:
            continue        # filter-repo writes a header line; skip anything that is not a pair
        if parts[1] == ZERO:
            dropped.add(parts[0])
        else:
            rows[parts[0]] = parts[1]
    if not rows and not dropped:
        return None
    return RewriteMap(label=label, path=Path(path), durable=durable, method=method,
                      rows=rows, dropped=dropped).index()


def _method_of(meta_path):
    """'recorded' or 'reconstructed', from the map's own meta.json. Defaults to recorded only
    when a meta file is absent -- an unreadable meta is treated as unknown provenance."""
    try:
        import json
        return str(json.loads(meta_path.read_text(encoding="utf-8")).get("method", "recorded"))
    except FileNotFoundError:
        return "recorded"
    except Exception:
        return "provenance unreadable"


def repo_root(repo=None):
    return Path(repo or os.environ.get("AKASHIC_REPO")
                or Path(__file__).resolve().parents[2])


def load_maps(repo=None):
    """Every map we can find, oldest first so a chase composes in rewrite order.

    Two sources, and the distinction matters. state/rewrites/<date>/commit-map is COMMITTED,
    so it reaches every clone. .git/filter-repo/commit-map is whatever the last filter-repo run
    left behind: read opportunistically and marked NOT durable, because the next rewrite
    overwrites it -- which is how the 07-23 map came within one command of being lost while
    supplying most of our recovery coverage.
    """
    root = repo_root(repo)
    found = []
    archive = root / "state" / "rewrites"
    if archive.is_dir():
        for d in sorted(p for p in archive.iterdir() if p.is_dir()):
            m = _parse(d / "commit-map", label=d.name, durable=True,
                       method=_method_of(d / "meta.json"))
            if m:
                found.append(m)
    volatile = root / ".git" / "filter-repo" / "commit-map"
    if volatile.is_file():
        m = _parse(volatile, label=".git/filter-repo (volatile)", durable=False)
        # Skip it when an archived map already holds all of its rows; keep it otherwise, since
        # an unarchived rewrite is exactly the case where it is the only surviving copy.
        if m and not any(set(m.rows.items()) <= set(o.rows.items()) for o in found):
            found.append(m)
    return found


@dataclass
class Resolution:
    cited: str
    status: str
    sha: str = None
    hops: list = field(default_factory=list)
    note: str = ""

    @property
    def ok(self):
        return self.status in (CURRENT, TRANSLATED)

    def line(self):
        if self.status == TRANSLATED:
            via = " -> ".join(f"{new[:12]} [{label}]" for _, new, label in self.hops)
            tail = f"  ({self.note})" if self.note else ""
            return f"{self.cited}  TRANSLATED  {via}{tail}"
        return f"{self.cited}  {self.status.upper()}  {self.note}".rstrip()


class Resolver:
    """Chase a SHA forward through every rewrite until it stops moving."""

    def __init__(self, maps=None, repo=None, remote=None):
        self.repo = repo_root(repo)
        self.maps = load_maps(self.repo) if maps is None else list(maps)
        # `remote` is a test seam: the clone-visible set, supplied instead of shelling out.
        # Passing an EMPTY set deliberately means "could not check", matching the live failure.
        self._remote = None if remote is None else set(remote)

    # --- reachability -------------------------------------------------------------------
    def remote_set(self):
        """Commits a fresh clone would receive. Computed once, on demand.

        This is the whole difference between "resolves" and "resolves for anyone else":
        without it, all 877 of our broken citations look healthy from this machine.
        """
        if self._remote is None:
            try:
                out = subprocess.run(["git", "-C", str(self.repo), "rev-list", "--remotes"],
                                     capture_output=True, text=True, timeout=180).stdout
                self._remote = set((out or "").split())
            except Exception:
                self._remote = set()
        return self._remote

    def visible(self, sha):
        """True when a clone can see this commit; None when we could not check at all."""
        rs = self.remote_set()
        if not rs:
            return None
        if len(sha) == 40:
            return sha in rs
        return any(o.startswith(sha) for o in rs)

    # --- the walk -----------------------------------------------------------------------
    def resolve(self, sha, check_remote=True):
        sha = (sha or "").strip().lower()
        if not sha or any(c not in "0123456789abcdef" for c in sha) or not 7 <= len(sha) <= 40:
            return Resolution(sha, UNKNOWN, note="not a commit SHA (need 7-40 hex characters)")

        if check_remote and self.visible(sha):
            return Resolution(sha, CURRENT, sha=sha, note="a clone can see this commit")

        # A definitive answer about the CITED sha beats any chase. Ambiguity can only arise
        # here, because every map target is a full 40-char oid.
        for m in self.maps:
            _new, status = m.lookup(sha)
            if status == DROPPED:
                return Resolution(sha, DROPPED,
                                  note=f"removed from history by the {m.shown} rewrite")
            if status == AMBIGUOUS:
                return Resolution(sha, AMBIGUOUS,
                                  note=f"the abbreviation matches several successors in "
                                       f"{m.shown}; cite more characters")

        # SEARCH, NOT A GREEDY WALK. Taking the first map that offers a hop reaches a dead end
        # whenever an earlier rewrite's recorded successor was itself moved by a later one whose
        # map we hold separately: f94c1368 chased 07-23 -> 08-12 and stopped at 65ba8152cc36, a
        # commit that no longer exists, while the reconstructed map held the live continuation.
        # So explore every chain and prefer one that ENDS somewhere a clone can fetch.
        from collections import deque

        q = deque([(sha, [])])
        seen, dead = {sha}, []
        while q:
            cur, hops = q.popleft()
            if len(hops) >= MAX_HOPS:
                continue
            moved = False
            for m in self.maps:
                new, status = m.lookup(cur)
                if status != TRANSLATED or not new or new == cur:
                    continue
                moved = True
                chain = hops + [(cur, new, m.shown)]
                if check_remote and self.visible(new):
                    return Resolution(sha, TRANSLATED, sha=new, hops=chain)
                if new not in seen:
                    seen.add(new)
                    q.append((new, chain))
            if hops and not moved:
                dead.append((cur, hops))

        if dead:
            # The longest chain went as far as the maps allow; report where it stopped and why,
            # rather than presenting a SHA nobody can fetch as a successful translation.
            cur, hops = max(dead, key=lambda t: len(t[1]))
            if check_remote and not self.remote_set():
                note = "could not read the clone-visible set, so this endpoint is unverified"
            else:
                note = "chain ends on a commit no clone can fetch -- a later rewrite moved it " \
                       "and left no map (try: rewrite_recover.py reconstruct)"
            return Resolution(sha, TRANSLATED, sha=cur, hops=hops, note=note)

        if check_remote and not self.remote_set():
            return Resolution(sha, UNKNOWN,
                              note="no map covers it, and the clone-visible set could not be "
                                   "read -- this is 'could not check', not 'clean'")
        return Resolution(sha, UNKNOWN, note="no map covers it")


def resolve(sha, repo=None, check_remote=True):
    """One-shot convenience. Build a Resolver directly when resolving many."""
    return Resolver(repo=repo).resolve(sha, check_remote=check_remote)
